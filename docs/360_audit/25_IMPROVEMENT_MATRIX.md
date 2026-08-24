# Improvement opportunity matrix

## Must fix before external deployment

| Problem | Evidence | Benefit | Risk/validation |
| --- | --- | --- | --- |
| HTTPS and secure cookie deployment | settings.py COOKIE_SECURE default false | Prevent session transport exposure | Deploy behind HTTPS and test cookies. |
| Legacy source password handling | auth.py fields/verification | Reduce credential risk | Requires source owner decision and auth regression tests. |
| Least-privilege DB and backup plan | Broad feature data access and no verified runbook | Limit blast radius/recover state | Role/schema migration and restore test. |

## Should fix

- Build reviewed RAG evaluation set and latency baseline.
- Add adversarial ACL and role workflow tests.
- Add readiness alerting and correlation IDs.
- Add tender JSON corruption/concurrency tests.
- Add authenticated UI/E2E test matrix.

## Nice to have

- Incremental component extraction.
- More granular data-quality reasons.
- Tenant detail view if the business requires it.
- Centralized metrics and distributed tracing only when deployment scale needs it.

## Requires business decision

- Definitive meaning of A/V/RG status and occupancy.
- Whether mapping records, tenancies, and unique applicants need separate KPIs.
- Official workflow notification and retention policy.
- Billing source-rate precedence and tender approval gate.

## Do not change now

- Do not replace PostgreSQL/pgvector, Ollama, or current RAG pipeline without
  measured evaluation.
- Do not add graph RAG/microservices/agents for appearance.
- Do not rewrite the UI or move APIs before contract/E2E coverage.
- Do not delete historical reports or compatibility aliases without evidence.

