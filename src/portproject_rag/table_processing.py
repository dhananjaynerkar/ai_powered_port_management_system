"""Measured native-table extraction; absence of a table is a valid outcome."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pdfplumber


@dataclass(frozen=True, slots=True)
class TableResult:
    table_count: int
    row_count: int
    maximum_columns: int
    representation: str
    error: str | None


def extract_native_tables(source: Path, page_number: int) -> TableResult:
    try:
        with pdfplumber.open(source) as document:
            tables = document.pages[page_number - 1].extract_tables()
    except Exception as error:
        return TableResult(0, 0, 0, "QUARANTINE", type(error).__name__)
    nonempty = [table for table in tables if table]
    rows = sum(len(table) for table in nonempty)
    columns = max((len(row) for table in nonempty for row in table if row), default=0)
    if not nonempty:
        return TableResult(0, 0, 0, "RAW_PAGE_CONTEXT", None)
    representation = "TABLE_ROW_AND_CONTEXT" if rows >= 2 and columns >= 2 else "RAW_PAGE_CONTEXT"
    return TableResult(len(nonempty), rows, columns, representation, None)
