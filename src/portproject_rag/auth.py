"""Local, database-backed portal authentication.

Sessions are opaque, random tokens.  Only their SHA-256 digest is persisted,
so a database reader cannot reuse an active browser session.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import scrypt, sha256
from hmac import compare_digest
from secrets import token_urlsafe
from uuid import UUID

import bcrypt
from fastapi import Cookie, HTTPException, Request
from psycopg import connect

from .settings import Settings

SESSION_COOKIE = "portproject_session"


@dataclass(frozen=True)
class PortalUser:
    user_id: UUID | None
    principal_id: str
    username: str
    display_name: str
    role: str


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or token_urlsafe(18).encode("utf-8")
    digest = scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1).hex()
    return f"scrypt$16384$8$1${salt.hex()}${digest}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p)).hex()
        return compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def _schema(settings: Settings) -> str:
    return settings.schema_name


def bootstrap_status(settings: Settings) -> bool:
    """Portal identities are the existing Authority/Tenant database accounts."""
    return True


def create_initial_user(settings: Settings, username: str, display_name: str, password: str, role: str) -> PortalUser:
    if role not in {"authority", "tenant"}:
        raise ValueError("role must be authority or tenant")
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT EXISTS (SELECT 1 FROM {_schema(settings)}.app_user FOR UPDATE)")
            if cursor.fetchone()[0]:
                raise ValueError("Initial setup has already been completed")
            cursor.execute(
                f"""INSERT INTO {_schema(settings)}.app_user (username, display_name, role, password_hash)
                    VALUES (%s, %s, %s, %s)
                    RETURNING user_id, username, display_name, role""",
                (username.strip(), display_name.strip(), role, _hash_password(password)),
            )
            row = cursor.fetchone()
    return PortalUser(row[0], f"local:{row[0]}", *row[1:])


def _external_authority(settings: Settings, username: str, password: str) -> PortalUser | None:
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT au.admin_id, COALESCE(au.name, au.user_name), au.user_name,
                          au.demo_password, au.passwd, ar.role_id
                     FROM public.admin_users au
                     JOIN public.admin_roles ar ON ar.admin_id=au.admin_id AND ar.is_active IS TRUE
                    WHERE au.account_status_code='A'
                      AND (LOWER(au.user_name)=LOWER(%s)
                           OR LOWER(au.user_name)=LOWER(%s || '@mumbaiport.gov.in')
                           OR LOWER(SPLIT_PART(au.user_name, '@', 1))=LOWER(%s))
                    ORDER BY ar.admin_role_id LIMIT 1""",
                (username.strip(), username.strip(), username.strip()),
            )
            row = cursor.fetchone()
            if not row:
                return None
    role = str(row[5] or "").strip().upper()
    if role not in {"HO", "NO", "DO"}:
        return None
    plain_password, password_hash = row[3], row[4]
    verified = bool(plain_password and compare_digest(str(plain_password), password))
    if not verified and password_hash:
        try:
            verified = bcrypt.checkpw(password.encode("utf-8"), str(password_hash).removeprefix("{bcrypt}").encode("utf-8"))
        except ValueError:
            verified = False
    if not verified:
        return None
    return PortalUser(None, f"authority:{row[0]}", str(row[2]), str(row[1]), "authority")


def _external_tenant(settings: Settings, username: str, password: str) -> PortalUser | None:
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT applicant_id, COALESCE(ind_org_name, authorised_person_name, username), username, password
                     FROM public.applicant_registration
                    WHERE LOWER(username)=LOWER(%s) AND status IN ('A', 'APPROVED') LIMIT 1""",
                (username.strip(),),
            )
            row = cursor.fetchone()
    if not row or not row[3]:
        return None
    try:
        verified = bcrypt.checkpw(password.encode("utf-8"), str(row[3]).removeprefix("{bcrypt}").encode("utf-8"))
    except ValueError:
        verified = compare_digest(str(row[3]), password)
    return PortalUser(None, f"tenant:{row[0]}", str(row[2]), str(row[1]), "tenant") if verified else None


def authenticate(settings: Settings, username: str, password: str, role: str) -> PortalUser | None:
    if role == "authority":
        return _external_authority(settings, username, password)
    if role == "tenant":
        return _external_tenant(settings, username, password)
    return None


def create_session(settings: Settings, user: PortalUser) -> str:
    token = token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.session_absolute_timeout_seconds)
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""INSERT INTO {_schema(settings)}.user_session
                    (user_id, principal_id, username, display_name, role, token_hash, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (user.user_id, user.principal_id, user.username, user.display_name, user.role, sha256(token.encode()).hexdigest(), expires_at),
            )
    return token


def delete_session(settings: Settings, token: str | None) -> None:
    if not token:
        return
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {_schema(settings)}.user_session WHERE token_hash=%s", (sha256(token.encode()).hexdigest(),))


def current_user(request: Request, portproject_session: str | None = Cookie(default=None)) -> PortalUser:
    settings: Settings = request.app.state.settings
    if not portproject_session:
        raise HTTPException(status_code=401, detail="Sign in is required.")
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT s.user_id, s.principal_id, s.username, s.display_name, s.role
                    FROM {_schema(settings)}.user_session s
                    WHERE s.token_hash=%s AND s.expires_at > now()
                      AND s.last_accessed_at > now() - (%s * interval '1 second')""",
                (sha256(portproject_session.encode()).hexdigest(), settings.session_idle_timeout_seconds),
            )
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    f"UPDATE {_schema(settings)}.user_session SET last_accessed_at=now() WHERE token_hash=%s",
                    (sha256(portproject_session.encode()).hexdigest(),),
                )
    if not row:
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")
    return PortalUser(*row)


def _login_key(username: str, ip_address: str) -> str:
    return sha256(f"{username.strip().lower()}|{ip_address}".encode()).hexdigest()


def check_login_rate_limit(settings: Settings, username: str, ip_address: str) -> None:
    key_hash = _login_key(username, ip_address)
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT COUNT(*) FROM {_schema(settings)}.login_attempt
                    WHERE key_hash=%s AND succeeded IS FALSE
                      AND attempted_at > now() - (%s * interval '1 second')""",
                (key_hash, settings.login_rate_limit_window_seconds),
            )
            if cursor.fetchone()[0] >= settings.login_max_failed_attempts:
                raise HTTPException(status_code=429, detail="Too many failed login attempts. Please try again later.")


def record_login_attempt(settings: Settings, username: str, ip_address: str, succeeded: bool) -> None:
    key_hash = _login_key(username, ip_address)
    with connect(settings.database_url.unicode_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {_schema(settings)}.login_attempt (key_hash, succeeded) VALUES (%s, %s)",
                (key_hash, succeeded),
            )
            if succeeded:
                cursor.execute(
                    f"DELETE FROM {_schema(settings)}.login_attempt WHERE key_hash=%s AND succeeded IS FALSE",
                    (key_hash,),
                )
