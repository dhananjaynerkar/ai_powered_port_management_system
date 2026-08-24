# PortProject RAG Portal

Local-first Port Management System portal with document ingestion, PostgreSQL +
pgvector retrieval, Authority/Tenant authentication, operational land metrics,
tenant mapping records, governed agendas, billing forecasting, and tender
publication workflows. It is a standalone target project; `AI_PMS` is a
reference project only and is not a runtime dependency.

## Start here

Read these documents in order:

- [Architecture](docs/ARCHITECTURE.md) — verified components, data flows, and decisions.
- [Operations](docs/OPERATIONS.md) — setup, start, readiness, and troubleshooting.
- [API reference](docs/API_REFERENCE.md) — routes, authentication, and contracts.
- [Project map](docs/PROJECT_MAP.md) — major folders and source-file ownership.
- [Audit](docs/AUDIT_2026-08-24.md) — verified strengths, risks, and deliberately deferred work.
- [Security gate](docs/hardening/PHASE_02_SECURITY.md) — deployment modes, session transport, and credential-compatibility boundaries.
- [Backup and recovery drill](docs/hardening/PHASE_03_BACKUP_RESTORE.md) — isolated restore evidence and remaining data-recovery decisions.

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
bundle described in [Phase 01](docs/hardening/PHASE_01_TEST_FIXTURE.md);
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
.\.venv\Scripts\portproject-rag inspect .. --output .\artifacts\corpus-report
.\.venv\Scripts\portproject-rag migrate
.\.venv\Scripts\portproject-rag ingest --report .\artifacts\corpus-report\corpus.json --dry-run
.\.venv\Scripts\portproject-rag ingest --report .\artifacts\corpus-report\corpus.json
.\.venv\Scripts\portproject-rag query "your document question" --limit 8
```

`inspect` is read-only. `migrate` creates only the configured application
schemas and views. `ingest` uses source hashes to avoid exact duplicate work;
low-quality pages are recorded for review rather than silently represented as
reliable native text.

## Security and data boundary

No cloud model fallback is configured. Retrieval uses PostgreSQL full-text and
pgvector cosine search with rank fusion and page-level citations. Portal
sessions are opaque HTTP-only cookies; only token hashes are stored. See
[Architecture](docs/ARCHITECTURE.md#security-and-permission-boundary) and
[Audit](docs/AUDIT_2026-08-24.md) for the verified local-development and
production deployment constraints.
