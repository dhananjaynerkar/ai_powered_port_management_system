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


def validate_query(settings: Settings, text: str) -> GuardrailDecision:
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text or "").strip()
    if len(cleaned) < 2:
        return GuardrailDecision(False, cleaned, "Please enter a meaningful question.")
    if len(cleaned) > settings.query_max_characters:
        return GuardrailDecision(False, cleaned, f"Questions are limited to {settings.query_max_characters:,} characters.")
    if any(pattern.search(cleaned) for pattern in _BLOCKED_PATTERNS):
        return GuardrailDecision(False, cleaned, "This request conflicts with the assistant security policy.")
    return GuardrailDecision(True, cleaned)


def referenced_source_ids(answer: str) -> set[str]:
    return set(re.findall(r"\[(S\d+)\]", answer or ""))


def validate_citations(answer: str, valid_source_ids: set[str]) -> tuple[bool, str | None]:
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
