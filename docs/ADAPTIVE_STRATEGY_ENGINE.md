# Adaptive strategy engine

The engine observes each page’s quality score, classification, image/table
signals, and local capabilities. It generates more than one viable strategy,
selects by expected quality, confidence, and cost, and persists the selected
plan plus fallback in `artifacts/strategy-decisions.*`.

It deliberately uses deterministic selection: these inputs are observable,
cheap, and safety-critical. OCR is a candidate only when the executable and
Python adapter are both available. Without them, image-only pages select
`quarantine`, retaining the source for later reprocessing. A later capability
change regenerates decisions instead of preserving an old hard-coded outcome.

Query plans likewise choose dense, lexical, page-filtered, and graph operations
only from query features and the graph assessment. Low evidence confidence must
cause the caller to retry the recorded fallback plan; live evidence scoring
cannot be validated until data is stored.
