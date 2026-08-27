# Phase 10 — Billing Forecast, Model Validation, and Financial Calculation

## Required final summary

| Gate | Result |
| --- | --- |
| Acceptance safety gate | **PASS** — every mutable acceptance operation verified `portproject_acceptance`, sentinel `acceptance/1`, and non-operational database identity |
| Billing model artifact integrity | **PASS** — model, manifest, training dataset, and formula hashes are recorded |
| Training/runtime feature parity | **PASS** — runtime uses the 15 manifest features in the training order |
| Reference XGBoost parity | **PASS** — pure-Python evaluator maximum absolute margin difference `0.0000106894`, tolerance `0.000020` |
| ML validation metrics | **PARTIAL** — reproducible metrics are recorded, but no approved business threshold exists |
| Formula implementation | **PASS** — independent April/September golden cases and unscheduled-month behavior pass |
| Rate precedence and units | **PASS** — selected-tenancy CSV overrides target-period PostgreSQL masters, with deterministic percentage normalization |
| Negative/malformed input validation | **PASS** — rejected before model evaluation or persistence |
| Source immutability | **PASS** — acceptance source tables are unchanged by a successful prediction |
| Prediction chat/audit persistence | **PASS** — successful predictions create or use only the authenticated principal's chat and write the expected audit event |
| Context and cross-principal isolation | **PASS** — concurrent predictions keep distinct context IDs and chat ownership |
| Incomplete/invalid billing behavior | **PASS** — no chat or audit mutation on rejected requests |
| Billing authorization | **PASS** — unauthenticated and tenant callers are denied before billing work |
| Phase 08 regression gate | **PASS** — 10/10 acceptance tests after reset; Phase 08 report remains intact |
| Phase 09 regression gate | **PASS** — 10/10 workflow tests in the established Phase 09 evidence; no workflow code was changed for Phase 10 |
| Plain Python suite | **PASS** — 63 passed, 27 skipped; acceptance tests are now explicitly opt-in |
| Guarded Phase 10 acceptance suite | **PASS** — 4/4 billing tests |
| Full guarded acceptance suite | **PASS WITH RETRY** — 24 tests passed in the dedicated run; one later combined run encountered a transient local Ollama retrieval `503`, and the isolated test passed after reset/retry |
| Ruff | **PASS** |
| Frontend production build | **PASS** |
| `/health` | **PASS** — acceptance database, HTTP 200 |
| `/health/ready` | **PASS** — `rag_ready=true`, no pending or failed documents |
| Browser authenticated E2E | **NOT AVAILABLE** — no browser runner is configured (carried forward from Phase 08) |
| Operational `portproject` database modified | **NO** — read-only verification returned `portproject`, no acceptance sentinel, and zero acceptance billing audit metadata |

**FINAL PHASE RESULT: PARTIAL**

The billing implementation, deterministic calculation layer, artifact integrity,
authorization boundary, provenance, persistence, and acceptance safety checks pass.
The result is PARTIAL only because the repository does not contain an approved
business error threshold or finance-approved rounding/promotion policy, and the
validation split shares customer identities across time rather than being an
independent-customer holdout. The system is not auto-promoted or retrained based
on these metrics.

## Scope and safety boundary

This phase covered billing forecast validation and the deterministic financial
calculation layer only. It did not change Phase 08 authentication/RAG ACL
behavior, execute the Phase 09 workflow lifecycle, tune RAG quality or latency,
validate billing model production quality, migrate tender persistence, or deploy
to production.

Before each mutable acceptance action the existing fixture tooling verified:

```text
current_database() = portproject_acceptance
acceptance sentinel = acceptance/1
current_database() != portproject
tender storage is below tests/runtime and is not operational storage
```

The final reset/check ended with `ACCEPTANCE FIXTURE READY`. The acceptance API
process was stopped after the final checks. The operational database read-only
check returned `current_database=portproject`, no `public.acceptance_environment`
table, and zero acceptance billing audit metadata. No operational write was
issued.

## Actual billing architecture and data flow

```text
public.mcustomer / tgeneralbill / plot / tax masters
        + selected-tenancy billing_tax_mapping.csv
                         |
                 billing prediction service
                         |
       pure-Python XgbJsonModel (log1p -> expm1)
                         |
          monthly forecast base amount
                         |
             deterministic formula layer
                         |
      final bill + intermediates + tax item provenance
                         |
       principal-owned chat message and audit event
```

The service reads source data and runtime artifacts. It does not write source
billing tables. The API requires an authority portal role for billing routes;
workflow roles DO/NO/HO remain distinct from the portal role.

Implemented endpoints validated in this phase:

| Endpoint | Purpose | Acceptance result |
| --- | --- | --- |
| `GET /api/v1/billing/status` | Artifact readiness | 200 for authority; safe filenames only |
| `GET /api/v1/billing/rules` | Dynamic form/rule metadata | 200 for authority |
| `GET /api/v1/billing/tenancies` | Eligible tenancy choices | 200 for authority |
| `GET /api/v1/billing/tenancies/{tenancy_id}/prefill` | Source-backed form prefill | 200 for complete fixture; 404 for incomplete fixture |
| `POST /api/v1/billing/predict` | Forecast, formula calculation, chat/audit persistence | 200 for valid authority request; 422 for invalid; 403/401 for unauthorized |

## Model and training validation

The training implementation in `src/portproject_rag/billing/train_model.py`
does the following, which was independently reproduced for validation:

1. Loads the source training CSV and validates required columns.
2. Restricts targets to positive rent/additional-rent billing lines.
3. Groups by customer, line category, and billing period.
4. Uses the next observed period as the target, with no target-period value in
   the feature row.
5. Uses a temporal split at target period `2025-01`.
6. Trains `XGBRegressor` on `log1p(target_amount)` and exports JSON.
7. The runtime evaluates that JSON without requiring XGBoost and applies
   `expm1` before the formula layer.

Dataset evidence:

| Measure | Observed |
| --- | ---: |
| Raw source rows | 202,518 |
| Forecast pairs | 93,835 |
| Training pairs | 67,360 |
| Validation pairs | 26,475 |
| Duplicate pair keys | 0 |
| Non-positive validation targets | 0 |
| Customers in both train and validation | 2,418 |

The temporal split avoids future-row target leakage. Because customers overlap
between the train and validation windows, this is not an independent-customer
generalization test; that limitation is recorded rather than hidden.

### Reproducible validation metrics

| Metric | Exported XGBoost | Previous-bill baseline |
| --- | ---: | ---: |
| MAE | 22,425.00 | 26,568.70 |
| RMSE | 240,651.53 | 334,470.74 |
| Raw R² | 0.5031 | 0.0402 |
| Log R² | 0.8902 | 0.8000 |
| Median absolute error | 3,436.07 | 2,667.63 |
| sMAPE | 41.04% | 48.75% |
| WAPE | 42.46% | 50.31% |
| Within ±5% | 4.84% | 34.14% |
| Within ±10% | 10.04% | 34.80% |
| Within ±20% | 21.57% | 37.33% |

The model improves aggregate MAE, RMSE, R², sMAPE, and WAPE, while the simple
previous-bill baseline has lower median error and better percentage-tolerance
hit rates. MAPE is not decision-grade for this distribution because small
positive targets dominate percentage error. No business tolerance, model
promotion threshold, or finance sign-off exists in the repository, so no claim
of production accuracy is made.

Error buckets show the remaining trade-off:

| Target bucket | Rows | MAE | Bias | WAPE |
| --- | ---: | ---: | ---: | ---: |
| Low | 8,827 | 1,402.16 | +803.69 | 55.12% |
| Medium | 8,823 | 5,014.30 | +1,080.82 | 42.98% |
| High | 8,825 | 60,859.36 | -30,605.12 | 42.20% |

The machine-readable evidence is in
`artifacts/evaluation/billing_model_validation.json`. The runtime manifest now
records the feature schema version, evaluator version, model hash, training
dataset hash, formula hash, pair count, validation method, and an explicit
unknown training date (`null`) rather than inventing one.

## Artifact integrity and runtime parity

| Artifact | SHA-256 |
| --- | --- |
| `billing_xgb_model.json` | `4C74CB3A913DCE11D2ED5EE7D9D9AE8E7D8A159DBF708F0794A00228AAE87661` |
| `billing_model_manifest.json` | `E52B66B50930B6564AD743E0ADE3F7BF5AE46F6BE5AB82E24F7E9681A796D28C` |
| `billing_training_dataset.csv` | `C8C8C6E01A1CE07D79860D0187A4432902A0CBA2B8FFA456BF69B2B8B45CC27F` |
| `Tax_Formulas_Expanded.md` | `C392935447FC28E3CE712E66E16523A98BCEEDC766D0B8AE728EE651D387B2C9` |

The pure evaluator was compared with native XGBoost JSON evaluation on multiple
feature vectors. The maximum absolute raw-margin difference was below the
documented `2e-5` tolerance. Runtime feature construction uses the same 15
columns and one-hot category semantics recorded in the manifest.

## Formula and financial calculation validation

The deterministic layer follows `Tax_Formulas_Expanded.md` and the dynamic
`billing_rules.json` configuration:

```text
AM   = monthly_base × 12
LV   = AM + AM/3
GRVP = LV - ((LV × 0.9) × 0.9)
NRVP = GRVP - GRVP/10
GRVS = GRVP - AM
NRVS = GRVS - GRVS/10
dual tax = ((AM/2) × structure factor × rate) + ((NRVS/2) × rate)
property tax = (NRVS × General)/2 + (NRVP × Sewerage)/2 + (NRVP × Water)/2
street tax = (NRVP × Street)/2
final = monthly base + predicted CGST + predicted SGST + scheduled formula taxes
```

The acceptance schedule is pre taxes in April/October and post taxes in
March/September. Unscheduled months return no scheduled formula tax. Golden
tests calculate April/MBPT and September/MBPT independently and compare each
tax component and total, rather than comparing only the final number.

Rates are resolved with explicit provenance: selected-tenancy CSV values take
precedence over target-period PostgreSQL masters, and missing values remain
zero with a warning. All sources use percentage points and are normalized once
(for example, `30` becomes `0.30` and `0.5` becomes `0.005`). This fixes the
previous bug that interpreted `0.5%` as a 50% fraction.

The implementation intentionally does not invent a monetary rounding policy.
Internal calculations remain floating point; the web UI formats values to two
decimal places for display. Finance must approve whether and where statutory
rounding is required before production promotion.

## Validation and failure behavior

Manual form requests now reject missing, non-finite, negative, invalid-period,
past-target, unsupported-frequency, unsupported-bill-type, and unknown-structure
values before model evaluation. Zero-valued CGST/SGST and other legitimate zero
inputs remain valid.

Missing/corrupt model or rules artifacts fail explicitly. The API translates
configuration/runtime failures to a controlled 503 response. User-facing
responses no longer expose absolute server filesystem paths; artifact names and
formula-source filenames are safe identifiers.

Incomplete source-backed tenancy prefill returns 404 and does not run a
prediction. Invalid requests return 422 and do not create chat or audit rows.

## Provenance, ownership, and concurrency evidence

The successful acceptance test verified:

* prefill values and each rate source came from the acceptance database/CSV;
* source customer, bill, plot, and tax rows were unchanged after prediction;
* the response included model provenance, formula schedule, intermediates, tax
  items, and calculation steps;
* exactly one user request and one assistant calculation message were written;
* the billing audit event contained tenancy/principal metadata but no password,
  session token, or database credential;
* an existing `chat_session_id` was accepted only when owned by the caller;
* concurrent DO/NO manual predictions received distinct context IDs and their
  chat rows retained the correct authenticated principals.

The in-memory service context is process-local. A restart does not claim to
recover an in-flight context; persisted chat/audit records remain the durable
record. The UI does not present an in-memory context as durable workflow state.

## Defects found and smallest safe fixes

| Defect | Severity | Fix |
| --- | --- | --- |
| Rates below one were treated as already-normalized fractions, turning Tree Cess `0.5%` into 50% | High financial correctness | Normalize all source/form percentage points exactly once and reject negative rates |
| Manual negative numeric inputs were silently clamped to zero | Medium financial correctness | Validate before model evaluation and reject negatives with 422 |
| Legitimate zero CGST/SGST values disabled the web submit button | Medium usability | Validate empty strings rather than truthiness |
| Billing API exposed absolute model/formula paths | Low information disclosure | Serialize safe artifact/source filenames only |
| Plain pytest collected shared mutable acceptance fixtures | Medium test safety/repeatability | Make acceptance tests explicitly opt-in through `load_acceptance_env.ps1` and keep the default suite isolated |

No billing source rows, tender records, workflow records, or operational data
were changed by these fixes.

## Automated tests and artifacts

Added or updated:

* `tests/test_billing_phase10.py` — rate units, negative validation, structure
  validation, independent formula golden cases, artifact failure behavior,
  XGBoost parity, and manifest hash checks.
* `tests/acceptance/test_phase10_billing_e2e.py` — guarded prefill, provenance,
  prediction/chat/audit persistence, source immutability, invalid requests,
  authorization, and concurrent principal isolation.
* `src/portproject_rag/billing/prediction_service.py` — correctness validation,
  intermediates, and safe response serialization.
* `src/portproject_rag/billing/train_model.py` — reproducible artifact metadata
  and SHA-256 recording on future exports.
* `src/portproject_rag/api.py` — safe billing artifact status identifiers.
* `tests/acceptance/conftest.py` and `scripts/load_acceptance_env.ps1` — explicit
  acceptance-test opt-in and safety isolation.
* `artifacts/evaluation/billing_model_validation.json` — reproducible metric,
  baseline, leakage, error-bucket, formula, and provenance evidence.

## Remaining blockers before a production-quality model sign-off

1. Obtain a finance/product-approved error threshold and model-promotion rule.
2. Evaluate on an independent-customer holdout or document why temporal
   customer overlap is acceptable for this business use.
3. Obtain and implement the approved statutory monetary rounding policy.
4. Add browser E2E only if a browser test runner is intentionally introduced;
   none is currently configured.

These are explicit decision points, not silently assumed defaults.

## Phase boundary

Phase 10 is complete. Stop here as required. Do not begin Phase 11, RAG quality
tuning, performance optimization, billing model promotion, tender persistence
migration, frontend redesign, or production deployment without an explicit new
phase request.
