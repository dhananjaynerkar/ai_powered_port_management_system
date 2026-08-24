# Operations guide

## Supported local environment

- Windows PowerShell
- Python 3.12 or newer through the project `.venv`
- Node.js/npm for the React UI
- PostgreSQL with pgvector and pgcrypto extensions available to the configured
  database role
- Local Ollama endpoint with the configured embedding and completion models

The provided server binds API traffic to `127.0.0.1:8001`; Vite serves the UI
at `127.0.0.1:5173`.

## First setup

```powershell
Set-Location <repo-root>
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
Set-Location web
npm ci
Set-Location ..
Copy-Item .env.example .env
```

For the documented test and lint commands, install the development extra:

```powershell
Set-Location <repo-root>
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

The optional billing-training dependencies are not required for the portal or
RAG runtime. Install them only for the training workflow:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[billing-training]"
```

Set `PORTPROJECT_RAG_DATABASE_URL` only in `.env`. Do not place the database
password in source, screenshots, support tickets, or generated documentation.

## Start and stop

Run `Start_App.cmd` or:

```powershell
.\start_app.ps1
```

The launcher checks the ports before starting child processes, writes logs to
`artifacts/runtime-logs`, waits for the two HTTP services, and opens the UI.
If a port is occupied but its expected health endpoint fails, it stops instead
of attaching to an unknown process.

## Health checks

```powershell
Invoke-WebRequest http://127.0.0.1:8001/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8001/health/ready -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:5173/ -UseBasicParsing
```

- `/health` means the API initialized its settings.
- `/health/ready` additionally reports corpus counts and returns success only
  when configured Ollama models and the reranker are usable.
- The Vite response only confirms the UI server is reachable; authenticated
  workflows still require a valid database account.

## Test and build

Always use the project virtual environment for Python checks:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check src tests
Set-Location web
npm run build
```

`pyproject.toml` also declares `src` as a pytest import path, but this does not
replace installing the project dependencies in the supported `.venv`.

The complete test suite includes source-backed integration checks. Those checks
require an approved test database URL and the non-secret billing and tender
fixture bundle described in [Phase 01](hardening/PHASE_01_TEST_FIXTURE.md).
Those inputs are intentionally not committed to Git and are not created by the
base install. Without that approved fixture, the package, unit tests, and lint
checks can still be verified, but live database, billing-artifact, and tender
source tests are expected to remain unavailable rather than silently using
developer-machine data.

## Configuration inventory

All settings use the `PORTPROJECT_RAG_` prefix. Major groups are:

| Group | Examples | Purpose |
| --- | --- | --- |
| Database/schema | `DATABASE_URL`, `SCHEMA_NAME`, `DOCUMENT_SCHEMA_NAME`, `VECTOR_SCHEMA_NAME` | PostgreSQL connection and application-owned schema names. |
| Local AI | `EMBEDDING_ENDPOINT`, `EMBEDDING_MODEL`, `GENERATION_ENDPOINT`, `LLM_PRIMARY_MODEL` | Ollama endpoints and models. |
| Retrieval | `RETRIEVAL_LIMIT`, `RRF_K`, `RERANKER_*`, `CONTEXT_TOKEN_BUDGET` | Candidate/reranking/context bounds. |
| Ingestion | `CHUNK_*`, `BATCH_SIZE`, `TABLE_MAX_PAGES`, `EMBEDDING_*` | Extraction and embedding throughput bounds. |
| Session/security | `LOGIN_*`, `SESSION_*`, `COOKIE_SECURE`, `QUERY_MAX_CHARACTERS` | Login throttling, session lifespan, transport setting, and query size. |

The full safe template is `.env.example`; it intentionally contains no real
credentials.

## Deployment gate

Before exposing this beyond local development, require: HTTPS, `COOKIE_SECURE`
enabled, least-privilege database credentials, a remediation decision for any
legacy plaintext source-password fields, network restrictions for PostgreSQL
and Ollama, backups for `rag.*` and tender JSON state, and authenticated
acceptance testing for authority/tenant/DO/NO/HO roles.
