"""Pure unit tests for the acceptance fixture's destructive-operation guards."""

from pathlib import Path

import pytest

from scripts import acceptance_fixture


def test_acceptance_dsn_refuses_operational_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "PORTPROJECT_RAG_DATABASE_URL",
        "postgresql://acceptance_user:secret@127.0.0.1:5432/portproject",
    )

    with pytest.raises(acceptance_fixture.AcceptanceSafetyError, match="not portproject_acceptance"):
        acceptance_fixture._acceptance_dsn()


def test_acceptance_dsn_accepts_only_approved_database(monkeypatch: pytest.MonkeyPatch) -> None:
    dsn = "postgresql://acceptance_user:secret@127.0.0.1:5432/portproject_acceptance"
    monkeypatch.setenv("PORTPROJECT_RAG_DATABASE_URL", dsn)

    assert acceptance_fixture._acceptance_dsn() == dsn


def test_tender_guard_refuses_operational_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    operational = acceptance_fixture.ROOT / "src" / "portproject_rag" / "tender_workflow" / "data" / "tender_workflows.json"
    monkeypatch.setenv("PORTPROJECT_RAG_TENDER_STORAGE_PATH", str(operational))

    with pytest.raises(acceptance_fixture.AcceptanceSafetyError, match="operational tender storage"):
        acceptance_fixture._safe_tender_path()


def test_tender_guard_requires_runtime_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PORTPROJECT_RAG_TENDER_STORAGE_PATH", str(tmp_path / "tender_workflows.json"))

    with pytest.raises(acceptance_fixture.AcceptanceSafetyError, match="below tests/runtime"):
        acceptance_fixture._safe_tender_path()
