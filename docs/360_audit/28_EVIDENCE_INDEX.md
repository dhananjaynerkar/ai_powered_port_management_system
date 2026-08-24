# Evidence index

Confidence describes how directly the conclusion is supported by current source
or observed validation.

| Conclusion | Evidence | Why it supports the conclusion | Confidence |
| --- | --- | --- | --- |
| Target is a React/Vite + FastAPI portal | web/package.json, web/src/main.tsx, api.py | Manifests and entrypoints name the frameworks and app shell. | HIGH |
| API runs on 8001 | src/portproject_rag/server.py | uvicorn invocation binds 127.0.0.1:8001. | HIGH |
| UI runs on 5173 | start_app.ps1 and Vite runtime | Launcher starts Vite and health-checks 5173. | HIGH |
| App uses PostgreSQL/pgvector | database.py, retrieval.py, settings.py | Migration creates vector tables/indexes and retrieval queries them. | HIGH |
| RAG is hybrid | retrieval.py retrieve/_candidate_rows | Lexical and dense queries are fused by RRF. | HIGH |
| RAG uses ACL filtering | retrieval.py ACL SQL | Current role is checked against chunk ACL roles before candidates are returned. | HIGH |
| Answers carry page citations | api.py build_evidence_payload and generation.py | Retrieved page metadata becomes source payload and citations are validated. | HIGH |
| Mapping rows are not unique tenants | api.py _tenant_terminology and authority metrics tests | Contract explicitly exposes mapping_records separately from applicant/tenancy counts. | HIGH |
| Tenant pagination is server-side | api.py authority_tenants and tenant tests | Count, filter, sort allowlist, limit, offset, and options run in API SQL. | HIGH |
| Agenda requires cited chat evidence | workflow.py create_agenda_from_chat | It rejects no-message or no-sourced-assistant conversations. | HIGH |
| Agenda handoff is role/state governed | workflow.py transition_agenda | It checks owner, source role, allowed states, target role, and writes history. | HIGH |
| Linked chats cannot be deleted | api.py delete_chat_session | It checks workflow_draft and agenda links and returns 409. | HIGH |
| Billing separates model and formula | billing/prediction_service.py | XgbJsonModel output and deterministic formula/tax fields are both returned. | HIGH |
| Tender uses source-backed inputs and JSON state | tender_workflow_service.py/config/data | Service loads exports/checklists and persists records in target JSON. | HIGH |
| Current RAG quality score is unknown | tests and evaluation docs | Timings/tests exist, but no reviewed Recall/MRR/faithfulness result was observed. | HIGH |
| Full authenticated UI is not verified | validation boundary and no test account used | No real credentials were used for role walkthrough. | HIGH |
| External deployment needs secure cookies | settings.py COOKIE_SECURE default false | Local HTTP default is unsafe for public HTTPS deployment. | HIGH |
| Source credential storage is a production risk | auth.py external identity queries | Legacy plaintext/password-field fallback is read during verification. | HIGH |
| Frontend/API modularity is a future risk | file-size/source inventory | Main frontend and API boundaries concentrate many features. | MEDIUM |
| Graph RAG is not justified by current evidence | strategy.py query plan and architecture docs | Strategy selects graph only with graph evidence; no graph store is present. | HIGH |

## Evidence limitations

Live database schema/readiness was observed without including rows or secrets.
Protected UI behavior, production deployment, query plans, and business semantic
sign-off remain NOT VERIFIED.

