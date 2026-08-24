from pathlib import Path

import pymupdf

from portproject_rag.ingestion import _json_safe
from portproject_rag.inspection import inspect_corpus
from portproject_rag.quality import page_classification, score_page_text


def test_inspection_identifies_exact_duplicate(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "A sufficiently long policy clause with enough text for native extraction. " * 20)
    document.save(source)
    document.close()
    duplicate = tmp_path / "duplicate.pdf"
    duplicate.write_bytes(source.read_bytes())

    profiles = inspect_corpus(tmp_path, tmp_path / "report")

    assert len(profiles) == 2
    assert sum(profile.classification == "DUPLICATE" for profile in profiles) == 1
    assert sum(profile.duplicate_of is None for profile in profiles) == 1
    assert (tmp_path / "report" / "corpus.json").exists()


def test_page_quality_requires_ocr_for_empty_image_page() -> None:
    quality = score_page_text("", has_images=True)

    assert quality.score == 0
    assert quality.band == "OCR_REQUIRED"
    assert page_classification(quality, has_images=True, table_signal=False) == "IMAGE_ONLY"


def test_page_quality_accepts_printable_native_text() -> None:
    quality = score_page_text("policy clause " * 100, has_images=False)

    assert quality.band == "HIGH"
    assert page_classification(quality, has_images=False, table_signal=False) == "NATIVE_TEXT_USABLE"


def test_json_metadata_removes_postgres_incompatible_nul_only() -> None:
    assert _json_safe({"producer": "scanner\x00", "items": ["ok\x00"]}) == {"producer": "scanner", "items": ["ok"]}
