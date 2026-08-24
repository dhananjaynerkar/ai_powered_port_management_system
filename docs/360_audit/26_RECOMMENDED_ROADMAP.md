# Evidence-based roadmap

## Phase 0 — Verify correctness

Priority P0/P1. Confirm business terminology for plot statuses, occupancy,
mapping rows, tenancy identifiers, billing source precedence, and agenda
approval. Validate with domain owners and fixture tests.

## Phase 1 — Critical fixes

Priority P1. Decide source password remediation, enforce HTTPS/secure cookies,
least-privilege roles, CORS deployment origins, and backup/restore for rag and
tender state. Validate with security and recovery tests.

## Phase 2 — Testing and evaluation

Priority P1/P2. Build reviewed RAG questions with expected pages; measure
Recall@K, MRR, citation accuracy, faithfulness, answer relevance, and p50/p95
latency. Add ACL, role, workflow concurrency, tender corruption, and billing
holdout tests.

## Phase 3 — Maintainability

Priority P2. Extract shared citation/Markdown components, then assistant,
workflow, dashboard, tenant, and feature-modal boundaries. Preserve imports,
build, state behavior, and authenticated UI tests at each step.

## Phase 4 — UX/accessibility

Priority P2. Test 1024/1280/1366/1440/1920 widths, keyboard navigation,
screen-reader labels, chart alternatives, long source names, loading/error
states, and role-specific disabled controls.

## Phase 5 — Production hardening

Priority P1/P2. Add process supervision, secrets management, structured logs,
metrics/alerts, database backup, deployment docs, dependency scanning, and
incident runbooks.

## Phase 6 — Optional enhancements

Only after metrics justify them: higher-quality table/OCR adapters, deeper
metadata filtering, transactionally migrated tender state, or graph retrieval.

Each task requires source diff, targeted tests, full regression checks, and
rollback notes.

