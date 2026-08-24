from __future__ import annotations

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings; values are loaded only from this package's .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="PORTPROJECT_RAG_", extra="ignore")

    database_url: AnyUrl
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
    reranker_max_length: int = Field(default=256, ge=64, le=2048)
    reranker_batch_size: int = Field(default=8, ge=1, le=64)
    batch_size: int = Field(default=16, ge=1, le=256)
    chunk_min_characters: int = Field(default=900, ge=200, le=10000)
    chunk_max_characters: int = Field(default=2200, ge=400, le=20000)
    retrieval_limit: int = Field(default=8, ge=1, le=100)
    retrieval_candidate_multiplier: int = Field(default=4, ge=1, le=50)
    rerank_candidate_count: int = Field(default=8, ge=1, le=100)
    rrf_k: int = Field(default=60, ge=1, le=1000)
    parent_context_window: int = Field(default=1, ge=0, le=5)
    context_token_budget: int = Field(default=1800, ge=256, le=32000)
    context_characters_per_token: int = Field(default=4, ge=1, le=16)
    output_token_budget: int = Field(default=350, ge=64, le=8192)
    generation_temperature: float = Field(default=0.1, ge=0, le=2)
    generation_think: bool = False
    generation_timeout_seconds: int = Field(default=180, ge=5, le=600)
    citation_validation_retries: int = Field(default=1, ge=0, le=3)
    query_max_characters: int = Field(default=3000, ge=100, le=20000)
    login_max_failed_attempts: int = Field(default=5, ge=1, le=100)
    login_rate_limit_window_seconds: int = Field(default=300, ge=1, le=86400)
    session_idle_timeout_seconds: int = Field(default=1800, ge=60, le=86400)
    session_absolute_timeout_seconds: int = Field(default=28800, ge=300, le=604800)
    cookie_secure: bool = False
    table_max_pages: int = Field(default=60, ge=0, le=1000)
    embedding_timeout_seconds: int = Field(default=45, ge=5, le=300)
    embedding_batch_size: int = Field(default=2, ge=1, le=32)
