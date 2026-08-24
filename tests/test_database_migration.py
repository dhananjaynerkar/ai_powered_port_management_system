from portproject_rag.database import migration_statements


def _render(schema: str, dimension: int) -> str:
    return "\n".join(statement.as_string(None) for statement in migration_statements(schema, dimension))


def test_schema_identifier_never_uses_embedding_dimension() -> None:
    rendered = _render("rag", 1024)

    assert '"rag".chunk' in rendered
    assert "embedding vector(1024)" in rendered
    assert "1024.chunk" not in rendered


def test_changing_dimension_does_not_change_schema_identifier() -> None:
    rendered = _render("rag", 768)

    assert '"rag".chunk' in rendered
    assert "embedding vector(768)" in rendered
    assert "768.chunk" not in rendered


def test_workflow_drafts_are_principal_scoped() -> None:
    rendered = _render("rag", 1024)

    assert 'CREATE TABLE IF NOT EXISTS "rag".workflow_draft' in rendered
    assert "principal_id text NOT NULL" in rendered
    assert 'workflow_draft_principal_idx ON "rag".workflow_draft(principal_id, updated_at DESC)' in rendered


def test_official_agenda_has_owner_state_versions_and_context_capsules() -> None:
    rendered = _render("rag", 1024)

    assert 'CREATE TABLE IF NOT EXISTS "rag".agenda' in rendered
    assert "current_owner_principal text NOT NULL" in rendered
    assert "assigned_nodal_principal text" in rendered
    assert 'CREATE TABLE IF NOT EXISTS "rag".agenda_version' in rendered
    assert 'CREATE TABLE IF NOT EXISTS "rag".context_capsule' in rendered
