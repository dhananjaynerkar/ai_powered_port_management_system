# Project map

**Status: CURRENT SOURCE OF TRUTH**

This map covers maintained source, configuration, runtime scripts, tests, and
generated-output boundaries. It intentionally does not describe every copied
PDF, CSV, or compiled asset as application source code.

## Root

| Path | Responsibility | Change guidance |
| --- | --- | --- |
| `README.md` | Entry point and supported local commands. | Keep links current when public contracts change. |
| `pyproject.toml` | Python package metadata, dependencies, tools, and `src` package discovery. | Add runtime dependencies here; keep training-only packages optional. |
| `.env` | Local runtime settings and database URL. | Never commit or copy to documentation. |
| `.env.example` | Safe configuration template. | Add new `Settings` keys here without real values. |
| `start_app.ps1`, `Start_App.cmd` | Windows launcher for API and Vite UI. | Keep ports and health paths synchronized with the runtime. |
| `artifacts/` | Generated reports, models, logs, and copied billing runtime artifacts. | Treat as runtime/build output, not Python source. |

## Python package

| Path | Responsibility |
| --- | --- |
| `src/pms_api/app.py` | Uvicorn application factory. This compatibility wrapper is retained because the server command targets it. |
| `src/portproject_rag/server.py` | Binds the local FastAPI server to `127.0.0.1:8001`. |
| `src/portproject_rag/settings.py` | Typed `PORTPROJECT_RAG_*` settings and safe bounds. |
| `src/portproject_rag/api.py` | HTTP boundary: request validation, authorization, dashboard/tenant queries, RAG answer routes, and feature adapters. |
| `src/portproject_rag/auth.py` | Existing Authority/Tenant identity verification, opaque session lifecycle, and login-attempt rate limiting. |
| `src/portproject_rag/database.py` | Idempotent `rag` schema migration and read views in `pms_doc`/`pms_vector`. |
| `src/portproject_rag/inspection.py` | PDF discovery and page-profile inspection. |
| `src/portproject_rag/capabilities.py`, `strategy.py`, `quality.py` | Capability detection, adaptive extraction decisions, and quality policy. |
| `src/portproject_rag/ocr.py`, `table_processing.py` | Optional OCR and bounded table extraction adapters. |
| `src/portproject_rag/ingestion.py` | Source hashing, extraction/chunking, local embedding calls, and persistence. |
| `src/portproject_rag/retrieval.py` | Role-filtered lexical+dense retrieval, reciprocal-rank fusion, reranking, and context assembly. |
| `src/portproject_rag/generation.py`, `guardrails.py` | Local generation prompt/response handling and input/citation controls. |
| `src/portproject_rag/workflow.py` | Official agenda ownership, versioning, handoffs, evidence snapshots, and role transitions. |
| `src/portproject_rag/billing/` | Source-backed billing prefill and prediction using runtime artifacts; it does not write billing source data. |
| `src/portproject_rag/tender_workflow/` | Source-backed tender publication workflow, LAC checklist, calculations, JSON workflow store, and PDF drafts. |
| `src/portproject_rag/cli.py` | Operator commands for inspection, migration, ingestion, and retrieval. |
| `src/portproject_rag/experiments.py`, `reporting.py` | Evaluation and report-generation support. |

## Frontend

| Path | Responsibility | Current maintenance boundary |
| --- | --- | --- |
| `web/src/main.tsx` | React application shell, authentication screens, dashboard, tenant table, chat, agenda workflow, and feature modals. | This is the largest maintained source file. Do not split it opportunistically; extract a tested component only with a defined feature boundary. |
| `web/src/shared/utils.ts` | Pure shared formatting, status, width, tenant, conversation, and pagination helpers extracted in Phase 16. | Keep browser-independent helpers here; do not move stateful components into this module. |
| `web/src/styles.css` | Design tokens, responsive layout, component styles, states, splitters, and feature-modal styles. | Keep shared tokens near the top; avoid page-specific overrides that change unrelated layouts. |
| `web/vite.config.ts` | Vite development/build configuration. |
| `web/package.json` | React/Vite/TypeScript dependencies and build scripts. |
| `web/dist/` | Generated production build. Ignored going forward; rebuild with `npm run build`. |

## Tests and documentation

| Path | Responsibility |
| --- | --- |
| `tests/test_authority_metrics.py` | Live dashboard aggregation, terminology, and date-quality contract. |
| `tests/test_tenant_pagination.py` | Server-side filtering, sorting, page-size bounds, and invalid-date handling. |
| `tests/test_chat_payload.py`, `test_guardrails.py` | Shared evidence payload and RAG guardrail/citation behavior. |
| `tests/test_database_migration.py` | Schema identifier/dimension separation and workflow migration contract. |
| `tests/test_inspection.py`, `test_strategy.py`, `test_live_corpus_evaluation.py` | Extraction quality and adaptive retrieval behavior. |
| `tests/test_billing_service.py`, `test_tender_workflow.py` | Source-backed billing and tender workflow behavior. |
| `docs/` | Architecture, operations, API contract, integration notes, evaluations, and audit records. |

## Current documentation hierarchy

| Document | Source-of-truth responsibility |
| --- | --- |
| `ARCHITECTURE.md`, `DIAGRAMS.md` | Runtime topology and data flows |
| `DATABASE.md`, `SECURITY.md` | Ownership, session, authorization, and deployment boundaries |
| `RAG_SYSTEM.md`, `WORKFLOW.md` | Evidence pipeline and official agenda semantics |
| `BILLING.md`, `TENDER.md` | Feature-specific source and persistence contracts |
| `OPERATIONS.md`, `BACKUP_AND_RECOVERY.md` | Local operation and recovery boundaries |
| `API_REFERENCE.md`, `TESTING_AND_EVALUATION.md` | API and verification contracts |
| `PRODUCTION_READINESS.md` | Current promotion status and residual gates |
| `INTERVIEW_DEFENSE_GUIDE.md` | Accurate technical explanations and limitations |

Files under `docs/hardening/` are phase evidence reports. Files under
`docs/360_audit/` and `docs/system_verification/` are historical audit material
and are not current source of truth unless a current document explicitly links
to a verified claim.
