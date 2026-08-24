# RAG pipeline deep dive

## Actual pipeline

1. PDF discovery and SHA-256 identity in inspection/ingestion.
2. Page profile and extraction-quality classification.
3. Adaptive native/OCR/alternative/table strategy selection.
4. Page text preservation and page metadata.
5. Chunk creation with document/page lineage.
6. Local embedding through configured Ollama embedding endpoint.
7. Persistence in rag.document, rag.document_page, and rag.chunk.
8. Question guardrail validation.
9. Query embedding.
10. PostgreSQL lexical and pgvector dense candidate retrieval.
11. ACL filter on chunk ACL roles.
12. Reciprocal-rank fusion.
13. CrossEncoder reranking.
14. Parent-context assembly and token budget.
15. Local Ollama generation with citation instructions.
16. Citation identifier and factual-paragraph validation.
17. API payload with source title, filename, page, excerpt, ranks, scores, and
    timings.

## Configuration

Settings are typed in settings.py. Important controls include embedding model
and dimension, chunk bounds, retrieval limit, candidate multiplier, rerank
candidate count, RRF K, context token budget, output token budget, generation
timeout, citation retries, and query maximum length.

## Grounding controls

guardrails.validate_query blocks selected prompt-injection/destructive patterns,
limits input size, and rejects empty questions. generation validates citations
against retrieved source IDs and requires citation-bearing factual paragraphs
when evidence exists.

## Failure behavior

- No evidence: generation is not called.
- Missing local model: readiness is false or model selection returns an error.
- Reranker initialization failure: readiness is false.
- Unknown citations: answer is rejected/retried by generation flow.
- OCR unavailable for scanned pages: strategy records quarantine rather than
  silently embedding empty evidence.

## Not proven by the current code alone

- A quantitative faithfulness score.
- Recall/precision on a reviewed question set.
- Robust multilingual OCR quality.
- Authenticated cross-role UI acceptance.

