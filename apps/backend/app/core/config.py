from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]
ENV_FILE = REPO_ROOT / ".env"


class Settings(BaseSettings):
    """Backend runtime settings loaded from the repo-root .env file."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    app_name: str = "x-clone backend"
    database_url: str = Field(
        default="postgresql+psycopg://app_user_placeholder:postgres_password_placeholder@localhost:5432/agentic_x_clone"
    )
    backend_cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    enable_api_docs: bool = True
    docs_url: str = "/docs"
    openapi_url: str = "/openapi.json"
    mutation_api_mode: str = "public"
    signup_max_dynamic_agents: int = Field(default=50, ge=1, le=1000)
    v2_cursor_signing_key: str = "cursor_signing_key_placeholder"
    v2_cursor_default_limit: int = Field(default=25, ge=1, le=100)
    v2_cursor_max_limit: int = Field(default=100, ge=1, le=100)
    v2_cursor_ttl_seconds: int = Field(default=86400, ge=1, le=604800)
    v2_client_request_id_max_length: int = Field(default=120, ge=1, le=120)
    v2_idempotency_ttl_seconds: int = Field(default=86400, ge=1, le=604800)

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list) and any(origin == "*" for origin in value):
            raise ValueError("Wildcard CORS origins are not allowed")
        return value

    @field_validator("mutation_api_mode")
    @classmethod
    def validate_mutation_api_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"public", "internal", "read_only"}:
            raise ValueError("mutation_api_mode must be public, internal, or read_only")
        return normalized

    @property
    def effective_docs_url(self) -> str | None:
        return self.docs_url if self.enable_api_docs else None

    @property
    def effective_openapi_url(self) -> str | None:
        return self.openapi_url if self.enable_api_docs else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
