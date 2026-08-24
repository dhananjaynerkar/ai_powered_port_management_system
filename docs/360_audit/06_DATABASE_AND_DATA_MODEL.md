# Database and data-model audit

## Persistence zones

### public schema

Existing PMS source tables are read by authentication, dashboard, tenant,
workflow officer lookup, billing, and tender source services. Important tables
observed in SQL include public.admin_users, public.admin_roles,
public.applicant_registration, public.applicant_property_mapping, public.plot,
public.m_property_status, and billing-related public customer/rate/history
tables. The portal does not migrate or rewrite these source tables.

### rag schema

database.py creates application-owned document, document_page, chunk, app_user,
user_session, chat_session, workflow_draft, chat_message, audit_event,
login_attempt, agenda, agenda_version, agenda_message, and context_capsule
tables. Foreign keys and indexes are declared by migration_statements.

### pms_doc and pms_vector

database.migrate creates read views: pms_doc.document_record,
pms_vector.document_chunk, pms_vector.chunk_embedding, and
pms_vector.chunk_acl. These views keep retrieval-facing names separate from
the canonical rag storage tables.

### Tender JSON

tender_workflow/data/tender_workflows.json stores local tender workflow records.
The service uses a process lock and atomic file replacement behavior as
implemented, but this is not equivalent to multi-process database transaction
isolation.

## Key table semantics

| Concept | Actual meaning |
| --- | --- |
| Applicant | public.applicant_registration profile identified by applicant_id. |
| Applicant ID in mapping | applicant_property_mapping.tenant_id key; it is not automatically a unique tenant master record. |
| Mapping record | One row in public.applicant_property_mapping. |
| Tenancy identifier | Distinct non-empty mapping.tenancy_id value. |
| Plot/property | public.plot record and its property/area/status values. |
| Portal user | rag session principal resolved from source account. |
| Agenda | rag.agenda official workflow record with an owner/state. |
| Evidence chunk | rag.chunk page-anchored text and optional ACL/embedding. |

## Vector data

rag.chunk.embedding is vector(embedding_dimensions), default 1024, with an HNSW
cosine index. pms_vector views expose the embedding and ACL fields to retrieval.

## Security implications

Source schema is trusted PMS data but includes legacy identity/password fields
read by authentication. Application tables contain session digests, chat
content, workflow evidence, and audit metadata. Least-privilege roles,
encryption/backup, and source password remediation are production decisions.

## Retention

The source code does not define a general retention/deletion policy. Private
chat deletion is blocked when linked to workflow records. Agenda versions and
messages remain part of the official record. A formal retention policy is NOT
VERIFIED.

