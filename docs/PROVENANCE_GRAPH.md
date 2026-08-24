# Provenance graph

The committed document has reliable document → page → chunk → embedding lineage.
Every stored page has strategy metadata and every chunk has page, strategy,
fallback, embedding model, and embedding timestamp. Retrieval lineage cannot
be evaluated until ingestion completes.
