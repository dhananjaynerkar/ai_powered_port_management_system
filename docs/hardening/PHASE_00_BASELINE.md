# Phase 00 — safe engineering baseline

**Status: PARTIAL**  
**Completed:** 2026-08-24  
**Scope:** repository boundary, ignore rules, secret/data exposure check, and
required quality checks only. No source refactor, database mutation, or
operational record change was performed.

## Repository state

| Check | Before | After |
|---|---|---|
| Target path | `C:\Users\15dha\OneDrive\Desktop\data\portproject_rag` | same |
| Target `.git` directory | absent | created |
| `git rev-parse --show-toplevel` | incorrectly resolved to unrelated parent `C:/Users/15dha` | target-local repository |
| Branch | parent checkout reported `main` | target `main` |
| Commit | no target commit | `08926c00f3c0dd68b160c85270b448f55fa0c8c9` |
| Baseline tag | none | `verified-baseline-2026-08-24` (`b2a6b87d9739c2f8caa70584b54ed55b4b195550`) |
| Remote | none | `origin` points to the user-provided GitHub URL |
| Working tree | not independently measurable | clean after baseline commit |

The provided GitHub repository was checked read-only. It is public and empty
at audit time. No `push` was performed.

## Intentionally ignored or excluded

The committed `.gitignore` now covers:

```text
.env
.venv/
node_modules/
web/dist/
web/.vite/
web/*.tsbuildinfo
coverage/ and .coverage
pytest/mypy/ruff caches
artifacts/
runtime_logs/
*.log
Python cache and *.egg-info/
```

The local-only `.git/info/exclude` additionally excludes the live tender/PMS
source exports and mutable tender workflow JSON:

```text
src/portproject_rag/tender_workflow/data/tender_workflows.json
src/portproject_rag/tender_workflow/data2/*.csv
src/portproject_rag/tender_workflow/data2/*.docx
src/portproject_rag/tender_workflow/data2/*.pdf
src/portproject_rag/tender_workflow/data2/*.xlsx
src/portproject_rag/tender_workflow/data2/tender_exports/*.csv
```

This is a safety boundary, not a claim that those runtime inputs are
unnecessary. The tender service currently reads them from
`src/portproject_rag/tender_workflow/tender_workflow_service.py` and
`config/tender_workflow.json`; Phase 1/11 must define an approved sanitized
fixture or private artifact delivery path.

## Data and secret exposure assessment

The scan inspected non-generated text/config/source files and printed only
paths/line numbers, never values.

- `.env` was present but ignored and was not staged.
- No hard-coded credential value was found in the staged source/config scan.
- Expected password/token references occur in authentication, billing
  connection plumbing, UI form fields, and session creation; these are code
  symbols/fields, not printed secret values.
- Tender source exports contain columns such as company, owner, contact,
  tenancy, and customer identifiers. They were excluded from the public-ready
  baseline and must not be pushed until sanitized and approved.
- `.env.example` contains configuration names/placeholders only and was
  staged; `.env` was verified absent from the staged file list.

## Staged baseline

The baseline contains 126 source/config/test/document files, including the
application code, current documentation, tests, frontend source, and safe
tender configuration/README files. It excludes local environments, generated
build/runtime outputs, the live database URL, and operational tender/PMS
exports described above.

No source files were rewritten for this phase. The only project-file change
was completing `.gitignore`; repository metadata and the phase report were
then committed as the safe baseline.

## Required checks

| Check | Command | Result |
|---|---|---|
| Python tests | `.\\.venv\\Scripts\\python.exe -m pytest -q` | **PASS — 31 passed** |
| Ruff | `.\\.venv\\Scripts\\ruff.exe check src tests` | **PASS — All checks passed** |
| Frontend build | `npm --prefix web run build` | **PASS — TypeScript/Vite build; 1,670 modules** |

These checks were run after the ignore-rule update and before the baseline
commit. They do not prove authenticated role behavior, production security,
backup/restore, or public data-release safety.

## Blocker and next phase boundary

**BLOCKED for public GitHub push:** the repository is public and local tender
source exports are operational-looking. Do not push until Phase 1 defines an
approved isolated/sanitized fixture and the data-release review is complete.

**Phase 1 is not started.** Per the supplied hardening instructions, this
phase stops here. The next phase requires an approved non-production fixture;
without one, Phase 1 must produce only a fixture plan and remain
`BLOCKED — APPROVED TEST DATABASE REQUIRED`.
