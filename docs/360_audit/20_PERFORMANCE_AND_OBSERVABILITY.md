# Performance and observability audit

## Measured in implementation

RAG responses include embedding, lexical retrieval, dense retrieval, rerank,
context assembly, generation, citation-validation, and total duration fields.
The launcher writes API/UI output and error logs under artifacts/runtime-logs.
Agenda, login, workflow, billing, and tender operations have source-level audit
or event behavior where implemented.

## Likely bottlenecks

| Area | Classification | Reason |
| --- | --- | --- |
| CrossEncoder startup/rerank | Likely bottleneck | Model initialization and CPU prediction are on request/startup path. |
| Ollama embedding/generation | Likely bottleneck | Local model inference and configured timeouts. |
| Dashboard aggregates | Not measured | Multiple live aggregate queries per request. |
| Tenant count + page query | Not measured | Count and page query plus filter options. |
| Large React entry/render | Likely maintainability/perf risk | Large component/state surface, but no browser profile. |
| Tender PDF generation | Not measured | Depends on document size and ReportLab work. |

No optimization should be applied until p50/p95 traces and query plans are
captured.

## Observability gaps

- No centralized metrics or trace exporter.
- No persisted model latency/error dashboard.
- No automated alert for readiness degradation.
- No structured correlation ID across browser/API/RAG/workflow.
- Logs may not be sufficient for multi-process tender diagnosis.

## Safe next measurement

Capture request route, principal role (not secrets), correlation ID, retrieval
timings, model name, candidate count, status, and error class with redaction.
Run database EXPLAIN only in a safe read-only environment.

