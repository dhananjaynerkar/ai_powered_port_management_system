"""Conservative, filename-derived source grouping for retrieval and evaluation.

This does not infer legal hierarchy or supersession.  It preserves the exact
source filename as the canonical citation anchor and only derives a family
when a title explicitly contains a recognisable identifier.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    document_family: str
    document_type: str
    canonical_source: str
    source_date: str | None
    clarification_number: str | None
    supersedes: str | None
    equivalent_source_group: str

    def payload(self) -> dict[str, str | None]:
        return asdict(self)


def derive_source_metadata(filename: str) -> SourceMetadata:
    """Derive only explicit title metadata; unknown files remain self-grouped."""
    normalized = " ".join(filename.rsplit(".", 1)[0].replace("_", " ").split())
    lowered = normalized.casefold()
    year_match = re.search(r"\b(19|20)\d{2}\b", normalized)
    source_date = year_match.group(0) if year_match else None
    clarification = re.search(r"clarification\s+no\.?\s*(\d+)\s+of\s+(\d{4})", normalized, re.IGNORECASE)
    bylaw = re.search(r"(?:by|bye)[- ]?law\s+no\.?\s*(\d+)", normalized, re.IGNORECASE)
    pglm = re.search(r"\bPGLM\s*(\d{4})", normalized, re.IGNORECASE)
    if clarification:
        family = f"Clarification No. {clarification.group(1)} of {clarification.group(2)}"
        return SourceMetadata(family, "clarification", filename, source_date, clarification.group(1), None, family)
    if bylaw:
        family = f"By-law No. {bylaw.group(1)}"
        return SourceMetadata(family, "bylaw", filename, source_date, None, None, family)
    if pglm:
        family = f"PGLM {pglm.group(1)}"
        return SourceMetadata(family, "policy_compilation", filename, source_date, None, None, family)
    if "tender" in lowered or "procedure" in lowered:
        return SourceMetadata(normalized, "tender", filename, source_date, None, None, normalized)
    return SourceMetadata(normalized, "unclassified", filename, source_date, None, None, normalized)
