# Complete system verification

**Status: HISTORICAL — NOT CURRENT SOURCE OF TRUTH**

This folder contains the evidence-based acceptance audit requested for the
`portproject_rag` checkout. It is deliberately separate from application
source and from the historical audit notes in `docs/360_audit/`.

## Scope

The audit covers the 51 phases in the supplied **Complete End-to-End Project
Verification & Acceptance Audit** prompt: environment, dependencies, runtime,
database, authentication, authorization, dashboard, tenants, corpus,
ingestion, RAG, chat, workflow, billing, tender, failure handling, UI/API,
performance, accessibility, backup/recovery, security, documentation, and
final release gates.

This pass is verification only. It does not refactor source, change routes,
alter schemas, ingest documents, mutate conversations/agendas/workflows, or
change model configuration. Read-only SQL and existing automated tests were
used. Tests that require an authorized account, role-specific fixture, or
production-like backup are explicitly marked as blocked or not tested.

## Status vocabulary

- **PASS** — executed with evidence and the acceptance condition was met.
- **PARTIAL** — a bounded portion passed, but a required acceptance part is
  still unverified or has a known gap.
- **FAIL** — the observed condition conflicts with a required safety or
  acceptance condition.
- **BLOCKED** — the test could not be run without missing authorized access,
  fixture data, or an external dependency; it is not an inferred failure.
- **NOT TESTED** — intentionally not run in this non-destructive audit.

## Start here

1. [`SYSTEM_VERIFICATION_REPORT.md`](SYSTEM_VERIFICATION_REPORT.md) — executive
   result and release recommendation.
2. [`FINAL_VERIFICATION_MATRIX.md`](FINAL_VERIFICATION_MATRIX.md) — one row for
   every phase with expected result, actual evidence, status, risk, and next
   action.
3. [`BLOCKERS.md`](BLOCKERS.md) — blockers that must be resolved before the
   production or authenticated-demo gates can pass.
4. [`PRODUCTION_GATE.md`](PRODUCTION_GATE.md) — explicit production decision.
5. [`INTERVIEW_DEMO_GATE.md`](INTERVIEW_DEMO_GATE.md) — reproducible local demo
   path and what still needs an authorized operator.
6. [`00_BASELINE.md`](00_BASELINE.md) — immutable audit baseline and command
   scope.

The application source and runtime documentation remain under the project
root. This folder records what was actually verified; it does not replace the
source of truth in `src/`, `web/`, PostgreSQL, or the local Ollama service.
