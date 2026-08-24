# Project structure audit

## Current categorized structure

### Source code

- src/portproject_rag/api.py: FastAPI HTTP boundary and route orchestration.
- src/portproject_rag/auth.py: database identity and session security.
- src/portproject_rag/database.py: migrations and application-owned views.
- src/portproject_rag/ingestion.py, inspection.py, strategy.py, quality.py,
  ocr.py, table_processing.py: document pipeline.
- src/portproject_rag/retrieval.py, generation.py, guardrails.py: RAG query
  pipeline.
- src/portproject_rag/workflow.py: official agenda workflow.
- src/portproject_rag/billing/: billing services and training helpers.
- src/portproject_rag/tender_workflow/: tender service, configuration, sources,
  local records, and PDF renderer.
- web/src/main.tsx and web/src/styles.css: React application and UI styling.

### Configuration

- pyproject.toml: Python metadata, dependencies, packaging, pytest, Ruff, and
  mypy settings.
- web/package.json and web/package-lock.json: frontend dependencies and build.
- .env.example: safe configuration template.
- start_app.ps1 and Start_App.cmd: Windows runtime launcher.

### Data and model artifacts

- artifacts/billing_forecast/: billing model, manifest, rules, and data.
- src/portproject_rag/tender_workflow/data2/: copied source-backed tender
  exports and evidence files.
- src/portproject_rag/tender_workflow/data/tender_workflows.json: tender
  workflow persistence.

### Generated output and runtime state

- artifacts/: reports, logs, model/runtime outputs.
- web/dist/: Vite build output.
- runtime_logs/: launcher/runtime logs.
- .pytest-tmp, caches, __pycache__: generated test/tool state.

Generated directories should not be treated as source. Existing generated files
were not deleted during this audit.

### Tests

tests/ covers authority metrics, tenant pagination, billing, chat payloads,
database migration, guardrails, inspection, live corpus evaluation, strategy,
and tender workflow.

### Documentation

docs/ contains current guides, historical reports, integration notes, and this
360_audit package. Historical documents should not override current source code.

## Move/reorganization judgment

| Area | Judgment | Reason |
| --- | --- | --- |
| pms_api.app.py wrapper | Keep | The server command targets the factory path. |
| billing and tender packages | Keep | They are coherent feature boundaries with tests. |
| web/src/main.tsx | Keep for now | Large and risky to split without UI regression tests. |
| web/src/styles.css | Keep for now | Shared selectors and responsive overrides are cross-feature. |
| generated build/cache output | Ignore | Reproducible from source; no deletion performed. |
| docs/360_audit | Add | Separates the requested audit evidence from operational docs. |

## Future target structure

A gradual future structure could split web/src into app shell, shared evidence
components, assistant, workflow, dashboard, tenants, and feature modals. This
is a recommendation only; moving files requires import mapping, build
validation, and authenticated UI tests.

