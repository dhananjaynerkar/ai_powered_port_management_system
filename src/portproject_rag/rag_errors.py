"""Typed, safe RAG pipeline failures.

The public API maps these stages to short user-facing messages.  The original
exception remains chained for logs and tests only; it is never returned to a
browser client.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RagFailureDetails:
    code: str
    public_message: str
    status_code: int


_DETAILS: dict[str, RagFailureDetails] = {
    "EMBEDDING_UNAVAILABLE": RagFailureDetails("EMBEDDING_UNAVAILABLE", "Search is temporarily unavailable. Please try again.", 503),
    "LEXICAL_FAILURE": RagFailureDetails("LEXICAL_FAILURE", "Search is temporarily unavailable. Please try again.", 503),
    "DENSE_FAILURE": RagFailureDetails("DENSE_FAILURE", "Search is temporarily unavailable. Please try again.", 503),
    "RERANKER_UNAVAILABLE": RagFailureDetails("RERANKER_UNAVAILABLE", "AI search is temporarily degraded. Please try again.", 503),
    "CONTEXT_FAILURE": RagFailureDetails("CONTEXT_FAILURE", "Search is temporarily unavailable. Please try again.", 503),
    "GENERATION_TIMEOUT": RagFailureDetails("GENERATION_TIMEOUT", "The answer model took too long to respond. Please try again.", 503),
    "GENERATION_FAILURE": RagFailureDetails("GENERATION_FAILURE", "The answer model is temporarily unavailable. Please try again.", 503),
    "CITATION_FAILURE": RagFailureDetails("CITATION_FAILURE", "The answer could not be grounded in retrieved documents. Please refine the question.", 422),
}


class RagStageError(RuntimeError):
    """An internal RAG failure with a safe, stable public stage code."""

    def __init__(self, stage: str, *, cause: Exception | None = None) -> None:
        if stage not in _DETAILS:
            raise ValueError(f"Unsupported RAG failure stage: {stage}")
        self.stage = stage
        self.details = _DETAILS[stage]
        self.cause = cause
        super().__init__(stage)

    @property
    def public_payload(self) -> dict[str, str]:
        return {"code": self.details.code, "message": self.details.public_message}
