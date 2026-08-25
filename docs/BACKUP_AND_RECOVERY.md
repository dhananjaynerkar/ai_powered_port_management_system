# Backup and recovery

**Status: CURRENT SOURCE OF TRUTH**

Recovery must reconstruct both application-owned state and its external source
dependencies. PostgreSQL persistence alone is not a complete recovery plan.

## State inventory

| State | Ownership | Recovery treatment |
| --- | --- | --- |
| `rag.*` tables and `pms_doc`/`pms_vector` views | Application | Include in an approved PostgreSQL backup; views can be recreated by migration. |
| `public.*` PMS tables | Source system | Recover from the PMS owner/export; the portal must not fabricate or overwrite them. |
| PDF corpus and source hashes | Source/ingestion input | Preserve originals or the approved corpus source; embeddings/chunks are rebuildable only when originals are available. |
| Ollama models and reranker cache | Local runtime | Re-download/reinstall through an approved offline/internal process; record model names/configuration. |
| Billing runtime artifacts | Application artifact bundle | Back up model manifest, model, rules, tax mapping, and required source exports together. |
| Tender JSON store and source exports | Application/local workflow | Back up atomically; JSON persistence is currently single-process/local scope. |
| `.env` and credentials | Secret material | Recreate from a secret-management process; never back up into Git or this documentation. |

## Safe drill requirements

The Phase 03 report defines the isolated restore drill. A valid drill uses a
cloned database/restore target and verifies:

1. PostgreSQL schema and `vector`/`pgcrypto` extensions;
2. row/count and embedding-dimension sanity;
3. migration/view recreation;
4. API startup, `/health`, and `/health/ready`;
5. representative read-only dashboard, corpus, and RAG queries;
6. billing/tender artifact availability;
7. no write against the operational database.

## RPO/RTO decisions

Retention, encryption, backup location, RPO, and RTO are deployment-owner
decisions. They must not be invented from this local project. Record approved
values in the operational runbook before an internal or production launch.

## Recovery limitation

If the PMS owner cannot provide a recoverable `public.*` export or service,
restoring the RAG schema alone will not recreate dashboard, tenant, authority,
or billing source behavior. Treat that dependency as an explicit recovery risk.
