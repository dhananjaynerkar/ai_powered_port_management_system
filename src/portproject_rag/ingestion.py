from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

import httpx
import pymupdf
from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg import connect, sql

from .inspection import PageProfile, PdfProfile
from .ocr import ocr_page
from .settings import Settings
from .strategy import Capabilities, decide_document


@dataclass(frozen=True, slots=True)
class IngestionResult:
    documents_inserted: int
    documents_skipped: int
    chunks_inserted: int
    duration_ms: int
    quarantined_documents: int = 0
    failed_documents: int = 0


INGESTION_STATES = frozenset({"indexed", "processing", "pending", "quarantined", "failed"})


def _clean_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", text)).strip()


def _json_safe(value: object) -> object:
    """PostgreSQL text/JSON cannot contain NUL; retain all other metadata."""
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _chunks(text: str, maximum_characters: int) -> Iterable[str]:
    """Keep paragraphs intact where possible; source page remains the citation anchor."""
    buffer = ""
    for paragraph in (item.strip() for item in text.split("\n\n")):
        if not paragraph:
            continue
        if buffer and len(buffer) + len(paragraph) + 2 > maximum_characters:
            yield buffer
            buffer = ""
        if len(paragraph) > maximum_characters:
            for start in range(0, len(paragraph), maximum_characters):
                if buffer:
                    yield buffer
                    buffer = ""
                yield paragraph[start : start + maximum_characters]
        else:
            buffer = f"{buffer}\n\n{paragraph}".strip()
    if buffer:
        yield buffer


def _embed_many(client: httpx.Client, settings: Settings, texts: list[str]) -> list[list[float]]:
    response = client.post(
        settings.embedding_endpoint.unicode_string(),
        json={"model": settings.embedding_model, "input": texts},
        timeout=settings.embedding_timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    embeddings = payload.get("embeddings")
    if not isinstance(embeddings, list) or len(embeddings) != len(texts):
        raise ValueError("Embedding endpoint did not return one embedding per input")
    if any(not isinstance(item, list) or len(item) != settings.embedding_dimensions for item in embeddings):
        raise ValueError("Embedding dimension differs from configured value")
    return embeddings


def _embed(client: httpx.Client, settings: Settings, text: str) -> list[float]:
    return _embed_many(client, settings, [text])[0]


def _set_document_state(cursor: Any, schema: sql.Identifier, document_id: object, state: str, reason: str | None = None) -> None:
    if state not in INGESTION_STATES:
        raise ValueError(f"Unsupported ingestion state: {state}")
    cursor.execute(
        sql.SQL("UPDATE {}.document SET ingestion_state = %s, ingestion_error = %s, updated_at = now() WHERE document_id = %s").format(schema),
        (state, reason, document_id),
    )


def _quarantine_reason(extraction_strategy: str | None, empty_reason: str | None) -> str:
    """Return an observable reason when extraction produced no indexable text."""
    if empty_reason:
        return empty_reason
    if extraction_strategy == "OCR_REQUIRED":
        return "OCR_PRODUCED_NO_USABLE_TEXT"
    return "NO_USABLE_TEXT_AFTER_EXTRACTION"


def ingest(settings: Settings, profiles: list[PdfProfile], dry_run: bool = False) -> IngestionResult:
    """Ingest profiles while keeping every document in an explicit state."""
    started = perf_counter()
    eligible = [profile for profile in profiles if profile.duplicate_of is None and profile.pages]
    if dry_run:
        return IngestionResult(0, len(profiles) - len(eligible), 0, int((perf_counter() - started) * 1000))
    inserted_documents = skipped_documents = inserted_chunks = 0
    quarantined_documents = failed_documents = 0
    schema = sql.Identifier(settings.schema_name)
    with connect(settings.database_url.unicode_string()) as connection, httpx.Client() as client:
        register_vector(connection)
        with connection.cursor() as cursor:
            capabilities = Capabilities.detect()
            for profile in eligible:
                cursor.execute(
                    sql.SQL("SELECT document_id, ingestion_state FROM {}.document WHERE file_sha256 = %s").format(schema),
                    (profile.sha256,),
                )
                existing = cursor.fetchone()
                if existing and existing[1] == "indexed":
                    skipped_documents += 1
                    continue
                metadata = json.dumps(_json_safe({"pdf_version": profile.pdf_version, "title": profile.title, "author": profile.author,
                                                  "producer": profile.producer, "issues": profile.issues}), ensure_ascii=False)
                if existing:
                    document_id = existing[0]
                    # Reprocessing a non-indexed document is safe because any
                    # partial page writes are removed before the new attempt.
                    cursor.execute(sql.SQL("DELETE FROM {}.document_page WHERE document_id = %s").format(schema), (document_id,))
                    cursor.execute(sql.SQL("""UPDATE {}.document
                        SET source_path = %s, original_filename = %s, file_size_bytes = %s, page_count = %s,
                            classification = %s, extraction_strategy = %s, extraction_quality = %s,
                            source_metadata = %s::jsonb, ingestion_state = 'processing', ingestion_error = NULL, updated_at = now()
                        WHERE document_id = %s""").format(schema),
                        (profile.path, profile.filename, profile.file_size_bytes, profile.pages,
                         profile.classification, profile.extraction_strategy, profile.extraction_quality, metadata, document_id),
                    )
                else:
                    cursor.execute(
                        sql.SQL("""
                            INSERT INTO {}.document (
                                source_path, original_filename, file_sha256, file_size_bytes, page_count,
                                classification, extraction_strategy, extraction_quality, source_metadata, ingestion_state
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, 'processing')
                            RETURNING document_id
                        """).format(schema),
                        (profile.path, profile.filename, profile.sha256, profile.file_size_bytes, profile.pages,
                         profile.classification, profile.extraction_strategy, profile.extraction_quality, metadata),
                    )
                    document_id = cursor.fetchone()[0]
                    inserted_documents += 1
                # Persist document identity before external extraction/embedding work.
                # Subsequent page writes are independently atomic and retries
                # can distinguish processing from a finished index.
                connection.commit()
                chunk_index = 0
                pages_inserted = 0
                decisions = {decision.page_number: decision for decision in decide_document(profile, capabilities)}
                empty_reason = None
                try:
                    with pymupdf.open(Path(profile.path)) as source:
                        for page_number, page in enumerate(source, start=1):
                            decision = decisions[page_number]
                            page_profile = next(item if isinstance(item, PageProfile) else PageProfile(**item) for item in profile.page_profiles if (item.page_number if isinstance(item, PageProfile) else item["page_number"]) == page_number)
                            page_text = _clean_text(page.get_text("text"))
                            method = decision.selected.extraction_method
                            ocr_confidence = None
                            ocr_error = None
                            if method == "TESSERACT":
                                ocr = ocr_page(Path(profile.path), page_number)
                                page_text, ocr_confidence, ocr_error = _clean_text(ocr.text), ocr.mean_confidence, ocr.error
                            elif method == "PYPDF":
                                method = "PYMUPDF_NATIVE_FALLBACK"
                            # Native table extraction is evaluated in a separately budgeted
                            # diagnostic run. It previously exceeded the corpus-time budget;
                            # ingestion preserves the reliable raw page representation instead.
                            table = None
                            if not page_text:
                                empty_reason = ocr_error or empty_reason or (
                                    "OCR_PRODUCED_NO_USABLE_TEXT"
                                    if profile.extraction_strategy == "OCR_REQUIRED"
                                    else "NO_USABLE_TEXT_AFTER_EXTRACTION"
                                )
                                continue
                            target = min(
                                settings.chunk_max_characters,
                                max(settings.chunk_min_characters, round(profile.average_characters_per_page * 0.55)),
                            )
                            page_chunks = list(_chunks(page_text, target))
                            if not page_chunks:
                                empty_reason = empty_reason or "NO_USABLE_TEXT_AFTER_CHUNKING"
                                continue
                            # Complete the external model call before starting page writes.
                            # A timeout therefore leaves no idle PostgreSQL transaction.
                            embeddings: list[list[float]] = []
                            for start in range(0, len(page_chunks), settings.embedding_batch_size):
                                texts = page_chunks[start : start + settings.embedding_batch_size]
                                embeddings.extend(_embed_many(client, settings, texts))
                            cursor.execute(
                                sql.SQL("""
                                    INSERT INTO {}.document_page (
                                        document_id, page_number, extracted_text, extraction_method, extraction_quality, page_metadata
                                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb) RETURNING page_id
                                """).format(schema),
                                (document_id, page_number, page_text, method, page_profile.extraction_quality_score,
                                 json.dumps({"width": page.rect.width, "height": page.rect.height, "strategy": decision.selected.strategy_id, "fallback": decision.fallback.strategy_id if decision.fallback else None, "ocr_confidence": ocr_confidence, "table_representation": table.representation if table else ("RAW_PAGE_CONTEXT" if decision.selected.table_method != "NONE" else None)})),
                            )
                            page_id = cursor.fetchone()[0]
                            for text, embedding in zip(page_chunks, embeddings, strict=True):
                                cursor.execute(
                                    sql.SQL("""
                                        INSERT INTO {}.chunk (
                                            document_id, page_id, chunk_index, chunk_type, chunk_text, token_estimate,
                                            metadata, embedding, embedding_model
                                        ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                                    """).format(schema),
                                    (document_id, page_id, chunk_index, "paragraph", text, max(1, len(text) // 4),
                                     json.dumps({"page_number": page_number, "strategy": decision.selected.strategy_id, "fallback": decision.fallback.strategy_id if decision.fallback else None, "table_representation": table.representation if table else ("RAW_PAGE_CONTEXT" if decision.selected.table_method != "NONE" else None)}), Vector(embedding), settings.embedding_model),
                                )
                                chunk_index += 1
                                inserted_chunks += 1
                            pages_inserted += 1
                            connection.commit()
                    if chunk_index > 0 and pages_inserted > 0:
                        _set_document_state(cursor, schema, document_id, "indexed")
                    else:
                        _set_document_state(cursor, schema, document_id, "quarantined", _quarantine_reason(profile.extraction_strategy, empty_reason))
                        quarantined_documents += 1
                    connection.commit()
                except Exception as exc:
                    connection.rollback()
                    _set_document_state(cursor, schema, document_id, "failed", type(exc).__name__)
                    connection.commit()
                    failed_documents += 1
        connection.commit()
    return IngestionResult(inserted_documents, skipped_documents + (len(profiles) - len(eligible)), inserted_chunks, int((perf_counter() - started) * 1000), quarantined_documents, failed_documents)
