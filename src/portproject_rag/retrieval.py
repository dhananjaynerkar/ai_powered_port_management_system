"""ACL-aware hybrid retrieval with safe reranker degradation and diagnostics."""
from __future__ import annotations

import re
from dataclasses import dataclass
from threading import Lock
from time import monotonic, perf_counter
from typing import Any
from uuid import UUID

import httpx
from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg import connect, sql

from .ingestion import _embed
from .query_analysis import QueryRepresentation, analyse_query
from .rag_errors import RagStageError
from .settings import Settings
from .source_metadata import derive_source_metadata


@dataclass(frozen=True, slots=True)
class RetrievalTimings:
    embed_ms: int
    lexical_retrieval_ms: int
    dense_retrieval_ms: int
    rerank_ms: int
    context_assembly_ms: int
    # The existing five values remain first for compatibility with callers
    # that construct this value positionally.  The remaining values separate
    # stages for performance evidence; none changes ranking or context.
    query_analysis_ms: int = 0
    candidate_fusion_ms: int = 0
    adjacent_candidates_ms: int = 0
    context_selection_ms: int = 0
    reranker_load_ms: int = 0
    reranker_pair_build_ms: int = 0
    reranker_predict_ms: int = 0
    reranker_postprocess_ms: int = 0


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
    source_metadata: dict[str, str | None] | None = None


@dataclass(frozen=True, slots=True)
class RetrievalDiagnostics:
    query: QueryRepresentation
    reranker_degraded: bool
    reranker_reason: str | None
    candidate_rows: list[dict[str, Any]]
    selected_rows: list[dict[str, Any]]
    excluded_rows: list[dict[str, Any]]
    context_budget_tokens: int
    context_tokens: int
    context_truncated: bool


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    chunks: list[RetrievedChunk]
    timings: RetrievalTimings
    candidate_count: int
    diagnostics: RetrievalDiagnostics | None = None


_RERANKERS: dict[tuple[str, str, int], Any] = {}
_RERANKER_FAILURES: dict[tuple[str, str, int], tuple[float, str]] = {}
_RERANKER_LOCK = Lock()
_SAFE_TSQUERY_TOKEN = re.compile(r"[A-Za-z0-9]+")
_MID_SENTENCE_START = re.compile(r"^[a-z]")


class _RerankScores(list[float]):
    """List-compatible reranker result with stage timing for diagnostics."""

    def __init__(self, values: list[float], *, load_ms: int, pair_build_ms: int, predict_ms: int, postprocess_ms: int) -> None:
        super().__init__(values)
        self.load_ms = load_ms
        self.pair_build_ms = pair_build_ms
        self.predict_ms = predict_ms
        self.postprocess_ms = postprocess_ms


def _reranker_key(settings: Settings) -> tuple[str, str, int]:
    return (settings.reranker_model, settings.reranker_device, settings.reranker_max_length)


def clear_reranker_cache() -> None:
    """Reset process-local singleton state for deterministic tests only."""
    with _RERANKER_LOCK:
        _RERANKERS.clear()
        _RERANKER_FAILURES.clear()


def reranker_state(settings: Settings) -> dict[str, str | bool | None]:
    """Report process-local reranker state without exposing exception details."""
    key = _reranker_key(settings)
    with _RERANKER_LOCK:
        if key in _RERANKERS:
            return {"state": "ready", "degraded": False, "reason": None}
        failure = _RERANKER_FAILURES.get(key)
    if failure and monotonic() - failure[0] < settings.reranker_failure_cooldown_seconds:
        return {"state": "degraded", "degraded": True, "reason": failure[1]}
    return {"state": "not_loaded", "degraded": False, "reason": None}


def _reranker(settings: Settings) -> Any:
    key = _reranker_key(settings)
    with _RERANKER_LOCK:
        cached = _RERANKERS.get(key)
        if cached is not None:
            return cached
        failure = _RERANKER_FAILURES.get(key)
        if failure and monotonic() - failure[0] < settings.reranker_failure_cooldown_seconds:
            raise RagStageError("RERANKER_UNAVAILABLE")
        try:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder(
                settings.reranker_model,
                device=settings.reranker_device,
                max_length=settings.reranker_max_length,
                local_files_only=settings.reranker_local_files_only,
            )
        except Exception as exc:  # model loading can exhaust Windows virtual memory
            _RERANKER_FAILURES[key] = (monotonic(), type(exc).__name__)
            raise RagStageError("RERANKER_UNAVAILABLE", cause=exc) from exc
        _RERANKERS[key] = model
        _RERANKER_FAILURES.pop(key, None)
        return model


def _rerank(settings: Settings, question: str, texts: list[str]) -> list[float]:
    """Run the configured singleton CrossEncoder or raise a typed stage error."""
    if not texts:
        return []
    try:
        load_started = perf_counter()
        model = _reranker(settings)
        load_ms = int((perf_counter() - load_started) * 1000)
        pairs_started = perf_counter()
        pairs = [[question, text] for text in texts]
        pair_build_ms = int((perf_counter() - pairs_started) * 1000)
        predict_started = perf_counter()
        scores = model.predict(pairs, batch_size=settings.reranker_batch_size, show_progress_bar=False)
        predict_ms = int((perf_counter() - predict_started) * 1000)
    except RagStageError:
        raise
    except Exception as exc:
        with _RERANKER_LOCK:
            _RERANKER_FAILURES[_reranker_key(settings)] = (monotonic(), type(exc).__name__)
            _RERANKERS.pop(_reranker_key(settings), None)
        raise RagStageError("RERANKER_UNAVAILABLE", cause=exc) from exc
    postprocess_started = perf_counter()
    values = [float(scores)] if isinstance(scores, (int, float)) else [float(score) for score in scores]
    return _RerankScores(
        values,
        load_ms=load_ms,
        pair_build_ms=pair_build_ms,
        predict_ms=predict_ms,
        postprocess_ms=int((perf_counter() - postprocess_started) * 1000),
    )


def _safe_or_query(terms: tuple[str, ...]) -> str | None:
    values: list[str] = []
    for term in terms:
        for token in _SAFE_TSQUERY_TOKEN.findall(term.casefold()):
            values.append(token)
            # PostgreSQL's ``simple`` configuration intentionally avoids an
            # English dictionary.  Add only conservative surface-form stems so
            # a user word such as "transferring" can still match "transfer".
            if len(token) > 5 and token.endswith("ing"):
                stem = token[:-3]
                if len(stem) > 2 and len(stem) >= 2 and stem[-1:] == stem[-2:-1]:
                    stem = stem[:-1]
                if len(stem) > 2:
                    values.append(stem)
            elif len(token) > 4 and token.endswith("ed"):
                values.append(token[:-2])
    values = list(dict.fromkeys(values))
    return " | ".join(values[:16]) or None


def _title_hint_count(query: QueryRepresentation, row: tuple[Any, ...]) -> int:
    if not query.document_hints:
        return 0
    haystack = re.sub(r"[^a-z0-9]+", " ", f"{row[6]} {row[7]}".casefold())
    matches = 0
    for hint in query.document_hints:
        terms = [term for term in _SAFE_TSQUERY_TOKEN.findall(hint.casefold()) if len(term) > 1]
        if terms and all(term in haystack for term in terms):
            matches += 1
    return matches


def _title_hint_score(query: QueryRepresentation, row: tuple[Any, ...], boost: float) -> float:
    return _title_hint_count(query, row) * boost


def _lexical_rows(
    cursor: Any, vector_schema: sql.Identifier, query: QueryRepresentation, user_role: str, candidate_limit: int
) -> tuple[dict[Any, list[int]], dict[Any, set[int]]]:
    acl = sql.SQL("(cardinality(a.acl_roles)=0 OR %s=ANY(a.acl_roles))")
    rows_by_id: dict[Any, list[int]] = {}
    facet_hits: dict[Any, set[int]] = {}
    queries: list[tuple[sql.Composed, tuple[Any, ...], int | None]] = []
    primary = sql.SQL("""
        SELECT c.chunk_id, row_number() OVER (ORDER BY ts_rank_cd(c.search_vector, websearch_to_tsquery('simple', %s)) DESC, c.chunk_id)::integer AS rank
        FROM {}.document_chunk c JOIN {}.chunk_acl a ON a.chunk_id=c.chunk_id
        WHERE c.search_vector @@ websearch_to_tsquery('simple', %s) AND {} LIMIT %s
    """).format(vector_schema, vector_schema, acl)
    queries.append((primary, (query.semantic_query, query.semantic_query, user_role, candidate_limit), None))
    for reference in query.exact_references[:4]:
        exact = sql.SQL("""
            SELECT c.chunk_id, row_number() OVER (ORDER BY ts_rank_cd(c.search_vector, phraseto_tsquery('simple', %s)) DESC, c.chunk_id)::integer AS rank
            FROM {}.document_chunk c JOIN {}.chunk_acl a ON a.chunk_id=c.chunk_id
            WHERE c.search_vector @@ phraseto_tsquery('simple', %s) AND {} LIMIT %s
        """).format(vector_schema, vector_schema, acl)
        queries.append((exact, (reference, reference, user_role, candidate_limit), None))
    salient = _safe_or_query(query.important_terms)
    if salient:
        fallback = sql.SQL("""
            SELECT c.chunk_id, row_number() OVER (ORDER BY ts_rank_cd(c.search_vector, to_tsquery('simple', %s)) DESC, c.chunk_id)::integer AS rank
            FROM {}.document_chunk c JOIN {}.chunk_acl a ON a.chunk_id=c.chunk_id
            WHERE c.search_vector @@ to_tsquery('simple', %s) AND {} LIMIT %s
        """).format(vector_schema, vector_schema, acl)
        queries.append((fallback, (salient, salient, user_role, candidate_limit), None))
    for facet_index, facet in enumerate(query.coverage_facets):
        facet_query = sql.SQL("""
            SELECT c.chunk_id, row_number() OVER (ORDER BY ts_rank_cd(c.search_vector, websearch_to_tsquery('simple', %s)) DESC, c.chunk_id)::integer AS rank
            FROM {}.document_chunk c JOIN {}.chunk_acl a ON a.chunk_id=c.chunk_id
            WHERE c.search_vector @@ websearch_to_tsquery('simple', %s) AND {} LIMIT %s
        """).format(vector_schema, vector_schema, acl)
        queries.append((facet_query, (facet, facet, user_role, candidate_limit), facet_index))
    try:
        for statement, parameters, facet_index in queries:
            cursor.execute(statement, parameters)
            for chunk_id, rank in cursor.fetchall():
                rows_by_id.setdefault(chunk_id, []).append(int(rank))
                if facet_index is not None:
                    facet_hits.setdefault(chunk_id, set()).add(facet_index)
    except Exception as exc:
        raise RagStageError("LEXICAL_FAILURE", cause=exc) from exc
    return rows_by_id, facet_hits


def _candidate_rows(
    settings: Settings, question: str | QueryRepresentation, user_role: str
) -> tuple[list[dict[str, Any]], int, int, int, int]:
    """Return ACL-filtered hybrid candidates before reranking."""
    query = question if isinstance(question, QueryRepresentation) else analyse_query(question)
    candidate_limit = settings.candidate_pool_size
    document_schema = sql.Identifier(settings.document_schema_name)
    vector_schema = sql.Identifier(settings.vector_schema_name)
    acl = sql.SQL("(cardinality(a.acl_roles)=0 OR %s=ANY(a.acl_roles))")
    dense_query = sql.SQL("""
        SELECT c.chunk_id, row_number() OVER (ORDER BY e.embedding <=> %s::vector, c.chunk_id)::integer AS rank
        FROM {}.document_chunk c JOIN {}.chunk_embedding e ON e.chunk_id=c.chunk_id
        JOIN {}.chunk_acl a ON a.chunk_id=c.chunk_id WHERE {} LIMIT %s
    """).format(vector_schema, vector_schema, vector_schema, acl)
    try:
        with connect(settings.database_url.unicode_string()) as connection:
            register_vector(connection)
            with connection.cursor() as cursor:
                started = perf_counter()
                lexical, lexical_facet_hits = _lexical_rows(cursor, vector_schema, query, user_role, candidate_limit)
                lexical_ms = int((perf_counter() - started) * 1000)
                started = perf_counter()
                dense: dict[Any, list[int]] = {}
                dense_facet_hits: dict[Any, set[int]] = {}
                embed_started = perf_counter()
                with httpx.Client() as client:
                    dense_queries = [(query.semantic_query, None), *[(facet, index) for index, facet in enumerate(query.coverage_facets)]]
                    for dense_text, facet_index in dense_queries:
                        try:
                            embedding = _embed(client, settings, dense_text)
                        except Exception as exc:
                            raise RagStageError("EMBEDDING_UNAVAILABLE", cause=exc) from exc
                        cursor.execute(dense_query, (Vector(embedding), user_role, candidate_limit))
                        for chunk_id, rank in cursor.fetchall():
                            dense.setdefault(chunk_id, []).append(int(rank))
                            if facet_index is not None:
                                dense_facet_hits.setdefault(chunk_id, set()).add(facet_index)
                embed_ms = int((perf_counter() - embed_started) * 1000)
                dense_total_ms = int((perf_counter() - started) * 1000)
                # Dense retrieval timing excludes the separately measured
                # embedding request.  The previous measurement contained both
                # values, which made stage percentages misleading.
                dense_ms = max(0, dense_total_ms - embed_ms)
                chunk_ids = list(set(lexical) | set(dense))
                if not chunk_ids:
                    return [], embed_ms, lexical_ms, dense_ms, 0
                cursor.execute(
                    sql.SQL("""SELECT c.chunk_id, c.document_id, c.chunk_index, c.chunk_text, c.section_title,
                        c.clause_number, COALESCE(NULLIF(d.source_metadata->>'title', ''), d.original_filename),
                        d.original_filename, c.page_number
                        FROM {}.document_chunk c JOIN {}.document_record d ON d.document_id=c.document_id
                        JOIN {}.chunk_acl a ON a.chunk_id=c.chunk_id
                        WHERE c.chunk_id=ANY(%s) AND {}""").format(vector_schema, document_schema, vector_schema, acl),
                    (chunk_ids, user_role),
                )
                metadata = {row[0]: row for row in cursor.fetchall()}
    except RagStageError:
        raise
    except Exception as exc:
        raise RagStageError("DENSE_FAILURE", cause=exc) from exc
    fusion_started = perf_counter()
    rows: list[dict[str, Any]] = []
    for chunk_id in chunk_ids:
        row = metadata.get(chunk_id)
        if row is None:
            continue
        lexical_ranks = lexical.get(chunk_id, [])
        lexical_rank = min(lexical_ranks) if lexical_ranks else None
        dense_ranks = dense.get(chunk_id, [])
        dense_rank = min(dense_ranks) if dense_ranks else None
        facet_indexes = sorted(lexical_facet_hits.get(chunk_id, set()) | dense_facet_hits.get(chunk_id, set()))
        fused = sum(1 / (settings.rrf_k + rank) for rank in lexical_ranks)
        fused += sum(1 / (settings.rrf_k + rank) for rank in dense_ranks)
        fused += _title_hint_score(query, row, settings.source_hint_boost)
        rows.append({
            "chunk_id": row[0], "document_id": row[1], "chunk_index": row[2], "chunk_text": row[3],
            "section_title": row[4], "clause_number": row[5], "document_title": row[6], "filename": row[7],
            "page_number": row[8], "lexical_rank": lexical_rank, "dense_rank": dense_rank,
            "lexical_ranks": lexical_ranks, "dense_ranks": dense_ranks,
            "facet_indexes": facet_indexes, "document_hint_matches": _title_hint_count(query, row),
            "adjacent_to_candidate": False, "fused_score": float(fused),
            "source_metadata": derive_source_metadata(str(row[7])).payload(),
        })
    rows.sort(key=lambda item: (-item["fused_score"], str(item["chunk_id"])))
    fusion_ms = int((perf_counter() - fusion_started) * 1000)
    return rows[:candidate_limit], embed_ms, lexical_ms, dense_ms, fusion_ms


def _adjacent_page_candidates(
    settings: Settings, rows: list[dict[str, Any]], user_role: str, query: QueryRepresentation
) -> list[dict[str, Any]]:
    """Expose immediate, ACL-filtered neighbouring pages for multi-part evidence.

    A PDF page boundary is an extraction boundary, not necessarily an evidence
    boundary.  This bounded expansion uses only pages adjacent to already
    retrieved anchors; it does not crawl an entire document or bypass ACL.
    """
    if query.answer_shape not in {"list", "comparison", "multi_document", "clarification"} or not rows:
        return []
    anchors_by_document: dict[UUID, list[dict[str, Any]]] = {}
    for row in rows:
        anchors_by_document.setdefault(row["document_id"], []).append(row)
    existing_pages = {(row["document_id"], row["page_number"]) for row in rows}
    vector_schema = sql.Identifier(settings.vector_schema_name)
    document_schema = sql.Identifier(settings.document_schema_name)
    acl = sql.SQL("(cardinality(a.acl_roles)=0 OR %s=ANY(a.acl_roles))")
    promoted: list[dict[str, Any]] = []
    try:
        with connect(settings.database_url.unicode_string()) as connection, connection.cursor() as cursor:
            for document_id, anchors in anchors_by_document.items():
                neighbour_pages = sorted({anchor["page_number"] + offset for anchor in anchors for offset in (-1, 1) if anchor["page_number"] + offset > 0})
                if not neighbour_pages:
                    continue
                cursor.execute(
                    sql.SQL("""SELECT DISTINCT ON (c.page_number) c.chunk_id, c.document_id, c.chunk_index, c.chunk_text,
                        c.section_title, c.clause_number, COALESCE(NULLIF(d.source_metadata->>'title', ''), d.original_filename),
                        d.original_filename, c.page_number
                        FROM {}.document_chunk c JOIN {}.document_record d ON d.document_id=c.document_id
                        JOIN {}.chunk_acl a ON a.chunk_id=c.chunk_id
                        WHERE c.document_id=%s AND c.page_number=ANY(%s) AND {}
                        ORDER BY c.page_number, c.chunk_index""").format(vector_schema, document_schema, vector_schema, acl),
                    (document_id, neighbour_pages, user_role),
                )
                for row in cursor.fetchall():
                    page_key = (row[1], row[8])
                    if page_key in existing_pages:
                        continue
                    anchor = min(
                        anchors,
                        key=lambda item: (abs(item["page_number"] - row[8]), -item["fused_score"], str(item["chunk_id"])),
                    )
                    # An extraction page can begin in the middle of a sentence.
                    # In that case its preceding, ACL-authorized page is a
                    # stronger continuation candidate than a merely adjacent
                    # page.  This is a textual boundary signal, not a page
                    # direction rule, and remains scoped to the same document
                    # and an already-retrieved anchor.
                    anchor_starts_mid_sentence = bool(_MID_SENTENCE_START.match(str(anchor["chunk_text"]).lstrip()))
                    structural_continuation = (
                        row[8] < anchor["page_number"] and anchor_starts_mid_sentence
                    )
                    promoted.append({
                        "chunk_id": row[0], "document_id": row[1], "chunk_index": row[2], "chunk_text": row[3],
                        "section_title": row[4], "clause_number": row[5], "document_title": row[6], "filename": row[7],
                        "page_number": row[8], "lexical_rank": None, "dense_rank": None, "lexical_ranks": [], "dense_ranks": [],
                        "facet_indexes": [], "document_hint_matches": _title_hint_count(query, row),
                        "adjacent_to_candidate": True, "adjacent_anchor_page": anchor["page_number"],
                        "structural_continuation": structural_continuation,
                        "fused_score": float(anchor["fused_score"] * 0.5),
                        "source_metadata": derive_source_metadata(str(row[7])).payload(),
                    })
    except Exception as exc:
        raise RagStageError("CONTEXT_FAILURE", cause=exc) from exc
    promoted.sort(key=lambda item: (-item["fused_score"], str(item["chunk_id"])))
    # At most the two immediate neighbours of each measured hybrid candidate;
    # the final context limit still bounds model exposure.
    return promoted[: len(rows) * 2]


def _context_budget(settings: Settings, answer_shape: str) -> int:
    budgets = {
        "direct_fact": settings.context_token_budget_direct,
        "list": settings.context_token_budget_list,
        "comparison": settings.context_token_budget_comparison,
        "multi_document": settings.context_token_budget_comparison,
        "clarification": settings.context_token_budget_comparison,
        "table": settings.context_token_budget_table,
    }
    # The shape-specific controls supersede the legacy single global budget.
    # Keeping the latter as an unknown-shape fallback preserves older config
    # files without silently forcing every known answer type back to 800 tokens.
    return budgets.get(answer_shape, settings.context_token_budget)


def _final_context_limit(settings: Settings, answer_shape: str) -> int:
    """Return the verified source cap for a shape without raising the global cap.

    Shape-specific values retain the globally certified four-source default
    unless an experiment or a later evidence-backed configuration narrows a
    simple answer type.
    """
    limits = {
        "direct_fact": settings.final_context_source_count_direct,
        "table": settings.final_context_source_count_table,
    }
    return min(settings.final_context_source_count, limits.get(answer_shape, settings.final_context_source_count))


def _table_evidence_boost(query: QueryRepresentation, text: str, boost: float) -> float:
    """Recover table rows whose OCR preserves units but disrupts column layout.

    This uses only a general rate-table signature: the question asks for a
    table/rate and the candidate contains a unit plus a time-band row.  It does
    not contain document, page, or evaluation-question identifiers.
    """
    if query.answer_shape != "table" or not boost:
        return 0.0
    normalized = re.sub(r"\bmet\s+re\b", "metre", " ".join(text.casefold().split()))
    asks_for_rate = any(term in query.important_terms for term in ("charge", "rate", "square", "metre", "day"))
    has_unit = bool(re.search(r"(?:per\s+(?:sq\.?|square)\s+metre\s+per\s+day|per\s+day)", normalized))
    has_time_band = bool(re.search(r"(?:upto|up\s+to|beyond)\s+\d+\s+days?", normalized))
    return boost if asks_for_rate and has_unit and has_time_band else 0.0


def _select_context_candidates(
    candidates: list[dict[str, Any]], limit: int, answer_shape: str = "direct_fact", *,
    prefer_structural_continuation: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Select complementary evidence before generic document/page diversity.

    Direct questions retain the prior diversity-first behavior.  Multi-part
    answers first preserve distinct user-stated facets, then closely related
    pages from a selected or explicitly hinted document, and finally fill the
    remaining slots with diverse sources.
    """
    selected: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    seen_documents: set[UUID] = set()
    seen_pages: set[tuple[UUID, int]] = set()

    def add(row: dict[str, Any]) -> bool:
        page_key = (row["document_id"], row["page_number"])
        if page_key in seen_pages:
            excluded.append({"chunk_id": str(row["chunk_id"]), "reason": "duplicate_page"})
            return False
        selected.append(row)
        seen_documents.add(row["document_id"])
        seen_pages.add(page_key)
        return True

    multi_evidence = answer_shape in {"list", "comparison", "multi_document", "clarification"}
    primary = [row for row in candidates if not row.get("adjacent_to_candidate")]
    adjacent = [row for row in candidates if row.get("adjacent_to_candidate")]
    if multi_evidence:
        hinted_documents = {row["document_id"] for row in primary if row.get("document_hint_matches", 0) > 0}
        list_focus_documents: set[UUID] = set()
        if answer_shape == "list" and primary:
            by_document: dict[UUID, list[dict[str, Any]]] = {}
            for row in primary:
                by_document.setdefault(row["document_id"], []).append(row)
            # Multiple facet-bearing pages in one source are stronger evidence
            # of a connected policy answer than a single incidental keyword
            # hit in another source.
            focus_document = max(
                by_document,
                key=lambda document_id: (
                    sum(bool(row.get("facet_indexes")) for row in by_document[document_id]),
                    sum(float(row["fused_score"]) for row in by_document[document_id]),
                    str(document_id),
                ),
            )
            list_focus_documents.add(focus_document)
        cohesion_documents = hinted_documents or list_focus_documents
        available_facets = sorted({facet for row in primary for facet in row.get("facet_indexes", [])})
        for facet in available_facets:
            if len(selected) >= limit:
                break
            eligible = [
                item for item in primary
                if facet in item.get("facet_indexes", [])
                and (item["document_id"], item["page_number"]) not in seen_pages
                and (not cohesion_documents or item["document_id"] in cohesion_documents)
            ]
            if not cohesion_documents:
                unseen_document = next((item for item in eligible if item["document_id"] not in seen_documents), None)
                row = unseen_document or (eligible[0] if eligible else None)
            else:
                row = eligible[0] if eligible else None
            if row is not None:
                add(row)

        # Retain a same-document continuation that supplies the beginning of a
        # selected mid-sentence source before filling context with additional
        # pages that only repeat already-covered query facets.  The signal is
        # derived from stored text and applies only to ACL-filtered immediate
        # neighbours of selected candidates.
        if prefer_structural_continuation:
            selected_pages_by_document = {
                (item["document_id"], item["page_number"]) for item in selected
            }
            continuations = sorted(
                (
                    item for item in adjacent
                    if item.get("structural_continuation")
                    and item["document_id"] in cohesion_documents
                    and (item["document_id"], item.get("adjacent_anchor_page")) in selected_pages_by_document
                ),
                key=lambda item: (-float(item["fused_score"]), str(item["chunk_id"])),
            )
            for row in continuations:
                if len(selected) >= limit:
                    break
                add(row)

        # A list normally needs connected conditions from the same source.  A
        # named document is another evidence-backed signal for this cohesion.
        focus_documents = cohesion_documents or {row["document_id"] for row in selected}
        for row in primary:
            if len(selected) >= limit:
                break
            if row["document_id"] in focus_documents:
                add(row)
        for row in adjacent:
            if len(selected) >= limit:
                break
            if row["document_id"] in focus_documents and row.get("adjacent_anchor_page") in {
                item["page_number"] for item in selected if item["document_id"] == row["document_id"]
            }:
                add(row)

    deferred: list[dict[str, Any]] = []
    for row in primary + adjacent:
        if len(selected) >= limit:
            break
        page_key = (row["document_id"], row["page_number"])
        if page_key in seen_pages:
            add(row)
            continue
        if row["document_id"] in seen_documents:
            deferred.append(row)
            continue
        add(row)
    for row in deferred:
        if len(selected) >= limit:
            break
        add(row)
    selected_ids = {row["chunk_id"] for row in selected}
    excluded_ids = {UUID(item["chunk_id"]) for item in excluded if item.get("chunk_id")}
    for row in primary + adjacent:
        if row["chunk_id"] not in selected_ids and row["chunk_id"] not in excluded_ids:
            excluded.append({"chunk_id": str(row["chunk_id"]), "reason": "final_source_limit"})
    return selected, excluded


def _expand_context_with_metadata(
    settings: Settings, rows: list[dict[str, Any]], user_role: str | None, answer_shape: str
) -> tuple[list[dict[str, Any]], int, bool]:
    if not rows:
        return [], 0, False
    vector_schema = sql.Identifier(settings.vector_schema_name)
    total_budget = _context_budget(settings, answer_shape)
    remaining_tokens = total_budget
    expanded: list[dict[str, Any]] = []
    truncated = False
    acl_clause = sql.SQL("cardinality(a.acl_roles)=0") if user_role is None else sql.SQL("(cardinality(a.acl_roles)=0 OR %s=ANY(a.acl_roles))")
    try:
        with connect(settings.database_url.unicode_string()) as connection, connection.cursor() as cursor:
            for index, row in enumerate(rows):
                parameters: list[Any] = [row["document_id"], row["chunk_index"] - settings.parent_context_window, row["chunk_index"] + settings.parent_context_window]
                if user_role is not None:
                    parameters.append(user_role)
                cursor.execute(
                    sql.SQL("""SELECT c.chunk_index, c.chunk_text FROM {}.document_chunk c
                        JOIN {}.chunk_acl a ON a.chunk_id=c.chunk_id
                        WHERE c.document_id=%s AND c.chunk_index BETWEEN %s AND %s AND {}
                        ORDER BY c.chunk_index""").format(vector_schema, vector_schema, acl_clause),
                    parameters,
                )
                fetched = cursor.fetchall()
                own = [text for chunk_index, text in fetched if chunk_index == row["chunk_index"]]
                neighbors = [text for chunk_index, text in fetched if chunk_index != row["chunk_index"]]
                context = "\n\n".join(own + neighbors)
                remaining_sources = max(1, len(rows) - index)
                per_source_budget = max(1, remaining_tokens // remaining_sources)
                estimated = max(1, len(context) // settings.context_characters_per_token)
                if estimated > per_source_budget:
                    context = context[: per_source_budget * settings.context_characters_per_token]
                    estimated = per_source_budget
                    truncated = True
                if not context:
                    continue
                remaining_tokens -= estimated
                expanded.append({**row, "context_text": context})
                if remaining_tokens <= 0:
                    truncated = truncated or index < len(rows) - 1
                    break
    except Exception as exc:
        raise RagStageError("CONTEXT_FAILURE", cause=exc) from exc
    return expanded, total_budget - remaining_tokens, truncated


def _expand_context(settings: Settings, rows: list[dict[str, Any]], user_role: str | None = None) -> list[dict[str, Any]]:
    """Compatibility helper; direct callers get public-only parent expansion."""
    expanded, _tokens, _truncated = _expand_context_with_metadata(settings, rows, user_role, "direct_fact")
    return expanded


def retrieve(
    settings: Settings, question: str, user_role: str, limit: int | None = None, *,
    prefer_structural_continuation: bool = True,
) -> RetrievalResult:
    if not question.strip():
        raise ValueError("A question is required")
    analysis_started = perf_counter()
    query = analyse_query(question)
    query_analysis_ms = int((perf_counter() - analysis_started) * 1000)
    final_limit = _final_context_limit(settings, query.answer_shape)
    if limit is not None:
        final_limit = min(limit, final_limit)
    candidate_result = _candidate_rows(settings, query, user_role)
    # Preserve test seams that return the historical four-item tuple while
    # allowing the live implementation to report candidate-fusion timing.
    if len(candidate_result) == 4:
        candidates, embed_ms, lexical_ms, dense_ms = candidate_result
        candidate_fusion_ms = 0
    else:
        candidates, embed_ms, lexical_ms, dense_ms, candidate_fusion_ms = candidate_result
    adjacent_started = perf_counter()
    candidates.extend(_adjacent_page_candidates(settings, candidates, user_role, query))
    adjacent_candidates_ms = int((perf_counter() - adjacent_started) * 1000)
    candidates.sort(key=lambda item: (-item["fused_score"], str(item["chunk_id"])))
    rerank_started = perf_counter()
    reranker_degraded = False
    reranker_reason: str | None = None
    # Keep the measured candidate pool wider than the expensive reranker input.
    # The existing rerank_candidate_count setting is the explicit cost/quality
    # control; candidates outside that prefix retain their fused hybrid score.
    rerank_count = min(settings.rerank_candidate_count, len(candidates))
    try:
        scores = _rerank(settings, query.semantic_query, [item["chunk_text"] for item in candidates[:rerank_count]])
    except RagStageError as exc:
        if not settings.reranker_allow_degraded_mode:
            raise
        reranker_degraded = True
        reranker_reason = exc.stage
        scores = []
    for index, item in enumerate(candidates):
        score = scores[index] if index < len(scores) else item["fused_score"]
        table_boost = _table_evidence_boost(query, item["chunk_text"], settings.table_evidence_boost)
        item["table_evidence_boost"] = table_boost
        item["rerank_score"] = score + table_boost
    candidates.sort(key=lambda item: (-item["rerank_score"], -item["fused_score"], str(item["chunk_id"])))
    rerank_ms = int((perf_counter() - rerank_started) * 1000)
    reranker_load_ms = int(getattr(scores, "load_ms", 0))
    reranker_pair_build_ms = int(getattr(scores, "pair_build_ms", 0))
    reranker_predict_ms = int(getattr(scores, "predict_ms", 0))
    reranker_postprocess_ms = int(getattr(scores, "postprocess_ms", 0))
    selection_started = perf_counter()
    selected, excluded = _select_context_candidates(
        candidates, final_limit, query.answer_shape,
        prefer_structural_continuation=prefer_structural_continuation,
    )
    context_selection_ms = int((perf_counter() - selection_started) * 1000)
    context_started = perf_counter()
    expanded, context_tokens, context_truncated = _expand_context_with_metadata(settings, selected, user_role, query.answer_shape)
    chunks = [
        RetrievedChunk(
            source_id=f"S{index}", document_id=item["document_id"], chunk_id=item["chunk_id"],
            document_title=item["document_title"], filename=item["filename"], page_number=item["page_number"], chunk_index=item["chunk_index"],
            chunk_text=item["chunk_text"], context_text=item["context_text"], section_title=item["section_title"],
            clause_number=item["clause_number"], lexical_rank=item["lexical_rank"], dense_rank=item["dense_rank"],
            fused_score=item["fused_score"], rerank_score=item["rerank_score"],
            source_metadata=item["source_metadata"],
        )
        for index, item in enumerate(expanded, start=1)
    ]
    context_ms = int((perf_counter() - context_started) * 1000)
    candidate_trace = [{key: value for key, value in row.items() if key != "chunk_text"} for row in candidates]
    diagnostics = RetrievalDiagnostics(
        query=query,
        reranker_degraded=reranker_degraded,
        reranker_reason=reranker_reason,
        candidate_rows=candidate_trace,
        selected_rows=[{"chunk_id": str(row["chunk_id"]), "filename": row["filename"], "page_number": row["page_number"]} for row in expanded],
        excluded_rows=excluded,
        context_budget_tokens=_context_budget(settings, query.answer_shape),
        context_tokens=context_tokens,
        context_truncated=context_truncated,
    )
    return RetrievalResult(
        chunks,
        RetrievalTimings(
            embed_ms, lexical_ms, dense_ms, rerank_ms, context_ms,
            query_analysis_ms=query_analysis_ms,
            candidate_fusion_ms=candidate_fusion_ms,
            adjacent_candidates_ms=adjacent_candidates_ms,
            context_selection_ms=context_selection_ms,
            reranker_load_ms=reranker_load_ms,
            reranker_pair_build_ms=reranker_pair_build_ms,
            reranker_predict_ms=reranker_predict_ms,
            reranker_postprocess_ms=reranker_postprocess_ms,
        ),
        len(candidates),
        diagnostics,
    )


def hybrid_search(settings: Settings, question: str, limit: int | None = None, user_role: str = "authority") -> list[RetrievedChunk]:
    """Compatibility wrapper for the CLI; API routes call :func:`retrieve` directly."""
    return retrieve(settings, question, user_role, limit).chunks
