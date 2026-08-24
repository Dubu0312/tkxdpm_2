"""Regressions found while reviewing the application as a whole (Round 9).

Each test here pins a bug that was live in the code, so it cannot come back.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import inspect

from app import google_calendar, notifications
from app.config import settings
from app.models import Schedule

SAIGON = "Asia/Ho_Chi_Minh"


def post(client, start, end, **extra):
    return client.post(
        "/api/schedules",
        json={"title": "Lịch", "start_time": start, "end_time": end, "timezone": SAIGON, **extra},
    )


# --------------------------------------------------------------------------
# Duration limits were compared on rounded minutes
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("end", "seconds"),
    [
        ("2026-06-01T09:14:31", 871),  # rounded up to 15 and slipped through
        ("2026-06-01T09:14:40", 880),
        ("2026-06-01T09:14:59", 899),
    ],
)
def test_a_schedule_seconds_under_the_minimum_is_rejected(client, end, seconds):
    response = post(client, "2026-06-01T09:00:00", end)
    assert response.status_code == 422, f"{seconds}s was accepted"
    assert response.json()["detail"]["code"] == "duration_out_of_range"


def test_a_schedule_seconds_over_the_maximum_is_rejected(client):
    response = post(client, "2026-07-01T09:00:00", "2026-07-08T09:00:30")
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "duration_out_of_range"


def test_the_reported_length_never_contradicts_the_bound_it_broke(client):
    """14m31s must not be reported as "15 minutes, below the minimum of 15"."""
    short = post(client, "2026-06-01T09:00:00", "2026-06-01T09:14:31").json()["detail"]
    assert short["duration_minutes"] < short["min_minutes"]

    long = post(client, "2026-07-01T09:00:00", "2026-07-08T09:00:30").json()["detail"]
    assert long["duration_minutes"] > long["max_minutes"]


def test_the_exact_boundaries_still_behave(client):
    assert post(client, "2026-06-02T09:00:00", "2026-06-02T09:15:00").status_code == 201
    assert post(client, "2026-06-03T09:00:00", "2026-06-10T09:00:00").status_code == 201


# --------------------------------------------------------------------------
# Bookkeeping writes bumped updated_at
# --------------------------------------------------------------------------


@pytest.fixture()
def calendar(monkeypatch):
    monkeypatch.setattr(settings, "google_calendar_mode", "memory")
    google_calendar.reset_client()
    yield google_calendar.get_client()
    google_calendar.reset_client()


def test_delivering_a_reminder_does_not_mark_a_schedule_as_edited(client, db):
    """A reminder going out is not a change to the schedule."""
    response = client.post(
        "/api/schedules",
        json={
            "title": "Có nhắc",
            "start_time": "2026-06-05T09:00:00",
            "end_time": "2026-06-05T10:00:00",
            "timezone": SAIGON,
            "reminder_minutes": 30,
        },
    )
    schedule_id = response.json()["id"]
    before = response.json()["updated_at"]

    with db() as session:
        schedule = session.get(Schedule, schedule_id)
        # 09:00 local is 02:00 UTC; stand just inside the reminder window.
        moment = datetime(2026, 6, 5, 1, 45)
        assert notifications.dispatch_due(session, moment) == [schedule]

    after = client.get(f"/api/schedules/{schedule_id}").json()
    assert after["notified_at"] is not None
    assert after["updated_at"] == before


def test_delivering_a_reminder_does_not_make_a_synced_schedule_look_stale(client, db, calendar):
    """The bug users would have seen: "cần đồng bộ lại" after a reminder fired."""
    created = client.post(
        "/api/schedules",
        json={
            "title": "Có nhắc và đã sync",
            "start_time": "2026-06-06T09:00:00",
            "end_time": "2026-06-06T10:00:00",
            "timezone": SAIGON,
            "reminder_minutes": 30,
        },
    ).json()
    assert client.post(f"/api/schedules/{created['id']}/google").status_code == 200

    with db() as session:
        notifications.dispatch_due(session, datetime(2026, 6, 6, 1, 45))

    after = client.get(f"/api/schedules/{created['id']}").json()
    assert after["notified_at"] is not None
    assert after["google_out_of_date"] is False


def test_a_real_edit_still_marks_the_schedule_as_changed(client, calendar):
    """The fix must not silence the genuine case."""
    created = client.post(
        "/api/schedules",
        json={
            "title": "Sẽ sửa",
            "start_time": "2026-06-07T09:00:00",
            "end_time": "2026-06-07T10:00:00",
            "timezone": SAIGON,
        },
    ).json()
    client.post(f"/api/schedules/{created['id']}/google")

    def explode(*args, **kwargs):
        raise google_calendar.CalendarUnavailable("network down")

    calendar.update = explode
    edited = client.put(
        f"/api/schedules/{created['id']}",
        json={
            "title": "Đã sửa",
            "start_time": "2026-06-07T09:00:00",
            "end_time": "2026-06-07T11:00:00",
            "timezone": SAIGON,
        },
    ).json()
    assert edited["updated_at"] != created["updated_at"]
    assert edited["google_out_of_date"] is True


# --------------------------------------------------------------------------
# A migrated database was missing the index create_all makes
# --------------------------------------------------------------------------


def test_a_freshly_created_database_has_the_start_time_index(db):
    with db() as session:
        indexes = {i["name"] for i in inspect(session.get_bind()).get_indexes("schedules")}
    assert "ix_schedules_start_time" in indexes


def test_the_migration_creates_the_same_indexes_as_create_all(tmp_path, monkeypatch):
    """A database upgraded column by column must end up with the same schema."""
    import sqlite3

    from sqlalchemy import create_engine

    import app.db as db_module
    import migrate

    legacy = tmp_path / "legacy.db"
    con = sqlite3.connect(legacy)
    con.execute(
        "CREATE TABLE schedules ("
        " id INTEGER NOT NULL, title VARCHAR(200) NOT NULL, description TEXT,"
        " location VARCHAR(200), start_time DATETIME NOT NULL, end_time DATETIME NOT NULL,"
        " created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL, PRIMARY KEY (id),"
        " CONSTRAINT ck_schedules_end_after_start CHECK (end_time > start_time))"
    )
    con.commit()
    con.close()

    engine = create_engine(f"sqlite:///{legacy}")
    monkeypatch.setattr(migrate, "engine", engine)
    migrate.migrate("Asia/Ho_Chi_Minh")

    fresh = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    db_module.Base.metadata.create_all(bind=fresh)

    def shape(target):
        inspector = inspect(target)
        return (
            {c["name"] for c in inspector.get_columns("schedules")},
            {i["name"] for i in inspector.get_indexes("schedules")},
        )

    assert shape(engine) == shape(fresh)
    engine.dispose()
    fresh.dispose()


def test_running_the_migration_twice_changes_nothing(tmp_path, monkeypatch):
    from sqlalchemy import create_engine

    import app.db as db_module
    import migrate

    engine = create_engine(f"sqlite:///{tmp_path / 'current.db'}")
    db_module.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(migrate, "engine", engine)

    assert migrate.migrate("Asia/Ho_Chi_Minh") == 0
    assert migrate.migrate("Asia/Ho_Chi_Minh") == 0
    engine.dispose()


# --------------------------------------------------------------------------
# Cross-feature behaviour confirmed during the review
# --------------------------------------------------------------------------


def test_a_rejected_edit_never_reaches_google(client, calendar):
    created = client.post(
        "/api/schedules",
        json={
            "title": "Nguyên bản",
            "start_time": "2026-06-08T09:00:00",
            "end_time": "2026-06-08T10:00:00",
            "timezone": SAIGON,
        },
    ).json()
    client.post(f"/api/schedules/{created['id']}/google")
    before = dict(next(iter(calendar.events.values())))

    refused = client.put(
        f"/api/schedules/{created['id']}",
        json={
            "title": "ĐỔI",
            "start_time": "2026-06-08T09:00:00",
            "end_time": "2026-06-08T09:05:00",  # too short
            "timezone": SAIGON,
        },
    )
    assert refused.status_code == 422
    assert next(iter(calendar.events.values())) == before


def test_deleting_a_schedule_clears_both_its_reminder_and_its_event(client, db, calendar):
    created = client.post(
        "/api/schedules",
        json={
            "title": "Xóa hết",
            "start_time": "2026-06-09T09:00:00",
            "end_time": "2026-06-09T10:00:00",
            "timezone": SAIGON,
            "reminder_minutes": 30,
        },
    ).json()
    client.post(f"/api/schedules/{created['id']}/google")

    assert client.delete(f"/api/schedules/{created['id']}").status_code == 204
    assert calendar.events == {}
    with db() as session:
        assert notifications.pending(session, datetime(2026, 6, 9, 0, 0)) == []


def test_a_schedule_created_in_the_past_can_still_be_synced(client, calendar):
    created = client.post(
        "/api/schedules",
        json={
            "title": "Quá khứ",
            "start_time": "2020-01-06T09:00:00",
            "end_time": "2020-01-06T10:00:00",
            "timezone": SAIGON,
        },
    ).json()
    assert client.post(f"/api/schedules/{created['id']}/google").status_code == 200


def test_a_reminder_further_back_than_now_is_due_immediately(client, db):
    """A schedule made shortly before it starts should still remind at once."""
    from app.models import utcnow

    start = utcnow() + timedelta(minutes=20)
    with db() as session:
        session.add(
            Schedule(
                title="Sắp bắt đầu",
                start_time=start,
                end_time=start + timedelta(hours=1),
                timezone=SAIGON,
                reminder_minutes=40320,
            )
        )
        session.commit()
    assert len(client.get("/api/notifications/due").json()) == 1
