"""Focused Phase 10 billing correctness and artifact regression tests."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

from portproject_rag.billing import BillingPredictionRequest, BillingPredictionService
from portproject_rag.billing.prediction_service import XgbJsonModel
from portproject_rag.settings import Settings


class _EmptyCursor:
    def execute(self, *_args, **_kwargs) -> None:
        return None

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _EmptyConnection:
    def cursor(self):
        return _EmptyCursor()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _service(monkeypatch) -> BillingPredictionService:
    service = BillingPredictionService(Settings().database_url.unicode_string())
    monkeypatch.setattr(service, "_connect", lambda: _EmptyConnection())
    return service


def test_tax_percentages_are_normalized_as_percentages_even_below_one() -> None:
    service = BillingPredictionService(Settings().database_url.unicode_string())

    rates, reasons = service._normalize_rates({"tree_cess": 0.5, "general": 30})

    assert rates["tree_cess"] == pytest.approx(0.005)
    assert rates["general"] == pytest.approx(0.30)
    assert any("mecess" in reason for reason in reasons)


def test_manual_forecast_rejects_negative_numeric_inputs(monkeypatch) -> None:
    service = _service(monkeypatch)

    with pytest.raises(ValueError, match="present_amount cannot be negative"):
        service.predict_from_inputs(
            BillingPredictionRequest(
                target_year=2027,
                target_month=12,
                present_year=2026,
                present_month=8,
                present_amount=-1,
                present_cgst=0,
                present_sgst=0,
                area=100,
                billing_frequency="monthly",
                bill_type="general",
                structure_type="other",
                rates={"general": 30},
            )
        )


def test_manual_forecast_rejects_unknown_or_missing_structure(monkeypatch) -> None:
    service = _service(monkeypatch)
    base = dict(
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
        rates={"general": 30},
    )

    with pytest.raises(ValueError, match="Missing: structure_type"):
        service.predict_from_inputs(BillingPredictionRequest(**base))
    with pytest.raises(ValueError, match="unsupported structure_type"):
        service.predict_from_inputs(BillingPredictionRequest(**base, structure_type="unknown"))


def test_formula_result_exposes_independent_intermediate_values() -> None:
    service = BillingPredictionService(Settings().database_url.unicode_string())
    formula = service._apply_formula_layer(
        rules=service.rules,
        monthly_base=14_000,
        rates={key: 0.0 for key in (item["key"] for item in service.rules["rates"])},
        target_month=12,
        structure_type="other",
        water_tax_included=True,
        present_amount=14_000,
        present_cgst=900,
        present_sgst=900,
    )

    expected_am = 14_000 * 12
    expected_lv = expected_am + expected_am / 3
    expected_grvp = expected_lv - ((expected_lv * 0.9) * 0.9)
    expected_nrvp = expected_grvp - expected_grvp / 10
    expected_grvs = expected_grvp - expected_am
    expected_nrvs = expected_grvs - expected_grvs / 10
    intermediates = formula["intermediates"]
    assert intermediates["annual_amount"] == pytest.approx(expected_am)
    assert intermediates["letting_value"] == pytest.approx(expected_lv)
    assert intermediates["grvp"] == pytest.approx(expected_grvp)
    assert intermediates["nrvp"] == pytest.approx(expected_nrvp)
    assert intermediates["grvs"] == pytest.approx(expected_grvs)
    assert intermediates["nrvs"] == pytest.approx(expected_nrvs)


@pytest.mark.parametrize(
    ("target_month", "expected_labels"),
    [
        (4, {"Property tax", "Water benefit tax", "Sewerage benefit tax", "Employee guarantee cess", "Street tax"}),
        (9, {"Maharashtra education cess", "Tree cess"}),
    ],
)
def test_formula_golden_cases_match_documented_schedule(target_month: int, expected_labels: set[str]) -> None:
    """Exercise both scheduled branches against independently calculated values."""
    service = BillingPredictionService(Settings().database_url.unicode_string())
    monthly = 14_000.0
    rates = {
        "general": 0.30,
        "sewerage": 0.10,
        "water": 0.10,
        "street": 0.02,
        "mecess": 0.01,
        "tree_cess": 0.005,
        "wbt": 0.05,
        "sbt": 0.05,
        "egcess": 0.03,
    }
    result = service._apply_formula_layer(
        rules=service.rules,
        monthly_base=monthly,
        rates=rates,
        target_month=target_month,
        structure_type="mbpt",
        water_tax_included=True,
        present_amount=monthly,
        present_cgst=900,
        present_sgst=900,
    )

    annual = monthly * 12
    letting_value = annual + annual / 3
    grvp = letting_value - ((letting_value * 0.9) * 0.9)
    nrvp = grvp - grvp / 10
    nrvs = (grvp - annual) - ((grvp - annual) / 10)
    half_annual = annual / 2
    factor = 0.837
    expected: dict[str, float]
    if target_month == 4:
        expected = {
            "Property tax": (nrvs * rates["general"] / 2) + (nrvp * rates["sewerage"] / 2) + (nrvp * rates["water"] / 2),
            "Water benefit tax": (half_annual * factor * rates["wbt"]) + (nrvs / 2 * rates["wbt"]),
            "Sewerage benefit tax": (half_annual * factor * rates["sbt"]) + (nrvs / 2 * rates["sbt"]),
            "Employee guarantee cess": (half_annual * factor * rates["egcess"]) + (nrvs / 2 * rates["egcess"]),
            "Street tax": nrvp * rates["street"] / 2,
        }
    else:
        expected = {
            "Maharashtra education cess": (half_annual * factor * rates["mecess"]) + (nrvs / 2 * rates["mecess"]),
            "Tree cess": (half_annual * factor * rates["tree_cess"]) + (nrvs / 2 * rates["tree_cess"]),
        }

    observed = {item["label"]: float(item["value"]) for item in result["tax_items"]}
    assert set(observed) == expected_labels
    for label, value in expected.items():
        assert observed[label] == pytest.approx(value)
    assert result["total_formula_tax"] == pytest.approx(sum(expected.values()))


def test_model_and_rules_artifact_failures_are_explicit(monkeypatch, tmp_path: Path) -> None:
    missing_model = tmp_path / "missing-model.json"
    monkeypatch.setenv("BILLING_MODEL_PATH", str(missing_model))
    with pytest.raises(FileNotFoundError, match="Billing model artifact not found"):
        BillingPredictionService(Settings().database_url.unicode_string())

    missing_rules = tmp_path / "missing-rules.json"
    monkeypatch.setenv("BILLING_RULES_PATH", str(missing_rules))
    monkeypatch.delenv("BILLING_MODEL_PATH", raising=False)
    with pytest.raises(FileNotFoundError, match="Billing rules file not found"):
        BillingPredictionService(Settings().database_url.unicode_string())

    corrupt_model = tmp_path / "corrupt-model.json"
    corrupt_model.write_text("{not-json", encoding="utf-8")
    monkeypatch.setenv("BILLING_MODEL_PATH", str(corrupt_model))
    monkeypatch.delenv("BILLING_RULES_PATH", raising=False)
    service = BillingPredictionService(Settings().database_url.unicode_string())
    with pytest.raises(json.JSONDecodeError):
        service._get_model()


def test_model_artifact_matches_reference_xgboost_margin_when_available() -> None:
    xgb = pytest.importorskip("xgboost")
    root = Path(__file__).resolve().parents[1]
    model_path = root / "artifacts" / "billing_forecast" / "runtime" / "models" / "billing_xgb_model.json"
    manifest_path = root / "artifacts" / "billing_forecast" / "runtime" / "models" / "billing_model_manifest.json"
    model = XgbJsonModel(model_path, manifest_path)
    reference = xgb.Booster()
    reference.load_model(str(model_path))
    values = {column: 0.0 for column in model.feature_columns}
    values.update(
        {
            "present_amount": 10_000.0,
            "present_cgst": 900.0,
            "present_sgst": 900.0,
            "present_area": 100.0,
            "present_year": 2026.0,
            "present_month": 8.0,
            "target_year": 2027.0,
            "target_month": 12.0,
            "horizon_months": 16.0,
            "present_amount_per_area": 100.0,
            "present_log_amount": math.log1p(10_000.0),
            "billing_frequency_monthly": 1.0,
            "line_category_rent": 1.0,
        }
    )
    import numpy as np

    matrix = np.array([[values[column] for column in model.feature_columns]], dtype="float32")
    observed = float(reference.predict(xgb.DMatrix(matrix, feature_names=model.feature_columns), output_margin=True)[0])
    assert model.predict_log(values) == pytest.approx(observed, abs=2e-5)


def test_billing_manifest_tracks_immutable_artifact_inputs() -> None:
    root = Path(__file__).resolve().parents[1]
    model_path = root / "artifacts" / "billing_forecast" / "runtime" / "models" / "billing_xgb_model.json"
    manifest_path = root / "artifacts" / "billing_forecast" / "runtime" / "models" / "billing_model_manifest.json"
    dataset_path = root / "artifacts" / "billing_forecast" / "source" / "billing_training_dataset.csv"
    formula_path = root / "artifacts" / "billing_forecast" / "runtime" / "Tax_Formulas_Expanded.md"

    def sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest().upper()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["artifact_sha256"] == sha256(model_path)
    assert manifest["training_dataset_sha256"] == sha256(dataset_path)
    assert manifest["formula_sha256"] == sha256(formula_path)
    assert manifest["feature_schema_version"] == "billing-features-v1"
    assert manifest["runtime_evaluator_version"] == "XgbJsonModel-v1"
