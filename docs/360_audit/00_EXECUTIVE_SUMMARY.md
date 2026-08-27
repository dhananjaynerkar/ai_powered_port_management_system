# 360-degree audit — executive summary

## Scope

This is an audit-only report created from the supplied audit prompt. It is based
on the target checkout. The local filesystem path is intentionally omitted from
the public repository copy.
The separate AI PMS checkout was treated as a reference only and was not used
as a runtime dependency.

Evidence sources include Python/React source, pyproject.toml, package manifests,
environment template names, launchers, migrations, tests, generated runtime
artifacts, existing documentation, and live readiness evidence already captured
for this target. No credentials, passwords, tenant rows, or production data are
included.

## What the project is

AI-Powered Port Management System is a local-first React/Vite and FastAPI portal for a Port
Management System. It authenticates existing Authority and Tenant database
accounts, exposes live land and applicant-property mapping views, answers
document questions with page citations, and supports governed agenda, billing,
and tender workflows.

## Verified current state

- API entry: src/portproject_rag/server.py, using pms_api.app:create_runtime_app.
- UI entry: web/src/main.tsx.
- API port: 8001 on loopback; UI port: 5173 on loopback.
- PostgreSQL source database: configured through PORTPROJECT_RAG_DATABASE_URL.
- RAG readiness observed as ready: 48 documents, 1,476 pages, 3,399 chunks,
  and 3,399 vectors; 1 document remained pending extraction at the observed
  snapshot.
- Project virtual-environment validation observed: 31 tests passed, Ruff passed,
  and the React production build passed.

## Strongest areas

1. The system has a real readiness endpoint separate from basic process health.
2. Retrieval uses lexical search, vector search, ACL filtering, rank fusion,
   reranking, parent context, and citation validation.
3. Dashboard and tenant APIs distinguish applicant-property mapping records from
   unique applicants and tenancy identifiers.
4. Agenda transitions enforce owner, role, state, and target-officer checks.
5. Billing and tender behavior is source-backed and covered by focused tests.

## Highest-risk gaps

| Priority | Finding | Status |
| --- | --- | --- |
| P1 | Secure-cookie/HTTPS deployment hardening is required outside loopback. | Implemented locally; production decision required |
| P1 | External login inherits legacy source password-field risk. | Evidence found; remediation requires source-system decision |
| P2 | Tender JSON persistence is process-local and not transactional across processes. | Implemented; concurrency limitation |
| P2 | The frontend is concentrated in large main.tsx and styles.css files. | Maintainability risk; no broad refactor recommended now |
| P2 | Quantitative RAG quality metrics are not established in the current runtime snapshot. | Not verified |

## Audit conclusion

The project is a functioning integrated local application, not a static UI
mock. Its main credibility risks are deployment hardening, inherited source
identity storage, RAG evaluation coverage, and long-term frontend modularity.
The smallest high-value next steps are security deployment decisions, a real
reviewed RAG evaluation set, observability for local AI dependencies, and
incremental feature-boundary extraction.

## What was not changed

This audit created only documentation under this folder and preserved the
existing source, API, SQL, database state, model settings, workflow behavior,
artifacts, and reference checkout.
