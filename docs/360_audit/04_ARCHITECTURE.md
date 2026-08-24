# Architecture audit

## Actual topology

Browser -> React/Vite on 127.0.0.1:5173 -> FastAPI on 127.0.0.1:8001 ->
PostgreSQL on configured database/port -> public PMS tables and rag-owned
tables/views.

FastAPI also calls local Ollama /api/embed, /api/chat, and /api/tags endpoints,
loads the configured CrossEncoder reranker, reads billing artifacts, and reads
tender source files/local workflow JSON.

## Layer responsibilities

1. Browser layer: role-aware rendering, forms, splitters, chat state, status
   states, and feature modals in web/src/main.tsx.
2. HTTP layer: Pydantic validation, cookies, route authorization, response
   shaping, and error mapping in api.py.
3. Domain services: auth.py, workflow.py, billing/prediction_service.py, and
   tender_workflow/tender_workflow_service.py.
4. Data processing: inspection, strategy, extraction, OCR, table, ingestion,
   retrieval, generation, and guardrails modules.
5. Persistence: PostgreSQL/pgvector migrations and views, public PMS reads,
   billing artifacts, and tender JSON state.

## Architectural style

The project is a modular monolith with a single FastAPI process and a single
React application. That is appropriate for a local operational portal because
authentication, RAG ACL decisions, database queries, and workflow transitions
share one trusted boundary.

## Evidence and limitations

The complete current data-flow diagram is in docs/ARCHITECTURE.md. This report
does not infer a microservice boundary, graph RAG, or cloud service because the
code does not require them. UI-authenticated end-to-end behavior is NOT VERIFIED
without a real account.

## Architecture decisions

- Keep the reference checkout separate.
- Keep source PMS data read-only from this portal.
- Keep RAG evidence in PostgreSQL/pgvector with page lineage.
- Keep official agenda state transitions in transactional PostgreSQL tables.
- Keep tender JSON as a known current limitation rather than silently calling it
  a database workflow.

