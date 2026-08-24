# Phase 10 — Billing correctness validation

**Date:** 2026-08-25  
**Status:** **PARTIAL / BLOCKED FOR ACCEPTANCE**  
**Scope:** ML forecast quality and deterministic billing/formula correctness were audited separately. No billing source table was modified, no model was retrained, and no forecast was written to an operational conversation during this phase.

## Gate decision

This phase cannot be accepted as production billing validation yet. The repository contains a reproducible temporal split and a deployed pure-Python model evaluator, so an engineering replay was possible. However:

1. There is no approved, immutable holdout manifest with owner/sign-off, and the runtime artifact does not carry enough provenance to prove which exact dataset/model run produced it.
2. There are no business-reviewed hand-calculated cases for the required formula edge cases.
3. The metrics recorded in the existing model manifest do not match a replay through the evaluator used by the application. This must be reconciled before the forecast can be described as quality-accepted.

The phase therefore stops here. No tuning, formula change, model replacement, or source-data mutation was performed.

## Evidence inventory

| Concern | Evidence | Finding |
|---|---|---|
| Training entry point | `src/portproject_rag/billing/train_model.py` | Current entry point uses a temporal cutoff (`target_period_index < 2025-01`), trains on `log1p(target_amount)`, and exports an XGBoost JSON model plus manifest. Retraining is manual and not part of an API request. |
| Runtime model | `src/portproject_rag/billing/prediction_service.py` (`XgbJsonModel`) | The API evaluates the exported JSON artifact with a pure-Python tree evaluator and reverses the transform with `expm1`. |
| Training data | `artifacts/billing_forecast/source/billing_training_dataset.csv` | 614,284 data rows, 152 columns, required training columns present, source billing periods 2019-03 through 2026-02. SHA-256: `C8C8C6E01A1CE07D79860D0187A4432902A0CBA2B8FFA456BF69B2B8B45CC27F`. |
| Runtime artifact | `artifacts/billing_forecast/runtime/models/billing_xgb_model.json` | Present; SHA-256: `4C74CB3A913DCE11D2ED5EE7D9D9AE8E7D8A159DBF708F0794A00228AAE87661`. |
| Existing manifest | `artifacts/billing_forecast/runtime/models/billing_model_manifest.json` | Contains feature columns, transform, parameters, cutoff and metrics, but no dataset hash/version, model hash, training date, code revision, dependency versions, or approval/run identifier. Its `training_data` and `formula_data` values point to old `C:\Users\kumar\...` paths. SHA-256: `AE916E1CDB96EF3EC26D1CEE6280712B10880005B7E839737B105547895A77D2`. |
| Deterministic rules | `artifacts/billing_forecast/runtime/config/billing_rules.json` and `Tax_Formulas_Expanded.md` | Formula schedules, structure factors, rate keys, tax sources, and target-month rules are configuration-backed. Rules SHA-256: `FF45D726C2A12840BAAADD5F0CA6DCFFAEA244F0707CDC3D25A239714E62B538`; formula SHA-256: `C392935447FC28E3CE712E66E16523A98BCEEDC766D0B8AE728EE651D387B2C9`. |
| Source prefill/rate precedence | `BillingPredictionService.tenancy_prefill` | Selected-tenancy CSV overrides are applied first; missing keys fall back to target-period PostgreSQL master rates. Area/profile/history/structure are read from the documented `public.*` tables. |
| Persistence/audit | `src/portproject_rag/api.py`, `/api/v1/billing/predict` | The service does not write `public.*` billing tables. After a successful forecast, the API may write the normal `rag.chat_session`/`rag.chat_message` rows and a `billing_forecast` audit event. |

The source bundle also contains `artifacts/billing_forecast/source/train_billing_model.py`, a historical copy with hard-coded `C:\Users\kumar\...` paths. It is not the current runtime entry point and should not be treated as a second production training contract.

## Part A — ML forecast replay

The following was measured read-only using the current copied dataset, the current cutoff, and the same pure-Python JSON evaluator used by the application. The replay did not retrain or rewrite the model. The cleaned source rows and temporal pairs were recomputed from the current training code:

| Split fact | Value |
|---|---:|
| Clean rows after required-field/period/category filtering | 202,518 |
| Total next-period pairs | 93,835 |
| Training pairs (`target_period_index < 2025-01`) | 67,360 |
| Replay validation pairs (`target_period_index >= 2025-01`) | 26,475 |
| Feature columns | 15 |

### Metrics — do not interpret R² as “accuracy”

| Metric | Existing manifest (training run) | Runtime evaluator replay | Acceptance |
|---|---:|---:|---|
| MAE (INR) | 22,552.85 | 19,795.76 | **Not accepted; mismatch requires reconciliation** |
| RMSE (INR) | 241,976.42 | 230,510.77 | **Not accepted; mismatch requires reconciliation** |
| R² raw | 0.49764 | 0.54412 | Descriptive only; not an accuracy percentage |
| R² log | 0.88887 | 0.92134 | Descriptive only; not an accuracy percentage |
| Median absolute error (INR) | Not recorded | 3,082.88 | Not accepted as a business target |
| MAPE | Not recorded | 233.22% | Mathematically defined here because targets are positive, but dominated by small denominators and not a suitable sole KPI |
| Sample count | 26,475 | 26,475 | Same count, but predictions/metrics differ |

Absolute-error percentiles from the replay were INR 3,082.88 (P50), 10,031.63 (P75), 32,566.77 (P90), 62,627.61 (P95), and 218,242.33 (P99). The five largest absolute errors were concentrated in high-value rent cases in target periods 2025-05 and 2025-11; identifiers are intentionally omitted from this Git-tracked report.

The mismatch is a release blocker, not evidence that either result is correct. The next controlled run must use an approved holdout manifest, record the exact dataset/model hashes, and compare the training-library prediction path with the deployed JSON evaluator on the same rows.

## Part B — deterministic formula audit

The API separates the model path from the formula path. The model produces a forecast base amount; `_apply_formula_layer` then applies the configured annual/letting/NRV calculations, scheduled taxes, present-bill CGST/SGST rates, and final total.

An independent engineering calculation was run from the formulas documented in `Tax_Formulas_Expanded.md` for a controlled INR 10,000 monthly base, MBPT structure, 1% rate inputs, and a 9%/9% present GST basis. April (pre-tax), September (post-tax), and May (unscheduled) cases matched the implementation exactly in the compared floating-point result (difference 0.00). These are engineering checks only; they are **not business-reviewed acceptance cases**.

| Required case | Observed source behavior | Acceptance |
|---|---|---|
| Missing area | Manual `predict_from_inputs` requires area and returns a validation error when absent. Source-backed `predict` uses `0.0` for the model area feature and records a fallback warning when no reliable area exists. | Not business-approved; verify intended zero-feature behavior |
| Invalid target period | Target must be after the present/latest period; invalid month/year is rejected. | Static pass; live API acceptance not run |
| Negative amount/rates | API Pydantic fields reject negative numeric inputs. The direct service path clamps manual amount/CGST/SGST/area to zero, so callers bypassing the API do not receive the same rejection semantics. | **Gap:** define one domain contract |
| Missing rate | `_normalize_rates` sets an absent rate to zero and records a fallback reason. | Static pass; business treatment not signed off |
| Selected-tenancy override | CSV formula rows are selected by applicability/active flags and latest `valid_from`; selected-tenancy values override database rates for matching keys. | Focused test passes; live multi-tenancy acceptance not run |
| Database rate fallback | Missing selected-tenancy values are filled from target-period `public.m_tax_rates`/schedule data when available. | Focused test passes; live API acceptance not run |
| Unmatched structure | `_apply_formula_layer` silently falls back to the configured `other` structure. Prefill emits a warning, but manual prediction can still calculate with the fallback. | **Gap:** business decision required; current behavior can hide an unmatched structure |
| Rounding | No explicit `Decimal`/quantization/rounding policy exists in the formula layer; the API returns floating-point totals and the UI formats them for display. | **Gap:** obtain billing rounding policy and test every monetary boundary |
| Tax sign/negative components | The documented formulas can produce a negative NRVS for some synthetic inputs; the implementation does not clamp negative intermediate/tax components. | **Gap:** business review required; do not add a clamp without sign-off |
| Source-table integrity | Billing service SQL is read-only against `public.*`; no billing `INSERT`, `UPDATE`, or `DELETE` exists. | Static pass; no before/after snapshot was run because no disposable fixture was authorized |

### Source precedence and formula trace

The returned forecast includes `model_raw_output`, `monthly_base_amount`, `tax_items`, `total_formula_tax`, `calculation_steps`, `forecast_quality`, `formula_source_file`, and fallback reasons. This is sufficient for an operator-facing trace, but it is not a substitute for business approval of the rates, structure mapping, schedule, rounding, or negative-intermediate policy.

## Model manifest gap

The current manifest is usable for loading the model but is not a release-grade provenance manifest. A reviewed replacement should add, at minimum:

- immutable training dataset identifier and SHA-256;
- feature-schema version and preprocessing code revision;
- model artifact SHA-256 and model/library version;
- UTC training timestamp and run ID;
- validation protocol, cutoff/holdout identifier, row count, and approval owner;
- MAE, RMSE, median absolute error, R², a denominator-safe percentage metric, error percentiles, and worst-case case references;
- formula/rate configuration hash and business sign-off reference.

Until those fields exist and the manifest/replay mismatch is resolved, the forecast should be presented as an unaccepted engineering forecast rather than a validated financial prediction.

## Persistence, security, and mutation boundary

- Billing endpoints require an authenticated Authority user.
- `GET /api/v1/billing/rules`, tenancy options, and prefill are source-backed reads.
- `POST /api/v1/billing/predict` can persist a normal chat user/assistant message and a `billing_forecast` audit event, but it does not mutate the PMS `public.*` billing source tables.
- No production mutation, chat write, audit write, source snapshot, or deletion was issued for this phase.

## Validation commands

The report-only change passed these non-mutating checks:

| Check | Result |
|---|---|
| `python -m pytest tests/test_billing_service.py -q` | **4 passed** |
| `python -m pytest -q` | **45 passed** |
| `python -m ruff check src tests` | **All checks passed** |
| `python -m compileall -q src tests` | **Passed** |
| `npm run build` (web) | **Passed**; TypeScript and Vite production build completed |

These checks establish repository integrity only; they are not a claim that the ML/formula acceptance gate is open.

## Required unblock plan

1. Obtain an approved sanitized holdout manifest and business owner for billing validation.
2. Run the training-library and pure-Python evaluator on the identical holdout rows; fail the release if their predictions differ beyond a documented tolerance.
3. Obtain signed hand-calculated cases covering every row in the Part B matrix, including missing area, missing/overridden/database rates, unmatched structure, invalid/negative input policy, schedule boundaries, and monetary rounding.
4. Add an immutable release manifest with the hashes and metrics listed above.
5. Execute the API flow only against a disposable fixture, verify chat/audit persistence, and compare source-table checksums before and after.

**Phase 10 stops here. Phase 11 has not been started.**
