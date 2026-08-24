# API reference audit

The complete route inventory is in docs/API_REFERENCE.md. This audit adds
ownership, consistency, and coverage observations.

## Route groups

| Group | Routes | Protection |
| --- | --- | --- |
| Health | /health, /health/ready | Public local diagnostics. |
| Auth | login/logout/me/bootstrap aliases | Login public; session routes protected. |
| Corpus | /api/v1/corpus, state, documents, local-llms | Signed in. |
| Authority | dashboard/metrics, tenants | Authority role. |
| Chat | sessions CRUD, /api/v1/query, /api/v1/chat, /api/v1/policy/query | Session/owner rules. |
| Agenda | drafts, officers, agendas, revisions, transition, query | Authority plus workflow owner/state. |
| Billing | status, rules, tenancies, prefill, predict | Authority role. |
| Tender | config, plots, checklists, calculate, workflows, documents | Authority role. |

## Validation and errors

Pydantic request models constrain lengths, enum-like actions, UUIDs, ranges,
and model names. API errors use 401 for missing session, 403/404 for protected
resource visibility, 409 for lifecycle conflicts, 422 for validation, and 503
for local AI/artifact availability.

## Compatibility observations

The answer behavior has aliases /api/v1/policy/query, /api/v1/query, and
/api/v1/chat. Logout and identity endpoints also have role-specific aliases.
They should not be removed without client inventory and deprecation policy.

## Coverage

Route existence is visible through OpenAPI and source decorators. Focused
Python tests cover key service behavior, but complete request-level tests for
every route, every authorization branch, and every UI consumer are NOT VERIFIED.

## API risks

- Error details should remain human-readable without exposing database/provider
  internals.
- Version reporting differs between API 0.2.0 and Python package 0.1.0.
- Pagination is implemented for tenants but not all list-like feature routes.
- Contract tests should be added before extracting routers from api.py.

