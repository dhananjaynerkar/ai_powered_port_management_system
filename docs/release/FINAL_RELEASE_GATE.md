# Phase 18 — Final Release Gate

**Review date:** 2026-08-25  
**Repository:** `portproject_rag`  
**Release reviewer:** Codex (independent evidence review)  
**Baseline commit at gate start:** `1836722` (`Phase 17 refresh documentation and interview package`)  
**Gate rule:** no application code, API contract, database schema, model setting, or UI behavior was changed during this gate.

## Decision summary

| Release target | Decision | Meaning |
|---|---|---|
| **LOCAL DEMO READY** | **CONDITIONAL PASS** | The repository, API liveness, PostgreSQL connection, UI build/delivery, and automated checks pass. A live RAG demo still requires the local Ollama dependencies to be running; the current readiness probe is 503 while Ollama is unavailable. |
| **INTERNAL PILOT READY** | **NOT VERIFIED** | No approved isolated database, non-production accounts, workflow fixtures, browser session, or deployment-owner sign-off is available. |
| **PRODUCTION READY** | **FAIL** | Production acceptance has open security, authorization, RAG quality/latency, billing, backup, and multi-user tender-storage blockers. Production is not approved. |

Production is not a score. The gate is **FAIL** because the prompt requires all P0/P1 blockers to be closed before a production PASS, and several required areas are either known failures or not verified against an approved fixture.

## Evidence boundary

- The configured PostgreSQL database is the operational local `portproject` database. Read-only integrity queries were used; no source PMS rows, credentials, tenant rows, chats, agendas, billing rows, or tender records were created, edited, or deleted by this gate.
- The API was started temporarily on `127.0.0.1:8018` and the UI on `127.0.0.1:5179` to avoid replacing any existing service. Both processes were stopped after smoke checks. PostgreSQL remained on its configured local port; Ollama was not running.
- `.env` was inspected only for redacted configuration shape and is not tracked by Git. No password or token was printed, copied, or committed.
- Where this gate could not safely reproduce an authenticated or destructive check, the result is explicitly `NOT VERIFIED`, not inferred from a source-code inspection.
- “Pass” for an automated test or read-only probe is not a production approval when the corresponding fixture, owner sign-off, or external dependency is absent.

## Gate evidence and status

| Area | Evidence collected | Status | Residual risk | Owner |
|---|---|---|---|---|
| Git clean state / secret hygiene | `git status --short --branch` was clean at gate start; final commit will contain only this report. `.env` is not in `git ls-files`; `.env.example` remains the tracked template. | **PASS** | Working-tree cleanliness must be rechecked after the report commit. | Release engineering |
| Python dependency integrity | `.venv\\Scripts\\python.exe -m pip check` → `No broken requirements found.` | **PASS** | No Python lockfile; resolver drift is possible on a future clean install. | Release engineering |
| Backend regression suite | `.venv\\Scripts\\python.exe -m pytest -q --tb=no` → **48 passed in 16.32s**. | **PASS** | Most mutation/E2E cases are contract tests because no approved disposable fixture exists. | QA / backend |
| Ruff / static quality | `.venv\\Scripts\\ruff.exe check src tests` → `All checks passed!` | **PASS** | Static checks do not prove runtime authorization or service availability. | Backend |
| Frontend production build | `npm run build` in `web` → Vite 7.3.6, 1,671 modules transformed, build completed successfully. | **PASS** | Authenticated browser behavior remains unverified in this gate. | Frontend |
| API startup and liveness | Temporary API on `127.0.0.1:8018` started from `pms_api.app:create_runtime_app`; `GET /health` returned HTTP 200 with database `portproject`, schema `rag`. | **PASS** | Startup used the live local database and its existing migration path; production deployment lifecycle was not exercised. | Backend / SRE |
| Readiness / dependency state | `GET /health/ready` returned HTTP 503: `status=not_ready`, `rag_ready=false`, `init_error=rag_dependency_unavailable`; corpus payload was returned. Ollama port 11434 was not listening. | **CONDITIONAL PASS** | A RAG release cannot claim ready until the approved embedding/generation services are available and their model health is verified. | RAG / SRE |
| Database integrity | Read-only query against `portproject`: `pgcrypto` and `vector` extensions present; `rag.document=49` (48 indexed, 1 quarantined), `rag.document_page=1474`, `rag.chunk=3399`, embeddings `3399`; all embedding dimensions `1024`; zero orphan pages and chunks; required application/read-view tables present. | **PASS** | This is the operational local database, not a production clone or least-privilege acceptance database. | DBA / backend |
| Corpus integrity | Current inventory agrees with the Phase 5 state contract: 48 indexed documents, 1,474 extracted pages, 3,399 chunks, 3,399 vectors, zero pending/processing/failed, one quarantined scanned PDF. No unsupported OCR text was promoted. Focused corpus/live tests are included in the 48-test suite. | **PASS** | One source PDF remains quarantined until an approved higher-quality OCR path is available; the physical source corpus is outside Git. | Ingestion / RAG |
| RAG golden evaluation | Focused reference/live tests (`test_rag_gold_set.py`, `test_rag_evaluation.py`, `test_live_corpus_evaluation.py`, `test_chat_payload.py`) → **7 passed**. Phase 7 baseline measured 11 reviewed cases with Recall@5 **0.56**, citation-page accuracy **0.2273**, no-answer accuracy **0.3333**; no independent human/judge score exists. | **CONDITIONAL PASS** | The baseline is reproducible evidence, not a quality acceptance result; retrieval false negatives and citation mismatch remain open. | RAG / product |
| Citation accuracy | Phase 7 recorded **9 citation-page mismatches** across the 11-case baseline and five citation-validation fallbacks. The guardrail/unit tests pass, but end-to-end page accuracy is not release-grade. | **FAIL** | Grounded-answer evidence is the product’s trust boundary; citation adjudication and a signed target are required before production. | RAG / domain reviewer |
| Authentication matrix | Static route/settings tests pass. No authenticated request was sent because Phase 1 fixture, non-production credentials, and reset helper are absent; the configured database is operational. | **NOT VERIFIED** | Authority/tenant login and role behavior are not accepted end to end. | Security / QA |
| Cross-principal isolation | Principal predicates and ACL code were inspected; no two-principal disposable test was run. | **NOT VERIFIED** | Private chat, agenda, evidence, and tenant isolation could regress without a fixture-backed matrix. | Security / backend |
| Workflow lifecycle | State constraints and transition code have static coverage; Phase 9 lifecycle, invalid-transition, and read-only checks were not run against a disposable agenda. | **NOT VERIFIED** | Create/submit/return/revise/approve/reject and no-mutation guarantees remain unaccepted. | Workflow owner / QA |
| Workflow concurrency | `SELECT ... FOR UPDATE` is present in static code. No concurrent requests or stale-version checks were executed; Phase 9 identifies missing expected-version enforcement as a risk. | **NOT VERIFIED** | Lost-update and competing-transition behavior is unproven. | Backend / DBA |
| Billing validation | Unit/service tests pass, but Phase 10 found a training-manifest vs deployed JSON evaluator metric mismatch, no approved immutable holdout, and no business-reviewed hand-calculated cases. | **FAIL** | Forecast quality, formula rounding, missing-rate/area behavior, and unmatched-structure policy are not financially accepted. | Billing owner / ML |
| Tender persistence | Disposable temporary-store lifecycle/PDF tests pass. Phase 11 found process-local locking and a shared `.tmp` collision under two writers; PostgreSQL migration is design-only. | **CONDITIONAL PASS** | Acceptable only for explicitly approved single-user/single-process local demos; not for multi-user or production. | Workflow owner / DBA |
| Browser matrix | UI delivery smoke returned HTTP 200 for `/`, `/authority/dashboard`, and `/authority/documents` at temporary port 5179. The required authenticated matrix at 1024×768, 1280×720, 1366×768, 1440×900, and 1920×1080 was not re-run because no approved browser session/fixture exists. | **NOT VERIFIED** | Protected dashboard, tenants, AI, workflow, billing, tender, logout, and overflow behavior need fixture-backed browser evidence. | Frontend / QA |
| Accessibility | Source-level labels, focus styles, skip link, native controls, and splitter semantics are present; no axe scan and no complete authenticated keyboard/modal/splitter traversal were available. | **NOT VERIFIED** | Focus order, dialog behavior, charts, and status announcements still need an accessible authenticated run. | Accessibility / frontend |
| Backup / restore | Phase 3 isolated schema-only `rag`/`pms_doc`/`pms_vector` restore passed with synthetic data and was cleaned up. Full data-bearing restore, corpus, billing artifacts, tender state, source `public.*`, RPO/RTO, retention, and permissions remain unapproved. | **CONDITIONAL PASS** | A schema-only drill is not a production recovery certificate. | DBA / SRE |
| Clean install | Phase 15 disposable clone evidence: Python install, `pip check`, Ruff, `npm ci`, frontend build, API liveness, UI smoke, and secret tracking passed. Full clean-clone suite was 34 passed/14 external-prerequisite failures; Python lockfile is still absent. | **CONDITIONAL PASS** | A clean install needs approved database, models, billing/tender fixtures, and a reproducibility policy before it is an integration release. | Release engineering |
| Security configuration | Local security-setting tests pass and reject unsafe internal/production configurations. Production HTTPS, cookie, CORS, least-privilege grants, private model network, and the source-credential migration/SSO decision are not deployed or verified. | **CONDITIONAL PASS** | Local mode is not production mode; plaintext compatibility is only acceptable as a bounded local setting. | Security / SRE |
| Failure recovery / observability | Phase 13 controlled probes pass for simulated database/Ollama/model/artifact failures, structured request IDs, readiness 503s, and safe failure audit events. Real stop/restore of PostgreSQL/Ollama was not performed against shared infrastructure. | **CONDITIONAL PASS** | Dependency restart, alerting, and real recovery timing remain unproven. | SRE / backend |
| Performance targets | Non-RAG read paths met Phase 14 local targets. RAG warm retrieval was ~13.6s, reranking ~12.6s, generation ~100–102s, and complete answer ~120s versus the stated ~30s interactive target. | **FAIL** | CPU reranking/generation are material latency blockers; no quality-preserving optimization decision has been approved. | RAG / infrastructure |

## Promotion blockers

The following items block an INTERNAL PILOT or PRODUCTION promotion. They are listed as evidence-backed gaps, not assumed priorities; the product owner must assign P0/P1 labels and owners before a release candidate can be approved.

1. **Approved isolated acceptance fixture:** provision a sanitized/resettable database, DO/NO/HO/Tenant principals, disposable chats/agendas, billing cases, tender records, and non-secret credentials. This unblocks authentication, cross-principal, workflow, browser, and mutation acceptance.
2. **RAG trust and latency:** reconcile the citation-page mismatch baseline, define an approved citation/abstention target, and choose a measured reranker/generation optimization that does not regress grounding. Keep the quarantined PDF out of search until OCR quality is accepted.
3. **Billing release evidence:** reconcile training-library and JSON-evaluator predictions, create an immutable dataset/model/code manifest, obtain business-reviewed formula cases, and decide rounding, negative-intermediate, missing-rate, and unmatched-structure semantics.
4. **Production security and identity:** deploy HTTPS with explicit origins and Secure cookies, verify least-privilege PostgreSQL grants/private model networking, and make an owner-approved decision to migrate source plaintext credentials or use an approved IdP.
5. **Data recovery:** approve source/application/corpus/billing/tender backup scope, encryption, retention, RPO/RTO, and perform a data-bearing isolated restore with row/count/permission reconciliation.
6. **Multi-user tender storage:** either explicitly constrain deployment to one process/user or complete the PostgreSQL-backed workflow migration with optimistic versioning, actor attribution, transactional audit, and concurrency tests.
7. **Service readiness and operations:** keep `/health/ready` failing closed until Ollama and required models are available, then verify model health, recovery, alerting, and latency under the approved pilot topology.

## Final go / no-go

**NO-GO for production and internal pilot.** The repository is suitable for a controlled local demonstration when its local database, Ollama models, ignored billing/tender artifacts, and local fixture assumptions are deliberately provisioned. It is not acceptable to present the current local state as a production-ready, fully validated portal or RAG service.

No automatic fixes were applied during this gate. The next action requires explicit owner decisions and approved fixtures; it must not be inferred from this report.

