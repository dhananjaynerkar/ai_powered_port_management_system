from types import SimpleNamespace

from portproject_rag import evaluation, generation
from portproject_rag.guardrails import referenced_source_ids, validate_citations
from portproject_rag.query_analysis import analyse_query
from portproject_rag.settings import Settings


def _settings() -> Settings:
    return Settings(database_url="postgresql://test@127.0.0.1:9/test")


def _evidence() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            source_id="S1",
            filename="policy.pdf",
            page_number=4,
            section_title=None,
            clause_number=None,
            context_text="This document does not contain the requested forecast.",
        ),
        SimpleNamespace(
            source_id="S2",
            filename="clarification.pdf",
            page_number=2,
            section_title=None,
            clause_number=None,
            context_text="This document does not contain the requested forecast.",
        ),
    ]


def test_safe_no_evidence_response_is_not_rejected_just_because_irrelevant_chunks_exist() -> None:
    valid, error = validate_citations(
        "I couldn't find that information in the documents available to you.",
        {"S1", "S2"},
    )

    assert valid is True
    assert error is None


def test_compact_multi_source_citation_syntax_is_normalized_without_creating_ids() -> None:
    answer = "The two documents support this conclusion. [S1, S2]"

    assert referenced_source_ids(answer) == {"S1", "S2"}
    assert validate_citations(answer, {"S1", "S2"}) == (True, None)
    assert validate_citations(answer, {"S1"})[0] is False


def test_no_evidence_model_marker_returns_a_deterministic_safe_disposition(monkeypatch) -> None:
    monkeypatch.setattr(
        generation,
        "_call_ollama_result",
        lambda *_args, **_kwargs: generation._OllamaResult("NO_EVIDENCE", None, None, None),
    )

    result = generation.generate_grounded_answer(
        _settings(),
        "What will the port throughput be in a future year?",
        _evidence(),
    )

    assert result.disposition == "NO_EVIDENCE"
    assert result.citation_valid is True
    assert "couldn't find" in result.answer.casefold()


def test_table_contract_asks_for_value_unit_condition_and_source() -> None:
    prompt = generation._prompt(
        "What is the charge per square metre per day for up to 15 days in Appendix A?",
        _evidence(),
    )

    assert "value; unit; requested row condition" in prompt[0]["content"].casefold()
    assert "QUESTION" in prompt[1]["content"]
    assert prompt[1]["content"].find("QUESTION") < prompt[1]["content"].find("EVIDENCE")


def test_answer_shape_prefers_table_and_explicit_cross_period_comparison_contracts() -> None:
    assert analyse_query("What is the charge per square metre per day for up to 15 days in Appendix A?").answer_shape == "table"
    assert analyse_query("How do the 2018 and 2019 clarification circulars treat the intervening period?").answer_shape == "comparison"
    assert analyse_query("What is the lease period in the tender conditions, and is renewal provided?").answer_shape == "direct_fact"
    assert analyse_query("How are the upfront premium installments scheduled, and what applies to delayed payment?").answer_shape == "list"


def test_comparison_and_table_contracts_limit_output_to_the_requested_shape() -> None:
    comparison = generation._prompt("How do the 2018 and 2019 circulars differ?", _evidence())
    table = generation._prompt("What is the Appendix A rate per square metre?", _evidence())

    assert "exactly two labelled bullets" in comparison[0]["content"].casefold()
    assert "do not use a markdown table" in comparison[0]["content"].casefold()
    assert "exactly one concise bullet" in table[0]["content"].casefold()
    assert "if the requested row is visible" in table[0]["content"].casefold()


def test_compact_prompt_keeps_the_answer_contract_once_in_the_user_message() -> None:
    prompt = generation._prompt("What is the Appendix A rate per square metre?", _evidence(), compact_instructions=True)

    assert "exactly one concise bullet" not in prompt[0]["content"].casefold()
    assert "exactly one concise bullet" in prompt[1]["content"].casefold()


def test_evaluation_honours_application_routing_before_document_generation(monkeypatch) -> None:
    def unexpected_retrieval(*_args, **_kwargs):
        raise AssertionError("A live-data request must not be sent to document retrieval by the evaluator.")

    monkeypatch.setattr(evaluation, "retrieve", unexpected_retrieval)
    result = evaluation._run_one(
        _settings(),
        {
            "id": "route-test", "question": "Show me the private balance and account history for tenant customer 184.",
            "question_type": "role_restricted_question", "allowed_role": "authority", "answer_should_exist": False,
            "expected_documents": [], "expected_pages": [], "must_include_facts": [],
        },
        generate=True,
    )

    assert result["status"] == "application_precondition"
    assert result["application_precondition"] == "ROUTED"
    assert result["generation_call_success"] is None


def test_citation_repair_rejects_a_rewrite_of_factual_text(monkeypatch) -> None:
    outputs = iter(
        [
            generation._OllamaResult("The lease lasts thirty years.", None, None, None),
            generation._OllamaResult("The lease lasts twenty years. [S1]", None, None, None),
        ]
    )
    monkeypatch.setattr(generation, "_call_ollama_result", lambda *_args, **_kwargs: next(outputs))

    result = generation.generate_grounded_answer(_settings(), "What is the lease term?", _evidence())

    assert result.citation_repair_used is True
    assert result.citation_repair_succeeded is False
    assert result.citation_valid is False
    assert "thirty years" not in result.answer.casefold()


def test_output_limit_stop_reason_is_preserved_for_evaluation_telemetry(monkeypatch) -> None:
    monkeypatch.setattr(
        generation,
        "_call_ollama_result",
        lambda *_args, **_kwargs: generation._OllamaResult("A short grounded answer. [S1]", None, None, None, 20, 120, "length"),
    )

    result = generation.generate_grounded_answer(_settings(), "What does the policy say?", _evidence())

    assert result.citation_valid is True
    assert result.stop_reason == "length"
    assert result.eval_count == 120


def test_generation_reports_prompt_and_answer_assembly_stages(monkeypatch) -> None:
    monkeypatch.setattr(
        generation,
        "_call_ollama_result",
        lambda *_args, **_kwargs: generation._OllamaResult("A short grounded answer. [S1]", 1, 2, 3, 4, 5, "stop"),
    )

    result = generation.generate_grounded_answer(_settings(), "What does the policy say?", _evidence())

    assert result.prompt_build_ms >= 0
    assert result.answer_assembly_ms >= 0
    assert result.prompt_eval_ms == 2
    assert result.token_generation_ms == 3
