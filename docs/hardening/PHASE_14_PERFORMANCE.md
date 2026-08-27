# Phase 14 — Performance Baseline and Targeted Optimization

Date: 2026-08-26 (acceptance re-check)  
Project: `portproject_rag`  
Status: **PARTIAL — acceptance read/calculation baselines are current; RAG reliability/quality-preserving optimization and a safe query-plan clone remain open**

## Current acceptance re-check (2026-08-26)

The measurements below were run after loading the private acceptance environment and checking the acceptance sentinel. The API was isolated on `127.0.0.1:8016`; the operational `portproject` database and its API were not used for these measurements.

Acceptance safety evidence:

- `current_database() = portproject_acceptance` and the fixture check reported `acceptance/1`.
- The acceptance corpus contained 4 documents, 4 pages, 4 chunks, and 4 vectors, with no pending, processing, quarantined, or failed documents.
- The acceptance tender path was `tests/runtime/tender/tender_workflows.json`, separate from operational storage.
- The fixture was reset after the agenda-transition and complete-RAG probes, and the final fixture check passed.
- No credentials, session cookies, tokens, password hashes, or database URLs were printed.

### Current sequential measurements

Each HTTP row has five warm samples after the acceptance API was ready. p95/p99 are interpolated and are directional at this sample count. Billing and tender rows call their deterministic services directly to avoid creating chat/audit rows; the agenda transition and complete-RAG probes were run against acceptance fixtures and then reset.

| Operation | Warm p50 (ms) | Warm p95 (ms) | Warm p99 (ms) | Status | Evidence note |
|---|---:|---:|---:|---|---|
| `/health` | 4.47 | 9.34 | 10.23 | PASS | 5/5 HTTP 200 |
| `/health/ready` | 49.32 | 173.85 | 174.81 | PASS | 5/5 HTTP 200; `rag_ready=true` |
| Public corpus | 48.01 | 132.27 | 148.94 | PASS | 5/5 HTTP 200 |
| Dashboard metrics | 177.12 | 199.44 | 200.27 | PASS | 5/5 authenticated HTTP 200 |
| Tenant first page (25 rows) | 76.10 | 77.55 | 77.61 | PASS | 5/5 authenticated HTTP 200 |
| Tenant filtered query (`Acceptance`) | 87.74 | 187.08 | 188.13 | PASS | 5/5 authenticated HTTP 200 |
| Corpus state | 134.90 | 425.38 | 461.03 | PASS | 5/5 authenticated HTTP 200 |
| Document list | 183.79 | 186.05 | 186.28 | PASS | 5/5 authenticated HTTP 200 |
| Agenda list | 643.76 | 928.96 | 963.70 | PASS | 5/5 authenticated HTTP 200 |
| Agenda detail | 301.30 | 407.32 | 408.71 | PASS | 5/5 authenticated HTTP 200 |
| Billing prediction (direct service) | 44.62 | 154.54 | 155.24 | PASS | 5/5 deterministic acceptance inputs |
| Tender calculation (direct service) | 0.43 | 8.28 | 9.84 | PASS | 5/5 deterministic acceptance inputs |
| Agenda transition `DO_DRAFT → SUBMITTED_TO_NO` | 188.60 | — | — | PASS | one safe acceptance mutation; reset immediately afterward |

### Current controlled read concurrency

Four workers were used only for read paths. These are local probes, not capacity claims.

| Operation | Requests | p50 (ms) | p95 (ms) | p99 (ms) | Statuses |
|---|---:|---:|---:|---:|---|
| Public corpus | 20 | 50.27 | 157.07 | 160.24 | 200 only |
| Readiness | 20 | 49.23 | 149.39 | 155.78 | 200 only |
| Dashboard metrics | 12 | 93.21 | 304.41 | 305.93 | 200 only |
| Tenant first page | 12 | 85.81 | 234.88 | 281.87 | 200 only |

All measured non-RAG acceptance paths stayed below the local targets defined below, including the agenda list at a directional p95 of 928.96 ms against a 1,000 ms target.

### Current RAG observation

One complete acceptance RAG call returned HTTP 200 in 25,329 ms with `citation_valid=true`, three candidates/sources, embedding 459 ms, lexical retrieval 24 ms, dense retrieval 2 ms, reranking 352 ms, context assembly 148 ms, generation 24,013 ms, and citation validation 1 ms. A second consecutive call returned HTTP 503 after approximately 25.95 seconds. This is not enough successful data for a p95/p99 claim and is recorded as a reliability gap, not hidden as a passing performance result. A standalone fresh-process retrieval probe also terminated in a native runtime access violation during reranker loading, so no fresh-process cold RAG number is claimed from that probe.

No RAG model, reranker, candidate count, output budget, timeout, or prompt was changed. The observed model-stage behavior needs a paired quality/latency decision before optimization.

## Historical operational baseline scope (2026-08-25)

The remainder of this document preserves the earlier operational read-only baseline for comparison. It is not used as current acceptance evidence. The current acceptance evidence is the section above.

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

## Current regression gate after the acceptance re-check

- Acceptance fixture reset/check — **PASS**; final output was `ACCEPTANCE FIXTURE READY` with `portproject_acceptance` and `acceptance/1`.
- Acceptance API `/health/ready` before shutdown — **PASS**; HTTP 200, `rag_ready=true`, 4 documents, 4 pages, 4 chunks, and 4 vectors.
- Full Python suite — **PASS**, 64 passed, 27 skipped.
- Ruff — **PASS**, `ruff check src tests`.
- Frontend production build — **PASS**, TypeScript and Vite build completed successfully.
- No source optimization was applied in this re-check, so no before/after code-change claim is made.

### Phase result

**PARTIAL.** The acceptance baseline and controlled read concurrency are reproducible and below the defined local targets for non-RAG paths. The RAG path has one successful cited response but a consecutive 503 and a fresh-process native reranker-load failure, so generation/retrieval p95/p99 and a safe optimization cannot honestly be marked complete. No approved clone exists for `EXPLAIN (ANALYZE, BUFFERS)`, and no optimization was applied without paired quality evidence.

Phase 15 was not started.
