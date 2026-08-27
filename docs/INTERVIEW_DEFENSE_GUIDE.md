# Interview defense guide

**Status: CURRENT SOURCE OF TRUTH**

This guide explains what is verified in the repository and where the honest
limits are. It is not a substitute for the source code or acceptance evidence.

## 30-second explanation

AI-Powered Port Management System is a local-first React/FastAPI application for a port
authority. It reads existing PMS identities, land/tenant mappings, and billing
references from PostgreSQL, indexes PDF pages into a `rag` schema with 1,024-
dimension pgvector embeddings, and answers role-filtered questions with page
citations from local models. A cited private answer can become a governed DO → NO
→ HO agenda. Authority users also have source-backed billing and tender workflows.

## 2-minute explanation

The browser is a Vite-built React shell and the API is FastAPI on loopback. The
database boundary is deliberate: `public.*` is PMS-owned source data, while
`rag.*` owns sessions, chats, documents, chunks, embeddings, agendas, and audit
events. Ingestion profiles PDFs, chooses native/OCR/alternative extraction,
stores page provenance, chunks text, and embeds with local `bge-m3`.

For a question, guardrails validate input, PostgreSQL combines lexical and
vector candidates, ACLs are applied before context assembly, RRF and a local
CrossEncoder rerank results, and a local Qwen model produces an answer. Citation
metadata is returned and persisted with the chat. Official agenda queries are
owner-checked before they can write to the thread.

The dashboard and tenant table are source-backed. Billing separates ML
forecasting from deterministic tax formulas. Tender publication is a
configuration-driven JSON workflow with explicit approvals and generated draft
PDFs.

## 5-minute explanation

1. **Why local-first:** tenant/policy data and model calls remain inside the
   approved local/internal environment; there is no cloud fallback configured.
2. **Why PostgreSQL + pgvector:** the portal already depends on PostgreSQL source
   relations, so application state, full-text search, vectors, ACLs, and joins
   can be governed in one database boundary.
3. **Why page provenance:** every page/chunk keeps document/page identity so an
   answer can show the evidence rather than only a generated paragraph.
4. **Why a workflow boundary:** private exploration must not silently mutate an
   official agenda. Ownership/state checks are enforced in the API and database
   records retain versions/messages/context snapshots.
5. **Why explicit source warnings:** billing/tender inputs are not inferred when
   an approved value is absent; the UI surfaces missing evidence for review.
6. **How it is validated:** the latest local checkpoint is recorded in
   `docs/hardening/RAG_CAPACITY_RESOURCE_CERTIFICATION.md`; the final run has
   **102 passed and 28 skipped** in the non-acceptance Python suite, with Ruff,
   the Vite production build, and guarded Phase 08/09 acceptance passing. Full
   production readiness remains a separate deployment-owner gate. The local
   capacity envelope is one active heavy RAG pipeline, one bounded waiter, and
   one FastAPI worker; the capacity certificate records the measured limits.

## Technology answers

| Technology | What | Why here | Where | Why not a more complex alternative |
| --- | --- | --- | --- | --- |
| React + Vite | Browser UI and build tool | Fast local development and a single deployable bundle | `web/src` | A larger framework would add routing/server complexity not required by the current shell. |
| FastAPI | Typed HTTP/API boundary | Fits Python RAG, database, and local-model adapters | `src/portproject_rag/api.py` | A separate service mesh would increase deployment surface without a measured need. |
| PostgreSQL | Source integration and application persistence | Existing PMS data, transactions, full-text, and workflow state already belong here | `database.py`, `api.py` | A second operational database would duplicate identity/source joins. |
| pgvector | Vector similarity in PostgreSQL | Keeps embeddings beside page/chunk provenance and ACL metadata | `rag.chunk.embedding` | An external vector service would add data egress and another consistency boundary. |
| Ollama | Local embedding/completion HTTP service | Keeps model execution local and model selection explicit | `settings.py`, `generation.py` | Cloud inference is not approved for this local data boundary. |
| CrossEncoder | Local reranking | Improves ordering after broad lexical/vector retrieval | `retrieval.py` | A more elaborate retrieval platform is not justified before measured error analysis. |
| JSON tender store | Local tender workflow persistence | Matches the current approved single-process/local scope | `tender_workflow_service.py` | PostgreSQL migration is reserved for an approved multi-user deployment decision. |
| XGBoost artifact | Billing-base forecast | Existing training/runtime contract and exported model manifest | `billing/` | Replacing the model without holdout evidence would be guesswork. |

## Deep technical questions

### How is access control applied to RAG?

The current principal is resolved from the session, and lexical/dense retrieval
filters candidates by `acl_roles` before RRF and CrossEncoder reranking.
Adjacent-page promotion and parent/context expansion join `chunk_acl` and
repeat the public-or-current-role predicate before text is assembled for the
model. The acceptance suite proves this with a mixed-ACL document: a tenant
retains a public anchor while restricted neighbouring pages are excluded.
Authorization is not delegated to the model, and the answer payload exposes
only validated source metadata from the selected result set.

### What happens when RAG is unavailable?

The API remains health-checkable, readiness reports the dependency failure, and
query routes return a controlled 503/error rather than a fabricated answer.
The exact dependency and timing fields are recorded in safe logs.

### What is not solved yet?

Production deployment still needs an approved external credential strategy,
HTTPS/secure-cookie deployment, least-privilege database role, approved backup
RPO/RTO, authenticated browser/accessibility evidence, and hardware-backed
capacity for the CPU-bound local model stack. The tender store is not a multi-process
production database, and human semantic review remains required for broader
RAG claims. These are explicit limitations, not hidden assumptions.
