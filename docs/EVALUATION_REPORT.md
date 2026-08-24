# Evaluation report — 2026-08-13 (historical baseline)

> **Historical scope:** This report predates the currently configured database
> and indexed corpus. It must not be used as a current RAG-readiness result.
> Current service health is `/health/ready`; current operational limits and
> validation scope are documented in [Operations](OPERATIONS.md) and
> [Audit](AUDIT_2026-08-24.md).

Completed: page-level inspection of the source corpus, compilation, and unit tests. Not completed: live database ingestion and retrieval evaluation, because `.env` is absent and no authorized `portproject` connection is configured.

The adaptive run generated one decision per observed page using current local capabilities. OCR, table extraction, and alternate-parser capabilities were all absent, so unavailable work is quarantined rather than invented.

| Metric | Result | Reason |
|---|---:|---|
| Source PDFs inspected | 50 | Read-only corpus run |
| Native/vector ingestion | Not run | Database configuration missing |
| OCR ingestion | Not run | No local OCR provider |
| Recall@5, MRR, citation accuracy | Not measurable | No stored corpus/evaluated queries |

Future evaluation must use reviewed real document/page expectations and calculate Recall@5, MRR, and citation-page accuracy from live results. Placeholder questions are not evidence of retrieval quality.
