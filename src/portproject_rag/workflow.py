from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException
from psycopg import connect
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .auth import PortalUser
from .settings import Settings

ROLE_LABELS = {"DO": "Data Entry Operator", "NO": "Nodal Officer", "HO": "Head of Department"}


@dataclass(frozen=True, slots=True)
class TransitionResult:
    agenda: dict[str, object]
    previous_owner: str
    action: str


def authority_identity(settings: Settings, user: PortalUser) -> tuple[str, int]:
    if user.role != "authority" or not user.principal_id.startswith("authority:"):
        raise HTTPException(status_code=403, detail="Authority access is required.")
    try:
        admin_id = int(user.principal_id.split(":", 1)[1])
    except (IndexError, ValueError) as exc:
        raise HTTPException(status_code=403, detail="Invalid authority identity.") from exc
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT ar.role_id FROM public.admin_roles ar
                JOIN public.admin_users au ON au.admin_id=ar.admin_id
                WHERE ar.admin_id=%s AND ar.is_active IS TRUE AND au.account_status_code='A'
                ORDER BY ar.admin_role_id LIMIT 1""", (admin_id,))
            row = cursor.fetchone()
    role = str(row[0]).upper() if row else ""
    if role not in ROLE_LABELS:
        raise HTTPException(status_code=403, detail="Your role cannot participate in agenda workflow.")
    return role, admin_id


def officer_directory(settings: Settings) -> list[dict[str, object]]:
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT au.admin_id, au.name, au.user_name, ar.role_id
                FROM public.admin_users au JOIN public.admin_roles ar ON ar.admin_id=au.admin_id
                WHERE au.account_status_code='A' AND ar.is_active IS TRUE AND ar.role_id IN ('DO','NO','HO')
                ORDER BY ar.role_id, COALESCE(au.name, au.user_name), au.admin_id""")
            rows = cursor.fetchall()
    return [
        {"principal_id": f"authority:{row[0]}", "name": row[1] or row[2], "username": row[2], "role": row[3], "role_title": ROLE_LABELS[row[3]]}
        for row in rows
    ]


def _display_code(number: int) -> str:
    return f"AGENDA-{number:06d}"


def _name_map(settings: Settings, principals: set[str]) -> dict[str, str]:
    admin_ids = []
    for principal in principals:
        if principal and principal.startswith("authority:"):
            try:
                admin_ids.append(int(principal.split(":", 1)[1]))
            except ValueError:
                continue
    if not admin_ids:
        return {}
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT admin_id, COALESCE(name, user_name) FROM public.admin_users WHERE admin_id=ANY(%s)", (admin_ids,))
            return {f"authority:{row[0]}": row[1] for row in cursor.fetchall()}


def _serialize_agenda(settings: Settings, row: dict[str, object], viewer: PortalUser) -> dict[str, object]:
    principals = {
        str(row[key]) for key in ("created_by_principal", "assigned_do_principal", "assigned_nodal_principal", "assigned_hod_principal", "current_owner_principal") if row.get(key)
    }
    names = _name_map(settings, principals)
    state = str(row["state"])
    return {
        "agenda_id": str(row["agenda_id"]),
        "code": _display_code(int(row["agenda_number"])),
        "title": row["title"],
        "state": state,
        "editing_version": row["editing_version"],
        "current_owner_principal": row["current_owner_principal"],
        "current_owner_role": row["current_owner_role"],
        "current_owner_name": names.get(str(row["current_owner_principal"]), str(row["current_owner_principal"])),
        "assigned_do_principal": row["assigned_do_principal"],
        "assigned_do_name": names.get(str(row["assigned_do_principal"]), str(row["assigned_do_principal"])),
        "assigned_nodal_principal": row["assigned_nodal_principal"],
        "assigned_nodal_name": names.get(str(row["assigned_nodal_principal"]), "Pending Assignment") if row["assigned_nodal_principal"] else "Pending Assignment",
        "assigned_hod_principal": row["assigned_hod_principal"],
        "assigned_hod_name": names.get(str(row["assigned_hod_principal"]), "Pending Assignment") if row["assigned_hod_principal"] else "Pending Assignment",
        "is_read_only": row["current_owner_principal"] != viewer.principal_id or state in {"APPROVED", "REJECTED"},
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def create_agenda_from_chat(settings: Settings, user: PortalUser, chat_session_id: UUID, title: str | None) -> dict[str, object]:
    role, _ = authority_identity(settings, user)
    if role != "DO":
        raise HTTPException(status_code=403, detail="Only a Data Entry Operator can create an agenda draft.")
    schema = settings.schema_name
    with connect(settings.database_url.unicode_string(), row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT title FROM {schema}.chat_session WHERE chat_session_id=%s AND principal_id=%s FOR UPDATE", (chat_session_id, user.principal_id))
            session = cursor.fetchone()
            if not session:
                raise HTTPException(status_code=404, detail="Conversation not found.")
            cursor.execute(f"SELECT sender, content, sources FROM {schema}.chat_message WHERE chat_session_id=%s ORDER BY created_at, message_id", (chat_session_id,))
            messages = cursor.fetchall()
            if not messages:
                raise HTTPException(status_code=400, detail="Ask a document question before creating an agenda.")
            if not any(item["sender"] == "assistant" and item["sources"] for item in messages):
                raise HTTPException(status_code=400, detail="An agenda can only be created after a cited document answer is available in this conversation.")
            draft_text = "\n\n".join(f"{('Officer query' if item['sender'] == 'user' else 'Verified RAG response')}:\n{item['content']}" for item in messages)
            agenda_title = (title or str(session["title"])).strip()[:180] or "Policy agenda"
            cursor.execute(f"""INSERT INTO {schema}.agenda
                (title, source_chat_session_id, created_by_principal, assigned_do_principal, current_owner_principal, current_owner_role)
                VALUES (%s,%s,%s,%s,%s,'DO') RETURNING *""",
                (agenda_title, chat_session_id, user.principal_id, user.principal_id, user.principal_id))
            agenda = cursor.fetchone()
            cursor.execute(f"""INSERT INTO {schema}.agenda_version
                (agenda_id, version_number, draft_text, created_by_principal) VALUES (%s,1,%s,%s)""",
                (agenda["agenda_id"], draft_text, user.principal_id))
            cursor.execute(f"""INSERT INTO {schema}.agenda_message
                (agenda_id, sender_principal, message_type, content) VALUES (%s,%s,'SYSTEM',%s)""",
                (agenda["agenda_id"], user.principal_id, "Private RAG conversation promoted to an official agenda draft."))
    return _serialize_agenda(settings, agenda, user)


def list_agendas(settings: Settings, user: PortalUser) -> list[dict[str, object]]:
    authority_identity(settings, user)
    schema = settings.schema_name
    with connect(settings.database_url.unicode_string(), row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"""SELECT * FROM {schema}.agenda WHERE
                %s IN (created_by_principal, assigned_do_principal, assigned_nodal_principal, assigned_hod_principal)
                ORDER BY updated_at DESC, agenda_number DESC""", (user.principal_id,))
            rows = cursor.fetchall()
    return [_serialize_agenda(settings, row, user) for row in rows]


def agenda_detail(settings: Settings, user: PortalUser, agenda_id: UUID) -> dict[str, object]:
    authority_identity(settings, user)
    schema = settings.schema_name
    with connect(settings.database_url.unicode_string(), row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"""SELECT * FROM {schema}.agenda WHERE agenda_id=%s AND
                %s IN (created_by_principal, assigned_do_principal, assigned_nodal_principal, assigned_hod_principal)""", (agenda_id, user.principal_id))
            agenda = cursor.fetchone()
            if not agenda:
                raise HTTPException(status_code=404, detail="Agenda not found.")
            cursor.execute(f"SELECT * FROM {schema}.agenda_message WHERE agenda_id=%s ORDER BY created_at, message_id", (agenda_id,))
            messages = cursor.fetchall()
            cursor.execute(f"SELECT * FROM {schema}.context_capsule WHERE agenda_id=%s ORDER BY created_at, capsule_id", (agenda_id,))
            capsules = cursor.fetchall()
            cursor.execute(f"SELECT version_number, draft_text, created_by_principal, created_at FROM {schema}.agenda_version WHERE agenda_id=%s ORDER BY version_number DESC", (agenda_id,))
            versions = cursor.fetchall()
    principals = {str(item["sender_principal"]) for item in messages} | {str(item["recipient_principal"]) for item in messages if item["recipient_principal"]}
    names = _name_map(settings, principals)

    def snapshot_sources(created_at: object) -> list[dict[str, object]]:
        """Return the real AI citations available when a handoff snapshot was created.

        Context capsules intentionally remain a compact workflow snapshot table and do
        not duplicate source JSON. The evidence shown for a capsule is therefore
        derived from the official AI messages that existed at that timestamp.
        """
        sources: list[dict[str, object]] = []
        seen: set[str] = set()
        for message in messages:
            if message["message_type"] != "AI" or message["created_at"] > created_at:
                continue
            raw_sources = message["sources"]
            if not isinstance(raw_sources, list):
                continue
            for source in raw_sources:
                if not isinstance(source, dict):
                    continue
                key = str(source.get("source_id") or f"{source.get('filename', '')}:{source.get('page', '')}")
                if key in seen:
                    continue
                seen.add(key)
                sources.append(source)
        return sources

    payload = _serialize_agenda(settings, agenda, user)
    payload["messages"] = [{
        "message_id": str(item["message_id"]), "sender_principal": item["sender_principal"],
        "sender_name": names.get(str(item["sender_principal"]), str(item["sender_principal"])),
        "recipient_principal": item["recipient_principal"], "message_type": item["message_type"],
        "content": item["content"], "sources": item["sources"], "created_at": item["created_at"].isoformat(),
    } for item in messages]
    payload["context_capsules"] = [{
        "capsule_id": str(item["capsule_id"]), "from_principal": item["from_principal"],
        "to_principal": item["to_principal"], "state": item["state_at_handoff"],
        "summary": item["summary"], "version": item["version_number"], "created_at": item["created_at"].isoformat(),
        "sources": snapshot_sources(item["created_at"]),
    } for item in capsules]
    payload["versions"] = [{"version": item["version_number"], "draft_text": item["draft_text"], "created_by_principal": item["created_by_principal"], "created_at": item["created_at"].isoformat()} for item in versions]
    return payload


def add_agenda_message(settings: Settings, user: PortalUser, agenda_id: UUID, content: str, message_type: str, sources: list[dict[str, object]] | None = None) -> None:
    detail = agenda_detail(settings, user, agenda_id)
    if detail["is_read_only"]:
        raise HTTPException(status_code=409, detail="This agenda is view-only for your role.")
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"""INSERT INTO {settings.schema_name}.agenda_message
                (agenda_id, sender_principal, message_type, content, sources) VALUES (%s,%s,%s,%s,%s)""",
                (agenda_id, user.principal_id, message_type, content, Jsonb(sources or [])))
            cursor.execute(f"UPDATE {settings.schema_name}.agenda SET updated_at=now() WHERE agenda_id=%s", (agenda_id,))


def save_agenda_revision(settings: Settings, user: PortalUser, agenda_id: UUID, draft_text: str) -> dict[str, object]:
    """Version an official draft only while its authenticated owner holds it."""
    if not draft_text.strip():
        raise HTTPException(status_code=422, detail="An agenda draft cannot be empty.")
    schema = settings.schema_name
    with connect(settings.database_url.unicode_string(), row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {schema}.agenda WHERE agenda_id=%s FOR UPDATE", (agenda_id,))
            agenda = cursor.fetchone()
            if not agenda or user.principal_id not in {agenda["created_by_principal"], agenda["assigned_do_principal"], agenda["assigned_nodal_principal"], agenda["assigned_hod_principal"]}:
                raise HTTPException(status_code=404, detail="Agenda not found.")
            if agenda["current_owner_principal"] != user.principal_id or agenda["state"] in {"APPROVED", "REJECTED"}:
                raise HTTPException(status_code=409, detail="This agenda is view-only for your role.")
            next_version = int(agenda["editing_version"]) + 1
            cursor.execute(f"""INSERT INTO {schema}.agenda_version
                (agenda_id, version_number, draft_text, created_by_principal) VALUES (%s,%s,%s,%s)""",
                (agenda_id, next_version, draft_text.strip(), user.principal_id))
            cursor.execute(f"""UPDATE {schema}.agenda SET editing_version=%s, updated_at=now()
                WHERE agenda_id=%s RETURNING *""", (next_version, agenda_id))
            updated = cursor.fetchone()
            cursor.execute(f"""INSERT INTO {schema}.agenda_message
                (agenda_id, sender_principal, message_type, content) VALUES (%s,%s,'SYSTEM',%s)""",
                (agenda_id, user.principal_id, f"Official draft saved as version v{next_version}."))
    return _serialize_agenda(settings, updated, user)


def transition_agenda(settings: Settings, user: PortalUser, agenda_id: UUID, action: str, target_principal: str | None, note: str) -> TransitionResult:
    actor_role, _ = authority_identity(settings, user)
    schema = settings.schema_name
    rules = {
        "submit_to_nodal": ({"DO_DRAFT", "RETURNED_TO_DO"}, "DO", "SUBMITTED_TO_NO", "NO"),
        "return_to_do": ({"SUBMITTED_TO_NO", "SUBMITTED_TO_HO"}, "REVIEWER", "RETURNED_TO_DO", "DO"),
        "submit_to_hod": ({"SUBMITTED_TO_NO"}, "NO", "SUBMITTED_TO_HO", "HO"),
        "approve": ({"SUBMITTED_TO_HO"}, "HO", "APPROVED", "HO"),
        "reject": ({"SUBMITTED_TO_HO"}, "HO", "REJECTED", "HO"),
    }
    if action not in rules:
        raise HTTPException(status_code=400, detail="Unsupported agenda action.")
    allowed_states, required_role, new_state, target_role = rules[action]
    with connect(settings.database_url.unicode_string(), row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {schema}.agenda WHERE agenda_id=%s FOR UPDATE", (agenda_id,))
            agenda = cursor.fetchone()
            if not agenda or user.principal_id not in {agenda["created_by_principal"], agenda["assigned_do_principal"], agenda["assigned_nodal_principal"], agenda["assigned_hod_principal"]}:
                raise HTTPException(status_code=404, detail="Agenda not found.")
            if agenda["current_owner_principal"] != user.principal_id:
                raise HTTPException(status_code=409, detail="Only the active owner can perform this handoff.")
            role_ok = actor_role in {"NO", "HO"} if required_role == "REVIEWER" else actor_role == required_role
            if agenda["state"] not in allowed_states or not role_ok:
                raise HTTPException(status_code=409, detail="This action is not valid for the current agenda state and role.")
            previous_owner = str(agenda["current_owner_principal"])
            if action == "return_to_do":
                new_owner = str(agenda["assigned_do_principal"])
            elif action in {"approve", "reject"}:
                new_owner = user.principal_id
            else:
                if not target_principal:
                    raise HTTPException(status_code=422, detail=f"Select an active {ROLE_LABELS[target_role]}.")
                if not target_principal.startswith("authority:"):
                    raise HTTPException(status_code=422, detail="Invalid target officer.")
                try:
                    target_id = int(target_principal.split(":", 1)[1])
                except ValueError as exc:
                    raise HTTPException(status_code=422, detail="Invalid target officer.") from exc
                cursor.execute("""SELECT 1 FROM public.admin_users au JOIN public.admin_roles ar ON ar.admin_id=au.admin_id
                    WHERE au.admin_id=%s AND au.account_status_code='A' AND ar.is_active IS TRUE AND ar.role_id=%s""", (target_id, target_role))
                if not cursor.fetchone():
                    raise HTTPException(status_code=422, detail="The selected officer is not active in the required workflow role.")
                new_owner = target_principal
            assignment = ""
            if action == "submit_to_nodal":
                assignment = ", assigned_nodal_principal=%s"
            elif action == "submit_to_hod":
                assignment = ", assigned_hod_principal=%s"
            params: list[object] = [new_state, new_owner, target_role]
            if assignment:
                params.append(new_owner)
            params.append(agenda_id)
            finalized = ", finalized_at=now()" if new_state in {"APPROVED", "REJECTED"} else ""
            cursor.execute(f"""UPDATE {schema}.agenda SET state=%s, current_owner_principal=%s,
                current_owner_role=%s, updated_at=now(){assignment}{finalized} WHERE agenda_id=%s RETURNING *""", params)
            updated = cursor.fetchone()
            summary = note.strip() or f"Agenda moved from {agenda['state']} to {new_state}."
            cursor.execute(f"""INSERT INTO {schema}.context_capsule
                (agenda_id, from_principal, to_principal, state_at_handoff, summary, version_number)
                VALUES (%s,%s,%s,%s,%s,%s)""", (agenda_id, previous_owner, new_owner, new_state, summary, agenda["editing_version"]))
            cursor.execute(f"""INSERT INTO {schema}.agenda_message
                (agenda_id, sender_principal, recipient_principal, message_type, content)
                VALUES (%s,%s,%s,'HANDOFF',%s)""", (agenda_id, previous_owner, new_owner, summary))
    return TransitionResult(_serialize_agenda(settings, updated, user), previous_owner, action)
