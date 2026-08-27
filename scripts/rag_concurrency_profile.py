"""Read-only two-request concurrency probe for the normal certified corpus.

This probe deliberately exercises the retrieval and generation pipeline in one
Python process.  It is not an API load test: the application query endpoint
also persists chat messages, so using it here would make a performance check
mutate the normal database.  The probe refuses any database other than the
normal ``portproject`` corpus and writes only the requested local artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier, Event, Thread
from time import perf_counter, sleep
from typing import Any

import psutil

from portproject_rag.evaluation import load_evaluation_contract
from portproject_rag.generation import generate_grounded_answer
from portproject_rag.query_analysis import (
    classify_source_domain,
    needs_property_clarification,
)
from portproject_rag.retrieval import retrieve
from portproject_rag.settings import Settings


def _run_one(settings: Settings, example: dict[str, Any], barrier: Barrier) -> dict[str, Any]:
    barrier.wait()
    started = perf_counter()
    try:
        retrieval = retrieve(settings, example["question"], example["allowed_role"])
        generated = generate_grounded_answer(
            settings, example["question"], retrieval.chunks, settings.llm_primary_model
        )
        return {
            "id": example["id"],
            "success": True,
            "citation_valid": generated.citation_valid,
            "answer_disposition": generated.disposition,
            "answer_sha256": hashlib.sha256(generated.answer.encode("utf-8")).hexdigest(),
            "source_count": len(retrieval.chunks),
            "prompt_eval_count": generated.prompt_eval_count,
            "eval_count": generated.eval_count,
            "timings_ms": {
                "retrieval_ms": sum(
                    getattr(retrieval.timings, name)
                    for name in (
                        "query_analysis_ms",
                        "embed_ms",
                        "lexical_retrieval_ms",
                        "dense_retrieval_ms",
                        "candidate_fusion_ms",
                        "adjacent_candidates_ms",
                        "rerank_ms",
                        "context_selection_ms",
                        "context_assembly_ms",
                    )
                ),
                "generation_ms": generated.generation_ms,
                "total_ms": round((perf_counter() - started) * 1000),
            },
            "stop_reason": generated.stop_reason,
        }
    except Exception as exc:  # pragma: no cover - exercised by host/resource failures
        return {
            "id": example["id"],
            "success": False,
            "error_type": type(exc).__name__,
            "timings_ms": {"total_ms": round((perf_counter() - started) * 1000)},
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path("evaluation/rag_answer_contract_v2.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ids", nargs=2, required=True, help="Exactly two reviewed document-RAG contract IDs.")
    args = parser.parse_args()

    settings = Settings().model_copy(update={"generation_temperature": 0.0})
    database_name = settings.database_url.path.lstrip("/")
    if database_name != "portproject":
        raise SystemExit("This read-only normal-corpus probe requires database portproject; no run was performed.")
    _version, examples = load_evaluation_contract(args.contract)
    by_id = {example["id"]: example for example in examples}
    if len(set(args.ids)) != 2 or any(identifier not in by_id for identifier in args.ids):
        raise SystemExit("Both requested contract IDs must be distinct known IDs; no run was performed.")
    selected = [by_id[identifier] for identifier in args.ids]
    for example in selected:
        if classify_source_domain(example["question"]) != "DOCUMENT_RAG" or needs_property_clarification(example["question"]):
            raise SystemExit("Concurrency probe accepts only document-RAG cases; no run was performed.")

    # Sample both the probe process and host headroom throughout warm-up and
    # the two-request window.  This makes resource pressure visible without
    # depending on platform-specific shell tooling.
    process = psutil.Process()
    memory_stop = Event()
    memory_samples: list[dict[str, int]] = []

    def sample_memory() -> None:
        while not memory_stop.is_set():
            try:
                virtual = psutil.virtual_memory()
                memory_samples.append(
                    {
                        "process_rss_bytes": process.memory_info().rss,
                        "available_physical_bytes": virtual.available,
                    }
                )
            except (psutil.Error, OSError):
                pass
            sleep(0.1)

    memory_thread = Thread(target=sample_memory, name="rag-memory-sampler", daemon=True)
    memory_thread.start()

    # Warm the process/model once before measuring exactly two simultaneous calls.
    warm_example = selected[0]
    warm_started = perf_counter()
    warm_retrieval = retrieve(settings, warm_example["question"], warm_example["allowed_role"])
    warm_generated = generate_grounded_answer(
        settings, warm_example["question"], warm_retrieval.chunks, settings.llm_primary_model
    )
    warmup = {
        "id": warm_example["id"],
        "citation_valid": warm_generated.citation_valid,
        "total_ms": round((perf_counter() - warm_started) * 1000),
    }

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="rag-concurrency") as pool:
        futures = [pool.submit(_run_one, settings, example, barrier) for example in selected]
        started = perf_counter()
        results = [future.result() for future in futures]
        wall_ms = round((perf_counter() - started) * 1000)
    memory_stop.set()
    memory_thread.join(timeout=1)

    payload = {
        "schema_version": "rag_concurrency_profile_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "database": database_name,
        "read_only": True,
        "contract": str(args.contract),
        "contract_ids": args.ids,
        "warmup": warmup,
        "simultaneous_requests": 2,
        "wall_ms": wall_ms,
        "memory": {
            "peak_process_rss_bytes": max((sample["process_rss_bytes"] for sample in memory_samples), default=0),
            "minimum_available_physical_bytes": min(
                (sample["available_physical_bytes"] for sample in memory_samples), default=0
            ),
            "sample_count": len(memory_samples),
        },
        "results": results,
        "notes": [
            "The warm-up and both measured calls use the live normal-corpus retrieval and generation pipeline.",
            "The two measured calls are released by a barrier and run in one process using two worker threads.",
            "No API endpoint, chat write, audit write, or expected-answer string is used by this probe.",
            "A successful probe is not a substitute for an HTTP/API load test; it is a pipeline-level concurrency check.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "database": database_name, "wall_ms": wall_ms}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
