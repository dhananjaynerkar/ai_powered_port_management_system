# Retrieval strategy

The query uses PostgreSQL full-text search and pgvector cosine similarity, fuses candidate ranks through configurable RRF, and returns the exact `document_page.page_number` attached to each chunk.

Reranking is not implemented. No local reranker is available and no baseline Recall@5/MRR exists to show that its added compute is justified. Apply scope/role predicates before exposing this local CLI to users.
