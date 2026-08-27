# Phase 09 — Complete DO → NO → HO Workflow E2E

## Required final summary

| Gate | Result |
| --- | --- |
| Acceptance safety gate | **PASS** |
| Authority authentication | **PASS** |
| Tenant authentication | **PASS** |
| DO authentication | **PASS** |
| NO authentication | **PASS** |
| HO authentication | **PASS** |
| Session lifecycle | **PASS** |
| Authorization matrix | **PASS** |
| Private-chat ownership | **PASS** |
| Cross-principal isolation | **PASS** |
| Tenant isolation | **PARTIAL** — tenant-to-tenant chat isolation is verified; no tenant property-detail API exists for a broader claim |
| RAG ACL filtering | **PASS** |
| Restricted evidence excluded from LLM context | **PASS** |
| Citation ACL | **PASS** |
| Agenda authorization | **PASS** |
| Billing authorization | **PASS** (Phase 08 regression gate) |
| Tender authorization | **PASS** (Phase 08 regression gate) |
| Workflow lifecycle | **PASS** |
| Workflow UI permission state | **BUILD-VERIFIED; browser execution not available** |
| Browser authenticated E2E | **NOT AVAILABLE** — no Playwright/Cypress/Selenium configuration exists |
| Acceptance reset/repeatability | **PASS** |
| Full Python suite | **PASS** — 74 passed, 3 intentional skips |
| Ruff | **PASS** |
| Frontend production build | **PASS** |
| Operational `portproject` DB modified | **NO** |

**FINAL PHASE RESULT: PARTIAL**

The complete backend/database workflow and security lifecycle passed against the
isolated acceptance database. The result is marked PARTIAL only for the same
documented boundary as Phase 08: browser automation is not configured, and the
application has no tenant property-detail route from which broader tenant-data
isolation could be tested. Phase 10 was not started.

## Scope and safety boundary

This phase tested only the official agenda workflow, its authorization/ownership
boundaries, evidence snapshots, workflow AI access, and related regression gates.
It did not perform the Phase 10 complete tender lifecycle, RAG quality tuning,
RAG performance optimization, billing model validation, tender persistence
migration, or production deployment.

Every mutable acceptance test uses the existing acceptance guard. Before fixture
reset or test mutations it verifies:

```text
current_database() = portproject_acceptance
acceptance sentinel = acceptance/1
current_database() != portproject
```

The isolated environment was:

| Item | Verified value |
| --- | --- |
| Database | `portproject_acceptance` |
| Sentinel | `acceptance/1` |
| Database role | non-superuser acceptance application role |
| Corpus | 4 documents, 4 pages, 4 chunks, 4 vectors |
| Workflow fixtures | DO_DRAFT, SUBMITTED_TO_NO, RETURNED_TO_DO, SUBMITTED_TO_HO, APPROVED, REJECTED |
| Tender storage | `tests/runtime/tender/tender_workflows.json` |
| Billing fixture | `tests/runtime/acceptance/billing_tax_mapping.csv` |

The final reset/check completed with `ACCEPTANCE FIXTURE READY`. The final
read-only operational check returned `current_database=portproject`, no
`public.acceptance_environment` table, zero `phase09-*` agendas, and zero
`phase09-*` chats. No operational write was issued.

## Actual workflow state machine

The transition rules were read from `src/portproject_rag/workflow.py` and then
verified through the live API:

| Current state | Action | Required source role/owner | Target | Next state |
| --- | --- | --- | --- | --- |
| DO_DRAFT or RETURNED_TO_DO | `submit_to_nodal` | current DO owner | active NO | SUBMITTED_TO_NO |
| SUBMITTED_TO_NO or SUBMITTED_TO_HO | `return_to_do` | current NO/HO reviewer | assigned DO | RETURNED_TO_DO |
| SUBMITTED_TO_NO | `submit_to_hod` | current NO owner | active HO | SUBMITTED_TO_HO |
| SUBMITTED_TO_HO | `approve` | current HO owner | same HO | APPROVED |
| SUBMITTED_TO_HO | `reject` | current HO owner | same HO | REJECTED |

Each successful transition updates the agenda, creates one context capsule, and
creates one handoff message in the same database transaction while the agenda
row is locked with `FOR UPDATE`.

## End-to-end lifecycle evidence

The guarded test `test_complete_do_no_do_revision_resubmit_no_ho_approval_and_capsule_history`
proved:

1. DO created an agenda from a private chat containing a real cited assistant answer; the agenda started as `DO_DRAFT`, version 1.
2. DO submitted to the active NO; state became `SUBMITTED_TO_NO` and owner became NO.
3. NO returned the agenda to DO; state became `RETURNED_TO_DO`.
4. DO saved version 2; version 1 remained immutable and its text was unchanged.
5. DO resubmitted to NO; state became `SUBMITTED_TO_NO`.
6. NO submitted to the active HO; state became `SUBMITTED_TO_HO` and owner became HO.
7. HO approved; state became `APPROVED`, owner remained HO, and `finalized_at` was set.
8. The separate seeded HO rejection path changed `SUBMITTED_TO_HO` to `REJECTED` without changing versions.

The full Phase 09 suite passed **10/10** tests. It also covered agenda creation
preconditions, wrong role/owner/state/target requests, inactive DO/NO/HO roles,
duplicate and terminal transitions, stale requests, concurrent transitions,
concurrent revisions, context capsule immutability, and workflow AI ownership.

## Creation and ownership controls

Agenda creation is restricted to an authenticated active DO and to a chat owned
by that same principal. Empty chats, chats without a cited assistant response,
foreign chat IDs, unknown UUIDs, malformed UUIDs, and non-DO creation attempts
were rejected without increasing agenda/version counts. A chat linked to an
agenda remained protected from deletion with the implemented `409` response and
no database mutation.

Foreign agenda reads and workflow AI requests use the application's participant
and resource-hiding semantics (`403`, `404`, or `409` as appropriate). A
non-current participant cannot consume the official workflow AI endpoint, and a
tenant cannot access an authority agenda.

## Authorization and stale-role defect

One real defect was reproduced before the fix: a NO principal could call the
revision endpoint for an agenda even though revision is a DO-only operation.
The endpoint checked principal membership/current ownership but did not require
the active workflow role to be DO and did not restrict the state to
`DO_DRAFT`/`RETURNED_TO_DO`.

The smallest safe fix in `src/portproject_rag/workflow.py` now:

* re-reads the active source role at the revision mutation boundary;
* rejects non-DO roles with `403`;
* requires the locked agenda row to be owned by that principal, have role DO,
  and be in `DO_DRAFT` or `RETURNED_TO_DO`;
* preserves the existing transactional version/message update.

The React workflow screen now shows draft editing only when the current owner is
the logged-in DO and the state is editable. NO/HO still see their authorized
handoff actions and do not see a misleading “Edit draft” control.

## Concurrency and atomicity

Acceptance tests sent two identical transitions concurrently and observed one
`200` and one `409`, with exactly one new capsule and one final state. Conflicting
NO actions likewise produced one commit and one rejection. Two concurrent DO
revision requests produced unique version numbers (`v2`/`v3` when both won, or a
single new version when one lost) and preserved all prior version text.

Invalid state, wrong role, inactive-role, invalid target, duplicate, terminal,
and stale requests left agenda state, version count, message count, and capsule
count unchanged. Database context managers roll back rejected mutations.

## Evidence snapshots and workflow AI

Context capsule sources are derived from official AI messages that existed at the
capsule timestamp. The acceptance test verified that adding a later AI message
with different evidence did not change an earlier capsule's source list.

A current owner successfully ran the workflow AI endpoint, received a grounded
answer with real citation metadata, and the AI message was saved to the official
agenda thread. A non-current participant received `409` before retrieval and a
tenant received `403`; neither request added messages or changed counts.

The RAG security boundary remains: ACL filtering occurs in candidate retrieval,
then reranking/context assembly, then generation and citation validation. The
Phase 08 candidate/context tests proved restricted evidence did not reach tenant
context, citations, or answer text.

## Regression artifacts

Added or updated:

* `tests/acceptance/test_phase09_workflow_e2e.py` — ten guarded lifecycle,
  authorization, ownership, evidence, concurrency, and workflow-AI tests.
* `src/portproject_rag/workflow.py` — DO-only revision authorization and
  editable-state enforcement.
* `web/src/main.tsx` — permission-aware workflow draft editing controls.
* `docs/hardening/PHASE_09_WORKFLOW_E2E.md` — this report.

Existing Phase 08 acceptance tests were rerun after the Phase 09 fix and passed
10/10. The project-wide Python suite passed **74 tests with 3 intentional
skips**. Ruff and the React production build both passed.

One early project-wide run encountered a transient local Ollama transport/model
failure while the acceptance API was under repeated RAG load. The API was
restarted, readiness re-verified, and the complete project-wide suite was rerun
successfully. No data or authorization defect was associated with that transient
runtime failure.

## Browser status and remaining blockers

The web package contains Vite/React/TypeScript but no configured Playwright,
Cypress, or Selenium runner. Browser-authenticated E2E is therefore **not
claimed**. The React production build is the available UI validation gate.

No tenant property-detail endpoint exists in the inspected route set, so this
phase does not claim isolation for a feature that is not implemented.

## Phase boundary

Phase 09 is complete. Work stops here as required; Phase 10 and all later
phases must be started explicitly in a separate request.
