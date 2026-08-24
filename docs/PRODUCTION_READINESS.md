# Production readiness

This legacy readiness note is retained for historical context. It described an
early corpus-only milestone and is no longer the source of truth for the
running portal.

For the current verified deployment contract, use:

- [Operations](OPERATIONS.md) for live health/readiness checks and local start-up.
- [Architecture](ARCHITECTURE.md) for the current PostgreSQL, pgvector, RAG,
  dashboard, billing, tender, and workflow boundaries.
- [Audit](AUDIT_2026-08-24.md) for current evidence-backed risks and deployment
  requirements.

The portal still requires a deployment review before any non-local exposure:
configure HTTPS/cookie security, replace or remediate legacy source password
storage, apply network/database least privilege, and perform authenticated
end-to-end acceptance testing.
