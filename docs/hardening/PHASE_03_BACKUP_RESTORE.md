# Phase 3 — Backup and disaster-recovery drill

Status: **PARTIAL — isolated application-schema recovery passed; full
production-data recovery is blocked pending an approved sanitized backup and
retention policy.**

This drill never restored over `portproject`, never copied rows from the PMS
`public` schema, and never uploaded a backup artifact. The temporary restore
database was removed after validation.

## State inventory

| State | Actual location | Recovery treatment |
|---|---|---|
| Source-system data | `public.*` PMS identities, plots, mappings, billing, and tender source exports | External recovery dependency. No source rows were copied because an approved sanitized backup/authorization was not available. |
| Application-owned state | `rag.*` sessions, chats, agendas, workflow drafts, messages, capsules, audit events, documents, pages, and chunks | Must be included in an approved production logical/physical backup. The drill restored its schema only and used synthetic rows. |
| Read views | `pms_doc.*`, `pms_vector.*` | Derived/rebuildable from `rag.*`; restored and validated as views. |
| Vector search state | `rag.chunk.embedding`, pgvector extension, embedding model/dimension settings | Embeddings are derived but expensive to rebuild. The extension and `vector(1024)` type were validated; production backup policy must decide whether to retain vectors or rebuild them. |
| Document corpus | Original PDFs and extraction/provenance inputs outside this public repository | Required to rebuild pages/chunks. No corpus files were copied in this drill. Maintain an approved immutable corpus backup. |
| Billing runtime | `artifacts/billing_forecast/runtime` model/rules/mapping artifacts, plus training/source inputs | Generated/rebuildable artifacts must be versioned or backed up with their manifest; raw training inputs remain a separate approved data dependency. |
| Tender workflow state | `src/portproject_rag/tender_workflow/data/tender_workflows.json` | Irreplaceable application workflow state until moved to a transactional table. It was not copied in this drill because the operational JSON is excluded from the public repository and no backup authorization was provided. |
| Configuration and models | `.env` secrets, `.env.example`, local Ollama model names, reranker configuration | `.env` must be provisioned from a secret store and is never backed up to Git. Keep the sanitized template and model manifest; retain model binaries through an approved local/private artifact process. |

## Isolated drill performed

### Backup

- Source database: local `portproject` (read-only for data purposes).
- Backup scope: schema-only custom-format dump of `rag`, `pms_doc`, and
  `pms_vector`.
- Backup artifact: `artifacts/phase3_backup_restore/` (ignored by Git and kept
  local); the generated dump was approximately 29 KB.
- The dump contained no `TABLE DATA`, `BLOBS`, or ACL entries.
- A SHA-256 checksum was recorded locally for the generated artifact:
  `ae8c99d8c6f62bc8f309e6711b92545bbad2ae0d6f4d97f04f66e0a6a47cd5c6`.

### Restore target

- Created a uniquely named temporary PostgreSQL database from `template0`.
- Created `vector` and `pgcrypto` extensions in that target.
- Restored the schema-only dump with ownership and ACL restoration disabled.
- Inserted one synthetic, non-sensitive document, page, and 1024-dimensional
  chunk solely to prove safe row/view/vector behavior.
- No `public` PMS rows and no real user, tenant, chat, agenda, PDF, billing, or
  tender values were copied.

### Validation results

| Check | Result |
|---|---|
| PostgreSQL extensions | `pgcrypto 1.3`, `vector 0.8.5` |
| Vector dimension | `rag.chunk.embedding` = `vector(1024)` |
| Application-owned objects | `rag` tables restored; `pms_doc`/`pms_vector` views restored |
| Synthetic document count | 1 through `pms_doc.document_record` |
| Synthetic chunk count | 1 through `pms_vector.document_chunk` |
| Synthetic embedding count | 1 through `pms_vector.chunk_embedding` |
| Application startup | Passed against the isolated target |
| `/health` | HTTP 200 |
| `/health/ready` | HTTP 200; expected corpus payload shape returned |
| Safe read queries | Passed against the restored target |
| Operational database | Not restored over or modified by the drill |
| Temporary target cleanup | Confirmed zero `portproject_phase3_restore_*` databases afterward |

## What this proves

The application-owned schema can be recreated from a logical schema backup,
pgvector configuration is compatible with the configured 1024-dimensional
embeddings, the read views can be restored, and the application can initialize
against an isolated empty/source-independent target.

## What this does not prove

This is not a production recovery certificate. It does not prove recovery of:

- PMS `public.*` source rows;
- real portal sessions, chats, agendas, or audit history;
- the indexed PDF corpus and its provenance files;
- billing model/rule artifacts and training inputs;
- tender JSON workflow records; or
- a complete permission/ownership/ACL restoration.

The source PMS database is an external recovery dependency until the system
owner provides an approved sanitized backup or a documented source-system
restore procedure. The application-owned data and tender state also require an
approved data-bearing backup drill before production acceptance.

## RPO, RTO, retention, encryption, and location decisions

No business owner or operations policy was supplied that authorizes numeric
values for these controls. They remain decisions requiring approval:

- **RPO:** choose the maximum acceptable data-loss interval separately for
  source PMS data, `rag` workflow state, and derived vectors.
- **RTO:** choose the maximum time to restore PostgreSQL, private Ollama/model
  dependencies, billing artifacts, corpus files, and the web/API services.
- **Retention:** define daily/weekly/monthly retention and point-in-time
  recovery requirements.
- **Encryption:** require encryption at rest and in transit for approved
  backups; store keys outside the repository and database host.
- **Backup location:** choose an approved private location with access logging,
  regional/legal controls, and a restore account limited to the drill target.
- **Validation cadence:** schedule a recurring isolated restore drill and keep
  its checksum, row/count results, and operator sign-off.

## Required next recovery gate

Before calling disaster recovery proven, obtain:

1. an approved sanitized snapshot or source-system recovery procedure for
   `public.*`;
2. an approved data-bearing backup of `rag.*` and tender workflow state;
3. the corpus, billing artifacts, and model-manifest recovery plan;
4. approved RPO/RTO/retention/encryption/location values; and
5. a second isolated restore drill that validates real row counts, permissions,
   representative read queries, and application behavior without touching
   `portproject`.

Phase 4 and later changes are intentionally not started.
