# Retrieval evaluation

No live retrieval experiment is possible yet: the project `.env` is absent, so the `portproject` schema has not been migrated and no embeddings/chunks exist. The adaptive query planner was unit-tested for normal semantic and relationship queries; it suppresses graph traversal while graph evidence is absent.

Recall@5, MRR, precision, citation accuracy, and vector-only versus hybrid comparisons remain **not measured**, not zero and not successful. They require a reviewed query set with real document/page expectations after ingestion.
