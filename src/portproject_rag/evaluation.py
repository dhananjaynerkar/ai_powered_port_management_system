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
from typing import Any, Mapping

from .generation import CLARIFICATION_ANSWER, GenerationResult, generate_grounded_answer
from .guardrails import is_safe_no_evidence_response, referenced_source_ids
from .query_analysis import classify_source_domain, needs_property_clarification
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
    """Measure any evidence hit and complete evidence coverage separately."""
    expected = _expected_pairs(example)
    ranked = _retrieved_pairs(chunks)
    if not expected:
        return {
            "any_hit_at_1": None, "any_hit_at_3": None, "any_hit_at_5": None,
            "evidence_coverage_at_1": None, "evidence_coverage_at_3": None, "evidence_coverage_at_5": None,
            "recall_at_1": None, "recall_at_3": None, "recall_at_5": None, "mrr": None, "ndcg_at_5": None,
        }

    def recall(k: int) -> float:
        return float(any(pair in expected for pair in ranked[:k]))

    first_rank = next((index for index, pair in enumerate(ranked, start=1) if pair in expected), None)
    mrr = 1 / first_rank if first_rank else 0.0
    relevance = [int(pair in expected) for pair in ranked[:5]]
    ideal = [1] * min(len(expected), 5)
    ideal_dcg = _dcg(ideal)
    def coverage(k: int) -> float:
        return len(set(ranked[:k]) & expected) / len(expected)

    any_hit = {1: recall(1), 3: recall(3), 5: recall(5)}
    return {
        "any_hit_at_1": any_hit[1], "any_hit_at_3": any_hit[3], "any_hit_at_5": any_hit[5],
        "evidence_coverage_at_1": coverage(1), "evidence_coverage_at_3": coverage(3), "evidence_coverage_at_5": coverage(5),
        # Backward-compatible aliases for the Phase 07 baseline artifacts.
        "recall_at_1": any_hit[1], "recall_at_3": any_hit[3], "recall_at_5": any_hit[5],
        "mrr": round(mrr, 6),
        "ndcg_at_5": round(_dcg(relevance) / ideal_dcg, 6) if ideal_dcg else 0.0,
    }


def _is_abstention(answer: str) -> bool:
    if is_safe_no_evidence_response(answer):
        return True
    normalized = " ".join(answer.casefold().split())
    return any(marker in normalized for marker in _ABSTENTION_MARKERS)


def _citation_ids(answer: str) -> list[str]:
    # The shared parser handles the model's safe [S1, S2] spelling as well as
    # the public canonical [S1][S2] spelling.
    return sorted(referenced_source_ids(answer))


def _final_context_has_required_evidence(example: dict[str, Any], chunks: list[RetrievedChunk]) -> bool | None:
    required = {(str(item["filename"]), int(item["page"])) for item in example.get("required_evidence_items", [])}
    if not required:
        return None
    return required.issubset(set(_retrieved_pairs(chunks)))


def load_fact_evidence_contract(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Load reviewed fact-to-evidence mappings used only by evaluation.

    Production retrieval receives only the user question and ACL-filtered corpus
    candidates. A fact is supported when one reviewed evidence set is fully
    present in final context.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "rag_fact_evidence_v1":
        raise ValueError("Unsupported fact-evidence contract")
    records: dict[str, list[dict[str, Any]]] = {}
    for record in payload.get("records", []):
        record_id = str(record["id"])
        facts = list(record.get("facts", []))
        for fact in facts:
            if not fact.get("fact_id") or not fact.get("acceptable_evidence_sets"):
                raise ValueError(f"Invalid fact-evidence metadata for {record_id}")
        records[record_id] = facts
    return records


def fact_coverage_metrics(
    example: dict[str, Any], chunks: list[RetrievedChunk], fact_requirements: Mapping[str, list[dict[str, Any]]] | None,
) -> dict[str, Any]:
    """Measure reviewed fact coverage without replacing page-level metrics."""
    facts = list((fact_requirements or {}).get(str(example.get("id")), []))
    if not facts:
        return {"status": "NOT_MAPPED", "required_fact_count": 0, "supported_fact_count": 0, "fact_coverage": None, "complete_fact_evidence": None, "facts": []}
    retrieved = set(_retrieved_pairs(chunks))
    details: list[dict[str, Any]] = []
    for fact in facts:
        evidence_sets = [
            {(str(item["filename"]), int(item["page"])) for item in evidence_set}
            for evidence_set in fact["acceptable_evidence_sets"]
        ]
        supported = any(evidence_set.issubset(retrieved) for evidence_set in evidence_sets)
        details.append({
            "fact_id": fact["fact_id"], "description": fact.get("description"), "supported": supported,
            "acceptable_evidence_sets": fact["acceptable_evidence_sets"],
        })
    supported_count = sum(item["supported"] for item in details)
    return {
        "status": "MEASURED", "required_fact_count": len(details), "supported_fact_count": supported_count,
        "fact_coverage": round(supported_count / len(details), 6),
        "complete_fact_evidence": supported_count == len(details), "facts": details,
    }


def _objective_fact_check(example: dict[str, Any], answer: str | None) -> dict[str, Any]:
    """Report only repeatable numeric-token coverage; do not claim semantic correctness.

    The reviewed contract remains the authority for factual/complete/citation
    support review.  This lightweight check merely makes accidental omission
    of a required number visible without embedding any question-specific rule.
    """
    expected_numbers = sorted(set(re.findall(r"\b\d+(?:\.\d+)?\b", " ".join(example.get("must_include_facts", [])))))
    answer_numbers = sorted(set(re.findall(r"\b\d+(?:\.\d+)?\b", answer or "")))
    return {
        "method": "numeric_token_presence_only",
        "expected_numeric_tokens": expected_numbers,
        "answer_numeric_tokens": answer_numbers,
        "all_expected_numbers_present": set(expected_numbers).issubset(answer_numbers) if expected_numbers else None,
    }


def citation_metrics(example: dict[str, Any], chunks: list[RetrievedChunk], generation: GenerationResult | None) -> dict[str, Any]:
    expected = _expected_pairs(example)
    if generation is None:
        return {"citation_source_accuracy": None, "citation_page_accuracy": None, "cited_source_ids": [], "citation_count": 0}
    cited_ids = _citation_ids(generation.answer)
    by_id = {chunk.source_id: (chunk.filename, chunk.page_number) for chunk in chunks}
    cited_pairs = [by_id[source_id] for source_id in cited_ids if source_id in by_id]
    expected_filenames = {filename for filename, _page in expected}
    if not cited_ids:
        accuracy = 1.0 if not expected and _is_abstention(generation.answer) else 0.0
        source_accuracy = accuracy
    else:
        accuracy = sum(pair in expected for pair in cited_pairs) / len(cited_ids)
        source_accuracy = sum(filename in expected_filenames for filename, _page in cited_pairs) / len(cited_ids)
    return {
        "citation_source_accuracy": round(source_accuracy, 6),
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
        "reranker_local_files_only": settings.reranker_local_files_only,
        "reranker_max_length": settings.reranker_max_length,
        "retrieval_limit": settings.retrieval_limit,
        "rerank_candidate_count": settings.rerank_candidate_count,
        "candidate_pool_size": settings.candidate_pool_size,
        "final_context_source_count": settings.final_context_source_count,
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
    if generation_error:
        categories.append("generation_failure")
    elif generation is not None and (not generation.citation_valid or generation.disposition == "CITATION_FAILURE"):
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


def _application_precondition_result(
    example: dict[str, Any], started: float, disposition: str, fact_requirements: Mapping[str, list[dict[str, Any]]] | None,
) -> dict[str, Any]:
    """Represent a pre-retrieval result that the real API returns before RAG.

    This prevents the evaluation harness from treating a live-data request or
    an identifier-missing rate request as a document-generation failure.
    """
    answer = CLARIFICATION_ANSWER if disposition == "CLARIFICATION_REQUIRED" else None
    retrieval_metric = retrieval_metrics(example, [])
    return {
        "id": example["id"], "question": example["question"], "question_type": example["question_type"],
        "expected_answer_shape": example.get("expected_answer_shape"),
        "allowed_role": example["allowed_role"], "answer_should_exist": example["answer_should_exist"],
        "expected_documents": example.get("expected_documents", []), "expected_pages": example.get("expected_pages", []),
        "expected_supporting_fact": example.get("expected_supporting_fact"), "status": "application_precondition",
        "application_precondition": disposition, "transport_success": True, "retrieval_success": None,
        "generation_call_success": None, "answer_valid": True, "citation_valid": True, "answer_correct": None,
        "correct_refusal": disposition == "CLARIFICATION_REQUIRED", "retrieved_chunks": [], "candidate_count": 0,
        "retrieval_metrics": retrieval_metric, "candidate_metrics": retrieval_metric,
        "citation_metrics": {"citation_source_accuracy": None, "citation_page_accuracy": None, "cited_source_ids": [], "citation_count": 0},
        "answer": answer, "generation": None, "generation_error": None,
        "objective_fact_check": _objective_fact_check(example, answer),
        "fact_evidence": fact_coverage_metrics(example, [], fact_requirements),
        "final_context_has_required_evidence": None,
        "timings": {name: 0 for name in ("query_analysis_ms", "embed_ms", "lexical_retrieval_ms", "dense_retrieval_ms", "candidate_fusion_ms", "adjacent_candidates_ms", "rerank_ms", "reranker_load_ms", "reranker_pair_build_ms", "reranker_predict_ms", "reranker_postprocess_ms", "context_selection_ms", "context_assembly_ms", "prompt_build_ms", "generation_ms", "citation_validation_ms", "answer_assembly_ms", "model_load_ms", "prompt_eval_ms", "token_generation_ms")} | {"total_ms": round((perf_counter() - started) * 1000)},
        "error_categories": ["application_precondition"],
        "diagnostics": {"query_type": None, "exact_references": [], "reranker_degraded": None, "reranker_reason": None, "candidate_rows": [], "selected_sources": [], "excluded_sources": [], "context_tokens": None, "context_budget_tokens": None, "truncated": None},
    }


def _run_one(
    settings: Settings, example: dict[str, Any], generate: bool,
    fact_requirements: Mapping[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    started = perf_counter()
    retrieval: RetrievalResult | None = None
    generation: GenerationResult | None = None
    generation_error: str | None = None
    if classify_source_domain(example["question"]) != "DOCUMENT_RAG":
        return _application_precondition_result(example, started, "ROUTED", fact_requirements)
    if needs_property_clarification(example["question"]):
        return _application_precondition_result(example, started, "CLARIFICATION_REQUIRED", fact_requirements)
    try:
        retrieval = retrieve(settings, example["question"], example["allowed_role"])
    except Exception as exc:  # noqa: BLE001 - preserve per-question failure evidence
        return {
            "id": example["id"],
            "question": example["question"],
            "question_type": example["question_type"],
            "expected_answer_shape": example.get("expected_answer_shape"),
            "allowed_role": example["allowed_role"],
            "answer_should_exist": example["answer_should_exist"],
            "expected_documents": example.get("expected_documents", []),
            "expected_pages": example.get("expected_pages", []),
            "retrieval_error": f"{type(exc).__name__}: {exc}",
            "transport_success": False,
            "retrieval_success": False,
            "generation_call_success": None,
            "answer_valid": False,
            "citation_valid": False,
            "answer_correct": None,
            "correct_refusal": False,
            "status": "retrieval_failed",
            "total_ms": round((perf_counter() - started) * 1000),
        }

    if generate:
        try:
            generation = generate_grounded_answer(settings, example["question"], retrieval.chunks, settings.llm_primary_model)
        except Exception as exc:  # noqa: BLE001 - preserve per-question failure evidence
            generation_error = f"{type(exc).__name__}: {exc}"

    candidate_chunks = retrieval.chunks
    if retrieval.diagnostics:
        candidate_chunks = [
            RetrievedChunk(
                source_id=f"C{index}", document_id=row["document_id"], chunk_id=row["chunk_id"],
                document_title=row["document_title"], filename=row["filename"], page_number=row["page_number"], chunk_index=row["chunk_index"],
                chunk_text="", context_text="", section_title=row.get("section_title"), clause_number=row.get("clause_number"),
                lexical_rank=row.get("lexical_rank"), dense_rank=row.get("dense_rank"), fused_score=float(row["fused_score"]), rerank_score=float(row.get("rerank_score", row["fused_score"])),
            )
            for index, row in enumerate(retrieval.diagnostics.candidate_rows, start=1)
        ]
    retrieval_metric = retrieval_metrics(example, retrieval.chunks)
    candidate_metric = retrieval_metrics(example, candidate_chunks)
    fact_evidence = fact_coverage_metrics(example, retrieval.chunks, fact_requirements)
    citation_metric = citation_metrics(example, retrieval.chunks, generation)
    errors = _error_categories(example, retrieval.chunks, retrieval, generation, generation_error)
    if generation is not None and generation.citation_valid and citation_metric.get("citation_page_accuracy") != 1.0:
        errors.append("citation_mismatch")
    truncated = bool(retrieval.diagnostics and retrieval.diagnostics.context_truncated)
    if truncated:
        errors.append("context_truncation_possible")
    answer = generation.answer if generation else None
    return {
        "id": example["id"],
        "question": example["question"],
        "question_type": example["question_type"],
        "expected_answer_shape": example.get("expected_answer_shape"),
        "allowed_role": example["allowed_role"],
        "answer_should_exist": example["answer_should_exist"],
        "expected_documents": example.get("expected_documents", []),
        "expected_pages": example.get("expected_pages", []),
        "expected_supporting_fact": example.get("expected_supporting_fact"),
        "status": "completed" if generation_error is None else "generation_failed",
        "transport_success": True,
        "retrieval_success": bool(retrieval.chunks) or not example["answer_should_exist"],
        "generation_call_success": None if not generate else generation_error is None,
        "answer_valid": bool(generation and generation.citation_valid) if generate else None,
        "citation_valid": bool(generation and generation.citation_valid) if generate else None,
        "answer_correct": None,
        "correct_refusal": "correct_refusal" in errors,
        "retrieved_chunks": [_chunk_payload(chunk) for chunk in retrieval.chunks],
        "candidate_count": retrieval.candidate_count,
        "retrieval_metrics": retrieval_metric,
        "candidate_metrics": candidate_metric,
        "citation_metrics": citation_metric,
        "answer": answer,
        "generation": {
            "generation_ms": generation.generation_ms,
            "citation_validation_ms": generation.citation_validation_ms,
            "citation_valid": generation.citation_valid,
            "citation_error": generation.citation_error,
            "first_pass_citation_valid": generation.first_pass_citation_valid,
            "citation_repair_used": generation.citation_repair_used,
            "citation_repair_succeeded": generation.citation_repair_succeeded,
            "disposition": generation.disposition,
            "raw_answer": generation.raw_answer,
            "prompt": generation.prompt,
            "prompt_eval_count": generation.prompt_eval_count,
            "eval_count": generation.eval_count,
            "stop_reason": generation.stop_reason,
        }
        if generation
        else None,
        "generation_error": generation_error,
        "objective_fact_check": _objective_fact_check(example, answer),
        "fact_evidence": fact_evidence,
        "final_context_has_required_evidence": _final_context_has_required_evidence(example, retrieval.chunks),
        "timings": {
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
            "prompt_build_ms": generation.prompt_build_ms if generation else None,
            "generation_ms": generation.generation_ms if generation else None,
            "citation_validation_ms": generation.citation_validation_ms if generation else None,
            "answer_assembly_ms": generation.answer_assembly_ms if generation else None,
            "model_load_ms": generation.model_load_ms if generation else None,
            "prompt_eval_ms": generation.prompt_eval_ms if generation else None,
            "token_generation_ms": generation.token_generation_ms if generation else None,
            "total_ms": round((perf_counter() - started) * 1000),
        },
        "error_categories": list(dict.fromkeys(errors)),
        "diagnostics": {
            "query_type": retrieval.diagnostics.query.answer_shape if retrieval.diagnostics else None,
            "exact_references": list(retrieval.diagnostics.query.exact_references) if retrieval.diagnostics else [],
            "reranker_degraded": retrieval.diagnostics.reranker_degraded if retrieval.diagnostics else None,
            "reranker_reason": retrieval.diagnostics.reranker_reason if retrieval.diagnostics else None,
            "candidate_rows": retrieval.diagnostics.candidate_rows if retrieval.diagnostics else [],
            "selected_sources": retrieval.diagnostics.selected_rows if retrieval.diagnostics else [],
            "excluded_sources": retrieval.diagnostics.excluded_rows if retrieval.diagnostics else [],
            "context_tokens": retrieval.diagnostics.context_tokens if retrieval.diagnostics else None,
            "context_budget_tokens": retrieval.diagnostics.context_budget_tokens if retrieval.diagnostics else None,
            "truncated": retrieval.diagnostics.context_truncated if retrieval.diagnostics else None,
        },
    }


def _aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    def metric(name: str) -> dict[str, Any]:
        values = [float(item["retrieval_metrics"][name]) for item in results if item.get("retrieval_metrics", {}).get(name) is not None]
        summary = summarize(values)
        return {"count": summary.count, "mean": summary.mean, "p50": summary.p50, "p95": summary.p95}

    timing_names = ("query_analysis_ms", "embed_ms", "lexical_retrieval_ms", "dense_retrieval_ms", "candidate_fusion_ms", "adjacent_candidates_ms", "rerank_ms", "reranker_load_ms", "reranker_pair_build_ms", "reranker_predict_ms", "reranker_postprocess_ms", "context_selection_ms", "context_assembly_ms", "prompt_build_ms", "generation_ms", "citation_validation_ms", "answer_assembly_ms", "model_load_ms", "prompt_eval_ms", "token_generation_ms", "total_ms")
    timings: dict[str, Any] = {}
    for name in timing_names:
        values = [float(item["timings"][name]) for item in results if item.get("timings", {}).get(name) is not None]
        summary = summarize(values)
        timings[name] = {"count": summary.count, "mean": summary.mean, "p50": summary.p50, "p95": summary.p95}

    errors: dict[str, int] = {}
    for item in results:
        for category in item.get("error_categories", []):
            errors[category] = errors.get(category, 0) + 1
    no_evidence_cases = [item for item in results if item.get("expected_answer_shape") == "no_evidence" and item.get("application_precondition") != "ROUTED"]
    correct_refusals = sum((item.get("generation") or {}).get("disposition") == "NO_EVIDENCE" for item in no_evidence_cases)
    clarification_cases = [item for item in results if item.get("expected_answer_shape") == "clarification"]
    correct_clarifications = sum(item.get("application_precondition") == "CLARIFICATION_REQUIRED" for item in clarification_cases)
    generated = [item.get("generation") for item in results if item.get("generation")]
    fact_measured = [item["fact_evidence"] for item in results if item.get("fact_evidence", {}).get("status") == "MEASURED"]
    required_facts = sum(int(item["required_fact_count"]) for item in fact_measured)
    supported_facts = sum(int(item["supported_fact_count"]) for item in fact_measured)
    return {
        "retrieval": {
            "any_hit_at_1": metric("any_hit_at_1"),
            "any_hit_at_3": metric("any_hit_at_3"),
            "any_hit_at_5": metric("any_hit_at_5"),
            "evidence_coverage_at_1": metric("evidence_coverage_at_1"),
            "evidence_coverage_at_3": metric("evidence_coverage_at_3"),
            "evidence_coverage_at_5": metric("evidence_coverage_at_5"),
            "recall_at_1": metric("recall_at_1"), "recall_at_3": metric("recall_at_3"), "recall_at_5": metric("recall_at_5"),
            "mrr": metric("mrr"),
            "ndcg_at_5": metric("ndcg_at_5"),
        },
        "citation_page_accuracy": {
            "count": sum(item.get("citation_metrics", {}).get("citation_page_accuracy") is not None for item in results),
            "mean": round(mean([item["citation_metrics"]["citation_page_accuracy"] for item in results if item.get("citation_metrics", {}).get("citation_page_accuracy") is not None]), 6)
            if any(item.get("citation_metrics", {}).get("citation_page_accuracy") is not None for item in results)
            else None,
        },
        "citation_source_accuracy": {
            "count": sum(item.get("citation_metrics", {}).get("citation_source_accuracy") is not None for item in results),
            "mean": round(mean([item["citation_metrics"]["citation_source_accuracy"] for item in results if item.get("citation_metrics", {}).get("citation_source_accuracy") is not None]), 6)
            if any(item.get("citation_metrics", {}).get("citation_source_accuracy") is not None for item in results)
            else None,
        },
        "no_answer_accuracy": {
            "status": "measured_from_deterministic_no_evidence_disposition",
            "count": len(no_evidence_cases),
            "correct": correct_refusals,
            "accuracy": round(correct_refusals / len(no_evidence_cases), 6) if no_evidence_cases else None,
        },
        "clarification_accuracy": {
            "count": len(clarification_cases),
            "correct": correct_clarifications,
            "accuracy": round(correct_clarifications / len(clarification_cases), 6) if clarification_cases else None,
        },
        "fact_evidence": {
            "scope": "reviewed fact-evidence mappings only",
            "question_count": len(fact_measured),
            "required_fact_count": required_facts,
            "supported_fact_count": supported_facts,
            "fact_coverage": round(supported_facts / required_facts, 6) if required_facts else None,
            "complete_fact_evidence_rate": round(
                sum(item["complete_fact_evidence"] is True for item in fact_measured) / len(fact_measured), 6
            ) if fact_measured else None,
        },
        "answer_faithfulness": {"status": "not_automatically_scored", "reason": "Requires independent human or approved judge review; no score is fabricated."},
        "answer_relevance": {"status": "not_automatically_scored", "reason": "Requires independent human or approved judge review; no score is fabricated."},
        "unsupported_factual_claim_rate": {"status": "not_automatically_scored", "reason": "Requires claim-level adjudication against source text; citation presence is not proof of support."},
        "latency_ms": timings,
        "error_breakdown": errors,
        "execution": {
            "transport_success": sum(item.get("transport_success") is True for item in results),
            "retrieval_success": sum(item.get("retrieval_success") is True for item in results),
            "generation_call_success": sum(item.get("generation_call_success") is True for item in results),
            "answer_valid": sum(item.get("answer_valid") is True for item in results),
            "citation_valid": sum(item.get("citation_valid") is True for item in results),
            "correct_refusal": sum(item.get("correct_refusal") is True for item in results),
            "answer_correct": "not_automatically_scored",
        },
        "generation_telemetry": {
            "generation_requested": sum(item.get("generation_call_success") is not None for item in results),
            "generation_returned": len(generated),
            "generation_timeout": sum("GENERATION_TIMEOUT" in (item.get("generation_error") or "") for item in results),
            "raw_answer_nonempty": sum(bool(item.get("raw_answer")) for item in generated),
            "first_pass_citation_valid": sum(item.get("first_pass_citation_valid") is True for item in generated),
            "citation_repair_attempted": sum(item.get("citation_repair_used") is True for item in generated),
            "citation_repair_success": sum(item.get("citation_repair_succeeded") is True for item in generated),
            "final_citation_valid": sum(item.get("citation_valid") is True for item in generated),
            "dispositions": {
                disposition: sum(item.get("disposition") == disposition for item in generated)
                for disposition in sorted({str(item.get("disposition")) for item in generated})
            },
        },
    }


def _write_csv(path: Path, results: list[dict[str, Any]]) -> None:
    fields = ["id", "question_type", "status", "answer_should_exist", "transport_success", "retrieval_success", "generation_call_success", "answer_valid", "citation_valid", "candidate_count", "any_hit_at_1", "any_hit_at_3", "any_hit_at_5", "evidence_coverage_at_3", "evidence_coverage_at_5", "mrr", "ndcg_at_5", "fact_coverage", "complete_fact_evidence", "citation_source_accuracy", "citation_page_accuracy", "first_pass_citation_valid", "citation_repair_used", "citation_repair_succeeded", "answer_disposition", "stop_reason", "final_context_has_required_evidence", "generation_error", "total_ms", "error_categories"]
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
                    **{name: item.get(name) for name in ("transport_success", "retrieval_success", "generation_call_success", "answer_valid", "citation_valid")},
                    **{name: retrieval_metric.get(name) for name in ("any_hit_at_1", "any_hit_at_3", "any_hit_at_5", "evidence_coverage_at_3", "evidence_coverage_at_5", "mrr", "ndcg_at_5")},
                    "fact_coverage": item.get("fact_evidence", {}).get("fact_coverage"),
                    "complete_fact_evidence": item.get("fact_evidence", {}).get("complete_fact_evidence"),
                    "citation_source_accuracy": citation_metric.get("citation_source_accuracy"),
                    "citation_page_accuracy": citation_metric.get("citation_page_accuracy"),
                    "citation_valid": generation.get("citation_valid"),
                    "first_pass_citation_valid": generation.get("first_pass_citation_valid"),
                    "citation_repair_used": generation.get("citation_repair_used"),
                    "citation_repair_succeeded": generation.get("citation_repair_succeeded"),
                    "answer_disposition": generation.get("disposition"),
                    "stop_reason": generation.get("stop_reason"),
                    "final_context_has_required_evidence": item.get("final_context_has_required_evidence"),
                    "generation_error": item.get("generation_error"),
                    "total_ms": item.get("timings", {}).get("total_ms"),
                    "error_categories": ";".join(item.get("error_categories", [])),
                }
            )


def load_evaluation_contract(path: Path) -> tuple[str, list[dict[str, Any]]]:
    """Load the reviewed v1 gold set or the richer v2 contract without rewriting facts."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema_version = str(payload.get("schema_version", ""))
    if schema_version == "rag_answer_contract_v2":
        examples: list[dict[str, Any]] = []
        for record in payload["records"]:
            examples.append({
                **record,
                "expected_documents": record["acceptable_documents"],
                "expected_supporting_fact": " ".join(record["must_include_facts"]),
            })
        return schema_version, examples
    if schema_version == "rag_gold_v1":
        return schema_version, list(payload["examples"])
    raise ValueError(f"Unsupported evaluation contract: {schema_version or 'missing schema_version'}")


def _write_human_review(path: Path, payload: dict[str, Any]) -> Path:
    """Create a deliberate review queue without fabricating semantic scores."""
    review = {
        "schema_version": "rag_answer_human_review_v1",
        "generated_at": payload["generated_at"],
        "source_evaluation": payload["gold_set"],
        "instructions": "Review factual correctness, completeness, faithfulness, and citation support against the displayed retrieved evidence. Leave a field null until a human reviewer completes it.",
        "records": [
            {
                "id": item["id"], "question": item["question"], "answer_should_exist": item["answer_should_exist"],
                "expected_supporting_fact": item.get("expected_supporting_fact"), "answer": item.get("answer"),
                "required_facts": (item.get("fact_evidence") or {}).get("facts", []),
                "raw_model_output": (item.get("generation") or {}).get("raw_answer"),
                "cited_source_ids": (item.get("citation_metrics") or {}).get("cited_source_ids", []),
                "retrieved_sources": [
                    {key: chunk.get(key) for key in ("source_id", "filename", "page_number", "section_title", "clause_number", "context_text")}
                    for chunk in item.get("retrieved_chunks", [])
                ],
                "factually_correct": None, "complete": None, "faithful": None, "citation_support": None,
                "review_notes": None,
            }
            for item in payload["questions"]
        ],
    }
    path.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def run_gold_evaluation(
    settings: Settings, gold_path: Path, output_base: Path, generate: bool = True, *, deterministic: bool = True
) -> tuple[Path, Path, dict[str, Any]]:
    """Run the current pipeline and write JSON/CSV evidence artifacts.

    Retrieval settings remain untouched. Generation evaluations use temperature
    zero by default so repeated evidence-complete cases are comparable.
    """
    contract_version, examples = load_evaluation_contract(gold_path)
    fact_contract_path = gold_path.with_name("rag_fact_evidence_v1.json")
    fact_requirements = load_fact_evidence_contract(fact_contract_path) if fact_contract_path.exists() else {}
    effective_settings = settings.model_copy(update={"generation_temperature": 0.0}) if generate and deterministic else settings
    results = [_run_one(effective_settings, example, generate, fact_requirements) for example in examples]
    payload: dict[str, Any] = {
        "schema_version": "rag_evaluation_v2",
        "generated_at": datetime.now(UTC).isoformat(),
        "gold_set": str(gold_path),
        "contract_version": contract_version,
        "fact_evidence_contract": str(fact_contract_path) if fact_contract_path.exists() else None,
        "pipeline_parameters_changed": False,
        "generation_enabled": generate,
        "active_configuration": _safe_config(effective_settings),
        "evaluation_overrides": {"generation_temperature": 0.0} if generate and deterministic else {},
        "question_count": len(results),
        "completed_count": sum(item["status"] == "completed" for item in results),
        "retrieval_failed_count": sum(item["status"] == "retrieval_failed" for item in results),
        "generation_failed_count": sum(item.get("generation_call_success") is False or item.get("answer_valid") is False for item in results),
        "aggregate": _aggregate(results),
        "questions": results,
        "measurement_notes": [
            "Any-hit, evidence coverage, MRR, and NDCG use expected filename+page pairs from the reviewed contract.",
            "Candidate-stage metrics are measured before reranking; final-context metrics remain separately available per question.",
            "Fact coverage uses reviewed evaluation-only fact-evidence metadata and does not replace page evidence coverage.",
            "Faithfulness, relevance, and unsupported-claim rate require independent claim-level adjudication and are intentionally not fabricated.",
            "The context-truncation flag is a conservative budget-boundary proxy because the current retrieval API does not return a truncation bit.",
        ],
    }
    output_base.parent.mkdir(parents=True, exist_ok=True)
    json_path = output_base.with_suffix(".json")
    csv_path = output_base.with_suffix(".csv")
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default) + "\n", encoding="utf-8")
    _write_csv(csv_path, results)
    _write_human_review(output_base.parent / "rag_answer_human_review.json", payload)
    return json_path, csv_path, payload


def run_generation_stability(
    settings: Settings, gold_path: Path, output_path: Path, *, repetitions: int = 2
) -> tuple[Path, dict[str, Any]]:
    """Repeat only evidence-complete document cases at deterministic temperature.

    This deliberately reuses the retrieved, ACL-filtered context for each
    repeat. It measures generator stability rather than adding retrieval
    variance or silently changing the reviewed gold questions.
    """
    if repetitions < 2:
        raise ValueError("repetitions must be at least 2")
    contract_version, examples = load_evaluation_contract(gold_path)
    effective_settings = settings.model_copy(update={"generation_temperature": 0.0})
    records: list[dict[str, Any]] = []
    for example in examples:
        if classify_source_domain(example["question"]) != "DOCUMENT_RAG" or needs_property_clarification(example["question"]):
            continue
        retrieval = retrieve(effective_settings, example["question"], example["allowed_role"])
        if not _final_context_has_required_evidence(example, retrieval.chunks):
            continue
        attempts: list[dict[str, Any]] = []
        for run_number in range(1, repetitions + 1):
            generated = generate_grounded_answer(effective_settings, example["question"], retrieval.chunks, effective_settings.llm_primary_model)
            attempts.append({
                "run": run_number, "answer": generated.answer, "raw_answer": generated.raw_answer,
                "citation_valid": generated.citation_valid, "disposition": generated.disposition,
                "citation_ids": _citation_ids(generated.answer), "stop_reason": generated.stop_reason,
                "prompt_eval_count": generated.prompt_eval_count, "eval_count": generated.eval_count,
                "generation_ms": generated.generation_ms, "model_load_ms": generated.model_load_ms,
                "prompt_eval_ms": generated.prompt_eval_ms, "token_generation_ms": generated.token_generation_ms,
            })
        records.append({
            "id": example["id"], "question": example["question"], "answer_shape": example.get("expected_answer_shape"),
            "final_context_complete": True, "source_ids": [chunk.source_id for chunk in retrieval.chunks],
            "attempts": attempts,
            "answers_identical": len({attempt["answer"] for attempt in attempts}) == 1,
            "citation_sets_identical": len({tuple(attempt["citation_ids"]) for attempt in attempts}) == 1,
            "all_final_citation_valid": all(attempt["citation_valid"] for attempt in attempts),
        })
    payload = {
        "schema_version": "rag_generation_stability_v1", "generated_at": datetime.now(UTC).isoformat(),
        "gold_set": str(gold_path), "contract_version": contract_version,
        "evaluation_overrides": {"generation_temperature": 0.0}, "repetitions": repetitions,
        "records": records,
        "summary": {
            "complete_context_questions": len(records),
            "all_answers_identical": sum(record["answers_identical"] for record in records),
            "all_citation_sets_identical": sum(record["citation_sets_identical"] for record in records),
            "all_final_citation_valid": sum(record["all_final_citation_valid"] for record in records),
        },
        "notes": [
            "Only questions whose final retrieved context contained every reviewed required evidence item are repeated.",
            "This is a generator-only stability measurement; retrieval is intentionally performed once per question.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path, payload
