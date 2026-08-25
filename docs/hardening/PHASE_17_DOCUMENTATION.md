# Phase 17 — Documentation and Interview-Defense Package

**Status: PASS**

This phase reconciles the maintained documentation with the current source,
configuration, and Phase 15/16 verification evidence. It does not change
application code, routes, schemas, model settings, or runtime behavior.

## Documentation hierarchy completed

The following current source-of-truth documents now exist or were refreshed:

| Document | Result |
| --- | --- |
| `README.md` | Refreshed entry point and documentation index. |
| `docs/ARCHITECTURE.md` | Marked current, corrected PostgreSQL port, and linked feature contracts. |
| `docs/PROJECT_MAP.md` | Added Phase 16 shared utility boundary and documentation ownership map. |
| `docs/OPERATIONS.md` | Aligned clean setup with the `.[dev]` extra and linked security/recovery docs. |
| `docs/API_REFERENCE.md` | Marked current and aligned parameter names/aliases with `api.py`. |
| `docs/DATABASE.md` | Added source/application ownership, tables, views, migration, and integrity boundaries. |
| `docs/RAG_SYSTEM.md` | Added ingestion, retrieval, guardrail, citation, readiness, and limitation contract. |
| `docs/SECURITY.md` | Added auth/session/ACL/deployment-mode and credential-compatibility contract. |
| `docs/WORKFLOW.md` | Added private-chat versus official-agenda lifecycle and permission model. |
| `docs/BILLING.md` | Added dynamic prefill, ML/formula separation, artifacts, and limitations. |
| `docs/TENDER.md` | Added source-backed state machine, JSON persistence boundary, and API behavior. |
| `docs/TESTING_AND_EVALUATION.md` | Added test layers, RAG evaluation rules, and evidence interpretation. |
| `docs/BACKUP_AND_RECOVERY.md` | Added ownership inventory and isolated recovery requirements. |
| `docs/PRODUCTION_READINESS.md` | Replaced the legacy note with current local/internal/production status. |
| `docs/INTERVIEW_DEFENSE_GUIDE.md` | Added 30-second, 2-minute, 5-minute, deep technical, and trade-off answers. |
| `docs/DIAGRAMS.md` | Added seven Mermaid diagrams: topology, RAG, auth, chat/agenda, billing, tender, and database ownership. |
| `docs/HISTORICAL_REPORTS.md` | Added historical-report index and current-source-of-truth rule. |

## Historical material handling

`docs/360_audit/README.md` and `docs/system_verification/README.md` now carry an
explicit **HISTORICAL — NOT CURRENT SOURCE OF TRUTH** banner. Phase reports stay
as evidence records; the new top-level feature documents are the current
operational contracts. No historical report was deleted or silently rewritten.

## Source verification used

The documentation was checked against:

- `src/portproject_rag/api.py` route decorators and access dependencies;
- `src/portproject_rag/settings.py` deployment/security validators;
- `src/portproject_rag/database.py` schemas, constraints, views, and indexes;
- `src/portproject_rag/retrieval.py`, `generation.py`, `guardrails.py`, and
  `ingestion.py` RAG boundaries;
- `src/portproject_rag/billing/` and its runtime rules/model manifest;
- `src/portproject_rag/tender_workflow/` and `config/tender_workflow.json`;
- Phase 15 clean-install and Phase 16 maintainability reports.

No unverified production metric, model-accuracy percentage, RPO/RTO, or business
approval was added. Where deployment-owner evidence is still required, the docs
label it as conditional, not as a completed fact.

## Verification evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Python regression suite | **PASS** | `python -m pytest -q --tb=no`: **48 passed**. |
| Ruff | **PASS** | `.venv\\Scripts\\ruff.exe check src tests`: all checks passed. |
| Frontend production build | **PASS** | `web/npm run build`: TypeScript/Vite build completed; 1,671 modules transformed. |
| Relative Markdown links | **PASS** | Repository-wide relative-link scan found no missing targets. |
| Diagram inventory | **PASS** | `docs/DIAGRAMS.md` contains 7 Mermaid blocks. |
| Diff hygiene | **PASS** | `git diff --check` found no whitespace errors. |

## Phase boundary

This phase is documentation-only and stops here. No Phase 18 release gate or
automatic production decision was started.
