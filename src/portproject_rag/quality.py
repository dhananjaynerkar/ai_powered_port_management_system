"""Deterministic page-quality signals used before choosing an extraction path."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PageQuality:
    character_count: int
    word_count: int
    printable_ratio: float
    whitespace_ratio: float
    malformed_character_count: int
    repeated_character_runs: int
    score: int
    band: str


def score_page_text(text: str, has_images: bool) -> PageQuality:
    """Score extraction signals, reserving zero for a page with no usable text.

    The thresholds distinguish empty image-backed pages from sparse front matter;
    they are exposed as score bands, not a claim that extracted legal text is correct.
    """
    characters = len(text)
    words = len(text.split())
    printable = sum(character.isprintable() for character in text)
    printable_ratio = printable / characters if characters else 0.0
    whitespace_ratio = sum(character.isspace() for character in text) / characters if characters else 1.0
    malformed = text.count("\ufffd")
    repeated_runs = sum(1 for index in range(3, characters) if text[index] == text[index - 1] == text[index - 2] == text[index - 3])
    if characters == 0:
        return PageQuality(characters, words, printable_ratio, whitespace_ratio, malformed, repeated_runs, 0, "OCR_REQUIRED" if has_images else "FAILED")
    density = min(1.0, characters / 500)
    score = round(100 * (0.55 * density + 0.25 * printable_ratio + 0.20 * min(1.0, words / 80)))
    score -= min(30, malformed * 5)
    score -= min(20, repeated_runs * 2)
    score -= 15 if whitespace_ratio > 0.55 else 0
    score = max(0, min(100, score))
    band = "HIGH" if score >= 80 else "ACCEPTABLE" if score >= 55 else "POOR"
    return PageQuality(characters, words, printable_ratio, whitespace_ratio, malformed, repeated_runs, score, band)


def page_classification(quality: PageQuality, has_images: bool, table_signal: bool) -> str:
    if quality.character_count == 0:
        return "IMAGE_ONLY" if has_images else "UNKNOWN"
    if table_signal:
        return "TABLE_HEAVY"
    if quality.band == "POOR":
        return "NATIVE_TEXT_POOR"
    if has_images:
        return "MIXED"
    return "NATIVE_TEXT_USABLE"
