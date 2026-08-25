"""BUG-03: a reminder whose moment has passed sat as "not sent yet" forever.

A reminder is only useful before the schedule starts, so `pending()` skipped it
— correctly — but nothing ever said so, and the API kept reporting
`notified_at: null`, which the interface read as "still going to fire".

The fix names the four states a reminder can be in. Nothing is stored for it:
`missed` is derived from the schedule, so moving a schedule back into the future
arms its reminder again on its own.
"""

from datetime import datetime, timedelta

from app import notifications
from app.models import Schedule, reminder_status, utcnow
from app.schemas import from_utc, resolve_timezone

SAIGON = "Asia/Ho_Chi_Minh"
TZ = resolve_timezone(SAIGON)
NOW = datetime(2026, 5, 10, 12, 0, 0)


def add(session, *, start, minutes=30, notified_at=None, title="Lịch"):
    schedule = Schedule(
        title=title,
        start_time=start,
        end_time=start + timedelta(hours=1),
        timezone=SAIGON,
        reminder_minutes=minutes,
        notified_at=notified_at,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return schedule


def at(delta: timedelta) -> str:
    """A wall-clock time in Saigon, `delta` from now."""
    return from_utc(utcnow() + delta, TZ).isoformat()


def create(client, start, end=None, **extra):
    return client.post(
        "/api/schedules",
        json={
            "title": "Lịch",
            "start_time": start,
            "end_time": end or from_utc(
                datetime.fromisoformat(start).astimezone(TZ).replace(tzinfo=None)
                + timedelta(hours=1),
                TZ,
            ).isoformat(),
            "timezone": SAIGON,
            **extra,
        },
    )


# --------------------------------------------------------------------------
# The four states
# --------------------------------------------------------------------------


def test_no_reminder_reads_as_none(db):
    with db() as session:
        schedule = add(session, start=NOW + timedelta(hours=2), minutes=None)
        assert reminder_status(schedule, NOW) == "none"


def test_a_reminder_still_to_come_is_scheduled(db):
    with db() as session:
        assert reminder_status(add(session, start=NOW + timedelta(hours=2)), NOW) == "scheduled"


def test_a_delivered_reminder_is_sent(db):
    with db() as session:
        schedule = add(session, start=NOW + timedelta(hours=2), notified_at=NOW)
        assert reminder_status(schedule, NOW) == "sent"


def test_a_reminder_on_a_schedule_that_already_started_is_missed(db):
    with db() as session:
        assert reminder_status(add(session, start=NOW - timedelta(minutes=5)), NOW) == "missed"


def test_a_schedule_starting_exactly_now_has_missed_its_reminder(db):
    with db() as session:
        assert reminder_status(add(session, start=NOW), NOW) == "missed"


def test_a_delivered_reminder_stays_sent_once_the_schedule_is_over(db):
    """Having gone out is a fact; it is not undone by time passing."""
    with db() as session:
        schedule = add(
            session, start=NOW - timedelta(hours=3), notified_at=NOW - timedelta(hours=4)
        )
        assert reminder_status(schedule, NOW) == "sent"


# --------------------------------------------------------------------------
# The classification and the dispatch windows cannot disagree
# --------------------------------------------------------------------------


def test_only_scheduled_reminders_are_pending(db):
    with db() as session:
        add(session, start=NOW + timedelta(hours=2), title="Sẽ nhắc")
        add(session, start=NOW - timedelta(hours=2), title="Đã lỡ")
        add(session, start=NOW + timedelta(hours=3), notified_at=NOW, title="Đã gửi")
        add(session, start=NOW + timedelta(hours=4), minutes=None, title="Không nhắc")

        assert [s.title for s in notifications.pending(session, NOW)] == ["Sẽ nhắc"]


def test_a_missed_reminder_is_never_dispatched(client, db):
    """It must not fire late: the meeting it was about has already begun."""
    with db() as session:
        add(session, start=NOW - timedelta(minutes=5))
        assert notifications.dispatch_due(session, NOW) == []
        assert notifications.due(session, NOW) == []


# --------------------------------------------------------------------------
# Through the API
# --------------------------------------------------------------------------


def test_the_api_reports_a_past_schedule_reminder_as_missed(client):
    body = create(client, at(timedelta(days=-2)), reminder_minutes=30).json()
    assert body["reminder_status"] == "missed"
    assert body["notified_at"] is None
    assert body["notify_at"] is not None


def test_the_api_reports_a_future_reminder_as_scheduled(client):
    body = create(client, at(timedelta(hours=5)), reminder_minutes=30).json()
    assert body["reminder_status"] == "scheduled"


def test_the_api_reports_no_reminder_as_none(client):
    assert create(client, at(timedelta(hours=5))).json()["reminder_status"] == "none"


def test_the_api_reports_a_delivered_reminder_as_sent(client):
    created = create(client, at(timedelta(minutes=10)), reminder_minutes=30).json()
    delivered = client.post("/api/notifications/dispatch").json()
    assert [item["schedule_id"] for item in delivered] == [created["id"]]
    assert client.get(f"/api/schedules/{created['id']}").json()["reminder_status"] == "sent"


def test_a_missed_reminder_does_not_appear_in_the_pending_list(client):
    create(client, at(timedelta(days=-2)), reminder_minutes=30)
    assert client.get("/api/notifications").json() == []
    assert client.post("/api/notifications/dispatch").json() == []


# --------------------------------------------------------------------------
# Moving a schedule moves its reminder's fate with it
# --------------------------------------------------------------------------


def put(client, schedule_id, start, **extra):
    end = from_utc(
        datetime.fromisoformat(start).astimezone(TZ).replace(tzinfo=None) + timedelta(hours=1), TZ
    ).isoformat()
    return client.put(
        f"/api/schedules/{schedule_id}",
        json={"title": "Lịch", "start_time": start, "end_time": end, "timezone": SAIGON, **extra},
    )


def test_moving_a_schedule_into_the_past_makes_its_reminder_missed(client):
    created = create(client, at(timedelta(hours=5)), reminder_minutes=30).json()
    assert created["reminder_status"] == "scheduled"

    moved = put(client, created["id"], at(timedelta(days=-3)), reminder_minutes=30)
    assert moved.status_code == 200
    assert moved.json()["reminder_status"] == "missed"
    assert client.get("/api/notifications").json() == []


def test_moving_it_back_into_the_future_arms_the_reminder_again(client):
    """Nothing was stored for `missed`, so the state simply follows the times."""
    created = create(client, at(timedelta(days=-3)), reminder_minutes=30).json()
    assert created["reminder_status"] == "missed"

    moved = put(client, created["id"], at(timedelta(days=4)), reminder_minutes=30)
    assert moved.json()["reminder_status"] == "scheduled"
    assert len(client.get("/api/notifications").json()) == 1


def test_removing_the_reminder_from_a_past_schedule_clears_the_state(client):
    created = create(client, at(timedelta(days=-3)), reminder_minutes=30).json()
    body = put(client, created["id"], at(timedelta(days=-3))).json()
    assert body["reminder_minutes"] is None
    assert body["reminder_status"] == "none"


def test_adding_a_reminder_to_a_past_schedule_reports_it_as_missed(client):
    """Creating one is still allowed; it just says plainly that it will not fire."""
    created = create(client, at(timedelta(days=-3))).json()
    assert created["reminder_status"] == "none"

    body = put(client, created["id"], at(timedelta(days=-3)), reminder_minutes=30).json()
    assert body["reminder_status"] == "missed"
