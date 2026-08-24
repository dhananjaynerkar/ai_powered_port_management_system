"""Evidence-driven, deterministic runtime strategy selection.

The selector is deliberately not an LLM: routing based on observable local
capabilities and page signals must be reproducible and inexpensive.
"""
from __future__ import annotations

import importlib.util
from dataclasses import asdict, dataclass
from typing import Iterable

from .capabilities import discover_ocr
from .inspection import PageProfile, PdfProfile


@dataclass(frozen=True, slots=True)
class Capabilities:
    ocr_available: bool
    table_extractor_available: bool
    alternative_parser_available: bool
    ocr_languages: tuple[str, ...] = ()

    @classmethod
    def detect(cls) -> "Capabilities":
        ocr = discover_ocr()
        return cls(
            ocr_available=ocr.available,
            table_extractor_available=importlib.util.find_spec("pdfplumber") is not None or importlib.util.find_spec("camelot") is not None,
            alternative_parser_available=importlib.util.find_spec("pypdf") is not None,
            ocr_languages=ocr.languages,
        )


@dataclass(frozen=True, slots=True)
class Strategy:
    strategy_id: str
    extraction_method: str
    table_method: str
    chunking_method: str
    retrieval_method: str
    expected_quality: int
    expected_cost: int
    confidence: int
    rationale: str


@dataclass(frozen=True, slots=True)
class StrategyDecision:
    document: str
    page_number: int
    observed_classification: str
    evidence: dict[str, object]
    candidates: tuple[Strategy, ...]
    selected: Strategy
    fallback: Strategy | None


def _strategy(identifier: str, extraction: str, table: str, chunking: str, quality: int, cost: int, confidence: int, rationale: str) -> Strategy:
    return Strategy(identifier, extraction, table, chunking, "ADAPTIVE_QUERY_PLAN", quality, cost, confidence, rationale)


def generate_page_strategies(page: PageProfile, capabilities: Capabilities) -> list[Strategy]:
    """Generate viable alternatives; no category is bound to one engine."""
    native = _strategy("native_page", "PYMUPDF_NATIVE", "NONE", "PAGE_PARAGRAPH", 85, 10, 90, "Printable native text is present.")
    quarantine = _strategy("quarantine", "NONE", "NONE", "NONE", 100, 1, 100, "No validated local extractor can produce reliable text.")
    candidates: list[Strategy] = []
    if page.classification == "NATIVE_TEXT_USABLE":
        candidates.append(native)
        if capabilities.alternative_parser_available:
            candidates.append(_strategy("alternate_parser_verify", "PYPDF_VERIFY", "NONE", "PAGE_PARAGRAPH", 75, 20, 65, "Independent parser is available for quality retry."))
    elif page.classification == "NATIVE_TEXT_POOR":
        if capabilities.alternative_parser_available:
            candidates.append(_strategy("alternate_parser_retry", "PYPDF", "NONE", "PAGE_PARAGRAPH", 65, 25, 60, "Native quality is poor; a low-cost parser retry is available."))
        if capabilities.ocr_available:
            candidates.append(_strategy("ocr_retry", "TESSERACT", "NONE", "PAGE_PARAGRAPH", 70, 70, 60, "OCR is available as a fallback after poor native extraction."))
        candidates.append(quarantine)
    elif page.classification in {"IMAGE_ONLY", "UNKNOWN"}:
        if capabilities.ocr_available:
            candidates.append(_strategy("ocr_page", "TESSERACT", "NONE", "PAGE_PARAGRAPH", 70, 70, 75, "Image-backed page can be OCRed locally."))
        candidates.append(quarantine)
    elif page.classification in {"TABLE_HEAVY", "MIXED"}:
        candidates.append(_strategy("native_preserve_layout", "PYMUPDF_NATIVE", "RAW_PAGE_CONTEXT", "PAGE_PARAGRAPH", 75, 15, 75, "Native text is retained while table/layout evidence is preserved."))
        if capabilities.table_extractor_available:
            candidates.append(_strategy("table_structured", "PYMUPDF_NATIVE", "STRUCTURED_TABLE", "TABLE_ROW_AND_CONTEXT", 88, 45, 75, "A table extractor is locally available."))
        if page.classification == "MIXED" and capabilities.ocr_available:
            candidates.append(_strategy("mixed_native_ocr", "PYMUPDF_PLUS_TESSERACT", "RAW_PAGE_CONTEXT", "PAGE_PARAGRAPH", 82, 65, 70, "Image and native regions can be processed separately."))
        candidates.append(quarantine)
    else:
        candidates.append(quarantine)
    return candidates


def select_strategy(candidates: Iterable[Strategy]) -> tuple[Strategy, Strategy | None]:
    """Choose maximum expected utility; quarantine wins only when no extractor is viable."""
    options = list(candidates)
    viable = [item for item in options if item.strategy_id != "quarantine"]
    ordered = sorted(viable or options, key=lambda item: (item.expected_quality * item.confidence - item.expected_cost * 10, item.confidence), reverse=True)
    quarantines = [item for item in options if item.strategy_id == "quarantine"]
    if viable and quarantines:
        ordered.extend(quarantines)
    return ordered[0], ordered[1] if len(ordered) > 1 else None


def decide_document(profile: PdfProfile, capabilities: Capabilities) -> list[StrategyDecision]:
    decisions = []
    for item in profile.page_profiles:
        page = item if isinstance(item, PageProfile) else PageProfile(**item)
        candidates = tuple(generate_page_strategies(page, capabilities))
        selected, fallback = select_strategy(candidates)
        decisions.append(StrategyDecision(
            document=profile.filename, page_number=page.page_number, observed_classification=page.classification,
            evidence={"quality_score": page.extraction_quality_score, "image_count": page.image_count, "table_signal": page.table_signal, "quality_band": page.quality_band, "capabilities": asdict(capabilities)},
            candidates=candidates, selected=selected, fallback=fallback,
        ))
    return decisions


def plan_query(question: str, graph_state: str = "GRAPH_NOT_NEEDED") -> dict[str, object]:
    """Generate a minimal query plan from observable query features."""
    text = question.lower()
    page_constrained = "page" in text and any(character.isdigit() for character in text)
    relationship = any(term in text for term in ("related", "reference", "cites", "between"))
    exact = '"' in question or any(term in text for term in ("section", "clause", "document mentions"))
    plans = ["DENSE"]
    if exact:
        plans.append("LEXICAL")
    if not exact and not relationship:
        plans.append("LEXICAL")
    if page_constrained:
        plans.append("PAGE_METADATA_FILTER")
    if relationship and graph_state in {"GRAPH_USEFUL_FOR_RETRIEVAL", "GRAPH_USEFUL_FOR_MULTI_HOP", "GRAPH_RAG_JUSTIFIED"}:
        plans.append("GRAPH_TRAVERSAL")
    return {"plans_considered": plans, "selected": "HYBRID_RRF" if {"DENSE", "LEXICAL"}.issubset(plans) else plans[0], "fallback": "HYBRID_RRF" if plans[0] != "HYBRID_RRF" else "LEXICAL", "rationale": "Query features selected only the retrieval operations with evidence of value."}
