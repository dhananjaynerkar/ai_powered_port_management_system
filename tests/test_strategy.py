from portproject_rag.inspection import PageProfile
from portproject_rag.strategy import (
    Capabilities,
    generate_page_strategies,
    plan_query,
    select_strategy,
)


def _page(kind: str, quality: int = 90, image_count: int = 0, table: bool = False) -> PageProfile:
    return PageProfile(1, kind, "NATIVE_PYMUPDF", quality, "HIGH", 500, 80, 1.0, 0.1, 0, 0, image_count, table)


def test_scanned_page_quarantines_when_ocr_is_unavailable() -> None:
    selected, fallback = select_strategy(generate_page_strategies(_page("IMAGE_ONLY", 0, image_count=1), Capabilities(False, False, False)))

    assert selected.strategy_id == "quarantine"
    assert fallback is None


def test_scanned_page_selects_ocr_when_capability_appears() -> None:
    selected, fallback = select_strategy(generate_page_strategies(_page("IMAGE_ONLY", 0, image_count=1), Capabilities(True, False, False)))

    assert selected.strategy_id == "ocr_page"
    assert fallback is not None and fallback.strategy_id == "quarantine"


def test_poor_native_page_does_not_repeat_failed_extraction_without_fallback() -> None:
    selected, _ = select_strategy(generate_page_strategies(_page("NATIVE_TEXT_POOR", quality=25), Capabilities(False, False, False)))

    assert selected.strategy_id == "quarantine"


def test_table_strategy_changes_when_extractor_is_available() -> None:
    selected, _ = select_strategy(generate_page_strategies(_page("TABLE_HEAVY", table=True), Capabilities(False, True, False)))

    assert selected.strategy_id == "table_structured"


def test_query_plan_avoids_graph_without_graph_evidence() -> None:
    plan = plan_query("How is X related to Y?", graph_state="GRAPH_NOT_NEEDED")

    assert "GRAPH_TRAVERSAL" not in plan["plans_considered"]
    assert plan["selected"] == "DENSE"
