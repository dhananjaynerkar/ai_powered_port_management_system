# Billing Forecast integration

The Billing Forecast context in the Authority AI Assistant is now a real, authenticated workflow. It is opened from the composer context selector and uses the same local PostgreSQL connection and session cookie as the rest of the portal.

## Runtime flow

1. The UI loads billing rules from `GET /api/v1/billing/rules`.
2. The tenancy selector loads source tenancy options from the copied tax-mapping export and, when available, maps them to `public.mcustomer` through the billing service.
3. Selecting a tenancy requests `GET /api/v1/billing/tenancies/{tenancy_id}/prefill`. Values are source-backed when those tables are available. Formula rates use a per-tenancy hierarchy: selected-tenancy CSV overrides first, then target-period `public.m_tax_rates`/`public.m_tax_for_treecess_street_edu` values for any missing keys. The API returns the source for each displayed rate so the UI does not imply that a master rate is a customer-specific override. Plot area is read from `public.plot.area`; when that column has no match, the service only recovers an explicitly labelled `AREA <number> SQM` value from `public.mcustomer.rrplotno` and marks it for operator verification. Other missing values remain blank and must be entered explicitly.
4. `Run prediction and add to chat` posts the validated form to `POST /api/v1/billing/predict`.
5. The service evaluates the exported XGBoost JSON artifact with its pure-Python tree evaluator, applies the configured formula layer, records an audit event, and stores the forecast summary in the authenticated chat session.

No billing endpoint writes to the source billing tables. Only the normal chat message and audit tables are written when a forecast is added to a conversation.

## Artifacts and source files

- Runtime model/rules: `artifacts/billing_forecast/runtime/`
- Copied source bundle and training data: `artifacts/billing_forecast/source/`
- Runtime service: `src/portproject_rag/billing/prediction_service.py`
- Offline-safe future prediction module: `src/portproject_rag/billing/future_prediction.py`
- Reproducible training entry point: `src/portproject_rag/billing/train_model.py`

The supplied training CSV is retained under `artifacts/billing_forecast/source/` for reproducibility. It is not loaded during application startup. The prebuilt JSON model is used at runtime, so normal portal startup does not require pandas, scikit-learn, or XGBoost.

## Retraining

Install the optional training dependencies in the project environment, then run:

```text
python -m pip install -e ".[billing-training]"
python -m portproject_rag.billing.train_model
```

The script defaults to the copied local dataset and writes the JSON model and manifest to `artifacts/billing_forecast/runtime/models/`. Override `BILLING_TRAINING_DATA`, `BILLING_FORMULA_DATA`, or `BILLING_OUTPUT_DIR` when using a different approved dataset or output location. Retraining is deliberately manual; a web request never trains a model.

## Guardrails

- Only authenticated Authority users can call the billing endpoints.
- Numeric inputs are validated by Pydantic and the prediction service; negative amounts, invalid months, and invalid target periods are rejected.
- The selected model artifact and rule file must exist before a forecast can run.
- Source-data limitations are shown as advisory notes in the modal, not as a generic red failure. An area is required for a manual forecast, and an unmatched structure must be explicitly selected rather than silently mapped. No value is invented: the only area fallback is the explicit `AREA <number> SQM` text pattern described above.
