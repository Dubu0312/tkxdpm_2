"""Schedules that run past midnight.

Nothing in the backend reasons in calendar days — validation, ordering and
overlap detection all compare instants — so an overnight schedule is just an
ordinary range. These tests pin that down, including the interaction with
timezones, DST and conflict detection.
"""

import pytest

SAIGON = "Asia/Ho_Chi_Minh"
TOKYO = "Asia/Tokyo"
NEW_YORK = "America/New_York"


def post(client, start, end, timezone=SAIGON, title="Ca đêm", country=None):
    payload = {"title": title, "start_time": start, "end_time": end, "timezone": timezone}
    if country is not None:
        payload["country"] = country
    return client.post("/api/schedules", json=payload)


def create(client, start, end, **kwargs):
    response = post(client, start, end, **kwargs)
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------
# Creating and reading
# --------------------------------------------------------------------------


def test_an_overnight_schedule_is_valid(client):
    body = create(client, "2026-03-10T23:30:00", "2026-03-11T01:00:00")
    assert body["start_time"] == "2026-03-10T23:30:00+07:00"
    assert body["end_time"] == "2026-03-11T01:00:00+07:00"


def test_an_overnight_schedule_keeps_its_real_duration(client, db):
    from app.models import Schedule

    body = create(client, "2026-03-10T23:30:00", "2026-03-11T01:00:00")
    with db() as session:
        row = session.get(Schedule, body["id"])
        assert (row.end_time - row.start_time).total_seconds() == 5400  # 1h30


@pytest.mark.parametrize(
    ("start", "end", "case"),
    [
        ("2026-03-10T23:30:00", "2026-03-11T01:00:00", "qua nửa đêm"),
        ("2026-03-31T23:00:00", "2026-04-01T02:00:00", "qua ranh giới tháng"),
        ("2026-12-31T23:30:00", "2027-01-01T01:00:00", "qua ranh giới năm"),
        ("2026-02-28T22:00:00", "2026-03-01T06:00:00", "qua cuối tháng 2"),
        ("2026-04-01T09:00:00", "2026-04-03T09:00:00", "kéo dài 48 giờ"),
        ("2026-05-01T23:50:00", "2026-05-02T00:10:00", "khoảng ngắn ôm nửa đêm"),
    ],
)
def test_ranges_crossing_a_date_boundary_are_accepted(client, start, end, case):
    assert post(client, start, end).status_code == 201, case


def test_end_at_exactly_midnight_is_valid(client):
    body = create(client, "2026-03-10T22:00:00", "2026-03-11T00:00:00")
    assert body["end_time"] == "2026-03-11T00:00:00+07:00"


def test_end_before_start_is_still_rejected(client):
    """A later clock time on an earlier day is not an overnight schedule."""
    response = post(client, "2026-03-10T23:30:00", "2026-03-10T01:00:00")
    assert response.status_code == 422
    assert "end_time must be after start_time" in response.text


def test_list_orders_an_overnight_schedule_by_its_start(client):
    create(client, "2026-03-10T23:30:00", "2026-03-11T01:00:00", title="Đêm")
    create(client, "2026-03-11T08:00:00", "2026-03-11T09:00:00", title="Sáng hôm sau")
    create(client, "2026-03-10T08:00:00", "2026-03-10T09:00:00", title="Sáng hôm trước")
    titles = [item["title"] for item in client.get("/api/schedules").json()]
    assert titles == ["Sáng hôm trước", "Đêm", "Sáng hôm sau"]


# --------------------------------------------------------------------------
# Conflict detection around midnight
# --------------------------------------------------------------------------


@pytest.fixture()
def overnight(client):
    """23:30 on 10 March through 01:00 on 11 March."""
    return create(client, "2026-03-10T23:30:00", "2026-03-11T01:00:00", title="Ca đêm")


@pytest.mark.parametrize(
    ("start", "end", "case"),
    [
        ("2026-03-10T23:00:00", "2026-03-10T23:45:00", "chồng phần trước nửa đêm"),
        ("2026-03-11T00:30:00", "2026-03-11T01:30:00", "chồng phần sau nửa đêm"),
        ("2026-03-10T23:50:00", "2026-03-11T00:10:00", "nằm trọn bên trong, ôm nửa đêm"),
        ("2026-03-10T20:00:00", "2026-03-11T05:00:00", "bao trùm cả lịch đêm"),
        ("2026-03-10T23:30:00", "2026-03-11T01:00:00", "trùng khít"),
        ("2026-03-11T00:00:00", "2026-03-11T00:20:00", "bắt đầu đúng thời khắc nửa đêm"),
    ],
)
def test_overlapping_an_overnight_schedule_is_rejected(client, overnight, start, end, case):
    response = post(client, start, end, title="Lịch khác")
    assert response.status_code == 409, case
    assert [item["id"] for item in response.json()["detail"]["conflicts"]] == [overnight["id"]]


@pytest.mark.parametrize(
    ("start", "end", "case"),
    [
        ("2026-03-10T22:00:00", "2026-03-10T23:30:00", "kết thúc đúng lúc lịch đêm bắt đầu"),
        ("2026-03-11T01:00:00", "2026-03-11T02:00:00", "bắt đầu đúng lúc lịch đêm kết thúc"),
        ("2026-03-11T08:00:00", "2026-03-11T09:00:00", "sáng hôm sau"),
        ("2026-03-09T23:30:00", "2026-03-10T01:00:00", "lịch đêm của hôm trước"),
    ],
)
def test_not_overlapping_an_overnight_schedule_is_accepted(client, overnight, start, end, case):
    assert post(client, start, end, title="Lịch khác").status_code == 201, case


def test_two_consecutive_overnight_schedules_are_allowed(client):
    create(client, "2026-03-10T23:00:00", "2026-03-11T01:00:00", title="Đêm 1")
    second = post(client, "2026-03-11T23:00:00", "2026-03-12T01:00:00", title="Đêm 2")
    assert second.status_code == 201


def test_editing_a_daytime_schedule_into_an_overnight_one(client):
    schedule = create(client, "2026-03-10T09:00:00", "2026-03-10T10:00:00")
    response = client.put(
        f"/api/schedules/{schedule['id']}",
        json={
            "title": "Thành ca đêm",
            "start_time": "2026-03-10T23:30:00",
            "end_time": "2026-03-11T01:00:00",
            "timezone": SAIGON,
        },
    )
    assert response.status_code == 200
    assert response.json()["end_time"] == "2026-03-11T01:00:00+07:00"


def test_an_overnight_schedule_does_not_conflict_with_itself_when_edited(client, overnight):
    response = client.put(
        f"/api/schedules/{overnight['id']}",
        json={
            "title": "Ca đêm dài hơn",
            "start_time": "2026-03-10T23:00:00",
            "end_time": "2026-03-11T02:00:00",
            "timezone": SAIGON,
        },
    )
    assert response.status_code == 200


# --------------------------------------------------------------------------
# Timezones and DST
# --------------------------------------------------------------------------


def test_an_overnight_schedule_in_one_zone_may_be_a_daytime_one_in_another(client):
    """23:30-01:00 in Saigon is 01:30-03:00 the next day in Tokyo: same instants."""
    body = create(client, "2026-03-10T23:30:00", "2026-03-11T01:00:00")
    assert body["start_time"] == "2026-03-10T23:30:00+07:00"
    # Tokyo is +09:00, so the same instant is 01:30 on 11 March there.
    clash = post(client, "2026-03-11T01:30:00", "2026-03-11T02:00:00", timezone=TOKYO)
    assert clash.status_code == 409


def test_a_daytime_schedule_elsewhere_can_clash_with_an_overnight_one(client, overnight):
    # Saigon 23:30-01:00 is 16:30-18:00 UTC; London 17:00-17:30 sits inside it.
    response = post(client, "2026-03-10T17:00:00", "2026-03-10T17:30:00", timezone="Europe/London")
    assert response.status_code == 409


def test_an_overnight_schedule_across_the_spring_forward(client, db):
    """New York 2026-03-07 23:30 -> 03:30 loses an hour: 3 real hours, not 4."""
    from app.models import Schedule

    body = create(client, "2026-03-07T23:30:00", "2026-03-08T03:30:00", timezone=NEW_YORK)
    assert body["start_time"] == "2026-03-07T23:30:00-05:00"
    assert body["end_time"] == "2026-03-08T03:30:00-04:00"
    with db() as session:
        row = session.get(Schedule, body["id"])
        assert (row.end_time - row.start_time).total_seconds() == 3 * 3600


def test_an_overnight_schedule_across_the_fall_back(client, db):
    """New York 2026-10-31 23:30 -> 03:30 gains an hour: 5 real hours."""
    from app.models import Schedule

    body = create(client, "2026-10-31T23:30:00", "2026-11-01T03:30:00", timezone=NEW_YORK)
    with db() as session:
        row = session.get(Schedule, body["id"])
        assert (row.end_time - row.start_time).total_seconds() == 5 * 3600


def test_conflicts_hold_for_an_overnight_schedule_across_a_dst_change(client):
    create(client, "2026-03-07T23:30:00", "2026-03-08T03:30:00", timezone=NEW_YORK)
    # 06:00 UTC is inside 04:30-07:30 UTC, the real span of the schedule above.
    response = post(client, "2026-03-08T06:00:00", "2026-03-08T06:30:00", timezone="UTC")
    assert response.status_code == 409


# --------------------------------------------------------------------------
# Holidays
# --------------------------------------------------------------------------


def test_an_overnight_schedule_reaching_into_a_holiday_is_rejected(client):
    """It really does occupy time on the holiday, so the country rule applies."""
    response = post(
        client, "2025-12-31T23:30:00", "2026-01-01T01:00:00", country="VN", title="Đón giao thừa"
    )
    assert response.status_code == 409
    assert response.json()["detail"]["holidays"][0]["date"] == "2026-01-01"


def test_an_overnight_schedule_ending_exactly_at_midnight_avoids_the_holiday(client):
    assert post(
        client, "2025-12-31T22:00:00", "2026-01-01T00:00:00", country="VN"
    ).status_code == 201
