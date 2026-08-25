# RAG system

**Status: CURRENT SOURCE OF TRUTH**

The portal is a local-first, evidence-constrained RAG system. It does not use a
cloud model fallback. Configuration is read from `Settings` in
`src/portproject_rag/settings.py` and `.env`.

## Ingestion pipeline

```text
PDF discovery
  -> page/profile inspection
  -> adaptive strategy selection
       native parser | OCR/Tesseract | alternative parser | bounded table extraction
  -> page text + extraction metadata
  -> provenance-preserving chunks
  -> local bge-m3 embeddings (default 1,024 dimensions)
  -> rag.document / document_page / chunk
```

The inspector and strategy modules classify quality before persistence. A page
that cannot be extracted reliably remains observable as pending, failed, or
quarantined; it is not marked indexed just to improve a dashboard number.

## Retrieval and answer pipeline

```text
question
  -> input guardrail and length validation
  -> query embedding
  -> PostgreSQL lexical candidates + pgvector cosine candidates
  -> role ACL filtering
  -> reciprocal-rank fusion (RRF)
  -> local CrossEncoder reranking
  -> parent/page context assembly
  -> local completion model
  -> citation validation
  -> answer, sources, timing, and chat persistence
```

Default model configuration is:

| Stage | Default |
| --- | --- |
| Embeddings | Ollama `bge-m3` |
| Completion | Ollama `qwen3.5:4b` |
| Reranker | `BAAI/bge-reranker-v2-m3` on CPU |
| Vector dimension | 1,024 |

The UI can request an available local completion model through
`/api/v1/local-llms`; the server still validates the request and logs the model
used. The fallback model is disabled by default.

## Evidence and guardrails

`guardrails.py` rejects invalid/overlong questions before retrieval. Retrieval
applies `chunk.acl_roles`: an empty array is available to portal roles; a
non-empty array requires the current role. The generation prompt is built from
retrieved context, and returned source metadata is page-anchored. Citation
validation determines `citation_valid`; a response without retrieved evidence
is not presented as a grounded answer.

The same source structure is used by private chat and official agenda messages.
Agenda AI queries run an ownership check before retrieval so read-only
participants cannot add to an official thread.

## Readiness states

`/health` means the API process and settings are alive. `/health/ready` reports
whether the configured corpus/model/reranker dependencies are usable. These are
different signals. A healthy API can correctly be not ready for RAG when
PostgreSQL, Ollama, the embedding model, or the reranker is unavailable.

## Known limitations

- Retrieval and generation latency depends on local CPU/GPU, Ollama model load,
  database size, and network loopback conditions.
- OCR/table extraction is optional and may leave a document pending or
  quarantined for review.
- Citation validation verifies returned evidence metadata; it is not a legal or
  business approval of the document content.
- The golden evaluation set and baseline metrics are maintained in the Phase 06
  and Phase 07 reports; no unverified quality percentage is claimed here.
