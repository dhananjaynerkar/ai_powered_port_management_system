# Corpus strategy — measured 2026-08-13

This report is based on the read-only run saved in
`artifacts/corpus-report/corpus.json`. It covered 50 PDFs, 1,504 pages,
80,675,595 bytes, and 3,624,944 characters extracted through PyMuPDF.

| Finding | Count | Ingestion decision |
|---|---:|---|
| Native-text PDFs | 23 | Initial native extraction and embedding |
| Scanned PDFs | 15 | Do not embed native text; send pages to OCR review |
| Hybrid PDFs | 3 | Preserve native pages; OCR only the image-only pages |
| Table-heavy PDFs | 8 | Hold for table-aware review before embedding |
| Exact duplicate | 1 | Store a duplicate relationship; do not re-embed |
| Image-only pages | 167 | OCR required before those pages can be evidence |
| Table-signal pages | 399 | Preserve table headers and rows as one evidence unit |
| Repeated header/footer signal | 2 documents | Remove only after page-level comparison review |

The observed extraction-quality range is 0–100 (mean 67.62). The classifier is
diagnostic, not an assertion of legal or factual completeness. In particular,
the 18 scanned/hybrid documents are not eligible for native-text ingestion.

## Decisions

| Decision | Chosen strategy | Evidence | Alternative rejected for now |
|---|---|---|---|
| Parser | PyMuPDF first | It supplied usable native text for 23 PDFs | OCR-all would duplicate work and risks OCR errors on born-digital text |
| OCR | Page-level only for image-only/hybrid pages | 167 image-only pages; 15 scanned PDFs | Whole-document OCR would overwrite usable native text |
| Tables | Review/table-aware path | 399 pages triggered a table signal | Paragraph chunking can lose row/header relationships |
| Chunking | Page-anchored, paragraph-preserving, adaptive size | Page number is the citation anchor; target derives from each document's measured average page text | One global chunk size is not used |
| Deduplication | SHA-256 before extraction/embedding | One exact duplicate was found | Filename-only checks are unreliable |
| Retrieval | PostgreSQL FTS + pgvector cosine + RRF | Legal/policy material needs both exact terms and semantic recall | Dense-only search misses exact clauses/identifiers |
| Vector index | HNSW cosine | Low-latency incremental retrieval after ingestion | IVFFlat needs trained-list tuning against a populated corpus |

## Storage contract

The migration creates only the configured `rag` schema:

- `document`: immutable source identity, hash, classification, quality, and parser metadata.
- `document_page`: page text and page metadata.
- `chunk`: child evidence chunks with the exact child-page foreign key, full-text vector, ACL-ready roles, embedding, and model version.

Indexes are created for document/page ordering, full-text search, ACL roles, and
HNSW cosine retrieval. The schema requires `vector` and `pgcrypto` extensions.

## Known gates

1. A database role with permission to create the `rag` schema and extensions is
   required before migration.
2. A local embedding endpoint compatible with Ollama `/api/embed` is required
   before non-dry-run ingestion. Its actual vector dimension must equal the
   configured `PORTPROJECT_RAG_EMBEDDING_DIMENSIONS`.
3. OCR/table extraction is intentionally not substituted with guessed text.
   Those documents remain reviewable until an OCR engine and quality threshold
   are configured and validated on this corpus.

