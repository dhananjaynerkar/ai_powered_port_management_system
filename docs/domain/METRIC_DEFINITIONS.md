# Metric definitions

All values below are produced by `src/portproject_rag/api.py` and are scoped to
the authenticated authority dashboard. Counts come from the live PostgreSQL
`public` schema; no values are hard-coded in the UI. Area values are sourced
from `public.plot.area` and are returned as square metres plus hectares
(`sqm / 10,000`).

## Dashboard metrics

| Display metric | API field / source | Calculation | Unit | Interpretation | Limitation |
| --- | --- | --- | --- | --- | --- |
| Total plot records | `total_plot_records` / `public.plot` | `COUNT(*)` | records | Number of source plot rows. | Not a count of occupied plots or land parcels after business deduplication. |
| Total land area | `total_land` / `public.plot.area` | `SUM(area)` | sq.m and ha | Sum of source plot areas. | Source area quality and parcel overlap are not validated here. |
| Approved land (A) | `approved_land` / `plot.status = 'A'` joined to lookup | Sum of `area` for source status code `A` | sq.m and ha | Area attached to the source status label `Approved`. | Approval is not asserted to mean occupancy. |
| Vacant land (`is_vacant`) | `vacant_land` / `public.plot.is_vacant` | Sum of `area` where `is_vacant IS TRUE` | sq.m and ha | Area explicitly flagged vacant in the source. | Null and false are not included; business definition of vacancy is source-dependent. |
| Not-vacant land (`is_vacant`) | `non_vacant_land` / `public.plot.is_vacant` | Sum of `area` where `is_vacant IS FALSE` | sq.m and ha | Area explicitly not flagged vacant. | It is intentionally not called occupied without domain sign-off. |
| Registered land (RG) | `registered_land` / `plot.status = 'RG'` joined to lookup | Sum of `area` for source status code `RG` | sq.m and ha | Area attached to source status label `Registered`. | Registration is not asserted to mean pending/occupied. |
| Plot status distribution | `plot_status_breakdown` | Group `public.plot` by `status` and lookup label; count and sum `area` | records and ha | Source status breakdown. | Status business semantics beyond stored labels require sign-off. |
| Vacancy breakdown | `vacancy_breakdown` | Group `public.plot` by nullable `is_vacant` | records and ha | Explicit true/false/null vacancy flag distribution. | It is separate from status and from the exclusive classification below. |
| Plot status and vacancy classification | `land_occupancy_breakdown` (compatibility key) | `RG` first; then `is_vacant=true`; then `is_vacant=false`; else unclassified | records and ha | A mutually exclusive reporting view that prevents double counting area. | This is a reporting precedence rule, not a legal occupancy model. “Not vacant” is used instead of unverified “Occupied”. |

## Applicant-property dimensions

| Display metric | API field / source | Calculation | Unit | Interpretation | Limitation |
| --- | --- | --- | --- | --- | --- |
| Applicant-property mapping records | `tenant_terminology.mapping_records`, `data_quality.mapping_records`, `tenancy_record_count` / `public.applicant_property_mapping` | `COUNT(*)` | records | Number of source mapping rows. | Not a unique tenant count and not an active-tenancy count. |
| Applicant IDs represented | `tenant_terminology.applicant_ids` | `COUNT(DISTINCT apm.tenant_id)` | IDs | Distinct applicant keys appearing in mapping rows. | Source key is named `tenant_id`; no separate tenant master count is asserted. |
| Tenancy identifiers | `tenant_terminology.tenancy_identifiers` | `COUNT(DISTINCT NULLIF(BTRIM(tenancy_id), ''))` | identifiers | Distinct non-empty source tenancy identifier values. | Not proof of active or legally current tenancies. |
| Matched applicant profiles | `tenant_terminology.matched_applicant_profiles` | `COUNT(DISTINCT ar.applicant_id)` after left join on `apm.tenant_id = ar.applicant_id` | profiles | Registration profiles matched by the application join. | The inspected catalog does not expose that join as a foreign-key constraint; unmatched rows are reported separately. |
| Derived tenure classification | `tenancy_lifecycle_breakdown` (compatibility key) | Classify `tenancy_type`: expired/exipred → Expired; other non-empty → Running; blank → Unclassified | mapping records | A transparent application-derived grouping. | Not a source lifecycle field or active-tenancy status. |
| Source lease / tenure values | `lease_type_breakdown` / `tenancy_type` | Group trimmed source values with only known display normalizations (`fifteen monthly`, `exipred lease`) | mapping records | Separate source-value distribution. | Raw values may mix term, lease, or frequency concepts; domain taxonomy is **DOMAIN SIGN-OFF REQUIRED**. |
| Tenant structure | `tenant_structure_breakdown` / `tenant_type` | Group trimmed source values | mapping records | Separate source structure distribution. | Must not be merged with lease type. |
| Billing periodicity | `billing_periodicity_breakdown` / `bill_periodicity` | Group trimmed source values | mapping records | Separate source billing-frequency distribution. | Not a lifecycle/status dimension. |
| Allotment | `allotment_breakdown` / `is_alloted` | Group true/false/null as Allotted/Not allotted/Unknown | mapping records | Explicit source allotment flag distribution. | Source field spelling and business meaning require sign-off. |

## Data-quality indicators

`data_quality` reports orphan mapping rows, missing contact/purpose/plot links,
missing start/end dates, historical start dates, and invalid start dates. These
are diagnostics and are not silently subtracted from the headline metrics.

## Contract rules

1. The API field names above remain stable for existing clients.
2. UI labels must use the verified display terms, not inferred legal language.
3. Raw source values are not rewritten by reporting queries.
4. Any change from “Not vacant” to “Occupied”, or from “Derived tenure
   classification” to “Active tenancy”, requires documented domain-owner
   sign-off and a separate migration/test review.

