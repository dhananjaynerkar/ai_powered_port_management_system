"""General, non-destructive query analysis for document retrieval and routing."""
from __future__ import annotations

import re
from dataclasses import dataclass

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9-]{2,}|\b\d{1,4}\b")
_SPACE_RE = re.compile(r"\s+")
_STOPWORDS = {
    "about", "after", "against", "answer", "and", "are", "been", "before", "can", "could", "does", "for", "from",
    "give", "have", "how", "into", "is", "may", "more", "of", "on", "or", "please", "regarding", "show", "that",
    "the", "their", "there", "these", "this", "under", "what", "when", "where", "which", "who", "with", "would",
}
_REFERENCE_PATTERNS = (
    re.compile(r"\b(?:section|sec\.?)[\s:.-]*(?:no\.?\s*)?([A-Za-z]?\d+[A-Za-z-]*)\b", re.IGNORECASE),
    re.compile(r"\b(?:by[-\s]?law|bye[-\s]?law)[\s:.-]*(?:no\.?\s*)?([A-Za-z]?\d+[A-Za-z-]*)\b", re.IGNORECASE),
    re.compile(r"\b(?:appendix|annexure)\s+([A-Za-z0-9-]+)\b", re.IGNORECASE),
    re.compile(r"\b(?:clarification|tender|tr|rr|pglm)\s*(?:no\.?\s*)?([A-Za-z0-9/-]+)?(?:\s+of\s+(\d{4}))?\b", re.IGNORECASE),
)


@dataclass(frozen=True, slots=True)
class QueryRepresentation:
    original_question: str
    semantic_query: str
    important_terms: tuple[str, ...]
    exact_references: tuple[str, ...]
    document_hints: tuple[str, ...]
    answer_shape: str
    source_domain: str
    coverage_facets: tuple[str, ...]


def _answer_shape(question: str) -> str:
    lowered = question.casefold()
    if any(term in lowered for term in ("compare", "difference", "distinguish", "versus", " vs ")):
        return "comparison"
    # A table request needs its compact, value-first contract even if it also
    # contains words such as "conditions" or "main".
    if any(term in lowered for term in ("appendix", "table", "rate", "per square", "per sq")):
        return "table"
    # Questions explicitly naming two periods/documents are comparison
    # questions even when the word "compare" is omitted.
    if (len(re.findall(r"\b(?:19|20)\d{2}\b", lowered)) >= 2 and " and " in lowered) or (
        "both" in lowered and any(term in lowered for term in ("document", "circular", "clarification"))
    ):
        return "comparison"
    if any(term in lowered for term in ("what clarification", "which clarification", "later clarification", "supersed")):
        return "clarification"
    if any(term in lowered for term in ("list", "main conditions", "requirements", "exceptions", "installment", "scheduled")):
        return "list"
    if any(term in lowered for term in ("across", "both", "documents", "and what")):
        return "multi_document"
    return "direct_fact"


def classify_source_domain(question: str) -> str:
    """Identify requests that need an existing structured workflow, not PDFs.

    The matching intentionally stays narrow.  A policy question mentioning a
    tender or a bill is still document RAG unless it asks for a live record or
    calculation.
    """
    lowered = question.casefold()
    if re.search(r"\b(predict|forecast)\b.*\b(bill|billing|invoice)\b", lowered):
        return "BILLING"
    if re.search(r"\b(current|live)\b.*\b(workflow|agenda)\b", lowered):
        return "WORKFLOW"
    if re.search(r"\b(show|list|what)\b.*\b(paid applications?|application \d|tenant account|account history)\b", lowered):
        return "LIVE_DATABASE"
    if re.search(r"\b(create|publish|start)\b.*\btender\b", lowered):
        return "TENDER"
    return "DOCUMENT_RAG"


def needs_property_clarification(question: str) -> bool:
    """Detect a narrow class of rate questions missing an identifying subject."""
    lowered = question.casefold()
    asks_for_value = any(term in lowered for term in ("lease rent", "lease rate", "correct rent", "correct rate"))
    vague_subject = any(term in lowered for term in ("this property", "this land", "the property")) or lowered.strip() in {
        "what is the correct lease rent?", "what is the correct lease rate?",
    }
    has_identifier = bool(re.search(r"\b(?:tenant|tenancy|application|plot|property)\s*(?:id|no\.?)?\s*[a-z0-9/-]{2,}", lowered))
    return asks_for_value and vague_subject and not has_identifier


def _coverage_facets(question: str, answer_shape: str) -> tuple[str, ...]:
    """Return a bounded set of user-stated evidence facets without an LLM.

    Multi-part questions often contain independent clauses joined by ``and`` or
    ``or``.  Each clause is a useful additional retrieval query, but only for
    answer shapes that genuinely need more than one supporting item.  This is
    syntax-driven and intentionally does not add domain facts, document names,
    page numbers, or evaluation identifiers.
    """
    if answer_shape not in {"list", "comparison", "multi_document", "clarification"}:
        return ()
    clauses = re.split(r"\s+\b(?:and|or)\b\s+", question, flags=re.IGNORECASE)
    facets: list[str] = []
    for clause in clauses:
        terms = [
            token.casefold()
            for token in _WORD_RE.findall(clause)
            if token.casefold() not in _STOPWORDS
        ]
        # Very short clauses such as "and why" add noise rather than evidence.
        if len(terms) < 2:
            continue
        facet = " ".join(terms[:14])
        if facet and facet not in facets:
            facets.append(facet)
        if len(facets) == 4:
            break
    return tuple(facets)


def analyse_query(question: str) -> QueryRepresentation:
    """Preserve the original question while extracting broadly useful hints."""
    original = _SPACE_RE.sub(" ", question or "").strip()
    references: list[str] = []
    hints: list[str] = []
    for pattern in _REFERENCE_PATTERNS:
        for match in pattern.finditer(original):
            phrase = _SPACE_RE.sub(" ", match.group(0)).strip()
            if phrase and phrase.casefold() not in {value.casefold() for value in references}:
                references.append(phrase)
                hints.append(phrase)
    important_terms = tuple(
        dict.fromkeys(token.casefold() for token in _WORD_RE.findall(original) if token.casefold() not in _STOPWORDS)
    )
    answer_shape = _answer_shape(original)
    return QueryRepresentation(
        original_question=original,
        semantic_query=original,
        important_terms=important_terms,
        exact_references=tuple(references),
        document_hints=tuple(hints),
        answer_shape=answer_shape,
        source_domain=classify_source_domain(original),
        coverage_facets=_coverage_facets(original, answer_shape),
    )
