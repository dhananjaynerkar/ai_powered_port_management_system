# Generation, citations, and guardrails

## Generation

The API selects a requested model only from the local completion model catalog.
The configured primary model is used by default. generation.py sends question
and retrieved evidence to the local chat endpoint with bounded output,
temperature, think, and timeout settings from Settings.

## Grounding contract

The generated response is expected to use source IDs such as S1. guardrails.py
extracts referenced IDs and compares them with retrieved IDs. It rejects
unknown IDs, citations with no retrieved evidence, and substantive factual
paragraphs without a citation when evidence exists.

## Citation path

RetrievedChunk -> build_evidence_payload in api.py -> source_id, document_id,
chunk_id, title, filename, page, section, clause, excerpt, scores and ranks ->
frontend Source/CitationList chips -> source preview.

Workflow agenda messages use the same source payload shape. Context capsules
derive sources from official AI messages at the handoff timestamp rather than
creating a second unverified citation store.

## Guardrails

validate_query removes control characters, enforces minimum/maximum length, and
blocks selected prompt-injection, system-prompt disclosure, guardrail bypass,
destructive SQL, and credential exfiltration patterns.

## Residual hallucination paths

Citation validation improves grounding but does not prove every statement is
semantically entailed by a cited excerpt. Source text can be misinterpreted by
the local model, and an answer can be technically citation-valid but
insufficiently relevant. A human-reviewed faithfulness evaluation is missing.

## UI security

The backend, not hidden UI controls, owns query validation, session ownership,
role checks, and ACL retrieval filtering. Authenticated UI behavior across every
role is NOT VERIFIED in this audit.

