# Phase 18 — Final Release / Production Gate

**Review date:** 2026-08-26
**Repository:** portproject_rag
**Release reviewer:** Codex (independent evidence review)  
**Gate baseline:** 709cce3 (Add Phase 18 final release gate)
**Gate rule:** no application code, API contract, database schema, model setting,
or UI behavior was changed during this gate. This report records current
evidence and does not silently repair failures.

> RAG runtime measurements and ACL status in this dated Phase 18 gate are
> superseded by `docs/hardening/RAG_RUNTIME_FINAL_CERTIFICATION.md`. That
> later certificate proves the mixed-ACL neighbour/parent boundary and records
> the current runtime/resource limitations; the overall release decision
> remains a historical production gate.

## Decision summary

| Release target | Decision | Meaning |
| --- | --- | --- |
| **LOCAL DEMO READY** | **CONDITIONAL PASS** | The current local API/UI services are live, the operational corpus is readable, the acceptance-backed API and guarded acceptance suite pass, and the production build is green. The demo still depends on local PostgreSQL, Ollama, ignored runtime artifacts, and known RAG reliability/latency limits. |
| **INTERNAL PILOT READY** | **NOT VERIFIED** | Acceptance API E2E is green, but authenticated browser/accessibility evidence, deployment-owner security settings, recovery sign-off, and multi-user tender storage are not verified for a pilot topology. |
| **PRODUCTION READY** | **FAIL** | Human semantic review, host-bound RAG capacity evidence, unresolved production security/recovery decisions, and multi-process tender persistence remain open. The mixed-ACL context boundary is covered by the later final runtime certificate. |

Production is not a score. It is **FAIL** because required P0/P1 production
blockers are not all closed and several deployment-owner decisions are not
evidenced.

## Safety and evidence boundary

- The operational API on 127.0.0.1:8001 was observed read-only. /health
  reported database portproject; /health/ready returned HTTP 200 with
  rag_ready=true and corpus counts. No operational write was issued by this
  gate.
- Acceptance reset/check and the guarded API ran against portproject_acceptance
  only. The final check reported sentinel acceptance/1, principals, ACL
  fixtures, workflow fixtures, billing fixtures, and tender storage at
  tests/runtime/tender/tender_workflows.json.
- The acceptance API was started temporarily on 127.0.0.1:8016 with offline
  local model-cache flags, then stopped. The fixture was reset after the
  acceptance run and checked again.
- No password, password hash, database URL, session cookie, bearer token, or
  credential value was printed. .env is ignored and untracked; acceptance
  credentials and runtime tender files are not tracked.
- The working tree was **not clean** at gate start. Existing user changes and
  uncommitted phase artifacts were preserved; no reset, checkout, or unrelated
  cleanup was performed.
- A later release report is not used as evidence for this gate. This file is
  the current Phase 18 decision record.

## Gate evidence and status

| Area | Evidence | Status | Residual risk | Owner |
| --- | --- | --- | --- | --- |
| Git clean state | git status --short --branch showed pre-existing modified and untracked files at gate start. | **FAIL** | A release commit cannot be reproduced from a clean tree until the owner reviews and commits or discards changes. | Release engineering |
| Secret hygiene | .env, acceptance credentials, and runtime tender state are not tracked; .env is ignored. | **PASS** | Secret-store provisioning and repository secret scanning still belong to deployment governance. | Security / release engineering |
| Diff hygiene | Full git diff --check reported only pre-existing trailing whitespace in docs/hardening/PHASE_14_PERFORMANCE.md; line-ending normalization warnings are non-errors. | **CONDITIONAL PASS** | The unrelated historical whitespace was not changed during a no-fix release gate. | Release engineering |
| Python dependency integrity | .venv\Scripts\python.exe -m pip check → No broken requirements found. | **PASS** | Python dependencies are range-based; no lockfile provides bit-for-bit resolution. | Release engineering |
| Python regression suite | .venv\Scripts\python.exe -m pytest -q --tb=no → **64 passed, 27 skipped in 12.11s**. | **PASS** | Skips are environment/acceptance-dependent and are not counted as passes. | QA / backend |
| Ruff / static quality | .venv\Scripts\ruff.exe check src tests → All checks passed! | **PASS** | Static checks do not prove deployment or authorization behavior. | Backend |
| Frontend production build | npm run build in web → Vite 7.3.6, **1,672 modules transformed**, build completed. | **PASS** | Authenticated browser behavior remains separate evidence. | Frontend |
| Startup and liveness | Existing local API returned /health HTTP 200. Acceptance API startup reached /health/ready on port 8016. | **PASS** | The operational process was already running; a production service-manager deployment was not exercised. | Backend / SRE |
| Readiness / dependency state | Operational /health/ready returned HTTP 200, rag_ready=true, 48 indexed documents, 1 quarantined document, 3,399 chunks/vectors. Acceptance readiness returned HTTP 200 with 4 documents/chunks/vectors. | **PASS** | Readiness depends on local PostgreSQL, Ollama, reranker, and corpus artifacts. | RAG / SRE |
| Database integrity | Read-only portproject query: pgcrypto and vector extensions; 49 documents, 1,474 pages, 3,399 chunks, 3,399 vectors, 1,024 dimensions, zero orphan pages/chunks; application views/objects present. | **PASS** | This is a local operational baseline, not a production clone with least-privilege evidence. | DBA / backend |
| Corpus integrity | Operational inventory: 48 indexed, 1 quarantined, no pending/processing/failed; view counts match chunks/embeddings. | **PASS** | The quarantined source remains outside trusted search until approved extraction quality exists. | Ingestion / RAG |
| RAG golden evaluation | Focused tests test_rag_gold_set.py, test_rag_evaluation.py, test_live_corpus_evaluation.py, and test_chat_payload.py: **7 passed**. Historical reviewed baseline remains Recall@5 0.56, citation-page accuracy 0.2273, no-answer accuracy 0.3333. | **CONDITIONAL PASS** | Unit/golden checks pass, but the reviewed citation/no-answer baseline is not a production quality acceptance target. | RAG / product |
| Citation accuracy | Existing Phase 7 evidence records 9 citation-page mismatches across 11 reviewed cases; Phase 14 acceptance observation had one successful cited answer followed by a 503. | **FAIL** | Grounded evidence is the product trust boundary; domain adjudication and an approved target are still required. | RAG / domain owner |
| Authentication matrix | Guarded acceptance suite includes Authority, Tenant, DO, NO, and HO valid/negative login, invalid session, logout, and protected-route checks. | **PASS** | Session timeout was configuration-checked rather than time-waited; production identity/SSO is not deployed. | Security / QA |
| Cross-principal and private-chat isolation | Acceptance tests passed foreign read/delete denial, tenant-to-tenant isolation, workflow-linked deletion protection, and no-mutation snapshots. | **PASS** | Broader tenant property-detail isolation is not implemented as a separately testable API. | Security / backend |
| Authorization matrix | Acceptance tests passed role-aware corpus/document/LLM, dashboard, tenant, workflow, billing, tender, and chat route expectations. | **PASS** | Matrix covers implemented routes; it is not evidence for unimplemented product capabilities. | Security / backend |
| RAG ACL and citation boundary | Acceptance tests passed public/authority/tenant/role-restricted candidate and citation behavior; the later final runtime certificate adds a mixed-ACL neighbour/parent regression. | **PASS (boundary)** | Evidence is acceptance-fixture scoped; broader future retrieval paths still require their own tests. | RAG / security |
| Workflow lifecycle | Guarded Phase 09 tests passed DO → NO → HO creation, revisions, returns, approvals/rejections, invalid transitions, ownership, and no-mutation checks. | **PASS** | Evidence is acceptance-fixture scoped; production deployment topology is not verified. | Workflow owner / QA |
| Workflow concurrency | Guarded Phase 09 tests passed concurrent transition/revision scenarios with unique versions and one valid transition. | **PASS** | Wider load/concurrency limits and deployment worker topology remain unmeasured. | Backend / DBA |
| Billing validation | Guarded Phase 10 tests passed source-backed prefill/prediction, formula and authorization behavior, source immutability, and audit/chat ownership. | **CONDITIONAL PASS** | No approved business threshold/holdout makes model-quality and financial-release acceptance incomplete. | Billing owner / ML |
| Tender persistence | Guarded acceptance tender checks passed against isolated runtime storage; Phase 11 still documents shared JSON temp-file collision/process-local locking. | **CONDITIONAL PASS** | Not acceptable for multi-process/multi-user production without transactional shared storage and concurrency migration. | Workflow owner / DBA |
| Browser matrix | Current browser smoke loaded the public shell at http://127.0.0.1:5173/, rendered the home DOM, and measured no document-level horizontal overflow at the available viewport. No Playwright/Cypress/Selenium runner is configured and no authenticated role matrix was executed. | **NOT VERIFIED** | Protected routes, login/logout, role controls, dialogs, splitters, and required five-width matrix need a reproducible authenticated browser runner. | Frontend / QA |
| Accessibility | Source-level labels/focus/splitter semantics exist; no automated accessibility scanner or authenticated keyboard/modal traversal was available in this gate. | **NOT VERIFIED** | Need axe-equivalent scan and authenticated keyboard/focus/contrast checks. | Accessibility / frontend |
| Backup / restore | Phase 03 isolated schema-only rag/view/vector restore passed with synthetic data and cleanup. | **CONDITIONAL PASS** | No approved data-bearing source/corpus/billing/tender restore, RPO/RTO, retention, encryption, or owner sign-off. | DBA / SRE |
| Clean install | Phase 15 disposable-copy evidence passed install, pip check, Ruff, npm ci, build, and liveness; full clean-clone suite was partial because approved DB/artifact inputs were absent. | **CONDITIONAL PASS** | Current dirty tree and absent private runtime inputs prevent a reproducible release artifact. | Release engineering |
| Security configuration | Settings/security regression tests pass and reject unsafe internal/production combinations. | **CONDITIONAL PASS** | HTTPS, secure cookies, explicit production origins, least-privilege PostgreSQL, private model networking, and credential migration/SSO are not deployed/verified. | Security / SRE |
| Failure recovery / observability | Phase 13 controlled dependency-failure probes and current resilience tests pass; real PostgreSQL/Ollama stop/restore was not performed against shared services. | **CONDITIONAL PASS** | Recovery timing, alerting, and service-manager restart behavior remain unproven. | SRE / backend |
| Performance targets | Phase 14 acceptance re-check passed non-RAG local targets. RAG observation had one 25.3s cited success followed by a 503; earlier warm CPU baseline was ~120s complete answer. | **FAIL** | RAG reliability/latency is not stable enough for the stated interactive target; no blind optimization was applied. | RAG / infrastructure |

## Acceptance run details

The guarded command was run only after loading .env.acceptance and resetting the
fixture:

~~~text
. .\scripts\load_acceptance_env.ps1
.venv\Scripts\python.exe -m pytest -q --tb=short tests/acceptance
24 passed in 258.63s (0:04:18)
~~~

The final reset/check reported:

~~~text
ACCEPTANCE FIXTURE READY
database=portproject_acceptance
sentinel=acceptance/1
~~~

The acceptance API was stopped after the run. No operational portproject
database or operational tender path was used for those mutable tests.

## Promotion blockers

1. **Citation trust:** reconcile the reviewed citation-page mismatch baseline,
   define a domain-approved citation/abstention target, and rerun a signed
   evaluation.
2. **RAG runtime capacity:** the mixed-ACL context boundary is now regression
   tested; the remaining runtime concern is CPU/memory capacity under the
   measured local model stack. See the final runtime certificate.
3. **RAG reliability and latency:** resolve the observed 503/slow local model
   behavior with paired quality/latency evidence; do not change models or
   budgets blindly.
4. **Production security/identity:** approve HTTPS, secure cookies, explicit
   origins, least-privilege PostgreSQL, private model networking, and the
   legacy credential migration/SSO strategy.
5. **Recovery:** approve data-bearing backup scope, encryption, retention,
   RPO/RTO, and an isolated restore with real row/count/permission checks.
6. **Tender storage:** replace or explicitly constrain the process-local JSON
   store before multi-user or production deployment.
7. **Release hygiene:** review and commit the current working tree from a
   clean, reproducible release baseline; keep secrets and runtime artifacts
   out of Git.

## Final go / no-go

**CONDITIONAL PASS for a controlled local demonstration.**

**NO-GO for internal pilot and production promotion.** The repository has
strong acceptance/API evidence and a working local path, but documented
quality, RAG security-boundary, browser/accessibility, recovery, deployment
security, and multi-user persistence gaps prevent a higher release decision.

No automatic fixes were applied during Phase 18. This is the final release
gate decision; the next phase must be explicitly authorized and must address
the blockers above rather than being inferred from this report.
