# Interview defense guide

## 30-second explanation

I built a local-first AI PMS portal with React and FastAPI. It
uses PostgreSQL and pgvector for hybrid document retrieval, local Ollama models
for embeddings and answers, page citations and guardrails for grounded output,
and a role-governed agenda workflow. It also integrates live land/tenant
mapping data, billing forecasting, and tender preparation.

## Two-minute explanation

The browser is a React/Vite shell calling a FastAPI modular monolith. Existing
PMS public tables provide identities, plots, mappings, and billing sources.
Application-owned PostgreSQL tables store document pages/chunks, embeddings,
sessions, conversations, agendas, versions, evidence snapshots, and audit
events. A PDF moves through inspection, adaptive extraction, page-anchored
chunking, local bge-m3 embeddings, lexical plus pgvector retrieval, ACL
filtering, rank fusion, reranking, bounded context, local generation, and
citation validation. A cited private chat can be promoted by a Data Entry
Operator into an official DO -> NO -> HO workflow.

## Five-minute technical explanation

Explain the actual modules and route groups using docs/ARCHITECTURE.md,
docs/API_REFERENCE.md, and this audit folder. Emphasize that billing combines
an exported XGBoost evaluator with deterministic tax/formula logic, while
tender uses source-backed vacant plots/checklists and local JSON workflow
records. Explain readiness separately from /health and name the current
limitations: RAG quality metrics, source password legacy risk, secure deployment,
JSON concurrency, and UI/E2E coverage.

## “Why” answers

- FastAPI: typed validation, dependency auth, and OpenAPI in one boundary.
- React/Vite/TypeScript: responsive stateful portal and fast local builds.
- PostgreSQL: existing source system plus transactional application state.
- pgvector: vector search beside lexical search and ACL metadata.
- Ollama: local model control and no cloud fallback.
- Hybrid retrieval: lexical exactness plus semantic similarity.
- Reranking: improve ordering of fused candidates.
- Guardrails/citations: reduce unsupported output; not a proof of faithfulness.
- Agenda workflow: preserve ownership, approvals, versions, and evidence.

## Honest limitations

Do not claim a measured RAG accuracy score, complete multilingual OCR, external
production hardening, or fully verified role-based browser acceptance until the
roadmap closes those gaps.
