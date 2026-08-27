"""Replay grounded generation from persisted, ACL-filtered retrieval context.

This avoids loading the CPU CrossEncoder and Qwen in the same process on the
constrained local machine.  It never queries or modifies PostgreSQL; the input
artifact must have been produced by a read-only retrieval evaluation.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from typing import Any

from portproject_rag.generation import generate_grounded_answer
from portproject_rag.settings import Settings


def _write_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _evidence(question: dict[str, Any]) -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            source_id=item["source_id"],
            filename=item["filename"],
            page_number=item["page_number"],
            section_title=item.get("section_title"),
            clause_number=item.get("clause_number"),
            context_text=item["context_text"],
        )
        for item in question.get("retrieved_chunks", [])
    ]


def _record(question: dict[str, Any], settings: Settings) -> dict[str, Any]:
    evidence = _evidence(question)
    started = perf_counter()
    try:
        generated = generate_grounded_answer(settings, question["question"], evidence, settings.llm_primary_model)
    except Exception as exc:  # noqa: BLE001 - preserve a checkpointed failure without sensitive details
        return {
            "id": question["id"], "question": question["question"], "status": "generation_failed",
            "retrieved_chunks": question.get("retrieved_chunks", []),
            "generation_error": type(exc).__name__, "duration_ms": round((perf_counter() - started) * 1000),
        }
    return {
        "id": question["id"], "question": question["question"], "status": "completed",
        "retrieved_chunks": question.get("retrieved_chunks", []),
        "answer": generated.answer, "raw_answer": generated.raw_answer,
        "citation_valid": generated.citation_valid, "citation_error": generated.citation_error,
        "first_pass_citation_valid": generated.first_pass_citation_valid,
        "citation_repair_used": generated.citation_repair_used,
        "citation_repair_succeeded": generated.citation_repair_succeeded,
        "disposition": generated.disposition, "stop_reason": generated.stop_reason,
        "prompt_eval_count": generated.prompt_eval_count, "eval_count": generated.eval_count,
        "timings_ms": {
            "prompt_build_ms": generated.prompt_build_ms,
            "model_load_ms": generated.model_load_ms,
            "prompt_eval_ms": generated.prompt_eval_ms,
            "token_generation_ms": generated.token_generation_ms,
            "generation_ms": generated.generation_ms,
            "citation_validation_ms": generated.citation_validation_ms,
            "answer_assembly_ms": generated.answer_assembly_ms,
            "total_ms": round((perf_counter() - started) * 1000),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrieval-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compact-instructions", action="store_true")
    args = parser.parse_args()

    retrieval = json.loads(args.retrieval_artifact.read_text(encoding="utf-8"))
    if retrieval.get("generation_enabled") is not False or retrieval.get("pipeline_parameters_changed") is not False:
        raise SystemExit("Input must be an unchanged, retrieval-only evaluation artifact.")
    settings = Settings().model_copy(
        update={
            "generation_temperature": 0.0,
            "generation_compact_instructions": args.compact_instructions,
        }
    )
    payload: dict[str, Any] = {
        "schema_version": "rag_generation_replay_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "retrieval_artifact": str(args.retrieval_artifact),
        "normal_corpus_read_only": True,
        "generation_configuration": {
            "model": settings.llm_primary_model,
            "temperature": settings.generation_temperature,
            "keep_alive": settings.generation_keep_alive,
            "compact_instructions": settings.generation_compact_instructions,
        },
        "checkpointed": True,
        "questions": [],
    }
    for question in retrieval.get("questions", []):
        if question.get("status") != "completed" or not question.get("retrieved_chunks"):
            continue
        payload["questions"].append(_record(question, settings))
        _write_checkpoint(args.output, payload)
    records = payload["questions"]
    payload["summary"] = {
        "generation_requested": len(records),
        "generation_returned": sum(record["status"] == "completed" for record in records),
        "generation_timeouts": sum(record.get("generation_error") == "RagStageError" for record in records),
        "first_pass_citation_valid": sum(record.get("first_pass_citation_valid") is True for record in records),
        "final_citation_valid": sum(record.get("citation_valid") is True for record in records),
    }
    _write_checkpoint(args.output, payload)
    print(json.dumps({"output": str(args.output), **payload["summary"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
