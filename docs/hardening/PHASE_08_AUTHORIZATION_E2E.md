# Phase 8 - authentication, authorization, and isolation E2E

Status: **BLOCKED - APPROVED TEST DATABASE REQUIRED**

Completed: 2026-08-25

## Phase gate

Phase 8 requires the approved non-production fixture from Phase 1. Phase 1 is
still explicitly blocked: this checkout has no approved cloned database,
sanitized fixture bundle, test credentials, fixture sentinel, or reset helper.
The configured connection is the operational portproject database.

Running login, chat creation/deletion, agenda transitions, billing, or tender
mutations against that database would test and mutate operational records. No
authenticated E2E request, database mutation, session creation, or destructive
reset was executed in Phase 8.

Evidence:

| File | Function/route | Evidence | Result |
|---|---|---|---|
| docs/hardening/PHASE_01_TEST_FIXTURE.md | Phase 1 gate | Explicitly states BLOCKED - APPROVED TEST DATABASE REQUIRED; current database is operational portproject. | **BLOCKED** |
| src/portproject_rag/settings.py | Settings | Loads the configured database URL from the local environment; the value was not printed. | **NOT VERIFIED for test isolation** |
| src/portproject_rag/auth.py | authenticate, create_session, current_user | Authority roles are read from source public.admin_users/public.admin_roles; sessions are application-owned. | Static contract inspected; E2E **NOT VERIFIED** |
| src/portproject_rag/api.py | login/logout/me routes | Authority and tenant login routes call the shared authentication/session path. | Static contract inspected; E2E **NOT VERIFIED** |

## Permission matrix

The matrix below is the acceptance plan, not a claim that the behavior passed.
Every row remains **NOT VERIFIED** until the approved fixture exists.

| Capability | Backend route/function | Authority | DO | NO | HO | Tenant | E2E result |
|---|---|---|---|---|---|---|---|
| Dashboard | /api/authority/dashboard/metrics | allowed | allowed | allowed | allowed | 403 guard | **NOT VERIFIED** |
| Tenant mappings | /api/authority/tenants | allowed | allowed | allowed | allowed | 403 guard | **NOT VERIFIED** |
| Document list | /api/v1/documents | authenticated | authenticated | authenticated | authenticated | authenticated | **NOT VERIFIED** |
| Document RAG | /api/v1/chat, /api/v1/policy/query, _answer_payload | authenticated; role passed to retrieval | same | same | same | same | **NOT VERIFIED** |
| Private chat create | POST /api/v1/chat/sessions | principal-owned | principal-owned | principal-owned | principal-owned | principal-owned | **NOT VERIFIED** |
| Private chat read/list | GET /api/v1/chat/sessions* | principal filter | principal filter | principal filter | principal filter | principal filter | **NOT VERIFIED** |
| Private chat delete | DELETE /api/v1/chat/sessions/{id} | owner filter plus workflow-link guard | same | same | same | same | **NOT VERIFIED** |
| Agenda list/read | /api/v1/workflow/agendas*, list_agendas, agenda_detail | participant and active role | same | same | same | 403 authority guard | **NOT VERIFIED** |
| Agenda create | POST /api/v1/workflow/agendas / create_agenda_from_chat | DO only, cited chat required | DO only | denied | denied | denied | **NOT VERIFIED** |
| Agenda revise | /api/v1/workflow/agendas/{id}/revisions / save_agenda_revision | active owner, non-terminal | owner/state dependent | owner/state dependent | owner/state dependent | denied | **NOT VERIFIED** |
| Agenda transition | /api/v1/workflow/agendas/{id}/transition / transition_agenda | role/state/owner/target checks | DO actions | NO review actions | HO terminal actions | denied | **NOT VERIFIED** |
| Agenda AI query | /api/v1/workflow/agendas/{id}/query | participant; read-only snapshot rejected | same | same | same | denied | **NOT VERIFIED** |
| Billing | /api/v1/billing/* | _require_authority | allowed | allowed | allowed | 403 guard | **NOT VERIFIED** |
| Tender | /api/v1/tender/* | _require_authority | allowed | allowed | allowed | 403 guard | **NOT VERIFIED** |

The labels allowed and guard above are static implementation observations, not
successful E2E outcomes.

## Required cross-principal tests

These tests were not run because no safe principals or disposable records
exist:

1. Principal B cannot list or read Principal A's private chat.
2. Principal B cannot delete Principal A's chat; the database remains unchanged.
3. An unauthorized agenda returns the documented not-found/forbidden result and
   does not reveal its messages, versions, or context capsules.
4. Unauthorized evidence is excluded before retrieval and therefore cannot
   enter the LLM context or citations.
5. Tenant data from one approved fixture principal cannot be read by another.
6. DO/NO/HO role checks are enforced by backend responses, not only UI state.

The code paths that must be verified are principal predicates in api.py and
workflow.py, role lookup in auth.py and workflow.py, the ACL predicate in
retrieval.py, and database writes guarded by principal_id. Static inspection
cannot prove all response bodies, database mutation results, or transaction
behavior.

## Required request evidence once unblocked

For every matrix row and isolation test, the acceptance artifact must record:

    fixture label (not a real credential)
    request method and route
    actor role and principal label
    resource fixture label
    expected status
    actual status/body classification
    database mutation: yes/no and affected fixture row
    retrieval evidence/context/citation result where applicable

No password, session token, raw tenant export, or source-system secret may be
written to the artifact.

## Exact blocker and unblock action

**BLOCKED:** an approved isolated database or sanitized fixture bundle and
non-secret test-account provisioning mechanism are required before any Phase 8
request can be executed safely.

Provide/approve the Phase 1 fixture, including DO, NO, HO, Tenant, two
principals, cited/private chats, disposable agendas, billing complete/incomplete
cases, and tender fixture state. Then the fixture can be reset and this matrix
can be executed without touching portproject.

Phase 8 stops here. No permission was weakened, no operational data was
changed, and Phase 9 was not started.

## Non-mutating repository validation

| Check | Result |
|---|---|
| Python tests | **PASS - 45 passed** |
| Ruff | **PASS - all checks passed** |
| Python compile check | **PASS** |
| React production build | **PASS - 1,670 modules** |
| Authenticated fixture E2E | **BLOCKED - no approved fixture** |
