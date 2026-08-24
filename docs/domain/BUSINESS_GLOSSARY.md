# Business glossary

## Purpose

This glossary prevents the dashboard, tenant registry, API, and source schema
from using *tenant*, *tenancy*, *mapping*, *status*, and *occupancy*
interchangeably. A display name is used only where its technical source and
calculation are explicit. Unproven business interpretations are marked
**DOMAIN SIGN-OFF REQUIRED** instead of being inferred from a column name.

## Controlled terms

| Display term | Technical source | Verified meaning in this application | Limitation / sign-off |
| --- | --- | --- | --- |
| Applicant profile | `public.applicant_registration` row keyed by `applicant_id` | A source applicant-registration profile. The API counts distinct profiles that join to a mapping row. | This is not asserted to be a unique legal person or organization without domain confirmation. **DOMAIN SIGN-OFF REQUIRED**. |
| Applicant ID represented | Distinct `public.applicant_property_mapping.tenant_id` | Distinct values of the mapping table's applicant key. The API joins this key to `applicant_registration.applicant_id`. | The source column is named `tenant_id`; this contract does not rename or claim it is a tenant master identifier. |
| Applicant-property mapping record | One row in `public.applicant_property_mapping` | One source relationship record linking an applicant key to property/tenancy attributes. | It is not a unique tenant count and not an active-tenancy count. |
| Tenancy identifier | Distinct non-empty `public.applicant_property_mapping.tenancy_id` | Distinct populated identifier values present in mapping rows. | No active/inactive tenancy master field is exposed by this contract. **DOMAIN SIGN-OFF REQUIRED** for calling these legal tenancies. |
| Plot record | One row in `public.plot` | A source property/plot record. `area` is the source land-area value. | Plot status and vacancy are separate source dimensions. |
| Plot status | `public.plot.status` joined to `public.m_property_status.status_id` | The source status label from the lookup table. Live metadata currently reports `A = Approved`, `V = Verified`, and `RG = Registered`. | These labels are source metadata, not proof that a status is an occupancy or lifecycle state. Official domain semantics beyond the stored label are **DOMAIN SIGN-OFF REQUIRED**. |
| Vacancy flag | `public.plot.is_vacant` | Nullable boolean source flag: `true`, `false`, or `null`. | `false` is displayed as “Not vacant”; it is not automatically renamed “Occupied”. **DOMAIN SIGN-OFF REQUIRED** for that synonym. |
| Plot status and vacancy classification | API's exclusive derived view | A non-source classification with precedence `status = RG`, then `is_vacant = true/false`, then `Unclassified`. | The precedence is an application reporting rule; it must not be interpreted as a business state machine. |
| Mapping record status | `public.applicant_property_mapping.status` | Source status text for each mapping row, with blank values shown as “Not provided”. | It is distinct from plot status and from derived tenure classification. |
| Source tenure value | `public.applicant_property_mapping.tenancy_type` | Raw/grouped source values used for the lease/tenure chart. | The source field is not proven to be a lifecycle field. |
| Derived tenure classification | API rule over `tenancy_type` | `Expired` when the trimmed value contains `expired` or the source typo `exipred`; non-empty other values are `Running`; blank values are `Unclassified`. | This is not a source lifecycle or active-tenancy status. **DOMAIN SIGN-OFF REQUIRED** before using “active”, “running tenancy”, or similar legal language. |
| Tenant structure | `public.applicant_property_mapping.tenant_type` | Separate source grouping dimension, with blank values as “Not provided”. | It must not be merged with lease type or lifecycle. |
| Billing periodicity | `public.applicant_property_mapping.bill_periodicity` | Separate source grouping dimension, with blank values as “Not provided”. | It is not a tenancy status. |
| Allotment flag | `public.applicant_property_mapping.is_alloted` | Nullable source boolean shown as `Allotted`, `Not allotted`, or `Not provided`. | The business meaning and spelling of the source field require domain confirmation. |

## Missingness and dates

The API renders blank values as `Not provided` (the UI presents this as `—`),
and displays valid dates before 1900 as `Historical date`. It does not rewrite
the source. Whether a historical date is a legitimate record or a sentinel is
**DOMAIN SIGN-OFF REQUIRED**.

## Compatibility names

The API retains the historical response keys `tenancy_lifecycle_breakdown` and
`land_occupancy_breakdown` for client compatibility. Their UI labels and source
definitions are intentionally more precise: **Derived tenure classification**
and **Plot status and vacancy classification**. The keys must not be read as
proof of the corresponding business concepts.

