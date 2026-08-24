# End-to-end data-flow audit

## Authority login

React login handler -> POST /api/authority/login -> Credentials validation ->
login rate-limit check -> auth._external_authority reads public.admin_users and
public.admin_roles -> password verification -> rag.user_session token digest
and rag.audit_event write -> HTTP-only cookie -> React user state.

## Tenant login

React tenant login -> POST /tenant/api/auth/login -> auth._external_tenant reads
public.applicant_registration -> password verification -> shared opaque session
flow. Tenant UI permissions are independently enforced by API dependencies.

## Dashboard

Dashboard component -> GET /api/authority/dashboard/metrics -> authority_metrics
-> _authority_land_metrics -> public.plot, public.m_property_status,
public.applicant_property_mapping, and public.applicant_registration -> live
aggregates and quality counters -> React charts/KPIs.

## Tenant table

Tenant component filter/sort/page state -> GET /api/authority/tenants with
server parameters -> authority_tenants validates dates, allowlists sort columns,
builds parameterized filters, counts rows, selects one page, and reads live
filter options -> React table and pagination.

## Private RAG chat

Question input -> POST /api/v1/query or compatible answer route -> QueryRequest
validation -> current_user -> validate_query -> selected local model ->
retrieval.retrieve -> embedding, lexical/vector candidates, ACL, RRF, rerank,
context -> generate_grounded_answer -> citation validation -> answer payload
with real source/page metadata -> optional rag.chat_message write and UI.

## Agenda creation and handoff

Create Agenda -> POST /api/v1/workflow/agendas with private chat id ->
create_agenda_from_chat verifies DO role, ownership, messages, and cited answer
-> rag.agenda, agenda_version, agenda_message writes -> role/state-specific
transition -> context_capsule and handoff message -> selected workflow UI.

## Billing

Billing selector -> GET rules/tenancies -> selected tenancy prefill reads CSV,
public PMS customer/profile/history/rate tables -> React form -> POST predict ->
BillingPredictionService evaluates exported XGBoost JSON plus deterministic tax
formula -> result summary and optional chat message.

## Tender

Tender context -> GET config/plots/checklist -> source exports and checklist
files -> proposal fields and checklist answers -> calculate -> workflow JSON
record/action -> draft markdown/PDF endpoints -> React modal.

## Logout

React logout -> POST logout alias -> delete_session removes token digest and
clears cookie -> UI returns to login.

## Failure behavior

The API maps validation to 422, missing session to 401, forbidden role/ownership
to 403 or 404, invalid workflow state to 409, and unavailable local
dependencies/artifacts to 503. UI-specific authenticated error behavior is
implemented but full role walkthrough is NOT VERIFIED here.

