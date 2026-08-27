# RAG capacity, resource governance, and deployment envelope

**Phase:** Local RAG Capacity, Resource Governance & Deployment Envelope  
**Scope:** bounded local CPU operation only. RAG quality, retrieval semantics,
models, quantization, billing, tender behavior, and workflow lifecycle were
not redesigned.

## Final result

| Gate | Result | Evidence |
| --- | --- | --- |
| Local RAG capacity | **PARTIAL** | One active heavy pipeline with one bounded waiter is implemented and both serialized direct requests completed, but minimum free RAM remained below a conservative 1 GiB safety margin. |
| Controlled internal pilot | **NOT VERIFIED** | The 15.65 GiB host is not a safe multi-user pilot target; the required browser, deployment-owner, recovery, and hardware evidence is absent. |
| RAG subsystem freeze | **YES** | No model, embedding, reranker, retrieval, quantization, or grounding changes were made; the frozen quality/ACL gates remained green. Capacity certification is reported separately as PARTIAL. |

The retained policy is deliberately narrow: one FastAPI/Uvicorn worker, one
active heavy RAG pipeline, and one bounded waiter with a 60-second queue wait.
A full or expired queue returns HTTP 503 with a safe capacity message. This is
a local-demo guardrail, not a claim that the laptop supports two concurrent
users.

## Required final summary

Current host RAM: **15.65 GiB physical**  
Current CPU: **11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz (4 cores,
8 logical processors)**  
GPU: **Intel Iris Xe integrated graphics; no `nvidia-smi`/CUDA GPU detected**  
Generation model: **qwen3.5:4b Q4_K_M**  
Embedding: **bge-m3**  
Reranker: **BAAI/bge-reranker-v2-m3**  
Recommended FastAPI workers: **1**  
Heavy inference concurrency: **1 active pipeline**  
Queue enabled: **YES**  
Queue capacity: **1 waiting request**  

Direct + direct: **SERIALIZE**  
Direct + complex: **UNSUPPORTED for parallel execution; not attempted after the direct/direct safety stop**  
Complex + complex: **UNSUPPORTED for parallel execution; not attempted after the direct/direct safety stop**  

Minimum observed free RAM: **412,794,880 bytes (~0.384 GiB) in the fresh
unbounded direct/direct baseline; 653,705,216 bytes (~0.609 GiB) in the
serialized gate experiment**  
Peak process memory: **2,261,032,960 bytes (~2.11 GiB) in the fresh
unbounded baseline; 2,300,674,048 bytes (~2.14 GiB) in the serialized gate
experiment**  
Sequential soak: **PARTIAL**  
Memory leak: **NOT PROVEN**  
Cancellation slot release: **PASS for exception/queue-timeout paths; real
browser disconnect cancellation was not observable in the synchronous API**  
FactCoverage: **1.00 (10/10 mapped reviewed facts)**  
Citation-valid: **9/9**  
Phase 08: **PASS (21-test acceptance run included Phase 08)**  
Phase 09: **PASS (21-test acceptance run included Phase 09)**  
Full Python: **PASS (102 passed, 28 skipped)**  
Ruff: **PASS**  
Frontend: **PASS**  
Operational DB modified: **NO**  

LOCAL DEMO CAPACITY: **PARTIAL / CONDITIONAL**  
CONTROLLED INTERNAL PILOT CAPACITY: **NOT VERIFIED**  
RAG subsystem freeze: **YES**  
Recommended next hardware/runtime action: **Keep the one-worker/one-active-
pipeline gate for local demonstrations; re-benchmark on a machine with at
least 32 GiB physical RAM and measured ≥4 GiB free headroom under the target
workload before an internal pilot. A dedicated GPU may materially reduce CPU
latency for Qwen and CrossEncoder, but no GPU migration is implemented or
claimed.**

## 1. Existing quality baseline

The quality gates were treated as frozen inputs, not optimization targets:

| Measure | Frozen value |
| --- | ---: |
| AnyHit@1 / @3 / @5 | 0.67 / 0.89 / 0.89 |
| EvidenceCoverage@5 | 0.85 |
| FactCoverage | 1.00 (10/10 mapped reviewed facts) |
| CompleteFactEvidenceRate | 1.00 (3/3) |
| Citation-valid generation | 9/9 |
| Generation timeouts in the frozen replay | 0 |
| Neighbour/parent ACL | PASS |

No embedding, reranker, generation model, quantization, retrieval limit, or
context-quality rule was changed in this phase.

## 2. Hardware

The verified host is an HP Laptop 14s-dq2xxx with 15.65 GiB physical RAM and
an Intel Iris Xe integrated adapter. `nvidia-smi` is unavailable and no CUDA
GPU was detected. The local Ollama service is version 0.31.1. The measured
model allocations are approximately 3.21 GB for Qwen Q4_K_M and 1.22 GB for
the F16 BGE embedding model; prior diagnostics observed approximately 2 GB of
CrossEncoder process/model footprint.

## 3. Process topology

`src/portproject_rag/server.py` now passes `workers=1` explicitly, and the
acceptance launcher passes `--workers 1`. The normal launcher also limits
OpenMP/MKL threads to one and disables tokenizer parallelism. The process-local
CrossEncoder cache and heavy-RAG gate are therefore not duplicated by worker
processes.

The normal API uses port 8001 and the isolated acceptance API uses port 8016.
The launchers refuse to start one while the other is healthy. A separate
legacy API was observed on port 8000 during measurement; it was not modified
or used as this project's runtime.

## 4. Memory model

Ollama model memory is not represented faithfully by the small Ollama server
RSS. The capacity artifacts sample both the Python probe RSS and host virtual
memory. The unbounded direct/direct baseline reached 0.384 GiB free RAM; the
serialized experiment reached 0.609 GiB free RAM and peak pagefile use of
4,394,409,984 bytes (~4.09 GiB). A clean unloaded-model state measured about
7.3 GiB available RAM before a retry. The shortfall and prior native Windows
failures make a 1 GiB free-RAM margin a conservative operational warning, not
a fabricated SLA.

## 5. Direct/direct result

The fresh read-only baseline (`artifacts/evaluation/rag_capacity_baseline_direct_direct.json`)
released two direct-fact requests concurrently in one Python process. Both
completed with valid citations in 66.272 seconds of measured pair wall time.
Peak probe RSS was 2,261,032,960 bytes and minimum available RAM was
412,794,880 bytes. This is functionally successful but resource-unsafe for the
retained local envelope, so it is classified **SERIALIZE**, not SUPPORTED.

## 6. Direct/complex result

Not run in parallel. The direct/direct baseline already crossed the safety
stop with less than 0.4 GiB available RAM, and the preceding runtime phase
recorded broader multi-shape native-process failures. Continuing to a
direct/complex test would knowingly repeat an unsafe host condition. No
direct/complex support claim is made.

## 7. Complex/complex result

Not run in parallel for the same safety reason. The phase explicitly forbids
testing higher-risk classes after an unsafe preceding class. No
complex/complex support claim is made.

## 8. Queue/semaphore experiment

`scripts/rag_capacity_profile.py` ran RG-001 and RG-002 from the reviewed
contract in one process with a gate limit of one, queue capacity one, and a
300-second experiment-only wait. The retained service setting is 60 seconds;
the longer experiment wait allowed the serialized pair to complete so that
resource and citation behavior could be measured.

Artifact: `artifacts/evaluation/rag_capacity_serialized_direct_pair.json`.
Both requests completed with valid citations. Pair wall time was 81.684
seconds. Because the barrier releases both threads together, scheduler order
was not fixed: one request waited 49.829 seconds and the other acquired
immediately. Peak probe RSS was 2,300,674,048 bytes, minimum free RAM was
653,705,216 bytes, and peak sampled pagefile use was 4,394,409,984 bytes. The
gate ended with active=0 and queued=0, proving release and no residual queue.

An explicit gate-limit-two rerun was not performed after the fresh unbounded
two-thread baseline already demonstrated the effective two-pipeline condition
and crossed the safety stop. This avoids repeating a known resource-risky
experiment; no two-active-pipeline support claim is made.

The API unit tests also prove full-queue rejection, queue timeout cleanup,
safe 503 mapping, success telemetry, and release when retrieval raises.

## 9. Retained concurrency policy

The default settings are:

```text
HEAVY_RAG_CONCURRENCY=1
HEAVY_RAG_QUEUE_CAPACITY=1
HEAVY_RAG_QUEUE_TIMEOUT_SECONDS=60
```

The gate surrounds retrieval, reranking, and generation, but not dashboard,
tenant, authentication, billing, or tender routes. The limit is process-local
and deliberately bounded. The API returns no host memory, model internals, or
database details to users.

## 10. Timeout policy

Queue wait and model inference are separate settings. The queue wait is 60
seconds. The existing Ollama HTTP client generation timeout is 180 seconds.
There is no arbitrary server-wide 30-second deadline; complex reviewed
questions have measured generation times above two minutes. Clients should
allow queue wait plus retrieval and generation time. A full/expired queue is a
capacity response, not a generic retrieval failure.

## 11. Keep-alive decision

The configured Ollama `keep_alive` remains `10m`. `/api/ps` showed both model
entries with expiry timestamps approximately ten minutes after their most
recent request. This preserves warm latency during an active local session
without keeping models resident forever. An explicit local `keep_alive=0`
request unloaded Qwen and BGE and increased available RAM from roughly 3.1 GiB
to roughly 7.3 GiB before a cold retry. Models are not unloaded between normal
active requests; explicit reclamation is reserved for idle environment
switches or controlled cold measurements.

## 12. Sequential soak

The required 10–20-request soak was not run because the host crossed the
resource stop during the two-request baseline. Existing reviewed sequential
artifacts cover six warm shape requests (RG-001, RG-005, RG-011 repeated) and
the current serialized pair adds two more complete requests. This is useful
evidence of repeatability but not a 10–20-request capacity certification; a
full soak remains **PARTIAL**.

## 13. Memory stability

No sustained request-after-request growth conclusion is possible from the
bounded samples. Model caching and the CrossEncoder cache are expected warm
state, not a leak. The correct classification is **memory leak: NOT PROVEN**.

## 14. Failure containment

The API persists chat or official agenda messages only after retrieval and
generation return a validated payload. Capacity rejection, retrieval errors,
generation timeouts, and citation failures therefore cannot persist a
successful assistant result. The gate releases in a `finally` block. The
initial acceptance run that lost its connection during host pressure was
followed by a guarded fixture reset/check; no partial workflow or chat success
was observed. Native process termination remains a service-availability risk,
not a database-corruption finding.

## 15. Cancellation behavior

Unit coverage proves that queue timeouts and pipeline exceptions release their
slot and leave active/queued counts at zero. The synchronous FastAPI route does
not expose a cooperative cancellation token for a browser disconnect, so a
real client-disconnect cancellation was not verified. A blocking Ollama call
finishes or times out under the 180-second client timeout, after which the
`finally` release runs.

## 16. Local-demo envelope

The supported local-demo envelope is one active heavy document-RAG request,
one bounded waiter, one application worker, loopback PostgreSQL/Ollama, and no
simultaneous acceptance API. This envelope is **conditional/PARTIAL** because
the host can complete serialized direct questions but still reaches low free
RAM and uses pagefile under load. Non-RAG routes are not held behind the gate.

## 17. Internal-pilot hardware recommendation

The current laptop is not verified for an internal pilot. A reasonable next
hardware class is at least 32 GiB physical RAM with measured free headroom of
at least 4 GiB under the pilot's target concurrent workload. This derives from
the observed 15.65 GiB host, roughly 6.4 GB combined model/process footprint,
and the measured sub-1 GiB margin, with additional operating-system and
request overhead; it is not a vendor/product recommendation.

A dedicated GPU could materially reduce CPU latency for both Qwen and the
CrossEncoder without changing retrieval semantics. Exact VRAM and backend
requirements must be measured on the target accelerator; the current host has
no suitable CUDA device, and no GPU migration was implemented.

## 18. Security regression

The clean guarded acceptance run passed all 21 Phase 08 + Phase 09 tests after
the model-unload/restart procedure. It included authentication, session and
principal isolation, private-chat ownership, mixed ACL and context-expansion
checks, citation behavior, and resource-hiding assertions. The fixture was
reset and checked afterward as `portproject_acceptance` with sentinel
`acceptance/1`. No operational database mutation was performed.

## 19. Workflow regression

Phase 09 remained green in the same 21-test acceptance run, including the
DO→NO→DO revision path, NO→HO handoff, HO outcome, ownership checks, stale-role
protection, concurrent transition/revision safety, and workflow-linked AI
query behavior. No complete new lifecycle was added to this phase.

## 20. Remaining limitations

- Direct/complex and complex/complex parallel classes were intentionally not
  run after the direct/direct safety stop; they are unsupported, not silently
  passed.
- The host's low free-RAM measurements and prior native failures prevent a
  broad local capacity or internal-pilot claim.
- No 10–20-request soak or sustained leak certification was attempted.
- Browser automation is not configured; authenticated browser E2E remains a
  later phase.
- Real browser-disconnect cancellation is not observable in the current
  synchronous API; exception and timeout release are tested.
- The separate legacy API observed on port 8000 was not changed and is outside
  this project's topology.

## Reproducibility artifacts and checks

- `scripts/rag_capacity_profile.py`
- `artifacts/evaluation/rag_capacity_baseline_direct_direct.json`
- `artifacts/evaluation/rag_capacity_serialized_direct_pair.json`
- `artifacts/evaluation/rag_concurrency_profile_memory.json`
- `tests/test_rag_capacity.py`
- `/health` and `/health/ready` returned HTTP 200 for the restored normal API;
  readiness reported `rag_ready=true` and capacity active=0/limit=1/queue=0.
- Full Python suite: `102 passed, 28 skipped`.
- Ruff: passed for `src`, `tests`, and `scripts`.
- React production build: passed (Vite transformed 1,672 modules).

**Phase result: PARTIAL.** The code now enforces and exposes an honest bounded
local operating envelope without changing RAG quality or security semantics.
The laptop can run one heavy request at a time, but its measured memory
headroom and prior native failures do not support an unconditional capacity
certification or internal-pilot claim; the quality/RAG behavior freeze remains
in force.
