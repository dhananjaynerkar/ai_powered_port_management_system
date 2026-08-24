from __future__ import annotations

from collections.abc import Sequence

from psycopg import connect, sql

from .settings import Settings


def migration_statements(schema_name: str, embedding_dimensions: int) -> Sequence[sql.Composable]:
    """Build migration statements with named identifier/value slots.

    `schema` is always an SQL identifier. `dimension` is always a numeric SQL
    literal inside `vector(...)`; separate named slots prevent positional swaps.
    """
    if embedding_dimensions < 1:
        raise ValueError("embedding_dimensions must be positive")
    schema = sql.Identifier(schema_name)
    dimension = sql.Literal(int(embedding_dimensions))
    statement = sql.SQL
    return (
        statement("CREATE SCHEMA IF NOT EXISTS {schema}").format(schema=schema),
        statement("""
            CREATE TABLE IF NOT EXISTS {schema}.document (
                document_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                source_path text NOT NULL UNIQUE,
                original_filename text NOT NULL,
                file_sha256 text NOT NULL UNIQUE,
                file_size_bytes bigint NOT NULL CHECK (file_size_bytes >= 0),
                page_count integer NOT NULL CHECK (page_count >= 0),
                classification text NOT NULL,
                extraction_strategy text NOT NULL,
                extraction_quality smallint NOT NULL CHECK (extraction_quality BETWEEN 0 AND 100),
                source_metadata jsonb NOT NULL DEFAULT '{{}}'::jsonb,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now()
            )
        """).format(schema=schema),
        statement("""
            CREATE TABLE IF NOT EXISTS {schema}.document_page (
                page_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                document_id uuid NOT NULL REFERENCES {schema}.document(document_id) ON DELETE CASCADE,
                page_number integer NOT NULL CHECK (page_number > 0),
                extracted_text text NOT NULL,
                extraction_method text NOT NULL,
                extraction_quality smallint NOT NULL CHECK (extraction_quality BETWEEN 0 AND 100),
                page_metadata jsonb NOT NULL DEFAULT '{{}}'::jsonb,
                UNIQUE(document_id, page_number)
            )
        """).format(schema=schema),
        statement("""
            CREATE TABLE IF NOT EXISTS {schema}.chunk (
                chunk_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                document_id uuid NOT NULL REFERENCES {schema}.document(document_id) ON DELETE CASCADE,
                page_id uuid NOT NULL REFERENCES {schema}.document_page(page_id) ON DELETE CASCADE,
                chunk_index integer NOT NULL CHECK (chunk_index >= 0),
                chunk_type text NOT NULL,
                chunk_text text NOT NULL,
                section_title text,
                clause_number text,
                token_estimate integer NOT NULL CHECK (token_estimate >= 0),
                acl_roles text[] NOT NULL DEFAULT ARRAY[]::text[],
                metadata jsonb NOT NULL DEFAULT '{{}}'::jsonb,
                search_vector tsvector GENERATED ALWAYS AS (to_tsvector('simple', chunk_text)) STORED,
                embedding vector({dimension}) NOT NULL,
                embedding_model text NOT NULL,
                embedding_created_at timestamptz NOT NULL DEFAULT now(),
                UNIQUE(document_id, chunk_index)
            )
        """).format(schema=schema, dimension=dimension),
        statement("CREATE INDEX IF NOT EXISTS document_page_document_idx ON {schema}.document_page(document_id, page_number)").format(schema=schema),
        statement("CREATE INDEX IF NOT EXISTS chunk_document_idx ON {schema}.chunk(document_id, chunk_index)").format(schema=schema),
        statement("CREATE INDEX IF NOT EXISTS chunk_search_idx ON {schema}.chunk USING gin(search_vector)").format(schema=schema),
        statement("CREATE INDEX IF NOT EXISTS chunk_acl_idx ON {schema}.chunk USING gin(acl_roles)").format(schema=schema),
        statement("CREATE INDEX IF NOT EXISTS chunk_embedding_hnsw_idx ON {schema}.chunk USING hnsw (embedding vector_cosine_ops)").format(schema=schema),
        statement("""
            CREATE TABLE IF NOT EXISTS {schema}.app_user (
                user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), username text NOT NULL UNIQUE,
                display_name text NOT NULL, role text NOT NULL CHECK (role IN ('authority','tenant')),
                password_hash text NOT NULL, is_active boolean NOT NULL DEFAULT true,
                created_at timestamptz NOT NULL DEFAULT now(), last_login_at timestamptz
            )
        """).format(schema=schema),
        statement("""
            CREATE TABLE IF NOT EXISTS {schema}.user_session (
                session_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES {schema}.app_user(user_id) ON DELETE CASCADE,
                token_hash text NOT NULL UNIQUE, created_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL
            )
        """).format(schema=schema),
        statement("CREATE INDEX IF NOT EXISTS user_session_expiry_idx ON {schema}.user_session(expires_at)").format(schema=schema),
        statement("ALTER TABLE {schema}.user_session ALTER COLUMN user_id DROP NOT NULL").format(schema=schema),
        statement("ALTER TABLE {schema}.user_session ADD COLUMN IF NOT EXISTS principal_id text").format(schema=schema),
        statement("ALTER TABLE {schema}.user_session ADD COLUMN IF NOT EXISTS username text").format(schema=schema),
        statement("ALTER TABLE {schema}.user_session ADD COLUMN IF NOT EXISTS display_name text").format(schema=schema),
        statement("ALTER TABLE {schema}.user_session ADD COLUMN IF NOT EXISTS role text").format(schema=schema),
        statement("ALTER TABLE {schema}.user_session ADD COLUMN IF NOT EXISTS last_accessed_at timestamptz NOT NULL DEFAULT now()").format(schema=schema),
        statement("CREATE INDEX IF NOT EXISTS user_session_principal_idx ON {schema}.user_session(principal_id)").format(schema=schema),
        statement("""
            CREATE TABLE IF NOT EXISTS {schema}.chat_session (
                chat_session_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES {schema}.app_user(user_id) ON DELETE CASCADE,
                title text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
            )
        """).format(schema=schema),
        statement("ALTER TABLE {schema}.chat_session ALTER COLUMN user_id DROP NOT NULL").format(schema=schema),
        statement("ALTER TABLE {schema}.chat_session ADD COLUMN IF NOT EXISTS principal_id text").format(schema=schema),
        statement("CREATE INDEX IF NOT EXISTS chat_session_principal_idx ON {schema}.chat_session(principal_id, updated_at DESC)").format(schema=schema),
        statement("""
            CREATE TABLE IF NOT EXISTS {schema}.workflow_draft (
                draft_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                chat_session_id uuid REFERENCES {schema}.chat_session(chat_session_id) ON DELETE SET NULL,
                principal_id text NOT NULL,
                title text NOT NULL,
                draft_text text NOT NULL,
                state text NOT NULL DEFAULT 'DRAFT' CHECK (state IN ('DRAFT', 'FORWARDED')),
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now()
            )
        """).format(schema=schema),
        statement("CREATE INDEX IF NOT EXISTS workflow_draft_principal_idx ON {schema}.workflow_draft(principal_id, updated_at DESC)").format(schema=schema),
        statement("""
            CREATE TABLE IF NOT EXISTS {schema}.chat_message (
                message_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), chat_session_id uuid NOT NULL REFERENCES {schema}.chat_session(chat_session_id) ON DELETE CASCADE,
                sender text NOT NULL CHECK (sender IN ('user','assistant')), content text NOT NULL,
                sources jsonb NOT NULL DEFAULT '[]'::jsonb, created_at timestamptz NOT NULL DEFAULT now()
            )
        """).format(schema=schema),
        statement("""
            CREATE TABLE IF NOT EXISTS {schema}.audit_event (
                event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES {schema}.app_user(user_id) ON DELETE SET NULL,
                event_type text NOT NULL, metadata jsonb NOT NULL DEFAULT '{{}}'::jsonb, created_at timestamptz NOT NULL DEFAULT now()
            )
        """).format(schema=schema),
        statement("ALTER TABLE {schema}.audit_event ADD COLUMN IF NOT EXISTS principal_id text").format(schema=schema),
        statement("""
            CREATE TABLE IF NOT EXISTS {schema}.login_attempt (
                attempt_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), key_hash text NOT NULL,
                succeeded boolean NOT NULL, attempted_at timestamptz NOT NULL DEFAULT now()
            )
        """).format(schema=schema),
        statement("CREATE INDEX IF NOT EXISTS login_attempt_window_idx ON {schema}.login_attempt(key_hash, attempted_at DESC)").format(schema=schema),
        statement("""
            CREATE TABLE IF NOT EXISTS {schema}.agenda (
                agenda_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                agenda_number bigint GENERATED BY DEFAULT AS IDENTITY UNIQUE,
                title text NOT NULL,
                source_chat_session_id uuid REFERENCES {schema}.chat_session(chat_session_id) ON DELETE SET NULL,
                created_by_principal text NOT NULL,
                assigned_do_principal text NOT NULL,
                assigned_nodal_principal text,
                assigned_hod_principal text,
                current_owner_principal text NOT NULL,
                current_owner_role text NOT NULL CHECK (current_owner_role IN ('DO','NO','HO')),
                state text NOT NULL DEFAULT 'DO_DRAFT' CHECK (state IN (
                    'DO_DRAFT','SUBMITTED_TO_NO','RETURNED_TO_DO','SUBMITTED_TO_HO','APPROVED','REJECTED'
                )),
                editing_version integer NOT NULL DEFAULT 1 CHECK (editing_version > 0),
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                finalized_at timestamptz
            )
        """).format(schema=schema),
        statement("CREATE INDEX IF NOT EXISTS agenda_participants_idx ON {schema}.agenda(created_by_principal, assigned_do_principal, assigned_nodal_principal, assigned_hod_principal, updated_at DESC)").format(schema=schema),
        statement("""
            CREATE TABLE IF NOT EXISTS {schema}.agenda_version (
                version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                agenda_id uuid NOT NULL REFERENCES {schema}.agenda(agenda_id) ON DELETE CASCADE,
                version_number integer NOT NULL,
                draft_text text NOT NULL,
                created_by_principal text NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                UNIQUE(agenda_id, version_number)
            )
        """).format(schema=schema),
        statement("""
            CREATE TABLE IF NOT EXISTS {schema}.agenda_message (
                message_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                agenda_id uuid NOT NULL REFERENCES {schema}.agenda(agenda_id) ON DELETE CASCADE,
                sender_principal text NOT NULL,
                recipient_principal text,
                message_type text NOT NULL CHECK (message_type IN ('OFFICER','AI','HANDOFF','SYSTEM')),
                content text NOT NULL,
                sources jsonb NOT NULL DEFAULT '[]'::jsonb,
                created_at timestamptz NOT NULL DEFAULT now()
            )
        """).format(schema=schema),
        statement("CREATE INDEX IF NOT EXISTS agenda_message_thread_idx ON {schema}.agenda_message(agenda_id, created_at, message_id)").format(schema=schema),
        statement("""
            CREATE TABLE IF NOT EXISTS {schema}.context_capsule (
                capsule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                agenda_id uuid NOT NULL REFERENCES {schema}.agenda(agenda_id) ON DELETE CASCADE,
                from_principal text NOT NULL,
                to_principal text NOT NULL,
                state_at_handoff text NOT NULL,
                summary text NOT NULL,
                version_number integer NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now()
            )
        """).format(schema=schema),
        statement("CREATE INDEX IF NOT EXISTS context_capsule_agenda_idx ON {schema}.context_capsule(agenda_id, created_at)").format(schema=schema),
    )


def migrate(settings: Settings) -> None:
    """Create only the configured schema's idempotent pgvector objects."""
    with connect(settings.database_url.unicode_string(), autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            for statement in migration_statements(settings.schema_name, settings.embedding_dimensions):
                cursor.execute(statement)
            source = sql.Identifier(settings.schema_name)
            document_schema = sql.Identifier(settings.document_schema_name)
            vector_schema = sql.Identifier(settings.vector_schema_name)
            cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(document_schema))
            cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(vector_schema))
            cursor.execute(sql.SQL("""CREATE OR REPLACE VIEW {}.document_record AS
                SELECT document_id, source_path, original_filename, file_sha256, file_size_bytes,
                       page_count, classification, extraction_strategy, extraction_quality,
                       source_metadata, created_at, updated_at
                FROM {}.document""").format(document_schema, source))
            cursor.execute(sql.SQL("""CREATE OR REPLACE VIEW {}.document_chunk AS
                SELECT c.chunk_id, c.document_id, c.page_id, c.chunk_index, c.chunk_type,
                       c.chunk_text, c.section_title, c.clause_number, c.token_estimate,
                       c.acl_roles, c.metadata, c.search_vector, p.page_number
                FROM {}.chunk c JOIN {}.document_page p ON p.page_id=c.page_id""").format(vector_schema, source, source))
            cursor.execute(sql.SQL("""CREATE OR REPLACE VIEW {}.chunk_embedding AS
                SELECT chunk_id, embedding, embedding_model, embedding_created_at FROM {}.chunk""").format(vector_schema, source))
            cursor.execute(sql.SQL("""CREATE OR REPLACE VIEW {}.chunk_acl AS
                SELECT chunk_id, acl_roles FROM {}.chunk""").format(vector_schema, source))
