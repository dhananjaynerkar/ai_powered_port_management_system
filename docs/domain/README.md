# Domain terminology and metric contracts

This folder is the canonical contract for user-facing business terms in the
authority dashboard and applicant-property registry. It is deliberately
separate from the raw PMS schema: source column names are preserved, while
display labels describe only meanings that are supported by the inspected code
and database metadata.

## Documents

- [Business glossary](BUSINESS_GLOSSARY.md) — controlled terms, source fields,
  and unresolved domain decisions.
- [Metric definitions](METRIC_DEFINITIONS.md) — dashboard and tenant-registry
  metrics with their calculation, unit, interpretation, and limitations.

## Evidence boundary

The contract was checked against the live `public` catalog and the current
metric/tenant API implementation on 2026-08-24. The check inspected table and
column metadata, key constraints, the `m_property_status` labels for `A`, `V`,
and `RG`, SQL expressions in `api.py`, and the corresponding regression tests.
No source rows, credentials, or personal data are included here.

The following decisions remain **DOMAIN SIGN-OFF REQUIRED** because the current
schema does not prove the business interpretation:

- whether an applicant-property mapping represents a legal tenancy;
- whether `is_vacant = false` should be called “occupied” in business language;
- whether `tenancy_type` values can be treated as a lifecycle/status field;
- whether historical dates before 1900 are valid historical records or sentinel
  values;
- the official business meaning of status codes beyond the labels stored in
  `public.m_property_status`.

