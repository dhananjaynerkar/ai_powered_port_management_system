from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .inspection import PageProfile, PdfProfile
from .strategy import Capabilities, StrategyDecision, decide_document


def write_final_ingestion_report(profiles: list[PdfProfile], output: Path, database_status: str) -> None:
    """Write a reproducible corpus-run report even when database configuration is absent."""
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for profile in profiles:
        pages = [item if isinstance(item, PageProfile) else PageProfile(**item) for item in profile.page_profiles]
        rows.append({
            "filename": profile.filename, "source_path": profile.path, "document_classification": profile.classification,
            "pages": profile.pages, "native_pages": sum(p.extraction_path == "NATIVE_PYMUPDF" for p in pages),
            "ocr_required_pages": sum(p.extraction_path == "OCR_REQUIRED" for p in pages),
            "table_pages": sum(p.table_signal for p in pages), "failed_pages": sum(p.classification == "UNKNOWN" for p in pages),
            "extraction_quality": profile.extraction_quality, "duplicate_of": profile.duplicate_of,
            "ingestion_status": "NOT_RUN_DATABASE_CONFIGURATION_MISSING" if database_status == "MISSING" else "PENDING",
            "chunks": None, "embeddings": None, "processing_time_ms": None, "errors": ";".join(profile.issues),
        })
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "database_status": database_status, "documents": rows}
    (output / "final-ingestion-report.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    with (output / "final-ingestion-report.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]) if rows else ["filename"])
        writer.writeheader()
        writer.writerows(rows)


def write_strategy_decisions(profiles: list[PdfProfile], output: Path, filename_suffix: str = "") -> tuple[int, Capabilities]:
    """Persist every selection so reprocessing can reassess it against new capabilities."""
    output.mkdir(parents=True, exist_ok=True)
    capabilities = Capabilities.detect()
    decisions: list[StrategyDecision] = []
    for profile in profiles:
        profile.page_profiles = [item if isinstance(item, PageProfile) else PageProfile(**item) for item in profile.page_profiles]
        decisions.extend(decide_document(profile, capabilities))
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "capabilities": asdict(capabilities),
        "decisions": [asdict(item) for item in decisions],
    }
    (output / f"strategy-decisions{filename_suffix}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    rows = [{
        "document": item.document, "page_number": item.page_number, "observed_classification": item.observed_classification,
        "selected_strategy": item.selected.strategy_id, "selected_extraction": item.selected.extraction_method,
        "fallback_strategy": item.fallback.strategy_id if item.fallback else None,
        "candidate_count": len(item.candidates), "rationale": item.selected.rationale,
        "expected_quality": item.selected.expected_quality, "confidence": item.selected.confidence,
    } for item in decisions]
    with (output / f"strategy-decisions{filename_suffix}.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]) if rows else ["document"])
        writer.writeheader()
        writer.writerows(rows)
    return len(decisions), capabilities
