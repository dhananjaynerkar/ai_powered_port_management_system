from __future__ import annotations

from psycopg import connect

from portproject_rag.api import _authority_land_metrics
from portproject_rag.settings import Settings


def test_authority_metrics_reconcile_with_live_plot_and_mapping_rows() -> None:
    """The dashboard contract must be derived from the current database state."""
    settings = Settings()
    payload = _authority_land_metrics(settings)

    with connect(settings.database_url.unicode_string()) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(area), 0) FROM public.plot")
        plot_count, plot_area = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM public.applicant_property_mapping")
        mapping_count = cursor.fetchone()[0]
        cursor.execute("""SELECT
                COUNT(DISTINCT tenant_id),
                COUNT(DISTINCT NULLIF(BTRIM(tenancy_id), '')),
                COUNT(DISTINCT ar.applicant_id),
                COUNT(*) FILTER (WHERE NULLIF(BTRIM(tenancy_id), '') IS NULL),
                COUNT(*) FILTER (WHERE ar.applicant_id IS NULL)
            FROM public.applicant_property_mapping apm
            LEFT JOIN public.applicant_registration ar ON ar.applicant_id = apm.tenant_id""")
        terminology_counts = cursor.fetchone()
        cursor.execute("""SELECT status_id, status FROM public.m_property_status
            WHERE status_id IN ('A', 'V', 'RG') ORDER BY status_id""")
        status_rows = cursor.fetchall()

    assert payload["tenancy_record_count"] == mapping_count
    assert payload["data_quality"]["mapping_records"] == mapping_count
    terminology = payload["tenant_terminology"]
    assert terminology["mapping_records"]["count"] == mapping_count
    assert terminology["applicant_ids"]["count"] == terminology_counts[0]
    assert terminology["tenancy_identifiers"]["count"] == terminology_counts[1]
    assert terminology["matched_applicant_profiles"]["count"] == terminology_counts[2]
    assert terminology["missing_tenancy_identifiers"]["count"] == terminology_counts[3]
    assert terminology["orphan_mapping_records"]["count"] == terminology_counts[4]
    assert "not a unique tenant" in terminology["mapping_records"]["definition"]
    assert "not a count of active tenancies" in terminology["tenancy_identifiers"]["definition"]
    assert sum(item["count"] for item in payload["plot_status_breakdown"]) == plot_count
    assert sum(item["area_sqm"] for item in payload["plot_status_breakdown"]) == float(plot_area)
    assert sum(item["count"] for item in payload["land_occupancy_breakdown"]) == plot_count
    assert sum(item["area_sqm"] for item in payload["land_occupancy_breakdown"]) == float(plot_area)
    assert {item["code"]: item["name"] for item in payload["plot_status_breakdown"] if item["code"] in {"A", "V", "RG"}} == dict(status_rows)
    assert payload["total_land"]["sqm"] == f"{float(plot_area):,.2f} sq.m"
    assert not {item["name"] for item in payload["plot_status_breakdown"]} & {"Occupied", "Vacant", "Pending"}
    assert {item["name"] for item in payload["land_occupancy_breakdown"]} >= {"Not vacant", "Vacant", "Registered"}
    assert "not a verified business synonym for occupied" in payload["land_occupancy_definition_source"]


def test_authority_metrics_keep_lease_and_tenant_dimensions_separate() -> None:
    settings = Settings()
    payload = _authority_land_metrics(settings)

    lease_names = {item["name"] for item in payload["lease_type_breakdown"]}
    lifecycle_names = {item["name"] for item in payload["tenancy_lifecycle_breakdown"]}
    tenant_structure_names = {item["name"] for item in payload["tenant_structure_breakdown"]}
    billing_names = {item["name"] for item in payload["billing_periodicity_breakdown"]}

    assert lifecycle_names <= {"Running", "Expired", "Unclassified"}
    assert sum(item["count"] for item in payload["tenancy_lifecycle_breakdown"]) == payload["tenancy_record_count"]
    assert "Joint-Tenancy" in tenant_structure_names
    assert "Yearly" in billing_names
    assert "15-Monthly" in lease_names
    assert "Joint-Tenancy" not in lease_names
    assert "Yearly" not in lease_names
    assert payload["tenancy_definition_source"].startswith("COUNT(public.applicant_property_mapping)")
    assert payload["tenant_terminology"]["lifecycle_records"]["label"] == "Derived tenure classifications"
    assert "not a canonical lifecycle status" in payload["tenancy_lifecycle_definition_source"]


def test_date_quality_is_reported_without_rewriting_source_values() -> None:
    settings = Settings()
    payload = _authority_land_metrics(settings)

    with connect(settings.database_url.unicode_string()) as connection, connection.cursor() as cursor:
        cursor.execute("""SELECT
            COUNT(*) FILTER (WHERE NULLIF(BTRIM(duration_to), '') IS NULL),
            COUNT(*) FILTER (WHERE NULLIF(BTRIM(duration_from), '') IS NOT NULL
                AND BTRIM(duration_from) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                AND LEFT(BTRIM(duration_from), 4)::int < 1900)
            FROM public.applicant_property_mapping""")
        missing_end_dates, historical_start_dates = cursor.fetchone()

    quality = payload["data_quality"]
    assert quality["missing_end_dates"] == missing_end_dates
    assert quality["historical_start_dates"] == historical_start_dates
