# Dashboard and tenant-table audit

## Dashboard metric contract

The Authority dashboard route is GET /api/authority/dashboard/metrics and calls
_authority_land_metrics. It reads public.plot for total plot count/area,
public.m_property_status for status labels, public.plot.is_vacant for vacancy,
and public.applicant_property_mapping plus applicant_registration for tenancy
and quality dimensions.

Returned dimensions include plot_status_breakdown, vacancy_breakdown,
land_occupancy_breakdown, tenancy_lifecycle_breakdown,
tenancy_record_status_breakdown, lease_type_breakdown,
tenant_structure_breakdown, billing_periodicity_breakdown, allotment_breakdown,
tenant_terminology, and data_quality.

The code deliberately keeps status, lease type, tenant structure, and billing
periodicity separate. Occupancy classification is derived as RG first, then
is_vacant true/false, then unclassified. Business confirmation of that mapping
is required before changing labels.

## Tenant record meaning

GET /api/authority/tenants returns applicant-property mapping rows. It returns
record_label and terminology definitions so the UI does not call 3,841 mapping
rows a unique tenant count. It also exposes distinct applicant IDs, tenancy
identifiers, matched profiles, missing tenancy identifiers, and orphan records
through tenant_terminology.

## Tenant table behavior

Search, status, lease type, allotment, date range, page size, sort column, and
sort direction are server-side. Sort columns are allowlisted. Page size is
clamped to 1–100. Date syntax and range order are validated. Historical dates
are displayed safely.

## Tests

test_authority_metrics.py protects aggregate reconciliation and terminology.
test_tenant_pagination.py protects filter options, page size, live lease
filtering, page clamping, and invalid dates.

## Gaps

- Unique tenant master count is NOT VERIFIED because the source model does not
  expose a canonical tenant master in inspected code.
- Table load/performance at much larger volumes is NOT MEASURED.
- Tenant detail route/click-through is not present in the inspected API map.
- Business definitions for status code A/V/RG require domain-owner confirmation.

