"""Application settings, loaded from environment variables / .env."""

from pathlib import Path

from pydantic import field_validator, model_validator
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

    # IANA timezone used when a request does not name one.
    default_timezone: str = "Asia/Ho_Chi_Minh"

    # Background reminder dispatch. Set notifications_enabled=false to turn the
    # poller off (tests do this and dispatch explicitly instead).
    notifications_enabled: bool = True
    notification_poll_seconds: int = 30

    # How long a schedule is allowed to be, in minutes. These are the single
    # source of truth for the rule: the API enforces them and serves them to the
    # frontend, so no length is written down anywhere else.
    min_duration_minutes: int = 15
    max_duration_minutes: int = 7 * 24 * 60  # one week

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

    @model_validator(mode="after")
    def _sane_duration_limits(self):
        if self.min_duration_minutes < 1:
            raise ValueError("min_duration_minutes must be at least 1")
        if self.max_duration_minutes < self.min_duration_minutes:
            raise ValueError("max_duration_minutes must not be below min_duration_minutes")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
