"""Application settings, loaded from environment variables / .env."""

from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app import timezones

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

    # IANA timezone used when a request does not name one. Stored under the
    # canonical spelling, so configuring "Asia/Saigon" cannot make the default
    # look like a different zone from the one schedules are saved with.
    default_timezone: str = "Asia/Ho_Chi_Minh"

    # Background reminder dispatch. Set notifications_enabled=false to turn the
    # poller off (tests do this and dispatch explicitly instead).
    notifications_enabled: bool = True
    notification_poll_seconds: int = 30

    # How long a schedule is allowed to be, in minutes. These are the single
    # source of truth for the rule: the API enforces them and serves them to the
    # frontend, so no length is written down anywhere else.
    # Google Calendar integration. "disabled" keeps the app fully usable without
    # credentials; "memory" is a local stand-in for demos and tests; "google" is
    # the real API. Credential files live outside the repository.
    google_calendar_mode: Literal["disabled", "memory", "google"] = "disabled"
    google_calendar_id: str = "primary"
    google_credentials_file: str = "secrets/google_client_secret.json"
    google_token_file: str = "secrets/google_token.json"
    google_event_id_prefix: str = "tkdpm"

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

    @field_validator("default_timezone")
    @classmethod
    def _canonical_timezone(cls, value: str) -> str:
        timezones.resolve(value)
        return timezones.canonical(value)

    @property
    def google_credentials_path(self) -> Path:
        return self._resolve(self.google_credentials_file)

    @property
    def google_token_path(self) -> Path:
        return self._resolve(self.google_token_file)

    @staticmethod
    def _resolve(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else PROJECT_ROOT / path

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
