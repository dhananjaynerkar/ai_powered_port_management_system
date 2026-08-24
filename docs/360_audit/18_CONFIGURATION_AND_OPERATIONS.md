# Configuration and operations audit

## Configuration groups

| Group | Settings | Classification |
| --- | --- | --- |
| Database | DATABASE_URL, SCHEMA_NAME, DOCUMENT_SCHEMA_NAME, VECTOR_SCHEMA_NAME | Required/production-sensitive |
| Embedding | EMBEDDING_ENDPOINT, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, EMBEDDING_TIMEOUT_SECONDS | Required for RAG readiness |
| Generation | GENERATION_ENDPOINT, LLM_PRIMARY_MODEL, LLM_FALLBACK_MODEL, LLM_ALLOW_FALLBACK | Required for answers; local-only |
| Retrieval | RETRIEVAL_LIMIT, CANDIDATE_MULTIPLIER, RRF_K, RERANK_CANDIDATE_COUNT, parent/context limits | Safe bounded defaults |
| Ingestion | CHUNK_MIN/MAX, BATCH_SIZE, TABLE_MAX_PAGES, EMBEDDING_BATCH_SIZE | Throughput/quality controls |
| Reranker | RERANKER_MODEL, DEVICE, FP16, MAX_LENGTH, BATCH_SIZE | Startup/runtime-sensitive |
| Sessions | LOGIN_MAX_FAILED_ATTEMPTS, LOGIN_RATE_LIMIT_WINDOW, SESSION_IDLE/ABSOLUTE | Security-sensitive |
| Transport | COOKIE_SECURE | Must be true with HTTPS |
| Billing | BILLING_* environment overrides | Artifact/rule deployment-sensitive |

The authoritative safe key list is .env.example; no secret values are included
in audit documents.

## Startup sequence

Start_App.cmd -> start_app.ps1 -> port/health checks -> API subprocess ->
FastAPI lifespan -> migrate configured schemas/extensions/views -> Ollama tags
check -> reranker initialization -> readiness state -> Vite subprocess -> UI.

## Health semantics

/health proves settings initialization and API process health. /health/ready
reports RAG readiness and corpus counts; it is the meaningful dependency gate.
UI HTTP 200 proves only that Vite is serving.

## Operational gaps

- No formal service supervisor beyond the local launcher.
- No deployment secret manager is implemented.
- No backup/restore runbook for rag and tender state is verified.
- No metrics/alerting backend is implemented.
- Runtime logs are local files.

