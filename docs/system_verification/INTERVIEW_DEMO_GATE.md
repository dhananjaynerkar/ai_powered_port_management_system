# Interview/demo gate

## Decision

**BLOCKED for a fully authenticated end-to-end demo.**

The local services are running and the project has a reproducible start path,
but an honest demonstration of login, dashboard data, tenant filtering, RAG
answers/citations, agenda creation, workflow handoff, billing, and tender
actions requires approved non-production credentials and safe fixture data.

## What is demonstrably ready locally

From the target project root:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check src tests
npm --prefix web run build
.
start_app.ps1
```

The current local endpoints are:

- UI: `http://127.0.0.1:5173`
- API liveness: `http://127.0.0.1:8001/health`
- API readiness: `http://127.0.0.1:8001/health/ready`

The local health/readiness and production build checks passed during this
audit. The exact model/corpus counts are in [`00_BASELINE.md`](00_BASELINE.md).

## What must not be improvised during a demo

- Do not use a real user’s password or reveal database password columns.
- Do not create a first account to bypass the existing database-backed login.
- Do not claim a grounded answer until the response contains verified source
  pages.
- Do not mutate operational agendas, billing records, tender workflows, or
  source documents merely to make a screenshot.
- Do not claim that `is_vacant=true` and status `V` mean the same thing.

## Required demo fixture

Provide a non-production dataset or cloned database with:

1. one approved Authority account for dashboard/tenant/RAG access;
2. one DO, one NO, and one HO account for workflow ownership tests;
3. one Tenant account for tenant isolation;
4. one private chat with a cited answer;
5. one unlinked private chat and one workflow-linked chat for delete behavior;
6. one agenda in each relevant state;
7. one complete billing tenancy and one source-incomplete tenancy; and
8. one eligible vacant plot plus approved tender/checklist inputs.

Once supplied, run the browser and API steps in the final matrix and attach
screenshots/logs to this folder. Until then, the safe claim is **local build
and service smoke verified; authenticated product demo pending**.
