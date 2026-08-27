# Operations guide

**Status: CURRENT SOURCE OF TRUTH**

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
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Set-Location web
npm ci
Set-Location ..
Copy-Item .env.example .env
```

Before running source-backed tests or readiness checks, replace the template
database URL with an operator-approved isolated test database. Do not use the
operational `portproject` database for a clean-install verification and do not
copy a developer `.env` into the checkout.

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

## Local RAG capacity envelope

The measured local host has 15.65 GiB physical RAM, an Intel Iris Xe integrated
graphics adapter (no CUDA/NVIDIA GPU), Ollama `qwen3.5:4b` Q4_K_M (about
3.21 GB), `bge-m3` (about 1.22 GB), and a CPU CrossEncoder whose process
footprint was about 2 GB in the measured runs. The API therefore runs one
Uvicorn worker and one active heavy RAG pipeline. A second heavy request may
wait in a bounded one-request queue for up to 60 seconds; when the queue is
full or the wait expires, the API returns HTTP 503 with the safe message
`AI processing capacity is currently busy. Please try again shortly.`

This gate covers document retrieval, reranking, and generation only. Dashboard,
tenant, authentication, billing, and tender routes do not consume its slot and
remain independently available. `/health/ready` reports `capacity` telemetry
(`inference_active`, `inference_limit`, `queue_length`, and `queue_capacity`)
but remains ready while a request is active.

The supported local-demo profile is a single active operator workload with one
heavy pipeline at a time. The bounded queue is a usability guard, not a claim
of multi-user capacity. A controlled internal pilot is **not verified** on this
host: the observed concurrent direct/direct run reached about 0.38 GiB free
RAM, and a serialized pair reached about 0.61 GiB free RAM while pagefile use
rose. A pilot should be re-benchmarked on a machine with at least 32 GiB
physical RAM and measured headroom of at least 4 GiB under its target workload;
that class follows from the current model/process footprint plus the observed
shortfall, rather than from a vendor-specific recommendation. Production
capacity is not certified.

Normal and acceptance services must not run together on this laptop because
both can load the CPU reranker and Ollama models. `start_app.ps1` refuses a
live acceptance API on port 8016; `scripts/start_acceptance.ps1` refuses a live
normal API on port 8001. Stop the other service before switching environments.

The Ollama request uses the configured `keep_alive=10m`: this preserves warm
latency during an active local session but allows idle model eviction. An
explicit `keep_alive=0` request can reclaim model memory before a cold run or
environment switch; do not unload models between normal active requests.

Timeouts are intentionally separate. The queue wait is 60 seconds, the
Ollama generation client timeout is 180 seconds, and the API does not impose a
single total HTTP deadline. Browser/API clients should allow queue wait plus
retrieval and generation time; complex reviewed questions have measured
latencies above two minutes on this CPU host.

The local launcher uses `reload=false`, one worker, and bounded BLAS/tokenizer
threads. Do not enable reload or add workers for this profile: extra workers
duplicate process-local reranker/model state and can recreate the native
resource failures observed during broader concurrent experiments.

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

For database ownership, source relations, and recovery boundaries, use
[DATABASE.md](DATABASE.md) and [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md).
For security-sensitive deployment settings, use [SECURITY.md](SECURITY.md) and
the Phase 02 security report; do not infer production safety from a local
`/health` response.

`pyproject.toml` also declares `src` as a pytest import path, but this does not
replace installing the project dependencies in the supported `.venv`.

The complete test suite includes source-backed integration checks. Those checks
require an approved test database URL and the non-secret billing and tender
fixture bundle described in [Phase 01](hardening/PHASE_01_ACCEPTANCE_ENVIRONMENT_IMPLEMENTED.md).
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
| Capacity | `HEAVY_RAG_CONCURRENCY`, `HEAVY_RAG_QUEUE_CAPACITY`, `HEAVY_RAG_QUEUE_TIMEOUT_SECONDS` | Process-local active-slot and bounded-wait limits. |
| Session/security | `LOGIN_*`, `SESSION_*`, `COOKIE_SECURE`, `QUERY_MAX_CHARACTERS` | Login throttling, session lifespan, transport setting, and query size. |

The full safe template is `.env.example`; it intentionally contains no real
credentials.

## Deployment gate

Before exposing this beyond local development, require: HTTPS, `COOKIE_SECURE`
enabled, least-privilege database credentials, a remediation decision for any
legacy plaintext source-password fields, network restrictions for PostgreSQL
and Ollama, backups for `rag.*` and tender JSON state, and authenticated
acceptance testing for authority/tenant/DO/NO/HO roles.
