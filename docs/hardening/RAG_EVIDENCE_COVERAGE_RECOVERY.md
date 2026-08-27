# RAG evidence coverage recovery

## Result

**PARTIAL — the configured reranker is restored and the deterministic/live
retrieval checks pass, but two reviewed multi-page cases remain incomplete in
final context.** No database writes,
ACL changes, generation changes, workflow changes, billing changes, tender
changes, or frontend changes were made in this phase.

## Scope and safety

- The normal corpus was queried only through explicit read-only transactions.
  The active normal database name was verified as `portproject` before those
  probes.  No acceptance or operational records were inserted, updated, or
  deleted.
- The reviewed `rag_answer_contract_v2` was read without alteration.
- The repair contains no question IDs, document IDs, filenames, page numbers,
  expected answers, or source-specific runtime rules.
- Existing ACL predicates remain in lexical retrieval, dense retrieval,
  neighbour-page lookup, parent expansion, and final context construction.

## Baseline evidence and root cause

All eight required pages for RG-003, RG-005, and RG-010 have indexed chunks.
The historical retrieval artifact showed that the issue was not missing source
files or missing ingestion:

| Case | Required evidence | Observed first failure |
| --- | --- | --- |
| RG-003 | tender pages 12, 36, 37 | pages 12 and 36 reached candidates but were displaced before final context; page 37 did not enter the primary 12-item pool. |
| RG-005 | PGLM pages 3, 9, 10 | pages 3 and 10 reached candidates; page 9 did not reach the primary pool. |
| RG-010 | clarification page 9 and PGLM page 18 | both reached candidates, but the clarification evidence was displaced by document-only diversity. |

The diagnostic regression test reproduced the second failure mode without a
database: the former selector could choose an unrelated document instead of a
second, complementary page from the same document.

## Candidate-pool experiment

The current live corpus was queried read-only with the same three questions,
using the primary hybrid candidate limit below.  This is a retrieval-only,
no-generation measurement.

| Primary pool | Mean required-evidence coverage | Complete cases | Mean retrieval-stage latency |
| ---: | ---: | ---: | ---: |
| 12 | 0.778 | 1 of 3 | 3,582 ms |
| 16 | 0.778 | 1 of 3 | 3,715 ms |
| 20 | 0.778 | 1 of 3 | 3,743 ms |
| 24 | 0.778 | 1 of 3 | 3,829 ms |

Increasing the primary pool was therefore not a material recovery and was not
made the default.  The surviving first failures are semantic candidate recall
for evidence split by PDF pages and final context selection, not a simple
candidate-limit problem.

## Implemented repair

### Bounded, generic facet retrieval

`query_analysis.py` now derives two to four user-stated clauses only for
multi-evidence answer shapes (`list`, `comparison`, `multi_document`, and
`clarification`).  The queries are deterministic and syntax-driven; no LLM is
called and no domain fact is added.

`retrieval.py` sends the original query plus each bounded facet through the
same ACL-filtered lexical and dense retrieval paths.  Fusion retains every
rank contribution and records facet hits for diagnostics.  Conservative
surface-form expansion also lets a term such as `transferring` contribute a
`transfer` lexical alternative when PostgreSQL is using the intentionally
non-stemming `simple` text configuration.

### Coverage-aware selection

Final selection still preserves page uniqueness and document diversity for
direct questions.  For multi-evidence questions it now:

1. preserves candidates that cover distinct user-stated facets;
2. keeps connected pages from a selected or explicitly hinted source before
   filling the remaining slots with unrelated documents; and
3. can retain an immediate neighbouring page only when that page is attached
   to an already ACL-filtered retrieved anchor.

The neighbouring-page step is bounded to one page on each side of existing
hybrid candidates.  It does not scan a document, bypass the candidate ACL, or
increase final context beyond the configured source limit.

## Verification completed

| Check | Result |
| --- | --- |
| Required source-page chunks exist | PASS (read-only source probe) |
| Candidate-pool sweep (12/16/20/24) | PASS (measured; no material pool gain) |
| Deterministic selector red test before repair | PASS (failed as expected) |
| Focused retrieval/generation unit tests | PASS — 25 passed |
| Ruff for changed RAG files/tests | PASS |
| Full Python suite | PASS — 89 passed, 27 skipped |
| React production build | PASS |
| Acceptance fixture safety check | PASS — `portproject_acceptance`, sentinel `acceptance/1` |
| Post-change live cross-encoder rerank | NOT VERIFIED |
| Post-change full golden retrieval evaluation | NOT RUN — depends on rerank completion |
| Post-change generation/citation evaluation | NOT RUN — generation intentionally frozen until retrieval can be measured end-to-end |

## Remaining blocker and next safe action

## Reranker restoration and certification attempt

### Root cause and smallest fix

The exact configured model was already present as the Hugging Face snapshot
`953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` under the standard local cache.
It contains the model safetensors file, tokenizer files, and configuration;
the inspected snapshot size was 2.29 GB.  The application had loaded the model
by Hub identifier without passing SentenceTransformers' supported
`local_files_only` option.  That caused unnecessary Hub resolution despite the
complete local artifact.

`Settings.reranker_local_files_only` now defaults to `true`, and the sole
CrossEncoder construction site passes it explicitly.  This is scoped to the
reranker; it does not change embedding, generation, or global network mode.

The original access violation (`0xC0000005`) during real retrieval was also
reproduced.  Candidate retrieval completed first; the crash occurred when a
fresh CrossEncoder was inferred in a process while a separately running,
verified project API worker retained about 3.3 GB of private memory.  The
verified duplicate project worker was stopped before isolated diagnostics and
was not replaced with multiple workers.  The unrelated port-8000 application
was left running.

### Startup waterfall

| Stage | Result | Evidence |
| --- | --- | --- |
| Python / project virtual environment | PASS | Python 3.13.14; project `.venv` |
| Torch | PASS | 2.13.0 CPU build imported normally |
| SentenceTransformers / Transformers | PASS | 5.7.0 / 5.15.0 |
| Exact artifact | PASS | local BAAI snapshot at the revision above |
| Local-only CrossEncoder load | PASS | 3.18 s direct load |
| Direct cold score | PASS | numeric score 0.9861; 0.42 s inference |
| Direct warm score | PASS | numeric score 0.9861; 0.24 s inference |
| Real application cold rerank | PASS | numeric score; state `ready` |
| Same-process second/third rerank | PASS | singleton reused; ~0.24 s warm scores |
| Three clean process launches | PASS | all returned numeric score with `ready` state |
| Real document retrieval | PASS | `degraded=false`; live rerank completed |

The direct model process reached roughly 2.07 GB RSS after inference.  At the
time of diagnosis the machine had 16.8 GB visible physical memory, about 3.9
GB free physical memory, and a 16.37 GB page file with 3.90 GB current use.
No page-file setting was changed.  The observed problem was duplicate process
memory pressure plus unnecessary Hub resolution, not a proven dependency or
page-file incompatibility.

### Unchanged golden retrieval evaluation

The reviewed contract was run with generation disabled after the reranker fix.
The final measurement artifact is
`artifacts/evaluation/rag_evidence_coverage_certified_v2.json`.

| Metric | Pre-coverage baseline | Current reranked result |
| --- | ---: | ---: |
| AnyHit@1 | 0.56 | 0.67 |
| AnyHit@3 | 0.67 | 0.89 |
| AnyHit@5 | 0.78 | 0.89 |
| EvidenceCoverage@3 | 0.59 | 0.76 |
| EvidenceCoverage@5 | 0.65 | 0.81 |
| MRR | 0.64 | 0.78 |
| NDCG@5 | 0.60 | 0.75 |
| Rerank latency p50 / p95 | not recorded here | 10,226 / 15,474 ms |
| Total retrieval latency p50 / p95 | not recorded here | 11,617 / 17,472 ms |

The configured reranker was not degraded in any evaluated question.

### Required-case waterfall result

| Case | Candidate / rerank finding | Final context | First remaining failure |
| --- | --- | --- | --- |
| RG-003 | required pages 12 and 36 reranked; page 37 was recovered as an authorized neighbour of page 36 | pages 18, 12, 36, 82 | final selection used the fourth slot for another primary page rather than the recovered neighbour page 37 |
| RG-005 | pages 10 and 3 reranked; page 9 was recovered as an authorized neighbour of page 10 | pages 10, 3, 22, 11 | final selection used the remaining slots for other primary/adjacent pages before page 9 |
| RG-010 | clarification page 9 and PGLM page 18 both reranked | both required pages included | PASS |

This phase made one measured, general selector correction: source cohesion for
named/list evidence and document diversity for unhinted multi-document or
clarification evidence.  It raised EvidenceCoverage@5 from 0.76 in the first
post-reranker run to 0.81.  A further rule that privileges a particular page
direction or document sequence cannot be justified generically from the three
remaining facts, so no question/page-specific rule was added.

Frozen generation replay and the human-review queue update were intentionally
not run: the phase gate requires all three final contexts to be complete first.
The current evidence coverage result must therefore remain PARTIAL.

### Final regression and safety checks

- Focused reranker and recovery tests: PASS.
- Full Python suite: PASS — 90 passed, 27 skipped.
- Ruff: PASS.
- React production build: PASS.
- Guarded Phase 08/09 acceptance suite: PASS — 24 passed in 222.21 seconds.
- The acceptance fixture was reset and checked afterwards; it again reported
  `portproject_acceptance` and sentinel `acceptance/1`.
- The temporary acceptance API was stopped after verification.  The normal
  corpus was read only; no `portproject` write was performed.

## Files changed

- `src/portproject_rag/query_analysis.py`
- `src/portproject_rag/retrieval.py`
- `tests/test_rag_recovery.py`
- `docs/hardening/RAG_EVIDENCE_COVERAGE_RECOVERY.md`
