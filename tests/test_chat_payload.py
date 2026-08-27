import json
from uuid import UUID

from portproject_rag import api
from portproject_rag.generation import GenerationResult
from portproject_rag.retrieval import RetrievalResult, RetrievalTimings, RetrievedChunk


def test_all_answer_routes_share_live_evidence_payload(monkeypatch) -> None:
    chunk = RetrievedChunk(
        source_id="S1",
        document_id=UUID("00000000-0000-0000-0000-000000000001"),
        chunk_id=UUID("00000000-0000-0000-0000-000000000002"),
        document_title="Database supplied title",
        filename="database-supplied.pdf",
        page_number=7,
        chunk_index=11,
        chunk_text="A policy clause.",
        context_text="Parent context and matched child text.",
        section_title="Lease conditions",
        clause_number="4.2",
        lexical_rank=1,
        dense_rank=2,
        fused_score=0.03,
        rerank_score=0.91,
    )
    monkeypatch.setattr(api, "retrieve", lambda settings, question, user_role, limit: RetrievalResult([chunk], RetrievalTimings(1, 2, 3, 4, 5), 1))
    monkeypatch.setattr(api, "_selected_local_model", lambda settings, requested_model: "selected-local-model")
    monkeypatch.setattr(api, "generate_grounded_answer", lambda settings, question, evidence, model: GenerationResult("Grounded answer [S1]", 6, 7, True, None))

    payload = api._answer_payload(object(), "What is the policy?", None, "authority")

    assert payload["route"] == "DOCUMENT_RAG"
    assert payload["llm_model"] == "selected-local-model"
    assert payload["sources"][0] == {
        "source_id": "S1",
        "document_id": "00000000-0000-0000-0000-000000000001",
        "chunk_id": "00000000-0000-0000-0000-000000000002",
        "title": "Database supplied title",
        "filename": "database-supplied.pdf",
        "page": 7,
        "section_title": "Lease conditions",
        "clause_number": "4.2",
        "excerpt": "A policy clause.",
        "score": 0.91,
        "fused_score": 0.03,
        "lexical_rank": 1,
        "dense_rank": 2,
        "source_metadata": None,
    }
    json.dumps(payload)
