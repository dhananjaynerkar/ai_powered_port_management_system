# Project overview

## Problem solved

The portal provides one authenticated interface for port land operations,
applicant-property mapping review, evidence-grounded policy questions, formal
agenda handoffs, billing forecasts, and source-backed tender preparation.

## Users and roles

| User concept | Evidence | Capabilities |
| --- | --- | --- |
| Authority portal user | auth.py and public.admin_users/public.admin_roles | Authority dashboard, tenant mappings, chat, agendas, billing, tender. |
| Data Entry Operator (DO) | workflow.py authority_identity and ROLE_LABELS | Creates agenda drafts from cited private chats and submits to Nodal Officer. |
| Nodal Officer (NO) | workflow.py transition_agenda | Reviews, returns to DO, or submits to HOD. |
| Head of Department (HO) | workflow.py transition_agenda | Approves or rejects submitted agenda. |
| Tenant portal user | auth.py _external_tenant and tenant login route | Tenant-authenticated portal surface and document access allowed by route. |
| Developer/operator | start_app.ps1, CLI, docs | Starts services, checks health, inspects corpus, migrates, and ingests. |

The API exposes a broad portal role of authority and re-checks DO/NO/HO for
official agenda operations. These are not interchangeable business concepts.

## Major feature areas

- Authentication and opaque sessions.
- Corpus state and document list.
- Authority dashboard live plot/mapping metrics.
- Server-filtered and server-paginated tenant mapping table.
- Private citation-backed RAG chat.
- Official agenda state machine with evidence snapshots.
- Billing forecast backed by database prefill and local model artifacts.
- Tender publication workflow backed by source exports, checklist evidence,
  local JSON state, deterministic calculation, and draft PDFs.

## Runtime maturity

The source and focused integration tests show the features are implemented.
Live protected UI acceptance for every role is NOT VERIFIED in this audit because
real database credentials were not used. The API readiness contract and local UI
reachability were verified.

## Source of truth

The current architecture and operations source of truth are:

- docs/ARCHITECTURE.md
- docs/OPERATIONS.md
- docs/API_REFERENCE.md
- this 360_audit directory

Older milestone reports are historical unless they explicitly state current
runtime evidence.

