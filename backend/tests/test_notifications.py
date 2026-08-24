"""Reminder notifications.

The moment a reminder fires is *derived* (`start_time - reminder_minutes`), so
these tests check that derivation, the pending/due windows, dispatch marking,
and what happens when a schedule is edited or deleted.
"""

from datetime import datetime, timedelta

import pytest

from app import notifications
from app.models import Schedule

SAIGON = "Asia/Ho_Chi_Minh"
TOKYO = "Asia/Tokyo"

# A fixed "now" in UTC for the module-level tests.
NOW = datetime(2026, 5, 10, 12, 0, 0)


def add(session, *, start, minutes=30, title="Lịch", timezone=SAIGON, notified_at=None, hours=1):
    schedule = Schedule(
        title=title,
        start_time=start,
        end_time=start + timedelta(hours=hours),
        timezone=timezone,
        reminder_minutes=minutes,
        notified_at=notified_at,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return schedule


# --------------------------------------------------------------------------
# Deriving the moment
# --------------------------------------------------------------------------


def test_notify_at_is_the_start_minus_the_lead_time(db):
    with db() as session:
        schedule = add(session, start=datetime(2026, 5, 10, 15, 0), minutes=30)
        assert schedule.notify_at == datetime(2026, 5, 10, 14, 30)


def test_no_reminder_means_no_moment(db):
    with db() as session:
        schedule = add(session, start=datetime(2026, 5, 10, 15, 0), minutes=None)
        assert schedule.notify_at is None


def test_a_long_lead_time_reaches_back_days(db):
    with db() as session:
        schedule = add(session, start=datetime(2026, 5, 10, 9, 0), minutes=2 * 24 * 60)
        assert schedule.notify_at == datetime(2026, 5, 8, 9, 0)


# --------------------------------------------------------------------------
# Pending and due windows
# --------------------------------------------------------------------------


def test_a_future_reminder_is_pending_but_not_due(db):
    with db() as session:
        add(session, start=NOW + timedelta(hours=2), minutes=30)  # fires in 90 minutes
        assert len(notifications.pending(session, NOW)) == 1
        assert notifications.due(session, NOW) == []


def test_a_reminder_whose_moment_has_arrived_is_due(db):
    with db() as session:
        add(session, start=NOW + timedelta(minutes=20), minutes=30)  # fired 10 minutes ago
        assert len(notifications.due(session, NOW)) == 1


def test_a_reminder_becomes_due_exactly_at_its_moment(db):
    with db() as session:
        add(session, start=NOW + timedelta(minutes=30), minutes=30)
        assert len(notifications.due(session, NOW)) == 1


def test_a_schedule_without_a_reminder_never_appears(db):
    with db() as session:
        add(session, start=NOW + timedelta(minutes=10), minutes=None)
        assert notifications.pending(session, NOW) == []
        assert notifications.due(session, NOW) == []


def test_a_reminder_for_a_schedule_that_already_started_drops_out(db):
    """Reminding someone about a meeting they are already in is not useful."""
    with db() as session:
        add(session, start=NOW - timedelta(minutes=5), minutes=30)
        assert notifications.pending(session, NOW) == []
        assert notifications.due(session, NOW) == []


def test_an_already_delivered_reminder_is_not_pending(db):
    with db() as session:
        add(session, start=NOW + timedelta(minutes=20), minutes=30, notified_at=NOW)
        assert notifications.pending(session, NOW) == []


def test_pending_is_ordered_by_start_time(db):
    with db() as session:
        add(session, start=NOW + timedelta(hours=3), title="Muộn")
        add(session, start=NOW + timedelta(hours=1), title="Sớm")
        assert [s.title for s in notifications.pending(session, NOW)] == ["Sớm", "Muộn"]


# --------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------


def test_dispatch_delivers_and_marks_the_reminder(db):
    with db() as session:
        schedule = add(session, start=NOW + timedelta(minutes=20), minutes=30)
        delivered = notifications.dispatch_due(session, NOW)
        assert [s.id for s in delivered] == [schedule.id]
        assert schedule.notified_at == NOW


def test_dispatch_does_not_send_the_same_reminder_twice(db):
    with db() as session:
        add(session, start=NOW + timedelta(minutes=20), minutes=30)
        assert len(notifications.dispatch_due(session, NOW)) == 1
        assert notifications.dispatch_due(session, NOW + timedelta(minutes=1)) == []


def test_dispatch_leaves_reminders_that_are_not_due_yet(db):
    with db() as session:
        schedule = add(session, start=NOW + timedelta(hours=5), minutes=30)
        assert notifications.dispatch_due(session, NOW) == []
        assert schedule.notified_at is None


def test_dispatch_logs_one_line_per_reminder(db, caplog):
    with db() as session:
        add(session, start=NOW + timedelta(minutes=20), minutes=30, title="Họp nhóm")
        with caplog.at_level("INFO", logger="app.notifications"):
            notifications.dispatch_due(session, NOW)
    assert "Họp nhóm" in caplog.text


# --------------------------------------------------------------------------
# Timezones — the moment is an instant, not a wall clock
# --------------------------------------------------------------------------


def test_the_same_lead_time_in_two_zones_fires_at_each_schedule_own_instant(db):
    with db() as session:
        saigon = add(session, start=datetime(2026, 5, 10, 2, 0), timezone=SAIGON)  # 09:00 local
        tokyo = add(session, start=datetime(2026, 5, 10, 0, 0), timezone=TOKYO)  # 09:00 local
        # Same local start time, different instants -> different reminder instants.
        assert saigon.notify_at == datetime(2026, 5, 10, 1, 30)
        assert tokyo.notify_at == datetime(2026, 5, 9, 23, 30)


def test_a_reminder_is_reported_in_the_schedule_timezone(client):
    response = client.post(
        "/api/schedules",
        json={
            "title": "Họp Tokyo",
            "start_time": "2026-05-10T09:00:00",
            "end_time": "2026-05-10T10:00:00",
            "timezone": TOKYO,
            "reminder_minutes": 30,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["reminder_minutes"] == 30
    assert body["notify_at"] == "2026-05-10T08:30:00+09:00"
    assert body["notified_at"] is None


def test_a_reminder_can_land_on_the_previous_local_day(client):
    """00:15 with a 30 minute lead fires at 23:45 the day before."""
    response = client.post(
        "/api/schedules",
        json={
            "title": "Ca đêm",
            "start_time": "2026-05-11T00:15:00",
            "end_time": "2026-05-11T01:15:00",
            "timezone": SAIGON,
            "reminder_minutes": 30,
        },
    )
    assert response.status_code == 201
    assert response.json()["notify_at"] == "2026-05-10T23:45:00+07:00"


def test_a_reminder_for_an_overnight_schedule_uses_its_start(client):
    response = client.post(
        "/api/schedules",
        json={
            "title": "Ca đêm dài",
            "start_time": "2026-05-10T23:30:00",
            "end_time": "2026-05-11T01:00:00",
            "timezone": SAIGON,
            "reminder_minutes": 60,
        },
    )
    assert response.status_code == 201
    assert response.json()["notify_at"] == "2026-05-10T22:30:00+07:00"


def test_a_reminder_across_a_dst_change_follows_the_real_instant(client):
    """New York springs forward at 02:00 on 8 March 2026."""
    response = client.post(
        "/api/schedules",
        json={
            "title": "Sau DST",
            "start_time": "2026-03-08T03:30:00",
            "end_time": "2026-03-08T04:30:00",
            "timezone": "America/New_York",
            "reminder_minutes": 60,
        },
    )
    assert response.status_code == 201
    # 03:30 EDT is 07:30 UTC; an hour earlier is 06:30 UTC, which is 01:30 EST.
    assert response.json()["notify_at"] == "2026-03-08T01:30:00-05:00"


# --------------------------------------------------------------------------
# Editing and deleting
# --------------------------------------------------------------------------


def put(client, schedule_id, **overrides):
    payload = {
        "title": "Lịch",
        "start_time": "2026-05-20T09:00:00",
        "end_time": "2026-05-20T10:00:00",
        "timezone": SAIGON,
        "reminder_minutes": 30,
    }
    payload.update(overrides)
    return client.put(f"/api/schedules/{schedule_id}", json=payload)


@pytest.fixture()
def sent(client, db):
    """A schedule whose reminder has already been delivered."""
    response = client.post(
        "/api/schedules",
        json={
            "title": "Lịch",
            "start_time": "2026-05-20T09:00:00",
            "end_time": "2026-05-20T10:00:00",
            "timezone": SAIGON,
            "reminder_minutes": 30,
        },
    )
    assert response.status_code == 201
    schedule_id = response.json()["id"]
    with db() as session:
        session.get(Schedule, schedule_id).notified_at = datetime(2026, 5, 20, 1, 30)
        session.commit()
    return schedule_id


def test_moving_the_schedule_re_arms_a_delivered_reminder(client, sent):
    response = put(client, sent, start_time="2026-05-21T09:00:00", end_time="2026-05-21T10:00:00")
    assert response.status_code == 200
    body = response.json()
    assert body["notified_at"] is None
    assert body["notify_at"] == "2026-05-21T08:30:00+07:00"


def test_changing_the_lead_time_re_arms_a_delivered_reminder(client, sent):
    body = put(client, sent, reminder_minutes=120).json()
    assert body["notified_at"] is None
    assert body["notify_at"] == "2026-05-20T07:00:00+07:00"


def test_editing_only_the_title_does_not_resend(client, sent):
    body = put(client, sent, title="Tên mới").json()
    assert body["title"] == "Tên mới"
    assert body["notified_at"] is not None


def test_changing_the_timezone_re_arms_because_the_instant_moves(client, sent):
    """Same wall clock in another zone is another instant, so the reminder moves."""
    body = put(client, sent, timezone=TOKYO).json()
    assert body["notified_at"] is None
    assert body["notify_at"] == "2026-05-20T08:30:00+09:00"


def test_removing_the_reminder_clears_the_moment(client, sent):
    body = put(client, sent, reminder_minutes=None).json()
    assert body["reminder_minutes"] is None
    assert body["notify_at"] is None


def test_deleting_the_schedule_removes_its_reminder(client, db):
    response = client.post(
        "/api/schedules",
        json={
            "title": "Sẽ xóa",
            "start_time": "2026-05-20T09:00:00",
            "end_time": "2026-05-20T10:00:00",
            "timezone": SAIGON,
            "reminder_minutes": 30,
        },
    )
    schedule_id = response.json()["id"]
    assert client.delete(f"/api/schedules/{schedule_id}").status_code == 204
    with db() as session:
        assert notifications.pending(session, datetime(2026, 5, 20, 0, 0)) == []


# --------------------------------------------------------------------------
# Validation and endpoints
# --------------------------------------------------------------------------


def test_a_schedule_has_no_reminder_by_default(client):
    body = client.post(
        "/api/schedules",
        json={
            "title": "Không nhắc",
            "start_time": "2026-05-20T09:00:00",
            "end_time": "2026-05-20T10:00:00",
            "timezone": SAIGON,
        },
    ).json()
    assert body["reminder_minutes"] is None
    assert body["notify_at"] is None


@pytest.mark.parametrize("minutes", [0, -5, 40321])
def test_an_out_of_range_lead_time_is_rejected(client, minutes):
    response = client.post(
        "/api/schedules",
        json={
            "title": "Sai",
            "start_time": "2026-05-20T09:00:00",
            "end_time": "2026-05-20T10:00:00",
            "timezone": SAIGON,
            "reminder_minutes": minutes,
        },
    )
    assert response.status_code == 422


def make_soon(client, minutes_ahead, reminder, title="Sắp tới"):
    """A schedule starting `minutes_ahead` from now, relative to real time."""
    from app.models import utcnow
    from app.schemas import from_utc, resolve_timezone

    tz = resolve_timezone(SAIGON)
    start = from_utc(utcnow() + timedelta(minutes=minutes_ahead), tz)
    end = start + timedelta(hours=1)
    return client.post(
        "/api/schedules",
        json={
            "title": title,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "timezone": SAIGON,
            "reminder_minutes": reminder,
        },
    )


def test_pending_endpoint_lists_reminders_that_can_still_fire(client):
    assert make_soon(client, 120, 30, title="Chưa tới").status_code == 201
    body = client.get("/api/notifications").json()
    assert len(body) == 1
    assert body[0]["title"] == "Chưa tới"
    assert body[0]["reminder_minutes"] == 30
    assert body[0]["notified_at"] is None


def test_due_endpoint_only_lists_reminders_whose_moment_arrived(client):
    make_soon(client, 120, 30, title="Chưa tới")
    make_soon(client, 5, 30, title="Đã tới")  # fires 25 minutes ago
    assert [item["title"] for item in client.get("/api/notifications/due").json()] == ["Đã tới"]


def test_dispatch_endpoint_sends_due_reminders_once(client):
    make_soon(client, 5, 30, title="Đã tới")
    delivered = client.post("/api/notifications/dispatch").json()
    assert [item["title"] for item in delivered] == ["Đã tới"]
    assert delivered[0]["notified_at"] is not None

    assert client.post("/api/notifications/dispatch").json() == []
    assert client.get("/api/notifications").json() == []


def test_dispatch_endpoint_leaves_future_reminders_alone(client):
    make_soon(client, 120, 30)
    assert client.post("/api/notifications/dispatch").json() == []
    assert len(client.get("/api/notifications").json()) == 1
