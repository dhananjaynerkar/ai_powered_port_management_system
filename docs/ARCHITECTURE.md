# Architecture

**Status: CURRENT SOURCE OF TRUTH**

## Scope

AI-Powered Port Management System is a local Windows-oriented React + FastAPI application.
It combines existing PMS public tables with application-owned `rag` tables and
a locally indexed PDF corpus. It does **not** require the separate AI PMS
reference checkout at runtime.

## Runtime topology

```text
Browser (React/Vite :5173)
        | opaque HTTP-only session cookie
        v
FastAPI (:8001, loopback only)
        |-- public.*              existing PMS identities, plots, mappings, billing data
        |-- rag.*                 portal sessions, chats, agendas, chunks, audit events
        |-- pms_doc / pms_vector  read views over rag document/chunk data
        v
PostgreSQL + pgvector (:5432)

FastAPI --> Ollama (/api/embed, /api/chat, /api/tags)
FastAPI (one local worker; bounded heavy-RAG gate) --> local CrossEncoder reranker
```

The launcher starts API and UI separately. The API lifespan runs the idempotent
application migration, then marks RAG ready only when the configured Ollama
models and local reranker can initialize.

## Main request flows

### Authentication and authorization

```text
Authority/Tenant login
  -> public identity lookup and password verification
  -> rate-limit record in rag.login_attempt
  -> random session token returned as HTTP-only cookie
  -> SHA-256 token digest stored in rag.user_session
  -> every protected route resolves the current principal and expiry
```

Authority routes require `PortalUser.role == "authority"`. The official agenda
workflow additionally re-reads the active `DO`, `NO`, or `HO` role from
`public.admin_roles`; UI read-only state follows the current agenda owner.

### Document ingestion and retrieval

```text
PDF -> inspect/profile -> strategy choice -> extract or quarantine
    -> page-anchored chunks -> local bge-m3 embeddings
    -> rag.document / document_page / chunk
    -> pms_doc and pms_vector read views

Question -> guardrail validation -> local query embedding
         -> PostgreSQL lexical + pgvector cosine candidates
         -> role ACL filter -> reciprocal-rank fusion -> CrossEncoder rerank
         -> ACL-filtered adjacent/parent context -> local LLM -> citation validation
         -> answer + real page-level source metadata
```

The document-RAG portion of this flow runs behind a process-local capacity gate
on the supported laptop: one active heavy pipeline and one bounded waiter. A
full or expired queue returns a safe HTTP 503 capacity response; it cannot
write a chat or agenda result. The gate is not used by non-RAG routes, and
`/health/ready` remains a dependency-readiness check rather than an activity
lock.

`rag.chunk.acl_roles` is applied in the lexical and dense candidate queries:
an empty array is public to portal roles; a populated array requires the
current role. This is before RRF and reranking. Adjacent-page promotion and
parent/context expansion join `chunk_acl` and repeat the same predicate before
context assembly. Phase 08 verifies this with an acceptance-only mixed-ACL
document: a tenant query retains the public anchor but excludes restricted
neighbours. The assistant does not intentionally generate an answer when
there is no retrieved evidence.

### Chat and official agendas

Private conversations are scoped to `principal_id`. A private conversation may
be deleted only when it is not linked to a workflow draft or agenda. An agenda
can be created only by a `DO` after the conversation contains an assistant
message with citations.

```text
Private cited chat
  -> DO creates agenda draft and v1
  -> DO submits to NO
  -> NO returns to DO or submits to HO
  -> HO approves or rejects
```

Each handoff creates an immutable agenda message and a compact
`context_capsule`. Evidence shown for a capsule is derived from the cited AI
messages that existed at the time of that snapshot; citations are not copied
into a second source of truth.

### Operational dashboard and tenant table

The Authority dashboard uses live `public.plot`, `public.m_property_status`,
`public.applicant_property_mapping`, and `public.applicant_registration`
queries. It keeps plot status, vacancy, occupancy, tenancy lifecycle, lease
type, tenant structure, billing periodicity, and allotment separate.

The tenant table is a server-paginated view of applicant-property mappings,
not a canonical unique-tenant master. Its filters, sort allowlist, paging, and
historical-date display are API-owned.

### Billing and tender workflows

Billing uses a PostgreSQL-backed prefill plus copied runtime model/rule
artifacts. It reads source data and retains calculation context in memory for
the current API process; it does not alter billing source tables.

Tender publication loads only eligible vacant-plot exports and checklist
evidence. It persists workflow records in the target project’s
`tender_workflow/data/tender_workflows.json` and produces draft PDFs. It does
not infer missing commercial approvals.

For rendered diagrams, see [DIAGRAMS.md](DIAGRAMS.md). Detailed ownership,
security, workflow, billing, tender, and recovery contracts are maintained in
[DATABASE.md](DATABASE.md), [SECURITY.md](SECURITY.md), [WORKFLOW.md](WORKFLOW.md),
[BILLING.md](BILLING.md), [TENDER.md](TENDER.md), and
[BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md). The measured local capacity
envelope is maintained in
[RAG_CAPACITY_RESOURCE_CERTIFICATION.md](hardening/RAG_CAPACITY_RESOURCE_CERTIFICATION.md).

## Database ownership

| Schema / data | Owner and use |
| --- | --- |
| `public.*` | Existing PMS source system. Used read-only by portal features except the project does not create or alter these source tables. |
| `rag.*` | Application-owned portal/RAG data: documents, chunks, sessions, chats, audit events, and agendas. |
| `pms_doc.*` | Read views that expose document records. |
| `pms_vector.*` | Read views that expose chunks, embeddings, and ACLs. |
| tender JSON data | Application-local workflow state; it is not a PostgreSQL transaction store. |

## Security and permission boundary

- Parameterized SQL is used for values; schema identifiers are constrained in
  `Settings` and composed as SQL identifiers during migration.
- Browser sessions are opaque, HTTP-only, `SameSite=Lax` cookies; only a token
  digest is persisted.
- Login failures are rate-limited by a hashed username/IP key.
- Query text is size-limited and rejects selected prompt-injection, secret
  exfiltration, and destructive database patterns.
- Generated citations are checked against the retrieval result; factual
  paragraphs without matching citations are rejected/retried by generation.
- API is loopback-bound by the provided server launcher. Cross-origin access is
  limited to the two local Vite origins.

## Deliberate decisions

1. **Do not merge source database and RAG terminology.** Mapping records,
   applicant IDs, and tenancy identifiers are separately exposed because the
   public source does not provide a canonical active-tenancy master field.
2. **Do not use graph retrieval without evidence.** Current strategy code
   selects graph traversal only when the graph-state evidence supports it.
3. **Do not silently fill unverified OCR/table values.** Low-quality extraction
   is retained as an observable review state.
4. **Do not perform a broad frontend rewrite during a live integration.** The
   large React entry file is a maintenance risk, but a gradual component
   extraction with build and interaction checks is safer than a bulk move.
