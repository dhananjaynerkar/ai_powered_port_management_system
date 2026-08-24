from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException
from psycopg import connect

from portproject_rag.api import app, authority_tenants
from portproject_rag.auth import PortalUser
from portproject_rag.settings import Settings


def _authority_user() -> PortalUser:
    return PortalUser(uuid4(), "tenant-table-test", "tenant-table-test", "Tenant Table Test", "authority")


def test_tenant_endpoint_returns_live_filter_options_and_25_row_pages() -> None:
    settings = Settings()
    app.state.settings = settings
    payload = authority_tenants(user=_authority_user())

    assert payload["page_size"] == 25
    assert payload["pages"] == max(1, (payload["total"] + 24) // 25)
    assert len(payload["tenants"]) <= 25
    assert payload["filters"]["statuses"]
    assert payload["filters"]["lease_types"]
    assert payload["filters"]["allotment_statuses"]
    assert payload["record_label"] == payload["tenant_terminology"]["mapping_records"]["label"]
    assert {"tenant_id", "tenancy_id"} <= payload["tenants"][0].keys()
    assert "Applicant-property mapping records" in payload["record_label"]


def test_tenant_endpoint_applies_live_lease_filter_and_clamps_page() -> None:
    settings = Settings()
    app.state.settings = settings
    with connect(settings.database_url.unicode_string()) as connection, connection.cursor() as cursor:
        cursor.execute("""SELECT tenancy_type
            FROM public.applicant_property_mapping
            WHERE NULLIF(BTRIM(tenancy_type), '') IS NOT NULL
            ORDER BY tenancy_type
            LIMIT 1""")
        lease_type = cursor.fetchone()[0]

    payload = authority_tenants(lease_type=lease_type, page=999999, page_size=25, user=_authority_user())

    assert payload["page"] == payload["pages"]
    assert all(row["tenancy_type"] == lease_type for row in payload["tenants"])


def test_tenant_endpoint_rejects_invalid_date_range() -> None:
    app.state.settings = Settings()
    with pytest.raises(HTTPException) as error:
        authority_tenants(date_from="not-a-date", user=_authority_user())
    assert error.value.status_code == 422
