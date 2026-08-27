# RAG generation, grounding, and citation recovery

Status: **PARTIAL — generator-owned complete-context cases pass; upstream
evidence gaps and human semantic review remain.**

## Scope and safety

This phase changed the generation/citation contract only. It preserved the
existing retrieval, ACL, workflow, billing, tender, and UI architecture.

* The normal-corpus evaluation used read-only queries against `portproject`.
  It confirmed the five reviewed gold documents were present. It made no
  database writes.
* Mutable regression work used `portproject_acceptance` only. Before that work,
  the fixture check confirmed `current_database=portproject_acceptance` and
  sentinel `acceptance/1`; its tender and billing paths remained under
  `tests/runtime`.
* The final acceptance reset/check passed. The temporary acceptance API
  returned `/health` = 200 with `database=portproject_acceptance` and
  `/health/ready` = 200 with `rag_ready=true`.
* No password, token, session cookie, or database URL is recorded here.

The acceptance fixture deliberately contains four synthetic ACL documents. It
does **not** contain the five documents used by the reviewed 11-question gold
set. An acceptance-only generation run therefore correctly returned
`NO_EVIDENCE` for the document questions; it is retained as a fixture-isolation
check, not presented as a quality result. The comparable before/after generation
measurement is the read-only normal-corpus run.

## Evidence artifacts

| Artifact | Purpose |
| --- | --- |
| `artifacts/evaluation/rag_recovery_after_full_final.json` | Historical post-retrieval baseline. Its raw prompts/model outputs were not retained. |
| `artifacts/evaluation/rag_generation_after_full.json` | First deterministic run after telemetry/parser changes, before final compact answer contracts. |
| `artifacts/evaluation/rag_generation_after_final.json` | Final deterministic, unchanged 11-question evaluation. Includes prompt, raw output, source IDs, counts, stop reason, and diagnostics per generated case. |
| `artifacts/evaluation/rag_answer_human_review.json` | Review queue. Subjective fields remain `null`; no semantic judgment was fabricated. |
| `artifacts/evaluation/rag_generation_stability.json` | Two deterministic generator repeats for every final-context-complete case. |

## Historical failure diagnosis

The historical artifact showed ten returned model calls, six citation-valid
answers, four invalid returned answers, and one timeout. Its retrieval metadata
is sufficient to determine context coverage; it did not preserve the raw prompt
or raw model completion. Where raw text is unavailable, classification is marked
as limited rather than guessed.

| ID | Answer shape | Necessary evidence in historical final context? | Classification | Evidence-backed conclusion |
| --- | --- | --- | --- | --- |
| RG-001 | direct fact | Yes | `CORRECT_AND_VALID` | Valid cited direct answer. |
| RG-002 | direct fact | Yes | `CORRECT_AND_VALID` | Valid cited direct answer. |
| RG-003 | list | No | `MISSING_REQUIRED_CONTEXT` | Required tender pages 12, 36, and 37 were absent; generator tuning cannot supply them. |
| RG-004 | list / multi-page | No | `MISSING_REQUIRED_CONTEXT` | Page 18 was absent from the recorded final evidence; the old response also showed truncation symptoms. |
| RG-005 | multi-document | No | `MISSING_REQUIRED_CONTEXT` | Only part of the required PGLM evidence reached context. |
| RG-006 | comparison | Yes | `PARTIALLY_CORRECT_CONTENT` | Recorded response ended mid-answer; output budget/prompt shape was a generator concern. |
| RG-007 | clarification | Not applicable | application-precondition bypass | The old evaluator called retrieval directly although the API already requires a property/tenancy identifier. It is not a generation failure. |
| RG-008 | no evidence | Not applicable | `CORRECT_CONTENT_BAD_CITATION_FORMAT` | Qwen returned a safe no-evidence response, but the validator rejected it merely because irrelevant chunks existed. |
| RG-009 | live-data route | Not applicable | application-precondition bypass | The API routes tenant-account requests away from document RAG; the old evaluator bypassed that boundary. |
| RG-010 | clarification | No | `MISSING_REQUIRED_CONTEXT` plus citation-placement failure | Required clarification/PGLM pages were not both present. A terminal citation list did not support its earlier paragraphs. |
| RG-011 | table value | Yes | `GENERATION_TIMEOUT` | The old table answer attempted to reproduce a table and was cut off/timed out. |

This separates upstream gaps from generator defects. No retrieval redesign was
performed in this phase.

## Defects fixed

1. **Safe refusal rejected by citation validation.** A fixed, non-factual
   no-evidence sentence is now accepted even if retrieval supplied irrelevant
   chunks. The model marker `NO_EVIDENCE` is converted to that sentence.
2. **Harmless compact citation syntax was not parsed.** `[S1, S2]` and
   `[S1; S2]` are safely canonicalized to `[S1][S2]`. The code never creates an
   identifier and the usual unknown-ID validation still applies.
3. **Prompt structure made the question less prominent than long evidence.**
   Prompts now present `QUESTION`, an explicit answer contract, valid source
   IDs, and simple per-source `Document / Page / Evidence` blocks.
4. **Answer-shape contracts were too generic.** Direct fact, list, comparison,
   multi-document, clarification, and table contracts are explicit. Comparison
   answers are two cited bullets rather than an unrestricted Markdown table;
   table-value answers are one value/unit/condition/source bullet.
5. **Output telemetry was missing.** Generation now records raw answer,
   prompt, prompt/evaluation token counts, Ollama stop reason, and repair
   outcome. The evaluator records them without logging credentials.
6. **The evaluator measured requests the API would never generate.** It now
   honours existing live-data routing and identifier clarification before
   document retrieval, matching the application’s public behavior.
7. **Citation repair safety was not directly covered.** A repair is accepted
   only when citation-stripped factual text is byte-equivalent; a regression
   test proves changed facts are rejected.

## Final deterministic evaluation

`rag_generation_after_final.json` used the unchanged 11 reviewed questions,
the existing Qwen `qwen3.5:4b` model, and temperature `0`. The application
precondition handled RG-007 (clarification) and RG-009 (live-data route), so
nine cases requested document generation.

| Measure | Historical baseline | Final result |
| --- | ---: | ---: |
| Questions | 11 | 11 |
| Model calls returned | 10 | 9 / 9 requested |
| Generation timeouts | 1 | 0 |
| First-pass citation-valid | 6 / 10 (historical final-valid figure only) | 8 / 9 |
| Final citation-valid | 6 / 10 | 8 / 9 |
| Citation repair attempted / succeeded | not recorded | 1 / 0 |
| Correct no-evidence response | not measured correctly | 1 / 1 no-evidence case |
| Clarification precondition | evaluator bypassed it | 1 / 1 |
| Fully complete final-context cases | not separately repeated | 4 |
| Deterministic stable answers/citation sets | not measured | 4 / 4 across two repeats |

The sole final invalid generation was RG-010. It had incomplete required
evidence in final context, and the model placed a list of citations after
uncited factual paragraphs. The validator correctly rejected it; citation
repair did not alter factual text to force a pass.

The conservative automatic numeric-token check is a supplement only. It found
the expected numeric tokens in RG-001, RG-002, RG-005, and RG-006. It does not
declare semantic correctness and flags formatting differences such as `1.00`
versus `1` for human review.

## Generator-focused replay

Three cases whose final contexts were complete but previously failed on answer
shape were replayed after the compact contracts:

| Case | Result |
| --- | --- |
| RG-004 installment/delay list | Citation-valid concise bullets; `stop_reason=stop`. The source text supplied all but the second due-date wording, so the model explicitly withheld that unsupported detail. |
| RG-006 2018/2019 comparison | Citation-valid two-bullet comparison; `stop_reason=stop`. |
| RG-011 Appendix A table value | Citation-valid single value/unit/condition bullet; `stop_reason=stop`. |

## Latency and model decision

The final full evaluation recorded p50 generation **53.8s** and p50 end-to-end
**70.6s**. This is lower than the historic approximately 113s / 149s medians,
but latency remains a separate concern.

The stability artifact shows the first request for each retained context spent
roughly 68–98s in prompt evaluation; second requests reduced that component to
roughly 18–20s while retaining identical answers and citations. Model-load
telemetry was only about 0.5–1.3s on these requests. This supports that
`keep_alive=10m` and a warm Qwen process help, while prompt evaluation—not model
loading—is the dominant remaining cost. A true cold-start run was not claimed,
because the model was already warm from the full evaluation and forcibly
unloading a shared local model was unnecessary.

Qwen3.5:4b is therefore **acceptable for the evidence-complete answer shapes
tested here**. There is no evidence-based need to benchmark an alternative model
in this phase. That does not claim it solves retrieval gaps or human semantic
review.

## Regression evidence

| Gate | Result |
| --- | --- |
| Focused generation/recovery tests | 24 passed |
| Isolated Phase 08/09/10 acceptance suite | 24 passed |
| Full Python suite | 86 passed, 27 skipped (acceptance opt-in) |
| Ruff | passed |
| React production build | passed |
| Acceptance reset/check | passed, `acceptance/1` |
| Acceptance health/readiness | 200 / 200, `rag_ready=true` |

## Remaining limitations

* RG-003, RG-005, and RG-010 still lack all required evidence in final context;
  this must be addressed only by a future, separately evidenced retrieval/data
  phase.
* All generation answers require the created human review artifact for claims
  of factual correctness, completeness, faithfulness, and citation support.
* The normal-corpus gold set cannot be used as an acceptance-only generation
  benchmark until a synthetic, reviewed equivalent is added to the acceptance
  fixture. No operational documents were copied into the acceptance database.
* Latency remains high, especially first prompt evaluation. It is documented,
  not optimized in this correctness phase.

## Files changed

* `src/portproject_rag/generation.py`
* `src/portproject_rag/guardrails.py`
* `src/portproject_rag/query_analysis.py`
* `src/portproject_rag/evaluation.py`
* `src/portproject_rag/cli.py`
* `src/portproject_rag/settings.py`
* `tests/test_rag_generation_recovery.py`
* `tests/test_guardrails.py`

No workflow, billing, tender, database migration, ACL, or frontend behavior was
changed.
