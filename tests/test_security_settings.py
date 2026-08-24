from __future__ import annotations

import bcrypt
import pytest
from pydantic import ValidationError

from portproject_rag.api import _session_cookie_options
from portproject_rag.auth import _verify_external_password
from portproject_rag.settings import Settings


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "postgresql://local_user:placeholder@127.0.0.1:5432/portproject",
    }
    values.update(overrides)
    return Settings(**values)


def _production_values() -> dict[str, object]:
    return {
        "database_url": "postgresql://portproject_app:placeholder@10.0.0.10:5432/portproject?sslmode=require",
        "deployment_environment": "production",
        "allowed_origins": "https://portal.example.test",
        "public_base_url": "https://portal.example.test",
        "cookie_secure": True,
        "cookie_samesite": "lax",
        "allow_legacy_plaintext_passwords": False,
        "database_role": "portproject_app",
    }


def test_local_defaults_keep_loopback_development_contract() -> None:
    settings = _settings()

    assert settings.deployment_environment == "local"
    assert settings.cookie_secure is False
    assert settings.cookie_samesite == "lax"
    assert settings.allow_legacy_plaintext_passwords is True
    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_non_local_deployment_requires_https_and_secure_cookies() -> None:
    with pytest.raises(ValidationError, match="HTTPS public_base_url"):
        _settings(deployment_environment="internal")

    values = _production_values()
    values["cookie_secure"] = False
    with pytest.raises(ValidationError, match="cookie_secure=true"):
        _settings(**values)


def test_production_rejects_dev_origins_legacy_plaintext_and_weak_database_transport() -> None:
    values = _production_values()
    values["allowed_origins"] = "http://localhost:5173"
    with pytest.raises(ValidationError, match="HTTPS"):
        _settings(**values)

    values = _production_values()
    values["allow_legacy_plaintext_passwords"] = True
    with pytest.raises(ValidationError, match="legacy plaintext"):
        _settings(**values)

    values = _production_values()
    values["database_url"] = "postgresql://portproject_app:placeholder@10.0.0.10:5432/portproject"
    with pytest.raises(ValidationError, match="sslmode"):
        _settings(**values)


def test_production_requires_a_named_non_privileged_database_role() -> None:
    values = _production_values()
    values["database_role"] = "postgres"
    values["database_url"] = "postgresql://postgres:placeholder@10.0.0.10:5432/portproject?sslmode=require"

    with pytest.raises(ValidationError, match="non-privileged"):
        _settings(**values)


def test_production_contract_accepts_private_ollama_and_explicit_origins() -> None:
    settings = _settings(**_production_values())

    assert settings.deployment_environment == "production"
    assert settings.cors_origins == ["https://portal.example.test"]
    assert settings.cookie_secure is True


def test_legacy_plaintext_compatibility_is_explicit_and_bcrypt_still_works() -> None:
    local_settings = _settings()
    locked_settings = _settings(allow_legacy_plaintext_passwords=False)
    hashed = bcrypt.hashpw(b"source-password", bcrypt.gensalt()).decode("utf-8")

    assert _verify_external_password(local_settings, "source-password", "source-password", None) is True
    assert _verify_external_password(locked_settings, "source-password", "source-password", None) is False
    assert _verify_external_password(locked_settings, "source-password", None, hashed) is True


def test_session_cookie_options_are_http_only_and_environment_driven() -> None:
    local = _session_cookie_options(_settings())
    assert local == {
        "httponly": True,
        "samesite": "lax",
        "secure": False,
        "max_age": 28800,
        "path": "/",
    }

    production = _session_cookie_options(_settings(**_production_values()))
    assert production["httponly"] is True
    assert production["secure"] is True
    assert production["samesite"] == "lax"
