from portproject_rag.billing import BillingPredictionRequest, BillingPredictionService
from portproject_rag.settings import Settings


def test_billing_rules_and_manual_forecast_use_copied_runtime_artifacts() -> None:
    service = BillingPredictionService(Settings().database_url.unicode_string())
    rules = service.rules_payload()

    assert rules["defaults"]["category"] == "general"
    assert {item["key"] for item in rules["rates"]} >= {"general", "mecess", "tree_cess"}

    result = service.predict_from_inputs(
        BillingPredictionRequest(
            target_year=2027,
            target_month=12,
            present_year=2026,
            present_month=8,
            present_amount=10_000,
            present_cgst=900,
            present_sgst=900,
            area=100,
            billing_frequency="monthly",
            bill_type="general",
            structure_type="other",
        )
    )
    assert result.final_amount >= 0
    assert result.model_source == "xgboost-json"
    assert result.metadata["manual_inputs"] is True


def test_permanent_source_structure_uses_the_documented_other_structure_rule() -> None:
    service = BillingPredictionService(Settings().database_url.unicode_string())

    assert service._configured_structure_value("Permanent") == "other"


def test_area_can_be_recovered_only_from_explicit_rrplotno_area_text() -> None:
    service = BillingPredictionService(Settings().database_url.unicode_string())

    assert service._area_from_text("SHIFTING OF 360 MM FOR LSHS.(AREA 181 SQM ON LAND ONLY)") == 181
    assert service._area_from_text("RR 1860") is None


def test_reported_billing_tenancy_prefill_is_actionable() -> None:
    service = BillingPredictionService(Settings().database_url.unicode_string())

    prefill = service.tenancy_prefill("10104960")

    assert prefill["customer_id"] == "184"
    assert prefill["fields"]["area"] == 181
    assert prefill["fields"]["structure_type"] == "other"
    assert prefill["rates"]["general"] == 30
    assert prefill["rates"]["sewerage"] == 78
    assert prefill["rates"]["water"] == 130
    assert prefill["rate_sources"]["general"] == "target-period PostgreSQL master rate"
    assert not any("no matching formula structure rule" in warning.lower() for warning in prefill["warnings"])
    assert any("mecess" in warning.lower() and "remain blank" in warning.lower() for warning in prefill["warnings"])

    csv_override = service.tenancy_prefill("31001218")
    assert csv_override["rates"]["mecess"] == 12
    assert csv_override["rate_sources"]["mecess"] == "selected-tenancy CSV override"
