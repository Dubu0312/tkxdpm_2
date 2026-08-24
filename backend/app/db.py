"""Database engine / session setup (SQLite via SQLAlchemy)."""

from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

if settings.database_url.startswith("sqlite:///"):
    db_path = Path(settings.database_url.removeprefix("sqlite:///"))
    db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class for ORM models."""


def init_db() -> None:
    """Create tables for any model registered on Base.

    The schema is small and there is no migration tool yet, so create_all is
    enough; swap in Alembic once schema changes need to be versioned.
    """
    from app import models  # noqa: F401  (import registers the models)

    Base.metadata.create_all(bind=engine)
    _assert_schema_current()


def _assert_schema_current() -> None:
    """Fail loudly on a database created before the current columns existed.

    ``create_all`` only creates missing tables, so an existing ``schedules``
    table keeps its old columns. Better a clear error than silent misreads.
    """
    columns = {column["name"] for column in inspect(engine).get_columns("schedules")}
    missing = {
        "timezone",
        "country",
        "reminder_minutes",
        "notified_at",
        "google_event_id",
        "google_synced_at",
    } - columns
    if missing:
        raise RuntimeError(
            f"The 'schedules' table is missing {sorted(missing)}. "
            "Run 'python migrate.py' from the backend directory to upgrade it."
        )


def get_session():
    """FastAPI dependency yielding a database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def check_connection() -> bool:
    """Return True if the database answers a trivial query."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
