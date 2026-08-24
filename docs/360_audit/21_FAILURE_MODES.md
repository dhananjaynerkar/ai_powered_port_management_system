# Failure-mode analysis

| Failure | Current behavior | Status/gap |
| --- | --- | --- |
| PostgreSQL unavailable | Startup migration/readiness or protected route fails; launcher health check stops. | User-facing recovery guidance should be tested. |
| Ollama unavailable | Readiness false; model discovery/answer returns availability error. | Implemented; alerting missing. |
| Embedding model missing | Lifespan reports missing model and not-ready. | Implemented. |
| Reranker fails | Lifespan catches initialization failure and not-ready. | Implemented; fallback retrieval behavior needs explicit test. |
| No retrieved evidence | Generation is not called. | Covered by guardrail test. |
| Citation validation fails | Generated response is rejected/retried according to generation settings. | Covered partially; semantic faithfulness missing. |
| Invalid workflow transition | Role/state/owner validation returns conflict. | Covered by service logic; concurrent test missing. |
| Tender JSON corrupted | Service load/save error likely prevents workflow operation. | Recovery/backup runbook NOT VERIFIED. |
| Billing artifact missing | Billing service raises availability error. | Focused test coverage exists. |
| UI/backend disconnect | React sets loading/error states and can retry selected views. | Full browser verification NOT VERIFIED. |
| Invalid tenant date/filter | API returns 422 and does not run the query. | Covered by test. |
| Linked chat delete | API returns 409 and preserves provenance. | Implemented and documented. |

## Priority resilience work

Add operator-friendly recovery steps, readiness monitoring, backup/restore
tests, concurrency tests, and authenticated browser failure-state checks.

