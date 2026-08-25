# Billing forecast

**Status: CURRENT SOURCE OF TRUTH**

Billing is an Authority-only feature. It combines source-backed customer and
tenancy prefill, an exported XGBoost forecast artifact, and deterministic tax
formula evaluation. The ML forecast and formula layer are intentionally
separate responsibilities.

## Runtime flow

```text
Authority opens Billing Forecast
  -> GET rules and eligible tenancies
  -> select tenancy
  -> GET source-backed prefill
  -> review/complete dynamic inputs and rates
  -> POST /api/v1/billing/predict
  -> persist the result as a user-scoped chat exchange
```

The service reads source values from `public.applicant_property_mapping`,
`public.plot`, `public.mcustomer`, `public.tgeneralbill`, and the configured
master/rate tables. Missing or ambiguous inputs remain visible as warnings or
blank fields; the service does not invent a rate or approval.

## ML and formula responsibilities

| Layer | Responsibility | Source of truth |
| --- | --- | --- |
| XGBoost model | Forecast the billing base from the trained feature schema. | `artifacts/billing_forecast/runtime/models/billing_xgb_model.json` and its manifest. |
| Formula layer | Apply configured billing/tax schedules, structure factors, rates, and rounding. | `artifacts/billing_forecast/runtime/config/billing_rules.json` plus source rate tables. |
| Chat/audit persistence | Store the request, result, sources/metadata, and audit event. | `rag.chat_session`, `rag.chat_message`, `rag.audit_event`. |

The UI must not treat a model value as a tax approval. The result includes
source/metadata, warnings, formula steps, and the model manifest reference for
review.

## Dynamic inputs and precedence

For a selected tenancy, customer-specific exported rows can override formula
visibility. Target-period PostgreSQL master rates are the fallback where a
customer override is absent. Structure and billing frequency are normalized
from source values and are not assumed identical for every customer.

Manual forecasts require the approved form fields. The backend validates
negative/invalid values, target periods, supported categories/frequencies, and
required area/structure inputs before calculation.

## Artifacts and optional dependencies

The portal runtime needs the exported runtime model/config artifacts. Training
requires the optional `billing-training` extra (`numpy`, `pandas`,
`scikit-learn`, and `xgboost`) and is not part of normal portal startup. Training
inputs and generated models remain local artifacts; do not commit credentials or
raw customer data.

## API

See [API reference](API_REFERENCE.md#billing-forecast) for the complete route
contract. All billing routes require an authenticated Authority principal.

## Limitations and review points

- A forecast is not an accounting posting or an approval.
- Missing source area, rates, structure matches, or billing history produces a
  warning/error instead of a fabricated value.
- Billing formula/model quality must be validated with approved holdout and
  hand-calculated cases; this document does not claim an accuracy percentage.
- The service does not mutate PMS billing source tables.
