# Tender publication audit

## Actual workflow

Tender context -> config -> eligible vacant plot export -> plot detail and source
snapshot -> LAC checklist evidence -> approved/manual proposal fields ->
deterministic calculation -> local workflow JSON state -> action/state
transition -> LAC, board-note, or tender markdown/PDF draft.

## Source-backed versus entered

Source-backed: eligible plot list, plot snapshot, mapping/source coverage, LAC
checklist labels/items, and configured source references.

Entered/approved: area when not prefilled, proposed use, tender method, lease
period, FSI, approved monthly SoR, escalation, discount, GST, and optional
charges. The service does not infer missing approvals.

## Calculation

The service calculates developed area, monthly/annual rent, escalation schedule,
discounted present values, GST, and optional charges. It reports steps and
source references. This is deterministic business calculation, not an ML model.

## State and artifacts

Workflow records are stored in target-project
src/portproject_rag/tender_workflow/data/tender_workflows.json. Available
actions are config-driven and validated against current status and requirements.
PDFs are generated through ReportLab and clearly marked as drafts.

## Risks

JSON persistence is not a multi-process transactional store. Corruption,
concurrent writers, backup, and deployment locking need an operational decision.
Moving it to PostgreSQL would require an approved migration, schema design,
backfill/rollback, and API compatibility tests; it must not be done merely for
architectural fashion.

## Validation

test_tender_workflow.py covers eligible vacant plots, deterministic calculation,
state/persistence, and PDF signature. Production publishing approval is NOT
VERIFIED and should remain a human-governed step.

