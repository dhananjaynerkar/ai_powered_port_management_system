import json
from pathlib import Path

from portproject_rag.evaluation import load_evaluation_contract

CONTRACT_PATH = Path(__file__).parents[1] / "evaluation" / "rag_answer_contract_v2.json"


def test_v2_contract_preserves_reviewed_questions_and_requires_evidence_structure() -> None:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "rag_answer_contract_v2"
    assert payload["source_contract"] == "rag_gold_v1.json"
    assert len(payload["records"]) == 11
    for record in payload["records"]:
        assert record["question"]
        assert record["expected_answer_shape"]
        assert isinstance(record["must_include_facts"], list)
        assert isinstance(record["required_evidence_items"], list)
        assert record["allowed_role"] in {"authority", "tenant"}


def test_evaluator_loads_v2_contract_without_generating_gold_facts() -> None:
    version, examples = load_evaluation_contract(CONTRACT_PATH)

    assert version == "rag_answer_contract_v2"
    assert examples[0]["question"] == "Under By-law No. 9, how much notice may be affixed before an obstruction is removed?"
    assert examples[0]["expected_documents"] == examples[0]["acceptable_documents"]
