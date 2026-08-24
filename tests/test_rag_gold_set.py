import json
from pathlib import Path

from psycopg import connect

from portproject_rag.settings import Settings

GOLD_PATH = Path(__file__).parents[1] / "evaluation" / "rag_gold_v1.json"
REQUIRED_TYPES = {
    "direct_fact",
    "multi_paragraph_answer",
    "multi_page_answer",
    "policy_interpretation",
    "cross_document_question",
    "ambiguous_question",
    "no_answer_question",
    "role_restricted_question",
    "similar_document_confusion_case",
    "table_related_question",
}


def test_gold_set_has_balanced_reviewed_schema() -> None:
    payload = json.loads(GOLD_PATH.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "rag_gold_v1"
    assert payload["review_policy"]["llm_generated_expected_evidence"] is False
    examples = payload["examples"]
    assert len(examples) >= len(REQUIRED_TYPES)
    assert {example["question_type"] for example in examples} == REQUIRED_TYPES
    assert len({example["id"] for example in examples}) == len(examples)
    for example in examples:
        assert example["question"]
        assert example["review_status"] == "reviewed"
        assert example["allowed_role"] in {"authority", "tenant"}
        assert isinstance(example["answer_should_exist"], bool)
        assert "expected_supporting_fact" in example and example["expected_supporting_fact"]


def test_gold_set_positive_references_match_live_indexed_sources() -> None:
    payload = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    settings = Settings()
    with connect(settings.database_url.unicode_string()) as connection, connection.cursor() as cursor:
        for example in payload["examples"]:
            expected_pages = set(example["expected_pages"])
            referenced_pages: set[int] = set()
            for document in example["expected_documents"]:
                cursor.execute(
                    f"""SELECT document_id, file_sha256, ingestion_state
                    FROM {settings.document_schema_name}.document_record
                    WHERE original_filename = %s""",
                    (document["filename"],),
                )
                row = cursor.fetchone()
                assert row, f"Missing gold-set source document: {document['filename']}"
                assert row[1] == document["source_sha256"], f"Source hash changed: {document['filename']}"
                assert row[2] == "indexed", f"Gold-set source is not indexed: {document['filename']}"
                cursor.execute(
                    f"""SELECT DISTINCT page_number
                    FROM {settings.vector_schema_name}.document_chunk
                    WHERE document_id = %s AND page_number = ANY(%s)""",
                    (row[0], document["pages"]),
                )
                referenced_pages.update(page[0] for page in cursor.fetchall())
            assert referenced_pages == expected_pages, f"Page references drifted for {example['id']}"
