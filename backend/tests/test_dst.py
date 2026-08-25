"""Daylight saving: skipped wall-clock times, and schedules that cross a change.

Round 12, BUG-05. Asking for 02:30 on the morning the clocks go forward is
asking for a time that does not happen. Python answers anyway — it lands on
03:30 — so the schedule quietly started an hour later than the user typed and
lasted an hour less than they meant. These tests pin the refusal, and pin that
the *valid* cases around it still work, because the fix would be worthless if it
also blocked a schedule that simply runs through the change.
"""

from datetime import datetime

from sqlalchemy import select

from app.models import Schedule

NEW_YORK = "America/New_York"  # clocks go forward 2026-03-08 02:00 -> 03:00
LONDON = "Europe/London"  # 2026-03-29 01:00 -> 02:00
SYDNEY = "Australia/Sydney"  # 2026-10-04 02:00 -> 03:00 (southern hemisphere)
TOKYO = "Asia/Tokyo"  # no DST at all


def post(client, start, end, timezone=NEW_YORK, title="Lịch", **extra):
    return client.post(
        "/api/schedules",
        json={
            "title": title,
            "start_time": start,
            "end_time": end,
            "timezone": timezone,
            **extra,
        },
    )


def create(client, start, end, timezone=NEW_YORK, title="Lịch", **extra):
    response = post(client, start, end, timezone, title, **extra)
    assert response.status_code == 201, response.text
    return response.json()


def refusal(response) -> dict:
    """The single validation item in a 422 body."""
    detail = response.json()["detail"]
    assert isinstance(detail, list) and len(detail) == 1, detail
    return detail[0]


# --------------------------------------------------------------------------
# A wall-clock time inside the jump is refused, not moved
# --------------------------------------------------------------------------


def test_nonexistent_start_time_is_refused(client):
    response = post(client, "2026-03-08T02:30:00", "2026-03-08T03:30:00")
    assert response.status_code == 422, response.text
    item = refusal(response)
    assert item["type"] == "nonexistent_local_time"
    assert item["loc"] == ["body", "start_time"]


def test_the_refusal_says_what_is_wrong_and_what_to_pick(client):
    item = refusal(post(client, "2026-03-08T02:30:00", "2026-03-08T03:30:00"))
    ctx = item["ctx"]
    assert ctx["timezone"] == NEW_YORK
    assert ctx["local_time"] == "2026-03-08T02:30:00"
    assert ctx["gap_minutes"] == 60
    assert ctx["next_valid"] == "2026-03-08T03:30:00"
    assert "does not exist" in item["msg"]


def test_nonexistent_end_time_is_refused_too(client):
    response = post(client, "2026-03-08T01:00:00", "2026-03-08T02:30:00")
    assert response.status_code == 422, response.text
    assert refusal(response)["loc"] == ["body", "end_time"]


def test_nothing_is_stored_when_the_time_does_not_exist(client, db):
    post(client, "2026-03-08T02:30:00", "2026-03-08T03:30:00")
    with db() as session:
        assert session.scalars(select(Schedule)).all() == []


def test_the_time_is_not_silently_shifted_to_the_next_valid_one(client, db):
    """The old behaviour: 02:30 was accepted and stored as 03:30."""
    assert post(client, "2026-03-08T02:30:00", "2026-03-08T04:00:00").status_code == 422
    create(client, "2026-03-08T03:30:00", "2026-03-08T04:00:00", title="Bản thật")
    with db() as session:
        rows = session.scalars(select(Schedule)).all()
    assert [row.title for row in rows] == ["Bản thật"]


def test_the_first_and_last_skipped_minute_are_refused(client):
    # The jump is [02:00, 03:00): 02:00 itself never happens, 03:00 does.
    assert post(client, "2026-03-08T02:00:00", "2026-03-08T04:00:00").status_code == 422
    assert post(client, "2026-03-08T02:59:00", "2026-03-08T04:00:00").status_code == 422
    assert post(client, "2026-03-08T03:00:00", "2026-03-08T04:00:00").status_code == 201


def test_the_rule_is_not_specific_to_one_zone(client):
    assert post(client, "2026-03-29T01:30:00", "2026-03-29T03:00:00", LONDON).status_code == 422
    assert post(client, "2026-10-04T02:30:00", "2026-10-04T04:00:00", SYDNEY).status_code == 422


def test_the_same_wall_clock_is_fine_in_a_zone_without_the_jump(client):
    """02:30 on 8 March is an ordinary time in Tokyo; only New York skips it."""
    body = create(client, "2026-03-08T02:30:00", "2026-03-08T03:30:00", TOKYO)
    assert body["start_time"] == "2026-03-08T02:30:00+09:00"


def test_editing_into_a_nonexistent_time_is_refused_and_changes_nothing(client):
    created = create(client, "2026-03-08T04:00:00", "2026-03-08T05:00:00")
    response = client.put(
        f"/api/schedules/{created['id']}",
        json={
            "title": "Đổi giờ",
            "start_time": "2026-03-08T02:30:00",
            "end_time": "2026-03-08T05:00:00",
            "timezone": NEW_YORK,
        },
    )
    assert response.status_code == 422, response.text
    assert refusal(response)["type"] == "nonexistent_local_time"
    assert client.get(f"/api/schedules/{created['id']}").json() == created


def test_an_explicit_offset_is_never_a_nonexistent_time(client):
    """An offset already names an instant, so there is nothing to resolve."""
    # 02:30-05:00 is 07:30 UTC, a real instant; New York calls it 03:30 EDT.
    body = create(client, "2026-03-08T02:30:00-05:00", "2026-03-08T04:30:00-04:00")
    assert body["start_time"] == "2026-03-08T03:30:00-04:00"


# --------------------------------------------------------------------------
# Schedules that legitimately cross a daylight-saving change
# --------------------------------------------------------------------------


def test_a_schedule_spanning_the_forward_jump_is_accepted(client, db):
    body = create(client, "2026-03-07T23:00:00", "2026-03-08T04:00:00")
    assert body["start_time"] == "2026-03-07T23:00:00-05:00"
    assert body["end_time"] == "2026-03-08T04:00:00-04:00"
    with db() as session:
        row = session.scalars(select(Schedule)).one()
    # Five hours on the wall clock, four hours of real time.
    assert row.start_time == datetime(2026, 3, 8, 4, 0)
    assert row.end_time == datetime(2026, 3, 8, 8, 0)


def test_a_schedule_spanning_the_backward_jump_is_accepted(client, db):
    body = create(client, "2026-10-31T23:00:00", "2026-11-01T03:00:00")
    assert body["start_time"] == "2026-10-31T23:00:00-04:00"
    assert body["end_time"] == "2026-11-01T03:00:00-05:00"
    with db() as session:
        row = session.scalars(select(Schedule)).one()
    # Four hours on the wall clock, five hours of real time.
    assert (row.end_time - row.start_time).total_seconds() == 5 * 3600


def test_duration_limits_measure_real_time_not_wall_clock(client):
    """01:50 to 03:00 reads as 70 minutes but really lasts 10 — below the minimum."""
    response = post(client, "2026-03-08T01:50:00", "2026-03-08T03:00:00")
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "duration_out_of_range"
    assert detail["duration_minutes"] == 10


def test_a_repeated_hour_is_taken_as_its_first_occurrence(client):
    """01:30 happens twice on 1 November; the offset says which one was stored."""
    body = create(client, "2026-11-01T01:30:00", "2026-11-01T02:30:00")
    assert body["start_time"] == "2026-11-01T01:30:00-04:00"  # the first pass, still on DST


def test_conflicts_across_a_change_are_judged_by_the_real_instant(client):
    # 03:00-05:00 New York on the day of the jump is 07:00-09:00 UTC.
    create(client, "2026-03-08T03:00:00", "2026-03-08T05:00:00", title="New York")
    # 17:00-18:00 Tokyo the same day is 08:00-09:00 UTC: inside it.
    assert post(client, "2026-03-08T17:00:00", "2026-03-08T18:00:00", TOKYO).status_code == 409
    # 16:00-17:00 Tokyo is 07:00-08:00 UTC... also inside it.
    assert post(client, "2026-03-08T16:00:00", "2026-03-08T17:00:00", TOKYO).status_code == 409
    # 18:00-19:00 Tokyo is 09:00-10:00 UTC: touching, therefore free.
    assert post(client, "2026-03-08T18:00:00", "2026-03-08T19:00:00", TOKYO).status_code == 201


def test_a_reminder_across_the_change_fires_at_the_real_instant(client):
    body = create(client, "2026-03-08T04:00:00", "2026-03-08T05:00:00", reminder_minutes=120)
    # Two real hours before 04:00 EDT (08:00 UTC) is 06:00 UTC, which is 01:00 EST
    # — the wall clock says three hours earlier because an hour was skipped.
    assert body["notify_at"] == "2026-03-08T01:00:00-05:00"
