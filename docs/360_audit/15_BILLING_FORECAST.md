# Billing forecast audit

## End-to-end implementation

React BillingForecastModal -> billing rules and tenancy endpoints -> selected
tenancy prefill -> BillingPredictionService -> PostgreSQL public customer,
profile, history, structure, and rate sources plus copied CSV mapping ->
exported XGBoost JSON evaluator -> deterministic formula/tax layer -> response
and optional chat message.

## Model and formula separation

The runtime model is an exported XGBoost JSON artifact evaluated by
XgbJsonModel without importing xgboost. Model feature columns and metrics come
from billing_model_manifest.json. The final amount also includes deterministic
billing rules, period logic, structure factors, rates, and tax mappings.

It is inaccurate to describe every displayed amount as an ML prediction: the
service returns a model raw output plus formula and tax calculations.

## Dynamic versus configured

Dynamic: selected tenancy, customer/profile/history/rates, CSV rows, target
period, missing-rate warnings, and database source values.

Configured/artifact-backed: feature definitions, model path, manifest, rules,
tax mapping, category/frequency/structure labels, and max forecast months.

Manual approved inputs remain required where source data is unavailable. The
service intentionally does not infer missing commercial approvals.

## Persistence and failure

The API reads source data and returns a prediction context; it does not write
billing source tables. Missing model/rules artifacts produce an availability
failure. Missing database values generate warnings and leave fields blank or
use explicitly documented fallback sources.

## Quality status

Focused billing tests pass. Current predictive accuracy on a reviewed holdout
set is NOT VERIFIED in this audit. The training script and manifest should be
audited separately before claiming production ML quality.

