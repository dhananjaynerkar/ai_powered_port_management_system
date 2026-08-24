# Production-readiness scorecard

Scores are not a substitute for acceptance. They summarize evidence and use a
conservative scale: Ready, Partial, Not ready, or Not verified.

| Area | Status | Evidence/why |
| --- | --- | --- |
| Architecture | Partial | Coherent modular monolith; large UI/API modules remain. |
| Code organization | Partial | Clear Python feature modules; frontend concentration is high. |
| RAG pipeline | Implemented | Full code path and readiness contract exist. |
| RAG quality | Not verified | No reviewed Recall/MRR/faithfulness score set. |
| Data correctness | Partial | Terminology/quality counters exist; business mappings need sign-off. |
| Authentication | Implemented locally | Database identities and opaque sessions tested indirectly; role E2E missing. |
| Authorization | Partial | Backend checks exist; adversarial cross-role tests missing. |
| Database | Partial | Idempotent migration/views and live schema observed; backup/restore unverified. |
| Reliability | Partial | Health/readiness and graceful errors exist; supervisor/alerting absent. |
| Observability | Partial | Timings/logs/audit events exist; centralized telemetry absent. |
| Testing | Partial | 31 tests pass; UI/E2E/security/performance gaps remain. |
| Frontend UX | Implemented | Build passes and feature states exist; authenticated visual matrix unverified. |
| Accessibility | Not verified | No complete keyboard/screen-reader audit. |
| Performance | Not verified | Timings exist, but no baseline/p95 targets or query plans. |
| Documentation | Strong baseline | Current docs and this 360-degree package exist. |
| Deployment | Local only | Launcher is Windows local; HTTPS/secret/backup deployment work remains. |

## Production gate

Do not expose externally until P1 security decisions, backup/restore, role
acceptance, ACL tests, reviewed RAG evaluation, and operational monitoring are
completed.

