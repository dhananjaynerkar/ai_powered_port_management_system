from types import SimpleNamespace
from uuid import uuid4

from portproject_rag.evaluation import citation_metrics, retrieval_metrics


def _chunk(source_id: str, filename: str, page: int) -> SimpleNamespace:
    return SimpleNamespace(
        source_id=source_id,
        document_id=uuid4(),
        chunk_id=uuid4(),
        filename=filename,
        page_number=page,
        document_title=filename,
        chunk_index=0,
        section_title=None,
        clause_number=None,
        lexical_rank=None,
        dense_rank=None,
        fused_score=1.0,
        rerank_score=1.0,
        chunk_text="evidence",
        context_text="evidence",
    )


def test_retrieval_metrics_use_filename_and_page_pairs() -> None:
    example = {
        "expected_documents": [{"filename": "policy.pdf", "pages": [4, 7]}],
        "expected_pages": [4, 7],
    }
    chunks = [_chunk("S1", "other.pdf", 1), _chunk("S2", "policy.pdf", 7)]

    metrics = retrieval_metrics(example, chunks)

    assert metrics["recall_at_1"] == 0.0
    assert metrics["recall_at_3"] == 1.0
    assert metrics["mrr"] == 0.5
    assert metrics["ndcg_at_5"] > 0


def test_negative_case_requires_abstention_without_citations() -> None:
    example = {"expected_documents": [], "expected_pages": []}
    generation = SimpleNamespace(
        answer="The indexed corpus does not contain enough evidence to answer this question.",
        citation_valid=True,
    )

    metrics = citation_metrics(example, [], generation)

    assert metrics["citation_page_accuracy"] == 1.0
    assert metrics["citation_count"] == 0
