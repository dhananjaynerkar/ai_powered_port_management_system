# AI-Powered Port Management System

Local-first AI PMS portal with document ingestion, PostgreSQL +
pgvector retrieval, Authority/Tenant authentication, operational land metrics,
tenant mapping records, governed agendas, billing forecasting, and tender
publication workflows. It is a standalone target project; AI PMS is a
reference project only and is not a runtime dependency.

## Implementation status

| Area | Status | Evidence |
| --- | --- | --- |
| PDF/OCR ingestion and page provenance | Implemented with explicit provider-availability and quarantine states | docs/ARCHITECTURE.md, docs/DIAGRAMS.md |
| Lexical + vector retrieval, RRF, and reranking | Implemented | src/portproject_rag/retrieval.py and tests |
| Role/tenant ACL filtering and citation validation | Implemented for documented acceptance paths | docs/SECURITY.md and docs/hardening/RAG_RUNTIME_FINAL_CERTIFICATION.md |
| Local Ollama generation | Implemented as a local dependency | docs/RAG_SYSTEM.md and .env.example |
| Workflow, billing, and tender modules | Implemented with documented acceptance/local-storage limits | docs/WORKFLOW.md, docs/BILLING.md, docs/TENDER.md |
| Production deployment and enterprise scale | Not verified | docs/PRODUCTION_READINESS.md and docs/release/FINAL_RELEASE_GATE.md |
| Agent/MCP/VLM/fine-tuning/true iterative multi-hop retrieval | Not claimed | No public implementation evidence |

## Evaluation snapshot

The reviewed runtime certificate records AnyHit@5 0.89, EvidenceCoverage@5 0.85, 10/10 mapped facts covered, and 9/9 citation-valid generation replays. These are corpus-bound checkpoints, not production-scale or semantic-faithfulness guarantees. See [the evaluation protocol](docs/evaluation_protocol.md) for the measurement boundary and reproduction fields.


## Start here

Read these documents in order:

- [Architecture](docs/ARCHITECTURE.md) — verified components, data flows, and decisions.
- [Diagrams](docs/DIAGRAMS.md) — versioned architecture, RAG, auth, workflow, billing, and tender diagrams.
- [Operations](docs/OPERATIONS.md) — setup, start, readiness, and troubleshooting.
- [API reference](docs/API_REFERENCE.md) — routes, authentication, and contracts.
- [Database](docs/DATABASE.md) — source-system versus application-owned data.
- [RAG system](docs/RAG_SYSTEM.md) — ingestion, retrieval, guardrails, and citations.
- [Final RAG runtime certification](docs/hardening/RAG_RUNTIME_FINAL_CERTIFICATION.md) — frozen quality, runtime measurements, concurrency, and ACL evidence.
- [RAG capacity certification](docs/hardening/RAG_CAPACITY_RESOURCE_CERTIFICATION.md) — bounded local capacity, memory evidence, worker/queue policy, and deployment envelope.
- [Security](docs/SECURITY.md) — deployment modes, sessions, authorization, and data boundaries.
- [Workflow](docs/WORKFLOW.md) — private chat, official agendas, ownership, and transitions.
- [Billing](docs/BILLING.md) — dynamic prefill, forecast artifact, and deterministic formulas.
- [Tender](docs/TENDER.md) — source-backed tender state machine and JSON persistence boundary.
- [Testing and evaluation](docs/TESTING_AND_EVALUATION.md) — regression, RAG, and acceptance evidence.
- [Evaluation protocol](docs/evaluation_protocol.md) — metric definitions, corpus boundaries, and reproducibility fields.
- [Backup and recovery](docs/BACKUP_AND_RECOVERY.md) — state inventory and restore boundary.
- [Project map](docs/PROJECT_MAP.md) — major folders and source-file ownership.
- [Production readiness](docs/PRODUCTION_READINESS.md) — current readiness levels and open promotion gates.
- [Interview defense guide](docs/INTERVIEW_DEFENSE_GUIDE.md) — accurate project explanations and trade-offs.
- [Phase 17 documentation evidence](docs/hardening/PHASE_17_DOCUMENTATION.md) — source reconciliation and documentation verification.
- [Phase 18 final release gate](docs/release/FINAL_RELEASE_GATE.md) — current local-demo, pilot, and production decision with residual blockers.
- [Security gate](docs/hardening/PHASE_02_SECURITY.md) — deployment modes, session transport, and credential-compatibility boundaries.
- [Backup and recovery drill](docs/hardening/PHASE_03_BACKUP_RESTORE.md) — isolated restore evidence and remaining data-recovery decisions.

Phase reports in `docs/hardening/` are evidence records for their named phase.
Older audit/system-verification documents are historical; use the current
documents above as the source of truth.

## Quick start

```powershell
Set-Location <repo-root>
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Set-Location .\web
npm ci
Set-Location ..
Copy-Item .env.example .env
.\start_app.ps1
```

For tests and local verification, replace the placeholder database URL in
`.env` with an operator-approved isolated database (for example, the
acceptance database). Never point a clean install at the operational
`portproject` database, and never copy a developer `.env` into the repository.

Open `http://127.0.0.1:5173` and sign in with an existing Authority or Tenant
database account. The API listens on `127.0.0.1:8001`; PostgreSQL and Ollama
must be available according to `.env`.

Use the project environment for Python commands:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check src tests
Set-Location web; npm run build
```

The complete suite also contains live database and source-backed integration
checks. Run those only with the approved isolated test database and fixture
bundle described in [Phase 01](docs/hardening/PHASE_01_ACCEPTANCE_ENVIRONMENT_IMPLEMENTED.md);
credentials and raw fixture data are intentionally not part of this repository.

The `dev` extra supplies the documented test and lint tools. The optional
`billing-training` extra is only needed for model-training workflows:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[billing-training]"
```

`npm ci` requires the committed `web/package-lock.json` and installs the
frontend dependencies without relying on a developer's existing
`node_modules` directory.

## Local ingestion commands

```powershell
.\.venv\Scripts\ai-pms inspect .. --output .\artifacts\corpus-report
.\.venv\Scripts\ai-pms migrate
.\.venv\Scripts\ai-pms ingest --report .\artifacts\corpus-report\corpus.json --dry-run
.\.venv\Scripts\ai-pms ingest --report .\artifacts\corpus-report\corpus.json
.\.venv\Scripts\ai-pms query "your document question" --limit 8
```

`inspect` is read-only. `migrate` creates only the configured application
schemas and views. `ingest` uses source hashes to avoid exact duplicate work;
low-quality pages are recorded for review rather than silently represented as
reliable native text.

## Security and data boundary

No cloud model fallback is configured. Retrieval uses PostgreSQL full-text and
pgvector cosine search with rank fusion and page-level citations. Portal
sessions are opaque HTTP-only cookies; only token hashes are stored. See
[Security](docs/SECURITY.md), [RAG system](docs/RAG_SYSTEM.md), and
[Production readiness](docs/PRODUCTION_READINESS.md) for current constraints.
