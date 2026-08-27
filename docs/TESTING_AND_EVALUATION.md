# Testing and evaluation

**Status: CURRENT SOURCE OF TRUTH**

The project uses pytest for Python regression/integration checks, Ruff for
static linting, and the Vite/TypeScript production build for the frontend.

## Standard checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check src tests
Set-Location web
npm run build
```

The latest local checkpoint is recorded in
`docs/hardening/RAG_CAPACITY_RESOURCE_CERTIFICATION.md`: the non-acceptance
suite completed with **102 passed and 28 skipped**. That result is an observed
checkpoint, not a promise that a new machine has the same database, Ollama
models, or fixture artifacts. The skipped tests are environment/acceptance
dependent and are not counted as passes. The guarded Phase 08/09 acceptance
suite is a separate **21-test** run against `portproject_acceptance`.

## Test areas

| Area | Representative tests/evidence |
| --- | --- |
| Settings/security | `test_security_settings.py`, authentication/guardrail tests |
| Database migration | `test_database_migration.py` |
| Dashboard/tenants | `test_authority_metrics.py`, `test_tenant_pagination.py` |
| RAG/ingestion | `test_inspection.py`, `test_strategy.py`, corpus/evaluation tests |
| Capacity/resilience | `test_rag_capacity.py`, `test_resilience_observability.py`, and `scripts/rag_capacity_profile.py` |
| Chat/guardrails | `test_chat_payload.py`, `test_guardrails.py` |
| Billing | `test_billing_service.py` and Phase 10 validation report |
| Tender | `test_tender_workflow.py` and Phase 11 persistence report |
| Resilience/observability | `test_resilience_observability.py` and Phase 13 report |

## RAG evaluation

The reviewed golden set is `evaluation/rag_gold_v1.json`. Phase 06 defines how
questions and expected source/page evidence were reviewed; Phase 07 records the
current-pipeline baseline and raw evidence. Do not replace the reviewed set with
automatically generated expectations, and do not report an arbitrary “accuracy
percentage” in place of retrieval/answer metrics.

## Test data boundary

Live database and source-backed tests require an approved isolated database and
fixture bundle. Credentials, raw tenant data, and operational workflow records
are intentionally excluded from Git. Never reset or mutate the production PMS
database as part of a test.

## Acceptance interpretation

- A passing build proves compilation/bundling, not database readiness.
- HTTP 200 `/health` proves process health, not RAG readiness.
- `/health/ready`, authenticated UI checks, authorization matrix, workflow
  lifecycle, backup/restore, and clean-install checks are separate evidence.
- Performance and model-quality claims require the conditions and artifacts
  documented in their phase reports.
