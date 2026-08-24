# Tender Publication workflow

The target project now contains a separate, source-backed Tender Publication workflow copied from the reference project. The reference checkout is not imported at runtime and is not modified.

## Target boundaries

- Backend service: `src/portproject_rag/tender_workflow/`
- Source configuration: `src/portproject_rag/tender_workflow/config/tender_workflow.json`
- Source exports and evidence: `src/portproject_rag/tender_workflow/data2/`
- Persisted workflow records: `src/portproject_rag/tender_workflow/data/tender_workflows.json`
- React dialog: `web/src/main.tsx` (`TenderPublicationModal`)
- Dialog styling: `web/src/styles.css`

The copied `tender_plot_master.csv` is used only to populate the eligible-vacant-plot selector and source snapshot. Historic tenancy, FSI, rate, and approval values are not treated as approvals for a new tender.

## Authenticated API

Authority users can access:

- `GET /api/v1/tender/config`
- `GET /api/v1/tender/plots`
- `GET /api/v1/tender/plots/{plot_id}`
- `GET /api/v1/tender/checklists/{checklist_key}`
- `POST /api/v1/tender/calculate`
- `GET /api/v1/tender/workflows`
- `POST /api/v1/tender/workflows`
- `GET /api/v1/tender/workflows/{workflow_id}`
- `POST /api/v1/tender/workflows/{workflow_id}/actions`
- `GET /api/v1/tender/workflows/{workflow_id}/documents/{lac|board-note|tender}`

All routes use the target project's existing session authentication and authority-role guard. Workflow actions are validated against the copied state machine. Returns require a comment; proposal fields and approved calculation inputs are validated before later stages can be generated or published.

## UI flow

Choose **Tender Publication Workflow** from the AI Assistant context selector. The dialog loads the current source exports, supports a new or existing workflow, pre-fills only source-backed plot/checklist values, lets an officer enter approved inputs, calculates the financial schedule, edits LAC evidence, executes the available state transition, and downloads reviewable PDF drafts.

The API remains the source of truth for eligibility, checklist content, calculation readiness, action availability, and persisted state. The UI does not hard-code commercial rates or approvals.

## Verification

Focused coverage is in `tests/test_tender_workflow.py`. It verifies eligible plot loading, deterministic calculation, state transition validation, and PDF generation. The target API's unauthenticated tender request returns `401`, while the OpenAPI contract exposes the tender routes; authenticated access is required by design.
