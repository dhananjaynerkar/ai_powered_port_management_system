"""Bounded, read-only local RAG capacity experiment.

The experiment runs exactly two reviewed document-RAG requests in one Python
process.  A process-local gate can serialize them (the retained local policy)
or permit two active pipelines for a separately approved experiment.  No API
route, chat write, audit write, or expected-answer text is used.
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

from portproject_rag.capacity import CapacityBusyError, HeavyInferenceGate
from portproject_rag.evaluation import load_evaluation_contract
from portproject_rag.generation import generate_grounded_answer
from portproject_rag.query_analysis import (
    classify_source_domain,
    needs_property_clarification,
)
from portproject_rag.retrieval import retrieve
from portproject_rag.settings import Settings


def _run_one(settings: Settings, example: dict[str, Any], barrier: Barrier, gate: HeavyInferenceGate) -> dict[str, Any]:
    barrier.wait()
    started = perf_counter()
    lease = None
    try:
        lease = gate.acquire()
        retrieval = retrieve(settings, example["question"], example["allowed_role"])
        generated = generate_grounded_answer(settings, example["question"], retrieval.chunks, settings.llm_primary_model)
        return {
            "id": example["id"],
            "success": True,
            "queue_wait_ms": lease.queue_wait_ms,
            "citation_valid": generated.citation_valid,
            "answer_disposition": generated.disposition,
            "answer_sha256": hashlib.sha256(generated.answer.encode("utf-8")).hexdigest(),
            "source_count": len(retrieval.chunks),
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
                "rerank_ms": retrieval.timings.rerank_ms,
                "generation_ms": generated.generation_ms,
                "total_ms": round((perf_counter() - started) * 1000),
            },
            "stop_reason": generated.stop_reason,
        }
    except CapacityBusyError as exc:
        return {
            "id": example["id"],
            "success": False,
            "capacity_rejected": True,
            "queue_wait_ms": exc.queue_wait_ms,
            "error_type": type(exc).__name__,
            "error_reason": exc.reason,
            "timings_ms": {"total_ms": round((perf_counter() - started) * 1000)},
        }
    except Exception as exc:  # pragma: no cover - exercised by native/resource failures
        return {
            "id": example["id"],
            "success": False,
            "capacity_rejected": False,
            "error_type": type(exc).__name__,
            "timings_ms": {"total_ms": round((perf_counter() - started) * 1000)},
        }
    finally:
        if lease is not None:
            lease.release()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path("evaluation/rag_answer_contract_v2.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ids", nargs=2, required=True, help="Exactly two reviewed document-RAG contract IDs.")
    parser.add_argument("--gate-limit", type=int, choices=(1, 2), default=1)
    parser.add_argument("--queue-capacity", type=int, choices=range(0, 3), default=1)
    parser.add_argument("--queue-timeout-seconds", type=int, default=300, choices=range(1, 601))
    args = parser.parse_args()

    settings = Settings().model_copy(update={"generation_temperature": 0.0})
    database_name = settings.database_url.path.lstrip("/")
    if database_name != "portproject":
        raise SystemExit("This read-only normal-corpus capacity profile requires database portproject; no run was performed.")
    _version, examples = load_evaluation_contract(args.contract)
    by_id = {example["id"]: example for example in examples}
    if len(set(args.ids)) != 2 or any(identifier not in by_id for identifier in args.ids):
        raise SystemExit("Both requested contract IDs must be distinct known IDs; no run was performed.")
    selected = [by_id[identifier] for identifier in args.ids]
    for example in selected:
        if classify_source_domain(example["question"]) != "DOCUMENT_RAG" or needs_property_clarification(example["question"]):
            raise SystemExit("Capacity profile accepts only document-RAG cases; no run was performed.")

    process = psutil.Process()
    memory_stop = Event()
    memory_samples: list[dict[str, int]] = []

    def sample_memory() -> None:
        while not memory_stop.is_set():
            try:
                virtual = psutil.virtual_memory()
                swap = psutil.swap_memory()
                memory_samples.append(
                    {
                        "process_rss_bytes": process.memory_info().rss,
                        "available_physical_bytes": virtual.available,
                        "pagefile_used_bytes": swap.used,
                    }
                )
            except (psutil.Error, OSError):
                pass
            sleep(0.1)

    sampler = Thread(target=sample_memory, name="rag-capacity-memory-sampler", daemon=True)
    sampler.start()
    warm_started = perf_counter()
    warm_retrieval = retrieve(settings, selected[0]["question"], selected[0]["allowed_role"])
    warm_generated = generate_grounded_answer(settings, selected[0]["question"], warm_retrieval.chunks, settings.llm_primary_model)
    warmup = {
        "id": selected[0]["id"],
        "citation_valid": warm_generated.citation_valid,
        "total_ms": round((perf_counter() - warm_started) * 1000),
    }

    gate = HeavyInferenceGate(args.gate_limit, args.queue_capacity, args.queue_timeout_seconds)
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="rag-capacity") as pool:
        futures = [pool.submit(_run_one, settings, example, barrier, gate) for example in selected]
        measured_started = perf_counter()
        results = [future.result() for future in futures]
        wall_ms = round((perf_counter() - measured_started) * 1000)
    memory_stop.set()
    sampler.join(timeout=1)
    payload = {
        "schema_version": "rag_capacity_profile_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "database": database_name,
        "read_only": True,
        "contract": str(args.contract),
        "contract_ids": args.ids,
        "configuration": {
            "generation_model": settings.llm_primary_model,
            "embedding_model": settings.embedding_model,
            "reranker_model": settings.reranker_model,
            "generation_keep_alive": settings.generation_keep_alive,
            "generation_timeout_seconds": settings.generation_timeout_seconds,
            "gate_limit": args.gate_limit,
            "queue_capacity": args.queue_capacity,
            "queue_timeout_seconds": args.queue_timeout_seconds,
        },
        "warmup": warmup,
        "simultaneous_requests": 2,
        "wall_ms": wall_ms,
        "memory": {
            "peak_process_rss_bytes": max((sample["process_rss_bytes"] for sample in memory_samples), default=0),
            "minimum_available_physical_bytes": min((sample["available_physical_bytes"] for sample in memory_samples), default=0),
            "peak_pagefile_used_bytes": max((sample["pagefile_used_bytes"] for sample in memory_samples), default=0),
            "sample_count": len(memory_samples),
        },
        "gate_after_run": gate.snapshot(),
        "results": results,
        "notes": [
            "The warm-up and both measured calls use the live normal-corpus retrieval and generation pipeline.",
            "The two measured calls are released by a barrier and run in one process using two worker threads.",
            "No API endpoint, chat write, audit write, or expected-answer string is used by this profile.",
            "A gate limit of one measures bounded serialization; a limit of two is an explicitly separate experiment.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "database": database_name, "wall_ms": wall_ms}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
