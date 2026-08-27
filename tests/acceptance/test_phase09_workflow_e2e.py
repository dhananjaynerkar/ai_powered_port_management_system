"""Phase 09 official DO -> NO -> HO workflow acceptance tests."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import httpx
from conftest import API_BASE_URL, db_snapshot, login
from psycopg import connect


def _assert_gate(dsn: str) -> None:
    with connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT current_database()")
        assert cursor.fetchone()[0] == "portproject_acceptance"
        cursor.execute("SELECT environment, database_name, fixture_version FROM public.acceptance_environment WHERE fixture_id=1")
        assert cursor.fetchone() == ("acceptance", "portproject_acceptance", 1)


def _source(dsn: str) -> dict[str, object]:
    _assert_gate(dsn)
    with connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT sources FROM rag.chat_message WHERE chat_session_id=(SELECT chat_session_id FROM rag.chat_session WHERE title='private_cited') AND sender='assistant'")
        row = cursor.fetchone()
    assert row and row[0]
    return dict(row[0][0])


def _seed_cited_chat(dsn: str, title: str) -> UUID:
    """Create a disposable cited DO chat for one acceptance scenario."""
    _assert_gate(dsn)
    chat_id = uuid4()
    source = _source(dsn)
    with connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO rag.chat_session (chat_session_id,user_id,principal_id,title) VALUES (%s,NULL,'authority:10001',%s)",
            (chat_id, title),
        )
        cursor.execute(
            "INSERT INTO rag.chat_message (chat_session_id,sender,content,sources) VALUES (%s,'user',%s,'[]'::jsonb)",
            (chat_id, "What does the acceptance policy require?"),
        )
        cursor.execute(
            "INSERT INTO rag.chat_message (chat_session_id,sender,content,sources) VALUES (%s,'assistant',%s,%s)",
            (chat_id, "The acceptance policy answer is grounded in the cited source [S1].", json.dumps([source])),
        )
    return chat_id


def _agenda_id(dsn: str, title: str) -> UUID:
    _assert_gate(dsn)
    with connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT agenda_id FROM rag.agenda WHERE title=%s ORDER BY agenda_number DESC LIMIT 1", (title,))
        row = cursor.fetchone()
    assert row, f"agenda fixture {title!r} is missing"
    return row[0]


def _agenda_state(dsn: str, agenda_id: UUID) -> dict[str, object]:
    _assert_gate(dsn)
    with connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT state,current_owner_principal,current_owner_role,assigned_nodal_principal,assigned_hod_principal,editing_version,finalized_at FROM rag.agenda WHERE agenda_id=%s", (agenda_id,))
        row = cursor.fetchone()
        assert row
        keys = ("state", "current_owner_principal", "current_owner_role", "assigned_nodal_principal", "assigned_hod_principal", "editing_version", "finalized_at")
        return dict(zip(keys, row, strict=True))


def _counts(dsn: str, agenda_id: UUID) -> dict[str, int]:
    _assert_gate(dsn)
    with connect(dsn) as connection, connection.cursor() as cursor:
        counts: dict[str, int] = {}
        for key, table in (("versions", "agenda_version"), ("messages", "agenda_message"), ("capsules", "context_capsule")):
            cursor.execute(f"SELECT COUNT(*) FROM rag.{table} WHERE agenda_id=%s", (agenda_id,))
            counts[key] = int(cursor.fetchone()[0])
        return counts


def _client() -> httpx.Client:
    return httpx.Client(base_url=API_BASE_URL, timeout=180, follow_redirects=False)


def _create_agenda(client: httpx.Client, dsn: str, title: str) -> tuple[UUID, UUID]:
    chat_id = _seed_cited_chat(dsn, title)
    response = client.post("/api/v1/workflow/agendas", json={"chat_session_id": str(chat_id), "title": title})
    assert response.status_code == 200, response.text
    agenda_id = UUID(response.json()["agenda"]["agenda_id"])
    return chat_id, agenda_id


def test_agenda_creation_from_cited_chat_and_version_one(acceptance_guard: str, credentials: dict[str, str]) -> None:
    with _client() as do:
        login(do, "do_test", credentials["DO_TEST"])
        chat_id, agenda_id = _create_agenda(do, acceptance_guard, "phase09-lifecycle")
        detail = do.get(f"/api/v1/workflow/agendas/{agenda_id}")
        assert detail.status_code == 200
        agenda = detail.json()["agenda"]
        assert agenda["state"] == "DO_DRAFT"
        assert agenda["current_owner_principal"] == "authority:10001"
        assert agenda["current_owner_role"] == "DO"
        assert agenda["editing_version"] == 1
        assert len(agenda["versions"]) == 1
        assert agenda["versions"][0]["version"] == 1
        assert agenda["versions"][0]["created_by_principal"] == "authority:10001"
        assert _agenda_state(acceptance_guard, agenda_id)["state"] == "DO_DRAFT"
        before = _counts(acceptance_guard, agenda_id)
        deleted = do.delete(f"/api/v1/chat/sessions/{chat_id}")
        assert deleted.status_code == 409
        assert _counts(acceptance_guard, agenda_id) == before


def test_agenda_creation_rejects_uncited_empty_foreign_and_non_do_chats(acceptance_guard: str, credentials: dict[str, str]) -> None:
    with _client() as do, _client() as no, _client() as tenant:
        login(do, "do_test", credentials["DO_TEST"])
        login(no, "no_test", credentials["NO_TEST"])
        login(tenant, "tenant_test", credentials["TENANT_TEST"], "tenant")
        baseline = db_snapshot(acceptance_guard)
        for title in ("private_normal", "private_empty"):
            with connect(acceptance_guard) as connection, connection.cursor() as cursor:
                cursor.execute("SELECT chat_session_id FROM rag.chat_session WHERE title=%s", (title,))
                chat_id = cursor.fetchone()[0]
            response = do.post("/api/v1/workflow/agendas", json={"chat_session_id": str(chat_id)})
            assert response.status_code == 400
        foreign = tenant.post("/api/v1/chat/sessions", json={"title": "phase09-foreign"})
        assert foreign.status_code == 200
        foreign_id = foreign.json()["chat_session_id"]
        assert do.post("/api/v1/workflow/agendas", json={"chat_session_id": foreign_id}).status_code == 404
        assert no.post("/api/v1/workflow/agendas", json={"chat_session_id": foreign_id}).status_code == 403
        assert do.post("/api/v1/workflow/agendas", json={"chat_session_id": str(uuid4())}).status_code == 404
        assert do.post("/api/v1/workflow/agendas", json={"chat_session_id": "not-a-uuid"}).status_code == 422
        assert db_snapshot(acceptance_guard)["agenda_versions"] == baseline["agenda_versions"]
        assert tenant.delete(f"/api/v1/chat/sessions/{foreign_id}").status_code == 204


def test_complete_do_no_do_revision_resubmit_no_ho_approval_and_capsule_history(acceptance_guard: str, credentials: dict[str, str]) -> None:
    with _client() as do, _client() as no, _client() as ho:
        login(do, "do_test", credentials["DO_TEST"])
        login(no, "no_test", credentials["NO_TEST"])
        login(ho, "ho_test", credentials["HO_TEST"])
        chat_id, agenda_id = _create_agenda(do, acceptance_guard, "phase09-complete-lifecycle")
        initial = do.get(f"/api/v1/workflow/agendas/{agenda_id}").json()["agenda"]
        assert initial["state"] == "DO_DRAFT"

        first = do.post(f"/api/v1/workflow/agendas/{agenda_id}/transition", json={"action": "submit_to_nodal", "target_principal": "authority:10002", "note": "Initial DO to NO handoff."})
        assert first.status_code == 200, first.text
        assert first.json()["agenda"]["state"] == "SUBMITTED_TO_NO"
        state = _agenda_state(acceptance_guard, agenda_id)
        assert state["current_owner_principal"] == "authority:10002"
        assert state["current_owner_role"] == "NO"
        assert state["assigned_nodal_principal"] == "authority:10002"
        assert _counts(acceptance_guard, agenda_id) == {"versions": 1, "messages": 2, "capsules": 1}

        returned = no.post(f"/api/v1/workflow/agendas/{agenda_id}/transition", json={"action": "return_to_do", "note": "Please revise the draft."})
        assert returned.status_code == 200, returned.text
        assert returned.json()["agenda"]["state"] == "RETURNED_TO_DO"
        assert _agenda_state(acceptance_guard, agenda_id)["current_owner_principal"] == "authority:10001"

        old_detail = do.get(f"/api/v1/workflow/agendas/{agenda_id}").json()["agenda"]
        old_v1 = old_detail["versions"][-1]["draft_text"]
        revision = do.post(f"/api/v1/workflow/agendas/{agenda_id}/revisions", json={"draft_text": "Revised official draft for Phase 09."})
        assert revision.status_code == 200, revision.text
        assert revision.json()["agenda"]["editing_version"] == 2
        detail = do.get(f"/api/v1/workflow/agendas/{agenda_id}").json()["agenda"]
        assert len(detail["versions"]) == 2
        assert detail["versions"][-1]["draft_text"] == old_v1
        assert detail["versions"][0]["draft_text"] == "Revised official draft for Phase 09."

        resubmit = do.post(f"/api/v1/workflow/agendas/{agenda_id}/transition", json={"action": "submit_to_nodal", "target_principal": "authority:10002", "note": "Revised draft resubmitted."})
        assert resubmit.status_code == 200
        assert _agenda_state(acceptance_guard, agenda_id)["state"] == "SUBMITTED_TO_NO"
        assert _counts(acceptance_guard, agenda_id)["capsules"] == 3

        to_ho = no.post(f"/api/v1/workflow/agendas/{agenda_id}/transition", json={"action": "submit_to_hod", "target_principal": "authority:10003", "note": "NO review complete."})
        assert to_ho.status_code == 200, to_ho.text
        state = _agenda_state(acceptance_guard, agenda_id)
        assert state["state"] == "SUBMITTED_TO_HO"
        assert state["current_owner_principal"] == "authority:10003"
        assert state["assigned_hod_principal"] == "authority:10003"

        capsules_before = ho.get(f"/api/v1/workflow/agendas/{agenda_id}").json()["agenda"]["context_capsules"]
        assert len(capsules_before) == 4
        approved = ho.post(f"/api/v1/workflow/agendas/{agenda_id}/transition", json={"action": "approve", "note": "Approved by HOD."})
        assert approved.status_code == 200, approved.text
        final = _agenda_state(acceptance_guard, agenda_id)
        assert final["state"] == "APPROVED"
        assert final["current_owner_principal"] == "authority:10003"
        assert final["current_owner_role"] == "HO"
        assert final["finalized_at"] is not None
        assert _counts(acceptance_guard, agenda_id)["versions"] == 2
        assert len(ho.get(f"/api/v1/workflow/agendas/{agenda_id}").json()["agenda"]["context_capsules"]) == 5


def test_ho_reject_supported_flow(acceptance_guard: str, credentials: dict[str, str]) -> None:
    agenda_id = _agenda_id(acceptance_guard, "agenda_submitted_to_ho")
    with _client() as ho:
        login(ho, "ho_test", credentials["HO_TEST"])
        before = _counts(acceptance_guard, agenda_id)
        response = ho.post(f"/api/v1/workflow/agendas/{agenda_id}/transition", json={"action": "reject", "note": "Rejected for missing evidence."})
        assert response.status_code == 200, response.text
        state = _agenda_state(acceptance_guard, agenda_id)
        assert state["state"] == "REJECTED"
        assert state["current_owner_principal"] == "authority:10003"
        assert state["finalized_at"] is not None
        after = _counts(acceptance_guard, agenda_id)
        assert after["versions"] == before["versions"]
        assert after["capsules"] == before["capsules"] + 1


def test_wrong_role_owner_state_target_and_inactive_protection(acceptance_guard: str, credentials: dict[str, str]) -> None:
    agenda_id = _agenda_id(acceptance_guard, "agenda_do_draft")
    with _client() as do, _client() as no, _client() as ho, _client() as tenant:
        login(do, "do_test", credentials["DO_TEST"])
        login(no, "no_test", credentials["NO_TEST"])
        login(ho, "ho_test", credentials["HO_TEST"])
        login(tenant, "tenant_test", credentials["TENANT_TEST"], "tenant")
        before = _counts(acceptance_guard, agenda_id)
        for client, action, target in ((do, "submit_to_hod", "authority:10003"), (do, "approve", None), (ho, "submit_to_nodal", "authority:10002"), (tenant, "submit_to_nodal", "authority:10002")):
            response = client.post(f"/api/v1/workflow/agendas/{agenda_id}/transition", json={"action": action, "target_principal": target})
            assert response.status_code in {403, 404, 409}
        assert _counts(acceptance_guard, agenda_id) == before

        submitted_no = _agenda_id(acceptance_guard, "agenda_submitted_to_no")
        before_no = _counts(acceptance_guard, submitted_no)
        response = no.post(f"/api/v1/workflow/agendas/{submitted_no}/revisions", json={"draft_text": "NO must not edit a DO draft."})
        assert response.status_code in {403, 409}
        assert _counts(acceptance_guard, submitted_no) == before_no

        with connect(acceptance_guard) as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE public.admin_roles SET is_active=false WHERE admin_id=10001")
        try:
            response = do.post(f"/api/v1/workflow/agendas/{agenda_id}/transition", json={"action": "submit_to_nodal", "target_principal": "authority:10002"})
            assert response.status_code == 403
            assert _counts(acceptance_guard, agenda_id) == before
        finally:
            with connect(acceptance_guard) as connection, connection.cursor() as cursor:
                cursor.execute("UPDATE public.admin_roles SET is_active=true WHERE admin_id=10001")

        submitted_no = _agenda_id(acceptance_guard, "agenda_submitted_to_no")
        submitted_ho = _agenda_id(acceptance_guard, "agenda_submitted_to_ho")
        for admin_id, client, agenda, action, target in (
            (10002, no, submitted_no, "submit_to_hod", "authority:10003"),
            (10003, ho, submitted_ho, "approve", None),
        ):
            with connect(acceptance_guard) as connection, connection.cursor() as cursor:
                cursor.execute("UPDATE public.admin_roles SET is_active=false WHERE admin_id=%s", (admin_id,))
            try:
                response = client.post(f"/api/v1/workflow/agendas/{agenda}/transition", json={"action": action, "target_principal": target})
                assert response.status_code == 403
            finally:
                with connect(acceptance_guard) as connection, connection.cursor() as cursor:
                    cursor.execute("UPDATE public.admin_roles SET is_active=true WHERE admin_id=%s", (admin_id,))

        for target in (None, "authority:10003", "authority:10099", "tenant:20001"):
            response = do.post(f"/api/v1/workflow/agendas/{agenda_id}/transition", json={"action": "submit_to_nodal", "target_principal": target})
            assert response.status_code in {409, 422}
        assert _counts(acceptance_guard, agenda_id) == before


def test_invalid_duplicate_terminal_and_stale_transitions_are_atomic(acceptance_guard: str, credentials: dict[str, str]) -> None:
    submitted_no = _agenda_id(acceptance_guard, "agenda_submitted_to_no")
    approved = _agenda_id(acceptance_guard, "agenda_approved")
    rejected = _agenda_id(acceptance_guard, "agenda_rejected")
    with _client() as do, _client() as no, _client() as ho:
        login(do, "do_test", credentials["DO_TEST"])
        login(no, "no_test", credentials["NO_TEST"])
        login(ho, "ho_test", credentials["HO_TEST"])
        before = _counts(acceptance_guard, submitted_no)
        for action, target in (("submit_to_nodal", "authority:10002"), ("return_to_do", None), ("approve", None)):
            response = do.post(f"/api/v1/workflow/agendas/{submitted_no}/transition", json={"action": action, "target_principal": target})
            assert response.status_code in {403, 409}
        assert _counts(acceptance_guard, submitted_no) == before
        for agenda, client in ((approved, ho), (rejected, ho)):
            state_before = _agenda_state(acceptance_guard, agenda)
            count_before = _counts(acceptance_guard, agenda)
            for action in ("approve", "reject", "return_to_do", "submit_to_hod"):
                response = client.post(f"/api/v1/workflow/agendas/{agenda}/transition", json={"action": action, "target_principal": "authority:10003" if action == "submit_to_hod" else None})
                assert response.status_code in {403, 409}
            assert _agenda_state(acceptance_guard, agenda) == state_before
            assert _counts(acceptance_guard, agenda) == count_before

        stale = _agenda_id(acceptance_guard, "agenda_do_draft")
        stale_before = _agenda_state(acceptance_guard, stale)
        first = do.post(f"/api/v1/workflow/agendas/{stale}/transition", json={"action": "submit_to_nodal", "target_principal": "authority:10002"})
        assert first.status_code == 200
        stale_response = do.post(f"/api/v1/workflow/agendas/{stale}/transition", json={"action": "submit_to_nodal", "target_principal": "authority:10002"})
        assert stale_response.status_code == 409
        assert _agenda_state(acceptance_guard, stale)["state"] == "SUBMITTED_TO_NO"
        assert stale_before["state"] == "DO_DRAFT"


def test_context_capsule_snapshot_and_workflow_ai_query(acceptance_guard: str, credentials: dict[str, str]) -> None:
    agenda_id = _agenda_id(acceptance_guard, "agenda_returned_to_do")
    with _client() as do, _client() as no:
        login(do, "do_test", credentials["DO_TEST"])
        login(no, "no_test", credentials["NO_TEST"])
        detail_before = do.get(f"/api/v1/workflow/agendas/{agenda_id}").json()["agenda"]
        capsules_before = detail_before["context_capsules"]
        assert capsules_before
        first_capsule = capsules_before[0]
        response = do.post(f"/api/v1/workflow/agendas/{agenda_id}/query", json={"question": "What does the acceptance policy require?", "limit": 4})
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["citation_valid"] is True
        assert payload["sources"]
        detail_after_query = do.get(f"/api/v1/workflow/agendas/{agenda_id}").json()["agenda"]
        assert any(message["message_type"] == "AI" and message["sources"] for message in detail_after_query["messages"])
        assert detail_after_query["context_capsules"][0]["sources"] == first_capsule["sources"]
        later_source = dict(payload["sources"][0])
        later_source["source_id"] = "later-evidence"
        _assert_gate(acceptance_guard)
        with connect(acceptance_guard) as connection, connection.cursor() as cursor:
            cursor.execute("INSERT INTO rag.agenda_message (agenda_id,sender_principal,message_type,content,sources) VALUES (%s,'authority:10001','AI','Later evidence snapshot test',%s)", (agenda_id, json.dumps([later_source])))
        frozen = do.get(f"/api/v1/workflow/agendas/{agenda_id}").json()["agenda"]["context_capsules"][0]
        assert frozen["sources"] == first_capsule["sources"]


def test_workflow_ai_requires_current_owner_and_participant_access(acceptance_guard: str, credentials: dict[str, str]) -> None:
    agenda_id = _agenda_id(acceptance_guard, "agenda_returned_to_do")
    before = _counts(acceptance_guard, agenda_id)
    with _client() as no, _client() as tenant:
        login(no, "no_test", credentials["NO_TEST"])
        login(tenant, "tenant_test", credentials["TENANT_TEST"], "tenant")
        non_owner = no.post(f"/api/v1/workflow/agendas/{agenda_id}/query", json={"question": "What does the acceptance policy require?", "limit": 4})
        assert non_owner.status_code == 409
        assert tenant.post(f"/api/v1/workflow/agendas/{agenda_id}/query", json={"question": "What does the acceptance policy require?", "limit": 4}).status_code == 403
    assert _counts(acceptance_guard, agenda_id) == before


def test_concurrent_same_and_conflicting_transitions_have_one_commit(acceptance_guard: str, credentials: dict[str, str]) -> None:
    same = _agenda_id(acceptance_guard, "agenda_returned_to_do")
    conflict = _agenda_id(acceptance_guard, "agenda_submitted_to_no")

    def request(username: str, password: str, action: str, target: str | None, note: str) -> int:
        with _client() as client:
            login(client, username, password)
            return client.post(f"/api/v1/workflow/agendas/{same if action == 'submit_to_nodal' else conflict}/transition", json={"action": action, "target_principal": target, "note": note}).status_code

    same_before = _counts(acceptance_guard, same)
    with ThreadPoolExecutor(max_workers=2) as pool:
        same_results = list(pool.map(lambda _: request("do_test", credentials["DO_TEST"], "submit_to_nodal", "authority:10002", "Concurrent DO handoff."), range(2)))
    assert sorted(same_results) == [200, 409]
    same_counts = _counts(acceptance_guard, same)
    assert same_counts["capsules"] == same_before["capsules"] + 1
    assert _agenda_state(acceptance_guard, same)["state"] == "SUBMITTED_TO_NO"

    conflict_before = _counts(acceptance_guard, conflict)
    def conflicting(action: str, target: str | None) -> int:
        return request("no_test", credentials["NO_TEST"], action, target, "Concurrent NO action.")

    with ThreadPoolExecutor(max_workers=2) as pool:
        conflict_results = list(pool.map(lambda pair: conflicting(*pair), (("return_to_do", None), ("submit_to_hod", "authority:10003"))))
    assert sorted(conflict_results) == [200, 409]
    state = _agenda_state(acceptance_guard, conflict)
    assert state["state"] in {"RETURNED_TO_DO", "SUBMITTED_TO_HO"}
    assert _counts(acceptance_guard, conflict)["capsules"] == conflict_before["capsules"] + 1


def test_concurrent_revision_versions_are_unique_and_immutable(acceptance_guard: str, credentials: dict[str, str]) -> None:
    with _client() as do, _client() as no:
        login(do, "do_test", credentials["DO_TEST"])
        login(no, "no_test", credentials["NO_TEST"])
        _, agenda_id = _create_agenda(do, acceptance_guard, "phase09-concurrent-revision")
        assert do.post(f"/api/v1/workflow/agendas/{agenda_id}/transition", json={"action": "submit_to_nodal", "target_principal": "authority:10002"}).status_code == 200
        assert no.post(f"/api/v1/workflow/agendas/{agenda_id}/transition", json={"action": "return_to_do", "note": "Return for concurrent revision."}).status_code == 200

        def revise(text: str) -> int:
            with _client() as client:
                login(client, "do_test", credentials["DO_TEST"])
                return client.post(f"/api/v1/workflow/agendas/{agenda_id}/revisions", json={"draft_text": text}).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(revise, ("Concurrent revision A", "Concurrent revision B")))
        assert sorted(results) in ([200, 200], [200, 409])
        detail = do.get(f"/api/v1/workflow/agendas/{agenda_id}").json()["agenda"]
        versions = [item["version"] for item in detail["versions"]]
        assert versions == sorted(set(versions), reverse=True)
        assert versions in ([3, 2, 1], [2, 1])
        successful_texts = {item["draft_text"] for item in detail["versions"] if item["version"] > 1}
        assert successful_texts.issubset({"Concurrent revision A", "Concurrent revision B"})
