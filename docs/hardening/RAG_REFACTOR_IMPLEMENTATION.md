# RAG Recovery and Refactor — Implementation Report

**Scope:** retrieval, grounded generation, citation safety, routing, diagnostics, and the honest frontend context selector.

**Stop boundary:** this report stops at the RAG refactor. It does not change billing or tender business logic, does not migrate the database, and does not start a later workflow phase.

## Executive result

**FINAL RESULT: PARTIAL**

The retrieval path, ACL boundary, reranker lifecycle, context assembly, routing, typed errors, evaluation contract, and citation-repair path were implemented and tested. The reviewed 11-question retrieval evaluation completed 11/11 questions with no retrieval failures and improved the measured retrieval metrics over the existing baseline. The real local generation run completed 10 calls, timed out on one call, and produced six citation-valid answers; five questions were classified as generation/citation failures. Faithfulness, answer relevance, and unsupported-claim rate remain unscored because no independent adjudicator was available and no score is fabricated.

The acceptance API suite passed after reset: **24 passed**. A single earlier run had one transient HTTP 500 caused by an acceptance PostgreSQL connection timeout while recording a login attempt; the affected test passed after fixture reset and passed again in the final full run. The acceptance fixture check passed after the final run.

## Required result summary

| Gate | Result | Evidence |
|---|---|---|
| Acceptance fixture safety | PASS | `scripts/check_acceptance_fixture.ps1`; database `portproject_acceptance`; sentinel `acceptance/1` |
| Retrieval evaluation | PASS | `artifacts/evaluation/rag_recovery_after_retrieval_final2.json`; 11/11 retrievals completed |
| Generation/citation evaluation | PARTIAL | `artifacts/evaluation/rag_recovery_after_full_final.json`; 10 generation calls returned, 6 citation-valid, 1 timeout |
| Acceptance API E2E | PASS after reset | `tests/acceptance`: 24 passed |
| Python suite | PASS | 77 passed, 27 opt-in acceptance tests skipped in the non-acceptance run |
| Ruff | PASS | `ruff check src tests` |
| Frontend build | PASS | `web`: `npm run build` |
| Browser E2E | NOT AVAILABLE | No configured Playwright/Cypress/Selenium run was present |
| Operational `portproject` DB modified | NO | Acceptance guard refused operational DB; mutable runs used only `portproject_acceptance` |

## Safety and data boundaries

The acceptance operations used the existing scripts and private `.env.acceptance` process environment. The guard verified:

```text
database=portproject_acceptance
sentinel=acceptance/1
tender_storage=tests\runtime\tender\tender_workflows.json
```

The API readiness check during the acceptance run returned HTTP 200 with `database=portproject_acceptance` and `rag_ready=true`. The operational tender JSON path was not used. No password, session cookie, token, hash, or database credential is included in this report.

## Evidence inventory

- Existing reviewed contract: `evaluation/rag_gold_v1.json` (11 questions).
- New structured contract: `evaluation/rag_answer_contract_v2.json`. It carries question type, answer shape, required evidence items, acceptable documents/groups, expected pages, and role scope without inventing new facts; it is sourced from the reviewed v1 set.
- Existing baseline: `artifacts/evaluation/rag_recovery_before.json`.
- Retrieval result after the final reranker-prefix correction: `artifacts/evaluation/rag_recovery_after_retrieval_final2.json` and `.csv`.
- Real local generation result: `artifacts/evaluation/rag_recovery_after_full_final.json` and `.csv`.
- Focused regression coverage: `tests/test_rag_recovery.py` and `tests/test_rag_answer_contract_v2.py`.

## Before/after measurements

The metrics below use expected filename+page pairs from the reviewed contract. “Any hit” means at least one expected page is present in the ranked result. “Evidence coverage” measures how many expected filename+page pairs are present; these are intentionally separate metrics.

| Metric | Existing baseline | Refactored retrieval | Change |
|---|---:|---:|---:|
| Any hit @ 1 | 0.44 | 0.56 | +0.12 |
| Any hit @ 3 | 0.56 | 0.67 | +0.11 |
| Any hit @ 5 | 0.56 | 0.78 | +0.22 |
| MRR | 0.50 | 0.64 | +0.14 |
| NDCG @ 5 | 0.43 | 0.60 | +0.17 |
| Evidence coverage @ 3 | not measured in the old schema | 0.59 | now measured |
| Evidence coverage @ 5 | not measured in the old schema | 0.65 | now measured |

The final retrieval run completed 11/11 questions with zero retrieval failures. Its p50 total latency was 24,499 ms and p50 reranker latency was 21,648 ms on this Windows CPU-only environment. This is an observed local measurement, not a production SLA. The local generation run measured p50 total latency of 148,789 ms and p50 generation latency of 113,344 ms for the 10 calls that returned.

## Root-cause findings and changes

### 1. Query/lexical mismatch

**Evidence:** the prior diagnosis showed natural-language lexical queries could miss a source even when dense retrieval found it. The old path used one strict lexical query. 

**Change:** `src/portproject_rag/query_analysis.py` preserves the original question while producing a semantic query, salient terms, exact reference expressions, answer shape, and narrow domain classification. `retrieval.py` now executes layered web-search, exact-reference phrase, and salient-term lexical retrieval, with ACL predicates in every layer. Dense retrieval still receives the semantic query. No document/page/question identifier is hard-coded.

### 2. Candidate pool and reranker reliability

**Evidence:** a local candidate sweep showed pool 12 added coverage over pool 8 while pools 20 and 30 added no measured coverage. The previous fresh-process reranker could intermittently fail during model loading on Windows.

**Change:** `candidate_pool_size=12` is recorded in settings. The configured `rerank_candidate_count=8` is now honored; only that prefix is sent to the expensive reranker and the remaining candidates retain their fused hybrid score. The reranker is a process singleton protected by a lock, records a cooldown-bounded failure state, exposes redacted readiness state, and falls back to ACL-safe fused scores when degraded. Failure details never reach the user response.

### 3. Source hints and conservative metadata

**Change:** document-title/filename hints receive a small score adjustment. `source_metadata.py` derives only conservative filename metadata (family, type, date, clarification number, canonical source, equivalence group). It deliberately leaves `supersedes` unset; legal supersession is not inferred from filenames.

### 4. Multi-evidence and context assembly

**Change:** final context selection prefers document/page diversity, rejects duplicate pages, records excluded candidates, expands only ACL-permitted parent neighbors, and applies bounded budgets by answer shape (direct fact, list, comparison, and table). Diagnostics record candidate rows, selected/excluded rows, budget, token estimate, truncation, and reranker state. No unauthorized parent chunk can enter context through the compatibility helper.

### 5. Table-aware retrieval diagnosis

**Evidence:** the reviewed table question’s correct By-law page was present in the candidate pool but could be displaced by reranking; the source text contains OCR layout noise such as split unit words.

**Change:** table-shaped queries receive a general table signature boost when the candidate contains a normalized unit/time-band pattern. The normalization is generic (`met re` → `metre`) and has no document, page, or expected-answer identifier. The acceptance tests verify both positive and negative signatures.

The existing ingestion strategy still records `RAW_PAGE_CONTEXT` when structured table extraction is unavailable. This refactor does not silently claim that every OCR table has been converted to a trusted relational representation.

### 6. Grounded generation and citations

**Change:** `generation.py` sends an explicit evidence-only contract, preserves the model keep-alive setting, parses model timing telemetry, and validates citations against the supplied source IDs. One repair attempt may change citation syntax only; factual words must remain identical. If validation still fails, the user receives a safe citation-failure response and the evaluator records the failure. Empty evidence returns an explicit `NO_EVIDENCE` disposition.

The real local generation result demonstrates why this remains **PARTIAL**: 6/10 returned answers passed citation validation, 4 returned answers failed citation validation, and one question timed out. Citation presence is not treated as proof of factual faithfulness.

### 7. Routing and ambiguity

**Change:** `api.py` routes narrow billing, workflow, live-database, and tender-operation requests to their existing domain paths instead of sending them through document RAG. Ordinary policy/tender-document questions remain document RAG. Ambiguous property-specific lease-rate questions ask for an identifier rather than guessing.

### 8. Frontend context selector and typed errors

**Change:** the existing context selector is honestly labeled **All permitted documents** and its accessibility text explains its actual behavior; no fake document-scope filtering was added. API error handling now renders the safe typed message returned by the backend instead of `[object Object]` or an unconditional generic error. The backend exposes stage-aware codes and a request correlation ID without stack traces, SQL, paths, credentials, or tokens.

## Evaluation contract and diagnostics

`src/portproject_rag/evaluation.py` now distinguishes:

- transport success,
- retrieval success,
- candidate-stage evidence metrics,
- final-context evidence metrics,
- generation call success,
- citation validity,
- conservative no-answer markers,
- reranker degraded state,
- context truncation,
- model load/prompt/token timing.

Faithfulness, relevance, unsupported-claim rate, and final answer correctness are explicitly `not_automatically_scored`. The evaluator does not convert citation presence into an unsupported quality claim.

## Acceptance and regression evidence

The final guarded acceptance run after fixture reset reported:

```text
24 passed in 105.21s
```

The previously failing workflow test was rerun after reset and passed. The representative post-reset repeatability subset passed 4/4 (health/authentication, private-chat ownership, and RAG ACL query coverage). The final fixture check again reported `ACCEPTANCE FIXTURE READY` with `portproject_acceptance` and `acceptance/1`.

Acceptance readiness after the run reported `rag_ready=true`. The process-local reranker can honestly report `degraded` after a model-load failure; the RAG path remains available through the ACL-preserving fused-score fallback. This is an intentional reliability state, not a hidden PASS.

## Security and workflow preservation

- ACL predicates are applied to lexical, dense, metadata, and parent-context queries.
- No user-supplied principal or ownership parameter is used to bypass retrieval ACLs.
- Official workflow, billing, and tender authorization tests remained green in the guarded acceptance suite.
- No workflow lifecycle expansion, billing calculation change, tender persistence migration, or production deployment was performed as part of this refactor.
- The acceptance tender storage path remains outside the operational tender data directory.

## Browser E2E

No configured browser automation runner was found or executed in this phase. The API/database acceptance tests are the evidence for authentication, authorization, chat ownership, workflow, billing, tender, and RAG ACL behavior. A browser-authenticated E2E result is therefore **NOT AVAILABLE**, not PASS.

## Remaining blockers and recommended next controlled work

1. **Generation quality:** citation-valid rate was 6/10 in the real local run; one generation timed out. Review the failed answers against the source text before changing prompts or models.
2. **Local latency:** CPU-only BGE reranking and local 4B generation are slow. Any optimization should be measured separately and must preserve ACL ordering and the current fallback behavior.
3. **Table normalization:** OCR-heavy pages still rely on raw page context when a structured extractor does not produce a table. A future ingestion phase may add a schema-backed normalized representation, but it needs its own migration/reindex and quality contract.
4. **Faithfulness adjudication:** independent claim-level review is still required; this report intentionally provides no fabricated faithfulness score.
5. **Browser automation:** add/use a browser runner only if the project adopts one; do not claim browser E2E from API tests.

## Files changed for this refactor

- `src/portproject_rag/query_analysis.py`
- `src/portproject_rag/source_metadata.py`
- `src/portproject_rag/rag_errors.py`
- `src/portproject_rag/retrieval.py`
- `src/portproject_rag/generation.py`
- `src/portproject_rag/evaluation.py`
- `src/portproject_rag/settings.py`
- `src/portproject_rag/api.py`
- `web/src/main.tsx`
- `evaluation/rag_answer_contract_v2.json`
- `tests/test_rag_recovery.py`
- `tests/test_rag_answer_contract_v2.py`
- `tests/test_chat_payload.py`

Existing unrelated user changes in the working tree were preserved.

