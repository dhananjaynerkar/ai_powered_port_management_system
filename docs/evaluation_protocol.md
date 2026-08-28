# RAG evaluation protocol

**Status:** Documented protocol and evidence map. The results below are historical, corpus-bound checkpoints; this file does not claim a new evaluation run.

## Purpose

Measure retrieval quality, evidence completeness, citation validity, and runtime behavior for the local-first RAG pipeline without exposing the operational corpus, raw passages, credentials, or private user data.

## Repository snapshot

- Repository: dhananjaynerkar/ai_powered_port_management_system
- Code snapshot used by the current public repository: 607c28dfe1cbffa4605fb0e2f4c5588235d89a85
- Review date for the current runtime certificate: 2026-08-27
- Retrieval store: PostgreSQL full-text search plus pgvector
- Generation boundary: local Ollama model and local CrossEncoder reranker
- Corpus boundary: read-only normal-corpus and isolated acceptance-fixture runs

## Versioned evaluation inputs

The repository contains versioned evaluation definitions:

- evaluation/rag_gold_v1.json
- evaluation/rag_fact_evidence_v1.json
- evaluation/rag_answer_contract_v2.json

The corresponding test and replay entry points include:

- tests/test_rag_gold_set.py
- tests/test_rag_evaluation.py
- tests/test_live_corpus_evaluation.py
- tests/test_chat_payload.py
- scripts/rag_generation_replay.py
- scripts/rag_performance_profile.py

Raw passages and runtime evaluation artifacts are intentionally not required to be public. A reviewer should be able to inspect the metric definitions and commands without receiving the operational corpus.

## Frozen quality checkpoint

The following values are copied from docs/hardening/RAG_RUNTIME_FINAL_CERTIFICATION.md and docs/hardening/RAG_PERFORMANCE_OPTIMIZATION.md. They are not recomputed by this documentation change.

| Measure | Result | Interpretation |
| --- | ---: | --- |
| AnyHit@1 | 0.67 | At least one relevant result in the first result |
| AnyHit@3 | 0.89 | At least one relevant result in the first three results |
| AnyHit@5 | 0.89 | At least one relevant result in the first five results |
| EvidenceCoverage@5 | 0.85 | Reviewed evidence coverage within the top five |
| FactCoverage | 1.00 (10/10) | Reviewed mapped facts covered |
| CompleteFactEvidenceRate | 1.00 (3/3) | Reviewed mapped cases fully evidenced |
| Citation-valid generation cases | 9/9 | Returned citations passed the project validator |
| Generation timeouts in that replay | 0 | No timeout in the nine-record replay |

The readiness snapshot documented in the release evidence contains 48 indexed documents, 1,474 pages, and 3,399 chunks/vectors. The same evidence records one quarantined document separately; quarantined material is not treated as trusted retrieval evidence.

## Required reporting fields

Every future result should record:

1. Git commit SHA.
2. Review date and host/runtime conditions.
3. Corpus or fixture identifier and document/page/chunk counts.
4. Model names and versions, embedding dimensions, reranker configuration, and generation settings.
5. Query-set version and sample size.
6. Retrieval mode: lexical, dense, fused, or reranked.
7. ACL/principal context used for the query.
8. Metric definitions and numerator/denominator.
9. Failed, refused, timed-out, and citation-invalid cases.
10. Whether the result was read-only normal-corpus evidence or an isolated acceptance-fixture result.

## Reproduction boundary

Use an approved isolated database and local model cache. Do not point a clean checkout at an operational database, copy a developer .env into the repository, or commit raw passages, credentials, or runtime artifacts.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q tests/test_rag_gold_set.py tests/test_rag_evaluation.py tests/test_live_corpus_evaluation.py tests/test_chat_payload.py
~~~

The live-corpus and generation replay scripts require their documented local database/model prerequisites. If those prerequisites are unavailable, record the evaluation as NOT RUN, not as a zero or a pass.

## Interpretation limits

- Citation validity means the project validator accepted the citation contract; it does not by itself prove semantic faithfulness or answer usefulness.
- The nine-record generation replay is a reviewed checkpoint, not evidence of production uptime, enterprise scale, or a statistically strong latency distribution.
- The current evidence does not establish production deployment, multi-process capacity, or a public live demo.
- Do not describe the project as agentic RAG, MCP, VLM, fine-tuned, or true iterative multi-hop retrieval; those capabilities are not evidenced in the repository.

