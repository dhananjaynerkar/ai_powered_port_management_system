# Phase 08 — Authentication, authorization, isolation, and RAG ACL E2E

## Final result summary

| Required gate | Result |
| --- | --- |
| Acceptance safety gate | **PASS** |
| Authority authentication | **PASS** |
| Tenant authentication | **PASS** |
| DO authentication | **PASS** |
| NO authentication | **PASS** |
| HO authentication | **PASS** |
| Session lifecycle | **PASS** (login, invalid session, logout, reuse rejection; timeout waiting was not performed) |
| Authorization matrix | **PASS** |
| Private-chat ownership | **PASS** |
| Cross-principal isolation | **PASS** |
| Tenant isolation | **PARTIAL** — tenant-to-tenant chat isolation and authority-route denial verified; no tenant property-detail route exists in this application to test |
| RAG ACL filtering | **PASS** |
| Restricted evidence excluded from LLM context | **PASS** |
| Citation ACL | **PASS** |
| Agenda authorization | **PASS** |
| Billing authorization | **PASS** |
| Tender authorization | **PASS** |
| Browser authenticated E2E | **NOT AVAILABLE** — no Playwright/Cypress/Selenium configuration in `web/package.json`; API E2E completed |
| Acceptance reset/repeatability | **PASS** |
| Full Python suite | **PASS** — 64 passed, 3 intentional skips |
| Ruff | **PASS** |
| Frontend production build | **PASS** |
| Operational `portproject` DB modified | **NO** |

**FINAL PHASE RESULT: PARTIAL**

The application passed the isolated API/database security and RAG ACL checks. The
result remains PARTIAL only because browser automation was not configured and the
application has no tenant property-detail route that could support a broader
tenant-data claim. Phase 09 was not started.

## Executive result

Phase 08 was executed against the isolated acceptance environment, not the
operational database. The acceptance guard verified the database and sentinel
before each fixture mutation. The complete Phase 08 suite passed **10/10** tests.

One real authorization defect was reproduced and fixed: a DO officer whose active
source role was deactivated could still save an agenda revision through a stale
session. The mutation boundary now re-reads the active source role, and the
regression test proves the request is rejected with no version mutation.

## Acceptance environment and safety evidence

| Check | Observed evidence |
| --- | --- |
| Acceptance database | `portproject_acceptance` |
| Acceptance sentinel | `acceptance/1` |
| Runtime role | non-superuser `portproject_acceptance_app` |
| Operational database | `portproject` (separate read-only verification) |
| Acceptance corpus | 4 indexed documents, 4 pages, 4 chunks, 4 vectors, 0 pending/processing/quarantined/failed |
| Principals | DO_TEST, NO_TEST, HO_TEST, TENANT_TEST, tenant_second, PRINCIPAL_A, PRINCIPAL_B |
| RAG ACL fixtures | public, authority, tenant, role-restricted |
| Workflow states | DO_DRAFT, SUBMITTED_TO_NO, RETURNED_TO_DO, SUBMITTED_TO_HO, APPROVED, REJECTED |
| Tender storage | `tests/runtime/tender/tender_workflows.json` |

The operational read-only check returned `current_database=portproject`, no
`public.acceptance_environment` table, zero acceptance fixture users, and no
acceptance document rows. No operational write was issued.

The final reset/check sequence ended with:

```text
ACCEPTANCE FIXTURE READY
database=portproject_acceptance
sentinel=acceptance/1
```

The API health gate returned:

```json
{"status":"ok","database":"portproject_acceptance","schema":"rag"}
{"status":"ready","rag_ready":true,"init_error":null,"corpus":{"documents":4,"pages":4,"pending_documents":0,"processing_documents":0,"quarantined_documents":0,"failed_documents":0,"chunks":4,"vectors":4}}
```

## Identity and role model

The implementation distinguishes portal role from workflow source role:

| Identity | Portal role | Workflow/source role | Principal | Tested domain |
| --- | --- | --- | --- | --- |
| `do_test` | authority | DO | `authority:10001` | authority dashboard, workflow, billing, tender |
| `no_test` | authority | NO | `authority:10002` | authority dashboard, review workflow, billing, tender |
| `ho_test` | authority | HO | `authority:10003` | authority dashboard, review workflow, billing, tender |
| `tenant_test` | tenant | none | `tenant:20001` | tenant-visible corpus, documents, chat |
| `tenant_second` | tenant | none | `tenant:20002` | tenant-to-tenant privacy check |

`authority_identity()` resolves the current active source role from the database;
`current_user` resolves the authenticated session principal. The RAG ACL values
are portal roles (`authority` and `tenant`), not DO/NO/HO workflow roles.

## Authentication E2E matrix

| Test | Request | Expected | Actual | Result |
| --- | --- | --- | --- | --- |
| AUTH-01 | Authority valid login | 200, authority session | 200, session established | PASS |
| AUTH-02 | Tenant valid login | 200, tenant session | 200, session established | PASS |
| AUTH-03 | `do_test` valid login | 200, authority portal, DO source role | 200, DO resolved | PASS |
| AUTH-04 | `no_test` valid login | 200, authority portal, NO source role | 200, NO resolved | PASS |
| AUTH-05 | `ho_test` valid login | 200, authority portal, HO source role | 200, HO resolved | PASS |
| AUTH-06 | Wrong password | 401, no cookie | 401, no session | PASS |
| AUTH-07 | Unknown username | 401, no cookie | 401, no session | PASS |
| AUTH-08 | Empty password | validation/auth rejection, no session | 422, no session | PASS |
| AUTH-09 | Malformed request | 422, no session | 422, no session | PASS |
| AUTH-10 | Invalid session cookie | 401 | 401 | PASS |
| AUTH-11 | Protected endpoint without session | 401 | 401 | PASS |
| AUTH-12 | Logout | 200, token invalidated | 200, token invalidated | PASS |
| AUTH-13 | Reuse cookie after logout | 401 | 401 | PASS |
| AUTH-14 | Configured idle/absolute timeout | safely testable without long wait | not time-waited; configuration remains enforced by resolver | NOT RUN |

Session rows store a SHA-256 token digest. Reports and test output never print
passwords, password hashes, raw cookies, bearer tokens, or database credentials.

## Authorization matrix (live HTTP results)

Unauthenticated protected requests returned 401. Authority DO/NO/HO requests
returned 200 on the authority capabilities below. Tenant requests returned 200
only on the tenant-visible capabilities and 403 on authority-only capabilities.

| Capability | Unauthenticated | Tenant | DO / NO / HO | Result |
| --- | ---: | ---: | ---: | --- |
| Corpus summary `/api/v1/corpus` | 401 | 200 | 200 | PASS |
| Document list `/api/v1/documents` | 401 | 200 | 200 | PASS |
| Local LLM list `/api/v1/local-llms` | 401 | 200 | 200 | PASS |
| Authority dashboard metrics | 401 | 403 | 200 | PASS |
| Authority tenant mappings | 401 | 403 | 200 | PASS |
| Workflow officers | 401 | 403 | 200 | PASS |
| Agenda list/read | 401 | 403 | participant/role-checked 200 | PASS |
| Workflow drafts | 401 | 200, principal-scoped | 200, principal-scoped | PASS |
| Private chat list/create/read | 401 | 200, own principal | 200, own principal | PASS |
| Billing status/rules/tenancies | 401 | 403 | 200 | PASS |
| Tender config/plots/workflows | 401 | 403 | 200 | PASS |

The tenant-visible workflow-draft behavior is an implemented product capability:
the route scopes by `principal_id` but does not add a separate authority source-role
gate. It is documented rather than changed in this phase.

## Session isolation

Two independent sessions were created and checked through `/api/v1/auth/me`.
Replacing one client's cookie with the other client's cookie changed the resolved
identity only to the cookie owner; request parameters cannot override session
ownership. Logging out A left B's session valid. Invalid cookies resolved to 401.

## Private chat ownership and tenant isolation

The test created chats for an authority principal, `tenant_test`, and
`tenant_second`. Each list returned only the caller's own sessions. Foreign reads
and deletes returned 404 and database chat/message counts did not change. Each
owner could delete its own unlinked chat. The seeded workflow-linked chat returned
409 with the product message that it cannot be deleted, and counts did not change.

This proves cross-principal and tenant-to-tenant chat isolation. No separate
tenant property-detail endpoint exists in the current application, so no claim is
made for a non-existent route.

## Identifier tampering / IDOR

The following real path identifiers were substituted between sessions:

| Identifier | Result |
| --- | --- |
| Foreign `chat_session_id` read/delete | 404, no mutation |
| Workflow-linked `chat_session_id` delete | 409, no mutation |
| Non-owner `agenda_id` revision | 404/409 ownership denial |
| Tenant authority-only billing/tender routes | 403 before service/action |
| Tenant authority-only workflow agenda/officer routes | 403 |

Authorization was derived from the authenticated principal and current role, not
from a user-supplied ownership field.

## RAG ACL and context-leak verification

The source ordering is: ACL predicate in lexical and dense candidate SQL, then
reranking, then context expansion, then citation/answer generation. The acceptance
test directly inspected the candidate rows and expanded context without loading a
second cross-encoder process. For a tenant question targeting role-restricted
evidence:

* restricted document rows did not survive the candidate boundary;
* restricted text did not enter expanded tenant context;
* the generated tenant answer contained no restricted phrase;
* restricted sources did not appear in citations.

For an authority question, the permitted authority source was returned. Public
evidence was returned to both authority and tenant. The generated responses
returned valid citations (`citation_valid=true`) on the successful acceptance
queries. RAG requests are local-model calls and observed durations were roughly
20–52 seconds; the final acceptance run passed without a 503.

## Agenda authorization

Pre-seeded agenda fixtures were used; the complete DO → NO → HO lifecycle was not
run. Participant reads succeeded, a tenant read was denied, a wrong-owner revision
was denied, and a wrong-role mutation did not change the agenda-version count.

### Defect reproduced and fixed

**Root cause:** `save_agenda_revision()` checked principal/owner state but did not
re-read the active source role. A DO session whose `public.admin_roles.is_active`
value was changed to false could still save a revision (HTTP 200).

**Smallest fix:** call `authority_identity(settings, user)` at the revision
mutation boundary in `src/portproject_rag/workflow.py`.

**Regression:** `test_agenda_authorization_and_active_role_recheck` deactivates the
acceptance-only role, asserts HTTP 403 and no `agenda_version` mutation, then
restores the fixture. The test passes.

## Billing and tender authorization

Authority DO/NO/HO access to the implemented billing and tender read routes
returned 200. Tenant and unauthenticated requests returned 403/401 before
prediction, tender action, or chat/audit mutation. Tender state remained in
`tests/runtime/tender/tender_workflows.json`; no operational tender path was used.
Numerical billing-model quality and complete tender persistence were explicitly
not tested in Phase 08.

## Error/resource visibility and audit security

Representative protected errors matched the implementation: 401 for missing or
invalid sessions, 403 for authenticated role denial, 404 for ownership-hiding,
409 for workflow-linked deletion, and 422 for malformed input. Responses contained
no stack traces, SQL, filesystem paths, password data, or session tokens.

Acceptance audit assertions passed for login failures, RAG query events, workflow
attempts, and billing/tender denial paths. Recent audit metadata contained no
password, session-token, database-URL, or PostgreSQL credential values.

## Browser E2E status

`web/package.json` contains Vite/TypeScript/React but no Playwright, Cypress, or
Selenium configuration. No browser framework was installed just for this phase.
Therefore browser authenticated E2E is **NOT AVAILABLE**. The backend/API E2E
coverage above is the reproducible security gate; a manual browser checklist can
be added when browser automation is introduced.

## Test artifacts and fixes

Added/updated:

* `tests/acceptance/conftest.py` — private acceptance env parsing, safety guard,
  credentials, session/database snapshots; it no longer contaminates the normal
  pytest process with acceptance environment variables.
* `tests/acceptance/test_phase08_e2e.py` — 10 guarded authentication,
  authorization, ownership, tenant-chat, RAG ACL, agenda, billing, tender, error,
  and audit tests.
* `src/portproject_rag/workflow.py` — active source-role re-check at agenda
  revision mutation.

The acceptance test process uses only the ignored `.env.acceptance` and the
acceptance sentinel. `.env.acceptance` and generated credentials are not printed,
committed, or included in this report.

## Reset/repeatability and regression evidence

* Full Phase 08 acceptance suite: **10 passed**.
* Representative post-reset repeatability subset (authentication, private-chat
  isolation, RAG ACL query): **3 passed**.
* Final reset/check: **ACCEPTANCE FIXTURE READY**, sentinel `acceptance/1`.
* Full Python suite: **64 passed, 3 skipped**.
* Ruff: **All checks passed**.
* React production build: **passed**, 1,671 modules transformed.
* `/health`: HTTP 200, database `portproject_acceptance`.
* `/health/ready`: HTTP 200, `rag_ready=true`, `init_error=null`.

## Remaining limitations

1. Browser authenticated E2E is not available because no browser test framework
   is configured.
2. Session timeout timing was not waited out because the configured windows are
   long; invalid-session and logout invalidation were tested.
3. Tenant property/application isolation beyond private chat is not applicable to
   an absent tenant-detail API route; authority-only route denial was tested.

## Operational database safety confirmation

The operational database read-only verification returned `portproject`, no
acceptance sentinel table, zero acceptance fixture users, and no acceptance
document rows. The acceptance reset/provision/check tooling always asserted the
acceptance database and sentinel before mutation. **Operational `portproject` was
not modified.**

## Evidence-based conclusion

Phase 08 backend/API security verification is complete and green in the isolated
acceptance environment. The only reasons the formal result is **PARTIAL** are the
unavailable browser automation and the explicitly bounded tenant-data scope; no
unresolved authentication, authorization, ownership, cross-principal, or RAG ACL
defect remains in the tested routes. Phase 09 was not started.
