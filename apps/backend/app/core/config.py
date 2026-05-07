from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    backend_cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"]
    )
    enable_api_docs: bool = True
    docs_url: str = "/docs"
    openapi_url: str = "/openapi.json"
    signup_max_dynamic_agents: int = Field(default=50, ge=1, le=1000)

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def effective_docs_url(self) -> str | None:
        return self.docs_url if self.enable_api_docs else None

    @property
    def effective_openapi_url(self) -> str | None:
        return self.openapi_url if self.enable_api_docs else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
