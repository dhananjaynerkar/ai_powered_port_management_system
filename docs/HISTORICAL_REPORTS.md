# Historical reports

**Status: INDEX — NOT CURRENT SOURCE OF TRUTH**

These packages preserve prior audits and acceptance evidence. They are useful
for traceability, but current architecture, operations, security, feature, and
release decisions live in the top-level documents linked from `README.md`.

| Location | Meaning |
| --- | --- |
| `docs/360_audit/` | Historical 360-degree audit package and its original evidence index. |
| `docs/system_verification/` | Historical end-to-end verification and release-gate records. |
| `docs/hardening/PHASE_*.md` | Evidence report for the named hardening phase; phase reports are not a substitute for the current source-of-truth documents. |
| `docs/AUDIT_*.md`, `docs/IMPLEMENTATION_AUDIT.md`, `docs/EVALUATION_REPORT.md`, and similar dated/integration notes | Historical or feature-specific evidence unless explicitly linked as current by the top-level docs. |

When an older report conflicts with current code or the current documentation
hierarchy, verify against the source and the latest phase evidence before using
the claim. Do not delete historical reports merely to hide disagreement.
