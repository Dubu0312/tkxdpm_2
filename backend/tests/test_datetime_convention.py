"""One rule for every datetime in a response.

Round 12, BUG-07. ``start_time``, ``end_time`` and ``notify_at`` came back in
the schedule's own timezone while ``notified_at`` came back in UTC. No instant
was wrong, but a client reading "the reminder fires at 16:30" next to "it was
sent at 09:31" was reading two clocks without being told, and the two fields are
one word apart. The convention is now: every datetime belonging to a schedule is
rendered in that schedule's timezone, offset always included.
"""

from datetime import UTC, datetime, timedelta

from app.models import Schedule, utcnow
from app.schemas import from_utc, resolve_timezone

SAIGON = "Asia/Ho_Chi_Minh"  # +07:00
TOKYO = "Asia/Tokyo"  # +09:00
OFFSETS = {SAIGON: "+07:00", TOKYO: "+09:00"}

#: Every datetime a schedule response can carry.
DATETIME_FIELDS = (
    "start_time",
    "end_time",
    "notify_at",
    "notified_at",
    "google_synced_at",
    "created_at",
    "updated_at",
)


def make_soon(client, minutes_ahead, reminder, timezone=SAIGON, title="Lịch"):
    """A schedule starting `minutes_ahead` from now, in `timezone`."""
    start = from_utc(utcnow() + timedelta(minutes=minutes_ahead), resolve_timezone(timezone))
    end = start + timedelta(hours=1)
    response = client.post(
        "/api/schedules",
        json={
            "title": title,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "timezone": timezone,
            "reminder_minutes": reminder,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def offsets(body: dict) -> set[str]:
    """The offset of every datetime present in a schedule body."""
    return {body[field][-6:] for field in DATETIME_FIELDS if body.get(field) is not None}


# --------------------------------------------------------------------------
# The rule
# --------------------------------------------------------------------------


def test_a_fresh_schedule_reports_every_datetime_in_its_own_zone(client):
    body = make_soon(client, 120, 30, TOKYO)
    assert offsets(body) == {"+09:00"}


def test_notified_at_uses_the_same_zone_as_notify_at(client):
    """The pair that gave the bug its name: "will fire at" and "was sent at"."""
    make_soon(client, 5, 30)  # its reminder was due 25 minutes ago
    client.post("/api/notifications/dispatch")
    body = client.get("/api/schedules").json()[0]

    assert body["notified_at"] is not None
    assert body["notified_at"].endswith(OFFSETS[SAIGON])
    assert body["notify_at"].endswith(OFFSETS[SAIGON])


def test_the_whole_record_stays_on_one_clock_after_a_dispatch(client):
    make_soon(client, 5, 30, TOKYO)
    client.post("/api/notifications/dispatch")
    assert offsets(client.get("/api/schedules").json()[0]) == {"+09:00"}


def test_each_schedule_uses_its_own_zone_not_a_shared_one(client):
    make_soon(client, 120, 30, SAIGON, title="Sài Gòn")
    make_soon(client, 300, 30, TOKYO, title="Tokyo")
    by_title = {item["title"]: item for item in client.get("/api/schedules").json()}
    assert offsets(by_title["Sài Gòn"]) == {"+07:00"}
    assert offsets(by_title["Tokyo"]) == {"+09:00"}


def test_no_datetime_is_rendered_as_bare_z(client):
    """"Z" is a zero offset spelled differently, and reads as a different zone."""
    make_soon(client, 5, 30, "UTC")
    client.post("/api/notifications/dispatch")
    body = client.get("/api/schedules").json()[0]
    for field in DATETIME_FIELDS:
        if body.get(field) is not None:
            assert body[field].endswith("+00:00"), field


# --------------------------------------------------------------------------
# Rendering changes the label, never the instant
# --------------------------------------------------------------------------


def test_notified_at_names_the_instant_that_was_stored(client, db):
    make_soon(client, 5, 30)
    client.post("/api/notifications/dispatch")
    body = client.get("/api/schedules").json()[0]

    with db() as session:
        stored = session.get(Schedule, body["id"]).notified_at
    reported = datetime.fromisoformat(body["notified_at"])
    assert reported.astimezone(UTC).replace(tzinfo=None) == stored


def test_created_and_updated_are_still_the_moment_the_server_acted(client):
    body = make_soon(client, 120, 30, TOKYO)
    created = datetime.fromisoformat(body["created_at"])
    assert created.utcoffset().total_seconds() == 9 * 3600
    assert abs((datetime.now(UTC) - created).total_seconds()) < 60


def test_google_synced_at_follows_the_same_rule(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "google_calendar_mode", "memory")
    created = make_soon(client, 120, 30, TOKYO)
    body = client.post(f"/api/schedules/{created['id']}/google").json()
    assert body["google_synced_at"].endswith("+09:00")
    assert offsets(body) == {"+09:00"}


# --------------------------------------------------------------------------
# The notifications endpoints report the same way
# --------------------------------------------------------------------------


def test_the_notification_view_uses_the_schedule_zone_throughout(client):
    make_soon(client, 120, 30, TOKYO)
    item = client.get("/api/notifications").json()[0]
    assert item["timezone"] == TOKYO
    assert item["notify_at"].endswith("+09:00")
    assert item["start_time"].endswith("+09:00")


def test_a_dispatched_notification_reports_notified_at_in_the_schedule_zone(client):
    make_soon(client, 5, 30, TOKYO)
    delivered = client.post("/api/notifications/dispatch").json()
    assert delivered[0]["notified_at"].endswith("+09:00")
    assert delivered[0]["notify_at"].endswith("+09:00")
