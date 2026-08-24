# PortProject RAG — 360-degree master audit

## 1. What is this project?

It is a local-first Port Management System portal combining a React/Vite
frontend, FastAPI backend, PostgreSQL/pgvector document RAG, existing PMS data,
official agenda workflow, billing forecast, and tender publication preparation.

## 2. What problem does it solve?

It gives Authority and Tenant users one controlled interface for port land
operations, mapping records, trusted-document questions, formal handoffs, and
source-backed calculations.

## 3. Who uses it?

Authority users include Data Entry Operators, Nodal Officers, and Heads of
Department. Tenant users have a separate login surface. Developer/operator
roles run the local launcher, ingestion CLI, checks, and maintenance.

## 4. Technologies and why

React/Vite/TypeScript provide the UI; Python/FastAPI provide typed routes and
authorization; PostgreSQL stores source/application state; pgvector stores
embeddings beside lexical search; Ollama supplies local embeddings/completion;
CrossEncoder reranks; PDF/OCR libraries support adaptive ingestion; XGBoost
JSON and deterministic formulas support billing; ReportLab produces tender
drafts. See 03_TECH_STACK_AND_WHY.

## 5. Architecture

Browser -> React/Vite -> FastAPI -> PostgreSQL/pgvector, local Ollama,
CrossEncoder, billing artifacts, and tender source/JSON files. It is a modular
monolith, not a collection of microservices. See 04_ARCHITECTURE.

## 6. Data used

The application reads public PMS identity, plot, status, applicant, mapping,
customer, history, rate, and source-export data. It writes application-owned
rag tables, audit/workflow data, and local tender JSON; source public tables are
not migrated by this project. See 06_DATABASE_AND_DATA_MODEL.

## 7. Data flow

Login, dashboard, tenant, chat/RAG, agenda, billing, tender, and logout flows
are traced in 05_END_TO_END_DATA_FLOWS.

## 8. RAG

PDF inspection -> adaptive extraction/OCR/table decision -> page chunks ->
bge-m3 embeddings -> PostgreSQL lexical/vector retrieval -> ACL -> RRF ->
rerank -> context -> Ollama generation -> citation validation -> answer. See
08_RAG_PIPELINE_DEEP_DIVE and 09_CHUNKING_EMBEDDING_RETRIEVAL.

## 9. Security/isolation

Opaque HTTP-only sessions, login throttling, backend role/owner checks, ACL
retrieval filtering, query guardrails, citation validation, and protected
workflow transitions are implemented. HTTPS secure cookies, legacy source
password remediation, CSRF assurance, and adversarial role tests remain
deployment work. See 11_AUTH_SECURITY_PERMISSIONS.

## 10. Workflow

Private cited chat -> DO draft -> NO review -> HO decision with versions,
messages, handoffs, evidence snapshots, and provenance-protected chats. See
14_WORKFLOW_AGENDA.

## 11. Billing

Selected-tenancy source prefill, local exported XGBoost evaluation, and
deterministic formula/tax calculations produce a forecast. See
15_BILLING_FORECAST.

## 12. Tender

Eligible vacant plot, checklist, approved/manual inputs, deterministic
calculation, local workflow state, and draft PDF generation are integrated. See
16_TENDER_PUBLICATION.

## 13. What is strong?

Real readiness contract, hybrid retrieval, page citations, ACL path, live
terminology contract, server-side tenant controls, governed agenda state,
source-backed billing/tender, and passing focused/full tests.

## 14. What is incomplete or risky?

Reviewed RAG quality metrics, full protected UI acceptance, security hardening,
source password migration, tender multi-process persistence, operational
monitoring, accessibility matrix, performance baselines, and backup/restore are
not fully proven.

## 15. What is technically weak?

Feature concentration in main.tsx/styles.css/api.py, no complete telemetry
system, and mixed current/historical reports before this audit.

## 16. What is unnecessarily complex?

No evidence justifies microservices, Kubernetes, Kafka, Redis, graph RAG, agent
framework migration, cloud vector storage, or a new state-management stack.

## 17. What is missing?

Reviewed evaluation set, adversarial ACL/E2E tests, accessibility/performance
baselines, secure deployment/backup runbooks, and source credential remediation.

## 18. What should improve?

Follow 26_RECOMMENDED_ROADMAP in phases, starting with correctness and security,
then evaluation, maintainability, UX, and production hardening.

## 19. What should not change?

Do not rewrite the UI/backend wholesale, replace PostgreSQL/pgvector/Ollama,
delete compatibility routes, alter source data, or add graph/microservice
complexity without evidence.

## 20. What should happen first?

Confirm business terminology and source-password policy, then establish secure
deployment and backup gates, then build reviewed RAG evaluation and role/E2E
coverage.

## 21. What proves each claim?

See 28_EVIDENCE_INDEX.md. Each major conclusion names an actual file,
function/route/table, reasoning, and confidence.

## Audit-only stop condition

This master report does not authorize implementation of its recommendations.
The project source, APIs, SQL, database, models, workflows, and UI behavior
were not refactored in this audit folder.
