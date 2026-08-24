"""Google Calendar integration.

These run against the in-memory stand-in (``GOOGLE_CALENDAR_MODE=memory``),
which enforces the same insert/update/delete rules as the API. The real client
is exercised by configuration, not by these tests — see the log for that caveat.
"""

from datetime import timedelta

import pytest

from app import google_calendar
from app.config import settings
from app.models import Schedule

SAIGON = "Asia/Ho_Chi_Minh"
TOKYO = "Asia/Tokyo"


@pytest.fixture()
def calendar(monkeypatch):
    """Switch the integration into its in-memory mode for one test."""
    monkeypatch.setattr(settings, "google_calendar_mode", "memory")
    google_calendar.reset_client()
    client = google_calendar.get_client()
    yield client
    google_calendar.reset_client()


def make(client, title="Họp nhóm", start="2026-09-01T09:00:00", end="2026-09-01T10:00:00",
         timezone=SAIGON, **extra):
    response = client.post(
        "/api/schedules",
        json={"title": title, "start_time": start, "end_time": end, "timezone": timezone, **extra},
    )
    assert response.status_code == 201, response.text
    return response.json()


def sync(client, schedule_id):
    return client.post(f"/api/schedules/{schedule_id}/google")


def only_event(store):
    assert len(store.events) == 1
    return next(iter(store.events.values()))


# --------------------------------------------------------------------------
# Running without credentials
# --------------------------------------------------------------------------


def test_the_app_works_with_the_integration_disabled(client):
    """The default checkout has no credentials and must stay fully usable."""
    assert settings.google_calendar_mode == "disabled"
    schedule = make(client)
    assert schedule["google_event_id"] is None
    assert schedule["google_out_of_date"] is False
    assert client.get("/api/schedules").status_code == 200
    assert client.delete(f"/api/schedules/{schedule['id']}").status_code == 204


def test_status_explains_that_it_is_not_configured(client):
    body = client.get("/api/config/google").json()
    assert body["mode"] == "disabled"
    assert body["enabled"] is False
    assert "disabled" in body["detail"]


def test_syncing_while_disabled_reports_503_rather_than_failing_obscurely(client):
    schedule = make(client)
    response = sync(client, schedule["id"])
    assert response.status_code == 503
    assert "GOOGLE_CALENDAR_MODE" in response.json()["detail"]


def test_status_reports_the_stand_in_mode_honestly(client, calendar):
    body = client.get("/api/config/google").json()
    assert body["mode"] == "memory"
    assert body["enabled"] is True
    assert "not in Google Calendar" in body["detail"]


# --------------------------------------------------------------------------
# Creating the event and linking it
# --------------------------------------------------------------------------


def test_syncing_creates_an_event_and_stores_the_link(client, calendar):
    schedule = make(client)
    body = sync(client, schedule["id"]).json()

    assert body["google_event_id"] == f"{settings.google_event_id_prefix}{schedule['id']}"
    assert body["google_calendar_id"] == settings.google_calendar_id
    assert body["google_synced_at"] is not None
    assert body["google_out_of_date"] is False
    assert only_event(calendar)["summary"] == "Họp nhóm"


def test_the_event_carries_the_optional_fields(client, calendar):
    schedule = make(
        client,
        description="Review sprint",
        location="Phòng A1",
        reminder_minutes=30,
    )
    sync(client, schedule["id"])
    event = only_event(calendar)
    assert event["description"] == "Review sprint"
    assert event["location"] == "Phòng A1"
    assert event["reminders"]["overrides"] == [{"method": "popup", "minutes": 30}]


def test_a_schedule_without_optional_fields_sends_no_empty_keys(client, calendar):
    sync(client, make(client)["id"])
    event = only_event(calendar)
    assert "description" not in event
    assert "location" not in event
    assert "reminders" not in event


# --------------------------------------------------------------------------
# Times keep their instant and their timezone
# --------------------------------------------------------------------------


def test_the_event_keeps_the_offset_and_the_zone_name(client, calendar):
    schedule = make(client, timezone=TOKYO)
    sync(client, schedule["id"])
    event = only_event(calendar)

    assert event["start"] == {"dateTime": "2026-09-01T09:00:00+09:00", "timeZone": TOKYO}
    assert event["end"] == {"dateTime": "2026-09-01T10:00:00+09:00", "timeZone": TOKYO}


def test_two_zones_with_the_same_wall_clock_send_different_instants(client, calendar):
    saigon = make(client, title="Sài Gòn", timezone=SAIGON)
    tokyo = make(
        client,
        title="Tokyo",
        start="2026-09-02T09:00:00",
        end="2026-09-02T10:00:00",
        timezone=TOKYO,
    )
    sync(client, saigon["id"])
    sync(client, tokyo["id"])

    starts = {event["summary"]: event["start"]["dateTime"] for event in calendar.events.values()}
    assert starts["Sài Gòn"].endswith("+07:00")
    assert starts["Tokyo"].endswith("+09:00")


def test_an_overnight_schedule_sends_both_dates(client, calendar):
    schedule = make(client, start="2026-09-01T23:30:00", end="2026-09-02T01:00:00")
    sync(client, schedule["id"])
    event = only_event(calendar)
    assert event["start"]["dateTime"].startswith("2026-09-01T23:30")
    assert event["end"]["dateTime"].startswith("2026-09-02T01:00")


def test_a_dst_schedule_sends_the_offset_in_force_at_each_end(client, calendar):
    schedule = make(
        client,
        start="2026-03-07T23:30:00",
        end="2026-03-08T03:30:00",
        timezone="America/New_York",
    )
    sync(client, schedule["id"])
    event = only_event(calendar)
    assert event["start"]["dateTime"].endswith("-05:00")  # EST
    assert event["end"]["dateTime"].endswith("-04:00")  # EDT


# --------------------------------------------------------------------------
# No duplicates
# --------------------------------------------------------------------------


def test_syncing_twice_updates_the_same_event(client, calendar):
    schedule = make(client)
    first = sync(client, schedule["id"]).json()
    second = sync(client, schedule["id"]).json()

    assert first["google_event_id"] == second["google_event_id"]
    assert len(calendar.events) == 1


def test_syncing_many_times_never_adds_an_event(client, calendar):
    schedule = make(client)
    for _ in range(5):
        assert sync(client, schedule["id"]).status_code == 200
    assert len(calendar.events) == 1


def test_a_lost_link_adopts_the_existing_event_instead_of_duplicating(client, calendar, db):
    """The event id is derived from the schedule, so a re-sync cannot fork."""
    schedule = make(client)
    sync(client, schedule["id"])

    with db() as session:  # pretend the link was lost locally
        session.get(Schedule, schedule["id"]).google_event_id = None
        session.commit()

    body = sync(client, schedule["id"]).json()
    assert len(calendar.events) == 1
    assert body["google_event_id"] == f"{settings.google_event_id_prefix}{schedule['id']}"


def test_an_event_deleted_on_google_is_recreated(client, calendar):
    schedule = make(client)
    event_id = sync(client, schedule["id"]).json()["google_event_id"]

    calendar.events.clear()  # someone deleted it in Google Calendar
    body = sync(client, schedule["id"]).json()

    assert body["google_event_id"] == event_id
    assert len(calendar.events) == 1


def test_two_schedules_get_two_events(client, calendar):
    sync(client, make(client, title="Một")["id"])
    sync(client, make(client, title="Hai", start="2026-09-03T09:00:00",
                      end="2026-09-03T10:00:00")["id"])
    assert len(calendar.events) == 2


def test_the_derived_event_id_must_be_valid_for_google(monkeypatch):
    """Google only accepts base32hex characters, so a bad prefix fails loudly."""
    schedule = Schedule(id=1)
    monkeypatch.setattr(settings, "google_event_id_prefix", "tkdpm")
    assert google_calendar.event_id_for(schedule) == "tkdpm1"

    monkeypatch.setattr(settings, "google_event_id_prefix", "TKXDPM")  # x is not allowed
    with pytest.raises(ValueError, match="valid Google event id"):
        google_calendar.event_id_for(schedule)


# --------------------------------------------------------------------------
# Keeping the event in step
# --------------------------------------------------------------------------


def put(client, schedule, **overrides):
    payload = {
        "title": schedule["title"],
        "start_time": schedule["start_time"],
        "end_time": schedule["end_time"],
        "timezone": schedule["timezone"],
    }
    payload.update(overrides)
    return client.put(f"/api/schedules/{schedule['id']}", json=payload)


def test_editing_a_linked_schedule_updates_the_event(client, calendar):
    schedule = make(client)
    sync(client, schedule["id"])

    body = put(client, schedule, title="Họp nhóm (đổi tên)").json()
    assert body["google_out_of_date"] is False
    assert only_event(calendar)["summary"] == "Họp nhóm (đổi tên)"
    assert len(calendar.events) == 1


def test_moving_a_linked_schedule_updates_the_times(client, calendar):
    schedule = make(client)
    sync(client, schedule["id"])

    put(client, schedule, start_time="2026-09-05T14:00:00", end_time="2026-09-05T15:00:00")
    event = only_event(calendar)
    assert event["start"]["dateTime"].startswith("2026-09-05T14:00")


def test_changing_the_timezone_updates_both_the_offset_and_the_zone(client, calendar):
    schedule = make(client)
    sync(client, schedule["id"])

    put(client, schedule, timezone=TOKYO)
    event = only_event(calendar)
    assert event["start"]["dateTime"].endswith("+09:00")
    assert event["start"]["timeZone"] == TOKYO


def test_editing_an_unlinked_schedule_creates_nothing(client, calendar):
    """Syncing is opt-in: editing must not silently push a schedule to Google."""
    schedule = make(client)
    put(client, schedule, title="Đổi tên")
    assert calendar.events == {}


def test_a_failed_push_marks_the_schedule_as_out_of_date(client, calendar, monkeypatch):
    schedule = make(client)
    sync(client, schedule["id"])

    def explode(*args, **kwargs):
        raise google_calendar.CalendarUnavailable("network down")

    monkeypatch.setattr(calendar, "update", explode)
    body = put(client, schedule, title="Sửa khi mạng hỏng").json()

    assert body["title"] == "Sửa khi mạng hỏng"  # the local edit stands
    assert body["google_out_of_date"] is True  # and the UI can offer to retry


# --------------------------------------------------------------------------
# Deleting and unlinking
# --------------------------------------------------------------------------


def test_deleting_a_schedule_deletes_its_event(client, calendar):
    schedule = make(client)
    sync(client, schedule["id"])

    assert client.delete(f"/api/schedules/{schedule['id']}").status_code == 204
    assert calendar.events == {}


def test_deleting_an_unlinked_schedule_touches_nothing(client, calendar):
    other = make(client, title="Có sync")
    sync(client, other["id"])
    plain = make(client, title="Không sync", start="2026-09-04T09:00:00",
                 end="2026-09-04T10:00:00")

    assert client.delete(f"/api/schedules/{plain['id']}").status_code == 204
    assert len(calendar.events) == 1


def test_deleting_still_works_when_google_cannot_be_reached(client, calendar, monkeypatch):
    """Someone must always be able to delete their own schedule."""
    schedule = make(client)
    sync(client, schedule["id"])

    def explode(*args, **kwargs):
        raise google_calendar.CalendarUnavailable("network down")

    monkeypatch.setattr(calendar, "delete", explode)
    assert client.delete(f"/api/schedules/{schedule['id']}").status_code == 204
    assert client.get("/api/schedules").json() == []


def test_deleting_when_the_event_is_already_gone_is_fine(client, calendar):
    schedule = make(client)
    sync(client, schedule["id"])
    calendar.events.clear()
    assert client.delete(f"/api/schedules/{schedule['id']}").status_code == 204


def test_unlinking_removes_the_event_but_keeps_the_schedule(client, calendar):
    schedule = make(client)
    sync(client, schedule["id"])

    body = client.delete(f"/api/schedules/{schedule['id']}/google").json()
    assert body["google_event_id"] is None
    assert body["google_synced_at"] is None
    assert calendar.events == {}
    assert client.get(f"/api/schedules/{schedule['id']}").status_code == 200


def test_unlinking_then_syncing_again_reuses_the_same_event_id(client, calendar):
    schedule = make(client)
    first = sync(client, schedule["id"]).json()["google_event_id"]
    client.delete(f"/api/schedules/{schedule['id']}/google")
    again = sync(client, schedule["id"]).json()["google_event_id"]

    assert again == first
    assert len(calendar.events) == 1


def test_syncing_a_missing_schedule_is_a_404(client, calendar):
    assert sync(client, 999).status_code == 404


# --------------------------------------------------------------------------
# Staleness indicator
# --------------------------------------------------------------------------


def test_a_never_synced_schedule_is_not_out_of_date(client, db):
    schedule = make(client)
    with db() as session:
        assert session.get(Schedule, schedule["id"]).google_out_of_date is False


def test_a_schedule_edited_after_its_last_push_is_out_of_date(client, db, calendar):
    schedule = make(client)
    sync(client, schedule["id"])
    with db() as session:
        row = session.get(Schedule, schedule["id"])
        row.google_synced_at = row.updated_at - timedelta(minutes=5)
        session.commit()
        assert row.google_out_of_date is True
