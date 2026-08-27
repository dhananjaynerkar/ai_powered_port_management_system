"""Read-only checks for the isolated acceptance fixture.

These checks are intentionally skipped during the normal suite. They become
active only when the caller explicitly supplies the acceptance marker and DSN;
the fixture script itself still verifies the database sentinel before reading.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from psycopg import connect

ACCEPTANCE_ENABLED = (
    os.environ.get("PORTPROJECT_RAG_ACCEPTANCE") == "1"
    and os.environ.get("PORTPROJECT_RAG_ACCEPTANCE_DATABASE") == "portproject_acceptance"
    and os.environ.get("PORTPROJECT_RAG_DATABASE_URL", "").rstrip("/").rsplit("/", 1)[-1]
    == "portproject_acceptance"
)
pytestmark = pytest.mark.skipif(not ACCEPTANCE_ENABLED, reason="Acceptance fixture is not enabled")


def _dsn() -> str:
    return os.environ["PORTPROJECT_RAG_DATABASE_URL"]


def test_acceptance_identity_and_sentinel() -> None:
    with connect(_dsn()) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT current_database()")
        assert cursor.fetchone()[0] == "portproject_acceptance"
        cursor.execute(
            "SELECT environment, database_name, fixture_version "
            "FROM public.acceptance_environment WHERE fixture_id=1"
        )
        assert cursor.fetchone() == ("acceptance", "portproject_acceptance", 1)


def test_acceptance_principals_acl_and_conversation_states() -> None:
    with connect(_dsn()) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM public.admin_users WHERE user_name IN ('do_test','no_test','ho_test')")
        assert cursor.fetchone()[0] == 3
        cursor.execute("SELECT COUNT(*) FROM public.applicant_registration WHERE username IN ('tenant_test','tenant_second')")
        assert cursor.fetchone()[0] == 2
        cursor.execute("SELECT COUNT(*) FROM public.admin_users WHERE admin_id=10001")
        assert cursor.fetchone()[0] == 1
        cursor.execute("SELECT COUNT(*) FROM public.applicant_registration WHERE applicant_id=20001")
        assert cursor.fetchone()[0] == 1
        cursor.execute("SELECT COUNT(*) FROM rag.document WHERE ingestion_state='indexed'")
        assert cursor.fetchone()[0] == 4
        cursor.execute("SELECT COUNT(*) FROM rag.chunk WHERE acl_roles @> ARRAY['authority']::text[]")
        assert cursor.fetchone()[0] == 2
        cursor.execute("SELECT title FROM rag.chat_session ORDER BY title")
        titles = {row[0] for row in cursor.fetchall()}
        assert {"private_empty", "private_normal", "private_cited", "workflow_linked"}.issubset(titles)
        cursor.execute(
            "SELECT COUNT(*) FROM rag.chat_message m "
            "JOIN rag.chat_session s ON s.chat_session_id=m.chat_session_id "
            "WHERE s.title='private_empty'"
        )
        assert cursor.fetchone()[0] == 0


def test_acceptance_workflow_billing_and_tender_files() -> None:
    root = Path(__file__).resolve().parents[1]
    tender_path = root / "tests" / "runtime" / "tender" / "tender_workflows.json"
    billing_path = root / "tests" / "runtime" / "acceptance" / "billing_tax_mapping.csv"
    assert tender_path.is_file()
    tender_records = json.loads(tender_path.read_text(encoding="utf-8"))
    assert len(tender_records) == 1
    assert tender_records[0]["status"] == "LAC_DRAFT"
    assert billing_path.is_file()
    with connect(_dsn()) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(DISTINCT state) FROM rag.agenda")
        assert cursor.fetchone()[0] >= 6
        cursor.execute("SELECT COUNT(*) FROM public.mcustomer WHERE customercode='ACCEPTANCE-TENANCY-001'")
        assert cursor.fetchone()[0] == 1
        cursor.execute("SELECT COUNT(*) FROM public.mcustomer WHERE customercode='BILLING_INCOMPLETE'")
        assert cursor.fetchone()[0] == 0
