# Final architecture

```text
PDF source -> SHA-256 discovery -> page-level quality/classification
-> candidate extraction/table/chunk strategies -> selected strategy + fallback
-> native text when usable / OCR-required quarantine when no capability exists
-> table-review signal -> page-anchored chunks -> local embeddings
-> rag.document, document_page, chunk -> FTS + cosine -> RRF -> page citation
```

The next extension points are a local OCR adapter emitting page text and confidence, and a table adapter emitting structured table chunks. Neither may replace good native text. Graph RAG is **not justified**: the measurable gaps are extraction, table representation, and baseline retrieval evaluation.
