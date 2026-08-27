# RAG Performance Optimization Without Quality Regression

**Phase result: PARTIAL — safe improvements retained; quality and security gates pass.**

## Scope and safety

This phase changed only document-RAG telemetry, context selection, and evaluation tooling. It did not change RAG ACLs, workflow, billing, tender logic, the embedding model, the generation model, model quantization, or streaming semantics.

Normal-corpus profiling used read-only retrieval against `portproject`. Acceptance checks used the separate `portproject_acceptance` fixture and its `acceptance/1` sentinel. The operational database was not mutated.

## Frozen baseline

The prior final context certificate remains the quality baseline:

| Measure | Frozen value |
| --- | ---: |
| AnyHit@1 / @3 / @5 | 0.67 / 0.89 / 0.89 |
| EvidenceCoverage@5 | 0.85 |
| MRR / NDCG | 0.78 / 0.78 |
| Fact coverage | 10/10 |
| Complete-fact cases | 3/3 |
| Citation-valid generation cases | 9/9 |

The original RG-001 profile used four context sources and had a warm p50 of 32.927 s: reranking 9.142 s, prompt evaluation 17.280 s, and generation 22.489 s. Its prompt contained 1,251 evaluated tokens.

## Root cause and measured pipeline

The slow path was measured rather than assumed. Reranking and prompt evaluation dominated a warm direct-fact request; dense retrieval was negligible once embeddings were warm. Cold start also included CrossEncoder and model loading.

The implementation now separately reports query analysis, candidate fusion, adjacent-context lookup, reranker loading/pair construction/prediction/post-processing, context selection, prompt construction, and answer assembly. The reranker's public API does not expose tokenizer and transformer-forward timings independently, so both remain accurately represented by `reranker_predict_ms`.

The initial process topology showed the Qwen model (about 3.2 GB), BGE embedding model (about 1.2 GB), and CrossEncoder (about 2.0 GB) competing for a 15.65 GiB CPU host. Experiments ran with only one application pipeline active at a time. Ollama confirmed a 4,096-token Qwen context window.

## Retained change

The final context remains capped at four sources globally. For answer shapes that are safely single-source by contract, the selector now uses smaller, shape-specific limits:

| Answer shape | Sources | Context budget |
| --- | ---: | ---: |
| Direct fact | 1 | 256 tokens |
| Table | 1 | 350 tokens |
| List, comparison, multi-evidence, clarification | 4 | existing policy |

This preserves multi-document coverage where it is required and reduces prompt payload only where the reviewed contract permits it. The paired same-session replay of RG-001, RG-002, RG-008, and RG-011 kept all citations valid, including the no-evidence case.

### Final direct-fact profile (RG-001)

`artifacts/evaluation/rag_performance_final_rg001.json` was produced by four isolated, read-only repetitions after stopping the acceptance service. Every result was citation-valid.

| Warm metric | Four-source baseline | Final one-source context | Change |
| --- | ---: | ---: | ---: |
| End-to-end p50 | 32.927 s | 19.114 s | -41.9% |
| Rerank p50 | 9.142 s | 11.117 s | +21.6% |
| Prompt evaluation p50 | 17.280 s | 0.196 s | -98.9% |
| Generation p50 | 22.489 s | 6.488 s | -71.2% |
| Prompt tokens p50 | 1,251 | 464 | -62.9% |

The warm RG-001 objective is therefore met without weakening citation validation. The slower reranker in this repeat is treated as normal CPU variation; the retained change targets prompt/context cost, not reranker quality.

## Experiments and decisions

| Experiment | Result | Decision |
| --- | --- | --- |
| Reranker prefix 8 | Preserved frozen retrieval metrics and all mapped facts | Retained |
| Reranker prefix 6 | EvidenceCoverage@5 0.80; fact coverage 0.90; complete-fact 2/3 | Rejected |
| Reranker prefix 4 | Same quality regression as prefix 6 | Rejected |
| Shape-specific direct/table context | Frozen retrieval quality retained; 9/9 full replay citation-valid | Retained |
| Compact system instructions | Full replay was 8/9 citation-valid; RG-010 stopped at length and missed a required factual citation | Rejected; disabled by default |
| Reranker batch size 4 | Not measured: duplicate normal API topology appeared, so the run was cancelled | No change |
| Smaller/low-quantized generation model | Not justified after a safe structural improvement | No change |
| Conditional reranker bypass | No calibrated evidence supports it | No change |
| Concurrency/load test | A bounded two-request pipeline probe completed; broader HTTP load is intentionally not claimed | See final runtime certificate |
| Streaming | Buffered generation is required for citation validation | No change |

The full shape-context generator replay is a quality result, not a comparable global latency result: it ran under a different host heat/load condition and recorded a 101.639 s p50 across nine heterogeneous cases. It nevertheless returned 9/9 citation-valid answers with zero timeouts. No overall generation-latency claim is made from that non-paired replay.

## Configuration and compatibility

New settings preserve the pre-existing global default and make the optimizations explicit:

- `final_context_source_count_direct=1`
- `final_context_source_count_table=1`
- `context_token_budget_direct=256`
- `context_token_budget_table=350`
- `generation_compact_instructions=false`

API timing fields were extended compatibly; existing fields and routes remain available. Reranker batch size remains 8 and is used as a batch in the source implementation. The selected generation model remains `qwen3.5:4b` Q4_K_M; no model or quantization switch was made.

## Regression and runtime checks

| Check | Result |
| --- | --- |
| Acceptance guarded Phase 08/09 subset | 21 passed in 121.13 s |
| Acceptance reset/check | Passed; `portproject_acceptance`, sentinel `acceptance/1` |
| Full Python suite | 96 passed, 28 skipped |
| Ruff (`src`, `tests`, `scripts`) | Passed |
| React production build | Passed |
| Normal API `/health/ready` | Passed; `rag_ready=true`, 48 documents, 3,399 vectors |
| Operational `portproject` database modified | No |

## Remaining work and non-claims

This is not a claim that every answer shape now meets the 25 s stretch target. Multi-evidence questions deliberately retain their four-source policy, and the bounded two-request probe is not an HTTP load or queue-capacity certification. CPU reranking remains a material cost. Browser or streaming changes were not part of this phase.

The final runtime certificate records the bounded mixed-shape sample, the two-request probe, memory headroom, and the remaining limitations. Any capacity claim beyond that evidence should use an isolated host or a safely constrained load harness without adding a second application process or changing evidence policy.

## Reproducibility artifacts

- `artifacts/evaluation/rag_performance_baseline_rg001.json`
- `artifacts/evaluation/rag_performance_final_rg001.json`
- `artifacts/evaluation/rag_performance_rerank_prefix_8.json`
- `artifacts/evaluation/rag_performance_rerank_prefix_6.json`
- `artifacts/evaluation/rag_performance_rerank_prefix_4.json`
- `artifacts/evaluation/rag_performance_shape_context_retrieval.json`
- `artifacts/evaluation/rag_performance_shape_context_generation.json`
- `artifacts/evaluation/rag_performance_shape_context_ab.json`
- `artifacts/evaluation/rag_performance_prompt_compaction_ab.json`
- `artifacts/evaluation/rag_performance_final_generation.json`
- `artifacts/evaluation/rag_performance_mixed_sample.json`
- `artifacts/evaluation/rag_performance_rg004.json`
- `artifacts/evaluation/rag_performance_rg006.json`
- `artifacts/evaluation/rag_performance_rg008.json`
- `artifacts/evaluation/rag_performance_warm_shapes.json`
- `artifacts/evaluation/rag_concurrency_profile_memory.json`

The profiling and replay scripts are intentionally read-only and record answer hashes or evaluation artifacts rather than exposing additional raw operational data.
