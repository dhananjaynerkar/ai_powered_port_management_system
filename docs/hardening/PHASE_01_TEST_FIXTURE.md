# Phase 01 — Isolated acceptance-test fixture design

**Date:** 2026-08-24  
**Status:** **BLOCKED — APPROVED TEST DATABASE REQUIRED**  
**Scope:** Design and evidence only. No application source, production database, operational export, or user account was changed.

## 1. Phase gate

Phase 1 is the creation of a safe, isolated acceptance-test environment. This checkout does not currently contain an approved cloned database, sanitized source fixture, test credentials, or a designated test database. The live connection resolves to the operational `portproject` database. Therefore this phase stops at a non-executable fixture plan and manifest template.

The plan must not be executed against `portproject`, `public`, `rag`, `pms_doc`, or `pms_vector` in the operational database.

## 2. Evidence inspected

The following boundaries were inspected from the current checkout:

| Boundary | Verified implementation contract | Fixture implication |
| --- | --- | --- |
| Authority sign-in | `auth._external_authority` reads active `public.admin_users` joined to active `public.admin_roles`; accepted workflow roles are `DO`, `NO`, and `HO`. Password verification supports the existing database compatibility forms. | A fixture must contain approved, sanitized authority source rows and non-production credentials. Do not invent a login or copy a real password. |
| Tenant sign-in | `auth._external_tenant` reads active/approved rows from `public.applicant_registration` and verifies the stored password representation. | A fixture must contain one approved sanitized tenant source row and a separately issued test credential. |
| Sessions | `auth.create_session` stores an opaque token digest in the configured `rag.user_session`; `principal_id`, `username`, `display_name`, and `role` are persisted and `user_id` can be null for source-backed identities. | Session fixtures must be created through the application or a reviewed seed helper in the isolated database, then reset with the application-owned state. Never copy live session rows or cookies. |
| Local setup identity | `auth.create_initial_user` writes `rag.app_user` only when the table is empty and accepts only the legacy `authority`/`tenant` roles. | This is not a substitute for source-backed DO/NO/HO fixtures. It must not be used to create fake operational authority users. |
| Workflow identity | `workflow.authority_identity` and `officer_directory` re-read `public.admin_users`/`public.admin_roles`; transitions validate the active target role. | The isolated source snapshot must include one active DO, NO, and HO and the role relationships required for handoff. |
| Private chat | `rag.chat_session` is principal-scoped; `rag.chat_message` stores `user`/`assistant` messages and JSON `sources`. | Include one empty/normal private chat and one cited private chat under principal A. Include a second principal for isolation checks. |
| Chat-to-agenda | `workflow.create_agenda_from_chat` requires a principal-owned chat containing an assistant message with non-empty sources. | A workflow-linked chat must be created only after a cited answer fixture exists; the agenda must reference that session. |
| Official agenda | `rag.agenda`, `agenda_version`, `agenda_message`, and `context_capsule` implement `DO_DRAFT`, `SUBMITTED_TO_NO`, `RETURNED_TO_DO`, `SUBMITTED_TO_HO`, `APPROVED`, and `REJECTED`. | Seed one agenda per state needed by the acceptance matrix, with only valid owner/role assignments. Do not use fabricated live names or IDs. |
| Billing | `BillingPredictionService` reads source-backed values from `public.mcustomer`, `public.applicant_property_mapping`, `public.plot`, `public.tgeneralbill`, `public.m_structure_type`, `public.m_tax_rates`, and `public.m_tax_for_treecess_street_edu`, plus configured model/rule/tax-mapping artifacts. It writes no database rows. | Provide one complete and one incomplete sanitized tenancy/customer source case, plus a test-only artifact bundle. The incomplete case must intentionally exercise the documented validation path. |
| Tender | `TenderWorkflowService` reads the configured tender source exports/checklists and writes mutable workflow records to `tender_workflows.json` under its data directory. Commercial and approval values remain workflow inputs. | Copy only approved sanitized source exports/checklists into a fixture directory. Point storage at a temporary fixture file; never use the operational JSON state. |

### Runtime/database evidence

On 2026-08-24, the configured connection was inspected read-only:

- Current database: `portproject` (operational; **not** an acceptance database).
- Non-template databases visible to the connection: `portproject`, `postgres`.
- Schemas visible: `public`, `rag`, `pms_doc`, `pms_vector` plus PostgreSQL system schemas.
- No `test`, `test_rag`, or `acceptance` schema/table was present.
- No `tests/fixtures`, seed database, compose-based database, reset helper, or approved test-account file exists in this checkout.
- The local `.env` contains connection/model setting names, but no approved fixture declaration or test-credential contract was found. Secret values were not displayed.

## 3. Required isolated environment

The operator must provide one of these, before any fixture creation is executed:

1. A cloned database with sensitive fields sanitized and an explicit name/connection approved for destructive test resets; or
2. A sanitized SQL/CSV/JSON fixture bundle plus a newly created empty database and a documented load procedure.

The environment must be distinct from `portproject`. A recommended shape is:

```text
database: <approved acceptance database>
application schema: rag
document schema: pms_doc
vector schema: pms_vector
source schema: public (sanitized snapshot only)
tender workflow state: <temporary fixture path outside operational data/>
runtime: PORTPROJECT_RAG_DATABASE_URL=<approved isolated URL>
```

The application should be started with a dedicated environment file or process environment that changes only the connection/artifact roots. The production/local operational `.env` must not be edited as part of fixture setup.

### Isolation guardrails

Before a reset or seed operation, an operator-owned script must verify all of the following and abort otherwise:

- `current_database()` equals the approved acceptance database name.
- The connection user is the approved least-privilege test user.
- The database is not named `portproject`.
- A fixture sentinel/schema marker exists and matches the expected environment identifier.
- Tender `storage_path` resolves inside the fixture workspace, never under the operational source tree.
- No password, cookie, raw tenant export, or live session token is written to logs.

## 4. Fixture manifest (logical, not data)

The companion [`PHASE_01_FIXTURE_MANIFEST.example.json`](PHASE_01_FIXTURE_MANIFEST.example.json) is deliberately non-executable. It contains placeholders and acceptance requirements, not operational identifiers, passwords, SQL, or copied source data.

The required logical fixture is:

### Principals and access

- One sanitized Authority portal identity for each workflow role: DO, NO, and HO.
- One sanitized Tenant portal identity.
- Two distinct principal references (`principal_a` and `principal_b`) used to prove chat, agenda, and session isolation. The actual role assignment must be approved when the fixture is provisioned; this document does not choose real accounts.
- Passwords are provisioned through a one-time local secret handoff or approved seed mechanism and are never committed.

### Chat and evidence

- `private_empty`: a principal-owned chat with no messages.
- `private_cited`: a principal-owned chat containing a user question and an assistant answer whose `sources` JSON contains real fixture document/page metadata.
- `workflow_linked`: a chat owned by the DO principal and linked to an agenda created only from the cited chat path.
- A second-principal query must not list or read principal A's private sessions/messages.
- Citation metadata must point to the sanitized fixture corpus, not to an operational PDF path.

### Agenda/workflow

At minimum, create approved test-only records that exercise:

- DO draft owned by the DO fixture principal.
- Submission to NO with a valid active NO target.
- Submission to HO with a valid active HO target.
- Return to DO.
- Approved and rejected terminal states.
- A read-only view for a non-owner principal.

Each record must have a valid `agenda_version`; handoff records must have a matching `agenda_message` and `context_capsule`. The fixture must not bypass the transition API to create impossible owner/state combinations.

### Billing

- `billing_complete`: a sanitized tenancy/customer with enough source data for `/api/v1/billing/tenancies/{id}/prefill` and `/api/v1/billing/predict` to complete using the configured test artifact bundle.
- `billing_incomplete`: a sanitized tenancy/customer that intentionally lacks one or more required source values and is expected to return the documented validation/error state.
- Values must be copied from an approved sanitized source or explicitly approved test data. This phase does not invent amounts, rates, plot areas, customer IDs, or tenancy IDs.
- The billing model JSON, manifest, rules, and tax mapping are read-only runtime inputs; they are not trained or modified by this fixture phase.

### Tender

- One eligible vacant plot from an approved sanitized tender source snapshot.
- One approved test-only checklist key and its sanitized evidence rows.
- A draft workflow with only approved fields supplied through the normal create/action API.
- A temporary fixture `tender_workflows.json` state file, reset between runs.
- No operational owner contact, customer, tenancy, or commercial values are copied into a public repository.

## 5. Reset strategy

Reset must be explicit, repeatable, and scoped to the isolated environment:

1. Verify the database and fixture sentinel guardrails above.
2. Stop the test API and remove expired test sessions through the reset helper.
3. Restore the sanitized source snapshot (or recreate the approved source fixture schema) without touching operational `portproject`.
4. Re-run the idempotent application migration for `rag`, `pms_doc`, and `pms_vector` in the acceptance database.
5. Clear application-owned fixture rows in dependency order or recreate only the application schema in the acceptance database. Do not issue `DROP`, `TRUNCATE`, or `DELETE` against the operational database.
6. Load the approved corpus fixture and verify document/page/chunk/vector counts and citation metadata.
7. Copy the approved tender source snapshot to the fixture directory and reset its workflow JSON to the known empty state.
8. Seed identities and domain fixtures through a reviewed helper, recording only non-sensitive fixture labels and generated IDs in the test report.
9. Run the acceptance suite and archive the redacted result.

Preferred rollback is database replacement from the sanitized dump rather than ad-hoc row deletion. If a reset helper is later implemented, it must refuse to run unless the database identity and sentinel checks pass.

## 6. Acceptance matrix enabled by this fixture

| Area | Required proof |
| --- | --- |
| Authentication | DO/NO/HO/Tenant login succeeds only for the approved fixture credentials; invalid credentials are rejected; sessions expire and logout revokes the session. |
| Principal isolation | Principal B cannot list, read, delete, or promote principal A's private chat; workflow participants see only authorized agenda records. |
| Grounded chat | A cited answer includes only fixture corpus evidence and page-level sources; an empty corpus or unavailable generator returns the supported error state. |
| Agenda governance | Creation requires a cited answer; only the current owner and valid role can transition; terminal states are read-only. |
| Billing | Complete tenancy prefill/prediction succeeds; incomplete tenancy produces a clear validation result; no source tables are mutated. |
| Tender | Eligible plot/checklist load; missing approved inputs block the action; workflow state and documents are stored only in fixture state. |
| Reset/repeatability | A reset returns the acceptance database and tender state to the same known baseline without changing `portproject`. |

## 7. Blocker and next action

**Blocked:** no approved isolated database, sanitized fixture bundle, or test credentials were available in the checkout or configured database. Executing the requested users/records against the current `portproject` database would violate the Phase 1 safety boundary.

To unblock Phase 1, provide or approve an isolated database/fixture bundle and the non-secret mechanism for provisioning its test accounts. Then this manifest can be converted into a reviewed seed/reset helper and the acceptance suite can be run against that environment only.

Phase 1 stops here. Phase 2 hardening work must not start automatically.
