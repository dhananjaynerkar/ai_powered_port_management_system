"""ACL-aware dense + lexical retrieval, RRF, BGE reranking, and parent expansion."""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any
from uuid import UUID

import httpx
from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg import connect, sql

from .ingestion import _embed
from .settings import Settings


@dataclass(frozen=True, slots=True)
class RetrievalTimings:
    embed_ms: int
    lexical_retrieval_ms: int
    dense_retrieval_ms: int
    rerank_ms: int
    context_assembly_ms: int


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    source_id: str
    document_id: UUID
    chunk_id: UUID
    document_title: str
    filename: str
    page_number: int
    chunk_index: int
    chunk_text: str
    context_text: str
    section_title: str | None
    clause_number: str | None
    lexical_rank: int | None
    dense_rank: int | None
    fused_score: float
    rerank_score: float


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    chunks: list[RetrievedChunk]
    timings: RetrievalTimings
    candidate_count: int


_RERANKERS: dict[tuple[str, str, int], Any] = {}


def _reranker(settings: Settings) -> Any:
    key = (settings.reranker_model, settings.reranker_device, settings.reranker_max_length)
    if key not in _RERANKERS:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError("sentence-transformers is required for the configured BGE reranker") from exc
        _RERANKERS[key] = CrossEncoder(settings.reranker_model, device=settings.reranker_device, max_length=settings.reranker_max_length)
    return _RERANKERS[key]


def _rerank(settings: Settings, question: str, texts: list[str]) -> list[float]:
    if not texts:
        return []
    scores = _reranker(settings).predict([[question, text] for text in texts], batch_size=settings.reranker_batch_size, show_progress_bar=False)
    if isinstance(scores, (int, float)):
        return [float(scores)]
    return [float(score) for score in scores]


def _candidate_rows(settings: Settings, question: str, user_role: str) -> tuple[list[dict[str, Any]], int, int, int]:
    candidate_limit = settings.rerank_candidate_count
    document_schema = sql.Identifier(settings.document_schema_name)
    vector_schema = sql.Identifier(settings.vector_schema_name)
    embed_started = perf_counter()
    with httpx.Client() as client:
        embedding = _embed(client, settings, question)
    embed_ms = int((perf_counter() - embed_started) * 1000)
    acl = sql.SQL("(cardinality(a.acl_roles)=0 OR %s=ANY(a.acl_roles))")
    lexical_query = sql.SQL("""
        SELECT c.chunk_id, row_number() OVER (
            ORDER BY ts_rank_cd(c.search_vector, websearch_to_tsquery('simple', %s)) DESC, c.chunk_id
        )::integer AS rank
        FROM {}.document_chunk c JOIN {}.chunk_acl a ON a.chunk_id=c.chunk_id
        WHERE c.search_vector @@ websearch_to_tsquery('simple', %s) AND {}
        LIMIT %s
    """).format(vector_schema, vector_schema, acl)
    dense_query = sql.SQL("""
        SELECT c.chunk_id, row_number() OVER (ORDER BY e.embedding <=> %s::vector, c.chunk_id)::integer AS rank
        FROM {}.document_chunk c JOIN {}.chunk_embedding e ON e.chunk_id=c.chunk_id
        JOIN {}.chunk_acl a ON a.chunk_id=c.chunk_id WHERE {} LIMIT %s
    """).format(vector_schema, vector_schema, vector_schema, acl)
    with connect(settings.database_url.unicode_string()) as connection:
        register_vector(connection)
        with connection.cursor() as cursor:
            started = perf_counter()
            cursor.execute(lexical_query, (question, question, user_role, candidate_limit))
            lexical = {row[0]: row[1] for row in cursor.fetchall()}
            lexical_ms = int((perf_counter() - started) * 1000)
            started = perf_counter()
            cursor.execute(dense_query, (Vector(embedding), user_role, candidate_limit))
            dense = {row[0]: row[1] for row in cursor.fetchall()}
            dense_ms = int((perf_counter() - started) * 1000)
            chunk_ids = list(set(lexical) | set(dense))
            if not chunk_ids:
                return [], embed_ms, lexical_ms, dense_ms
            cursor.execute(
                sql.SQL("""SELECT c.chunk_id, c.document_id, c.chunk_index, c.chunk_text, c.section_title,
                    c.clause_number, COALESCE(NULLIF(d.source_metadata->>'title', ''), d.original_filename),
                    d.original_filename, c.page_number
                    FROM {}.document_chunk c JOIN {}.document_record d ON d.document_id=c.document_id
                    WHERE c.chunk_id=ANY(%s)""").format(vector_schema, document_schema),
                (chunk_ids,),
            )
            metadata = {row[0]: row for row in cursor.fetchall()}
    rows: list[dict[str, Any]] = []
    for chunk_id in chunk_ids:
        row = metadata[chunk_id]
        lexical_rank = lexical.get(chunk_id)
        dense_rank = dense.get(chunk_id)
        fused = (1 / (settings.rrf_k + lexical_rank) if lexical_rank else 0) + (1 / (settings.rrf_k + dense_rank) if dense_rank else 0)
        rows.append({
            "chunk_id": row[0], "document_id": row[1], "chunk_index": row[2], "chunk_text": row[3],
            "section_title": row[4], "clause_number": row[5], "document_title": row[6],
            "filename": row[7], "page_number": row[8],
            "lexical_rank": lexical_rank, "dense_rank": dense_rank, "fused_score": float(fused),
        })
    rows.sort(key=lambda item: (-item["fused_score"], str(item["chunk_id"])))
    return rows[:candidate_limit], embed_ms, lexical_ms, dense_ms


def _expand_context(settings: Settings, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return rows
    vector_schema = sql.Identifier(settings.vector_schema_name)
    remaining_tokens = settings.context_token_budget
    expanded: list[dict[str, Any]] = []
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            for row in rows:
                cursor.execute(
                    sql.SQL("""SELECT chunk_text FROM {}.document_chunk
                        WHERE document_id=%s AND chunk_index BETWEEN %s AND %s
                        ORDER BY chunk_index""").format(vector_schema),
                    (row["document_id"], row["chunk_index"] - settings.parent_context_window, row["chunk_index"] + settings.parent_context_window),
                )
                context = "\n\n".join(item[0] for item in cursor.fetchall())
                estimated = max(1, len(context) // settings.context_characters_per_token)
                if estimated > remaining_tokens:
                    context = context[: remaining_tokens * settings.context_characters_per_token]
                    estimated = remaining_tokens
                if not context:
                    break
                remaining_tokens -= estimated
                expanded.append({**row, "context_text": context})
                if remaining_tokens <= 0:
                    break
    return expanded


def retrieve(settings: Settings, question: str, user_role: str, limit: int | None = None) -> RetrievalResult:
    if not question.strip():
        raise ValueError("A question is required")
    result_limit = min(limit, settings.retrieval_limit) if limit is not None else settings.retrieval_limit
    candidates, embed_ms, lexical_ms, dense_ms = _candidate_rows(settings, question, user_role)
    rerank_started = perf_counter()
    scores = _rerank(settings, question, [item["chunk_text"] for item in candidates])
    for item, score in zip(candidates, scores, strict=True):
        item["rerank_score"] = score
    candidates.sort(key=lambda item: (-item["rerank_score"], -item["fused_score"], str(item["chunk_id"])))
    rerank_ms = int((perf_counter() - rerank_started) * 1000)
    context_started = perf_counter()
    selected = _expand_context(settings, candidates[:result_limit])
    chunks = [
        RetrievedChunk(
            source_id=f"S{index}", document_id=item["document_id"], chunk_id=item["chunk_id"],
            document_title=item["document_title"], filename=item["filename"], page_number=item["page_number"], chunk_index=item["chunk_index"],
            chunk_text=item["chunk_text"], context_text=item["context_text"], section_title=item["section_title"],
            clause_number=item["clause_number"], lexical_rank=item["lexical_rank"], dense_rank=item["dense_rank"],
            fused_score=item["fused_score"], rerank_score=item["rerank_score"],
        )
        for index, item in enumerate(selected, start=1)
    ]
    context_ms = int((perf_counter() - context_started) * 1000)
    return RetrievalResult(chunks, RetrievalTimings(embed_ms, lexical_ms, dense_ms, rerank_ms, context_ms), len(candidates))


def hybrid_search(settings: Settings, question: str, limit: int | None = None, user_role: str = "authority") -> list[RetrievedChunk]:
    """Compatibility wrapper for the CLI; API routes call :func:`retrieve` directly."""
    return retrieve(settings, question, user_role, limit).chunks
