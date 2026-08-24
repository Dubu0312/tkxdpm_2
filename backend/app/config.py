"""Application settings, loaded from environment variables / .env."""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "tkxdpm_2"
    environment: str = "development"
    debug: bool = True

    backend_host: str = "127.0.0.1"
    backend_port: int = 8001

    # SQLite by default; the file lives in ./data and is not version controlled.
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'app.db'}"

    # Frontend dev server origin, allowed through CORS.
    cors_origins: str = "http://localhost:5173"

    @field_validator("database_url")
    @classmethod
    def _absolutise_sqlite_path(cls, value: str) -> str:
        """Resolve relative SQLite paths against the project root, not the CWD."""
        prefix = "sqlite:///"
        if not value.startswith(prefix):
            return value
        raw = value[len(prefix):]
        if raw in ("", ":memory:") or raw.startswith("/"):
            return value
        return prefix + str((PROJECT_ROOT / raw).resolve())

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
