"""Timezone behaviour: storage in UTC, rendering per schedule, conflicts across zones."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.models import Schedule

SAIGON = "Asia/Ho_Chi_Minh"  # UTC+07, no DST
TOKYO = "Asia/Tokyo"  # UTC+09, no DST
LONDON = "Europe/London"  # UTC+00 / +01
NEW_YORK = "America/New_York"  # UTC-05 / -04


def post(client, start, end, timezone, title="Lịch"):
    return client.post(
        "/api/schedules",
        json={"title": title, "start_time": start, "end_time": end, "timezone": timezone},
    )


def create(client, start, end, timezone, title="Lịch"):
    response = post(client, start, end, timezone, title)
    assert response.status_code == 201, response.text
    return response.json()


def stored(db, schedule_id: int) -> Schedule:
    with db() as session:
        return session.scalars(select(Schedule).where(Schedule.id == schedule_id)).one()


# --------------------------------------------------------------------------
# Storage and rendering
# --------------------------------------------------------------------------


def test_naive_input_is_read_in_the_payload_timezone_and_stored_as_utc(client, db):
    body = create(client, "2026-09-01T09:00:00", "2026-09-01T10:00:00", TOKYO)
    row = stored(db, body["id"])
    assert row.start_time == datetime(2026, 9, 1, 0, 0)  # 09:00 +09:00 -> 00:00 UTC
    assert row.end_time == datetime(2026, 9, 1, 1, 0)
    assert row.timezone == TOKYO
    assert row.start_time.tzinfo is None  # stored naive, by convention UTC


def test_offset_aware_input_is_accepted_and_converted(client, db):
    body = create(client, "2026-09-01T09:00:00+07:00", "2026-09-01T10:00:00+07:00", SAIGON)
    assert stored(db, body["id"]).start_time == datetime(2026, 9, 1, 2, 0)
    assert body["start_time"] == "2026-09-01T09:00:00+07:00"


def test_offset_wins_over_the_timezone_field_for_the_instant(client, db):
    """An explicit offset defines the instant; `timezone` only drives rendering."""
    body = create(client, "2026-09-01T09:00:00+09:00", "2026-09-01T10:00:00+09:00", SAIGON)
    assert stored(db, body["id"]).start_time == datetime(2026, 9, 1, 0, 0)
    # 00:00 UTC rendered in Saigon is 07:00.
    assert body["start_time"] == "2026-09-01T07:00:00+07:00"


def test_response_keeps_the_wall_clock_the_user_typed(client):
    body = create(client, "2026-09-01T09:00:00", "2026-09-01T10:00:00", TOKYO)
    assert body["start_time"] == "2026-09-01T09:00:00+09:00"
    assert body["end_time"] == "2026-09-01T10:00:00+09:00"
    assert client.get(f"/api/schedules/{body['id']}").json() == body


def test_the_same_instant_is_preserved_across_timezones(client, db):
    """Two schedules entered in different zones for the same instant agree in UTC."""
    tokyo = create(client, "2026-09-01T18:00:00", "2026-09-01T19:00:00", TOKYO, "Tokyo")
    # Same instant in Saigon is 16:00-17:00; use a different day to avoid a conflict.
    saigon = create(client, "2026-09-02T16:00:00", "2026-09-02T17:00:00", SAIGON, "Saigon")
    tokyo_row = stored(db, tokyo["id"])
    saigon_row = stored(db, saigon["id"])
    assert tokyo_row.start_time == datetime(2026, 9, 1, 9, 0)  # 18:00 +09:00
    assert saigon_row.start_time == datetime(2026, 9, 2, 9, 0)  # 16:00 +07:00


def test_default_timezone_is_used_when_omitted(client):
    response = client.post(
        "/api/schedules",
        json={
            "title": "Không nêu timezone",
            "start_time": "2026-09-01T09:00:00",
            "end_time": "2026-09-01T10:00:00",
        },
    )
    assert response.status_code == 201
    assert response.json()["timezone"] == SAIGON


def test_unknown_timezone_is_rejected(client):
    response = post(client, "2026-09-01T09:00:00", "2026-09-01T10:00:00", "Mars/Olympus")
    assert response.status_code == 422
    assert "Unknown timezone" in response.text


def test_list_is_ordered_by_real_instant_not_wall_clock(client):
    # 08:00 Tokyo (= 23:00 UTC previous day) really happens before 08:00 in London.
    create(client, "2026-09-02T08:00:00", "2026-09-02T09:00:00", LONDON, "London 08:00")
    create(client, "2026-09-02T08:00:00", "2026-09-02T09:00:00", TOKYO, "Tokyo 08:00")
    titles = [item["title"] for item in client.get("/api/schedules").json()]
    assert titles == ["Tokyo 08:00", "London 08:00"]


def test_timestamps_are_reported_in_utc(client):
    body = create(client, "2026-09-01T09:00:00", "2026-09-01T10:00:00", TOKYO)
    created = datetime.fromisoformat(body["created_at"])
    assert created.utcoffset().total_seconds() == 0
    assert abs((datetime.now(UTC) - created).total_seconds()) < 60


# --------------------------------------------------------------------------
# Conflict detection across timezones
# --------------------------------------------------------------------------


def test_same_wall_clock_in_different_zones_is_not_a_conflict(client):
    create(client, "2026-09-01T09:00:00", "2026-09-01T10:00:00", TOKYO, "Tokyo")
    # 09:00-10:00 in London is 17:00-18:00 Tokyo: a different instant entirely.
    assert post(client, "2026-09-01T09:00:00", "2026-09-01T10:00:00", LONDON).status_code == 201


def test_overlap_across_timezones_is_rejected(client):
    tokyo = create(client, "2026-09-01T11:00:00", "2026-09-01T12:00:00", TOKYO, "Tokyo")
    # Tokyo 11:00-12:00 = 02:00-03:00 UTC; Saigon 09:30-10:30 = 02:30-03:30 UTC.
    response = post(client, "2026-09-01T09:30:00", "2026-09-01T10:30:00", SAIGON)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert [item["id"] for item in detail["conflicts"]] == [tokyo["id"]]
    # The conflicting schedule is reported in its own timezone.
    assert detail["conflicts"][0]["start_time"] == "2026-09-01T11:00:00+09:00"


def test_touching_across_timezones_is_allowed(client):
    create(client, "2026-09-01T11:00:00", "2026-09-01T12:00:00", TOKYO, "Tokyo")
    # Saigon 10:00 = 03:00 UTC, exactly when the Tokyo schedule ends.
    assert post(client, "2026-09-01T10:00:00", "2026-09-01T11:00:00", SAIGON).status_code == 201


def test_conflict_is_detected_across_a_date_boundary(client):
    # Tokyo 2026-09-02 08:00-09:00 = 2026-09-01 23:00-00:00 UTC.
    tokyo = create(client, "2026-09-02T08:00:00", "2026-09-02T09:00:00", TOKYO, "Tokyo")
    # London 2026-09-01 23:30-00:30 overlaps it although the local date differs.
    response = post(client, "2026-09-01T23:30:00", "2026-09-02T00:30:00", LONDON)
    assert response.status_code == 409
    assert [item["id"] for item in response.json()["detail"]["conflicts"]] == [tokyo["id"]]


def test_changing_only_the_timezone_moves_the_instant_and_can_conflict(client):
    create(client, "2026-09-01T11:00:00", "2026-09-01T12:00:00", TOKYO, "Tokyo")
    other = create(client, "2026-09-01T11:00:00", "2026-09-01T12:00:00", LONDON, "London")
    # Re-declaring the London schedule as Tokyo time lands it on top of the first.
    response = client.put(
        f"/api/schedules/{other['id']}",
        json={
            "title": "London",
            "start_time": "2026-09-01T11:00:00",
            "end_time": "2026-09-01T12:00:00",
            "timezone": TOKYO,
        },
    )
    assert response.status_code == 409


def test_moving_a_schedule_to_another_timezone_is_allowed_when_free(client):
    schedule = create(client, "2026-09-01T11:00:00", "2026-09-01T12:00:00", TOKYO)
    response = client.put(
        f"/api/schedules/{schedule['id']}",
        json={
            "title": schedule["title"],
            "start_time": "2026-09-01T11:00:00",
            "end_time": "2026-09-01T12:00:00",
            "timezone": LONDON,
        },
    )
    assert response.status_code == 200
    assert response.json()["start_time"] == "2026-09-01T11:00:00+01:00"  # BST in September


# --------------------------------------------------------------------------
# Daylight saving time
# --------------------------------------------------------------------------


def test_dst_offsets_differ_within_the_same_zone(client):
    winter = create(client, "2026-01-15T09:00:00", "2026-01-15T10:00:00", LONDON, "Đông")
    summer = create(client, "2026-07-15T09:00:00", "2026-07-15T10:00:00", LONDON, "Hè")
    assert winter["start_time"].endswith("+00:00")  # GMT
    assert summer["start_time"].endswith("+01:00")  # BST


def test_a_range_crossing_the_spring_forward_keeps_its_real_duration(client, db):
    # 2026-03-08: New York jumps 02:00 EST -> 03:00 EDT, so 01:30-03:30 is 1 hour.
    body = create(client, "2026-03-08T01:30:00", "2026-03-08T03:30:00", NEW_YORK)
    row = stored(db, body["id"])
    assert (row.end_time - row.start_time).total_seconds() == 3600
    assert body["start_time"] == "2026-03-08T01:30:00-05:00"
    assert body["end_time"] == "2026-03-08T03:30:00-04:00"


def test_a_range_crossing_the_fall_back_keeps_its_real_duration(client, db):
    # 2026-11-01 New York repeats 01:00-02:00. The first 01:30 is EDT (-04:00) and
    # 02:30 is EST (-05:00), so two real hours pass while the clock shows one.
    body = create(client, "2026-11-01T01:30:00", "2026-11-01T02:30:00", NEW_YORK)
    row = stored(db, body["id"])
    assert (row.end_time - row.start_time).total_seconds() == 7200
    assert body["start_time"] == "2026-11-01T01:30:00-04:00"
    assert body["end_time"] == "2026-11-01T02:30:00-05:00"


def test_conflicts_still_hold_around_a_dst_transition(client):
    create(client, "2026-03-08T01:30:00", "2026-03-08T03:30:00", NEW_YORK, "Qua DST")
    # 06:45 UTC falls inside 06:30-07:30 UTC, the real span of the schedule above.
    response = post(client, "2026-03-08T06:45:00+00:00", "2026-03-08T07:15:00+00:00", LONDON)
    assert response.status_code == 409
