"""Phase 08 authentication, authorization, isolation, and RAG ACL E2E tests."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import httpx
from conftest import db_snapshot, login, session_row
from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg import connect

from portproject_rag.query_analysis import analyse_query
from portproject_rag.retrieval import (
    _adjacent_page_candidates,
    _candidate_rows,
    _expand_context,
    _expand_context_with_metadata,
)
from portproject_rag.settings import Settings

AUTHORITY_USERS = (
    ("do_test", "DO_TEST", "authority:10001", "DO"),
    ("no_test", "NO_TEST", "authority:10002", "NO"),
    ("ho_test", "HO_TEST", "authority:10003", "HO"),
)


def _chat_id_by_title(dsn: str, title: str) -> str:
    with connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT current_database()")
        assert cursor.fetchone()[0] == "portproject_acceptance"
        cursor.execute("SELECT chat_session_id FROM rag.chat_session WHERE title=%s", (title,))
        row = cursor.fetchone()
    assert row, f"fixture chat {title!r} is missing"
    return str(row[0])


def _agenda_id_by_state(dsn: str, state: str) -> str:
    with connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT agenda_id FROM rag.agenda WHERE state=%s ORDER BY agenda_number LIMIT 1", (state,))
        row = cursor.fetchone()
    assert row, f"fixture agenda state {state!r} is missing"
    return str(row[0])


def test_acceptance_startup_and_health(acceptance_guard: str, client: httpx.Client) -> None:
    health = client.get("/health")
    ready = client.get("/health/ready")
    assert health.status_code == 200
    assert health.json()["database"] == "portproject_acceptance"
    assert ready.status_code == 200
    payload = ready.json()
    assert payload["rag_ready"] is True
    assert payload["init_error"] is None
    assert payload["corpus"]["documents"] == 4


def test_real_authentication_negative_cases_and_session_storage(
    acceptance_guard: str, credentials: dict[str, str], client: httpx.Client
) -> None:
    for username, key, principal, workflow_role in AUTHORITY_USERS:
        response = login(client, username, credentials[key])
        assert response.json()["role"] == "authority"
        cookie = client.cookies.get("portproject_session")
        assert cookie
        cookie_header = response.headers.get("set-cookie", "").lower()
        assert "httponly" in cookie_header
        assert "samesite=lax" in cookie_header
        assert session_row(acceptance_guard, cookie) == (principal, username, "authority", True)
        assert client.get("/api/v1/auth/me").json()["username"] == username
        assert client.post("/api/v1/auth/logout").status_code == 200
        assert client.get("/api/v1/auth/me").status_code == 401

    tenant_response = login(client, "tenant_test", credentials["TENANT_TEST"], "tenant")
    assert tenant_response.json()["role"] == "tenant"
    assert client.post("/api/v1/auth/logout").status_code == 200

    for path, payload in (
        ("/api/authority/login", {"username": "do_test", "password": "wrong"}),
        ("/api/authority/login", {"username": "unknown_acceptance", "password": "wrong"}),
        ("/api/authority/login", {"username": "do_test", "password": ""}),
        ("/api/authority/login", {}),
    ):
        response = client.post(path, json=payload)
        assert response.status_code in {401, 422}
        assert "portproject_session" not in response.cookies


def test_session_isolation_and_logout_scope(acceptance_guard: str, credentials: dict[str, str]) -> None:
    with httpx.Client(base_url="http://127.0.0.1:8016", timeout=60) as authority, httpx.Client(
        base_url="http://127.0.0.1:8016", timeout=60
    ) as tenant:
        login(authority, "do_test", credentials["DO_TEST"])
        login(tenant, "tenant_test", credentials["TENANT_TEST"], "tenant")
        assert authority.get("/api/v1/auth/me").json()["username"] == "do_test"
        assert tenant.get("/api/v1/auth/me").json()["username"] == "tenant_test"

        authority_cookie = authority.cookies.get("portproject_session")
        tenant_cookie = tenant.cookies.get("portproject_session")
        assert authority_cookie and tenant_cookie and authority_cookie != tenant_cookie
        assert session_row(acceptance_guard, authority_cookie)[0] == "authority:10001"
        assert session_row(acceptance_guard, tenant_cookie)[0] == "tenant:20001"

        authority.cookies.set("portproject_session", "invalid-acceptance-cookie")
        assert authority.get("/api/v1/auth/me").status_code == 401
        authority.cookies.set("portproject_session", tenant_cookie)
        assert authority.get("/api/v1/auth/me").json()["username"] == "tenant_test"
        authority.cookies.set("portproject_session", authority_cookie)
        assert authority.post("/api/v1/auth/logout").status_code == 200
        assert authority.get("/api/v1/auth/me").status_code == 401
        assert tenant.get("/api/v1/auth/me").status_code == 200


def test_authorization_matrix(acceptance_guard: str, credentials: dict[str, str]) -> None:
    routes = {
        "corpus": ("GET", "/api/v1/corpus", {"authority": 200, "tenant": 200}),
        "documents": ("GET", "/api/v1/documents", {"authority": 200, "tenant": 200}),
        "local_llms": ("GET", "/api/v1/local-llms", {"authority": 200, "tenant": 200}),
        "dashboard": ("GET", "/api/authority/dashboard/metrics", {"authority": 200, "tenant": 403}),
        "tenants": ("GET", "/api/authority/tenants", {"authority": 200, "tenant": 403}),
        "officers": ("GET", "/api/v1/workflow/officers", {"authority": 200, "tenant": 403}),
        "agendas": ("GET", "/api/v1/workflow/agendas", {"authority": 200, "tenant": 403}),
        "drafts": ("GET", "/api/v1/workflow/drafts", {"authority": 200, "tenant": 200}),
        "billing": ("GET", "/api/v1/billing/status", {"authority": 200, "tenant": 403}),
        "tender": ("GET", "/api/v1/tender/config", {"authority": 200, "tenant": 403}),
        "chat": ("GET", "/api/v1/chat/sessions", {"authority": 200, "tenant": 200}),
    }
    for username, key, _, _ in AUTHORITY_USERS:
        with httpx.Client(base_url="http://127.0.0.1:8016", timeout=60) as http_client:
            login(http_client, username, credentials[key])
            for _, (_, path, expected) in routes.items():
                assert http_client.get(path).status_code == expected["authority"], (username, path)
    with httpx.Client(base_url="http://127.0.0.1:8016", timeout=60) as http_client:
        login(http_client, "tenant_test", credentials["TENANT_TEST"], "tenant")
        for _, (_, path, expected) in routes.items():
            assert http_client.get(path).status_code == expected["tenant"], path
    with httpx.Client(base_url="http://127.0.0.1:8016", timeout=60) as http_client:
        assert http_client.get("/api/v1/public/corpus").status_code == 200
        assert http_client.get("/api/v1/corpus").status_code == 401


def test_private_chat_ownership_idor_and_linked_delete(acceptance_guard: str, credentials: dict[str, str]) -> None:
    with httpx.Client(base_url="http://127.0.0.1:8016", timeout=60) as authority, httpx.Client(
        base_url="http://127.0.0.1:8016", timeout=60
    ) as tenant, httpx.Client(base_url="http://127.0.0.1:8016", timeout=60) as second_tenant:
        login(authority, "do_test", credentials["DO_TEST"])
        login(tenant, "tenant_test", credentials["TENANT_TEST"], "tenant")
        login(second_tenant, "tenant_second", credentials["TENANT_TEST"], "tenant")
        authority_chat = authority.post("/api/v1/chat/sessions").json()["chat_session_id"]
        tenant_chat = tenant.post("/api/v1/chat/sessions").json()["chat_session_id"]
        second_tenant_chat = second_tenant.post("/api/v1/chat/sessions").json()["chat_session_id"]
        authority_ids = {item["chat_session_id"] for item in authority.get("/api/v1/chat/sessions").json()["sessions"]}
        tenant_ids = {item["chat_session_id"] for item in tenant.get("/api/v1/chat/sessions").json()["sessions"]}
        second_tenant_ids = {item["chat_session_id"] for item in second_tenant.get("/api/v1/chat/sessions").json()["sessions"]}
        assert authority_chat in authority_ids and tenant_chat not in authority_ids
        assert tenant_chat in tenant_ids and authority_chat not in tenant_ids
        assert second_tenant_chat in second_tenant_ids and tenant_chat not in second_tenant_ids
        assert authority.get(f"/api/v1/chat/sessions/{tenant_chat}").status_code == 404
        assert tenant.get(f"/api/v1/chat/sessions/{authority_chat}").status_code == 404
        assert tenant.get(f"/api/v1/chat/sessions/{second_tenant_chat}").status_code == 404
        assert second_tenant.get(f"/api/v1/chat/sessions/{tenant_chat}").status_code == 404
        before = db_snapshot(acceptance_guard)
        assert authority.delete(f"/api/v1/chat/sessions/{tenant_chat}").status_code == 404
        assert tenant.delete(f"/api/v1/chat/sessions/{authority_chat}").status_code == 404
        assert tenant.delete(f"/api/v1/chat/sessions/{second_tenant_chat}").status_code == 404
        assert second_tenant.delete(f"/api/v1/chat/sessions/{tenant_chat}").status_code == 404
        after = db_snapshot(acceptance_guard)
        assert (after["chat_sessions"], after["chat_messages"]) == (before["chat_sessions"], before["chat_messages"])
        assert authority.delete(f"/api/v1/chat/sessions/{authority_chat}").status_code == 204
        assert tenant.delete(f"/api/v1/chat/sessions/{tenant_chat}").status_code == 204
        assert second_tenant.delete(f"/api/v1/chat/sessions/{second_tenant_chat}").status_code == 204
        linked = _chat_id_by_title(acceptance_guard, "workflow_linked")
        before_linked = db_snapshot(acceptance_guard)
        response = authority.delete(f"/api/v1/chat/sessions/{linked}")
        assert response.status_code == 409
        assert db_snapshot(acceptance_guard) == before_linked


def test_rag_acl_candidate_context_boundary(acceptance_guard: str) -> None:
    settings = Settings(database_url=acceptance_guard)
    authority_rows, *_ = _candidate_rows(settings, "Who may approve an official agenda handoff?", "authority")
    tenant_rows, *_ = _candidate_rows(settings, "What does the role-restricted note say?", "tenant")
    public_authority_rows, *_ = _candidate_rows(settings, "What do port land leases require?", "authority")
    public_tenant_rows, *_ = _candidate_rows(settings, "What do port land leases require?", "tenant")
    tenant_context = _expand_context(settings, tenant_rows[:8])
    authority_files = {row["filename"] for row in authority_rows}
    tenant_files = {row["filename"] for row in tenant_rows}
    assert "acceptance_authority_policy.pdf" in authority_files
    assert "acceptance_restricted_policy.pdf" not in tenant_files
    assert all("role-restricted evidence" not in row["context_text"] for row in tenant_context)
    assert "acceptance_public_policy.pdf" in {row["filename"] for row in public_authority_rows}
    assert "acceptance_public_policy.pdf" in {row["filename"] for row in public_tenant_rows}


def test_mixed_acl_neighbours_are_excluded_from_parent_and_adjacent_context(acceptance_guard: str) -> None:
    """An authorized anchor must not pull restricted parent or page neighbours."""
    settings = Settings(database_url=acceptance_guard)
    document_id, page_ids = uuid4(), [uuid4() for _ in range(3)]
    chunk_ids = [uuid4() for _ in range(3)]
    source_path = f"acceptance://mixed-acl-{document_id}.pdf"
    texts = ["Authority-only preceding context.", "Tenant-visible anchor context.", "Authority-only following context."]
    anchor = {
        "chunk_id": chunk_ids[1], "document_id": document_id, "chunk_index": 1, "chunk_text": texts[1],
        "section_title": "Mixed ACL fixture", "clause_number": "MIXED-1", "document_title": "Mixed ACL fixture",
        "filename": "acceptance_mixed_acl.pdf", "page_number": 2, "fused_score": 1.0,
    }
    with connect(acceptance_guard) as connection:
        try:
            register_vector(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO rag.document
                       (document_id,source_path,original_filename,file_sha256,file_size_bytes,page_count,classification,extraction_strategy,extraction_quality,source_metadata,ingestion_state)
                       VALUES (%s,%s,%s,%s,0,3,'acceptance_fixture','fixture',100,'{}'::jsonb,'indexed')""",
                    (document_id, source_path, "acceptance_mixed_acl.pdf", str(document_id),),
                )
                for page_id, page_number in zip(page_ids, (1, 2, 3)):
                    cursor.execute(
                        """INSERT INTO rag.document_page
                           (page_id,document_id,page_number,extracted_text,extraction_method,extraction_quality,page_metadata)
                           VALUES (%s,%s,%s,%s,'fixture',100,'{}'::jsonb)""",
                        (page_id, document_id, page_number, texts[page_number - 1]),
                    )
                for index, (chunk_id, page_id, text_value) in enumerate(zip(chunk_ids, page_ids, texts)):
                    cursor.execute(
                        """INSERT INTO rag.chunk
                           (chunk_id,document_id,page_id,chunk_index,chunk_type,chunk_text,section_title,clause_number,token_estimate,acl_roles,metadata,embedding,embedding_model)
                           VALUES (%s,%s,%s,%s,'fixture',%s,'Mixed ACL fixture',%s,8,%s,'{}'::jsonb,%s,'acceptance-fixture')""",
                        (
                            chunk_id, document_id, page_id, index, text_value, f"MIXED-{index}",
                            ["authority"] if index != 1 else [], Vector([1.0] + [0.0] * 1023),
                        ),
                    )
            connection.commit()

            expanded, _tokens, _truncated = _expand_context_with_metadata(settings, [anchor], "tenant", "multi_document")
            adjacent = _adjacent_page_candidates(settings, [anchor], "tenant", analyse_query("What connected policy applies?"))

            assert len(expanded) == 1
            assert expanded[0]["context_text"] == texts[1]
            assert adjacent == []
        finally:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM rag.document WHERE document_id=%s", (document_id,))
            connection.commit()


def test_rag_query_citation_acl(acceptance_guard: str, credentials: dict[str, str]) -> None:
    with httpx.Client(base_url="http://127.0.0.1:8016", timeout=180) as authority, httpx.Client(
        base_url="http://127.0.0.1:8016", timeout=180
    ) as tenant:
        login(authority, "do_test", credentials["DO_TEST"])
        login(tenant, "tenant_test", credentials["TENANT_TEST"], "tenant")
        allowed = authority.post("/api/v1/query", json={"question": "Who may approve an official agenda handoff?", "limit": 8})
        denied = tenant.post("/api/v1/query", json={"question": "What does the role-restricted note say?", "limit": 8})
        assert allowed.status_code == 200, allowed.text
        assert denied.status_code == 200, denied.text
        allowed_sources = {source["filename"] for source in allowed.json()["sources"]}
        denied_payload = denied.json()
        denied_sources = {source["filename"] for source in denied_payload["sources"]}
        assert "acceptance_authority_policy.pdf" in allowed_sources
        assert "acceptance_restricted_policy.pdf" not in denied_sources
        assert "role-restricted evidence" not in denied_payload["answer"]


def test_agenda_authorization_and_active_role_recheck(acceptance_guard: str, credentials: dict[str, str]) -> None:
    do_agenda = _agenda_id_by_state(acceptance_guard, "DO_DRAFT")
    submitted_no = _agenda_id_by_state(acceptance_guard, "SUBMITTED_TO_NO")
    with httpx.Client(base_url="http://127.0.0.1:8016", timeout=60) as do, httpx.Client(
        base_url="http://127.0.0.1:8016", timeout=60
    ) as no, httpx.Client(base_url="http://127.0.0.1:8016", timeout=60) as tenant:
        login(do, "do_test", credentials["DO_TEST"])
        login(no, "no_test", credentials["NO_TEST"])
        login(tenant, "tenant_test", credentials["TENANT_TEST"], "tenant")
        assert do.get(f"/api/v1/workflow/agendas/{do_agenda}").status_code == 200
        assert no.get(f"/api/v1/workflow/agendas/{submitted_no}").status_code == 200
        assert tenant.get(f"/api/v1/workflow/agendas/{do_agenda}").status_code == 403
        assert do.post(f"/api/v1/workflow/agendas/{submitted_no}/revisions", json={"draft_text": "wrong owner"}).status_code in {404, 409}
        before = db_snapshot(acceptance_guard)
        with connect(acceptance_guard) as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE public.admin_roles SET is_active=false WHERE admin_id=10001")
        try:
            response = do.post(f"/api/v1/workflow/agendas/{do_agenda}/revisions", json={"draft_text": "inactive role"})
            assert response.status_code == 403
            assert db_snapshot(acceptance_guard)["agenda_versions"] == before["agenda_versions"]
        finally:
            with connect(acceptance_guard) as connection, connection.cursor() as cursor:
                cursor.execute("UPDATE public.admin_roles SET is_active=true WHERE admin_id=10001")


def test_billing_and_tender_authorization_before_mutation(acceptance_guard: str, credentials: dict[str, str]) -> None:
    with httpx.Client(base_url="http://127.0.0.1:8016", timeout=60) as authority, httpx.Client(
        base_url="http://127.0.0.1:8016", timeout=60
    ) as tenant:
        login(authority, "do_test", credentials["DO_TEST"])
        login(tenant, "tenant_test", credentials["TENANT_TEST"], "tenant")
        for path in ("/api/v1/billing/status", "/api/v1/billing/rules", "/api/v1/billing/tenancies", "/api/v1/tender/config", "/api/v1/tender/plots", "/api/v1/tender/workflows"):
            assert authority.get(path).status_code == 200
            assert tenant.get(path).status_code == 403
        before = db_snapshot(acceptance_guard)
        billing_payload = {"customer_id": "ACCEPTANCE-TENANCY-001", "tenancy_id": "ACCEPTANCE-TENANCY-001", "target_year": 2027, "target_month": 12, "bill_type": "General billing", "billing_frequency": "Monthly", "area": 100, "rates": {}}
        assert tenant.post("/api/v1/billing/predict", json=billing_payload).status_code == 403
        tender_path = Path.cwd() / "tests" / "runtime" / "tender" / "tender_workflows.json"
        tender_before = tender_path.read_bytes()
        assert tenant.post("/api/v1/tender/workflows", json={"plot_id": "1", "checklist_key": "lac", "fields": {}, "checklist_answers": {}}).status_code == 403
        assert tender_path.read_bytes() == tender_before
        after = db_snapshot(acceptance_guard)
        assert after["chat_sessions"] == before["chat_sessions"]


def test_error_responses_and_audit_redaction(acceptance_guard: str, credentials: dict[str, str], client: httpx.Client) -> None:
    login(client, "do_test", credentials["DO_TEST"])
    assert client.get("/api/v1/chat/sessions/not-a-uuid").status_code == 422
    assert client.get("/api/v1/chat/sessions/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.post("/api/authority/login", json={"username": "do_test", "password": "wrong"}).status_code == 401
    with connect(acceptance_guard) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT event_type, metadata::text FROM rag.audit_event ORDER BY created_at DESC LIMIT 100")
        audit_text = "\n".join(f"{event}:{metadata}" for event, metadata in cursor.fetchall()).lower()
    for forbidden in ("password", "session_token", "database_url", "postgresql://"):
        assert forbidden not in audit_text
