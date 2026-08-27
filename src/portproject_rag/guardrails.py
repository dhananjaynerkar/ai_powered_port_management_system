"""Input and output controls for authenticated document RAG."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .settings import Settings


@dataclass(frozen=True, slots=True)
class GuardrailDecision:
    allowed: bool
    cleaned_text: str
    reason: str | None = None


_BLOCKED_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bignore\s+(all\s+)?(previous|prior)\s+instructions?\b",
        r"\b(reveal|show|print|repeat)\s+(the\s+)?(system|developer)\s+prompt\b",
        r"\b(bypass|disable|override)\s+(the\s+)?(guardrails|safety|security|acl|rls)\b",
        r"\b(drop|truncate|delete\s+from|alter|grant|revoke)\s+(table|database|schema)\b",
        r"\b(exfiltrate|dump)\s+(credentials?|passwords?|secrets?|tokens?)\b",
    )
)

_CITATION_GROUP = re.compile(r"\[\s*(S\d+(?:\s*[,;]\s*S\d+)*)\s*\]", re.IGNORECASE)
_SAFE_NO_EVIDENCE = {
    "the indexed corpus does not contain enough evidence to answer this question",
    "i couldn't find that information in the documents available to you",
    "i could not find that information in the documents available to you",
}


def validate_query(settings: Settings, text: str) -> GuardrailDecision:
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text or "").strip()
    if len(cleaned) < 2:
        return GuardrailDecision(False, cleaned, "Please enter a meaningful question.")
    if len(cleaned) > settings.query_max_characters:
        return GuardrailDecision(False, cleaned, f"Questions are limited to {settings.query_max_characters:,} characters.")
    if any(pattern.search(cleaned) for pattern in _BLOCKED_PATTERNS):
        return GuardrailDecision(False, cleaned, "This request conflicts with the assistant security policy.")
    return GuardrailDecision(True, cleaned)


def normalize_citation_syntax(answer: str) -> str:
    """Canonicalize safe bracketed source lists without adding any source ID.

    The model may render the same retrieved citations as ``[S1, S2]`` or
    ``[S1; S2]``.  Converting those forms to ``[S1][S2]`` keeps the public
    citation component and the validator on one exact representation.  Text
    that is not a simple list of source IDs is left unchanged.
    """

    def replace(match: re.Match[str]) -> str:
        ids = re.findall(r"S\d+", match.group(1), flags=re.IGNORECASE)
        return "".join(f"[{source_id.upper()}]" for source_id in ids)

    return _CITATION_GROUP.sub(replace, answer or "")


def referenced_source_ids(answer: str) -> set[str]:
    return set(re.findall(r"\[(S\d+)\]", normalize_citation_syntax(answer), flags=re.IGNORECASE))


def is_safe_no_evidence_response(answer: str) -> bool:
    """Recognize only the application's fixed non-factual refusal messages."""
    normalized = re.sub(r"[.!?]+$", "", " ".join((answer or "").casefold().split()))
    return normalized in _SAFE_NO_EVIDENCE


def validate_citations(answer: str, valid_source_ids: set[str]) -> tuple[bool, str | None]:
    if is_safe_no_evidence_response(answer):
        return True, None
    cited = referenced_source_ids(answer)
    unknown = cited - valid_source_ids
    if unknown:
        return False, f"Unknown citation identifiers: {', '.join(sorted(unknown))}"
    if valid_source_ids and not cited:
        return False, "The generated answer did not cite retrieved evidence."
    if not valid_source_ids and cited:
        return False, "The generated answer cited evidence that was not retrieved."
    if valid_source_ids:
        uncited = [
            paragraph
            for paragraph in re.split(r"\n\s*\n", answer.strip())
            if len(re.findall(r"\b\w+\b", paragraph)) >= 12 and not referenced_source_ids(paragraph)
        ]
        if uncited:
            return False, "Every factual paragraph must include a retrieved source citation."
    return True, None
