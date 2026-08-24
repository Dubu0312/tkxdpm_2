"""Test fixtures.

The whole suite runs against throwaway SQLite files: ``DATABASE_URL`` is pointed
at a temp directory *before* the app is imported, so nothing here ever touches
the developer's ``data/app.db``. On top of that each test gets its own database.
"""

import os
import tempfile
from pathlib import Path

_TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="tkxdpm2-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_DIR / 'app.db'}"
# Reminders are dispatched explicitly in tests, never by the background poller.
os.environ["NOTIFICATIONS_ENABLED"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db import Base, get_session  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def db(tmp_path):
    """A fresh database per test; yields its session factory."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield sessionmaker(bind=engine, autoflush=False, autocommit=False)
    engine.dispose()


@pytest.fixture()
def client(db):
    def override_get_session():
        session = db()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
