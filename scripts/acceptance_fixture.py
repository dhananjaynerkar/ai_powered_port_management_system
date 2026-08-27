"""Provision and reset a synthetic, database-identity-guarded acceptance fixture.

This module deliberately refuses to operate on the operational ``portproject``
database.  It creates no production copy: all principals, source rows, RAG
documents, chats, and agenda records are synthetic and acceptance-owned.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg import connect, sql

ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_DATABASE = "portproject_acceptance"
OPERATIONAL_DATABASE = "portproject"
ACCEPTANCE_ENVIRONMENT = "acceptance"
SENTINEL_TABLE = "public.acceptance_environment"
RUNTIME_ROOT = ROOT / "tests" / "runtime" / "acceptance"
CREDENTIALS_PATH = RUNTIME_ROOT / "credentials.json"
TENDER_RUNTIME_PATH = ROOT / "tests" / "runtime" / "tender" / "tender_workflows.json"
FIXTURE_NAMESPACE = uuid5(NAMESPACE_URL, "https://example.invalid/portproject/acceptance")


class AcceptanceSafetyError(RuntimeError):
    """Raised when the acceptance safety contract is not satisfied."""


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ[key.strip()] = value


def _load_acceptance_environment() -> None:
    _load_dotenv(ROOT / ".env.acceptance")
    if os.environ.get("PORTPROJECT_RAG_ACCEPTANCE") != "1":
        raise AcceptanceSafetyError("PORTPROJECT_RAG_ACCEPTANCE=1 is required.")
    if os.environ.get("PORTPROJECT_RAG_ACCEPTANCE_DATABASE") != ACCEPTANCE_DATABASE:
        raise AcceptanceSafetyError("PORTPROJECT_RAG_ACCEPTANCE_DATABASE must be portproject_acceptance.")


def _database_name(dsn: str) -> str:
    path = urlsplit(dsn).path.rstrip("/")
    return path.rsplit("/", 1)[-1]


def _acceptance_dsn() -> str:
    dsn = os.environ.get("PORTPROJECT_RAG_DATABASE_URL", "").strip()
    if not dsn:
        raise AcceptanceSafetyError("PORTPROJECT_RAG_DATABASE_URL is required.")
    if _database_name(dsn) != ACCEPTANCE_DATABASE:
        raise AcceptanceSafetyError("Configured database is not portproject_acceptance; aborting.")
    return dsn


def _connect_acceptance(*, row_factory=None):
    dsn = _acceptance_dsn()
    connection = connect(dsn, row_factory=row_factory) if row_factory else connect(dsn)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            database_row = cursor.fetchone()
            current_database = database_row["current_database"] if isinstance(database_row, dict) else database_row[0]
            if current_database == OPERATIONAL_DATABASE or current_database != ACCEPTANCE_DATABASE:
                raise AcceptanceSafetyError(f"Safety refusal: current_database={current_database!r}.")
            cursor.execute(
                "SELECT environment, database_name, fixture_version FROM public.acceptance_environment WHERE fixture_id=1"
            )
            sentinel = cursor.fetchone()
            if isinstance(sentinel, dict):
                sentinel = (sentinel["environment"], sentinel["database_name"], sentinel["fixture_version"])
            if not sentinel or tuple(sentinel) != (ACCEPTANCE_ENVIRONMENT, ACCEPTANCE_DATABASE, 1):
                raise AcceptanceSafetyError("Acceptance sentinel is missing or invalid; aborting.")
    except Exception:
        connection.close()
        raise
    return connection


def _safe_tender_path() -> Path:
    configured = os.environ.get("PORTPROJECT_RAG_TENDER_STORAGE_PATH", "").strip()
    path = (ROOT / configured).resolve() if configured and not Path(configured).is_absolute() else Path(configured or TENDER_RUNTIME_PATH).resolve()
    operational = (ROOT / "src" / "portproject_rag" / "tender_workflow" / "data" / "tender_workflows.json").resolve()
    if path == operational or operational in path.parents:
        raise AcceptanceSafetyError("Tender acceptance path resolves to operational tender storage; aborting.")
    if ROOT / "tests" / "runtime" not in path.parents:
        raise AcceptanceSafetyError("Tender acceptance storage must remain below tests/runtime.")
    return path


def _fixture_uuid(name: str) -> UUID:
    return uuid5(FIXTURE_NAMESPACE, name)


def _credentials() -> dict[str, str]:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    if CREDENTIALS_PATH.is_file():
        payload = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
        if all(key in payload for key in ("DO_TEST", "NO_TEST", "HO_TEST", "TENANT_TEST")):
            return {key: str(payload[key]) for key in ("DO_TEST", "NO_TEST", "HO_TEST", "TENANT_TEST")}
    payload = {key: f"Acceptance-{secrets.token_urlsafe(24)}" for key in ("DO_TEST", "NO_TEST", "HO_TEST", "TENANT_TEST")}
    CREDENTIALS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _create_database(admin_dsn: str) -> None:
    if _database_name(admin_dsn) in {OPERATIONAL_DATABASE, ACCEPTANCE_DATABASE}:
        raise AcceptanceSafetyError("Admin connection must target a maintenance database, not portproject.")
    with connect(admin_dsn, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            current_database = cursor.fetchone()[0]
            if current_database == OPERATIONAL_DATABASE:
                raise AcceptanceSafetyError("Admin session resolved to operational portproject; aborting.")
            cursor.execute("SELECT 1 FROM pg_database WHERE datname=%s", (ACCEPTANCE_DATABASE,))
            if cursor.fetchone() is None:
                cursor.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(ACCEPTANCE_DATABASE)))


def _create_source_tables(connection) -> None:
    # The sentinel is created by this bootstrap transaction, so verify the
    # actual session identity before the first acceptance mutation.
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database()")
        current_database = cursor.fetchone()[0]
        if current_database == OPERATIONAL_DATABASE or current_database != ACCEPTANCE_DATABASE:
            raise AcceptanceSafetyError(f"Safety refusal during bootstrap: current_database={current_database!r}.")
    statements = [
        """CREATE TABLE IF NOT EXISTS public.acceptance_environment (
            fixture_id integer PRIMARY KEY CHECK (fixture_id=1),
            environment text NOT NULL,
            database_name text NOT NULL,
            fixture_version integer NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )""",
        """CREATE TABLE IF NOT EXISTS public.admin_users (
            admin_id integer PRIMARY KEY, name text NOT NULL, user_name text NOT NULL UNIQUE,
            demo_password text, passwd text, account_status_code char(1) NOT NULL,
            reg_timestamp timestamp NOT NULL, update_by text NOT NULL, update_timestamp timestamp NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS public.admin_roles (
            admin_role_id integer PRIMARY KEY, role_id text NOT NULL, update_by text NOT NULL,
            update_timestamp timestamp NOT NULL, admin_id integer NOT NULL, is_active boolean DEFAULT true,
            is_fullright boolean DEFAULT false
        )""",
        """CREATE TABLE IF NOT EXISTS public.applicant_registration (
            applicant_id integer PRIMARY KEY, ind_org_name text, authorised_person_name text,
            username text NOT NULL UNIQUE, password text NOT NULL, status text
        )""",
        """CREATE TABLE IF NOT EXISTS public.applicant_property_mapping (
            tenant_id integer NOT NULL, tenancy_type text, tenant_type text, status text, purpose text,
            bill_periodicity text, tenancy_id text, lease_type_id integer, has_additional_rent boolean,
            property_id integer, customer_code text, "Structure_type_id" text, update_timestamp timestamp,
            update_by text, duration_from text, duration_to text, is_alloted boolean,
            PRIMARY KEY (tenant_id, property_id)
        )""",
        """CREATE TABLE IF NOT EXISTS public.m_property_status (
            status_id text PRIMARY KEY, status text NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS public.plot (
            plot_id integer PRIMARY KEY, estate_id integer, plot_code text, rr_no text, street_no text,
            main_structure_name text, location text, area numeric NOT NULL DEFAULT 0, status text NOT NULL,
            is_active boolean NOT NULL DEFAULT true, is_vacant boolean, owner boolean NOT NULL DEFAULT true,
            owner_name text, dept_name text, customer_code text, is_verified boolean NOT NULL DEFAULT true
        )""",
        """CREATE TABLE IF NOT EXISTS public.mcustomer (
            customerid integer PRIMARY KEY, customercode text, commencedate timestamp NOT NULL,
            billingeffectedon timestamp NOT NULL, rrplotno text, estateid integer NOT NULL,
            billperiodicity integer NOT NULL, billingmonth integer NOT NULL, typeofconstructionid integer,
            isadditionalrent integer NOT NULL DEFAULT 0, modifieddate timestamp NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS public.tgeneralbill (
            generalbillid integer PRIMARY KEY, billyearmonth char(6), customerid text, billchargeid integer,
            amount numeric, cgst numeric, sgst numeric
        )""",
        """CREATE TABLE IF NOT EXISTS public.m_structure_type (
            structure_type_id integer PRIMARY KEY, structure_type text NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS public.m_tax_rates (
            tax_rate_id integer PRIMARY KEY, tax_period_from date, tax_period_to date,
            gen_tax numeric, wtr_tax numeric, sewr_tax numeric, wbt numeric, sbt numeric, egc numeric,
            edc numeric, prop numeric
        )""",
        """CREATE TABLE IF NOT EXISTS public.m_tax_for_treecess_street_edu (
            tax_edu_id integer PRIMARY KEY, tax_name text, tax_percentage numeric,
            period_from date, period_to date
        )""",
    ]
    with connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)
        # Keep an already-created acceptance database forward-compatible when
        # this fixture contract gains a source column.
        cursor.execute("ALTER TABLE public.applicant_property_mapping ADD COLUMN IF NOT EXISTS is_alloted boolean")
        cursor.execute(
            """INSERT INTO public.acceptance_environment (fixture_id, environment, database_name, fixture_version)
               VALUES (1, %s, %s, 1) ON CONFLICT (fixture_id) DO UPDATE SET environment=EXCLUDED.environment,
               database_name=EXCLUDED.database_name, fixture_version=EXCLUDED.fixture_version""",
            (ACCEPTANCE_ENVIRONMENT, ACCEPTANCE_DATABASE),
        )


def _clear_fixture(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """TRUNCATE TABLE
                rag.context_capsule, rag.agenda_message, rag.agenda_version, rag.agenda,
                rag.chat_message, rag.workflow_draft, rag.chat_session, rag.user_session,
                rag.login_attempt, rag.audit_event, rag.chunk, rag.document_page, rag.document,
                rag.app_user RESTART IDENTITY CASCADE"""
        )
        cursor.execute(
            """TRUNCATE TABLE public.admin_roles, public.admin_users, public.applicant_registration,
                public.applicant_property_mapping, public.plot, public.m_property_status,
                public.mcustomer, public.tgeneralbill, public.m_structure_type,
                public.m_tax_rates, public.m_tax_for_treecess_street_edu RESTART IDENTITY CASCADE"""
        )


def _seed_source_rows(connection, credentials: dict[str, str]) -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc).replace(tzinfo=None)
    with connection.cursor() as cursor:
        officers = [(10001, "DO Test", "do_test", credentials["DO_TEST"], "DO"), (10002, "NO Test", "no_test", credentials["NO_TEST"], "NO"), (10003, "HO Test", "ho_test", credentials["HO_TEST"], "HO")]
        for admin_id, name, username, password, role in officers:
            cursor.execute(
                """INSERT INTO public.admin_users (admin_id,name,user_name,demo_password,passwd,account_status_code,reg_timestamp,update_by,update_timestamp)
                   VALUES (%s,%s,%s,%s,NULL,'A',%s,'acceptance',%s)""",
                (admin_id, name, username, password, now, now),
            )
            cursor.execute(
                """INSERT INTO public.admin_roles (admin_role_id,role_id,update_by,update_timestamp,admin_id,is_active,is_fullright)
                   VALUES (%s,%s,'acceptance',%s,%s,true,true)""",
                (admin_id, role, now, admin_id),
            )
        cursor.execute(
            """INSERT INTO public.applicant_registration (applicant_id,ind_org_name,authorised_person_name,username,password,status)
               VALUES (20001,'Acceptance Tenant One','Tenant Test','tenant_test',%s,'APPROVED')""",
            (credentials["TENANT_TEST"],),
        )
        cursor.execute("INSERT INTO public.m_property_status (status_id,status) VALUES ('A','Approved'),('V','Vacant'),('RG','Registered')")
        plots = [
            (1, "ACC-001", "RR-ACC-001", "Policy Wharf", 1000, "A", False, "ACCEPTANCE-TENANCY-001"),
            (2, "ACC-002", "RR-ACC-002", "Vacant Yard", 2000, "V", True, None),
            (3, "ACC-003", "RR-ACC-003", "Registered Shed", 1500, "RG", False, None),
        ]
        for plot_id, code, rr_no, structure, area, status, is_vacant, customer_code in plots:
            cursor.execute(
                """INSERT INTO public.plot (plot_id,estate_id,plot_code,rr_no,main_structure_name,location,area,status,is_active,is_vacant,owner,owner_name,dept_name,customer_code,is_verified)
                   VALUES (%s,1,%s,%s,%s,'Acceptance Port',%s,%s,%s,%s,true,'Acceptance Authority','Acceptance Estates',%s,true)""",
                (plot_id, code, rr_no, structure, area, status, True, is_vacant, customer_code),
            )
        mappings = [
            (20001, "Long Lease", "Sole-Tenancy", "APPROVED", "Policy use", "Monthly", "ACCEPTANCE-TENANCY-001", 1, False, 1, "ACCEPTANCE-TENANCY-001", "1", now, "2025-01-01", "2027-12-31", True),
            (20002, "Yearly", "Joint-Tenancy", "APPROVED", "Review use", "Yearly", "ACCEPTANCE-TENANCY-002", 1, False, 3, "ACCEPTANCE-TENANCY-002", "1", now, "2025-01-01", "2026-12-31", False),
        ]
        cursor.execute(
            """INSERT INTO public.applicant_registration (applicant_id,ind_org_name,authorised_person_name,username,password,status)
               VALUES (20002,'Acceptance Tenant Two','Tenant Second','tenant_second',%s,'APPROVED')""",
            (credentials["TENANT_TEST"],),
        )
        for row in mappings:
            cursor.execute(
                """INSERT INTO public.applicant_property_mapping
                   (tenant_id,tenancy_type,tenant_type,status,purpose,bill_periodicity,tenancy_id,lease_type_id,has_additional_rent,property_id,customer_code,"Structure_type_id",update_timestamp,update_by,duration_from,duration_to,is_alloted)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'acceptance',%s,%s,%s)""",
                row,
            )
        cursor.execute("INSERT INTO public.m_structure_type (structure_type_id,structure_type) VALUES (1,'Other')")
        cursor.execute(
            """INSERT INTO public.mcustomer
               (customerid,customercode,commencedate,billingeffectedon,rrplotno,estateid,billperiodicity,billingmonth,typeofconstructionid,isadditionalrent,modifieddate)
               VALUES (30001,'ACCEPTANCE-TENANCY-001','2025-01-01','2025-01-01','RR-ACC-001',1,1,1,1,0,'2026-01-01')"""
        )
        cursor.executemany(
            """INSERT INTO public.tgeneralbill (generalbillid,billyearmonth,customerid,billchargeid,amount,cgst,sgst)
               VALUES (%s,%s,'30001',2,%s,900,900)""",
            [(1, "202501", 10000), (2, "202502", 10100), (3, "202503", 10200)],
        )
        cursor.execute(
            """INSERT INTO public.m_tax_rates
               (tax_rate_id,tax_period_from,tax_period_to,gen_tax,wtr_tax,sewr_tax,wbt,sbt,egc,edc,prop)
               VALUES (1,'2025-01-01',NULL,30,10,10,5,5,3,0,30)"""
        )
        cursor.executemany(
            """INSERT INTO public.m_tax_for_treecess_street_edu (tax_edu_id,tax_name,tax_percentage,period_from,period_to)
               VALUES (%s,%s,%s,'2025-01-01',NULL)""",
            [(1, "Street Tax", 2), (2, "Mah. State Edn. Cess", 1), (3, "Tree Cess", 0.5)],
        )


def _embedding(index: int) -> Vector:
    values = [0.0] * 1024
    values[index % 1024] = 1.0
    return Vector(values)


def _seed_rag_rows(connection) -> dict[str, dict[str, object]]:
    fixtures = [
        ("public", "Acceptance Public Port Policy", "Acceptance public evidence: port land leases require an approved use and timely payment.", []),
        ("authority", "Acceptance Authority Procedure", "Acceptance authority evidence: only authority officers may approve an official agenda handoff.", ["authority"]),
        ("tenant", "Acceptance Tenant Guidance", "Acceptance tenant evidence: tenants may review their own registration details through the tenant portal.", ["tenant"]),
        ("restricted", "Acceptance Restricted Note", "Acceptance role-restricted evidence: this note is available only to authority retrieval.", ["authority"]),
    ]
    result: dict[str, dict[str, object]] = {}
    register_vector(connection)
    with connection.cursor() as cursor:
        for key, title, text, acl_roles in fixtures:
            document_id = _fixture_uuid(f"document:{key}")
            page_id = _fixture_uuid(f"page:{key}")
            chunk_id = _fixture_uuid(f"chunk:{key}")
            filename = f"acceptance_{key}_policy.pdf"
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            cursor.execute(
                """INSERT INTO rag.document
                   (document_id,source_path,original_filename,file_sha256,file_size_bytes,page_count,classification,extraction_strategy,extraction_quality,source_metadata,ingestion_state)
                   VALUES (%s,%s,%s,%s,%s,1,'acceptance_fixture','fixture',100,%s,'indexed')""",
                (document_id, f"acceptance://{filename}", filename, digest, len(text.encode("utf-8")), json.dumps({"title": title, "fixture": key})),
            )
            cursor.execute(
                """INSERT INTO rag.document_page (page_id,document_id,page_number,extracted_text,extraction_method,extraction_quality,page_metadata)
                   VALUES (%s,%s,1,%s,'fixture',100,%s)""",
                (page_id, document_id, text, json.dumps({"fixture": key})),
            )
            cursor.execute(
                """INSERT INTO rag.chunk
                   (chunk_id,document_id,page_id,chunk_index,chunk_type,chunk_text,section_title,clause_number,token_estimate,acl_roles,metadata,embedding,embedding_model)
                   VALUES (%s,%s,%s,0,'fixture',%s,%s,%s,%s,%s,%s,%s,'acceptance-fixture')""",
                (chunk_id, document_id, page_id, text, title, f"A-{key}", max(1, len(text) // 4), acl_roles, json.dumps({"fixture": key}), _embedding(len(result))),
            )
            result[key] = {"document_id": str(document_id), "chunk_id": str(chunk_id), "filename": filename, "page": 1, "title": title}
    return result


def _insert_chat(
    connection,
    principal: str,
    title: str,
    *,
    cited: bool,
    source: dict[str, object] | None = None,
    empty: bool = False,
) -> UUID:
    session_id = _fixture_uuid(f"chat:{principal}:{title}")
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO rag.chat_session (chat_session_id,user_id,principal_id,title) VALUES (%s,NULL,%s,%s)",
            (session_id, principal, title),
        )
        if empty:
            return session_id
        cursor.execute(
            "INSERT INTO rag.chat_message (chat_session_id,sender,content,sources) VALUES (%s,'user',%s,'[]'::jsonb)",
            (session_id, "What does the acceptance policy say?"),
        )
        sources = [source] if cited and source else []
        answer = "The acceptance fixture contains a grounded policy answer [S1]." if cited else "Acceptance chat fixture without an answer."
        cursor.execute(
            "INSERT INTO rag.chat_message (chat_session_id,sender,content,sources) VALUES (%s,'assistant',%s,%s)",
            (session_id, answer, json.dumps(sources)),
        )
    return session_id


def _seed_workflows(connection, sources: dict[str, dict[str, object]]) -> None:
    from portproject_rag.auth import PortalUser
    from portproject_rag.settings import Settings
    from portproject_rag.workflow import create_agenda_from_chat, transition_agenda

    settings = Settings(database_url=_acceptance_dsn(), deployment_environment="local", allowed_origins="http://localhost:5180,http://127.0.0.1:5180")
    do_user = PortalUser(None, "authority:10001", "do_test", "DO Test", "authority")
    no_user = PortalUser(None, "authority:10002", "no_test", "NO Test", "authority")
    ho_user = PortalUser(None, "authority:10003", "ho_test", "HO Test", "authority")
    source = {"source_id": "S1", "document_id": sources["public"]["document_id"], "chunk_id": sources["public"]["chunk_id"], "title": sources["public"]["title"], "filename": sources["public"]["filename"], "page": 1, "section_title": "Acceptance public evidence", "clause_number": "A-public", "excerpt": "Acceptance public evidence.", "score": 1.0, "fused_score": 1.0, "lexical_rank": 1, "dense_rank": 1}

    # Keep explicit private-chat states separate from workflow-linked chats so
    # the acceptance checks exercise empty, normal, and cited conversations.
    _insert_chat(connection, "authority:10001", "private_empty", cited=False, empty=True)
    _insert_chat(connection, "authority:10001", "private_normal", cited=False)
    _insert_chat(connection, "authority:10001", "private_cited", cited=True, source=source)
    connection.commit()

    def create(title: str) -> UUID:
        chat_id = _insert_chat(connection, do_user.principal_id, title, cited=True, source=source)
        connection.commit()
        agenda = create_agenda_from_chat(settings, do_user, chat_id, title)
        return UUID(str(agenda["agenda_id"]))

    linked = create("workflow_linked")
    create("agenda_do_draft")
    submitted_no = create("agenda_submitted_to_no")
    transition_agenda(settings, do_user, submitted_no, "submit_to_nodal", "authority:10002", "Acceptance handoff to NO.")
    returned_do = create("agenda_returned_to_do")
    transition_agenda(settings, do_user, returned_do, "submit_to_nodal", "authority:10002", "Acceptance handoff to NO.")
    transition_agenda(settings, no_user, returned_do, "return_to_do", None, "Acceptance return to DO.")
    submitted_ho = create("agenda_submitted_to_ho")
    transition_agenda(settings, do_user, submitted_ho, "submit_to_nodal", "authority:10002", "Acceptance handoff to NO.")
    transition_agenda(settings, no_user, submitted_ho, "submit_to_hod", "authority:10003", "Acceptance handoff to HO.")
    approved = create("agenda_approved")
    transition_agenda(settings, do_user, approved, "submit_to_nodal", "authority:10002", "Acceptance handoff to NO.")
    transition_agenda(settings, no_user, approved, "submit_to_hod", "authority:10003", "Acceptance handoff to HO.")
    transition_agenda(settings, ho_user, approved, "approve", None, "Acceptance approval.")
    rejected = create("agenda_rejected")
    transition_agenda(settings, do_user, rejected, "submit_to_nodal", "authority:10002", "Acceptance handoff to NO.")
    transition_agenda(settings, no_user, rejected, "submit_to_hod", "authority:10003", "Acceptance handoff to HO.")
    transition_agenda(settings, ho_user, rejected, "reject", None, "Acceptance rejection.")
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM rag.agenda WHERE source_chat_session_id IS NOT NULL")
        if cursor.fetchone()[0] < 7:
            raise AcceptanceSafetyError("Workflow fixture creation did not create the expected linked agendas.")
        cursor.execute("SELECT COUNT(*) FROM rag.chat_session WHERE title='workflow_linked'")
        if cursor.fetchone()[0] != 1:
            raise AcceptanceSafetyError("workflow_linked chat fixture is missing.")
    # Keep the returned value useful for a debugger without exposing IDs in logs.
    _ = linked


def _write_billing_fixture() -> None:
    path_text = os.environ.get("BILLING_TAX_MAPPING_CSV", "tests/runtime/acceptance/billing_tax_mapping.csv")
    path = (ROOT / path_text).resolve() if not Path(path_text).is_absolute() else Path(path_text).resolve()
    if ROOT / "tests" / "runtime" not in path.parents:
        raise AcceptanceSafetyError("Billing acceptance mapping must remain below tests/runtime.")
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        ["tenancy_id", "bill_periodicity", "has_additional_rent", "Structure_type_id", "is_active", "is_applicable", "applicable_in_report", "tax_in_percent", "tax_percent", "tax_name", "tax_name_short", "tax_code", "valid_from"],
        ["ACCEPTANCE-TENANCY-001", "monthly", "false", "1", "true", "true", "true", "true", "30", "Property Taxes", "Prop.Tax", "340", "2025-01-01"],
        ["ACCEPTANCE-TENANCY-001", "monthly", "false", "1", "true", "true", "true", "true", "2", "Street Tax", "Street Tax", "ST", "2025-01-01"],
        ["ACCEPTANCE-TENANCY-001", "monthly", "false", "1", "true", "true", "true", "true", "3", "Emp. Guarantee Cess", "EGCess", "341", "2025-01-01"],
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)


def _write_tender_fixture() -> None:
    path = _safe_tender_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Build one disposable LAC draft through the real tender service so later
    # acceptance tests have an eligible plot, checklist, and proposal record.
    path.write_text("[]\n", encoding="utf-8")
    from portproject_rag.tender_workflow import TenderWorkflowService

    service = TenderWorkflowService()
    plots = service.list_plots()
    checklists = service.config_payload().get("checklists", [])
    if not plots or not checklists:
        raise AcceptanceSafetyError("Tender source fixtures do not expose an eligible plot and checklist.")
    service.create_workflow(
        {
            "plot_id": plots[0]["id"],
            "checklist_key": checklists[0]["key"],
            "fields": {},
            "checklist_answers": {},
        }
    )


def reset() -> None:
    _load_acceptance_environment()
    _acceptance_dsn()
    with _connect_acceptance() as connection:
        _clear_fixture(connection)
        credentials = _credentials()
        _seed_source_rows(connection, credentials)
        sources = _seed_rag_rows(connection)
        connection.commit()
        _seed_workflows(connection, sources)
    _write_billing_fixture()
    _write_tender_fixture()
    print("ACCEPTANCE FIXTURE RESET")


def provision(admin_dsn: str) -> None:
    _load_acceptance_environment()
    _create_database(admin_dsn)
    with connect(_acceptance_dsn()) as connection:
        _create_source_tables(connection)
        connection.commit()
    from portproject_rag.database import migrate
    from portproject_rag.settings import Settings

    settings = Settings(database_url=_acceptance_dsn(), deployment_environment="local", allowed_origins="http://localhost:5180,http://127.0.0.1:5180")
    migrate(settings)
    reset()
    check()


def check() -> None:
    _load_acceptance_environment()
    with _connect_acceptance() as connection:
        with connection.cursor() as cursor:
            required_tables = [("rag", "document"), ("rag", "chat_session"), ("rag", "agenda"), ("pms_doc", "document_record"), ("pms_vector", "document_chunk")]
            for schema_name, table_name in required_tables:
                cursor.execute("SELECT to_regclass(%s)", (f"{schema_name}.{table_name}",))
                if cursor.fetchone()[0] is None:
                    raise AcceptanceSafetyError(f"Missing required object {schema_name}.{table_name}.")
            cursor.execute("SELECT extname FROM pg_extension WHERE extname IN ('vector','pgcrypto')")
            if {row[0] for row in cursor.fetchall()} != {"vector", "pgcrypto"}:
                raise AcceptanceSafetyError("Required PostgreSQL extensions are missing.")
            checks = {
                "DO": "SELECT 1 FROM public.admin_users WHERE user_name='do_test' AND account_status_code='A'",
                "NO": "SELECT 1 FROM public.admin_users WHERE user_name='no_test' AND account_status_code='A'",
                "HO": "SELECT 1 FROM public.admin_users WHERE user_name='ho_test' AND account_status_code='A'",
                "Tenant": "SELECT 1 FROM public.applicant_registration WHERE username='tenant_test' AND status IN ('A','APPROVED')",
                "Principal_A": "SELECT 1 FROM public.admin_users WHERE admin_id=10001",
                "Principal_B": "SELECT 1 FROM public.applicant_registration WHERE applicant_id=20001 AND username='tenant_test'",
                "RAG_fixture": "SELECT 1 FROM rag.document WHERE ingestion_state='indexed' AND original_filename='acceptance_public_policy.pdf'",
                "ACL_fixture": "SELECT 1 FROM rag.chunk WHERE acl_roles @> ARRAY['authority']::text[]",
                "private_empty": "SELECT 1 FROM rag.chat_session WHERE title='private_empty'",
                "private_normal": "SELECT 1 FROM rag.chat_session WHERE title='private_normal'",
                "private_cited": "SELECT 1 FROM rag.chat_session WHERE title='private_cited'",
                "workflow_linked": "SELECT 1 FROM rag.chat_session WHERE title='workflow_linked'",
                "workflow_states": "SELECT COUNT(DISTINCT state) FROM rag.agenda WHERE state IN ('DO_DRAFT','SUBMITTED_TO_NO','RETURNED_TO_DO','SUBMITTED_TO_HO','APPROVED','REJECTED')",
            }
            for label, query in checks.items():
                cursor.execute(query)
                value = cursor.fetchone()[0]
                if (label == "workflow_states" and value < 6) or (label != "workflow_states" and value is None):
                    raise AcceptanceSafetyError(f"Missing acceptance fixture: {label}.")
            cursor.execute("SELECT COUNT(*) FROM public.mcustomer WHERE customercode='ACCEPTANCE-TENANCY-001'")
            if cursor.fetchone()[0] != 1:
                raise AcceptanceSafetyError("BILLING_COMPLETE source record is missing.")
            cursor.execute("SELECT COUNT(*) FROM public.mcustomer WHERE customercode='BILLING_INCOMPLETE'")
            # The incomplete case is intentionally represented by an absent customer;
            # this exercises the existing missing-source validation without fake rules.
            if cursor.fetchone()[0] != 0:
                raise AcceptanceSafetyError("BILLING_INCOMPLETE must remain source-incomplete.")
    tender_path = _safe_tender_path()
    tender_records = json.loads(tender_path.read_text(encoding="utf-8")) if tender_path.is_file() else None
    if not isinstance(tender_records, list) or len(tender_records) != 1 or tender_records[0].get("status") != "LAC_DRAFT":
        raise AcceptanceSafetyError("Tender acceptance storage is missing its reset LAC draft.")
    billing_path_text = os.environ.get("BILLING_TAX_MAPPING_CSV", "tests/runtime/acceptance/billing_tax_mapping.csv")
    billing_path = (ROOT / billing_path_text).resolve() if not Path(billing_path_text).is_absolute() else Path(billing_path_text).resolve()
    if not billing_path.is_file():
        raise AcceptanceSafetyError("Billing acceptance mapping is missing.")
    print("ACCEPTANCE FIXTURE READY")
    print(f"database={ACCEPTANCE_DATABASE}")
    print("sentinel=acceptance/1")
    print("principals=DO_TEST,NO_TEST,HO_TEST,TENANT_TEST,PRINCIPAL_A,PRINCIPAL_B")
    print("rag_acl=public,authority,tenant,role-restricted")
    print("workflow_states=DO_DRAFT,SUBMITTED_TO_NO,RETURNED_TO_DO,SUBMITTED_TO_HO,APPROVED,REJECTED")
    print(f"tender_storage={tender_path.relative_to(ROOT)}")
    print(f"billing_fixture={billing_path.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("provision", help="Create the acceptance database and seed fixtures")
    subparsers.add_parser("reset", help="Reset only acceptance-owned mutable state")
    subparsers.add_parser("check", help="Verify the acceptance sentinel and fixture inventory")
    args = parser.parse_args()
    try:
        if args.command == "provision":
            admin_dsn = os.environ.get("PORTPROJECT_RAG_ACCEPTANCE_ADMIN_DATABASE_URL", "").strip()
            if not admin_dsn:
                raise AcceptanceSafetyError(
                    "PORTPROJECT_RAG_ACCEPTANCE_ADMIN_DATABASE_URL is required in the private process environment."
                )
            provision(admin_dsn)
        elif args.command == "reset":
            reset()
        else:
            check()
    except AcceptanceSafetyError as error:
        print(f"ACCEPTANCE ABORT: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
