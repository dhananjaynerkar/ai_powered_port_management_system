"""Phase 10 billing API, provenance, mutation, and isolation acceptance tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx
from conftest import API_BASE_URL, login
from psycopg import connect

COMPLETE_TENANCY = "ACCEPTANCE-TENANCY-001"
INCOMPLETE_TENANCY = "ACCEPTANCE-TENANCY-002"


def _gate(dsn: str) -> None:
    with connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT current_database()")
        assert cursor.fetchone()[0] == "portproject_acceptance"
        cursor.execute(
            "SELECT environment, database_name, fixture_version "
            "FROM public.acceptance_environment WHERE fixture_id=1"
        )
        assert cursor.fetchone() == ("acceptance", "portproject_acceptance", 1)


def _source_snapshot(dsn: str) -> dict[str, Any]:
    _gate(dsn)
    with connect(dsn) as connection, connection.cursor() as cursor:
        snapshot: dict[str, Any] = {}
        for name, query in {
            "customers": "SELECT COUNT(*), COALESCE(SUM(customerid), 0) FROM public.mcustomer",
            "bills": "SELECT COUNT(*), COALESCE(SUM(amount), 0), COALESCE(SUM(cgst), 0), COALESCE(SUM(sgst), 0) FROM public.tgeneralbill",
            "plots": "SELECT COUNT(*), COALESCE(SUM(area), 0) FROM public.plot",
            "rates": "SELECT COUNT(*), COALESCE(SUM(gen_tax), 0), COALESCE(SUM(wtr_tax), 0), COALESCE(SUM(sewr_tax), 0) FROM public.m_tax_rates",
        }.items():
            cursor.execute(query)
            snapshot[name] = tuple(cursor.fetchone())
        return snapshot


def _complete_payload(prefill: dict[str, Any], *, target_month: int = 9) -> dict[str, Any]:
    fields = prefill["fields"]
    return {
        "tenancy_id": COMPLETE_TENANCY,
        "customer_id": prefill["customer_id"],
        "target_year": fields["target_year"],
        "target_month": target_month,
        "present_year": fields["present_year"],
        "present_month": fields["present_month"],
        "present_amount": fields["present_amount"],
        "present_cgst": fields["present_cgst"],
        "present_sgst": fields["present_sgst"],
        "area": fields["area"],
        "billing_frequency": fields["billing_frequency"],
        "bill_type": fields["bill_type"],
        "structure_type": fields["structure_type"],
        "rates": prefill["rates"],
        "allocated_rate_keys": prefill["allocated_rate_keys"],
    }


def test_complete_billing_path_provenance_chat_audit_and_source_immutability(
    acceptance_guard: str, credentials: dict[str, str], client: httpx.Client
) -> None:
    before = _source_snapshot(acceptance_guard)
    login(client, "do_test", credentials["DO_TEST"])
    status = client.get("/api/v1/billing/status")
    assert status.status_code == 200
    status_payload = status.json()
    assert status_payload["model"] == "billing_xgb_model.json"
    assert status_payload["manifest"] == "billing_model_manifest.json"
    assert ":\\" not in str(status_payload)
    rules = client.get("/api/v1/billing/rules")
    tenancies = client.get("/api/v1/billing/tenancies")
    assert rules.status_code == 200
    assert tenancies.status_code == 200
    assert any(item["tenancy_id"] == COMPLETE_TENANCY for item in tenancies.json()["options"])

    prefill_response = client.get(f"/api/v1/billing/tenancies/{COMPLETE_TENANCY}/prefill")
    assert prefill_response.status_code == 200
    prefill = prefill_response.json()
    assert prefill["customer_id"] == "30001"
    assert prefill["fields"]["area"] == 1000.0
    assert prefill["sources"]["area"].startswith("public.plot.area")
    assert prefill["rate_sources"]["general"] == "selected-tenancy CSV override"
    assert prefill["rate_sources"]["sbt"] == "target-period PostgreSQL master rate"

    response = client.post("/api/v1/billing/predict", json=_complete_payload(prefill))
    assert response.status_code == 200, response.text
    payload = response.json()
    prediction = payload["prediction"]
    assert payload["success"] is True
    assert prediction["model_source"] == "xgboost-json"
    assert ":\\" not in str(prediction)
    assert prediction["monthly_base_amount"] > 0
    assert prediction["calculation_intermediates"]["annual_amount"] > 0
    assert prediction["formula_schedule"] == "Post taxes · March / September"
    tree = next(item for item in prediction["tax_items"] if item["label"] == "Tree cess")
    # The acceptance fixture supplies Tree Cess as 0.5%, not 50%.
    assert tree["components"]["annual_amount_part"] < prediction["monthly_base_amount"]
    assert payload["chat_session_id"]

    after = _source_snapshot(acceptance_guard)
    assert after == before
    with connect(acceptance_guard) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM rag.chat_message WHERE chat_session_id=%s",
            (payload["chat_session_id"],),
        )
        assert cursor.fetchone()[0] == 2
        cursor.execute(
            "SELECT event_type, metadata->>'tenancy_id' FROM rag.audit_event "
            "WHERE event_type='billing_forecast' AND principal_id='authority:10001' "
            "ORDER BY created_at DESC LIMIT 1"
        )
        event = cursor.fetchone()
        assert event == ("billing_forecast", COMPLETE_TENANCY)


def test_incomplete_and_invalid_billing_requests_do_not_write(
    acceptance_guard: str, credentials: dict[str, str], client: httpx.Client
) -> None:
    login(client, "do_test", credentials["DO_TEST"])
    assert client.get(f"/api/v1/billing/tenancies/{INCOMPLETE_TENANCY}/prefill").status_code == 404
    before = _source_snapshot(acceptance_guard)
    with connect(acceptance_guard) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM rag.chat_session")
        chat_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM rag.audit_event WHERE event_type='billing_forecast'")
        audit_count = cursor.fetchone()[0]

    invalid = {
        "customer_id": "30001",
        "target_year": 2027,
        "target_month": 12,
        "present_year": 2026,
        "present_month": 8,
        "present_amount": -1,
        "present_cgst": 0,
        "present_sgst": 0,
        "area": 1000,
        "billing_frequency": "monthly",
        "bill_type": "general",
        "structure_type": "other",
    }
    assert client.post("/api/v1/billing/predict", json=invalid).status_code == 422
    invalid["present_amount"] = 1000
    invalid["structure_type"] = "not-a-real-structure"
    assert client.post("/api/v1/billing/predict", json=invalid).status_code == 422

    after = _source_snapshot(acceptance_guard)
    assert after == before
    with connect(acceptance_guard) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM rag.chat_session")
        assert cursor.fetchone()[0] == chat_count
        cursor.execute("SELECT COUNT(*) FROM rag.audit_event WHERE event_type='billing_forecast'")
        assert cursor.fetchone()[0] == audit_count


def test_billing_authorization_and_unauthenticated_boundary(
    acceptance_guard: str, credentials: dict[str, str]
) -> None:
    with httpx.Client(base_url=API_BASE_URL, timeout=120) as anonymous:
        assert anonymous.get("/api/v1/billing/status").status_code == 401

    with httpx.Client(base_url=API_BASE_URL, timeout=120) as tenant:
        login(tenant, "tenant_test", credentials["TENANT_TEST"], "tenant")
        for path in (
            "/api/v1/billing/status",
            "/api/v1/billing/rules",
            "/api/v1/billing/tenancies",
            f"/api/v1/billing/tenancies/{COMPLETE_TENANCY}/prefill",
        ):
            assert tenant.get(path).status_code == 403
        assert tenant.post("/api/v1/billing/predict", json={}).status_code == 403


def test_concurrent_manual_predictions_keep_context_and_chat_principals_isolated(
    acceptance_guard: str, credentials: dict[str, str]
) -> None:
    def run(username: str, password_key: str, customer_id: str, amount: float) -> dict[str, Any]:
        with httpx.Client(base_url=API_BASE_URL, timeout=120) as local:
            login(local, username, credentials[password_key])
            payload = {
                "customer_id": customer_id,
                "target_year": 2026,
                "target_month": 9,
                "present_year": 2026,
                "present_month": 8,
                "present_amount": amount,
                "present_cgst": 0,
                "present_sgst": 0,
                "area": 100,
                "billing_frequency": "monthly",
                "bill_type": "general",
                "structure_type": "other",
                "rates": {},
            }
            response = local.post("/api/v1/billing/predict", json=payload)
            assert response.status_code == 200, response.text
            return response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.map(
            lambda args: run(*args),
            (("do_test", "DO_TEST", "CONCURRENT-A", 1000), ("no_test", "NO_TEST", "CONCURRENT-B", 2000)),
        )

    assert first["chat_session_id"] != second["chat_session_id"]
    assert first["prediction"]["request"]["customer_id"] == "CONCURRENT-A"
    assert second["prediction"]["request"]["customer_id"] == "CONCURRENT-B"
    with connect(acceptance_guard) as connection, connection.cursor() as cursor:
        for payload, principal in ((first, "authority:10001"), (second, "authority:10002")):
            cursor.execute(
                "SELECT principal_id FROM rag.chat_session WHERE chat_session_id=%s",
                (payload["chat_session_id"],),
            )
            assert cursor.fetchone()[0] == principal
