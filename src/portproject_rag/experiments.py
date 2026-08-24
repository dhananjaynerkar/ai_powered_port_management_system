from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .inspection import PageProfile, PdfProfile
from .table_processing import extract_native_tables


def run_table_experiment(profiles: list[PdfProfile], output: Path, max_pages: int = 40) -> dict[str, int]:
    """Measure table extractor coverage on triaged pages before trusting it at ingestion."""
    observations = []
    total_signalled_pages = sum(
        (item if isinstance(item, PageProfile) else PageProfile(**item)).table_signal
        for profile in profiles for item in profile.page_profiles
    )
    for profile in profiles:
        for item in profile.page_profiles:
            page = item if isinstance(item, PageProfile) else PageProfile(**item)
            if not page.table_signal or page.classification == "IMAGE_ONLY":
                continue
            if len(observations) >= max_pages:
                break
            result = extract_native_tables(Path(profile.path), page.page_number)
            observations.append({"document": profile.filename, "page_number": page.page_number, "classification": page.classification, "table_count": result.table_count, "row_count": result.row_count, "maximum_columns": result.maximum_columns, "representation": result.representation, "error": result.error})
        if len(observations) >= max_pages:
            break
    summary = {"sampled_signalled_pages": len(observations), "total_signalled_pages": total_signalled_pages, "pages_with_structured_tables": sum(item["table_count"] > 0 for item in observations), "rows": sum(item["row_count"] for item in observations), "errors": sum(item["error"] is not None for item in observations), "budgeted": len(observations) < total_signalled_pages}
    output.mkdir(parents=True, exist_ok=True)
    (output / "table-experiment.json").write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "summary": summary, "pages": observations}, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
