"""Shared guarded fixtures for Phase 08 acceptance E2E tests.

The module loads only the private, ignored acceptance environment.  Every
database fixture re-checks the database name and sentinel before returning so
these tests cannot silently fall back to the operational database.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import httpx
import pytest
from psycopg import connect

ROOT = Path(__file__).resolve().parents[2]
ACCEPTANCE_DATABASE = "portproject_acceptance"
OPERATIONAL_DATABASE = "portproject"
API_BASE_URL = os.environ.get("PHASE08_API_BASE_URL", "http://127.0.0.1:8016")


def _read_acceptance_env() -> dict[str, str]:
    path = ROOT / ".env.acceptance"
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


ACCEPTANCE_ENV = _read_acceptance_env()
HAS_ACCEPTANCE_FILE = bool(ACCEPTANCE_ENV)
ACCEPTANCE_ENABLED = (
    HAS_ACCEPTANCE_FILE
    and os.environ.get("PORTPROJECT_RAG_RUN_ACCEPTANCE_TESTS") == "1"
    and ACCEPTANCE_ENV.get("PORTPROJECT_RAG_ACCEPTANCE") == "1"
    and ACCEPTANCE_ENV.get("PORTPROJECT_RAG_ACCEPTANCE_DATABASE") == ACCEPTANCE_DATABASE
    and ACCEPTANCE_ENV.get("PORTPROJECT_RAG_DATABASE_URL", "").rstrip("/").rsplit("/", 1)[-1]
    == ACCEPTANCE_DATABASE
)

pytestmark = pytest.mark.skipif(
    not ACCEPTANCE_ENABLED,
    reason="Acceptance tests are opt-in; run scripts/load_acceptance_env.ps1 first.",
)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Keep acceptance tests out of a plain project-wide run.

    ``pytestmark`` in a conftest is not guaranteed to mark sibling modules in
    every pytest collection mode, so apply the opt-in gate explicitly.
    """
    if ACCEPTANCE_ENABLED:
        return
    skip = pytest.mark.skip(reason="Acceptance tests are opt-in; run scripts/load_acceptance_env.ps1 first.")
    acceptance_root = (ROOT / "tests" / "acceptance").resolve()
    for item in items:
        try:
            path = Path(str(item.fspath)).resolve()
        except (AttributeError, OSError):
            continue
        if acceptance_root in path.parents:
            item.add_marker(skip)


def _dsn() -> str:
    if not ACCEPTANCE_ENABLED:
        raise RuntimeError("Phase 08 acceptance configuration is invalid; refusing to run.")
    return ACCEPTANCE_ENV["PORTPROJECT_RAG_DATABASE_URL"]


def _assert_acceptance_identity(cursor: Any) -> None:
    cursor.execute("SELECT current_database()")
    current_database = cursor.fetchone()[0]
    if current_database != ACCEPTANCE_DATABASE or current_database == OPERATIONAL_DATABASE:
        raise RuntimeError(f"Acceptance safety refusal: current_database={current_database!r}")
    cursor.execute(
        "SELECT environment, database_name, fixture_version "
        "FROM public.acceptance_environment WHERE fixture_id=1"
    )
    if cursor.fetchone() != ("acceptance", ACCEPTANCE_DATABASE, 1):
        raise RuntimeError("Acceptance safety refusal: acceptance/1 sentinel is missing or invalid")


@pytest.fixture(scope="session")
def acceptance_guard() -> str:
    dsn = _dsn()
    with connect(dsn) as connection, connection.cursor() as cursor:
        _assert_acceptance_identity(cursor)
    tender_path = (ROOT / "tests" / "runtime" / "tender" / "tender_workflows.json").resolve()
    operational_tender = (ROOT / "src" / "portproject_rag" / "tender_workflow" / "data" / "tender_workflows.json").resolve()
    if operational_tender == tender_path or operational_tender in tender_path.parents:
        raise RuntimeError("Acceptance safety refusal: tender path is operational")
    return dsn


@pytest.fixture(scope="session")
def credentials(acceptance_guard: str) -> dict[str, str]:
    path = ROOT / "tests" / "runtime" / "acceptance" / "credentials.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {"DO_TEST", "NO_TEST", "HO_TEST", "TENANT_TEST"}
    if not required.issubset(payload):
        raise RuntimeError("Acceptance credentials fixture is incomplete")
    return {key: str(payload[key]) for key in required}


@pytest.fixture
def client(acceptance_guard: str) -> httpx.Client:
    with httpx.Client(base_url=API_BASE_URL, timeout=180, follow_redirects=False) as http_client:
        yield http_client


def login(http_client: httpx.Client, username: str, password: str, role: str = "authority") -> httpx.Response:
    path = "/api/authority/login" if role == "authority" else "/tenant/api/auth/login"
    response = http_client.post(path, json={"username": username, "password": password})
    if response.status_code != 200:
        raise AssertionError(f"login failed for {username}: {response.status_code} {response.text}")
    return response


def db_snapshot(dsn: str) -> dict[str, int | str]:
    with connect(dsn) as connection, connection.cursor() as cursor:
        _assert_acceptance_identity(cursor)
        snapshot: dict[str, int | str] = {}
        cursor.execute("SELECT current_database()")
        snapshot["database"] = cursor.fetchone()[0]
        for name, query in {
            "chat_sessions": "SELECT COUNT(*) FROM rag.chat_session",
            "chat_messages": "SELECT COUNT(*) FROM rag.chat_message",
            "audit_events": "SELECT COUNT(*) FROM rag.audit_event",
            "agenda_versions": "SELECT COUNT(*) FROM rag.agenda_version",
        }.items():
            cursor.execute(query)
            snapshot[name] = int(cursor.fetchone()[0])
        return snapshot


def session_row(dsn: str, cookie: str) -> tuple[Any, ...] | None:
    token_hash = hashlib.sha256(cookie.encode("utf-8")).hexdigest()
    with connect(dsn) as connection, connection.cursor() as cursor:
        _assert_acceptance_identity(cursor)
        cursor.execute(
            "SELECT principal_id, username, role, expires_at > now() "
            "FROM rag.user_session WHERE token_hash=%s",
            (token_hash,),
        )
        return cursor.fetchone()
