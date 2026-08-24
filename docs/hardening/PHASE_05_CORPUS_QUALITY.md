# Phase 5 — corpus quality and ingestion-state closure

Status: **COMPLETE — the observed pending scan is explicitly quarantined;
indexed-corpus invariants are green.**

Completed: 2026-08-25  
Scope: the existing local `portproject` application schema and the 50-PDF
source-corpus inspection report. No retrieval model or embedding configuration
was changed. No source PDF was copied into this repository.

## Boundary and evidence

The corpus inspection report was generated from the local source directory and
is not a production data artifact. The live application database was queried
read-only for diagnosis and was changed only by the explicit Phase 5 migration
and the targeted retry described below.

| Evidence | Observed result |
|---|---|
| Source-corpus profiles | 50 PDF profiles in the inspection report; duplicate profiles are not inserted as separate application documents |
| Application document rows | 49 rows: 48 indexed and one non-indexed source document |
| Pending document before retry | `TR 198of 66.pdf`, 2 pages, `SCANNED`, `OCR_REQUIRED`, extraction quality 0 |
| Source file | Exists locally at `C:\Users\15dha\OneDrive\Desktop\data\TR 198of 66.pdf`; it is not tracked by Git |
| Supported capabilities | Tesseract executable detected at `C:\Program Files\Tesseract-OCR\tesseract.exe` with `eng` and `osd`; alternative parser and table extractor were also detected |
| OCR attempt | Both pages were rendered and passed through the supported Tesseract path; both returned zero usable characters without an OCR exception |
| Visual check | The two pages are scanned historical pages with visible source content, not safely indexable from the returned OCR result |

The direct OCR result is the reason for the state decision. The system does
not infer text, mark the file ready, or create unsupported citations from the
page image.

## State model

Every application document now has an explicit state and optional reason:

| State | Meaning | UI/API treatment |
|---|---|---|
| `processing` | Identity exists and extraction/embedding work is in progress | Visible as processing; never counted as ready |
| `indexed` | At least one extracted page and chunk set completed with embeddings | Counted in ready metrics and retrieval scope |
| `pending` | Existing row has no completed index and still needs an operator retry | Visible as pending; not searchable |
| `quarantined` | The supported path completed but could not produce reliable indexable content | Visible with the reason; not searchable |
| `failed` | A processing or embedding exception was captured | Visible with the exception class; not searchable |

The state and reason are exposed through `pms_doc.document_record`, the corpus
state API, the document list API, and the assistant document context. Header
readiness now distinguishes indexed, processing, pending, quarantined, and
failed counts instead of presenting every document as ready.

## Processing performed

1. Added an idempotent migration for `rag.document.ingestion_state` and
   `rag.document.ingestion_error`.
2. Backfilled existing rows deterministically: rows with chunks became
   `indexed`; rows without chunks became `pending`.
3. Retried the observed non-indexed profile with the currently supported
   extraction and embedding pipeline.
4. The retry produced no usable OCR text, so the document was set to:

   ```text
   state:  quarantined
   reason: OCR_PRODUCED_NO_USABLE_TEXT
   ```

   Its page, chunk, and embedding counts remain zero. This is intentional and
   prevents unsupported retrieval or fabricated page citations.

5. A retry is safe: non-indexed documents remove any partial page/chunk rows,
   reset to `processing`, and then either finish as `indexed`, become
   `quarantined`, or record `failed` with an exception class.

## Live post-retry inventory

The values below were queried after migration and targeted retry:

| Metric | Value |
|---|---:|
| Indexed documents | 48 |
| Indexed extracted pages | 1,474 |
| Indexed chunks | 3,399 |
| Indexed embeddings | 3,399 |
| Pending documents | 0 |
| Processing documents | 0 |
| Quarantined documents | 1 |
| Failed documents | 0 |

The source physical page count is retained as provenance. The API's `pages`
metric counts persisted extracted pages (1,474); two physically blank or
non-content pages in otherwise indexed PDFs are not written as empty searchable
pages. The quality invariants therefore assert that each indexed document has
extracted pages and chunks, and that each persisted page has chunks, rather than
treating a physically blank PDF page as searchable content.

## Invariants verified

The corpus-state API now evaluates these conditions over `indexed` documents:

- every indexed document has at least one extracted page;
- every indexed document has at least one chunk;
- every persisted indexed page has a chunk;
- every indexed chunk has an embedding;
- every indexed chunk has a positive page number and ACL metadata;
- every indexed embedding has the configured 1024 dimensions.

Post-retry result: **all six invariant counts are 0**. The retrieval model,
`bge-m3` embedding model, and `vector(1024)` database contract were not
changed.

## Tests and validation

Added/updated checks cover:

- explicit ingestion-state/reason migration SQL;
- scanned-page strategy selection when OCR is available or unavailable;
- explicit `OCR_PRODUCED_NO_USABLE_TEXT` quarantine reasoning;
- live evaluation restricted to `indexed` state;
- the live corpus state and zero-invariant contract.

Validation completed for this phase:

- `ruff check src tests` — passed;
- Python bytecode compilation — passed;
- focused corpus, strategy, migration, and live-corpus tests — passed after
  the final patch;
- frontend production build — passed (`tsc` and Vite build);
- database migration — passed against local `portproject`;
- targeted corpus retry — completed with 1 quarantine and 0 failures;
- post-retry state/invariant query — passed with all six counts at 0.

## Remaining, explicit follow-up

The quarantined PDF needs a higher-quality OCR path (for example, image
pre-processing or an approved alternative OCR engine) before it can be
indexed. That is an extraction-capability change, not a reason to weaken the
quality gate. Phase 5 stops here; no Phase 6 work is started automatically.
