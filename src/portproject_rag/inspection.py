from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pymupdf

from .quality import page_classification, score_page_text

MIN_USEFUL_PAGE_CHARS = 32


@dataclass(slots=True)
class PageProfile:
    page_number: int
    classification: str
    extraction_path: str
    extraction_quality_score: int
    quality_band: str
    character_count: int
    word_count: int
    printable_ratio: float
    whitespace_ratio: float
    malformed_character_count: int
    repeated_character_runs: int
    image_count: int
    table_signal: bool


@dataclass(slots=True)
class PdfProfile:
    path: str
    filename: str
    sha256: str
    file_size_bytes: int
    pages: int | None
    pdf_version: str | None
    title: str | None
    author: str | None
    producer: str | None
    created_at: str | None
    modified_at: str | None
    extracted_characters: int
    average_characters_per_page: float
    text_page_ratio: float
    image_only_page_ratio: float
    image_count: int
    font_count: int
    landscape_page_ratio: float
    repeated_header_footer: bool
    table_signal_pages: int
    classification: str
    extraction_strategy: str
    chunking_strategy: str
    extraction_quality: int
    issues: list[str]
    page_profiles: list[PageProfile] = field(default_factory=list)
    duplicate_of: str | None = None


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _metadata_date(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def _classify(text_ratio: float, image_ratio: float, quality: int, table_pages: int, pages: int) -> tuple[str, str, str]:
    if text_ratio == 0 and image_ratio > 0:
        return "SCANNED", "OCR_REQUIRED", "PAGE_AWARE_AFTER_OCR"
    if image_ratio > 0 and text_ratio > 0:
        return "HYBRID", "NATIVE_WITH_PAGE_OCR_REVIEW", "SECTION_AND_PAGE_AWARE"
    if quality < 45:
        return "TEXT_WITH_POOR_EXTRACTION", "ADVANCED_PARSER_REVIEW", "PAGE_AWARE"
    if pages and table_pages / pages >= 0.35:
        return "TABLE_HEAVY", "NATIVE_WITH_TABLE_REVIEW", "SECTION_AND_TABLE_AWARE"
    return "TEXT_NATIVE", "NATIVE_PYMUPDF", "SECTION_AWARE"


def profile_pdf(path: Path) -> PdfProfile:
    """Inspect one PDF without changing the source file."""
    sha256 = _hash_file(path)
    stat = path.stat()
    issues: list[str] = []
    try:
        document = pymupdf.open(path)
    except Exception as exc:  # PyMuPDF provides different exception classes by version.
        return PdfProfile(
            path=str(path.resolve()), filename=path.name, sha256=sha256, file_size_bytes=stat.st_size,
            pages=None, pdf_version=None, title=None, author=None, producer=None, created_at=None,
            modified_at=None, extracted_characters=0, average_characters_per_page=0.0,
            text_page_ratio=0.0, image_only_page_ratio=0.0, image_count=0, font_count=0,
            landscape_page_ratio=0.0, repeated_header_footer=False, table_signal_pages=0,
            classification="CORRUPTED_OR_UNREADABLE", extraction_strategy="MANUAL_REVIEW",
            chunking_strategy="NONE", extraction_quality=0, issues=[f"open_failed:{type(exc).__name__}"],
        )

    with document:
        metadata = document.metadata or {}
        page_count = document.page_count
        texts: list[str] = []
        image_count = font_count = text_pages = image_only_pages = landscape_pages = table_pages = 0
        edge_lines: list[str] = []
        page_profiles: list[PageProfile] = []
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            texts.append(text)
            images = page.get_images(full=True)
            image_count += len(images)
            font_count += len(page.get_fonts(full=True))
            table_signal = len(page.get_drawings()) >= 12 or bool(re.search(r"\btable\b", text, flags=re.IGNORECASE))
            page_quality = score_page_text(text, bool(images))
            page_kind = page_classification(page_quality, bool(images), table_signal)
            page_profiles.append(PageProfile(
                page_number=page_number, classification=page_kind,
                extraction_path="NATIVE_PYMUPDF" if page_kind in {"NATIVE_TEXT_USABLE", "TABLE_HEAVY", "MIXED"} else "OCR_REQUIRED",
                extraction_quality_score=page_quality.score, quality_band=page_quality.band,
                character_count=page_quality.character_count, word_count=page_quality.word_count,
                printable_ratio=round(page_quality.printable_ratio, 4), whitespace_ratio=round(page_quality.whitespace_ratio, 4),
                malformed_character_count=page_quality.malformed_character_count, repeated_character_runs=page_quality.repeated_character_runs,
                image_count=len(images), table_signal=table_signal,
            ))
            if len(text) >= MIN_USEFUL_PAGE_CHARS:
                text_pages += 1
            if len(text) < MIN_USEFUL_PAGE_CHARS and images:
                image_only_pages += 1
            if page.rect.width > page.rect.height:
                landscape_pages += 1
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            if lines:
                edge_lines.extend((f"H:{lines[0]}", f"F:{lines[-1]}"))
            if table_signal:
                table_pages += 1

    total_text = sum(len(text) for text in texts)
    average = total_text / page_count if page_count else 0.0
    text_ratio = text_pages / page_count if page_count else 0.0
    image_ratio = image_only_pages / page_count if page_count else 0.0
    repeated = any(count >= max(3, round(page_count * 0.6)) for count in Counter(edge_lines).values())
    garbled = sum(text.count("\ufffd") for text in texts)
    quality = round(sum(item.extraction_quality_score for item in page_profiles) / page_count) if page_count else 0
    if repeated:
        issues.append("repeated_header_or_footer_detected")
    if image_ratio:
        issues.append("image_only_pages_detected")
    if garbled:
        issues.append("replacement_characters_detected")
    classification, extraction, chunking = _classify(text_ratio, image_ratio, quality, table_pages, page_count)
    return PdfProfile(
        path=str(path.resolve()), filename=path.name, sha256=sha256, file_size_bytes=stat.st_size,
        pages=page_count, pdf_version=metadata.get("format"), title=metadata.get("title") or None,
        author=metadata.get("author") or None, producer=metadata.get("producer") or None,
        created_at=_metadata_date(metadata.get("creationDate")), modified_at=_metadata_date(metadata.get("modDate")),
        extracted_characters=total_text, average_characters_per_page=round(average, 2),
        text_page_ratio=round(text_ratio, 4), image_only_page_ratio=round(image_ratio, 4),
        image_count=image_count, font_count=font_count, landscape_page_ratio=round(landscape_pages / page_count, 4) if page_count else 0.0,
        repeated_header_footer=repeated, table_signal_pages=table_pages, classification=classification,
        extraction_strategy=extraction, chunking_strategy=chunking, extraction_quality=quality, issues=issues,
        page_profiles=page_profiles,
    )


def inspect_corpus(root: Path, output: Path) -> list[PdfProfile]:
    resolved_root = root.resolve()
    generated_workspace = resolved_root / "portproject_rag"
    pdf_paths = sorted(
        path for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() == ".pdf"
        and not path.resolve().is_relative_to(generated_workspace)
    )
    output.mkdir(parents=True, exist_ok=True)
    profiles = [profile_pdf(path) for path in pdf_paths]
    seen: dict[str, PdfProfile] = {}
    for profile in profiles:
        original = seen.get(profile.sha256)
        if original:
            profile.duplicate_of = original.path
            profile.classification = "DUPLICATE"
            profile.extraction_strategy = "SKIP_DUPLICATE"
            profile.chunking_strategy = "NONE"
        else:
            seen[profile.sha256] = profile
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "root": str(root.resolve()), "documents": [asdict(item) for item in profiles]}
    (output / "corpus.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    with (output / "corpus.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(asdict(profiles[0]).keys()) if profiles else ["path"])
        writer.writeheader()
        writer.writerows(asdict(item) for item in profiles)
    return profiles
