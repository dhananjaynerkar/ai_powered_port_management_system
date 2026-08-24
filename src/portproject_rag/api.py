from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from time import perf_counter
from typing import Any, cast
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg import connect
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from .auth import (
    SESSION_COOKIE,
    PortalUser,
    authenticate,
    check_login_rate_limit,
    create_session,
    current_user,
    delete_session,
    record_login_attempt,
)
from .billing import BillingPredictionRequest, BillingPredictionService
from .database import migrate
from .generation import generate_grounded_answer
from .guardrails import validate_query
from .retrieval import RetrievedChunk, _rerank, retrieve
from .settings import Settings
from .tender_workflow import TenderWorkflowError, TenderWorkflowService
from .workflow import (
    add_agenda_message,
    agenda_detail,
    authority_identity,
    create_agenda_from_chat,
    list_agendas,
    officer_directory,
    save_agenda_revision,
    transition_agenda,
)


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=120, pattern=r"^[A-Za-z0-9@._-]+$")
    password: str = Field(min_length=1, max_length=256)


class InitialSetup(Credentials):
    display_name: str = Field(min_length=2, max_length=160)
    role: str = Field(pattern=r"^(authority|tenant)$")


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=20000)
    limit: int | None = Field(default=None, ge=1, le=20)
    chat_session_id: UUID | None = None
    llm_model: str | None = Field(default=None, max_length=256, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")


class ForwardDraftRequest(BaseModel):
    chat_session_id: UUID
    title: str | None = Field(default=None, max_length=180)


class AgendaTransitionRequest(BaseModel):
    action: str = Field(pattern=r"^(submit_to_nodal|return_to_do|submit_to_hod|approve|reject)$")
    target_principal: str | None = Field(default=None, max_length=80)
    note: str = Field(default="", max_length=4000)


class AgendaQuestionRequest(BaseModel):
    question: str = Field(min_length=2, max_length=20000)
    limit: int | None = Field(default=None, ge=1, le=20)
    llm_model: str | None = Field(default=None, max_length=256, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")


class AgendaRevisionRequest(BaseModel):
    draft_text: str = Field(min_length=1, max_length=30000)


class BillingRequest(BaseModel):
    """Validated payload for the source-backed billing forecast form."""

    customer_id: str = Field(default="", max_length=120)
    chat_session_id: UUID | None = None
    tenancy_id: str | None = Field(default=None, max_length=120)
    target_year: int = Field(default=0, ge=2000, le=2200)
    target_month: int = Field(default=0, ge=0, le=12)
    bill_type: str = Field(default="", max_length=80)
    current_year: int | None = Field(default=None, ge=2000, le=2200)
    current_month: int | None = Field(default=None, ge=1, le=12)
    structure_type: str | None = Field(default=None, max_length=80)
    water_tax_included: bool | None = None
    present_year: int | None = Field(default=None, ge=2000, le=2200)
    present_month: int | None = Field(default=None, ge=1, le=12)
    present_amount: float | None = Field(default=None, ge=0)
    present_cgst: float | None = Field(default=None, ge=0)
    present_sgst: float | None = Field(default=None, ge=0)
    billing_frequency: str | None = Field(default=None, max_length=40)
    area: float | None = Field(default=None, ge=0)
    line_category: str | None = Field(default=None, max_length=80)
    rates: dict[str, float] = Field(default_factory=dict)
    allocated_rate_keys: list[str] = Field(default_factory=list, max_length=32)


class TenderWorkflowCreateRequest(BaseModel):
    plot_id: str = Field(min_length=1, max_length=120)
    checklist_key: str = Field(min_length=1, max_length=80)
    fields: dict[str, object] = Field(default_factory=dict)
    checklist_answers: dict[str, str] = Field(default_factory=dict)


class TenderWorkflowActionRequest(BaseModel):
    action: str = Field(min_length=1, max_length=80)
    fields: dict[str, object] = Field(default_factory=dict)
    checklist_answers: dict[str, str] = Field(default_factory=dict)
    comment: str = Field(default="", max_length=4000)


class TenderCalculationRequest(BaseModel):
    fields: dict[str, object] = Field(default_factory=dict)


def _settings() -> Settings:
    return Settings()


def _stats(settings: Settings) -> dict[str, int]:
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"""SELECT COUNT(*), COALESCE(SUM(page_count), 0) FROM {settings.document_schema_name}.document_record d
                WHERE EXISTS (SELECT 1 FROM {settings.vector_schema_name}.document_chunk c WHERE c.document_id=d.document_id)""")
            documents, pages = cursor.fetchone()
            cursor.execute(f"""SELECT COUNT(*) FROM {settings.document_schema_name}.document_record d
                WHERE NOT EXISTS (SELECT 1 FROM {settings.vector_schema_name}.document_chunk c WHERE c.document_id=d.document_id)""")
            pending_documents = cursor.fetchone()[0]
            cursor.execute(f"SELECT COUNT(*) FROM {settings.vector_schema_name}.document_chunk")
            chunks = cursor.fetchone()[0]
            cursor.execute(f"SELECT COUNT(*) FROM {settings.vector_schema_name}.chunk_embedding WHERE embedding IS NOT NULL")
            vectors = cursor.fetchone()[0]
    return {"documents": documents, "pages": int(pages), "pending_documents": pending_documents, "chunks": chunks, "vectors": vectors}


def _corpus_state(settings: Settings) -> dict[str, object]:
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"""SELECT d.document_id, d.original_filename, d.page_count,
                COUNT(DISTINCT c.chunk_id), COUNT(DISTINCT e.chunk_id)
                FROM {settings.document_schema_name}.document_record d
                LEFT JOIN {settings.vector_schema_name}.document_chunk c ON c.document_id=d.document_id
                LEFT JOIN {settings.vector_schema_name}.chunk_embedding e ON e.chunk_id=c.chunk_id
                GROUP BY d.document_id, d.original_filename, d.page_count
                ORDER BY d.original_filename""")
            rows = cursor.fetchall()
    return {
        **_stats(settings),
        "documents_state": [
            {"document_id": str(row[0]), "filename": row[1], "pages": row[2], "chunks": row[3], "embeddings": row[4], "indexed": row[3] > 0 and row[3] == row[4]}
            for row in rows
        ],
    }


def _user_payload(user: PortalUser) -> dict[str, str]:
    role_title = "Tenant"
    if user.role == "authority":
        role_title = {"HO": "Head of Department", "NO": "Nodal Officer", "DO": "Data Entry Operator"}.get(user.principal_id.split(":", 1)[0], "Authority Officer")
        try:
            admin_id = int(user.principal_id.split(":", 1)[1])
            with connect(app.state.settings.database_url.unicode_string()) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT role_id FROM public.admin_roles WHERE admin_id=%s AND is_active IS TRUE ORDER BY admin_role_id LIMIT 1", (admin_id,))
                    row = cursor.fetchone()
            role_title = {"HO": "Head of Department", "NO": "Nodal Officer", "DO": "Data Entry Operator"}.get(row[0] if row else "", "Authority Officer")
        except (IndexError, ValueError):
            pass
    return {"user_id": str(user.user_id) if user.user_id else user.principal_id, "username": user.username, "name": user.display_name, "role": user.role, "role_title": role_title}


def _log(settings: Settings, user: PortalUser | None, event_type: str, metadata: dict[str, object]) -> None:
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {settings.schema_name}.audit_event (user_id, principal_id, event_type, metadata) VALUES (%s, %s, %s, %s)",
                (user.user_id if user else None, user.principal_id if user else None, event_type, Jsonb(metadata)),
            )


def build_evidence_payload(results: list[RetrievedChunk]) -> list[dict[str, object]]:
    """Build the single source/citation representation returned by every answer route."""
    return [
        {
            "source_id": item.source_id,
            "document_id": str(item.document_id),
            "chunk_id": str(item.chunk_id),
            "title": item.document_title,
            "filename": item.filename,
            "page": item.page_number,
            "section_title": item.section_title,
            "clause_number": item.clause_number,
            "excerpt": item.chunk_text,
            "score": item.rerank_score,
            "fused_score": item.fused_score,
            "lexical_rank": item.lexical_rank,
            "dense_rank": item.dense_rank,
        }
        for item in results
    ]


def _ollama_api_base(settings: Settings) -> str:
    return settings.generation_endpoint.unicode_string().rsplit("/", 1)[0]


def _local_completion_models(settings: Settings) -> list[str]:
    """Discover local Ollama models that explicitly support text completion."""
    with httpx.Client(timeout=settings.generation_timeout_seconds) as client:
        tags = client.get(f"{_ollama_api_base(settings)}/tags")
        tags.raise_for_status()
        names = [item.get("name") for item in tags.json().get("models", []) if isinstance(item.get("name"), str)]
        models: list[str] = []
        for name in names:
            details = client.post(f"{_ollama_api_base(settings)}/show", json={"name": name})
            details.raise_for_status()
            if "completion" in details.json().get("capabilities", []):
                models.append(name)
    return sorted(set(models), key=str.casefold)


def _selected_local_model(settings: Settings, requested_model: str | None) -> str:
    if requested_model is None:
        return settings.llm_primary_model
    try:
        available = _local_completion_models(settings)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Local model catalog is unavailable.") from exc
    if requested_model not in available:
        raise HTTPException(status_code=400, detail="The selected model is not available for local text generation.")
    return requested_model


def _answer_payload(
    settings: Settings, question: str, limit: int | None, user_role: str, llm_model: str | None = None
) -> dict[str, object]:
    started = perf_counter()
    selected_model = _selected_local_model(settings, llm_model)
    retrieval = retrieve(settings, question, user_role, limit)
    generated = generate_grounded_answer(settings, question, retrieval.chunks, selected_model)
    timings = {
        "embed_ms": retrieval.timings.embed_ms,
        "lexical_retrieval_ms": retrieval.timings.lexical_retrieval_ms,
        "dense_retrieval_ms": retrieval.timings.dense_retrieval_ms,
        "rerank_ms": retrieval.timings.rerank_ms,
        "context_assembly_ms": retrieval.timings.context_assembly_ms,
        "generation_ms": generated.generation_ms,
        "citation_validation_ms": generated.citation_validation_ms,
    }
    return {
        "answer": generated.answer,
        "sources": build_evidence_payload(retrieval.chunks),
        "citation_valid": generated.citation_valid,
        "citation_error": generated.citation_error,
        "route": "DOCUMENT_RAG",
        "llm_model": selected_model,
        "candidate_count": retrieval.candidate_count,
        "timings": timings,
        "duration_ms": round((perf_counter() - started) * 1000),
    }


def _dashboard_metrics(settings: Settings) -> dict[str, object]:
    schema = settings.schema_name
    stats = _stats(settings)
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COALESCE(ROUND(AVG(extraction_quality)), 0) FROM {schema}.document")
            mean_quality = int(cursor.fetchone()[0])
            cursor.execute(f"""SELECT COALESCE(classification, 'unclassified'), COUNT(*)
                FROM {schema}.document GROUP BY classification ORDER BY COUNT(*) DESC, classification""")
            classification_breakdown = [{"name": row[0].replace("_", " ").title(), "count": row[1]} for row in cursor.fetchall()]
            cursor.execute(f"""SELECT extraction_strategy, COUNT(*) FROM {schema}.document
                GROUP BY extraction_strategy ORDER BY COUNT(*) DESC, extraction_strategy""")
            strategy_breakdown = [{"name": row[0].replace("_", " ").title(), "count": row[1]} for row in cursor.fetchall()]
    return {**stats, "mean_extraction_quality": mean_quality, "classification_breakdown": classification_breakdown, "strategy_breakdown": strategy_breakdown}


_BREAKDOWN_COLORS = ("#254c80", "#d72e2e", "#4f84b7", "#29934d", "#d49e00", "#8f46bd", "#3199a6")


def _label(value: object, fallback: str = "Not provided") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _date_display(value: object) -> str:
    """Keep raw dates intact in storage but avoid presenting sentinel dates as current facts."""
    text = str(value or "").strip()
    if not text:
        return "Not provided"
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return "Invalid date"
    return "Historical date" if parsed.year < 1900 else text


def _as_int(value: object) -> int:
    return int(str(value or 0))


def _as_float(value: object) -> float:
    return float(str(value or 0))


def _count_breakdown(rows: list[tuple[object, object]]) -> list[dict[str, object]]:
    return [
        {"name": _label(name), "count": _as_int(count), "color": _BREAKDOWN_COLORS[index % len(_BREAKDOWN_COLORS)]}
        for index, (name, count) in enumerate(rows)
    ]


def _area_breakdown(rows: list[tuple[object, object, object, object]]) -> list[dict[str, object]]:
    return [
        {
            "code": str(code) if code is not None else None,
            "name": _label(name, "Unknown"),
            "count": _as_int(count),
            "area_sqm": _as_float(area),
            "value": _as_float(area) / 10000,
            "color": _BREAKDOWN_COLORS[index % len(_BREAKDOWN_COLORS)],
        }
        for index, (code, name, count, area) in enumerate(rows)
    ]


def _tenant_terminology(cursor: Any) -> dict[str, object]:
    """Return one live terminology contract for tenant-related data.

    The source model stores applicant-property relationships in
    ``applicant_property_mapping``.  It does not provide a canonical tenant
    master count or an explicit active-tenancy field, so the API keeps those
    concepts distinct and exposes the live counts alongside their definitions.
    """

    cursor.execute("""SELECT
            COUNT(*) AS mapping_records,
            COUNT(DISTINCT apm.tenant_id) AS applicant_ids,
            COUNT(DISTINCT NULLIF(BTRIM(apm.tenancy_id), '')) AS tenancy_ids,
            COUNT(DISTINCT ar.applicant_id) AS matched_applicant_profiles,
            COUNT(*) FILTER (WHERE NULLIF(BTRIM(apm.tenancy_id), '') IS NULL) AS missing_tenancy_ids,
            COUNT(*) FILTER (WHERE ar.applicant_id IS NULL) AS orphan_mapping_records
        FROM public.applicant_property_mapping apm
        LEFT JOIN public.applicant_registration ar ON ar.applicant_id = apm.tenant_id""")
    counts = cursor.fetchone() or (0, 0, 0, 0, 0, 0)
    mapping_count = _as_int(counts[0])
    return {
        "mapping_records": {
            "count": mapping_count,
            "label": "Applicant-property mapping records",
            "definition": "Rows in public.applicant_property_mapping representing applicant-property relationships; this is not a unique tenant or active-tenancy count.",
        },
        "applicant_ids": {
            "count": _as_int(counts[1]),
            "label": "Applicant IDs represented",
            "definition": "Distinct public.applicant_property_mapping.tenant_id values; this is the mapping table's applicant key, not a tenant master-profile count.",
        },
        "tenancy_identifiers": {
            "count": _as_int(counts[2]),
            "label": "Tenancy identifiers",
            "definition": "Distinct non-empty public.applicant_property_mapping.tenancy_id values; this is not a count of active tenancies.",
        },
        "matched_applicant_profiles": {
            "count": _as_int(counts[3]),
            "label": "Matched applicant profiles",
            "definition": "Distinct applicant_registration profiles joined by applicant_id to a mapping record.",
        },
        "missing_tenancy_identifiers": {
            "count": _as_int(counts[4]),
            "label": "Mapping records without a tenancy identifier",
            "definition": "Applicant-property mapping rows whose tenancy_id is null or blank.",
        },
        "orphan_mapping_records": {
            "count": _as_int(counts[5]),
            "label": "Mapping records without a matched applicant profile",
            "definition": "Applicant-property mapping rows with no matching applicant_registration row.",
        },
        "lifecycle_records": {
            "count": mapping_count,
            "label": "Tenancy lifecycle records (derived)",
            "definition": "Applicant-property mapping records classified from tenancy_type; the database does not expose a canonical active-tenancy master field here.",
        },
    }


def _authority_land_metrics(settings: Settings) -> dict[str, object]:
    """Return live, separately-defined plot and tenancy metrics for the dashboard.

    The source tables contain several different concepts. This function keeps
    plot status, vacancy, tenancy-record status, lease type, tenant structure,
    and billing periodicity separate instead of presenting them as one chart.
    Raw database rows are not modified here.
    """

    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT COUNT(*), COALESCE(SUM(area), 0)
                FROM public.plot""")
            plot_count, total_sqm = cursor.fetchone() or (0, 0)

            cursor.execute("""SELECT p.status,
                    COALESCE(NULLIF(BTRIM(s.status), ''), p.status, 'Unknown'),
                    COUNT(*), COALESCE(SUM(p.area), 0)
                FROM public.plot p
                LEFT JOIN public.m_property_status s ON s.status_id = p.status
                GROUP BY p.status, s.status
                ORDER BY p.status NULLS LAST""")
            plot_status_rows = cursor.fetchall()

            cursor.execute("""SELECT CASE
                    WHEN is_vacant IS TRUE THEN 'Vacant (is_vacant=true)'
                    WHEN is_vacant IS FALSE THEN 'Not vacant (is_vacant=false)'
                    ELSE 'Unknown (is_vacant is null)'
                END, COUNT(*), COALESCE(SUM(area), 0)
                FROM public.plot
                GROUP BY is_vacant
                ORDER BY is_vacant NULLS LAST""")
            vacancy_rows = cursor.fetchall()

            cursor.execute("""WITH classified AS (
                    SELECT CASE
                        WHEN status = 'RG' THEN 'Registered'
                        WHEN is_vacant IS TRUE THEN 'Vacant'
                        WHEN is_vacant IS FALSE THEN 'Occupied'
                        ELSE 'Unclassified'
                    END AS category, area
                    FROM public.plot
                )
                SELECT category, COUNT(*), COALESCE(SUM(area), 0)
                FROM classified
                GROUP BY category
                ORDER BY CASE category
                    WHEN 'Occupied' THEN 1
                    WHEN 'Vacant' THEN 2
                    WHEN 'Registered' THEN 3
                    ELSE 4
                END""")
            occupancy_rows = cursor.fetchall()

            cursor.execute("""WITH classified AS (
                    SELECT CASE
                        WHEN NULLIF(BTRIM(tenancy_type), '') IS NULL THEN 'Unclassified'
                        WHEN LOWER(BTRIM(tenancy_type)) LIKE '%expired%'
                            OR LOWER(BTRIM(tenancy_type)) LIKE '%exipred%' THEN 'Expired'
                        ELSE 'Running'
                    END AS category
                    FROM public.applicant_property_mapping
                )
                SELECT category, COUNT(*)
                FROM classified
                GROUP BY category
                ORDER BY CASE category
                    WHEN 'Running' THEN 1
                    WHEN 'Expired' THEN 2
                    ELSE 3
                END""")
            tenancy_lifecycle_rows = cursor.fetchall()

            cursor.execute("""SELECT COALESCE(NULLIF(BTRIM(status), ''), 'Not provided'), COUNT(*)
                FROM public.applicant_property_mapping
                GROUP BY COALESCE(NULLIF(BTRIM(status), ''), 'Not provided')
                ORDER BY COUNT(*) DESC, 1""")
            record_status_rows = cursor.fetchall()

            cursor.execute("""SELECT CASE
                    WHEN LOWER(BTRIM(tenancy_type)) = 'fifteen monthly' THEN '15-Monthly'
                    WHEN LOWER(BTRIM(tenancy_type)) = 'exipred lease' THEN 'Expired Lease'
                    ELSE COALESCE(NULLIF(BTRIM(tenancy_type), ''), 'Not provided')
                END, COUNT(*)
                FROM public.applicant_property_mapping
                GROUP BY 1
                ORDER BY COUNT(*) DESC, 1""")
            lease_type_rows = cursor.fetchall()

            cursor.execute("""SELECT COALESCE(NULLIF(BTRIM(tenant_type), ''), 'Not provided'), COUNT(*)
                FROM public.applicant_property_mapping
                GROUP BY COALESCE(NULLIF(BTRIM(tenant_type), ''), 'Not provided')
                ORDER BY COUNT(*) DESC, 1""")
            tenant_structure_rows = cursor.fetchall()

            cursor.execute("""SELECT COALESCE(NULLIF(BTRIM(bill_periodicity), ''), 'Not provided'), COUNT(*)
                FROM public.applicant_property_mapping
                GROUP BY COALESCE(NULLIF(BTRIM(bill_periodicity), ''), 'Not provided')
                ORDER BY COUNT(*) DESC, 1""")
            billing_rows = cursor.fetchall()

            cursor.execute("""SELECT CASE
                    WHEN is_alloted IS TRUE THEN 'Allotted'
                    WHEN is_alloted IS FALSE THEN 'Not allotted'
                    ELSE 'Unknown'
                END, COUNT(*)
                FROM public.applicant_property_mapping
                GROUP BY is_alloted
                ORDER BY is_alloted NULLS LAST""")
            allotment_rows = cursor.fetchall()

            cursor.execute("""SELECT
                    COUNT(*) AS mapping_records,
                    COUNT(ar.applicant_id) AS matched_applicants,
                    COUNT(*) FILTER (WHERE ar.applicant_id IS NULL) AS orphan_mappings,
                    COUNT(*) FILTER (WHERE NULLIF(BTRIM(ar.authorised_person_name), '') IS NULL) AS missing_contact_person,
                    COUNT(*) FILTER (WHERE NULLIF(BTRIM(apm.purpose), '') IS NULL) AS missing_purpose,
                    COUNT(*) FILTER (WHERE apm.property_id IS NULL OR apm.property_id = 0) AS missing_plot_links,
                    COUNT(*) FILTER (WHERE NULLIF(BTRIM(apm.duration_from), '') IS NULL) AS missing_start_dates,
                    COUNT(*) FILTER (WHERE NULLIF(BTRIM(apm.duration_to), '') IS NULL) AS missing_end_dates,
                    COUNT(*) FILTER (WHERE NULLIF(BTRIM(apm.duration_from), '') IS NOT NULL
                        AND BTRIM(apm.duration_from) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                        AND LEFT(BTRIM(apm.duration_from), 4)::int < 1900) AS historical_start_dates,
                    COUNT(*) FILTER (WHERE NULLIF(BTRIM(apm.duration_from), '') IS NOT NULL
                        AND (BTRIM(apm.duration_from) !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                            OR to_char(to_date(BTRIM(apm.duration_from), 'YYYY-MM-DD'), 'YYYY-MM-DD') <> BTRIM(apm.duration_from))) AS invalid_start_dates
                FROM public.applicant_property_mapping apm
                LEFT JOIN public.applicant_registration ar ON ar.applicant_id = apm.tenant_id""")
            quality = cursor.fetchone() or (0,) * 10
            tenant_terminology = _tenant_terminology(cursor)

    def land(value: object) -> dict[str, str]:
        numeric = _as_float(value)
        return {"sqm": f"{numeric:,.2f} sq.m", "hectares": f"{numeric / 10000:,.2f} ha"}

    status_breakdown = _area_breakdown(plot_status_rows)
    vacancy_breakdown = _area_breakdown([(None, name, count, area) for name, count, area in vacancy_rows])
    occupancy_breakdown = _area_breakdown([(None, name, count, area) for name, count, area in occupancy_rows])
    status_by_code = {item["code"]: item for item in status_breakdown}
    approved = status_by_code.get("A", {"area_sqm": 0})
    registered = status_by_code.get("RG", {"area_sqm": 0})
    vacant = next((item for item in vacancy_breakdown if str(item["name"]).startswith("Vacant (")), {"area_sqm": 0})
    non_vacant = next((item for item in vacancy_breakdown if str(item["name"]).startswith("Not vacant (")), {"area_sqm": 0})

    return {
        "total_plot_records": f"{_as_int(plot_count):,} plots",
        "total_land": land(total_sqm),
        "approved_land": land(approved["area_sqm"]),
        "vacant_land": land(vacant["area_sqm"]),
        "non_vacant_land": land(non_vacant["area_sqm"]),
        "registered_land": land(registered["area_sqm"]),
        "plot_status_breakdown": status_breakdown,
        "vacancy_breakdown": vacancy_breakdown,
        "land_occupancy_breakdown": occupancy_breakdown,
        "tenancy_record_count": _as_int(quality[0]),
        "tenancy_lifecycle_breakdown": _count_breakdown(tenancy_lifecycle_rows),
        "tenancy_record_status_breakdown": _count_breakdown(record_status_rows),
        "lease_type_breakdown": _count_breakdown(lease_type_rows),
        "tenant_structure_breakdown": _count_breakdown(tenant_structure_rows),
        "billing_periodicity_breakdown": _count_breakdown(billing_rows),
        "allotment_breakdown": _count_breakdown(allotment_rows),
        "tenant_terminology": tenant_terminology,
        "status_definition_source": "public.m_property_status joined to public.plot.status",
        "vacancy_definition_source": "public.plot.is_vacant",
        "land_occupancy_definition_source": "Exclusive public.plot view: RG status first, then is_vacant=true/false, then unclassified",
        "tenancy_definition_source": "COUNT(public.applicant_property_mapping) mapping records; not a canonical tenant count",
        "tenancy_lifecycle_definition_source": "Derived from public.applicant_property_mapping.tenancy_type; values containing expired or source typo exipred are Expired",
        "data_quality": {
            "mapping_records": _as_int(quality[0]),
            "matched_applicants": _as_int(quality[1]),
            "orphan_mappings": _as_int(quality[2]),
            "missing_contact_person": _as_int(quality[3]),
            "missing_purpose": _as_int(quality[4]),
            "missing_plot_links": _as_int(quality[5]),
            "missing_start_dates": _as_int(quality[6]),
            "missing_end_dates": _as_int(quality[7]),
            "historical_start_dates": _as_int(quality[8]),
            "invalid_start_dates": _as_int(quality[9]),
        },
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = _settings()
    migrate(settings)
    app.state.settings = settings
    app.state.rag_ready = False
    app.state.rag_init_error = None
    try:
        with httpx.Client(timeout=settings.embedding_timeout_seconds) as client:
            response = client.get(str(settings.embedding_endpoint).rsplit("/", 1)[0] + "/tags")
            response.raise_for_status()
            installed = {item.get("name", "") for item in response.json().get("models", [])}
        def installed_model(name: str) -> bool:
            return name in installed or f"{name}:latest" in installed
        required = {settings.embedding_model, settings.llm_primary_model}
        missing = sorted(model for model in required if not installed_model(model))
        if missing:
            raise RuntimeError(f"Missing configured Ollama models: {', '.join(missing)}")
        _rerank(settings, "readiness check", ["readiness check"])
        app.state.rag_ready = True
    except Exception as exc:
        app.state.rag_init_error = f"{type(exc).__name__}: {exc}"
    yield


app = FastAPI(title="PortProject RAG Portal", version="0.2.0", lifespan=lifespan)
# The browser UI is served from Vite on port 5173 during local development.
# Keep the method list aligned with the authenticated API contract: private
# conversations can be deleted through the browser, which requires a CORS
# preflight for DELETE when UI and API use different local origins.
_cors_settings = Settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


def _billing_service() -> BillingPredictionService:
    """Create the billing service only when the authenticated feature is used."""
    service = getattr(app.state, "billing_service", None)
    if service is not None:
        return service
    try:
        service = BillingPredictionService(app.state.settings.database_url.unicode_string())
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Billing forecast artifacts are not ready.") from exc
    app.state.billing_service = service
    return service


def _tender_service() -> TenderWorkflowService:
    """Return the target project's source-backed tender workflow service."""
    service = getattr(app.state, "tender_workflow_service", None)
    if service is None:
        service = TenderWorkflowService()
        app.state.tender_workflow_service = service
    return service


def _require_authority(user: PortalUser) -> None:
    if user.role != "authority":
        raise HTTPException(status_code=403, detail="Authority access is required.")


@app.get("/health")
def health() -> dict[str, object]:
    settings: Settings = app.state.settings
    return {"status": "ok", "database": settings.database_url.path.lstrip("/"), "schema": settings.schema_name}


@app.get("/health/ready")
def ready() -> JSONResponse:
    payload = {
        "status": "ready" if app.state.rag_ready else "not_ready",
        "rag_ready": app.state.rag_ready,
        "init_error": app.state.rag_init_error,
        "corpus": _stats(app.state.settings),
    }
    return JSONResponse(payload, status_code=200 if app.state.rag_ready else 503)


@app.get("/api/v1/auth/bootstrap-status")
def setup_status() -> dict[str, bool]:
    return {"setup_required": False}


@app.post("/api/v1/auth/bootstrap")
def setup(request: InitialSetup, response: Response) -> dict[str, object]:
    raise HTTPException(status_code=410, detail="Portal signup is disabled. Sign in with an existing Authority or Tenant database account.")


def _session_cookie_options(settings: Settings) -> dict[str, object]:
    return {
        "httponly": True,
        "samesite": settings.cookie_samesite,
        "secure": settings.cookie_secure,
        "max_age": settings.session_absolute_timeout_seconds,
        "path": "/",
    }


def _login(credentials: Credentials, response: Response, role: str, http_request: Request) -> dict[str, object]:
    settings: Settings = app.state.settings
    ip_address = http_request.client.host if http_request.client else "unknown"
    check_login_rate_limit(settings, credentials.username, ip_address)
    user = authenticate(settings, credentials.username, credentials.password, role)
    if not user:
        record_login_attempt(settings, credentials.username, ip_address, False)
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    record_login_attempt(settings, credentials.username, ip_address, True)
    token = create_session(settings, user)
    response.set_cookie(SESSION_COOKIE, token, **_session_cookie_options(settings))
    _log(settings, user, "login", {"role": role, "ip_address": ip_address})
    return {"status": "ok", **_user_payload(user)}


@app.post("/api/authority/login")
def authority_login(credentials: Credentials, response: Response, http_request: Request) -> dict[str, object]:
    return _login(credentials, response, "authority", http_request)


@app.post("/tenant/api/auth/login")
def tenant_login(credentials: Credentials, response: Response, http_request: Request) -> dict[str, object]:
    return _login(credentials, response, "tenant", http_request)


@app.post("/api/v1/auth/logout")
@app.post("/api/authority/logout")
@app.post("/tenant/api/auth/logout")
def logout(request: Request, response: Response, user: PortalUser = Depends(current_user)) -> dict[str, str]:
    settings: Settings = app.state.settings
    delete_session(settings, request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, **{key: value for key, value in _session_cookie_options(settings).items() if key != "max_age"})
    _log(settings, user, "logout", {})
    return {"status": "ok"}


@app.get("/api/v1/auth/me")
@app.get("/api/authority/me")
@app.get("/tenant/api/auth/me")
def me(user: PortalUser = Depends(current_user)) -> dict[str, object]:
    return _user_payload(user)


@app.get("/api/v1/corpus")
def corpus(user: PortalUser = Depends(current_user)) -> dict[str, object]:
    settings: Settings = app.state.settings
    return {**_stats(settings), "embedding_model": settings.embedding_model, "embedding_dimensions": settings.embedding_dimensions}


@app.get("/api/v1/corpus/state")
def corpus_state(user: PortalUser = Depends(current_user)) -> dict[str, object]:
    return _corpus_state(app.state.settings)


@app.get("/api/v1/local-llms")
def local_llms(user: PortalUser = Depends(current_user)) -> dict[str, object]:
    try:
        models = _local_completion_models(app.state.settings)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Local model catalog is unavailable.") from exc
    return {"models": models, "default_model": app.state.settings.llm_primary_model}


@app.get("/api/v1/billing/status")
def billing_status(user: PortalUser = Depends(current_user)) -> dict[str, object]:
    _require_authority(user)
    service = _billing_service()
    return {
        "ready": True,
        "model": str(service.model_path),
        "manifest": str(service.manifest_path),
        "model_loaded": service.model_loaded,
    }


@app.get("/api/v1/billing/rules")
def billing_rules(user: PortalUser = Depends(current_user)) -> dict[str, object]:
    _require_authority(user)
    return _billing_service().rules_payload()


@app.get("/api/v1/billing/tenancies")
def billing_tenancies(user: PortalUser = Depends(current_user)) -> dict[str, object]:
    _require_authority(user)
    try:
        return {"options": _billing_service().tenancy_options()}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Billing tenancy options are unavailable.") from exc


@app.get("/api/v1/billing/tenancies/{tenancy_id}/prefill")
def billing_tenancy_prefill(tenancy_id: str, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    _require_authority(user)
    try:
        return _billing_service().tenancy_prefill(tenancy_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Billing tenancy prefill is unavailable.") from exc


@app.post("/api/v1/billing/predict")
def billing_predict(request: BillingRequest, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    _require_authority(user)
    try:
        service = _billing_service()
        request_payload = request.model_dump(exclude_none=True)
        chat_session_id = request_payload.pop("chat_session_id", None)
        forecast_request = BillingPredictionRequest(**request_payload)
        result = service.predict_from_inputs(forecast_request) if forecast_request.present_amount is not None else service.predict(forecast_request)
        user_created_at: str | None = None
        assistant_created_at: str | None = None
        with connect(app.state.settings.database_url.unicode_string()) as connection:
            with connection.cursor() as cursor:
                if chat_session_id:
                    cursor.execute(
                        f"SELECT 1 FROM {app.state.settings.schema_name}.chat_session WHERE chat_session_id=%s AND principal_id=%s FOR UPDATE",
                        (chat_session_id, user.principal_id),
                    )
                    if not cursor.fetchone():
                        raise HTTPException(status_code=404, detail="Conversation not found.")
                else:
                    cursor.execute(
                        f"""INSERT INTO {app.state.settings.schema_name}.chat_session (user_id, principal_id, title)
                            VALUES (%s, %s, %s) RETURNING chat_session_id""",
                        (user.user_id, user.principal_id, "Billing Forecast"),
                    )
                    chat_session_id = cursor.fetchone()[0]
                cursor.execute(
                    f"INSERT INTO {app.state.settings.schema_name}.chat_message (chat_session_id, sender, content) VALUES (%s, 'user', %s) RETURNING created_at",
                    (chat_session_id, f"Billing forecast for {forecast_request.tenancy_id or forecast_request.customer_id or 'manual input'}"),
                )
                user_created_at = cursor.fetchone()[0].isoformat()
                cursor.execute(
                    f"INSERT INTO {app.state.settings.schema_name}.chat_message (chat_session_id, sender, content, sources) VALUES (%s, 'assistant', %s, %s) RETURNING created_at",
                    (chat_session_id, result.summary(), Jsonb([])),
                )
                assistant_created_at = cursor.fetchone()[0].isoformat()
                cursor.execute(f"UPDATE {app.state.settings.schema_name}.chat_session SET updated_at=now() WHERE chat_session_id=%s", (chat_session_id,))
        _log(app.state.settings, user, "billing_forecast", {
            "context_id": result.context_id,
            "target_year": forecast_request.target_year,
            "target_month": forecast_request.target_month,
            "tenancy_id": forecast_request.tenancy_id,
            "model_source": result.model_source,
            "fallback_applied": result.fallback_applied,
        })
        return {"success": True, "summary": result.summary(), "prediction": result.as_dict(), "chat_session_id": str(chat_session_id), "user_created_at": user_created_at, "assistant_created_at": assistant_created_at}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Billing prediction is temporarily unavailable.") from exc


@app.get("/api/v1/tender/config")
def tender_config(user: PortalUser = Depends(current_user)) -> dict[str, object]:
    _require_authority(user)
    try:
        return _tender_service().config_payload()
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/tender/plots")
def tender_plots(user: PortalUser = Depends(current_user)) -> dict[str, object]:
    _require_authority(user)
    try:
        return {"plots": _tender_service().list_plots()}
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/tender/plots/{plot_id}")
def tender_plot_detail(plot_id: str, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    _require_authority(user)
    try:
        return _tender_service().plot_detail(plot_id)
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/tender/checklists/{checklist_key}")
def tender_checklist(checklist_key: str, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    _require_authority(user)
    try:
        return _tender_service().checklist(checklist_key)
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/tender/calculate")
def tender_calculate(request: TenderCalculationRequest, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    _require_authority(user)
    try:
        return _tender_service().calculate(request.fields)
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/tender/workflows")
def tender_workflows(user: PortalUser = Depends(current_user)) -> dict[str, object]:
    _require_authority(user)
    try:
        return {"workflows": _tender_service().list_workflows()}
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/v1/tender/workflows")
def tender_create_workflow(request: TenderWorkflowCreateRequest, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    _require_authority(user)
    try:
        workflow = _tender_service().create_workflow(request.model_dump())
        _log(app.state.settings, user, "tender_workflow_created", {"workflow_id": workflow["id"], "plot_id": request.plot_id, "checklist_key": request.checklist_key})
        return {"workflow": workflow}
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/tender/workflows/{workflow_id}")
def tender_get_workflow(workflow_id: str, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    _require_authority(user)
    try:
        return {"workflow": _tender_service().get_workflow(workflow_id)}
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/tender/workflows/{workflow_id}/actions")
def tender_apply_action(workflow_id: str, request: TenderWorkflowActionRequest, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    _require_authority(user)
    try:
        workflow = _tender_service().apply_action(workflow_id, request.model_dump())
        _log(app.state.settings, user, "tender_workflow_action", {"workflow_id": workflow_id, "action": request.action, "status": workflow.get("status")})
        return {"workflow": workflow}
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/tender/workflows/{workflow_id}/documents/{document_kind}")
def tender_document(workflow_id: str, document_kind: str, user: PortalUser = Depends(current_user)) -> Response:
    _require_authority(user)
    try:
        content = _tender_service().document_pdf(workflow_id, document_kind)
        return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{document_kind}-{workflow_id}.pdf"'})
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/public/corpus")
def public_corpus() -> dict[str, int]:
    """Publish aggregate corpus counts only; document contents remain authenticated."""
    return _stats(app.state.settings)


@app.get("/api/v1/documents")
def documents(limit: int = 100, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    settings: Settings = app.state.settings
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"""SELECT d.original_filename, d.page_count, d.classification, d.extraction_quality, COUNT(c.chunk_id)
                FROM {settings.document_schema_name}.document_record d
                LEFT JOIN {settings.vector_schema_name}.document_chunk c ON c.document_id=d.document_id
                GROUP BY d.document_id, d.original_filename, d.page_count, d.classification, d.extraction_quality
                ORDER BY d.original_filename LIMIT %s""", (min(limit, 200),))
            rows = cursor.fetchall()
    return {"documents": [{"filename": r[0], "pages": r[1], "classification": r[2], "quality": r[3], "chunks": r[4]} for r in rows]}


@app.get("/api/authority/dashboard/metrics")
def authority_metrics(user: PortalUser = Depends(current_user)) -> dict[str, object]:
    if user.role != "authority":
        raise HTTPException(status_code=403, detail="Authority access is required.")
    return _authority_land_metrics(app.state.settings)


@app.get("/api/authority/tenants")
def authority_tenants(
    query: str = "",
    status: str = "",
    lease_type: str = "",
    allotment_status: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
    page_size: int = 25,
    sort_by: str = "tenant_id",
    sort_direction: str = "desc",
    user: PortalUser = Depends(current_user),
) -> dict[str, object]:
    if user.role != "authority":
        raise HTTPException(status_code=403, detail="Authority access is required.")
    for label, value in (("date_from", date_from), ("date_to", date_to)):
        if value:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=f"{label} must use YYYY-MM-DD format.") from exc
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must be before or equal to date_to.")

    page_size = min(max(page_size, 1), 100)
    sort_columns = {
        "tenant_id": "apm.tenant_id",
        "tenancy_id": "NULLIF(BTRIM(apm.tenancy_id), '')",
        "tenant_name": "COALESCE(NULLIF(BTRIM(ar.ind_org_name), ''), NULLIF(BTRIM(ar.username), ''), '')",
        "contact_person": "COALESCE(NULLIF(BTRIM(ar.authorised_person_name), ''), '')",
        "tenancy_type": "COALESCE(NULLIF(BTRIM(apm.tenancy_type), ''), '')",
        "purpose": "COALESCE(NULLIF(BTRIM(apm.purpose), ''), '')",
        "commencement": "apm.duration_from",
        "status": "COALESCE(NULLIF(BTRIM(apm.status), ''), '')",
    }
    order_column = sort_columns.get(sort_by, sort_columns["tenant_id"])
    order_direction = "ASC" if sort_direction.lower() == "asc" else "DESC"
    query_text = query.strip()
    pattern = f"%{query_text}%"
    where_clauses = ["""(%s='' OR CAST(apm.tenant_id AS text) ILIKE %s OR COALESCE(apm.tenancy_id, '') ILIKE %s
        OR COALESCE(NULLIF(BTRIM(ar.ind_org_name), ''), NULLIF(BTRIM(ar.username), ''), '') ILIKE %s
        OR COALESCE(NULLIF(BTRIM(ar.authorised_person_name), ''), '') ILIKE %s
        OR COALESCE(NULLIF(BTRIM(apm.tenancy_type), ''), '') ILIKE %s
        OR COALESCE(NULLIF(BTRIM(apm.purpose), ''), '') ILIKE %s)"""]
    query_params: list[object] = [query_text, pattern, pattern, pattern, pattern, pattern, pattern]
    if status.strip():
        where_clauses.append("COALESCE(NULLIF(BTRIM(apm.status), ''), 'Not provided') = %s")
        query_params.append(status.strip())
    if lease_type.strip():
        where_clauses.append("COALESCE(NULLIF(BTRIM(apm.tenancy_type), ''), 'Not provided') = %s")
        query_params.append(lease_type.strip())
    if allotment_status.strip():
        where_clauses.append("CASE WHEN apm.is_alloted IS TRUE THEN 'Allotted' WHEN apm.is_alloted IS FALSE THEN 'Not allotted' ELSE 'Not provided' END = %s")
        query_params.append(allotment_status.strip())
    if date_from:
        where_clauses.append("NULLIF(BTRIM(apm.duration_from), '') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' AND BTRIM(apm.duration_from) >= %s")
        query_params.append(date_from)
    if date_to:
        where_clauses.append("NULLIF(BTRIM(apm.duration_from), '') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' AND BTRIM(apm.duration_from) <= %s")
        query_params.append(date_to)
    where = "WHERE " + " AND ".join(where_clauses)
    with connect(app.state.settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM public.applicant_property_mapping apm LEFT JOIN public.applicant_registration ar ON ar.applicant_id=apm.tenant_id {where}", tuple(query_params))
            total = cursor.fetchone()[0] or 0
            pages = max(1, (total + page_size - 1) // page_size)
            page = min(max(page, 1), pages)
            data_params = [*query_params, page_size, (page - 1) * page_size]
            cursor.execute(f"""SELECT apm.tenant_id, COALESCE(NULLIF(BTRIM(apm.tenancy_id), ''), 'Not provided'),
                COALESCE(NULLIF(BTRIM(ar.ind_org_name), ''), NULLIF(BTRIM(ar.username), ''), 'Not linked'),
                COALESCE(NULLIF(BTRIM(ar.authorised_person_name), ''), 'Not provided'),
                COALESCE(NULLIF(BTRIM(apm.tenancy_type), ''), 'Not provided'),
                COALESCE(NULLIF(BTRIM(apm.purpose), ''), 'Not provided'),
                COALESCE(NULLIF(BTRIM(apm.duration_from::text), ''), 'Not provided'),
                COALESCE(NULLIF(BTRIM(apm.status), ''), 'Not provided')
                FROM public.applicant_property_mapping apm LEFT JOIN public.applicant_registration ar ON ar.applicant_id=apm.tenant_id {where}
                ORDER BY {order_column} {order_direction} NULLS LAST, apm.tenant_id DESC
                LIMIT %s OFFSET %s""", tuple(data_params))
            rows = cursor.fetchall()
            cursor.execute("""SELECT DISTINCT COALESCE(NULLIF(BTRIM(status), ''), 'Not provided')
                FROM public.applicant_property_mapping ORDER BY 1""")
            status_options = [row[0] for row in cursor.fetchall()]
            cursor.execute("""SELECT DISTINCT COALESCE(NULLIF(BTRIM(tenancy_type), ''), 'Not provided')
                FROM public.applicant_property_mapping ORDER BY 1""")
            lease_type_options = [row[0] for row in cursor.fetchall()]
            cursor.execute("""SELECT DISTINCT CASE
                    WHEN is_alloted IS TRUE THEN 'Allotted'
                    WHEN is_alloted IS FALSE THEN 'Not allotted'
                    ELSE 'Not provided'
                END
                FROM public.applicant_property_mapping ORDER BY 1""")
            allotment_options = [row[0] for row in cursor.fetchall()]
            tenant_terminology = _tenant_terminology(cursor)
    mapping_terms = cast(dict[str, object], tenant_terminology["mapping_records"])
    mapping_label = str(mapping_terms["label"])
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "record_label": mapping_label,
        "tenant_terminology": tenant_terminology,
        "filters": {
            "statuses": status_options,
            "lease_types": lease_type_options,
            "allotment_statuses": allotment_options,
        },
        "tenants": [
            {
                "tenant_id": str(r[0]),
                "tenancy_id": r[1],
                "tenant_name": r[2],
                "contact_person": r[3],
                "tenancy_type": r[4],
                "purpose": r[5],
                "commencement": _date_display(r[6]),
                "commencement_raw": r[6],
                "status": r[7],
            }
            for r in rows
        ],
    }


@app.post("/api/v1/chat/sessions")
def create_chat_session(user: PortalUser = Depends(current_user)) -> dict[str, str]:
    settings: Settings = app.state.settings
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {settings.schema_name}.chat_session (user_id, principal_id, title) VALUES (%s, %s, %s) RETURNING chat_session_id, title",
                (user.user_id, user.principal_id, "New conversation"),
            )
            row = cursor.fetchone()
    return {"chat_session_id": str(row[0]), "title": row[1]}


@app.get("/api/v1/chat/sessions")
def list_chat_sessions(user: PortalUser = Depends(current_user)) -> dict[str, object]:
    settings: Settings = app.state.settings
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT chat_session_id, title, updated_at FROM {settings.schema_name}.chat_session
                    WHERE principal_id=%s ORDER BY updated_at DESC, created_at DESC""",
                (user.principal_id,),
            )
            rows = cursor.fetchall()
    return {"sessions": [{"chat_session_id": str(row[0]), "title": row[1], "updated_at": row[2].isoformat()} for row in rows]}


@app.get("/api/v1/chat/sessions/{chat_session_id}")
def get_chat_session(chat_session_id: UUID, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    settings: Settings = app.state.settings
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT title FROM {settings.schema_name}.chat_session WHERE chat_session_id=%s AND principal_id=%s", (chat_session_id, user.principal_id))
            title = cursor.fetchone()
            if not title:
                raise HTTPException(status_code=404, detail="Conversation not found.")
            cursor.execute(f"""SELECT sender, content, sources, created_at FROM {settings.schema_name}.chat_message
                WHERE chat_session_id=%s ORDER BY created_at, message_id""", (chat_session_id,))
            rows = cursor.fetchall()
    return {"chat_session_id": str(chat_session_id), "title": title[0], "messages": [{"sender": row[0], "content": row[1], "sources": row[2], "created_at": row[3].isoformat()} for row in rows]}


@app.delete("/api/v1/chat/sessions/{chat_session_id}", status_code=204)
def delete_chat_session(chat_session_id: UUID, user: PortalUser = Depends(current_user)) -> Response:
    """Delete an unshared private conversation owned by the current principal.

    Workflow-linked conversations are protected so deleting the private source
    cannot silently remove provenance from an agenda or forwarded draft.
    The audit row is written in the same transaction as the delete.
    """
    settings: Settings = app.state.settings
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT cs.title,
                    EXISTS (SELECT 1 FROM {settings.schema_name}.workflow_draft wd
                        WHERE wd.chat_session_id=cs.chat_session_id),
                    EXISTS (SELECT 1 FROM {settings.schema_name}.agenda a
                        WHERE a.source_chat_session_id=cs.chat_session_id)
                    FROM {settings.schema_name}.chat_session cs
                    WHERE cs.chat_session_id=%s AND cs.principal_id=%s
                    FOR UPDATE""",
                (chat_session_id, user.principal_id),
            )
            session = cursor.fetchone()
            if not session:
                raise HTTPException(status_code=404, detail="Conversation not found.")
            if session[1] or session[2]:
                raise HTTPException(status_code=409, detail="This conversation is linked to workflow records and cannot be deleted.")
            cursor.execute(
                f"DELETE FROM {settings.schema_name}.chat_session WHERE chat_session_id=%s AND principal_id=%s",
                (chat_session_id, user.principal_id),
            )
            if cursor.rowcount != 1:
                raise HTTPException(status_code=404, detail="Conversation not found.")
            cursor.execute(
                f"""INSERT INTO {settings.schema_name}.audit_event
                    (user_id, principal_id, event_type, metadata)
                    VALUES (%s, %s, %s, %s)""",
                (user.user_id, user.principal_id, "chat_session_deleted", Jsonb({"chat_session_id": str(chat_session_id)})),
            )
    return Response(status_code=204)


@app.get("/api/v1/workflow/drafts")
def list_workflow_drafts(user: PortalUser = Depends(current_user)) -> dict[str, object]:
    settings: Settings = app.state.settings
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT draft_id, chat_session_id, title, draft_text, state, updated_at
                    FROM {settings.schema_name}.workflow_draft
                    WHERE principal_id=%s ORDER BY updated_at DESC, created_at DESC""",
                (user.principal_id,),
            )
            rows = cursor.fetchall()
    return {"drafts": [{"draft_id": str(row[0]), "chat_session_id": str(row[1]) if row[1] else None, "title": row[2], "draft_text": row[3], "state": row[4], "updated_at": row[5].isoformat()} for row in rows]}


@app.post("/api/v1/workflow/drafts")
def forward_chat_to_workflow(request: ForwardDraftRequest, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    """Persist an evidence-based private chat as a workflow draft for the same officer."""
    settings: Settings = app.state.settings
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT title FROM {settings.schema_name}.chat_session WHERE chat_session_id=%s AND principal_id=%s FOR UPDATE",
                (request.chat_session_id, user.principal_id),
            )
            session = cursor.fetchone()
            if not session:
                raise HTTPException(status_code=404, detail="Conversation not found.")
            cursor.execute(
                f"SELECT sender, content FROM {settings.schema_name}.chat_message WHERE chat_session_id=%s ORDER BY created_at, message_id",
                (request.chat_session_id,),
            )
            messages = cursor.fetchall()
            if not messages:
                raise HTTPException(status_code=400, detail="Ask a document question before forwarding this conversation.")
            body = "\n\n".join(f"{('Officer query' if sender == 'user' else 'RAG evidence response')}:\n{content}" for sender, content in messages)
            title = (request.title or session[0]).strip()[:180] or "Workflow draft"
            cursor.execute(
                f"""INSERT INTO {settings.schema_name}.workflow_draft
                    (chat_session_id, principal_id, title, draft_text, state)
                    VALUES (%s, %s, %s, %s, 'FORWARDED')
                    RETURNING draft_id, state, updated_at""",
                (request.chat_session_id, user.principal_id, title, body),
            )
            row = cursor.fetchone()
    _log(settings, user, "workflow_draft_forwarded", {"draft_id": str(row[0]), "chat_session_id": str(request.chat_session_id)})
    return {"draft_id": str(row[0]), "state": row[1], "updated_at": row[2].isoformat(), "title": title}


@app.get("/api/v1/workflow/officers")
def workflow_officers(user: PortalUser = Depends(current_user)) -> dict[str, object]:
    authority_identity(app.state.settings, user)
    return {"officers": officer_directory(app.state.settings)}


@app.get("/api/v1/workflow/agendas")
def workflow_agendas(user: PortalUser = Depends(current_user)) -> dict[str, object]:
    return {"agendas": list_agendas(app.state.settings, user)}


@app.post("/api/v1/workflow/agendas")
def create_workflow_agenda(request: ForwardDraftRequest, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    agenda = create_agenda_from_chat(app.state.settings, user, request.chat_session_id, request.title)
    _log(app.state.settings, user, "agenda_created", {"agenda_id": agenda["agenda_id"], "source_chat_session_id": str(request.chat_session_id)})
    return {"agenda": agenda}


@app.get("/api/v1/workflow/agendas/{agenda_id}")
def get_workflow_agenda(agenda_id: UUID, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    return {"agenda": agenda_detail(app.state.settings, user, agenda_id)}


@app.post("/api/v1/workflow/agendas/{agenda_id}/revisions")
def save_workflow_agenda_revision(agenda_id: UUID, request: AgendaRevisionRequest, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    agenda = save_agenda_revision(app.state.settings, user, agenda_id, request.draft_text)
    _log(app.state.settings, user, "agenda_revision_saved", {"agenda_id": str(agenda_id), "editing_version": agenda["editing_version"]})
    return {"agenda": agenda}


@app.post("/api/v1/workflow/agendas/{agenda_id}/transition")
def transition_workflow_agenda(agenda_id: UUID, request: AgendaTransitionRequest, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    result = transition_agenda(app.state.settings, user, agenda_id, request.action, request.target_principal, request.note)
    _log(app.state.settings, user, "agenda_transition", {
        "agenda_id": str(agenda_id), "action": result.action, "previous_owner": result.previous_owner,
        "current_owner": result.agenda["current_owner_principal"], "state": result.agenda["state"],
    })
    return {"agenda": result.agenda}


@app.post("/api/v1/workflow/agendas/{agenda_id}/query")
def query_in_workflow_agenda(agenda_id: UUID, request: AgendaQuestionRequest, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    settings: Settings = app.state.settings
    guardrail = validate_query(settings, request.question)
    if not guardrail.allowed:
        _log(settings, user, "agenda_rag_query_blocked", {"agenda_id": str(agenda_id), "reason": guardrail.reason})
        raise HTTPException(status_code=400, detail=guardrail.reason)
    # This ownership check runs before retrieval so a read-only participant cannot
    # consume or alter the official thread through a crafted request.
    current = agenda_detail(settings, user, agenda_id)
    if current["is_read_only"]:
        raise HTTPException(status_code=409, detail="This agenda is a read-only snapshot for your role.")
    try:
        payload = _answer_payload(settings, guardrail.cleaned_text, request.limit, user.role, request.llm_model)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Retrieval unavailable: {type(exc).__name__}") from exc
    add_agenda_message(settings, user, agenda_id, request.question, "OFFICER")
    add_agenda_message(settings, user, agenda_id, str(payload["answer"]), "AI", payload["sources"])
    _log(settings, user, "agenda_corpus_query", {
        "agenda_id": str(agenda_id), "duration_ms": payload["duration_ms"], "source_count": len(payload["sources"]),
        "candidate_count": payload["candidate_count"], "citation_valid": payload["citation_valid"], "llm_model": payload["llm_model"], **payload["timings"],
    })
    return payload


@app.post("/api/v1/policy/query")
@app.post("/api/v1/query")
@app.post("/api/v1/chat")
def query(request: QueryRequest, user: PortalUser = Depends(current_user)) -> dict[str, object]:
    settings: Settings = app.state.settings
    guardrail = validate_query(settings, request.question)
    if not guardrail.allowed:
        _log(settings, user, "rag_query_blocked", {"reason": guardrail.reason, "question_length": len(request.question)})
        raise HTTPException(status_code=400, detail=guardrail.reason)
    try:
        payload = _answer_payload(settings, guardrail.cleaned_text, request.limit, user.role, request.llm_model)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Retrieval unavailable: {type(exc).__name__}") from exc
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            session_id = request.chat_session_id
            if session_id:
                cursor.execute(f"SELECT 1 FROM {settings.schema_name}.chat_session WHERE chat_session_id=%s AND principal_id=%s FOR UPDATE", (session_id, user.principal_id))
                if not cursor.fetchone():
                    raise HTTPException(status_code=404, detail="Conversation not found.")
            else:
                cursor.execute(f"""INSERT INTO {settings.schema_name}.chat_session (user_id, principal_id, title)
                    VALUES (%s, %s, %s) RETURNING chat_session_id""", (user.user_id, user.principal_id, request.question.strip()[:80]))
                session_id = cursor.fetchone()[0]
            cursor.execute(f"INSERT INTO {settings.schema_name}.chat_message (chat_session_id, sender, content) VALUES (%s, 'user', %s) RETURNING created_at", (session_id, request.question))
            user_created_at = cursor.fetchone()[0].isoformat()
            cursor.execute(f"""INSERT INTO {settings.schema_name}.chat_message (chat_session_id, sender, content, sources)
                VALUES (%s, 'assistant', %s, %s) RETURNING created_at""", (session_id, payload["answer"], Jsonb(payload["sources"])))
            assistant_created_at = cursor.fetchone()[0].isoformat()
            cursor.execute(f"UPDATE {settings.schema_name}.chat_session SET updated_at=now() WHERE chat_session_id=%s", (session_id,))
    _log(settings, user, "corpus_query", {
        "duration_ms": payload["duration_ms"], "source_count": len(payload["sources"]),
        "question_length": len(request.question), "candidate_count": payload["candidate_count"],
        "citation_valid": payload["citation_valid"], "citation_error": payload["citation_error"], "route": payload["route"], "llm_model": payload["llm_model"], **payload["timings"],
    })
    return {**payload, "chat_session_id": str(session_id), "user_created_at": user_created_at, "assistant_created_at": assistant_created_at}
