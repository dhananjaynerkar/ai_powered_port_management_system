# Tender publication workflow

**Status: CURRENT SOURCE OF TRUTH**

Tender publication is an Authority-only, source-backed workflow implemented by
`src/portproject_rag/tender_workflow/tender_workflow_service.py`. It uses a
versioned JSON store under the tender runtime directory, not a PostgreSQL
tender-state migration.

## Flow

```text
eligible vacant plot
  -> LAC checklist and source snapshot
  -> proposal/approved financial inputs
  -> deterministic calculation
  -> LAC draft/submission/approval
  -> Board Note draft/submission/approval
  -> calculation finalized
  -> Tender/RFP draft
  -> NIT submission/approval
  -> published
```

The eligible plot list is loaded from the configured source export. Selected
plot details and checklist documents provide evidence/prefill; approved
proposal inputs remain explicit form fields. Historic values are references,
not automatic approvals for a new tender.

## State machine

The current configuration (`config/tender_workflow.json`) defines:

`LAC_DRAFT → LAC_SUBMITTED → LAC_APPROVED → BOARD_NOTE_DRAFT →
BOARD_NOTE_SUBMITTED → BOARD_NOTE_APPROVED → CALCULATION_FINALIZED →
TENDER_DRAFT → NIT_SUBMITTED → NIT_APPROVED → PUBLISHED`.

Return actions move LAC, Board Note, or NIT back to their draft state and
require a comment. Each action validates the current state and required fields.

## Persistence and documents

Workflow records are stored in `tender_workflows.json` under the configured
tender data directory. The service writes the record and supports reload after
restart. It generates PDF drafts for `lac`, `board-note`, and `tender` through
the local ReportLab renderer.

The JSON store is appropriate only for the approved local/single-process scope.
Multi-process or production use requires the Phase 11 PostgreSQL persistence
decision and migration; this phase does not silently make that change.

## API

See [API reference](API_REFERENCE.md#tender-publication) for the route list.
The UI uses `/api/v1/tender/config`, plot/checklist reads, calculation, workflow
creation/actions, reload, and PDF download endpoints.

## Source boundaries

The tender service does not infer missing approvals, rates, FSI, or proposed use.
Required fields and source availability are surfaced to the operator. The
exported `tender_plot_master.csv` and related references must come from an
approved source export and should never be replaced with invented rows.
