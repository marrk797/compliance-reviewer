"""Centralised application settings.

All secrets and tunables live in environment variables. ``Settings`` exposes a
single, validated source of truth. Never log raw values from this object.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Database (SQLite + sqlite-vec) ---
    database_path: Path = Field(default=Path("./data/data.sqlite"), alias="DATABASE_PATH")

    # --- Auth ---
    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expires_minutes: int = Field(default=720, alias="JWT_EXPIRES_MINUTES")

    # --- LLM ---
    # Default to Groq because it offers a free, no-credit-card key.
    llm_provider: Literal["groq", "openai", "anthropic"] = Field(
        default="groq", alias="LLM_PROVIDER"
    )
    llm_model: str = Field(default="llama-3.3-70b-versatile", alias="LLM_MODEL")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    # --- Embeddings (local, no key) ---
    embedding_provider: Literal["fastembed", "openai"] = Field(
        default="fastembed", alias="EMBEDDING_PROVIDER"
    )
    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5", alias="EMBEDDING_MODEL"
    )
    embedding_dim: int = Field(default=384, alias="EMBEDDING_DIM")

    # --- Privacy / security ---
    delete_source_files_after_processing: bool = Field(
        default=True, alias="DELETE_SOURCE_FILES_AFTER_PROCESSING"
    )
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, alias="MAX_UPLOAD_BYTES")
    allowed_upload_extensions: str = Field(
        default="pdf,docx,txt", alias="ALLOWED_UPLOAD_EXTENSIONS"
    )
    storage_dir: Path = Field(default=Path("./storage"), alias="STORAGE_DIR")
    tmp_dir: Path = Field(default=Path("./tmp"), alias="TMP_DIR")

    # --- Retrieval ---
    chunk_token_size: int = Field(default=500, alias="CHUNK_TOKEN_SIZE")
    chunk_token_overlap: int = Field(default=50, alias="CHUNK_TOKEN_OVERLAP")
    retrieval_top_k: int = Field(default=6, alias="RETRIEVAL_TOP_K")

    # --- App ---
    app_env: Literal["development", "staging", "production", "test"] = Field(
        default="development", alias="APP_ENV"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    @field_validator("storage_dir", "tmp_dir")
    @classmethod
    def _ensure_dir(cls, value: Path) -> Path:
        value.mkdir(parents=True, exist_ok=True)
        return value

    @field_validator("database_path")
    @classmethod
    def _ensure_db_parent(cls, value: Path) -> Path:
        value.parent.mkdir(parents=True, exist_ok=True)
        return value

    @property
    def allowed_extensions_set(self) -> set[str]:
        return {ext.strip().lower().lstrip(".") for ext in self.allowed_upload_extensions.split(",") if ext.strip()}

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
