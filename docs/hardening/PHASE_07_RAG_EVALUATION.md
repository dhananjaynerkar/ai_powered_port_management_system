# Phase 7 - current RAG baseline evaluation

Status: COMPLETE. The existing retrieval and generation pipeline was measured against the reviewed golden set. No retrieval, reranker, chunking, prompt, model, or limit was tuned.

Completed: 2026-08-25. This was a local, measurement-only run against the indexed portproject database and local Ollama. No source documents, answers, credentials, or tenant data were uploaded.

## Reproducible artifacts

Evaluator: src/portproject_rag/evaluation.py
Tests: tests/test_rag_evaluation.py
Command: .venv\Scripts\python.exe -m portproject_rag.cli evaluate-gold --gold evaluation/rag_gold_v1.json --output artifacts/evaluation/rag_baseline_v1

The ignored JSON artifact preserves expected pages, returned chunks and scores, context text, answers, citations, timings, and error categories. The CSV is a compact review table. Raw passages remain out of Git. After correcting the evaluator's classification of citation-validation fallbacks, the artifact categories were recomputed from the unchanged raw evidence; retrieval and generation were not rerun or altered.

## Active settings

Embedding: bge-m3 (1024 dimensions); LLM: qwen3.5:4b; reranker: BAAI/bge-reranker-v2-m3 on CPU; retrieval limit: 8; rerank candidates: 8; RRF k: 60; parent window: 1; context budget: 800 estimated tokens; output budget: 80; temperature: 0.1; thinking disabled; citation retries: 1.

These are the active local values captured without the database URL. No setting was changed.

## Baseline results

All 11 cases completed retrieval and returned from the generation endpoint. Transport failures: 0. Five answers fell back after citation validation and are counted as generation failures in the error breakdown.

Recall@1: 0.44; Recall@3: 0.56; Recall@5: 0.56; MRR: 0.50; NDCG@5: 0.43 (nine answer-bearing cases).

Citation-page accuracy across all 11: 0.2273. No-answer accuracy: 0.3333 (1/3). Relevance is an exact filename-plus-page pair from the reviewed set.

Faithfulness, answer relevance, and unsupported-claim rate are not automatically scored because no independent approved judge or human annotation exists. The artifact records this gap rather than fabricating scores.

## Latency in milliseconds

Embedding mean/p50/p95: 1247.64 / 1157 / 1998.5. Lexical: 20.18 / 12 / 50. Dense: 76.73 / 41 / 189.5. Rerank: 13658 / 12504 / 20974. Context: 83.73 / 59 / 166. Generation: 76229.36 / 81048 / 94717.5. End-to-end: 91424.09 / 94195 / 115265.5.

CPU reranking and local generation dominate the observed cost. This is diagnostic evidence only; no model switch or budget reduction was made.

## Error breakdown

Document/page never retrieved: 4 (RG-005, RG-007, RG-010, RG-011).

Generation/citation-validation failure: 5. Citation-page mismatch: 9. Incorrect refusal: 3. Correct refusal: 1 (RG-009). Context-truncation possible: 3 (budget-boundary proxy). Reranker-specific failure: not observable because the public result does not expose pre-rerank candidates.

## Findings and unimplemented experiments

The measured gaps are retrieval false negatives, citation/page grounding failures, inconsistent negative-case behavior, CPU inference latency, and missing independent claim review.

Only after approval: test query rewrite/lexical expansion (target Recall@5 at least 0.80 with no negative leakage); page-scoped citation adjudication (target at least 95% validator pass and 90% gold-page accuracy); approved local generation benchmarks (target end-to-end p95 at most 60 seconds without quality regression); and a deterministic missing-input gate (target at least 90% negative accuracy and zero fabricated numeric answers). These are proposals only, with risks of broader context, over-refusal, slower responses, or reduced completeness.

Phase 7 stops here. No tuning or model replacement was applied. Full tests, Ruff, compile checks, and React build are rerun before commit; raw artifacts remain local and ignored.
