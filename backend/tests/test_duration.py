"""Minimum and maximum length of a schedule.

The limits live in ``settings`` (``MIN_DURATION_MINUTES`` / ``MAX_DURATION_MINUTES``)
and are enforced by the API. Length is measured between the two instants, so it
is the real elapsed time whatever timezone the schedule uses, however it crosses
midnight, and across a DST change where the wall clock is misleading.
"""

from datetime import datetime, timedelta

import pytest

from app.config import settings

SAIGON = "Asia/Ho_Chi_Minh"
TOKYO = "Asia/Tokyo"
NEW_YORK = "America/New_York"

MIN = settings.min_duration_minutes
MAX = settings.max_duration_minutes

BASE = datetime(2026, 6, 1, 9, 0)


def post(client, minutes, start=BASE, timezone=SAIGON, title="Lịch"):
    return client.post(
        "/api/schedules",
        json={
            "title": title,
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(minutes=minutes)).isoformat(),
            "timezone": timezone,
        },
    )


def duration_error(response):
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "duration_out_of_range"
    return detail


# --------------------------------------------------------------------------
# The limits themselves
# --------------------------------------------------------------------------


def test_the_limits_are_served_rather_than_hard_coded(client):
    body = client.get("/api/config").json()
    assert body["min_duration_minutes"] == MIN
    assert body["max_duration_minutes"] == MAX
    assert body["default_timezone"] == settings.default_timezone


def test_the_configured_limits_are_sane():
    assert 1 <= MIN < MAX


# --------------------------------------------------------------------------
# At the boundaries
# --------------------------------------------------------------------------


def test_exactly_the_minimum_is_accepted(client):
    assert post(client, MIN).status_code == 201


def test_exactly_the_maximum_is_accepted(client):
    assert post(client, MAX).status_code == 201


def test_one_minute_under_the_minimum_is_rejected(client):
    detail = duration_error(post(client, MIN - 1))
    assert detail["duration_minutes"] == MIN - 1
    assert detail["min_minutes"] == MIN
    assert detail["max_minutes"] == MAX
    assert "below the minimum" in detail["message"]


def test_one_minute_over_the_maximum_is_rejected(client):
    detail = duration_error(post(client, MAX + 1))
    assert detail["duration_minutes"] == MAX + 1
    assert "above the maximum" in detail["message"]


@pytest.mark.parametrize("minutes", [1, 2, MIN - 1])
def test_anything_shorter_than_the_minimum_is_rejected(client, minutes):
    duration_error(post(client, minutes))


@pytest.mark.parametrize("minutes", [MAX + 1, MAX * 2, 365 * 24 * 60])
def test_anything_longer_than_the_maximum_is_rejected(client, minutes):
    duration_error(post(client, minutes))


@pytest.mark.parametrize("minutes", [MIN, MIN + 1, 60, MAX - 1, MAX])
def test_lengths_inside_the_range_are_accepted(client, minutes):
    assert post(client, minutes, start=BASE + timedelta(days=minutes)).status_code == 201


def test_nothing_is_stored_when_the_length_is_refused(client):
    duration_error(post(client, 1))
    assert client.get("/api/schedules").json() == []


# --------------------------------------------------------------------------
# Length is measured between instants
# --------------------------------------------------------------------------


def test_the_timezone_does_not_change_the_length(client):
    """The same wall-clock span is the same length in any zone."""
    assert post(client, MIN, timezone=TOKYO).status_code == 201
    assert post(client, MIN - 1, timezone=TOKYO).status_code == 422


def test_a_range_written_with_offsets_is_measured_between_the_instants(client):
    """09:00+07:00 to 09:00+09:00 is two hours earlier, not the same moment."""
    response = client.post(
        "/api/schedules",
        json={
            "title": "Chéo múi giờ",
            "start_time": "2026-06-01T09:00:00+09:00",
            "end_time": "2026-06-01T09:00:00+07:00",  # two hours later in real time
            "timezone": TOKYO,
        },
    )
    assert response.status_code == 201


def test_an_overnight_schedule_is_measured_across_midnight(client):
    """23:50 to 00:10 is 20 minutes, not a negative or a 23-hour span."""
    response = client.post(
        "/api/schedules",
        json={
            "title": "Qua nửa đêm",
            "start_time": "2026-06-01T23:50:00",
            "end_time": "2026-06-02T00:10:00",
            "timezone": SAIGON,
        },
    )
    assert MIN <= 20, "this case assumes the minimum is at most 20 minutes"
    assert response.status_code == 201


def test_a_short_overnight_schedule_is_still_too_short(client):
    response = client.post(
        "/api/schedules",
        json={
            "title": "Quá ngắn qua nửa đêm",
            "start_time": "2026-06-01T23:59:00",
            "end_time": "2026-06-02T00:01:00",
            "timezone": SAIGON,
        },
    )
    assert duration_error(response)["duration_minutes"] == 2


def test_a_schedule_spanning_days_is_measured_in_real_time(client):
    """Two whole days is 2880 minutes — accepted only because the cap is a week."""
    response = client.post(
        "/api/schedules",
        json={
            "title": "Hai ngày",
            "start_time": "2026-06-01T09:00:00",
            "end_time": "2026-06-03T09:00:00",
            "timezone": SAIGON,
        },
    )
    assert response.status_code == 201
    assert MAX >= 2880


def test_a_schedule_longer_than_the_cap_across_days_is_rejected(client):
    response = client.post(
        "/api/schedules",
        json={
            "title": "Quá dài",
            "start_time": "2026-06-01T09:00:00",
            "end_time": "2026-06-20T09:00:00",
            "timezone": SAIGON,
        },
    )
    assert duration_error(response)["duration_minutes"] == 19 * 24 * 60


def test_dst_makes_the_wall_clock_lie_and_the_real_length_wins(client):
    """01:30 to 03:30 on the spring-forward day is one real hour, not two."""
    response = client.post(
        "/api/schedules",
        json={
            "title": "Qua DST",
            "start_time": "2026-03-08T01:30:00",
            "end_time": "2026-03-08T03:30:00",
            "timezone": NEW_YORK,
        },
    )
    assert response.status_code == 201  # 60 real minutes, inside the range


def test_a_dst_night_that_looks_long_enough_but_is_not(client):
    """01:50 to 03:00 reads as 70 minutes but only 10 real minutes pass."""
    response = client.post(
        "/api/schedules",
        json={
            "title": "Ảo giác DST",
            "start_time": "2026-03-08T01:50:00",
            "end_time": "2026-03-08T03:00:00",
            "timezone": NEW_YORK,
        },
    )
    assert duration_error(response)["duration_minutes"] == 10


# --------------------------------------------------------------------------
# Editing
# --------------------------------------------------------------------------


def put(client, schedule_id, minutes, start=BASE):
    return client.put(
        f"/api/schedules/{schedule_id}",
        json={
            "title": "Lịch",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(minutes=minutes)).isoformat(),
            "timezone": SAIGON,
        },
    )


@pytest.fixture()
def existing(client):
    response = post(client, 60)
    assert response.status_code == 201
    return response.json()


def test_shrinking_a_schedule_below_the_minimum_is_rejected(client, existing):
    duration_error(put(client, existing["id"], MIN - 1))
    # The stored schedule is untouched.
    stored = client.get(f"/api/schedules/{existing['id']}").json()
    assert stored["end_time"].endswith("10:00:00+07:00")


def test_stretching_a_schedule_past_the_maximum_is_rejected(client, existing):
    duration_error(put(client, existing["id"], MAX + 1))


def test_editing_within_the_limits_still_works(client, existing):
    assert put(client, existing["id"], MIN).status_code == 200
    assert put(client, existing["id"], MAX).status_code == 200


# --------------------------------------------------------------------------
# The other rules still apply
# --------------------------------------------------------------------------


def test_end_before_start_is_still_a_plain_validation_error(client):
    """A negative length is malformed input, not a duration-limit refusal."""
    response = client.post(
        "/api/schedules",
        json={
            "title": "Ngược",
            "start_time": "2026-06-01T10:00:00",
            "end_time": "2026-06-01T09:00:00",
            "timezone": SAIGON,
        },
    )
    assert response.status_code == 422
    assert "end_time must be after start_time" in response.text


def test_the_length_is_checked_before_overlaps(client):
    """A schedule that cannot exist at any length should say so first."""
    assert post(client, 60).status_code == 201
    detail = duration_error(post(client, 1))  # same slot, but too short
    assert detail["code"] == "duration_out_of_range"


def test_a_valid_length_still_reports_an_overlap(client):
    assert post(client, 60).status_code == 201
    response = post(client, 60, start=BASE + timedelta(minutes=30))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "schedule_conflict"


def test_a_valid_length_still_reports_a_holiday(client):
    response = client.post(
        "/api/schedules",
        json={
            "title": "Tết",
            "start_time": "2026-02-17T09:00:00",
            "end_time": "2026-02-17T10:00:00",
            "timezone": SAIGON,
            "country": "VN",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "holiday_conflict"


def test_a_reminder_still_works_on_a_minimum_length_schedule(client):
    response = client.post(
        "/api/schedules",
        json={
            "title": "Ngắn nhất",
            "start_time": "2026-06-01T09:00:00",
            "end_time": (BASE + timedelta(minutes=MIN)).isoformat(),
            "timezone": SAIGON,
            "reminder_minutes": 30,
        },
    )
    assert response.status_code == 201
    assert response.json()["notify_at"] == "2026-06-01T08:30:00+07:00"
