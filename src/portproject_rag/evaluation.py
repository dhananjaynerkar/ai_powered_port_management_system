"""Measurement-only evaluation for the reviewed RAG golden set.

This module deliberately calls the existing retrieval and generation functions
without changing their settings.  It produces local, ignored artifacts with
the per-question evidence needed to reproduce a Phase 7 baseline.
"""
from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

from .generation import GenerationResult, generate_grounded_answer
from .retrieval import RetrievalResult, RetrievedChunk, retrieve
from .settings import Settings

_SOURCE_RE = re.compile(r"\[(S\d+)\]")
_ABSTENTION_MARKERS = (
    "does not contain enough evidence",
    "does not contain sufficient evidence",
    "not enough evidence",
    "insufficient evidence",
    "cannot determine",
    "can't determine",
    "cannot be determined",
    "need more information",
    "additional information is required",
    "please provide",
    "not available in the indexed corpus",
    "not found in the indexed corpus",
)


@dataclass(frozen=True, slots=True)
class MetricSummary:
    count: int
    mean: float | None
    p50: float | None
    p95: float | None


def _json_default(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return round(ordered[lower], 2)
    weight = position - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * weight, 2)


def summarize(values: list[float]) -> MetricSummary:
    return MetricSummary(
        count=len(values),
        mean=round(mean(values), 2) if values else None,
        p50=_percentile(values, 0.50),
        p95=_percentile(values, 0.95),
    )


def _expected_pairs(example: dict[str, Any]) -> set[tuple[str, int]]:
    pairs: set[tuple[str, int]] = set()
    for document in example.get("expected_documents", []):
        pairs.update((str(document["filename"]), int(page)) for page in document.get("pages", []))
    return pairs


def _retrieved_pairs(chunks: list[RetrievedChunk]) -> list[tuple[str, int]]:
    return [(chunk.filename, chunk.page_number) for chunk in chunks]


def _dcg(relevances: list[int]) -> float:
    return sum((2**relevance - 1) / math.log2(index + 2) for index, relevance in enumerate(relevances))


def retrieval_metrics(example: dict[str, Any], chunks: list[RetrievedChunk]) -> dict[str, float | None]:
    expected = _expected_pairs(example)
    ranked = _retrieved_pairs(chunks)
    if not expected:
        return {"recall_at_1": None, "recall_at_3": None, "recall_at_5": None, "mrr": None, "ndcg_at_5": None}

    def recall(k: int) -> float:
        return float(any(pair in expected for pair in ranked[:k]))

    first_rank = next((index for index, pair in enumerate(ranked, start=1) if pair in expected), None)
    mrr = 1 / first_rank if first_rank else 0.0
    relevance = [int(pair in expected) for pair in ranked[:5]]
    ideal = [1] * min(len(expected), 5)
    ideal_dcg = _dcg(ideal)
    return {
        "recall_at_1": recall(1),
        "recall_at_3": recall(3),
        "recall_at_5": recall(5),
        "mrr": round(mrr, 6),
        "ndcg_at_5": round(_dcg(relevance) / ideal_dcg, 6) if ideal_dcg else 0.0,
    }


def _is_abstention(answer: str) -> bool:
    normalized = " ".join(answer.casefold().split())
    return any(marker in normalized for marker in _ABSTENTION_MARKERS)


def _citation_ids(answer: str) -> list[str]:
    return list(dict.fromkeys(_SOURCE_RE.findall(answer)))


def citation_metrics(example: dict[str, Any], chunks: list[RetrievedChunk], generation: GenerationResult | None) -> dict[str, Any]:
    expected = _expected_pairs(example)
    if generation is None:
        return {"citation_page_accuracy": None, "cited_source_ids": [], "citation_count": 0}
    cited_ids = _citation_ids(generation.answer)
    by_id = {chunk.source_id: (chunk.filename, chunk.page_number) for chunk in chunks}
    cited_pairs = [by_id[source_id] for source_id in cited_ids if source_id in by_id]
    if not cited_ids:
        accuracy = 1.0 if not expected and _is_abstention(generation.answer) else 0.0
    else:
        accuracy = sum(pair in expected for pair in cited_pairs) / len(cited_ids)
    return {
        "citation_page_accuracy": round(accuracy, 6),
        "cited_source_ids": cited_ids,
        "citation_count": len(cited_ids),
        "citation_ids_known": len(cited_pairs) == len(cited_ids),
    }


def _safe_config(settings: Settings) -> dict[str, Any]:
    """Return the active evaluation knobs without database credentials."""
    return {
        "embedding_model": settings.embedding_model,
        "embedding_dimensions": settings.embedding_dimensions,
        "llm_primary_model": settings.llm_primary_model,
        "reranker_model": settings.reranker_model,
        "reranker_device": settings.reranker_device,
        "reranker_max_length": settings.reranker_max_length,
        "retrieval_limit": settings.retrieval_limit,
        "rerank_candidate_count": settings.rerank_candidate_count,
        "rrf_k": settings.rrf_k,
        "parent_context_window": settings.parent_context_window,
        "context_token_budget": settings.context_token_budget,
        "context_characters_per_token": settings.context_characters_per_token,
        "output_token_budget": settings.output_token_budget,
        "generation_temperature": settings.generation_temperature,
        "generation_think": settings.generation_think,
        "citation_validation_retries": settings.citation_validation_retries,
    }


def _error_categories(
    example: dict[str, Any],
    chunks: list[RetrievedChunk],
    retrieval: RetrievalResult,
    generation: GenerationResult | None,
    generation_error: str | None,
) -> list[str]:
    categories: list[str] = []
    expected = _expected_pairs(example)
    ranked = _retrieved_pairs(chunks)
    if expected:
        first_rank = next((index for index, pair in enumerate(ranked, start=1) if pair in expected), None)
        if first_rank is None:
            categories.append("document_never_retrieved")
        elif first_rank > 5:
            categories.append("document_retrieved_ranked_low")
    # The public RetrievalResult does not expose the pre-rerank candidate list,
    # so a reranker-specific failure cannot be claimed without extra tracing.
    if generation_error:
        categories.append("generation_failure")
    elif generation is not None and not generation.citation_valid:
        categories.extend(("generation_failure", "citation_mismatch"))
    # A citation-validation failure is a generation failure, not evidence that
    # the answer correctly or incorrectly refused the question.
    if generation is not None and generation.citation_valid:
        expected_answer = bool(example["answer_should_exist"])
        refusal = _is_abstention(generation.answer)
        if not expected_answer and refusal:
            categories.append("correct_refusal")
        elif not expected_answer and not refusal:
            categories.append("incorrect_refusal")
        elif expected_answer and refusal:
            categories.append("incorrect_refusal")
    return categories


def _chunk_payload(chunk: RetrievedChunk) -> dict[str, Any]:
    return {
        "source_id": chunk.source_id,
        "document_id": str(chunk.document_id),
        "chunk_id": str(chunk.chunk_id),
        "filename": chunk.filename,
        "document_title": chunk.document_title,
        "page_number": chunk.page_number,
        "chunk_index": chunk.chunk_index,
        "section_title": chunk.section_title,
        "clause_number": chunk.clause_number,
        "lexical_rank": chunk.lexical_rank,
        "dense_rank": chunk.dense_rank,
        "fused_score": chunk.fused_score,
        "rerank_score": chunk.rerank_score,
        "chunk_text": chunk.chunk_text,
        "context_text": chunk.context_text,
    }


def _run_one(settings: Settings, example: dict[str, Any], generate: bool) -> dict[str, Any]:
    started = perf_counter()
    retrieval: RetrievalResult | None = None
    generation: GenerationResult | None = None
    generation_error: str | None = None
    try:
        retrieval = retrieve(settings, example["question"], example["allowed_role"])
    except Exception as exc:  # noqa: BLE001 - preserve per-question failure evidence
        return {
            "id": example["id"],
            "question": example["question"],
            "question_type": example["question_type"],
            "allowed_role": example["allowed_role"],
            "answer_should_exist": example["answer_should_exist"],
            "expected_documents": example.get("expected_documents", []),
            "expected_pages": example.get("expected_pages", []),
            "retrieval_error": f"{type(exc).__name__}: {exc}",
            "status": "retrieval_failed",
            "total_ms": round((perf_counter() - started) * 1000),
        }

    if generate:
        try:
            generation = generate_grounded_answer(settings, example["question"], retrieval.chunks, settings.llm_primary_model)
        except Exception as exc:  # noqa: BLE001 - preserve per-question failure evidence
            generation_error = f"{type(exc).__name__}: {exc}"

    retrieval_metric = retrieval_metrics(example, retrieval.chunks)
    citation_metric = citation_metrics(example, retrieval.chunks, generation)
    errors = _error_categories(example, retrieval.chunks, retrieval, generation, generation_error)
    if generation is not None and generation.citation_valid and citation_metric.get("citation_page_accuracy") != 1.0:
        errors.append("citation_mismatch")
    truncated = any(len(chunk.context_text) >= settings.context_token_budget * settings.context_characters_per_token for chunk in retrieval.chunks)
    if truncated:
        errors.append("context_truncation_possible")
    answer = generation.answer if generation else None
    return {
        "id": example["id"],
        "question": example["question"],
        "question_type": example["question_type"],
        "allowed_role": example["allowed_role"],
        "answer_should_exist": example["answer_should_exist"],
        "expected_documents": example.get("expected_documents", []),
        "expected_pages": example.get("expected_pages", []),
        "expected_supporting_fact": example.get("expected_supporting_fact"),
        "status": "completed" if generation_error is None else "generation_failed",
        "retrieved_chunks": [_chunk_payload(chunk) for chunk in retrieval.chunks],
        "candidate_count": retrieval.candidate_count,
        "retrieval_metrics": retrieval_metric,
        "citation_metrics": citation_metric,
        "answer": answer,
        "generation": {
            "generation_ms": generation.generation_ms,
            "citation_validation_ms": generation.citation_validation_ms,
            "citation_valid": generation.citation_valid,
            "citation_error": generation.citation_error,
        }
        if generation
        else None,
        "generation_error": generation_error,
        "timings": {
            "embed_ms": retrieval.timings.embed_ms,
            "lexical_retrieval_ms": retrieval.timings.lexical_retrieval_ms,
            "dense_retrieval_ms": retrieval.timings.dense_retrieval_ms,
            "rerank_ms": retrieval.timings.rerank_ms,
            "context_assembly_ms": retrieval.timings.context_assembly_ms,
            "generation_ms": generation.generation_ms if generation else None,
            "citation_validation_ms": generation.citation_validation_ms if generation else None,
            "total_ms": round((perf_counter() - started) * 1000),
        },
        "error_categories": list(dict.fromkeys(errors)),
    }


def _aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    def metric(name: str) -> dict[str, Any]:
        values = [float(item["retrieval_metrics"][name]) for item in results if item.get("retrieval_metrics", {}).get(name) is not None]
        summary = summarize(values)
        return {"count": summary.count, "mean": summary.mean, "p50": summary.p50, "p95": summary.p95}

    timing_names = ("embed_ms", "lexical_retrieval_ms", "dense_retrieval_ms", "rerank_ms", "context_assembly_ms", "generation_ms", "citation_validation_ms", "total_ms")
    timings: dict[str, Any] = {}
    for name in timing_names:
        values = [float(item["timings"][name]) for item in results if item.get("timings", {}).get(name) is not None]
        summary = summarize(values)
        timings[name] = {"count": summary.count, "mean": summary.mean, "p50": summary.p50, "p95": summary.p95}

    errors: dict[str, int] = {}
    for item in results:
        for category in item.get("error_categories", []):
            errors[category] = errors.get(category, 0) + 1
    negative = [item for item in results if not item["answer_should_exist"]]
    correct_refusals = sum("correct_refusal" in item.get("error_categories", []) for item in negative)
    return {
        "retrieval": {
            "recall_at_1": metric("recall_at_1"),
            "recall_at_3": metric("recall_at_3"),
            "recall_at_5": metric("recall_at_5"),
            "mrr": metric("mrr"),
            "ndcg_at_5": metric("ndcg_at_5"),
        },
        "citation_page_accuracy": {
            "count": sum(item.get("citation_metrics", {}).get("citation_page_accuracy") is not None for item in results),
            "mean": round(mean([item["citation_metrics"]["citation_page_accuracy"] for item in results if item.get("citation_metrics", {}).get("citation_page_accuracy") is not None]), 6)
            if any(item.get("citation_metrics", {}).get("citation_page_accuracy") is not None for item in results)
            else None,
        },
        "no_answer_accuracy": {
            "status": "measured_from_conservative_abstention_markers",
            "count": len(negative),
            "correct": correct_refusals,
            "accuracy": round(correct_refusals / len(negative), 6) if negative else None,
        },
        "answer_faithfulness": {"status": "not_automatically_scored", "reason": "Requires independent human or approved judge review; no score is fabricated."},
        "answer_relevance": {"status": "not_automatically_scored", "reason": "Requires independent human or approved judge review; no score is fabricated."},
        "unsupported_factual_claim_rate": {"status": "not_automatically_scored", "reason": "Requires claim-level adjudication against source text; citation presence is not proof of support."},
        "latency_ms": timings,
        "error_breakdown": errors,
    }


def _write_csv(path: Path, results: list[dict[str, Any]]) -> None:
    fields = ["id", "question_type", "status", "answer_should_exist", "candidate_count", "recall_at_1", "recall_at_3", "recall_at_5", "mrr", "ndcg_at_5", "citation_page_accuracy", "citation_valid", "generation_error", "total_ms", "error_categories"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in results:
            retrieval_metric = item.get("retrieval_metrics", {})
            citation_metric = item.get("citation_metrics", {})
            generation = item.get("generation") or {}
            writer.writerow(
                {
                    "id": item["id"],
                    "question_type": item["question_type"],
                    "status": item["status"],
                    "answer_should_exist": item["answer_should_exist"],
                    "candidate_count": item.get("candidate_count"),
                    **{name: retrieval_metric.get(name) for name in ("recall_at_1", "recall_at_3", "recall_at_5", "mrr", "ndcg_at_5")},
                    "citation_page_accuracy": citation_metric.get("citation_page_accuracy"),
                    "citation_valid": generation.get("citation_valid"),
                    "generation_error": item.get("generation_error"),
                    "total_ms": item.get("timings", {}).get("total_ms"),
                    "error_categories": ";".join(item.get("error_categories", [])),
                }
            )


def run_gold_evaluation(settings: Settings, gold_path: Path, output_base: Path, generate: bool = True) -> tuple[Path, Path, dict[str, Any]]:
    """Run the current pipeline and write JSON/CSV evidence artifacts."""
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    examples = gold["examples"]
    results = [_run_one(settings, example, generate) for example in examples]
    payload: dict[str, Any] = {
        "schema_version": "rag_baseline_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "gold_set": str(gold_path),
        "pipeline_parameters_changed": False,
        "generation_enabled": generate,
        "active_configuration": _safe_config(settings),
        "question_count": len(results),
        "completed_count": sum(item["status"] == "completed" for item in results),
        "retrieval_failed_count": sum(item["status"] == "retrieval_failed" for item in results),
        "generation_failed_count": sum(item["status"] == "generation_failed" for item in results),
        "aggregate": _aggregate(results),
        "questions": results,
        "measurement_notes": [
            "Recall and NDCG use expected filename+page pairs from the reviewed golden set.",
            "The current public retrieval result does not expose pre-rerank candidates; reranker-specific failures are therefore marked unobservable rather than inferred.",
            "Faithfulness, relevance, and unsupported-claim rate require independent claim-level adjudication and are intentionally not fabricated.",
            "The context-truncation flag is a conservative budget-boundary proxy because the current retrieval API does not return a truncation bit.",
        ],
    }
    output_base.parent.mkdir(parents=True, exist_ok=True)
    json_path = output_base.with_suffix(".json")
    csv_path = output_base.with_suffix(".csv")
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default) + "\n", encoding="utf-8")
    _write_csv(csv_path, results)
    return json_path, csv_path, payload
