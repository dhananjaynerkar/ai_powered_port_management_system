# Data-quality audit

## Verified handling

- Empty/blank display values are normalized to Not provided in API responses.
- Historical commencement dates before 1900 display as Historical date rather
  than being silently rewritten.
- Invalid date formats display as Invalid date and are counted in dashboard
  quality data.
- Mapping records without tenancy IDs, contacts, purposes, plot links, start
  dates, and end dates are counted.
- Orphan mapping records are counted by left joining applicant_registration.
- Source strings are not altered in the database by the dashboard query.

Evidence: api.py _date_display, _authority_land_metrics, _tenant_terminology,
and authority metric tests.

## Semantic controls

The dashboard explicitly separates:

- plot status
- vacancy
- derived land occupancy
- tenancy lifecycle
- mapping status
- lease type
- tenant structure
- billing periodicity
- allotment

This prevents Running/Expired and Monthly/Joint/Yearly from being treated as one
dimension.

## Remaining data-quality risks

| Risk | Evidence | Status |
| --- | --- | --- |
| Mapping rows may be mistaken for unique tenants | API returns record_label and terminology definitions. | Controlled by terminology contract; business master count NOT VERIFIED. |
| Source historical dates may be sentinel/default values | API reports historical dates but does not rewrite source. | Requires business validation. |
| N/A/Not provided may hide different missingness causes | Several fields use fallback labels. | Could be improved with field-level quality reasons. |
| Status code meanings may be business-dependent | m_property_status is joined for labels. | Current code uses source labels; formal domain dictionary NOT VERIFIED. |
| Billing/tender source exports may have missing fields | Services emit warnings and leave unapproved inputs blank. | Controlled, but source remediation remains. |

## Required quality policy

Do not replace source values with guessed corrections. Add reviewed business
definitions, source-quality dashboards, and fixture-based tests when a domain
owner confirms the meaning of historical dates, status codes, and mapping
relationships.

