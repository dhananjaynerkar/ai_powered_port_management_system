from __future__ import annotations

import ipaddress
from typing import Literal
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit

from pydantic import AnyUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_ALLOWED_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
STRONG_DATABASE_SSLMODES = {"require", "verify-ca", "verify-full"}
PRIVILEGED_DATABASE_ROLES = {"postgres", "root", "admin", "sa"}


class Settings(BaseSettings):
    """Runtime settings with explicit local, internal, and production gates."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="PORTPROJECT_RAG_", extra="ignore")

    database_url: AnyUrl
    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)
    deployment_environment: Literal["local", "internal", "production"] = "local"
    allowed_origins: str = LOCAL_ALLOWED_ORIGINS
    public_base_url: AnyUrl | None = None
    schema_name: str = Field(default="rag", pattern=r"^[a-z_][a-z0-9_]*$")
    document_schema_name: str = Field(default="pms_doc", pattern=r"^[a-z_][a-z0-9_]*$")
    vector_schema_name: str = Field(default="pms_vector", pattern=r"^[a-z_][a-z0-9_]*$")
    embedding_endpoint: AnyUrl = "http://127.0.0.1:11434/api/embed"
    embedding_model: str = "bge-m3"
    embedding_dimensions: int = Field(default=1024, ge=1, le=16384)
    generation_endpoint: AnyUrl = "http://127.0.0.1:11434/api/chat"
    llm_primary_model: str = "qwen3.5:4b"
    llm_fallback_model: str = "qwen3.5:4b"
    llm_allow_fallback: bool = False
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_device: str = "cpu"
    reranker_use_fp16: bool = False
    reranker_local_files_only: bool = True
    reranker_max_length: int = Field(default=256, ge=64, le=2048)
    reranker_batch_size: int = Field(default=8, ge=1, le=64)
    batch_size: int = Field(default=16, ge=1, le=256)
    chunk_min_characters: int = Field(default=900, ge=200, le=10000)
    chunk_max_characters: int = Field(default=2200, ge=400, le=20000)
    retrieval_limit: int = Field(default=8, ge=1, le=100)
    retrieval_candidate_multiplier: int = Field(default=4, ge=1, le=50)
    rerank_candidate_count: int = Field(default=8, ge=1, le=100)
    candidate_pool_size: int = Field(default=12, ge=1, le=100)
    final_context_source_count: int = Field(default=4, ge=1, le=20)
    # The global four-source limit remains certified for multi-evidence
    # answers. Measured direct/table defaults narrow only simple shapes whose
    # reviewed evidence and citation replay remained complete.
    final_context_source_count_direct: int = Field(default=1, ge=1, le=20)
    final_context_source_count_table: int = Field(default=1, ge=1, le=20)
    rrf_k: int = Field(default=60, ge=1, le=1000)
    source_hint_boost: float = Field(default=0.01, ge=0, le=1)
    table_evidence_boost: float = Field(default=0.75, ge=0, le=2)
    parent_context_window: int = Field(default=1, ge=0, le=5)
    context_token_budget: int = Field(default=1800, ge=256, le=32000)
    context_token_budget_direct: int = Field(default=256, ge=256, le=32000)
    context_token_budget_list: int = Field(default=1400, ge=256, le=32000)
    context_token_budget_comparison: int = Field(default=2200, ge=256, le=32000)
    context_token_budget_table: int = Field(default=350, ge=256, le=32000)
    context_characters_per_token: int = Field(default=4, ge=1, le=16)
    output_token_budget: int = Field(default=350, ge=64, le=8192)
    output_token_budget_direct: int = Field(default=160, ge=64, le=8192)
    output_token_budget_list: int = Field(default=280, ge=64, le=8192)
    # Contracts below request short, source-attributed answers.  These limits
    # prevent a small local model from reproducing source tables or writing a
    # legal essay, while still leaving enough room for a grounded comparison.
    output_token_budget_comparison: int = Field(default=260, ge=64, le=8192)
    output_token_budget_table: int = Field(default=120, ge=64, le=8192)
    generation_temperature: float = Field(default=0.1, ge=0, le=2)
    generation_think: bool = False
    generation_compact_instructions: bool = False
    generation_keep_alive: str = Field(default="10m", min_length=1, max_length=24)
    generation_timeout_seconds: int = Field(default=180, ge=5, le=600)
    # Local CPU capacity controls.  The safe default is one active heavy RAG
    # pipeline and one bounded waiter; larger values require a measured,
    # deployment-specific capacity decision.
    heavy_rag_concurrency: int = Field(default=1, ge=1, le=2)
    heavy_rag_queue_capacity: int = Field(default=1, ge=0, le=4)
    heavy_rag_queue_timeout_seconds: int = Field(default=60, ge=1, le=600)
    citation_validation_retries: int = Field(default=1, ge=0, le=3)
    reranker_allow_degraded_mode: bool = True
    reranker_failure_cooldown_seconds: int = Field(default=300, ge=0, le=3600)
    query_max_characters: int = Field(default=3000, ge=100, le=20000)
    login_max_failed_attempts: int = Field(default=5, ge=1, le=100)
    login_rate_limit_window_seconds: int = Field(default=300, ge=1, le=86400)
    session_idle_timeout_seconds: int = Field(default=1800, ge=60, le=86400)
    session_absolute_timeout_seconds: int = Field(default=28800, ge=300, le=604800)
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_secure: bool = False
    allow_legacy_plaintext_passwords: bool = True
    database_role: str | None = Field(default=None, min_length=1, max_length=63, pattern=r"^[A-Za-z_][A-Za-z0-9_$-]*$")
    table_max_pages: int = Field(default=60, ge=0, le=1000)
    embedding_timeout_seconds: int = Field(default=45, ge=5, le=300)
    embedding_batch_size: int = Field(default=2, ge=1, le=32)

    @field_validator("allowed_origins")
    @classmethod
    def _validate_allowed_origins(cls, value: str) -> str:
        origins = [item.strip().rstrip("/") for item in value.split(",") if item.strip()]
        if not origins or "*" in origins:
            raise ValueError("allowed_origins must contain explicit origins and cannot use '*'")
        for origin in origins:
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"Invalid allowed origin: {origin}")
            if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
                raise ValueError(f"Allowed origins must not contain a path or query: {origin}")
        return ",".join(origins)

    @property
    def cors_origins(self) -> list[str]:
        return [item for item in self.allowed_origins.split(",") if item]

    @staticmethod
    def _private_or_loopback_host(host: str | None) -> bool:
        if not host:
            return False
        normalized = host.strip("[]").lower()
        if normalized in {"localhost", "ollama"} or normalized.endswith((".local", ".internal", ".svc")):
            return True
        try:
            address = ipaddress.ip_address(normalized)
        except ValueError:
            return False
        return address.is_loopback or address.is_private or address.is_link_local

    @model_validator(mode="after")
    def _validate_deployment_security_contract(self) -> "Settings":
        query_pairs = parse_qsl(self.database_url.query or "", keep_blank_values=True)
        if not any(key == "connect_timeout" for key, _value in query_pairs):
            query_pairs.append(("connect_timeout", str(self.database_connect_timeout_seconds)))
            self.database_url = AnyUrl.build(
                scheme=self.database_url.scheme,
                username=self.database_url.username,
                password=self.database_url.password,
                host=self.database_url.host or "",
                port=self.database_url.port,
                path=(self.database_url.path or "").lstrip("/"),
                query=urlencode(query_pairs),
                fragment=self.database_url.fragment,
            )
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("cookie_samesite=none requires cookie_secure=true")

        if self.deployment_environment == "local":
            return self

        if self.public_base_url is None or self.public_base_url.scheme != "https":
            raise ValueError("internal and production deployments require an HTTPS public_base_url")
        if not self.cookie_secure:
            raise ValueError("internal and production deployments require cookie_secure=true")
        if self.allowed_origins == LOCAL_ALLOWED_ORIGINS:
            raise ValueError("internal and production deployments require explicit allowed_origins")
        if any(urlsplit(origin).scheme != "https" for origin in self.cors_origins):
            raise ValueError("internal and production allowed_origins must use HTTPS")
        if self.allow_legacy_plaintext_passwords:
            raise ValueError("legacy plaintext password compatibility must be disabled outside local development")
        for endpoint in (self.embedding_endpoint, self.generation_endpoint):
            if not self._private_or_loopback_host(endpoint.host):
                raise ValueError("Ollama endpoints must resolve to loopback/private network hosts")

        if self.deployment_environment == "production":
            database_user = (self.database_url.username or "").lower()
            if not self.database_role or not database_user:
                raise ValueError("production requires database_role and a named database URL user")
            if database_user != self.database_role.lower() or database_user in PRIVILEGED_DATABASE_ROLES:
                raise ValueError("production database_role must match a non-privileged application database user")
            sslmode = parse_qs(self.database_url.query or "").get("sslmode", [None])[0]
            if sslmode not in STRONG_DATABASE_SSLMODES:
                raise ValueError("production database_url requires sslmode=require, verify-ca, or verify-full")
        return self
