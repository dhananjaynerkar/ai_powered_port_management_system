# Production readiness

**Status: CURRENT SOURCE OF TRUTH**

This project is a verified local/internal development baseline, not an
automatic production approval. The status below separates what is demonstrated
from what still requires deployment-owner evidence.

| Target | Status | Evidence/condition |
| --- | --- | --- |
| Local demo | **PASS** | API/UI start instructions, health/readiness routes, frontend build, and the current Python suite are documented; the current Phase 16 checkpoint recorded 48 tests passing. |
| Controlled internal pilot | **CONDITIONAL** | Requires an approved database/fixture environment, HTTPS, secure cookies, explicit origins, private Ollama, and authenticated role/isolation acceptance. |
| Production | **NOT VERIFIED** | Requires the Phase 18 release gate, strong PostgreSQL TLS/least privilege, credential compatibility decision, backup/restore evidence, browser/accessibility matrix, performance targets, and failure-recovery evidence. |

## Promotion blockers

1. Use the `internal` or `production` `Settings` contract; do not carry local
   cookie/CORS/legacy-password defaults into production.
2. Provide a non-privileged database role and approved source-database access.
3. Resolve the legacy source-password strategy (migration, SSO, or isolated
   compatibility design) without rewriting source credentials implicitly.
4. Approve RPO/RTO, encryption, retention, and restore procedures.
5. Run authenticated cross-principal authorization, workflow concurrency,
   billing/tender, browser/accessibility, and RAG evaluation checks in an
   approved environment.
6. Complete the independent Phase 18 release decision.

## Historical material

Phase reports remain evidence records, not substitute production approval. The
older `docs/360_audit/` and `docs/system_verification/` folders are labelled
historical and should not override this document.
