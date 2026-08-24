# Phase 9 - agenda workflow acceptance

Status: **BLOCKED - DISPOSABLE TEST AGENDA REQUIRED**

Completed: 2026-08-25

## Gate and scope

Phase 9 requires disposable/test agenda records and the approved isolated
fixture from Phase 1. Phase 1 remains blocked and Phase 8 documented the same
missing fixture. The configured database is operational portproject.

No agenda was created, revised, submitted, returned, approved, rejected, or
deleted. No transition request, concurrent request, or reset was sent to the
operational database. This report separates static code evidence from runtime
acceptance evidence.

## Static state-machine evidence

| File | Function/class | Verified from source | Result |
|---|---|---|---|
| src/portproject_rag/database.py | agenda table | States are constrained to DO_DRAFT, SUBMITTED_TO_NO, RETURNED_TO_DO, SUBMITTED_TO_HO, APPROVED, and REJECTED. | **PASS - static only** |
| src/portproject_rag/workflow.py | create_agenda_from_chat | Requires an active DO identity, principal-owned chat, and an assistant message with non-empty sources; inserts version 1 and a system message. | **PASS - static only** |
| src/portproject_rag/workflow.py | transition_agenda | Defines role/state/action rules, validates active target officers, updates owner/state, creates context capsule and HANDOFF message. | **PASS - static only** |
| src/portproject_rag/workflow.py | save_agenda_revision | Locks the agenda row, increments editing_version, inserts agenda_version, updates the agenda, and records a system message. | **PASS - static only** |
| src/portproject_rag/api.py | workflow routes | Exposes create, read, revision, transition, and agenda-query routes through current_user. | **PASS - static only** |

## Valid lifecycle acceptance matrix

The following is the required runtime test sequence. Every actual result is
**NOT VERIFIED** because the disposable fixture does not exist.

| Step | State/owner before | Actor/action | Expected state/owner after | Required evidence | Result |
|---|---|---|---|---|---|
| 1 | cited private chat owned by DO | DO creates agenda | DO_DRAFT, DO, version 1 | API response, agenda/version/message rows | **NOT VERIFIED** |
| 2 | DO_DRAFT, DO | DO submits to active NO | SUBMITTED_TO_NO, NO | target validation, state/owner, HANDOFF, capsule | **NOT VERIFIED** |
| 3 | SUBMITTED_TO_NO, NO | NO returns to DO | RETURNED_TO_DO, DO | state/owner, HANDOFF, capsule | **NOT VERIFIED** |
| 4 | RETURNED_TO_DO, DO | DO saves revision | RETURNED_TO_DO, DO, version 2 | version row, editing_version, system message | **NOT VERIFIED** |
| 5 | RETURNED_TO_DO, DO | DO resubmits to NO | SUBMITTED_TO_NO, NO | state/owner, history, capsule version | **NOT VERIFIED** |
| 6 | SUBMITTED_TO_NO, NO | NO submits to active HO | SUBMITTED_TO_HO, HO | target validation, state/owner, history | **NOT VERIFIED** |
| 7 | SUBMITTED_TO_HO, HO | HO approves | APPROVED, HO, finalized_at set | terminal state, history, capsule, UI read-only | **NOT VERIFIED** |
| 8 | SUBMITTED_TO_HO, HO | HO rejects (if selected) | REJECTED, HO, finalized_at set | terminal state and history | **NOT VERIFIED** |

## Invalid-transition matrix

| Case | Expected backend behavior | Runtime result |
|---|---|---|
| Wrong role | 403/409; no state or history mutation | **NOT VERIFIED** |
| Wrong owner | 409; no mutation | **NOT VERIFIED** |
| Wrong current state | 409; no mutation | **NOT VERIFIED** |
| Wrong/inactive recipient | 422; no mutation | **NOT VERIFIED** |
| Duplicate submit | 409; exactly one prior outcome remains | **NOT VERIFIED** |
| Stale client/revision | Must be tested for lost-update behavior | **NOT VERIFIED** |
| Missing target officer | 422; no mutation | **NOT VERIFIED** |
| Already approved/rejected | 409/read-only; no mutation | **NOT VERIFIED** |

## Concurrency and transaction review

Static review found PostgreSQL row locks in transition_agenda and
save_agenda_revision using SELECT ... FOR UPDATE. This is evidence that
competing transitions on the same agenda are serialized by the database
transaction; it is not a completed concurrency proof.

The current revision request does not carry an expected editing_version. The
implementation locks the row and increments the current version, but a stale
client can therefore be serialized after a newer edit rather than rejected as
a stale write. This is a measured static risk, not a production change made in
this blocked phase. A disposable concurrent test must determine whether this
behavior is acceptable before any version-check change is considered.

add_agenda_message first calls agenda_detail on one connection and inserts on a
second connection. The read-only check therefore also requires a runtime
race/permission test; it was not treated as proven from static inspection.

## Required acceptance evidence after unblocking

For each lifecycle and invalid/concurrent request, record:

    disposable fixture label
    state and owner before
    authenticated actor role/principal label
    request route and payload classification
    expected and actual status
    state and owner after
    agenda_version, agenda_message, and context_capsule rows
    database mutation/no-mutation
    transaction/concurrency outcome
    UI read-only or editable state

Never record passwords, session tokens, raw tenant data, or operational IDs in
the acceptance artifact.

## Blocker and stop condition

**BLOCKED:** provide/approve the Phase 1 isolated database or sanitized fixture
bundle, disposable DO/NO/HO principals, cited private chat, and reset helper.
Only then can the lifecycle and concurrency requests be executed safely.

Phase 9 stops here. No workflow data was changed and Phase 10 was not started.

## Non-mutating repository validation

| Check | Result |
|---|---|
| Python tests | **PASS - 45 passed** |
| Ruff | **PASS - all checks passed** |
| Python compile check | **PASS** |
| React production build | **PASS - 1,670 modules** |
| Workflow acceptance E2E | **BLOCKED - disposable fixture unavailable** |
