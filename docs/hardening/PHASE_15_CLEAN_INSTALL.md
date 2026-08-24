# Phase 15 — Clean install and reproducibility

**Executed:** 2026-08-25 (local Windows validation)
**Scope:** disposable clone, package installation, frontend installation/build,
documented checks, and isolated health/readiness smoke tests.
**Status:** **PARTIAL — installation and local smoke checks pass; the complete
integration suite needs the approved test services and fixture bundle that are
intentionally outside Git.**

## Objective and boundary

This phase checks that the project can be installed from the repository rather
than succeeding only because the developer machine already has a virtualenv,
`node_modules`, database credentials, model files, or generated workflow
artifacts. No real `.env` value, database password, tenant row, model binary, or
ignored source bundle was copied into the disposable clone.

The validation clone was created from the pushed `main` commit `9d07c10`
(`Record Phase 14 performance baseline`). The actual local checkout remained
separate from the disposable environments.

## Setup corrections made before the final run

The documented setup had three reproducibility gaps:

1. It assumed `.venv` already existed instead of creating it.
2. `pytest` and `ruff` were documented but were not project dependencies.
3. The root quick start omitted `.env` creation and used an unconstrained
   `npm install` despite a committed lockfile.

The minimal corrections are:

- `python -m venv .venv` is now the first Python setup step.
- `pyproject.toml` now exposes a `dev` extra containing `pytest` and `ruff`.
- Setup uses `pip install -e ".[dev]"`, `npm ci`, and
  `Copy-Item .env.example .env`.
- The README and Operations guide state the approved database/fixture
  prerequisite for source-backed integration tests.

The `billing-training` extra remains separate and optional; it is not installed
for the portal/RAG runtime.

## Final disposable-run evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Fresh Python environment | **PASS** | Python 3.12.10; created with `python -m venv .venv` |
| Editable package install | **PASS** | `pip install -e ".[dev]"`; `portproject-rag` imports and CLI help runs |
| Dependency integrity | **PASS** | `pip check` reported no broken requirements |
| Development tools | **PASS** | pytest 8.4.2; Ruff 0.16.4 |
| Ruff | **PASS** | `ruff check src tests` — all checks passed |
| Non-live regression suite | **PASS** | 31 passed after excluding explicitly source-backed integration modules |
| Full regression suite | **PARTIAL** | 34 passed, 14 failed; failures are external database or ignored fixture prerequisites, not import/install failures |
| Frontend dependency install | **PASS** | `npm ci`; 70 packages installed, audit reported 0 vulnerabilities |
| Frontend production build | **PASS** | `npm run build` completed with Vite 7.3.6 |
| API liveness smoke | **PASS** | Fresh API on isolated port 8015 returned HTTP 200 and `X-Request-ID` |
| API readiness smoke | **EXPECTED BLOCK** | HTTP 503 with `init_error=database_unavailable` from the safe `.env.example` placeholder URL |
| UI delivery smoke | **PASS** | Fresh Vite instance on isolated port 5175 returned HTTP 200 |
| Secret tracking check | **PASS** | `.env.example` is tracked; `.env`, `.venv`, `node_modules`, and artifacts are ignored/untracked |

The disposable API and Vite processes were stopped after the checks. The
existing project services were not replaced or reconfigured.

## Full-suite failure classification

The 14 expected clean-clone failures are attributable to two missing approved
inputs:

- **Database-backed checks (8):** authority metrics, live corpus state, RAG gold
  references, and tenant pagination. The template URL intentionally uses the
  `USER`/`CHANGE_ME` placeholder and must not be replaced with guessed or
  copied credentials.
- **Ignored runtime/source fixtures (6):** four billing service tests require
  `artifacts/billing_forecast/runtime/...`; two tender tests require the
  generated `data2/tender_exports/tender_plot_master.csv` source bundle.

Those files are ignored by design because they can contain private operational
data or generated model artifacts. Phase 01 defines the approved isolated
fixture contract; it must be provisioned before claiming a full integration
pass. The clean base environment confirmed that `pandas` and `xgboost` are not
installed unless the optional `billing-training` extra is requested (NumPy and
scikit-learn are transitive dependencies of the RAG embedding stack).

## Reproduction procedure

From a fresh clone, follow [Operations](../OPERATIONS.md):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Set-Location web
npm ci
npm run build
Set-Location ..
Copy-Item .env.example .env
\.venv\Scripts\python.exe -m pytest -q
\.venv\Scripts\ruff.exe check src tests
```

Before the full suite or `/health/ready`, provision only the approved isolated
database, Ollama models, and non-secret billing/tender fixture bundle. Never
copy the developer `.env`, database dump, tenant data, or model cache into Git.

## Remaining reproducibility risk

Python dependency ranges are declared in `pyproject.toml`, but the project does
not yet commit a Python lockfile. This run proves clean installation against the
current resolver output; it does not claim bit-for-bit rebuilds across future
package releases. A lockfile should be introduced only as a separately scoped
release-engineering change after choosing the supported Python/OS matrix.

**Phase 15 stops here.**
