from __future__ import annotations

import importlib.util
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class OcrCapability:
    executable: str | None
    languages: tuple[str, ...]

    @property
    def available(self) -> bool:
        return self.executable is not None and importlib.util.find_spec("pytesseract") is not None


def discover_ocr() -> OcrCapability:
    candidates = [shutil.which("tesseract"), r"C:\Program Files\Tesseract-OCR\tesseract.exe"]
    executable = next((item for item in candidates if item and Path(item).is_file()), None)
    if not executable:
        return OcrCapability(None, ())
    result = subprocess.run([executable, "--list-langs"], capture_output=True, text=True, check=False, timeout=15)
    languages = tuple(line.strip() for line in result.stdout.splitlines() if line.strip() and not line.startswith("List of"))
    return OcrCapability(executable, languages)
