# Phase 01 — Isolated acceptance environment

Status: implemented and locally verified on 2026-08-25.

This phase adds a resettable acceptance environment for the existing
AI-Powered Port Management System application. It does not refactor application logic, alter the
production corpus, or copy operational rows or credentials.

## Safety boundary

The operational database remains `portproject`. Acceptance uses a separate
PostgreSQL database named `portproject_acceptance` and the `acceptance_fixture`
sentinel in `public.acceptance_environment`:

| Field | Required value |
| --- | --- |
| environment | `acceptance` |
| database_name | `portproject_acceptance` |
| fixture_version | `1` |

Every reset/check connection verifies both `current_database()` and the
sentinel before it can read or write. A connection that resolves to
`portproject` is refused. The provisioning command also refuses a maintenance
DSN that names either operational or acceptance database.

The acceptance database is synthetic. Its public tables reproduce only the
columns required by the current application contracts; no production rows,
PDFs, passwords, or tenant data are copied. Generated test passwords are
written only to the ignored file `tests/runtime/acceptance/credentials.json`
and are never printed by the tooling or stored in documentation.

## What is provisioned

`scripts/acceptance_fixture.py` creates the isolated database (when absent),
installs the `vector` and `pgcrypto` extensions through the existing migration,
creates the minimal source-table contract, and seeds deterministic synthetic
fixtures:

- Authority roles: DO, NO, and HO (`do_test`, `no_test`, `ho_test`).
- Two approved tenant principals (`tenant_test`, `tenant_second`).
- Two privacy-test principals with different roles: Principal A is the DO
  authority (`authority:10001`) and Principal B is the tenant
  (`tenant:20001`). The NO authority (`authority:10002`) is separately used as
  the workflow handoff owner.
- Three plots and two applicant-property mappings for dashboard/tenant flows.
- A complete billing source case (`ACCEPTANCE-TENANCY-001`) and an incomplete
  case represented by a missing customer row (`BILLING_INCOMPLETE`).
- Four one-page, 1024-dimensional RAG documents: public, authority, tenant,
  and role-restricted evidence. ACLs use the same role contract as retrieval.
- A truly empty private chat (zero messages), normal/cited chats, and a
  workflow-linked chat.
- Agenda states: `DO_DRAFT`, `SUBMITTED_TO_NO`, `RETURNED_TO_DO`,
  `SUBMITTED_TO_HO`, `APPROVED`, and `REJECTED`.
- One resettable LAC draft below `tests/runtime/tender`, created through the
  real tender service from an eligible bundled plot and checklist, plus a
  synthetic billing mapping CSV below `tests/runtime/acceptance`.

The tender service now honors `PORTPROJECT_RAG_TENDER_STORAGE_PATH`; acceptance
storage therefore cannot mutate the operational
`src/portproject_rag/tender_workflow/data/tender_workflows.json` file.

## Local setup

1. Copy `.env.acceptance.example` to `.env.acceptance`.
2. Set only the private acceptance `PORTPROJECT_RAG_DATABASE_URL` in that file.
   Do not commit `.env.acceptance`; it is ignored by Git.
3. Set `PORTPROJECT_RAG_ACCEPTANCE_ADMIN_DATABASE_URL` only in the current
   PowerShell process when provisioning. It must target a maintenance database
   such as `postgres`, never `portproject`, and is never written to a project
   file or passed as a command-line argument.
4. Run:

```powershell
.\scripts\provision_acceptance_fixture.ps1
```

The command is repeatable. It creates `portproject_acceptance` if needed and
then performs a guarded reset and check.

The real `.env.acceptance` is deliberately not included in this checkout: it
would contain a local database credential. The database was verified during
implementation using process-local variables only. An operator must provide
the acceptance credential before running the PowerShell wrappers; no password
is inferred, copied, printed, or committed by this phase.

## Reset, check, and run

```powershell
.\scripts\reset_acceptance_fixture.ps1
.\scripts\check_acceptance_fixture.ps1
.\scripts\start_acceptance.ps1 -ApiPort 8016 -WebPort 5180
```

`start_acceptance.ps1` loads the acceptance environment, checks the sentinel,
prints the UI command, and runs the API in the current terminal. The UI is
started separately from `web` on the printed port. To load the same variables
into another PowerShell terminal, dot-source:

```powershell
. .\scripts\load_acceptance_env.ps1
```

The acceptance API must report `portproject_acceptance` from `/health`. The
readiness endpoint also requires the local Ollama service and configured local
models; a missing Ollama/model is a dependency failure, not a database fixture
failure.

## Verification evidence

The following checks were run against the local instance:

- Acceptance fixture reset/check: passed; sentinel `acceptance/1` present.
- Safety refusal smoke: pointing the reset command at the operational
  `portproject` DSN aborted before opening a mutating fixture connection.
- Acceptance-only read-only tests: `3 passed`.
- Normal test suite: `54 passed, 3 skipped`.
- Acceptance-only read-only suite after reset: `3 passed` (including the
  zero-message `private_empty` invariant).
- Pure acceptance-safety guard tests: `4 passed`.
- Operational identity check: `current_database=portproject`, 49 documents and
  3,399 chunks; no `public.acceptance_environment` table was added there.
- Acceptance identity check: `current_database=portproject_acceptance`, four
  documents and four chunks, sentinel present.
- API `/health`: HTTP 200 with database `portproject_acceptance`.
- API `/health/ready`: HTTP 200 after local Ollama was available, with
  `rag_ready=true` and corpus counts of 4 documents, 4 pages, 4 chunks, and 4
  vectors.
- Authenticated acceptance API smoke: DO login, `/api/v1/auth/me`, dashboard
  metrics, tenant pagination, corpus, billing options/prefill, tender plots,
  and workflow agenda listing returned successfully; tenant login was denied
  authority metrics with HTTP 403.
- Direct authentication smoke: the synthetic DO authority and tenant
  principals authenticated successfully using the generated local credentials.
- Billing smoke: `ACCEPTANCE-TENANCY-001` appeared in tenancy options and
  source-backed prefill returned and the prediction path completed using the
  existing exported model/rules (with its documented fallback); the incomplete
  case remained absent.
- Tender smoke: bundled eligible plots loaded, the acceptance storage path was
  used, and a complete calculation returned `ready=true`.
- ACL retrieval smoke: authority retrieval returned authority/restricted/public
  evidence, while tenant retrieval returned only public/tenant evidence. The
  first CPU reranker load took about 48 seconds in this machine; this is a
  local model-startup cost, not a fixture or database failure.
- Frontend production build: `web/npm run build` passed; no web files were
  changed by this phase.

The first readiness probe correctly returned HTTP 503 while Ollama was not
listening. Once the local dependency was available, the same acceptance
database reached ready state without any fixture or migration change.

## Files added or changed

- `.env.acceptance.example` — placeholder-only local configuration.
- `.gitignore` — ignores `.env.acceptance` and `tests/runtime`.
- `scripts/acceptance_fixture.py` — guarded provision/reset/check and fixture
  generation.
- `scripts/provision_acceptance_fixture.ps1` — safe first-time provisioning.
- `scripts/reset_acceptance_fixture.ps1` — destructive action limited to the
  acceptance database after identity checks.
- `scripts/check_acceptance_fixture.ps1` — read-only fixture verification.
- `scripts/load_acceptance_env.ps1` — process-local environment loader.
- `scripts/start_acceptance.ps1` — checked API startup on acceptance settings.
- `tests/test_acceptance_fixture.py` — opt-in, read-only acceptance checks;
  skipped unless the explicit acceptance marker and DSN are supplied.
- `tests/test_acceptance_safety.py` — database-identity and tender-storage
  guard tests that never connect to PostgreSQL.
- `tests/test_tender_workflow.py` — verifies the isolated tender storage
  override.
- `src/portproject_rag/tender_workflow/tender_workflow_service.py` — reads the
  acceptance-only storage-path override while preserving the operational
  default.

## Explicit non-goals

This phase does not run Phase 8 browser E2E, does not tune retrieval or UI
behavior, does not copy operational documents, and does not change the
`portproject` database. Those are separate phases and require separate
approval.
