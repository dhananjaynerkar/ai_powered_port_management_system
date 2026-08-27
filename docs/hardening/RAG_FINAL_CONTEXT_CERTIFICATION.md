# RAG final context certification

## Result

**PASS — reviewed fact evidence is complete for RG-003, RG-005, and RG-010.**

This is a narrow final-context certification. It retains the configured
`bge-m3` embedding model, `BAAI/bge-reranker-v2-m3` reranker, four-source
context limit, Qwen model, answer-shape contracts, citation parser, ACL
boundaries, and page-level diagnostics. No corpus records, ACL rules, workflow
logic, billing logic, tender logic, or frontend behavior were changed.

## Safety and scope

- Normal-corpus inspection used read-only queries against `portproject`.
- Acceptance mutations used the existing guarded scripts only. Before and after
  the run, the fixture check reported `portproject_acceptance`, sentinel
  `acceptance/1`, and the isolated tender path under `tests/runtime`.
- The operational `portproject` database was not modified.
- The fact-evidence map is evaluation metadata in
  `evaluation/rag_fact_evidence_v1.json`; production retrieval never loads it.
- All neighbour, lexical, dense, rerank, parent-context, and final-context
  paths remain ACL-filtered.

## Baseline

The preceding evidence-coverage artifact reported the following page-based
baseline: AnyHit@1/3/5 = 0.67/0.89/0.89, EvidenceCoverage@3/5 = 0.76/0.81,
MRR = 0.78, NDCG@5 = 0.75, and 6 of 8 page-evidence cases complete. RG-003
and RG-005 were the remaining reported page-evidence gaps; RG-010 was already
complete.

## Exact corpus evidence and fact classification

### RG-003 — transfer or sub-leasing conditions

The selected final context contains Annexure pages 12 and 36. The originally
nominated page 37 is absent.

| Reviewed fact | Corpus evidence | Classification |
| --- | --- | --- |
| General bar on sub-leasing and special-purpose policy exception | Annexure p.12, chunk 30; p.36, chunk 113 | `EXACT_EXPECTED_PAGE_PRESENT` |
| Prior Board approval, transferee liabilities, remaining term, and Port land-use plan | Annexure p.12, chunks 30–32; p.36, chunks 113–115 | `EXACT_EXPECTED_PAGE_PRESENT` |
| Pro-rata upfront rental, 50% pro-rata fee, and operation-of-law administrative-charge exception | Annexure p.12, chunk 31; p.36, chunk 114 | `EXACT_EXPECTED_PAGE_PRESENT` |
| Prior Board approval and applicable transfer charges/fees for transfer or assignment | Annexure p.12, chunk 32; Annexure p.37, chunk 116 | `EQUIVALENT_AUTHORITATIVE_EVIDENCE_PRESENT` |

Page 37's provision is not merely similar: its transfer/assignment wording is
also present on page 12. Therefore RG-003 is **FACT COMPLETE**, while the
original page-identity check correctly remains false. This is an evaluator
page-equivalence issue, not a reason to add a page-specific runtime rule.

### RG-005 — PGLM approval threshold and path

| Reviewed fact | Corpus evidence | Classification |
| --- | --- | --- |
| Statutory 30-year threshold and Central Government approval beyond 30 years | PGLM p.3, chunk 4 | `EXACT_EXPECTED_PAGE_PRESENT` |
| Board approval for a maximum cumulative 30-year lease | PGLM p.9, chunk 18 | `FACT_MISSING` before the selector correction; `EXACT_EXPECTED_PAGE_PRESENT` after it |
| Board recommendation and Empowered Committee/Government path up to 99 years | PGLM p.9, chunk 18 plus p.10, chunk 19 | `FACT_MISSING` before the selector correction; `EXACT_EXPECTED_PAGE_PRESENT` after it |
| Capital-intensive proposals over 30 years follow Board recommendation and Empowered Committee/Ministry approval | PGLM p.10, chunks 19–20 | `EXACT_EXPECTED_PAGE_PRESENT` |

PGLM page 10 begins mid-sentence (“the said land ...”) from the provision that
starts on page 9. Page 3 provides the statutory background but not the distinct
Board-approved cumulative-30-year condition. Pages 11 and 22 did not provide
that missing fact. RG-005 was a genuine final-selection omission, not an
evaluator-equivalence issue.

### RG-010

The final context contains Clarification No. 1 of 2018 p.9 and PGLM p.18.
Both reviewed facts are supported: the later clarification's fresh-lease/
renewal-period authority rule and the corresponding PGLM clarification text.
RG-010 remains **FACT COMPLETE**.

## Fact-level evaluation metadata

`evaluation/rag_fact_evidence_v1.json` maps the three reviewed cases to ten
atomic reviewed facts and conservative acceptable evidence sets:

- RG-003: four transfer/sub-lease facts;
- RG-005: four threshold/approval-path facts; and
- RG-010: two clarification facts.

An evidence set may contain more than one page only when the corpus text proves
the fact spans those pages. A different document or an entire document family
is never treated as equivalent merely by filename. `FACT_COVERAGE` is therefore
separate from the existing filename-plus-page `EvidenceCoverage@K` metric.

The certification retrieval artifact measured **10/10 supported facts**,
`FACT_COVERAGE = 1.00`, and `COMPLETE_FACT_EVIDENCE_RATE = 1.00` across these
three mapped cases.

## Selection correction

The retained correction is generic and deterministic:

1. Immediate neighbours remain bounded to ACL-authorized pages at ±1 from an
   already retrieved anchor.
2. For multi-evidence shapes only, a neighbour is preferred before redundant
   source filling only when the selected anchor begins mid-sentence and the
   neighbour is its same-document structural predecessor.
3. It does not use question IDs, document IDs, filenames, page numbers, gold
   facts, expected answers, an LLM, or a fixed page direction rule.

This placed PGLM p.9 alongside the selected p.10/p.3 context for RG-005. Direct
fact and table selection paths retain their existing diversity behavior.

## Source-limit and selection experiment

The experiment used one identical ACL-filtered, hybrid/reranked candidate set
per eligible question and varied only final selection/context assembly. The
embedding model, reranker, candidate pool, and generation were fixed.

| Strategy | Limit | EvidenceCoverage@5 | FactCoverage | Complete page evidence | Complete fact evidence | Context characters p50 | Retrieval/context p50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Current | 4 | 0.916667 | 0.80 | 0.75 | 0.666667 | 5,600 | 10,559 ms |
| Current | 5 | 0.958333 | 1.00 | 0.875 | 1.00 | 5,600 | 10,573 ms |
| Current | 6 | 0.958333 | 1.00 | 0.875 | 1.00 | 5,600 | 10,683 ms |
| Improved structural continuation | 4 | 0.958333 | 1.00 | 0.875 | 1.00 | 5,600 | 10,562 ms |
| Improved structural continuation | 5 | 0.958333 | 1.00 | 0.875 | 1.00 | 5,600 | 10,559 ms |
| Improved structural continuation | 6 | 0.958333 | 1.00 | 0.875 | 1.00 | 5,600 | 10,682 ms |

The retained option is **improved structural continuation at limit 4**. It
achieves the fact-complete result without globally adding a fifth or sixth
source. Limits 5 and 6 were rejected as unnecessary additional context.

## Final retrieval certification

The live retrieval-only certification artifact is
`artifacts/evaluation/rag_final_context_certified.json`.

| Measure | Previous certified baseline | Final certification |
| --- | ---: | ---: |
| AnyHit@1 | 0.67 | 0.67 |
| AnyHit@3 | 0.89 | 0.89 |
| AnyHit@5 | 0.89 | 0.89 |
| EvidenceCoverage@3 | 0.76 | 0.74 |
| EvidenceCoverage@5 | 0.81 | 0.85 |
| MRR | 0.78 | 0.78 |
| NDCG@5 | 0.75 | 0.78 |
| Complete page evidence | 6/8 (0.75) | 7/8 (0.875) |
| FactCoverage (mapped cases) | not previously measured | 1.00 (10/10) |
| CompleteFactEvidenceRate (mapped cases) | not previously measured | 1.00 (3/3) |
| Context tokens p50 | not previously recorded | 1,400 |
| Retrieval/context latency p50 | 11,617 ms | 9,142 ms |

The lower EvidenceCoverage@3 is retained as an honest page-ranking diagnostic;
it does not change the fact-complete determination, and AnyHit/MRR are
unchanged. RG-011 remains page-evidence complete in both the experiment and the
final certification. The no-evidence and property-clarification routing paths
were unchanged.

## Frozen generation replay

The combined retrieval-plus-generation process aborted twice before producing
an artifact under concurrent local model memory pressure. The normal API worker
and acceptance API cannot safely load separate reranker instances on this
machine at the same time. This is a local process-resource finding, not a model
or corpus change.

After isolating the process, a generator-only replay used the exact persisted,
ACL-filtered final contexts from the retrieval certification artifact. It kept
`qwen3.5:4b`, temperature `0`, answer-shape contracts, citation parser, and
citation repair unchanged. It checkpointed every generated record.

| Measure | Previous generation recovery | Frozen final-context replay |
| --- | ---: | ---: |
| Requested document-generation calls | 9 | 9 |
| Returned calls | 9 | 9 |
| Generation timeouts | 0 | 0 |
| First-pass citation-valid | 8/9 | 9/9 |
| Final citation-valid | 8/9 | 9/9 |
| RG-003 citation-valid | no complete-context replay | yes |
| RG-005 citation-valid | no complete-context replay | yes |
| RG-010 citation-valid | no complete-context replay | yes |
| Generation latency p50 | 53.8 s | 46.3 s |

The artifact is
`artifacts/evaluation/rag_final_context_generation_certified.json`. Its
corresponding 11-record human-review queue is
`artifacts/evaluation/rag_answer_human_review.json`. Subjective fields remain
`null`; citation validity is not presented as fabricated factual-correctness,
faithfulness, or completeness scoring.

## Regression and security

| Gate | Result |
| --- | --- |
| Focused fact/selector tests | PASS — 21 passed |
| Full Python suite | PASS — 92 passed, 27 skipped acceptance opt-in tests |
| Ruff | PASS |
| Frontend production build | PASS |
| Phase 08 authentication/authorization/RAG ACL acceptance | PASS in isolated run |
| Phase 09 workflow acceptance | PASS in isolated run |
| Combined Phase 08 + 09 acceptance suite | PASS — 20 passed in 163.52 s |
| Acceptance reset/check after tests | PASS — `acceptance/1` |
| Normal API after restoration | PASS — `/health/ready` 200 with 48-document normal corpus |

The first combined acceptance attempt failed after the temporary acceptance API
was run alongside the normal API and both attempted to load the local reranker.
The fixture remained isolated, the run was reset, and the isolated repeat
passed. No authorization, ownership, workflow, or ACL assertion failed.

## Files changed in this phase

- `src/portproject_rag/retrieval.py`
- `src/portproject_rag/evaluation.py`
- `evaluation/rag_fact_evidence_v1.json`
- `tests/test_rag_recovery.py`
- `tests/test_rag_evaluation.py`
- `docs/hardening/RAG_FINAL_CONTEXT_CERTIFICATION.md`

## Remaining limitations

- Fact coverage is explicitly scoped to the three mapped reviewed cases; it
  must not be extrapolated to every corpus question without additional reviewed
  fact/evidence mappings.
- Page-level and fact-level metrics intentionally differ for RG-003; both are
  preserved for auditability.
- Human review is still required for factual correctness, completeness,
  faithfulness, and citation support claims.
- Concurrent local API processes that each load the CPU reranker are a known
  resource constraint. This phase documents it but does not begin performance
  optimization.

## Final decision

**EVIDENCE COVERAGE RECOVERY = PASS.** RAG quality is frozen at this certified
state. The next work, if authorized, should be performance optimization without
quality regression.
