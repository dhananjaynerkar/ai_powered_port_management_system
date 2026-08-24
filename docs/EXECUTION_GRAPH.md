# Execution graph

`artifacts/execution-graph.json` is the first graph built strictly from actual
runtime execution data. It captures situation → strategy → tool → failure →
fallback → result for the measured table-stall event, plus the separate
embedding-stall observation. PostgreSQL JSON/relational storage is sufficient
at this evidence volume; a graph database is not justified.
