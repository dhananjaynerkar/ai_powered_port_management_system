# Database and ownership

**Status: CURRENT SOURCE OF TRUTH**

The portal uses one PostgreSQL database configured by
`PORTPROJECT_RAG_DATABASE_URL`. It does not create or replace the PMS source
tables. The application migration creates an application-owned schema and two
read-oriented views schemas.

## Ownership boundary

| Area | Owner | Access pattern |
| --- | --- | --- |
| `public.*` PMS identities, plots, mappings, and billing reference data | Existing PMS/source system | Read-only queries from the portal; no portal migration owns these tables. |
| `rag.*` (or `PORTPROJECT_RAG_SCHEMA_NAME`) | PortProject RAG | Idempotent migration creates and maintains application state. |
| `pms_doc.*` | PortProject RAG read views | Views over document records in the configured RAG schema. |
| `pms_vector.*` | PortProject RAG read views | Views over chunks, embeddings, and ACL metadata. |
| Files under `artifacts/` and tender runtime data | Local application/runtime | Rebuildable or source-exported artifacts; not a substitute for source-system backup. |

## Application-owned tables

`src/portproject_rag/database.py` is the migration source. It creates:

- `document`, `document_page`, and `chunk`: PDF provenance, page text, chunks,
  full-text search vectors, ACL roles, and fixed-dimension embeddings.
- `app_user` and `user_session`: local portal principals and session state.
- `chat_session` and `chat_message`: principal-scoped private conversations and
  persisted answers/citations.
- `workflow_draft`: personal drafts forwarded from a private conversation.
- `agenda`, `agenda_version`, `agenda_message`, and `context_capsule`: official
  agenda ownership, revisions, messages, handoff snapshots, and evidence.
- `audit_event` and `login_attempt`: security/feature audit records and login
  rate-limit history.

The embedding column is declared as `vector(PORTPROJECT_RAG_EMBEDDING_DIMENSIONS)`;
the verified default is 1,024 dimensions. The migration also creates `vector`
and `pgcrypto` extensions, GIN indexes for lexical search/ACLs, and an HNSW
cosine index for embeddings.

## Source-system tables used by the portal

The current code references these source relations explicitly:

- identity and roles: `public.admin_users`, `public.admin_roles`,
  `public.applicant_registration`;
- land and tenant mapping: `public.plot`,
  `public.applicant_property_mapping`, `public.m_property_status`;
- billing sources: `public.tgeneralbill`, `public.mcustomer`,
  `public.m_structure_type`, `public.m_tax_rates`, and
  `public.m_tax_for_treecess_street_edu`.

The portal does not infer ownership of these relations from their names. The
SQL in `api.py`, `auth.py`, and `billing/prediction_service.py` is the evidence
for each dependency. Verify the live schema before deploying to a different PMS
database.

## Migration and reset

`portproject-rag migrate` (or the API lifespan) runs the idempotent migration.
It creates the configured schemas/views and backfills old documents from
`processing` to `indexed` when chunks exist, otherwise to `pending`. It does not
delete source rows. A reset must target an isolated database or schema; never
run destructive cleanup against the operational PMS database.

## Data integrity rules

- `document.file_sha256` and `source_path` are unique.
- Pages are unique per document/page number.
- Chunks are unique per document/chunk index and retain page provenance.
- Embedding dimension must match the configured dimension.
- Agenda states and roles are constrained by database checks and service-level
  authorization.
- Private chat and agenda access is filtered by principal/participant before
  retrieval or mutation.

## Backup boundary

The RAG schema and local workflow state are application-owned and should be
included in an approved backup. PMS `public.*` data is an external recovery
dependency unless the PMS owner provides a sanctioned backup/export. See
[Backup and recovery](BACKUP_AND_RECOVERY.md) and the Phase 03 drill for the
verified boundary; no backup should overwrite an operational database.
