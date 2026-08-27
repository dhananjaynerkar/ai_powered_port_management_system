# RAG Answer Failure Root-Cause Diagnosis

Date: 2026-08-26  
Scope: read-only diagnosis of the current `portproject` corpus and local RAG runtime. No model, prompt, retrieval setting, database row, chat, or source document was changed.

## Executive conclusion

The evidence does **not** support blaming embeddings or source ingestion for the tested statutory/policy questions.

For the tested Section 150 question, the expected rule exists in the source document, survives native extraction, is wholly present in one stored chunk, and is returned by dense retrieval at rank 3. The first proven loss occurs at **reranker initialization**: the configured BGE CrossEncoder cannot load in a fresh process because Windows returns `OSError 1455` (the paging file is too small). The request therefore cannot reach final context, generation, citation validation, or the UI answer.

This explains a class of failed/503 RAG requests. It is not yet valid to claim that every question in the supplied PDF has the same first failure: the 19-page contract is not fully machine-readable and the runtime failure prevents stable complete-answer measurement.

## Test contract discovered

The supplied question-and-answer contract is [`queries/Queries.pdf`](../../queries/Queries.pdf).

- 19 pages.
- 32 explicit `Question:` labels, representing 16 unique Indian Contract Act questions repeated twice.
- Additional Port/PGLM policy question-and-answer pairs are present, but are not consistently marked with a parseable `Question:` label.
- The contract PDF is a test oracle; it is **not** an indexed document in the RAG corpus.

This is sufficient to classify the questions, but not sufficient to fabricate a total score for every pair. A full, repeatable evaluation requires the same contract in structured rows containing the original question, expected answer type, expected source, and expected fact/evidence locator.

## Actual implementation path

```
question
  -> validate_query
  -> BGE-M3 query embedding
  -> ACL-filtered lexical and pgvector candidate queries
  -> RRF fusion
  -> BGE CrossEncoder reranker
  -> neighbouring-chunk context assembly
  -> local Ollama generation
  -> strict citation validation
  -> persisted chat response / UI rendering
```

The path is implemented in:

- `src/portproject_rag/ingestion.py` — PyMuPDF/Tesseract extraction, page-preserving chunks, BGE-M3 embeddings.
- `src/portproject_rag/retrieval.py` — candidate retrieval, ACL predicate, RRF, BGE reranking, context assembly.
- `src/portproject_rag/generation.py` — evidence prompt, local Ollama call, retry after citation validation failure.
- `src/portproject_rag/guardrails.py` — input and citation controls.
- `src/portproject_rag/api.py` — authenticated answer routes and persisted chat messages.
- `web/src/main.tsx` — request submission, loading state, source display, and generic failure presentation.

## Corpus and embedding verification

Read-only PostgreSQL inspection found:

| Check | Result |
|---|---:|
| Indexed documents | 48 |
| Quarantined documents | 1 |
| Embedded chunks | 3,399 |
| Embedded documents | 48 |
| Vector dimension | 1,024 |
| Contract Act document | Indexed, 53 pages, native PyMuPDF extraction, quality 90 |
| Contract Act pages with empty extracted text | 0 |

The Section 150 evidence is on page 39, chunk index 86. It is 1,838 characters and contains both the gratuitous-bailor and bailment-for-hire rules. It was not lost during extraction or chunking.

## Question taxonomy and answer contract

The supplied questions belong to document RAG, not live tenant/billing/tender data routing.

| Question type | Where it must come from | Correct answer shape |
|---|---|---|
| `DOCUMENT_STATUTORY_FACT` | Act section in indexed PDF | Direct conclusion, section reference, page/source citation. |
| `DOCUMENT_STATUTORY_EXCEPTIONS` | One Act provision | Short numbered list of exceptions, each fact cited. |
| `DOCUMENT_POLICY_NUMERIC_WITH_CONDITIONS` | PGLM/circular/clarification | Value plus unit, conditions/limitations, source citation. |
| `DOCUMENT_POLICY_REQUIREMENT` | Circular/clarification | Requirement, who it applies to, and any exception, cited. |
| `DOCUMENT_POLICY_COMPARISON` | One or more provisions | Clear side-by-side distinction, cited on each factual paragraph. |
| `DOCUMENT_SCENARIO_APPLICATION` | Relevant provisions | Result first, then a concise application of each cited provision to the scenario. |
| `MULTI_DOCUMENT_POLICY` | More than one indexed source | Explicit synthesis with a citation for each source-backed conclusion. |
| `NO_EVIDENCE` | No authorised corpus evidence | Natural no-evidence response; no invented fact or citation. |

Questions about a current tenant, payment, workflow state, billing forecast, tender record, or application ID are a different category. They require their dedicated database/service route; sending them to the document route must be classified as **wrong data-source routing**, not as an embedding failure.

## Evidence waterfall — tested questions

### Q15 — Section 150 bailor responsibility

| Stage | Evidence |
|---|---|
| Source exists | Yes — `Contract Act 1872.pdf` |
| Document indexed | Yes |
| Expected text extracted | Yes — native extraction, page 39 |
| Expected text in chunk | Yes — chunk index 86 |
| Dense rank | 3 |
| Lexical rank | Absent |
| Hybrid candidate set | Present |
| Reranker | **Failed to initialize** |
| Final context | Not reached |
| Generation | Not reached through complete path |
| Citation validation | Not reached through complete path |
| First failure stage | **RERANKER_INITIALIZATION** |
| Root cause | `OSError 1455`: Windows paging file too small while loading `BAAI/bge-reranker-v2-m3` |
| Confidence | High |

### Additional candidate-stage evidence

| Contract case | Expected evidence status | Dense rank | Lexical rank | Candidate set | Full-answer result |
|---|---|---:|---:|---|---|
| Section 25 statutory exceptions | Present in `Contract Act 1872.pdf` | 1 | absent | present | blocked at reranker runtime |
| Custom bond area tenure | Present in PGLM clarification material | 1 | 1 | present | blocked at reranker runtime |
| EMD under Clarification 3 | Present in `Clarification No 2 of 2019_1048.pdf` | 3 | absent | present | blocked at reranker runtime |

These records are stored in [`artifacts/evaluation/rag_question_diagnostics.json`](../../artifacts/evaluation/rag_question_diagnostics.json).

## Secondary findings

### Lexical retrieval is too strict for long legal questions

The Section 150 question compiles to an AND-heavy PostgreSQL `websearch_to_tsquery`. The final query requires all of terms such as `section`, `150`, `gratuitous`, `non-gratuitous`, `defects`, and `bailed` in one chunk. The correct chunk uses the statutory wording `bailed for hire`, so the complete query has zero lexical matches even though the individual terms are indexed.

Dense retrieval recovered the correct chunk at rank 3, so this is a proven **lexical recall weakness**, not the first failure for Q15.

### Local generation is available but has a reliability/latency risk

The local Ollama catalog is reachable and contains the configured `qwen3.5:4b` model. A minimal completion completed in 1,366 ms. A direct evidence-grounded generation probe with a deliberately short 20-second diagnostic timeout produced `ReadTimeout`.

The normal configuration permits 180 seconds, so this single short-timeout probe does not prove a normal-config generation defect. It does prove that a visible “Searching…” state can be caused after evidence retrieval by generation latency, not only by search.

Earlier acceptance evidence also recorded one complete cited answer in 25.3 seconds followed by consecutive HTTP 503 outcomes. This supports a reliability issue, not a stable per-question quality score.

### The API obscures the failed stage

`api.py` catches every exception from the complete answer pipeline and emits `503 Retrieval unavailable: <exception type>`. A reranker failure, embedding failure, generation timeout, and citation failure are therefore indistinguishable to the UI. The UI further replaces the server detail with a generic “AI Assistant is temporarily unavailable” message.

### The context selector is not a RAG filter

The private-chat request only submits question, chat session ID, and selected model. The selected UI context is not included in the document-RAG request. Its Billing/Tender options open their respective workflows; it does not filter the ordinary RAG corpus. Users should not expect it to scope document retrieval.

## Root-cause distribution

No overall answer-quality distribution is reported because the supplied contract is not fully structured and complete answer execution is not stable. For the **four candidate-stage probes**:

| First proven result | Count |
|---|---:|
| Source missing | 0 |
| Extraction failure | 0 |
| Chunking failure | 0 |
| Embedding/dense candidate failure | 0 |
| Lexical recall weakness | 3 |
| Reranker initialization failure | 1 complete-path probe |
| Context / generation / citation correctness measured end-to-end | Not reliably measurable while reranker initialization fails |

## Direct answers to the required questions

| Question | Evidence-backed answer |
|---|---|
| Is the embedding model the main problem? | **No** for the tested cases. The correct chunk was retrieved densely. |
| Is chunking the main problem? | **No** for Q15. The complete rule is contained in one extracted chunk. |
| Is the reranker the main problem? | **Yes, for the reproduced complete-path failure.** Initialization fails before context assembly. |
| Is the LLM the main problem? | **Not proven as the main cause.** It is reachable, but evidence-grounded generation exhibits latency risk. |
| Is citation validation blocking good answers? | **Not verified** for these contract questions because the reranker failure occurs earlier. |
| Are some questions using the wrong data source? | **No** for the supplied Act/PGLM/circular bank. **Yes, if** a user asks live tenant/billing/workflow/tender data through this document-only route. |
| #1 verified root cause | The fresh-process BGE CrossEncoder cannot initialize because the Windows paging file is too small (`OSError 1455`). |

## Safe next diagnostic gate

Do not tune chunk size, embedding model, top-k, temperature, or citations yet. First make the reranker process reliably load in a controlled acceptance environment, then run the original questions unchanged through the stage-by-stage waterfall and score answer/citation correctness. The original PDF should be converted to a structured evaluation file without changing the questions or expected answers.
