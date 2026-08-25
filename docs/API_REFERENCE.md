# API reference

**Status: CURRENT SOURCE OF TRUTH**

All API paths below are implemented in `src/portproject_rag/api.py`. Protected
routes require the opaque `portproject_session` cookie. Authority routes also
require an Authority database identity; agenda routes validate the active
`DO`/`NO`/`HO` source role as needed.

## Health and authentication

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | Public local | Basic API/settings health. |
| GET | `/health/ready` | Public local | RAG readiness plus aggregate corpus counts. |
| GET | `/api/v1/auth/bootstrap-status` | Public | Reports that signup is disabled. |
| POST | `/api/v1/auth/bootstrap` | Public | Intentionally returns `410`; existing database accounts must sign in. |
| POST | `/api/authority/login` | Public | Authority authentication. |
| POST | `/tenant/api/auth/login` | Public | Tenant authentication. |
| POST | `/api/v1/auth/logout`, `/api/authority/logout`, `/tenant/api/auth/logout` | Signed in | Ends the current session. |
| GET | `/api/v1/auth/me`, `/api/authority/me`, `/tenant/api/auth/me` | Signed in | Current user display payload. |

Login request body: `{ "username": "...", "password": "..." }`.

## Corpus and local model discovery

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/public/corpus` | Public | Aggregate corpus counts only. |
| GET | `/api/v1/corpus` | Signed in | Corpus dashboard metrics. |
| GET | `/api/v1/corpus/state` | Signed in | Per-document index state. |
| GET | `/api/v1/documents` | Signed in | Document list with page/chunk counts. |
| GET | `/api/v1/local-llms` | Signed in | Locally available completion models. |

## Dashboard and tenant mappings

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/authority/dashboard/metrics` | Authority | Live plot/mapping metrics and data-quality counters. |
| GET | `/api/authority/tenants` | Authority | Server-paginated applicant-property mappings. |

Tenant query keys: `query`, `status`, `lease_type`, `allotment_status`,
`date_from`, `date_to`, `page`, `page_size` (1–100), `sort_by`, and
`sort_direction`. Date values must be `YYYY-MM-DD`; `sort_by` is restricted to
the endpoint's source-column allowlist.

## Private chat and document RAG

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/chat/sessions` | Signed in | Creates a private conversation. |
| GET | `/api/v1/chat/sessions` | Signed in | Lists the current principal's conversations. |
| GET | `/api/v1/chat/sessions/{chat_session_id}` | Owner | Reads one private conversation. |
| DELETE | `/api/v1/chat/sessions/{chat_session_id}` | Owner | Deletes an unshared private conversation; returns `409` if workflow-linked. |
| POST | `/api/v1/policy/query`, `/api/v1/query`, `/api/v1/chat` | Signed in | RAG answer with citations and optional chat persistence. |

Question payload keys are `question`, optional `limit` (1–20), optional
`chat_session_id`, and optional local `llm_model`. Successful answer payloads
include `answer`, `sources`, `citation_valid`, `llm_model`, candidate count,
and timing fields.

## Agenda workflow

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET/POST | `/api/v1/workflow/drafts` | Signed in | Personal workflow drafts. |
| GET | `/api/v1/workflow/officers` | Authority | Active DO/NO/HO directory. |
| GET/POST | `/api/v1/workflow/agendas` | Authority | Assigned agenda list / create agenda from cited chat. |
| GET | `/api/v1/workflow/agendas/{agenda_id}` | Participant | Agenda, official messages, versions, and evidence snapshots. |
| POST | `/api/v1/workflow/agendas/{agenda_id}/revisions` | Current owner | Saves a new official draft version. |
| POST | `/api/v1/workflow/agendas/{agenda_id}/transition` | Current owner | Performs state-authorized handoff/approval/rejection. |
| POST | `/api/v1/workflow/agendas/{agenda_id}/query` | Current owner | Adds a grounded AI answer to the official thread. |

Supported transitions: `submit_to_nodal`, `return_to_do`, `submit_to_hod`,
`approve`, and `reject`. The service verifies owner, source role, state, and
target officer before mutation.

## Billing forecast

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/billing/status` | Authority | Artifact availability/status. |
| GET | `/api/v1/billing/rules` | Authority | Form rules, rates, labels, and limits. |
| GET | `/api/v1/billing/tenancies` | Authority | Eligible tenancy choices. |
| GET | `/api/v1/billing/tenancies/{tenancy_id}/prefill` | Authority | Source-backed selected-tenancy prefill. |
| POST | `/api/v1/billing/predict` | Authority | Validated billing forecast and calculation context. |

## Tender publication

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/tender/config` | Authority | Form and workflow configuration. |
| GET | `/api/v1/tender/plots` | Authority | Eligible vacant plots. |
| GET | `/api/v1/tender/plots/{plot_id}` | Authority | Source-backed plot detail/prefill. |
| GET | `/api/v1/tender/checklists/{checklist_key}` | Authority | LAC checklist evidence. |
| POST | `/api/v1/tender/calculate` | Authority | Deterministic proposal calculation. |
| GET/POST | `/api/v1/tender/workflows` | Authority | List/create local tender workflow records. |
| GET | `/api/v1/tender/workflows/{workflow_id}` | Authority | One workflow record. |
| POST | `/api/v1/tender/workflows/{workflow_id}/actions` | Authority | Validated state action. |
| GET | `/api/v1/tender/workflows/{workflow_id}/documents/{document_kind}` | Authority | Generated draft PDF (`lac`, `board-note`, or `tender`). |

## Error contract

FastAPI validation errors use `422`; missing authentication is `401`; missing
authority/ownership is `403` or `404` depending on resource visibility;
invalid lifecycle state is `409`; unavailable local model or billing artifacts
is `503`. Clients should show the human-readable `detail` message instead of
raw exception text.
