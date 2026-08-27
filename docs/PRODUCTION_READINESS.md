# Production readiness

**Status: CURRENT SOURCE OF TRUTH**

This project is a verified local/internal development baseline, not an
automatic production approval. The status below separates what is demonstrated
from what still requires deployment-owner evidence.

| Target | Status | Evidence/condition |
| --- | --- | --- |
| Local demo | **CONDITIONAL PASS** | The API/UI, readiness path, frontend build, full Python suite, guarded Phase 08/09 acceptance E2E, and bounded local capacity gate are verified; the demo still depends on local PostgreSQL/Ollama, ignored runtime artifacts, and a one-heavy-request CPU envelope. See [capacity certification](hardening/RAG_CAPACITY_RESOURCE_CERTIFICATION.md). |
| Controlled internal pilot | **NOT VERIFIED** | The current 15.65 GiB host reached unsafe memory headroom during measured RAG pairs. Authenticated browser/accessibility evidence, deployment-owner security settings, recovery sign-off, and multi-user tender storage are also not verified for a pilot topology. |
| Production | **FAIL** | Deployment-owner security/recovery decisions, human semantic review, hardware-backed capacity, and multi-process tender persistence remain open. See [FINAL_RELEASE_GATE.md](release/FINAL_RELEASE_GATE.md) and the [capacity certification](hardening/RAG_CAPACITY_RESOURCE_CERTIFICATION.md). |

## Promotion blockers

1. Use the `internal` or `production` `Settings` contract; do not carry local
   cookie/CORS/legacy-password defaults into production.
2. Provide a non-privileged database role and approved source-database access.
3. Resolve the legacy source-password strategy (migration, SSO, or isolated
   compatibility design) without rewriting source credentials implicitly.
4. Approve RPO/RTO, encryption, retention, and restore procedures.
5. Resolve the remaining RAG and release blockers: human citation/semantic
   review, hardware-backed runtime capacity, production security, recovery, and
   multi-process tender storage.
6. Re-run the authenticated browser/accessibility and deployment-owner checks
   before proposing an internal pilot or production promotion.

## Historical material

Phase reports remain evidence records, not substitute production approval. The
older `docs/360_audit/` and `docs/system_verification/` folders are labelled
historical and should not override this document.
