"""Read-only, repeatable latency profiling for the certified RAG contract.

The script intentionally uses the live pipeline and records timings only.  It
refuses any database other than the normal certified corpus because it is not
an acceptance fixture validator and must not mix fixture evidence with the
normal-corpus performance baseline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from portproject_rag.evaluation import load_evaluation_contract
from portproject_rag.generation import generate_grounded_answer
from portproject_rag.query_analysis import (
    classify_source_domain,
    needs_property_clarification,
)
from portproject_rag.retrieval import retrieve
from portproject_rag.settings import Settings


def _settings_summary(settings: Settings) -> dict[str, Any]:
    return {
        "embedding_model": settings.embedding_model,
        "generation_model": settings.llm_primary_model,
        "reranker_model": settings.reranker_model,
        "reranker_batch_size": settings.reranker_batch_size,
        "rerank_candidate_count": settings.rerank_candidate_count,
        "candidate_pool_size": settings.candidate_pool_size,
        "final_context_source_count": settings.final_context_source_count,
        "final_context_source_count_direct": settings.final_context_source_count_direct,
        "final_context_source_count_table": settings.final_context_source_count_table,
        "generation_keep_alive": settings.generation_keep_alive,
        "generation_temperature": settings.generation_temperature,
    }


def _profile_one(settings: Settings, example: dict[str, Any], run_number: int) -> dict[str, Any]:
    started = perf_counter()
    retrieval = retrieve(settings, example["question"], example["allowed_role"])
    generated = generate_grounded_answer(settings, example["question"], retrieval.chunks, settings.llm_primary_model)
    return {
        "id": example["id"],
        "run": run_number,
        "answer_shape": example.get("expected_answer_shape"),
        "source_pairs": [{"filename": chunk.filename, "page": chunk.page_number} for chunk in retrieval.chunks],
        "citation_valid": generated.citation_valid,
        "answer_disposition": generated.disposition,
        "answer_sha256": hashlib.sha256(generated.answer.encode("utf-8")).hexdigest(),
        "timings_ms": {
            "query_analysis_ms": retrieval.timings.query_analysis_ms,
            "embed_ms": retrieval.timings.embed_ms,
            "lexical_retrieval_ms": retrieval.timings.lexical_retrieval_ms,
            "dense_retrieval_ms": retrieval.timings.dense_retrieval_ms,
            "candidate_fusion_ms": retrieval.timings.candidate_fusion_ms,
            "adjacent_candidates_ms": retrieval.timings.adjacent_candidates_ms,
            "rerank_ms": retrieval.timings.rerank_ms,
            "reranker_load_ms": retrieval.timings.reranker_load_ms,
            "reranker_pair_build_ms": retrieval.timings.reranker_pair_build_ms,
            "reranker_predict_ms": retrieval.timings.reranker_predict_ms,
            "reranker_postprocess_ms": retrieval.timings.reranker_postprocess_ms,
            "context_selection_ms": retrieval.timings.context_selection_ms,
            "context_assembly_ms": retrieval.timings.context_assembly_ms,
            "prompt_build_ms": generated.prompt_build_ms,
            "model_load_ms": generated.model_load_ms,
            "prompt_eval_ms": generated.prompt_eval_ms,
            "token_generation_ms": generated.token_generation_ms,
            "generation_ms": generated.generation_ms,
            "citation_validation_ms": generated.citation_validation_ms,
            "answer_assembly_ms": generated.answer_assembly_ms,
            "total_ms": round((perf_counter() - started) * 1000),
        },
        "tokens": {"prompt_eval_count": generated.prompt_eval_count, "eval_count": generated.eval_count},
        "stop_reason": generated.stop_reason,
        "context": {
            "source_count": len(retrieval.chunks),
            "estimated_tokens": retrieval.diagnostics.context_tokens if retrieval.diagnostics else None,
            "budget_tokens": retrieval.diagnostics.context_budget_tokens if retrieval.diagnostics else None,
            "truncated": retrieval.diagnostics.context_truncated if retrieval.diagnostics else None,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path("evaluation/rag_answer_contract_v2.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ids", nargs="+", required=True, help="Reviewed document-RAG contract IDs to repeat.")
    parser.add_argument("--repetitions", type=int, default=4, choices=range(1, 9))
    args = parser.parse_args()

    settings = Settings()
    database_name = settings.database_url.path.lstrip("/")
    if database_name != "portproject":
        raise SystemExit("This read-only normal-corpus profiler requires database portproject; no run was performed.")
    _version, examples = load_evaluation_contract(args.contract)
    wanted = set(args.ids)
    selected = [example for example in examples if example["id"] in wanted]
    if {example["id"] for example in selected} != wanted:
        raise SystemExit("One or more requested contract IDs are unknown; no run was performed.")
    for example in selected:
        if classify_source_domain(example["question"]) != "DOCUMENT_RAG" or needs_property_clarification(example["question"]):
            raise SystemExit("Performance repetitions must use document-RAG cases, not routed or clarification cases.")

    effective = settings.model_copy(update={"generation_temperature": 0.0})
    records = [
        _profile_one(effective, example, run_number)
        for run_number in range(1, args.repetitions + 1)
        for example in selected
    ]
    payload = {
        "schema_version": "rag_performance_profile_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "database": database_name,
        "read_only": True,
        "contract": str(args.contract),
        "contract_ids": sorted(wanted),
        "repetitions": args.repetitions,
        "configuration": _settings_summary(effective),
        "records": records,
        "notes": [
            "The first record is process-cold for retrieval. Ollama model warmth depends on its actual keep-alive state and is measured by load telemetry.",
            "Answers are represented by SHA-256 only; full quality and citation artifacts remain in the frozen evaluation outputs.",
            "The script issues read-only retrieval queries and writes only the requested local artifact.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "records": len(records), "database": database_name}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
