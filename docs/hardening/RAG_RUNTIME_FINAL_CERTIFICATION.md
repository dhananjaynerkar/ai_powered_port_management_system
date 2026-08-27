# Final RAG runtime certification

**Review date:** 2026-08-27  
**Scope:** normal-corpus RAG runtime, limited concurrency, ACL context boundary,
and current-source-of-truth documentation.  No retrieval redesign, model
replacement, re-embedding, quantization change, billing change, tender change,
or frontend redesign was performed.

## Executive result

| Gate | Result |
| --- | --- |
| RAG quality frozen | **YES** — the frozen quality artifacts remain unchanged and the final replay is 9/9 citation-valid with zero timeouts. |
| Mixed-shape runtime | **PARTIAL** — nine one-pass, read-only observations completed; the CPU host does not support a statistically strong p95 per shape and two broader multi-shape attempts terminated at the native process level. |
| Two-request concurrency | **PASS** for the bounded pipeline probe: two simultaneous direct-fact requests completed in one process, with valid citations and no crash. This is not an HTTP capacity certification. |
| ACL neighbour/parent boundary | **PASS** for the implemented retrieval paths; acceptance regression excludes restricted adjacent and parent/context rows. |
| Documentation reconciliation | **YES** for current RAG/security/architecture/diagram/interview documents; historical phase records remain labelled evidence snapshots. |
| RAG subsystem freeze | **NO** — quality and ACL gates pass, but the runtime/capacity gate is not strong enough to freeze a CPU-bound local deployment. |

The measured system is not a generic “19-second chatbot.” The 19.114-second
number is a certified warm RG-001 direct-fact p50 only. Multi-evidence requests
remain materially slower on this host.

## Frozen quality baseline

These values are sourced from `docs/hardening/RAG_FINAL_CONTEXT_CERTIFICATION.md`
and its persisted evaluation artifacts; they were not recomputed from generated
text in this runtime phase:

| Measure | Frozen result |
| --- | ---: |
| AnyHit@1 | 0.67 |
| AnyHit@3 | 0.89 |
| AnyHit@5 | 0.89 |
| EvidenceCoverage@5 | 0.85 |
| FactCoverage | 1.00 (10/10 reviewed mapped facts) |
| CompleteFactEvidenceRate | 1.00 (3/3 mapped cases) |
| Frozen generation citation validity | 9/9 |
| Frozen generation timeouts | 0 |
| RG-003 / RG-005 / RG-010 | Fact complete |

The shape-context generation artifact contains nine returned, citation-valid
records and zero timeouts. The performance sample records answer hashes only;
it does not replace the reviewed quality artifact or claim semantic correctness
from citation presence alone.

## Process topology and safety boundary

The normal runtime was started without reload. At the final topology check:

- exactly one process owned the normal API listener on `127.0.0.1:8001`; its
  command was `python -m portproject_rag.server`;
- the parent process was the launcher and the child was the single listening
  application worker;
- no acceptance listener remained on port 8016;
- no second project API worker or reload process was used during the final
  profiling runs;
- the CrossEncoder is process-local (`retrieval.py` `_RERANKERS` cache), so the
  single normal worker owns one cache instance;
- Ollama was one local service on `127.0.0.1:11434`.

Acceptance mutations were run only after the existing environment loader and
fixture guard reported `database=portproject_acceptance` and `sentinel=acceptance/1`.
The acceptance API and listener were stopped after the reset/check. The normal
performance profiler and concurrency probe refuse any database other than
`portproject` and issue read-only retrieval calls; no normal-corpus query API
was used for profiling because that endpoint persists chat records.

## Memory baseline and resource profile

Observed host: 15.65 GiB physical RAM. No Windows page-file setting was
changed.

| Observation | Evidence |
| --- | ---: |
| Physical RAM before unloading local models | 15.65 GiB total; 2.83 GiB available (pre-profile observation) |
| Physical RAM after unloading local models | 7.73 GiB available |
| Normal API worker RSS at final health check | 142.7 MiB (no RAG request in that worker) |
| Peak profiler/concurrency-process RSS | 2,391,429,120 bytes (~2.23 GiB), sampled 1,122 times |
| Minimum available physical RAM during two-request probe | 1,149,124,608 bytes (~1.07 GiB) |
| Page file at final check | 3,887 MiB current; 6,303 MiB reported peak |
| Ollama Qwen allocation observable through `/api/ps` | 3,208,915,187 bytes (~3.21 GB), Q4_K_M |
| Ollama BGE allocation observable through `/api/ps` | 1,218,969,598 bytes (~1.22 GB) when loaded |

Ollama's process RSS is not a reliable model-memory measurement on this host
because the model allocations are observable separately through `/api/ps`.
The 1.07 GiB minimum available RAM and earlier native process terminations are
resource evidence, not a quality or authorization result.

## Warm-up protocol

For the explicit concurrency probe, a single RG-001 request warmed the
embedding service, CrossEncoder, and Qwen before the barrier released the two
measured requests. Warm-up was excluded from the concurrency wall time. For
the shape sample, isolated runs were stopped between selected cold processes;
the six-record mixed sample loaded models on RG-001 and then measured later
records warm in that same process. The artifact fields expose model/reranker
load time so cold and warm observations are not silently combined.

## Per-shape runtime observations

All records below are read-only normal-corpus profiles at `generation_temperature=0`
using `bge-m3`, `BAAI/bge-reranker-v2-m3`, and `qwen3.5:4b`. Values are full
retrieval-plus-generation wall time. A one-record p50/p95 is deliberately
shown as `n=1`, not as a statistically meaningful distribution.

| Shape / records | Warm observations (p50; p95; max) | Representative stages |
| --- | --- | --- |
| DIRECT_FACT (`RG-001` runs 2–4, `RG-002` warm in mixed sample; n=4) | 19.742 s; 37.974 s; 41.081 s | RG-001 retained three-run certified p50 is 19.114 s; direct warm retrieval includes ~10.177–13.453 s rerank and generation varies with host load. |
| TABLE (`RG-011`; n=1) | 49.475 s; 49.475 s; 49.475 s | 13.585 s rerank; 27.166 s prompt evaluation; 34.064 s generation. |
| LIST (`RG-003`; n=1 warm in mixed sample) | 110.457 s; 110.457 s; 110.457 s | 12.184 s rerank; 70.473 s prompt evaluation; 95.536 s generation; 1,787 prompt tokens. |
| COMPARISON (`RG-005`; n=1 warm in mixed sample) | 154.275 s; 154.275 s; 154.275 s | 13.439 s rerank; 100.977 s prompt evaluation; 137.900 s generation; 2,570 prompt tokens. |
| CLARIFICATION-shaped document case (`RG-010`; n=1 warm in mixed sample) | 121.597 s; 121.597 s; 121.597 s | 12.966 s rerank; 93.278 s prompt evaluation; 104.792 s generation. |
| NO_EVIDENCE (`RG-008`; n=1 isolated) | 67.540 s; 67.540 s; 67.540 s | Retrieval returned one semantically non-supporting chunk, so the model was called and returned disposition `NO_EVIDENCE`; this is not the zero-evidence short-circuit. |

The explicitly measured complex cases are RG-003, RG-005, RG-006, and RG-010.
RG-006's isolated one-pass result was 180.779 s (34.089 s rerank,
97.313 s prompt evaluation, 140.238 s generation). It did not receive a
second warm full-request observation, so no invented warm p95 is reported for
that case.

The retained direct-fact comparison remains:

| RG-001 warm repeat set | Baseline | Retained configuration |
| --- | ---: | ---: |
| End-to-end p50 | 32.927 s | 19.114 s |
| Prompt evaluation p50 | 17.280 s | 0.196 s |
| Generation p50 | 22.489 s | 6.488 s |
| Prompt evaluated tokens | 1,251 | 464 |

The retained rule is limited to contract-safe direct/table context counts; the
four-source multi-evidence policy remains intact.

## Mixed-set latency

The transparent mixed set contains **nine observations**: RG-001, RG-002,
RG-003, RG-004, RG-005, RG-006, RG-008, RG-010, and RG-011. It includes direct,
list, comparison, clarification-shaped, table, and no-evidence cases; no slow
valid complex case was removed.

| Mixed set (one transparent nine-observation operational sample) | Result |
| --- | ---: |
| Observed mixed-condition p50 | 110.457 s |
| Observed mixed-condition p95 (inclusive sample quantile) | 171.038 s |
| Maximum | 180.779 s (`RG-006`, isolated process) |
| Citation-valid observations | 9/9 |
| Timeouts | 0 |

The set mixes one process-cold RG-001 record, warm later records, and isolated
shape runs. It is therefore a transparent operational sample, not a controlled
all-warm capacity distribution. The quantile is reported because the prompt
requires it, with the mixed conditions and sample count disclosed; an all-warm
mixed p50/p95 remains **not certified**.

## Cold latency

Cold/isolated full-request observations were: RG-001 78.401 s (probe), RG-004
156.427 s, RG-006 180.779 s, and RG-008 67.540 s. The observed cold range is
67.540–180.779 s; the slowest cold record is RG-006. Model and reranker load
times are present in each artifact and are not folded into a false warm claim.

## Two-request concurrency

`scripts/rag_concurrency_profile.py` runs two selected contract questions in
one Python process. It uses a barrier, two worker threads, and no API endpoint
or chat write. The measured pair was RG-001 + RG-002 after an RG-001 warm-up:

| Request | Result | Retrieval | Generation | Total | Citation |
| --- | --- | ---: | ---: | ---: | --- |
| RG-001 | success / `ANSWER` | 22.440 s | 8.434 s | 31.018 s | valid |
| RG-002 | success / `ANSWER` | 22.565 s | 33.887 s | 56.601 s | valid |
| Pair wall time | — | — | — | 56.600 s | both completed |

There was one process, no second CrossEncoder initialization, no access
violation, no `OSError 1455`, no model reload storm, no request-context or
source mixing, and no chat/ACL path. The probe is a pipeline-level concurrency
check, not an HTTP worker-pool or multi-user capacity guarantee.

## Queue/semaphore decision

No inference semaphore or queue was introduced. The exact two-request probe
completed without a crash or failed request, so the evidence does not justify
changing request semantics or adding hidden queue time. `queue_wait_ms` is
**not applicable (no queue exists)**. The earlier broad multi-shape attempts
terminated without artifacts under native Windows resource pressure; this is a
reason to keep the deployment scope to a bounded local host, not a reason to
spawn another model process. A future pilot needs a bounded, observable,
timeout-aware inference gate measured on its target hardware.

## No-evidence and clarification behavior

The API short-circuits routed requests and missing-property clarification in
`src/portproject_rag/api.py` (`_answer_payload`): no retrieval or LLM call is
made, and the response has `llm_model=None`. The generator also short-circuits
when its evidence list is empty (`src/portproject_rag/generation.py`,
`generate_grounded_answer`).

RG-008 is different: retrieval returned one candidate, then Qwen emitted the
safe `NO_EVIDENCE` disposition. There is no proven, general pre-generation
threshold that can safely classify every semantically weak candidate without
changing retrieval/quality semantics, so no new heuristic was added.

## ACL neighbour/parent proof

Source tracing shows the actual order:

1. lexical and dense candidate SQL applies `(cardinality(a.acl_roles)=0 OR
   %s=ANY(a.acl_roles))` before RRF and reranking (`retrieval.py` lines 266–274);
2. adjacent-page promotion repeats that predicate while joining `chunk_acl`
   (`retrieval.py` lines 354–422);
3. parent/context expansion repeats the public-or-current-role predicate before
   assembling `context_text` (`retrieval.py` lines 600–644);
4. citation validation checks the final returned source IDs in `generation.py`.

The acceptance regression
`test_mixed_acl_neighbours_are_excluded_from_parent_and_adjacent_context`
creates a temporary acceptance-only document with a public/tenant anchor and
authority-only neighbouring pages. For a tenant role, `_expand_context_with_metadata`
returns only the authorized anchor and `_adjacent_page_candidates` returns no
restricted neighbour. The test deletes the temporary rows and the fixture is
reset/check-verified afterward. No restricted neighbour enters final context,
the generation prompt, or citation metadata in this path.

## Documentation drift found and corrected

The audit found a real documentation conflict: `ARCHITECTURE.md`, `DIAGRAMS.md`,
`INTERVIEW_DEFENSE_GUIDE.md`, `RAG_SYSTEM.md`, and `SECURITY.md` described
neighbour expansion as lacking a second ACL predicate, while current code had
already added ACL-aware adjacent and parent/context SQL. The current documents
now describe the actual boundary and the acceptance evidence. The RAG diagram
shows analysis → lexical/dense retrieval → ACL → RRF → reranker → ACL-safe
context → Qwen → citation validation.

Volatile test counts were centralized toward the latest certificate in the
current testing/readiness/interview documents. Historical phase reports retain
their original observed counts and are not treated as current runtime claims.

## Quality and regression gates

| Gate | Result / evidence |
| --- | --- |
| Acceptance fixture safety | PASS — `portproject_acceptance`, sentinel `acceptance/1`, isolated tender path; reset/check passed before and after mutable tests. |
| Phase 08 acceptance | PASS — included authentication, session, authorization, chat ownership, RAG ACL, mixed-ACL, billing/tender authorization, error, and audit tests. |
| Phase 09 acceptance | PASS — complete guarded DO → NO → HO workflow tests. |
| Combined Phase 08 + 09 | PASS — 21 passed in 125.15 s on the clean retry. |
| Post-reset representative subset | PASS — 5 passed in 44.60 s. |
| Full Python suite | PASS — 96 passed, 28 skipped (acceptance opt-in when not loaded). |
| Ruff | PASS — `ruff check src tests scripts`. |
| Frontend production build | PASS — TypeScript/Vite, 1,672 modules transformed. |
| Normal `/health` | PASS — HTTP 200, `database=portproject`, `schema=rag`. |
| Normal `/health/ready` | PASS — HTTP 200, `rag_ready=true`, 48 documents, 1,474 pages, 3,399 chunks/vectors, no init error. |
| Operational DB modified | **NO** — performance probes refused non-normal DB and issued read-only retrieval; acceptance mutations were isolated and guarded. |

The first acceptance retry failed because the acceptance API was forcibly
closed during a RAG request under host resource pressure; subsequent tests saw
connection refusals. That failure is retained as an environment finding, not
hidden. After unloading models and restarting a single acceptance API, the
same Phase 08/09 suite passed 21/21 and the fixture reset/check passed.

## Decisions and remaining limitations

- **Current model:** `qwen3.5:4b` Q4_K_M.
- **Quantization change:** NO — current Q4_K_M is already the configured
  baseline; no Q3/Q2 experiment was justified.
- **Embedding model changed:** NO (`bge-m3`, 1,024 dimensions).
- **Reranker changed:** NO (`BAAI/bge-reranker-v2-m3`, CPU).
- **Conditional reranker bypass:** NO — no calibrated quality evidence
  supports weakening complex-question reranking.
- **Inference queue:** NO for the tested two-request local scope; broader
  capacity is not certified.
- **Human semantic review:** still required for factual correctness,
  completeness, faithfulness, and citation support beyond the reviewed fact
  contract.
- **Browser authenticated E2E:** not part of this runtime phase and remains
  unavailable in the repository's configured tooling.
- **Tender production persistence:** remains a separate multi-process storage
  limitation.

## Reproducibility artifacts

- `artifacts/evaluation/rag_performance_baseline_rg001.json`
- `artifacts/evaluation/rag_performance_final_rg001.json`
- `artifacts/evaluation/rag_performance_probe.json`
- `artifacts/evaluation/rag_performance_mixed_sample.json`
- `artifacts/evaluation/rag_performance_rg004.json`
- `artifacts/evaluation/rag_performance_rg006.json`
- `artifacts/evaluation/rag_performance_rg008.json`
- `artifacts/evaluation/rag_performance_warm_shapes.json`
- `artifacts/evaluation/rag_concurrency_profile_memory.json`
- `artifacts/evaluation/rag_final_context_certified.json`
- `artifacts/evaluation/rag_final_context_generation_certified.json`
- `tests/acceptance/test_phase08_e2e.py`
- `scripts/rag_performance_profile.py`
- `scripts/rag_concurrency_profile.py`

The memory sampler uses the small `psutil` development dependency declared in
`pyproject.toml`; it is not imported by the application runtime.

## Required final summary

RAG RUNTIME FINAL CERTIFICATION
===============================

RAG quality frozen: YES  
AnyHit@5: 0.89  
EvidenceCoverage@5: 0.85  
FactCoverage: 1.00 (10/10)  
Citation-valid: 9/9; 0 timeouts  
Warm direct-fact p50: 19.114 s (RG-001 retained certified warm set, n=3)  
Warm table p50: 49.475 s (RG-011, n=1)  
Warm complex p50: 121.597 s across measured warm RG-003/RG-005/RG-010 sample (n=3; RG-006 has no warm repeat)  
Warm mixed p50: NOT CERTIFIED (observed mixed-condition p50 110.457 s; nine observations)  
Warm mixed p95: NOT CERTIFIED (observed mixed-condition p95 171.038 s; nine observations)  
Cold full-request latency: 67.540–180.779 s in isolated samples  
Two simultaneous requests: PASS  
Peak memory: ~2.23 GiB profiler RSS; ~1.07 GiB minimum available RAM during pair  
Inference queue required: NO for bounded two-request scope  
Current model: qwen3.5:4b Q4_K_M  
Quantization change: NO  
Embedding model changed: NO  
Reranker changed: NO  
Neighbour/parent ACL: PASS  
Documentation reconciled: YES  
Phase 08: PASS  
Phase 09: PASS  
Full Python: PASS (96 passed, 28 skipped)  
Ruff: PASS  
Frontend build: PASS  
Operational DB modified: NO  
RAG subsystem freeze: NO — runtime/capacity evidence remains host-bound and partial  
Primary remaining project blocker: bounded production capacity/resource plan for the local CPU RAG stack, followed by human semantic review and authenticated browser/accessibility evidence.

**Phase result: PARTIAL.** Quality and ACL behavior are certified and regression
gates are green, but the machine's low memory headroom and native failures in
broader multi-shape attempts prevent a full runtime/capacity freeze. No Phase 09
or later RAG tuning is started by this report.
