# Runtime recovery

Two real adaptive recovery events are recorded in `artifacts/runtime-events.*`.
The table event showed that structured enrichment may not block core ingestion;
the selected recovery is raw page context with retained provenance. The second
event stalled after a page insert while awaiting an embedding batch. A fresh
two-text BGE-M3 probe previously completed in 0.6 seconds, so the exact cause
is not proven; the system now applies a configurable 45-second embedding
timeout rather than waiting indefinitely.

The database retains the first fully committed document (7 pages, 16 vectors).
The stalled document transaction was stopped and did not commit partial rows.
