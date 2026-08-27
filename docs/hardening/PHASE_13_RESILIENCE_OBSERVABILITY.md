# Phase 13 — Failure, Resilience and Observability

Date: 2026-08-25  
Project: `portproject_rag`  
Scope: controlled local failure probes, safe readiness behavior, request observability, and failure audit coverage.  
Status: **PARTIAL — production dependency-failure exercise remains intentionally blocked**

## Boundary and evidence rules

- No PostgreSQL or Ollama process was stopped. PostgreSQL is the live `portproject` operational database and Ollama is shared local infrastructure; stopping either would not be an isolated disposable test.
- No credentials were created, guessed, submitted, or printed.
- No billing, tender, chat, workflow, or document rows were created or changed by the probes.
- Unavailable dependencies were simulated with loopback port `127.0.0.1:9`, temporary missing artifact paths, and in-process monkeypatches.
- The isolated acceptance API was restarted only to load the verified code change. It recovered on `127.0.0.1:8016` and returned healthy/readiness responses afterward.

## Baseline observed before the change

The source inspection and controlled probes established these gaps:

1. `/health` was a liveness response, but `/health/ready` called `_stats()` without a failure boundary. A database exception escaped as an unhandled application error instead of a stable HTTP 503 readiness payload.
2. Startup migration ran before the application state was initialized and before the lifespan yielded. A migration/database outage could prevent the API from exposing liveness/readiness at all.
3. API access logs were ordinary Uvicorn lines with no application request/correlation ID or duration fields.
4. Successful audit writes occurred after several mutations. If the separate audit connection failed, the user could receive a 500 after the business mutation had already committed.
5. RAG, billing, and tender failure paths did not consistently emit a semantic failure audit event. RAG failures were returned as 503s but were not audit-recorded.
6. The frontend showed “Document search is still preparing” for every readiness failure, including a database outage or unavailable local AI dependency.
7. A real unreachable PostgreSQL endpoint did not fail quickly enough during startup because the shared connection URLs had no bounded `connect_timeout`.

## Implemented changes

### API resilience and structured observability

Implemented in `src/portproject_rag/api.py` and `src/portproject_rag/settings.py`:

- Added bounded `X-Request-ID` handling. Safe IDs are echoed; unsafe/missing IDs are replaced with a generated UUID. Responses expose the ID for the local cross-origin UI.
- Added JSON structured request records containing only `event`, request ID, method, path, status code, duration, and safe exception type. Request bodies, passwords, session tokens, prompts, and document text are not logged.
- Added startup dependency records for PostgreSQL migration and RAG readiness failures. Raw exception messages are not returned as readiness state.
- Kept `/health` as liveness. It reports that the API process is alive without asserting database/RAG readiness.
- Hardened `/health/ready`: a PostgreSQL/statistics failure now returns HTTP 503 with:

  ```json
  {"status":"not_ready","rag_ready":false,"init_error":"database_unavailable","corpus":null}
  ```

- Startup migration failure now leaves the process able to expose liveness/readiness (`database_migration_failed`) rather than failing before the lifespan yields. The application remains not ready and does not claim a false success.
- Audit writes now include the current request ID when available. An audit-write failure is recorded as a structured `audit_write_failed` event and does not turn a previously committed business operation into a false 500.
- Added failure audit events for login failure, RAG query failure (private and workflow), billing forecast failure, and tender workflow creation/transition failure. Only event type, safe operation identifiers, lengths, and exception class are recorded.
- Added `database_connect_timeout_seconds` (default 5 seconds) and injects `connect_timeout` into the configured PostgreSQL URL when the operator has not supplied one. Existing database call sites therefore fail fast without a broad connection-wrapper rewrite.

### Frontend dependency state

Implemented in `web/src/main.tsx`:

- Readiness state now distinguishes:
  - `database_unavailable` → “Document search is temporarily unavailable. Retry when the service is ready.”
  - `rag_dependency_unavailable` → “Local AI dependencies are unavailable. Retry when they return.”
  - other not-ready states → “Document search is still preparing.”
- The composer remains disabled until readiness is restored; no fake answer or success state is created.

## Controlled failure results

| Scenario | Controlled result | API/UI implication | Status |
|---|---|---|---|
| Ollama/catalog unavailable | `ConnectError` from loopback port 9 | Model catalog path fails closed; no model is claimed available | PASS |
| Generation model/request unavailable | `ConnectError` from loopback port 9 | Generation exception propagates to the API failure boundary; no answer is persisted | PASS |
| Request timeout | Synthetic `httpx.ReadTimeout` | Timeout is distinguishable from a successful generation | PASS |
| Embedding model unavailable | `ConnectError` from loopback port 9 | Ingestion/retrieval embedding fails before any answer mutation | PASS |
| Reranker unavailable | Synthetic `RuntimeError` from reranker loader | Retrieval does not fabricate ranked evidence | PASS |
| PostgreSQL unavailable during readiness | Synthetic `_stats()` outage | `/health/ready` returns stable HTTP 503 and `database_unavailable` JSON | PASS |
| PostgreSQL unavailable at startup migration | Synthetic migration outage | Lifespan remains alive but not ready with `database_migration_failed` | PASS |
| Billing artifact unavailable | Temporary missing model artifact | Service raises `FileNotFoundError`; API maps it to “Billing forecast artifacts are not ready.” | PASS |
| Tender state/config unavailable | Temporary missing tender config | Service raises `TenderWorkflowError`; API maps it to a controlled 503/422 path | PASS |
| Frontend loses backend | No authenticated disposable browser fixture is available | Full authenticated UI exercise is not claimed; source review confirms workspace error state and composer-disabled readiness state | BLOCKED |
| Recovery after dependency returns | Live API restarted after verified source change; `/health` 200 and `/health/ready` 200 with `rag_ready=true` | Process/readiness recovery verified; actual PostgreSQL/Ollama stop-and-return remains untested | PARTIAL |

### Additional controlled probe after the Phase 13 hardening

The new regression test first failed because an unreachable URL had no timeout.
After the settings fix, the test passed and the acceptance API started with the
bounded URL. The acceptance API then returned `/health` HTTP 200 and
`/health/ready` HTTP 200 with `rag_ready=true`; no operational database was
used or modified.

An additional isolated process was started with only its PostgreSQL host
rewritten to loopback port `9`. It became reachable after the bounded startup
attempt, returned `/health` HTTP 200, and returned `/health/ready` HTTP 503 with
`{"init_error":"database_unavailable","rag_ready":false}`. The process was
then stopped; the real PostgreSQL service was never stopped.

## Audit coverage after the change

| Operation | Success event | Failure event / safe log |
|---|---|---|
| Login | `login` | `login_failure` |
| RAG request | `corpus_query`, `agenda_corpus_query` | `rag_query_failed`, `agenda_rag_query_failed` |
| Workflow transition | `agenda_transition`, `tender_workflow_action` | `tender_workflow_failed` for tender create/transition |
| Billing prediction | `billing_forecast` | `billing_forecast_failed` |
| Tender creation | `tender_workflow_created` | `tender_workflow_failed` |
| Application/request error | JSON `request_failed` structured record | Safe exception class only |
| Audit persistence failure | N/A | JSON `audit_write_failed` structured record |

## Validation performed

- `.venv\Scripts\python.exe -m pytest -q tests/test_resilience_observability.py` — **4 passed**.
- `.venv\Scripts\python.exe -m pytest -q --tb=no` — **63 passed, 27 skipped** (acceptance tests are opt-in).
- `ruff check src tests` — passed.
- `npm run build` from `web` — passed (`tsc -b` and Vite production build).
- Isolated acceptance API after restart:
  - `GET http://127.0.0.1:8016/health` → HTTP 200, `database=portproject_acceptance`.
  - `GET http://127.0.0.1:8016/health/ready` → HTTP 200, `rag_ready=true`, 4 documents, 4 pages, 4 chunks, 4 vectors, 0 pending.
  - A safe request ID was echoed; an unsafe request ID was replaced with a generated identifier.
  - Runtime log contains JSON `request_completed` records with method/path/status/duration/request ID.
- Isolated PostgreSQL-outage process:
  - `/health` → HTTP 200 (liveness preserved).
  - `/health/ready` → HTTP 503 with `database_unavailable` and `rag_ready=false`.

## Remaining risk / next authorized phase

- A real dependency outage and recovery test still needs an isolated disposable stack or an explicitly approved maintenance window. It must not be performed against the live `portproject` database or shared Ollama service.
- Audit rows are still stored in the existing JSONB metadata column; no schema migration was required. A future phase may add a first-class correlation column only if operational query/reporting requirements justify it.
- This phase does not add retries, circuit breakers, or automatic dependency restarts. Those would change operational behavior and require a separate decision.

Phase 14 was not started.
