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
  -> role ACL filtering (before RRF and reranking)
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

`guardrails.py` rejects invalid/overlong questions before retrieval. The lexical
and dense candidate queries apply `chunk.acl_roles`: an empty array is
available to portal roles; a non-empty array requires the current role. This
filter is applied before reciprocal-rank fusion and CrossEncoder reranking.
The generation prompt is then built from the selected context, and returned
source metadata is page-anchored. Citation validation determines
`citation_valid`; a response without retrieved evidence is not presented as a
grounded answer.

The context-expansion boundary is ACL-aware as well. `_adjacent_page_candidates`
and `_expand_context_with_metadata` join `chunk_acl` and require either a
public row (`acl_roles` is empty) or the current role before admitting an
adjacent/parent chunk. The Phase 08 acceptance fixture now creates an
acceptance-only document whose neighbouring pages are restricted to another
role; both page-neighbour and parent/context expansion exclude those rows.
Thus the security boundary is before reranking for primary candidates and
before model context assembly for expanded rows. This does not make the model
an authorization boundary: citations are still validated against the final
authorized result set.

The same source structure is used by private chat and official agenda messages.
Agenda AI queries run an ownership check before retrieval so read-only
participants cannot add to an official thread.

## Capacity boundary

On the supported local Windows profile, the API runs one worker and wraps the
complete retrieval/rerank/generation path in a process-local bounded gate. One
heavy pipeline is active at a time and one additional request may wait for up
to 60 seconds. A full or expired queue returns a safe capacity-busy response;
it is not reported as a retrieval or citation failure. The gate does not cover
non-RAG routes and does not alter retrieval limits, reranker behavior, context
selection, or model quality. Its state is exposed only as safe counts in
`/health/ready` and answer telemetry.

The current host's measured RAM pressure means this is a local-demo envelope,
not a multi-user or production capacity guarantee. Normal and acceptance APIs
are intentionally mutually exclusive on the development laptop so their
process-local model state cannot compete for the same memory.

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
- Phase 08 ACL evidence is fixture-scoped. The mixed-ACL context-expansion
  test proves the implemented database boundary for the tested paths; it does
  not claim that unrelated, future retrieval paths are automatically covered.
- The golden evaluation set and baseline metrics are maintained in the Phase 06
  and Phase 07 reports; no unverified quality percentage is claimed here.
