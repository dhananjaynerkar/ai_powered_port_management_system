# Implementation audit — historical baseline

> **Historical scope:** This report describes the early pre-database audit. Its
> statements about a missing `.env`, unavailable corpus storage, and unmeasured
> retrieval are no longer the current runtime state. Use
> [Architecture](ARCHITECTURE.md), [Operations](OPERATIONS.md), and the
> [2026-08-24 audit](AUDIT_2026-08-24.md) for the present implementation and
> deployment risks. The observations below are retained as evidence of the
> original extraction baseline.

## Current architecture

PyMuPDF profiles PDFs and pages, emits JSON/CSV, and records SHA-256 duplicates. The loader creates isolated `rag.document`, `rag.document_page`, and `rag.chunk` tables with FTS, ACL GIN, and HNSW indexes. Retrieval combines FTS and cosine search using reciprocal-rank fusion. The embedding endpoint is local and model dimension checked at response time.

## Findings

| Priority | Finding | Evidence and recommendation |
|---|---|---|
| Historical blocker | No configured database URL | At the time of this audit, `.env` was absent and migration, insertion, and retrieval evaluation could not run. This is not a current readiness statement. |
| Critical | No local OCR engine | Tesseract and `pytesseract` are unavailable. Scanned pages must remain un-ingested rather than become empty evidence. |
| High | Original gate was document-level | Page classification now exists; ingestion still needs a validated OCR provider. |
| High | Table signal is heuristic | `pdfplumber`, Camelot, and Tabula tooling are unavailable; table rows are not represented. |
| High | Chunks lack headings/sections | Native chunks preserve page lineage but do not parse hierarchy or remove headers/footers. |
| Medium | HNSW has no measured query plan | Benchmark after storage before changing the index. |
| Medium | CLI does not apply ACL scope | The schema is ACL-ready; do not expose this local tool to untrusted users. |

## Strengths

Source PDFs are never modified; configuration does not hardcode a password; exact duplicate files are prevented; and citations use the matched child page.
