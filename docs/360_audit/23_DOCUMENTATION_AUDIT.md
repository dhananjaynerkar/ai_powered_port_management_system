# Documentation audit

## Current documentation status

| Topic | Source of truth | Status |
| --- | --- | --- |
| Architecture | docs/ARCHITECTURE.md and 360_audit/04 | Current/verified |
| Setup/operations | docs/OPERATIONS.md and 360_audit/18 | Current/verified |
| APIs | docs/API_REFERENCE.md and 360_audit/17 | Current route map |
| RAG strategy | docs/FINAL_ARCHITECTURE.md plus 360_audit/08/09/10 | Current with metric gaps |
| Database | 360_audit/06 | Current code-derived |
| Workflow | 360_audit/14 | Current code-derived |
| Billing | docs/BILLING_FORECAST_INTEGRATION.md plus 360_audit/15 | Partially verified |
| Tender | docs/TENDER_PUBLICATION_INTEGRATION.md plus 360_audit/16 | Current implementation |
| Testing/evaluation | 360_audit/19 | Current observed suite |
| Security/deployment | 360_audit/11 and docs/PRODUCTION_READINESS.md | Current risk guidance |
| Interview explanation | 360_audit/27 | This audit artifact |

## Historical/stale documents

IMPLEMENTATION_AUDIT.md and EVALUATION_REPORT.md contain early pre-database
claims and are now explicitly marked historical. They should not be deleted
because they record earlier evidence.

## Missing before this audit

There was no single 360-degree report, evidence index, feature maturity matrix,
technical debt register, failure matrix, or interview defense guide. This folder
supplies those missing documents without changing application code.

## Documentation maintenance rule

When a route/schema/model changes, update the relevant current source-of-truth
document and the evidence index. Date historical reports rather than silently
rewriting them.

