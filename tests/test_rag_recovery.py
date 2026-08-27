from types import ModuleType, SimpleNamespace
from uuid import UUID, uuid4

from portproject_rag import api, generation, retrieval
from portproject_rag.api import _answer_payload, _rag_http_exception
from portproject_rag.evaluation import retrieval_metrics
from portproject_rag.query_analysis import (
    analyse_query,
    classify_source_domain,
    needs_property_clarification,
)
from portproject_rag.rag_errors import RagStageError
from portproject_rag.settings import Settings
from portproject_rag.source_metadata import derive_source_metadata


def _settings() -> Settings:
    return Settings(database_url="postgresql://test@127.0.0.1:9/test")


def _row(document: UUID, chunk: UUID, page: int, score: float) -> dict[str, object]:
    return {
        "chunk_id": chunk,
        "document_id": document,
        "chunk_index": page,
        "chunk_text": f"Evidence for page {page}",
        "section_title": None,
        "clause_number": None,
        "document_title": f"Document {document}",
        "filename": f"policy-{document}.pdf",
        "page_number": page,
        "lexical_rank": page,
        "dense_rank": page,
        "lexical_ranks": [page],
        "fused_score": score,
        "source_metadata": None,
    }


def test_query_normalization_preserves_reference_identifiers_and_uses_narrow_data_routing() -> None:
    query = analyse_query("Under Section 150 and Appendix A of By-law No. 9, compare Clarification No. 2 of 2019.")

    assert "Section 150" in query.exact_references
    assert "Appendix A" in query.exact_references
    assert any("2019" in reference for reference in query.exact_references)
    assert "150" in query.important_terms
    assert query.answer_shape == "comparison"
    assert classify_source_domain("Explain tender conditions in the policy") == "DOCUMENT_RAG"
    assert classify_source_domain("Predict the next billing amount") == "BILLING"
    assert needs_property_clarification("What is the correct lease rent for this property?") is True
    assert needs_property_clarification("What is the lease rate for plot 42?") is False


def test_multi_evidence_query_analysis_derives_bounded_user_stated_facets() -> None:
    query = analyse_query("What conditions apply to transfer or sub-leasing, and what approval path is required?")

    assert query.answer_shape in {"list", "multi_document"}
    assert 2 <= len(query.coverage_facets) <= 4
    assert all("page" not in facet and "document" not in facet for facet in query.coverage_facets)


def test_context_candidate_selection_keeps_page_and_document_diversity() -> None:
    document_a, document_b = uuid4(), uuid4()
    rows = [
        _row(document_a, uuid4(), 1, 0.9),
        _row(document_a, uuid4(), 1, 0.8),
        _row(document_a, uuid4(), 2, 0.7),
        _row(document_b, uuid4(), 1, 0.6),
    ]

    selected, excluded = retrieval._select_context_candidates(rows, 3)

    assert {(row["document_id"], row["page_number"]) for row in selected} == {(document_a, 1), (document_a, 2), (document_b, 1)}
    assert {item["reason"] for item in excluded} == {"duplicate_page"}


def test_context_candidate_selection_preserves_distinct_evidence_facets_before_generic_diversity() -> None:
    """A multi-part answer needs one supporting source per uncovered facet.

    This is deliberately independent of a particular document, page, or
    golden-set question.  It protects the generic selection policy when a
    hybrid candidate pool already contains complementary evidence.
    """
    document_a, document_b = uuid4(), uuid4()
    rows = [
        {**_row(document_a, uuid4(), 1, 0.9), "facet_indexes": [0]},
        {**_row(document_b, uuid4(), 1, 0.8), "facet_indexes": []},
        {**_row(document_a, uuid4(), 2, 0.7), "facet_indexes": [1]},
        {**_row(document_a, uuid4(), 3, 0.6), "facet_indexes": [2]},
    ]

    selected, _excluded = retrieval._select_context_candidates(rows, 3, "list")

    assert {facet for row in selected for facet in row.get("facet_indexes", [])} == {0, 1, 2}


def test_context_candidate_selection_keeps_an_adjacent_authorized_page_for_multi_part_evidence() -> None:
    document = uuid4()
    rows = [
        {**_row(document, uuid4(), 4, 0.9), "facet_indexes": [0], "adjacent_to_candidate": False},
        {**_row(document, uuid4(), 5, 0.8), "facet_indexes": [1], "adjacent_to_candidate": False},
        {**_row(document, uuid4(), 6, 0.2), "facet_indexes": [], "adjacent_to_candidate": True, "adjacent_anchor_page": 5},
        {**_row(uuid4(), uuid4(), 1, 0.7), "facet_indexes": [], "adjacent_to_candidate": False},
    ]

    selected, _excluded = retrieval._select_context_candidates(rows, 3, "list")

    assert {(row["document_id"], row["page_number"]) for row in selected} == {(document, 4), (document, 5), (document, 6)}


def test_context_selection_prioritizes_textual_predecessor_over_redundant_source() -> None:
    """A preceding page is preferred only when the selected anchor is a fragment.

    This guards the generic continuation rule without using a document, page,
    question, or gold-answer identifier.
    """
    document = uuid4()
    rows = [
        {**_row(document, uuid4(), 10, 0.9), "facet_indexes": [0], "document_hint_matches": 1, "adjacent_to_candidate": False},
        {**_row(document, uuid4(), 3, 0.8), "facet_indexes": [0], "document_hint_matches": 1, "adjacent_to_candidate": False},
        {**_row(document, uuid4(), 9, 0.2), "facet_indexes": [], "document_hint_matches": 1, "adjacent_to_candidate": True, "adjacent_anchor_page": 10, "structural_continuation": True},
        {**_row(document, uuid4(), 22, 0.7), "facet_indexes": [], "document_hint_matches": 1, "adjacent_to_candidate": False},
    ]

    selected, _excluded = retrieval._select_context_candidates(rows, 3, "multi_document")

    assert {(row["document_id"], row["page_number"]) for row in selected} == {(document, 3), (document, 9), (document, 10)}


def test_table_evidence_boost_requires_general_unit_and_time_band_signature() -> None:
    query = analyse_query("What is the charge per square metre per day for up to 15 days in Appendix A?")

    assert retrieval._table_evidence_boost(query, "Charges per Sq. met re per day. Upto 15 days.", 0.75) == 0.75
    assert retrieval._table_evidence_boost(query, "A charge may be recovered after a notice.", 0.75) == 0.0


def test_reranker_failure_uses_acl_safe_rrf_fallback(monkeypatch) -> None:
    document = uuid4()
    rows = [_row(document, uuid4(), 1, 0.9), _row(uuid4(), uuid4(), 2, 0.8)]
    monkeypatch.setattr(retrieval, "_candidate_rows", lambda *_args: (rows, 1, 2, 3))
    monkeypatch.setattr(retrieval, "_rerank", lambda *_args: (_ for _ in ()).throw(RagStageError("RERANKER_UNAVAILABLE")))
    monkeypatch.setattr(
        retrieval,
        "_expand_context_with_metadata",
        lambda _settings, selected, user_role, _shape: ([{**row, "context_text": row["chunk_text"]} for row in selected], 10, False),
    )

    settings = _settings().model_copy(update={"final_context_source_count_direct": 2})
    result = retrieval.retrieve(settings, "What does Section 150 require?", "tenant")

    assert result.diagnostics and result.diagnostics.reranker_degraded is True
    assert result.diagnostics.reranker_reason == "RERANKER_UNAVAILABLE"
    assert [chunk.chunk_id for chunk in result.chunks] == [rows[0]["chunk_id"], rows[1]["chunk_id"]]


def test_reranker_uses_scoped_local_artifact_resolution(monkeypatch) -> None:
    seen: dict[str, object] = {}

    class FakeCrossEncoder:
        def __init__(self, _model: str, **kwargs: object) -> None:
            seen.update(kwargs)

    sentence_transformers = ModuleType("sentence_transformers")
    sentence_transformers.CrossEncoder = FakeCrossEncoder  # type: ignore[attr-defined]
    monkeypatch.setitem(__import__("sys").modules, "sentence_transformers", sentence_transformers)
    retrieval.clear_reranker_cache()

    try:
        retrieval._reranker(_settings())

        assert seen["local_files_only"] is True
        assert seen["device"] == "cpu"
    finally:
        retrieval.clear_reranker_cache()


def test_reranker_respects_configured_prefix_of_candidate_pool(monkeypatch) -> None:
    rows = [_row(uuid4(), uuid4(), index, 1.0 - index / 20) for index in range(1, 11)]
    seen: list[int] = []
    monkeypatch.setattr(retrieval, "_candidate_rows", lambda *_args: (rows, 1, 2, 3))

    def fake_rerank(_settings, _question, texts):
        seen.append(len(texts))
        return [float(index) for index, _text in enumerate(texts, start=1)]

    monkeypatch.setattr(retrieval, "_rerank", fake_rerank)
    monkeypatch.setattr(
        retrieval,
        "_expand_context_with_metadata",
        lambda _settings, selected, user_role, _shape: ([{**row, "context_text": row["chunk_text"]} for row in selected], 10, False),
    )

    result = retrieval.retrieve(_settings(), "What does Section 150 require?", "tenant")

    assert seen == [_settings().rerank_candidate_count]
    assert result.candidate_count == 10


def test_retrieval_stage_telemetry_keeps_embedding_separate_from_dense_and_fusion(monkeypatch) -> None:
    row = _row(uuid4(), uuid4(), 1, 0.9)
    monkeypatch.setattr(retrieval, "_candidate_rows", lambda *_args: ([row], 11, 12, 13, 14))
    monkeypatch.setattr(retrieval, "_adjacent_page_candidates", lambda *_args: [])
    monkeypatch.setattr(retrieval, "_rerank", lambda *_args: [0.9])
    monkeypatch.setattr(
        retrieval,
        "_expand_context_with_metadata",
        lambda _settings, selected, user_role, _shape: ([{**item, "context_text": item["chunk_text"]} for item in selected], 10, False),
    )

    result = retrieval.retrieve(_settings(), "What does Section 150 require?", "tenant")

    assert result.timings.embed_ms == 11
    assert result.timings.dense_retrieval_ms == 13
    assert result.timings.candidate_fusion_ms == 14
    assert result.timings.query_analysis_ms >= 0
    assert result.timings.context_selection_ms >= 0


def test_simple_answer_context_limits_do_not_change_multi_evidence_limit() -> None:
    settings = _settings()

    assert retrieval._final_context_limit(settings, "direct_fact") == 1
    assert retrieval._final_context_limit(settings, "table") == 1
    assert retrieval._final_context_limit(settings, "comparison") == 4
    assert retrieval._final_context_limit(settings, "multi_document") == 4


def test_citation_repair_accepts_only_citation_only_change(monkeypatch) -> None:
    outputs = iter(
        [
            generation._OllamaResult("The source confirms the lease is for thirty years with no renewal option.", None, None, None),
            generation._OllamaResult("The source confirms the lease is for thirty years with no renewal option. [S1]", None, None, None),
        ]
    )
    monkeypatch.setattr(generation, "_call_ollama_result", lambda *_args, **_kwargs: next(outputs))
    evidence = [SimpleNamespace(source_id="S1", filename="policy.pdf", page_number=4, section_title=None, clause_number=None, context_text="Thirty years; no renewal.")]

    result = generation.generate_grounded_answer(_settings(), "What is the lease term?", evidence)

    assert result.first_pass_citation_valid is False
    assert result.citation_repair_used is True
    assert result.citation_valid is True
    assert result.answer.endswith("[S1]")


def test_multi_page_metrics_distinguish_any_hit_from_evidence_coverage() -> None:
    example = {"expected_documents": [{"filename": "policy.pdf", "pages": [4, 7]}]}
    chunks = [SimpleNamespace(filename="policy.pdf", page_number=4), SimpleNamespace(filename="other.pdf", page_number=1)]

    metrics = retrieval_metrics(example, chunks)

    assert metrics["any_hit_at_1"] == 1.0
    assert metrics["evidence_coverage_at_1"] == 0.5
    assert metrics["evidence_coverage_at_3"] == 0.5


def test_stage_error_exposes_only_safe_message_and_correlation_id() -> None:
    response = _rag_http_exception(RagStageError("GENERATION_TIMEOUT"))

    assert response.status_code == 503
    assert response.detail["code"] == "GENERATION_TIMEOUT"
    assert "took too long" in response.detail["message"].casefold()
    assert "request_id" in response.detail


def test_structured_domain_and_ambiguity_requests_do_not_enter_document_retrieval(monkeypatch) -> None:
    monkeypatch.setattr("portproject_rag.api.retrieve", lambda *_args: (_ for _ in ()).throw(AssertionError("document retrieval must not run")))

    billing = _answer_payload(_settings(), "Predict the next billing amount", None, "authority")
    ambiguous = _answer_payload(_settings(), "What is the correct lease rent for this property?", None, "authority")

    assert billing["route"] == "BILLING"
    assert billing["answer_disposition"] == "ROUTED"
    assert ambiguous["route"] == "DOCUMENT_RAG"
    assert ambiguous["answer_disposition"] == "AMBIGUOUS"


def test_readiness_reports_reranker_state_without_forcing_model_load(monkeypatch) -> None:
    api.app.state.settings = _settings()
    api.app.state.rag_ready = True
    api.app.state.rag_init_error = None
    monkeypatch.setattr(api, "_stats", lambda _settings: {"indexed_documents": 1})
    monkeypatch.setattr(api, "reranker_state", lambda _settings: {"state": "degraded", "degraded": True, "reason": "OSError"})

    response = api.ready()

    assert response.status_code == 200
    assert response.body and b'"reranker"' in response.body


def test_source_metadata_is_conservative_and_does_not_infer_supersession() -> None:
    metadata = derive_source_metadata("Clarification No 2 of 2019_1048.pdf")

    assert metadata.document_family == "Clarification No. 2 of 2019"
    assert metadata.clarification_number == "2"
    assert metadata.supersedes is None
