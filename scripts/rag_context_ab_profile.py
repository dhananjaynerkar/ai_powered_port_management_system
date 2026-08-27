"""Checkpointed same-session generation A/B replay for persisted contexts."""
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


def _evidence(question: dict[str, Any]) -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            source_id=item["source_id"], filename=item["filename"], page_number=item["page_number"],
            section_title=item.get("section_title"), clause_number=item.get("clause_number"),
            context_text=item["context_text"],
        )
        for item in question["retrieved_chunks"]
    ]


def _run(label: str, question: dict[str, Any], settings: Settings) -> dict[str, Any]:
    started = perf_counter()
    generated = generate_grounded_answer(settings, question["question"], _evidence(question), settings.llm_primary_model)
    return {
        "variant": label, "id": question["id"], "citation_valid": generated.citation_valid,
        "disposition": generated.disposition, "answer": generated.answer,
        "source_count": len(question["retrieved_chunks"]),
        "context_characters": sum(len(item["context_text"]) for item in question["retrieved_chunks"]),
        "prompt_eval_count": generated.prompt_eval_count, "eval_count": generated.eval_count,
        "timings_ms": {
            "model_load_ms": generated.model_load_ms, "prompt_eval_ms": generated.prompt_eval_ms,
            "token_generation_ms": generated.token_generation_ms, "generation_ms": generated.generation_ms,
            "total_ms": round((perf_counter() - started) * 1000),
        },
    }


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ids", nargs="+", required=True)
    parser.add_argument("--candidate-compact-instructions", action="store_true")
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    for payload in (baseline, candidate):
        if payload.get("generation_enabled") is not False:
            raise SystemExit("A/B inputs must be unchanged retrieval-only artifacts.")
    wanted = set(args.ids)
    by_variant = {
        "baseline": {item["id"]: item for item in baseline["questions"]},
        "candidate": {item["id"]: item for item in candidate["questions"]},
    }
    if any(item not in by_variant["baseline"] or item not in by_variant["candidate"] for item in wanted):
        raise SystemExit("Requested ID is missing from one A/B artifact.")
    settings = Settings().model_copy(update={"generation_temperature": 0.0})
    candidate_settings = settings.model_copy(
        update={"generation_compact_instructions": args.candidate_compact_instructions}
    )
    payload: dict[str, Any] = {
        "schema_version": "rag_context_ab_profile_v1", "generated_at": datetime.now(UTC).isoformat(),
        "baseline_artifact": str(args.baseline), "candidate_artifact": str(args.candidate),
        "model": settings.llm_primary_model, "temperature": settings.generation_temperature,
        "execution_order": "baseline_then_candidate_per_question",
        "candidate_compact_instructions": args.candidate_compact_instructions,
        "records": [],
    }
    for item_id in args.ids:
        for label in ("baseline", "candidate"):
            active_settings = candidate_settings if label == "candidate" else settings
            payload["records"].append(_run(label, by_variant[label][item_id], active_settings))
            _write(args.output, payload)
    _write(args.output, payload)
    print(json.dumps({"output": str(args.output), "records": len(payload["records"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
