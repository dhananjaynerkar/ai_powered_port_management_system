"""Local page OCR with measurable confidence; no cloud fallback."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image

from .capabilities import discover_ocr
from .quality import score_page_text


@dataclass(frozen=True, slots=True)
class OcrResult:
    text: str
    mean_confidence: float | None
    quality_score: int
    error: str | None


def ocr_page(source: Path, page_number: int, language: str = "eng", dpi: int = 220) -> OcrResult:
    capability = discover_ocr()
    if not capability.available:
        return OcrResult("", None, 0, "OCR_UNAVAILABLE")
    if language not in capability.languages:
        return OcrResult("", None, 0, f"OCR_LANGUAGE_UNAVAILABLE:{language}")
    pytesseract.pytesseract.tesseract_cmd = capability.executable
    with pymupdf.open(source) as document:
        page = document[page_number - 1]
        pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)
    text = " ".join(item.strip() for item in data["text"] if item.strip())
    confidences = [float(item) for item in data["conf"] if item not in {"-1", -1}]
    quality = score_page_text(text, has_images=True)
    return OcrResult(text, round(sum(confidences) / len(confidences), 2) if confidences else None, quality.score, None)
