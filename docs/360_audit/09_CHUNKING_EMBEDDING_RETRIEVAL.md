# Chunking, embedding, and retrieval audit

## Chunking

The implementation is page-anchored, character-bounded chunking. Settings
provide chunk_min_characters (default 900) and chunk_max_characters (default
2200). The chunk stores document_id, page_id, chunk_index, chunk_type,
section_title, clause_number, token_estimate, metadata, and ACL roles.

This is not proven to be semantic recursive chunking, sentence-transformer
token-window chunking, or a table-aware hierarchical chunker. Page lineage is
preserved. Headings and clause metadata are retained only when extraction logic
identifies them. Header/footer removal and table fidelity are not guaranteed.

## Embedding

Settings default to local Ollama bge-m3 at /api/embed with 1024 dimensions.
ingestion validates the returned embedding shape before persistence. Batch and
timeout settings are bounded. Storage uses pgvector vector(1024) and an HNSW
cosine index.

## Retrieval

retrieval.py computes a query embedding, then executes:

1. lexical full-text candidate ranking with simple configuration;
2. dense cosine candidate ranking;
3. ACL condition cardinality(a.acl_roles)=0 or current role membership;
4. candidate union and reciprocal-rank fusion;
5. optional CrossEncoder reranking;
6. parent context window and character/token budget assembly.

Candidate limits are controlled by rerank_candidate_count and retrieval
settings; RRF uses configured rrf_k.

## Recall/precision risks

Recall may be lost through low-quality extraction, too-small candidate limits,
exact lexical tokenization, absent metadata filters, and scanned/table pages
that are quarantined. Precision may be lost when generic chunks score highly,
parent context adds neighboring noise, or source wording is ambiguous.

## Metrics

The API returns retrieval and generation timings and candidate_count. Recall,
MRR, NDCG, citation faithfulness, and answer relevance are NOT VERIFIED as
measured production metrics.

