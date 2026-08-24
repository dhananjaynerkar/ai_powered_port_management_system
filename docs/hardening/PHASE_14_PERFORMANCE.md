# Phase 14 — Performance Baseline and Targeted Optimization

Date: 2026-08-25  
Project: `portproject_rag`  
Status: **PARTIAL — baselines complete; measured RAG bottlenecks require a quality/infra decision before optimization**

## Scope and safety boundary

This phase measured read-only application paths and pure calculation paths. No chat, agenda, workflow, billing, tender, or document rows were written by the benchmark.

- PostgreSQL remained running and the live `portproject` database was used only for read-only measurements.
- Ollama remained running during the measurements. The idle `qwen3.5:4b` model was unloaded after the benchmark only to free memory so the project API could restart; the Ollama service and model files were not removed.
- `EXPLAIN (ANALYZE, BUFFERS)` was **not** run because no approved safe database clone exists.
- Agenda transition was **not** benchmarked because it mutates live workflow state and no disposable workflow fixture is available.
- No credentials were created, guessed, submitted, or printed.

## Runtime conditions

| Item | Observed condition |
|---|---|
| OS/runtime | Windows local development runtime |
| CPU | 11th Gen Intel Core i5-1135G7 @ 2.40 GHz, 8 logical processors |
| RAM | 16,805,027,840 bytes reported (~15.7 GiB) |
| Python / Node | Python 3.13.14 / Node v22.22.3 |
| API/UI | API `127.0.0.1:8001`, Vite UI `127.0.0.1:5173` |
| Database | PostgreSQL `portproject`, schema `rag` |
| Local models | `bge-m3`, `qwen3.5:4b`, local BGE reranker `BAAI/bge-reranker-v2-m3` on CPU |
| Indexed corpus | 48 documents, 1,474 pages, 3,399 chunks, 3,399 vectors, 1 quarantined document, 0 pending/processing/failed |
| Retrieval request | `What are the key conditions for a port land lease?`, role `authority`, limit 4 |
| Measurement method | `time.perf_counter()`, direct read-only service calls and HTTP calls; cold means first call in a fresh Python process/service state, warm means repeated calls in the same process |

## Local/internal SLO targets

These are engineering targets for this CPU-only local/internal deployment, not production commitments:

| Operation | Target |
|---|---:|
| Liveness `/health` | warm p95 < 250 ms |
| Readiness `/health/ready` | warm p95 < 500 ms sequential; < 750 ms under 4-worker read-only load |
| Dashboard metrics | warm p95 < 1,000 ms |
| Tenant first page / filtered query | warm p95 < 1,000 ms |
| Corpus state | warm p95 < 1,000 ms |
| Agenda list/detail | warm p95 < 1,000 ms |
| Billing prediction | warm p95 < 1,000 ms after model load |
| Tender calculation | warm p95 < 250 ms |
| Retrieval without generation | warm p95 < 5,000 ms |
| Complete grounded RAG answer | warm p95 < 30,000 ms for an interactive local answer |

## Sequential baseline results

For samples of five, p50/p95/p99 are interpolated percentiles. For samples of three, p95/p99 are directional only. Complete RAG had two warm samples; p95/p99 are therefore not statistically meaningful and are reported as a range.

| Operation | Cold ms | Warm samples / summary | Target result |
|---|---:|---|---|
| `/health` HTTP | 9.65 | 2.64–5.54; p50 3.10, p95 5.06, p99 5.45 | PASS |
| `/health/ready` HTTP | 156.78 | 57.32–170.97; p50 166.19, p95 170.20, p99 170.82 | PASS |
| Public corpus HTTP | 53.03 | 52.61–165.79; p50 61.97, p95 163.68, p99 165.37 | PASS |
| Dashboard land metrics (read-only) | 95.02 | 90.19–203.41; p50 202.10, p95 203.34, p99 203.40 | PASS |
| Tenant first page (25 rows) | 61.82 | 56.65–179.05; p50 59.36, p95 166.08, p99 176.50 | PASS |
| Tenant filtered query (`Port`) | 103.83 | 102.43–208.70; p50 105.43, p95 198.37, p99 206.63 | PASS |
| Corpus state | 335.61 | 129.38–256.32; p50 135.47, p95 244.24, p99 253.95 | PASS |
| Agenda list (read-only fixture) | 102.03 | 93.35–101.40; p50 93.98, p95 100.66, p99 101.25 | PASS |
| Agenda detail (read-only fixture) | 141.86 | 134.25–357.86; p50 240.57, p95 346.13, p99 355.51 | PASS |
| Billing prediction from approved-form inputs | 244.19 | 41.51–47.99; p50 46.16, p95 47.88, p99 47.97 | PASS after model load |
| Tender calculation | 1.08 | 0.34–0.46; p50 0.35, p95 0.43, p99 0.45 | PASS |

## RAG stage baseline

| Stage | Measured result |
|---|---:|
| Retrieval cold total | 39,139 ms |
| Retrieval warm total | 13,147–13,662 ms; p50 13,602 ms |
| Embedding warm stage | ~909 ms in the final sample |
| Lexical PostgreSQL stage | ~9 ms |
| Dense pgvector PostgreSQL stage | ~38 ms |
| Reranking warm stage | ~12,623 ms |
| Context assembly | ~42 ms |
| Candidates / selected chunks | 8 candidates / 1 selected chunk |
| Complete RAG cold | 148,819 ms |
| Complete RAG warm | 119,061–121,062 ms; two-sample p50 ~120,061 ms |
| Generation warm stage | 100,076–101,836 ms |
| Citation validation | 0 ms in both warm samples |
| Grounding result | 1 cited source and `citation_valid=true` on every measured answer |

### Bottleneck conclusion

The database retrieval stages are not the measured bottleneck. CPU reranking is approximately 12.6 seconds warm, and local generation is approximately 100–102 seconds warm. The complete answer is therefore about two orders of magnitude slower than the interactive target even though the answer remains grounded and citation-valid.

No model-size, model-switch, output-budget, reranker-candidate, or quality-affecting change was made. Such a change requires a paired quality benchmark and an explicit product/infra decision; optimizing it blindly would risk lowering grounded-answer quality.

## Controlled concurrency

Four workers were used against read-only paths. These are local stress probes, not capacity claims.

| Operation | Requests | p50 | p95 | Max | Status |
|---|---:|---:|---:|---:|---|
| Public corpus HTTP | 20 | 522 ms | 601 ms | 615 ms | PASS target |
| Readiness HTTP | 20 | 507 ms | 614 ms | 618 ms | PASS 750 ms concurrency target |
| Dashboard metrics direct | 12 | 129 ms | 210 ms | 219 ms | PASS |
| Tenant first page direct | 12 | 92 ms | 189 ms | 192 ms | PASS |

The dashboard and tenant read paths remain below the local 1-second target under this small read-only load. The readiness and public corpus endpoints are below the concurrency target but show expected connection/serialization overhead compared with sequential calls.

## UI/static delivery check

Vite responses were measured after the dev server was running:

| URL | First request | Warm range |
|---|---:|---:|
| `/` | 298 ms | 9–45 ms |
| `/authority/dashboard` | 91 ms | 9–14 ms |
| `/authority/documents` | 31 ms | 8–13 ms |

These are document-delivery timings only; authenticated data rendering was not claimed without an approved disposable browser account.

## Optimization decision

No source optimization was applied in Phase 14.

Reason: every measured non-RAG path already meets its local target, and the two RAG bottlenecks are quality-sensitive local model stages. A safe optimization requires:

1. a fixed RAG quality set with citation/grounding acceptance criteria;
2. paired latency and quality measurements for reranker/model alternatives;
3. a disposable or approved runtime for repeated concurrent generation tests;
4. a decision on whether CPU-only local latency is acceptable or whether inference hardware/model policy changes are permitted.

Changing the model, lowering retrieval candidates, disabling reranking, or reducing output tokens without that evidence would violate the phase objective.

## Query-plan boundary

No `EXPLAIN (ANALYZE, BUFFERS)` output is included. The only available database is the live `portproject` operational database, and the project has no approved clone or snapshot target for invasive execution plans. Sequential scans alone are not evidence sufficient to add indexes.

## Regression validation

- `.venv\Scripts\python.exe -m pytest -q` — 48 passed before the performance run.
- `ruff check src/portproject_rag/api.py tests/test_resilience_observability.py` — passed.
- `npm --prefix web run build` — passed.
- After the standalone reranker/generation benchmark, the project API restarted successfully on `127.0.0.1:8001`.
- Live recovery check: `/health` HTTP 200 with `X-Request-ID`; `/health/ready` HTTP 200 with `rag_ready=true`, 48 documents, 1,474 pages, 3,399 chunks, and 3,399 vectors.

## Remaining gaps and next decision

- Real authenticated dashboard/tenant/agenda transition HTTP timings need an approved disposable account/fixture. Direct read-only service timings are evidence for the database paths but not a substitute for a full browser trace.
- Database `EXPLAIN (ANALYZE, BUFFERS)` needs an approved safe clone.
- RAG latency needs a quality-preserving optimization decision. The current baseline should be treated as CPU-local and not as a production SLO.

Phase 15 was not started.
