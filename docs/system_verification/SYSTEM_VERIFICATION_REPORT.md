# Complete end-to-end system verification report

**Target:** target checkout (local path redacted)
**Audit date:** 2026-08-24  
**Mode:** evidence-based, local-only, non-destructive acceptance audit

## Final result

**NOT READY FOR PRODUCTION.** The project is runnable locally and passes its
current dependency, automated-test, lint, build, readiness, schema, vector
integrity, guardrail, and bounded read-only query checks. It is not honest to
call it production-accepted because authentication/role E2E, live RAG answer
quality, workflow concurrency, backup/restore, browser viewport/accessibility,
and production security hardening are not all verified; the security gate has
an explicit fail condition.

The complete phase-by-phase evidence is in
[`FINAL_VERIFICATION_MATRIX.md`](FINAL_VERIFICATION_MATRIX.md). Blockers and
closure conditions are in [`BLOCKERS.md`](BLOCKERS.md).

## Required top summary

| Area | Status | Evidence-based conclusion |
|---|---|---|
| Environment | PARTIAL | Runtime is known and healthy; target has no independent Git root |
| Runtime | PASS | API 8001, UI 5173, PostgreSQL 5432, Ollama 11434 are listening; readiness is ready |
| Database | PARTIAL | Correct `portproject`/schemas/extensions and checked references are healthy; one pending document remains |
| Authentication | BLOCKED | Protected routes return 401 without a session; authorized login was not available to test |
| Authorization | BLOCKED | Role checks exist in source; approved DO/NO/HO/Tenant fixture matrix was unavailable |
| Dashboard | PARTIAL | Live metrics run, but status `V` and `is_vacant=true` have materially different areas |
| Tenants | PARTIAL | Live server-side pagination/filter/sort/date validation works; canonical tenant terminology and authenticated UI remain open |
| Corpus | PARTIAL | 48 indexed documents, 1 pending, 3,399 chunks and vectors; pending extraction prevents an all-ready claim |
| Ingestion | PARTIAL | Persisted corpus and provenance schema are present; no new PDF was ingested during the safe audit |
| RAG | PARTIAL | ACL/citation coverage and guardrails are tested; live retrieval/generation/evidence quality is not accepted |
| Chat | PARTIAL | Principal scoping and protected routes are present; authenticated lifecycle/UI states remain unverified |
| Workflow | PARTIAL/BLOCKED | State machine and ownership checks exist; valid/invalid/concurrent live transitions require a safe fixture |
| Billing | PARTIAL | Focused service/formula tests pass; live customer/model-quality acceptance remains open |
| Tender | PARTIAL | Isolated source-backed calculation/PDF tests pass; live persistence/actions remain open |
| UI | PARTIAL | React production build passes; authenticated browser viewport and accessibility evidence is missing |
| Security | FAIL | Local `cookie_secure=false` and legacy external password-material compatibility require production hardening/review |
| Performance | PARTIAL | Small warm local read baseline captured; no representative concurrent load test |
| Accessibility | NOT TESTED | Static handlers/labels exist, but no axe/keyboard/browser audit |
| Backup/recovery | NOT TESTED | No restore artifact or drill supplied |
| Documentation | PASS for this audit / PARTIAL for project-wide reality | This report is complete; historical/current doc navigation still needs cleanup |

## Verified strengths

1. **The target is runnable.** The supported launcher checks dependencies and
   starts the API and React UI on loopback. The current API process reached
   application startup complete and `/health/ready` returned `200` with
   `rag_ready=true` and `init_error=null`.
2. **The build baseline is clean.** `pip check` reported no broken
   requirements, 31 automated tests passed, Ruff reported no findings, and the
   TypeScript/Vite production build transformed 1,670 modules successfully.
3. **The vector corpus is materially present.** The application projection
   reports 48 indexed documents, 1 pending document, 1,476 pages, 3,399
   chunks, and 3,399 vectors. All checked vectors are 1024-dimensional and
   all indexed chunks have lexical, dense, rerank-eligible, page-citation, and
   ACL coverage according to the live corpus test.
4. **The database boundary is explicit.** The app uses `portproject` with
   `rag`, `pms_doc`, and `pms_vector`; pgvector and pgcrypto are installed.
   Foreign-key-style orphan checks performed here returned zero for the
   checked chunk/page/chat/agenda relationships.
5. **The tenant query is not a fake static table.** It reads
   `public.applicant_property_mapping`, supports server-side query/status/lease
   type/allotment/date filters, allow-listed sorting, page size bounds, and
   validated date ranges. A read-only call returned 3,841 records and 154
   pages at page size 25.
6. **Guardrails are observable.** Normal input is allowed while prompt
   injection, destructive SQL, empty input, and over-limit input are rejected;
   the focused guardrail suite passed.

## Material gaps and data-meaning risks

### 1. Vacancy has two live meanings

The source contains both `plot.status` and `plot.is_vacant`. In this audit,
status `V` (the UI’s historical “vacant” style code) covers 65,847.28 sq.m,
whereas `is_vacant=true` covers 1,030,814.67 sq.m. The API documents these as
separate definitions, but a user-facing KPI labelled only “Vacant Land” can
still be read as either. This is a domain decision, not a CSS issue.

### 2. Tenant, tenancy, and mapping are distinct

The 3,841 tenant-page rows are applicant-property mapping records. The live
terminology query separately reports 3,839 tenancy identifiers, 3,841 mapping
applicant IDs, and 3,072 matched applicant profiles. The UI must not call all
three concepts “tenants” without a shared business glossary.

### 3. Corpus is not fully ready

One document has no chunks and no vectors. Readiness exposes that fact as one
pending document; any “documents ready” label must preserve that state.

### 4. External authentication carries legacy credential risk

The compatibility path reads `demo_password` and `passwd` from the external
`public.admin_users` table. The audit only counted populated fields and never
printed values. This must be reviewed and isolated before deployment.

### 5. Acceptance-critical actions are still unproven

No authorized account or disposable role fixture was supplied. Therefore the
audit did not create or delete chats, transition agendas, run billing/tender
mutations, test cross-principal access, or claim a real generated answer.

## Performance/plan observations

Warm local read samples (five calls, one machine) were approximately:

- dashboard metrics: median 90.7ms, max 93.0ms;
- tenant page/filter query: median 59.7ms, max 174.5ms;
- corpus stats: median 44.0ms, max 45.7ms;
- readiness: median 282.8ms, max 386.0ms.

These are diagnostic samples, not SLOs. `EXPLAIN` showed index-only scans for
tenant count/page reads, a sequential scan for the 2,770-row plot aggregate,
and a configured HNSW cosine index on `rag.chunk.embedding`. A representative
load test and `EXPLAIN (ANALYZE, BUFFERS)` in a safe clone are still needed.

## Security and safety conclusion

The audit itself did not print credentials, call external services, ingest new
files, change database rows, or bypass login. It did confirm that local
settings use non-secure cookies and that the external compatibility schema has
legacy password material. Production promotion must stop until the P0
security and recovery blockers are closed.

## Recommended acceptance sequence

1. Resolve the security and backup/recovery P0 gates.
2. Create a non-production fixture with approved DO/NO/HO/Tenant accounts and
   two principals for isolation/concurrency tests.
3. Complete or quarantine the pending document and run the warm RAG question
   set, checking source pages and timings.
4. Obtain domain sign-off for status/occupancy and tenant/tenancy/mapping
   terminology; update one shared contract used by dashboard and tenant UI.
5. Run workflow, billing, tender, deletion, outage, and API contract tests on
   the fixture without touching operational records.
6. Run the browser viewport/accessibility matrix and a clean-install/restore
   drill.
7. Re-run this folder’s matrix and only then reconsider the production gate.

## Scope declaration

No application code, route, schema, model setting, database row, source PDF,
workflow record, or reference project was changed by this audit. Generated
build/runtime logs may reflect the verification requests; they are not
application feature changes.
