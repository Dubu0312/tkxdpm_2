"""Public-holiday validation: refuse schedules that fall on an official holiday."""

import pytest

# Reference days used throughout (all official, all computed by the holidays package):
#   VN 2026-02-17 Lunar New Year   |   VN 2026-09-02 National Day
#   US 2026-07-04 Independence Day |   JP 2026-01-01 New Year's Day
WORKDAY = "2026-03-10"  # an ordinary Tuesday in every country used here


def post(
    client,
    day,
    country=None,
    start="09:00",
    end="10:00",
    tz="Asia/Ho_Chi_Minh",
    title="Lịch",
):
    payload = {
        "title": title,
        "start_time": f"{day}T{start}:00",
        "end_time": f"{day}T{end}:00",
        "timezone": tz,
    }
    if country is not None:
        payload["country"] = country
    return client.post("/api/schedules", json=payload)


def create(client, **kwargs):
    response = post(client, **kwargs)
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------
# The country field itself
# --------------------------------------------------------------------------


def test_country_is_optional_and_defaults_to_none(client):
    body = create(client, day=WORKDAY)
    assert body["country"] is None


def test_country_is_stored_and_returned_upper_case(client):
    assert create(client, day=WORKDAY, country="vn")["country"] == "VN"


def test_empty_country_means_no_country(client):
    assert create(client, day=WORKDAY, country="")["country"] is None


def test_unknown_country_is_rejected(client):
    response = post(client, day=WORKDAY, country="XX")
    assert response.status_code == 422
    assert "Unknown country" in response.text


def test_without_a_country_a_holiday_is_allowed(client):
    """No country means no claim about holidays, so nothing is blocked."""
    assert post(client, day="2026-02-17").status_code == 201


def test_countries_endpoint_lists_supported_countries(client):
    response = client.get("/api/countries")
    assert response.status_code == 200
    countries = response.json()
    assert len(countries) > 100
    codes = {item["code"] for item in countries}
    assert {"VN", "US", "JP"} <= codes
    assert {"code": "VN", "name": "Vietnam"} in countries
    # Sorted by name so the frontend can render it as-is.
    assert [item["name"] for item in countries] == sorted(item["name"] for item in countries)


# --------------------------------------------------------------------------
# Refusing holidays
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("day", "country", "name"),
    [
        ("2026-02-17", "VN", "Lunar New Year"),  # moving feast, computed not tabulated
        ("2026-09-02", "VN", "National Day"),
        ("2026-07-04", "US", "Independence Day"),
        ("2026-01-01", "JP", "New Year's Day"),
    ],
)
def test_creating_on_a_holiday_is_rejected(client, day, country, name):
    response = post(client, day=day, country=country)
    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "holiday_conflict"
    assert detail["country"] == country
    assert detail["holidays"] == [{"date": day, "name": name}]


def test_a_holiday_in_one_country_is_a_working_day_in_another(client):
    # 4 July is a US holiday but an ordinary Saturday in Vietnam.
    assert post(client, day="2026-07-04", country="US").status_code == 409
    free = post(client, day="2026-07-04", country="VN", start="14:00", end="15:00")
    assert free.status_code == 201


def test_nothing_is_stored_when_a_holiday_is_refused(client):
    assert post(client, day="2026-02-17", country="VN").status_code == 409
    assert client.get("/api/schedules").json() == []


def test_a_range_spanning_several_days_reports_every_holiday(client):
    response = client.post(
        "/api/schedules",
        json={
            "title": "Nghỉ Tết",
            "start_time": "2026-02-16T09:00:00",
            "end_time": "2026-02-18T17:00:00",
            "timezone": "Asia/Ho_Chi_Minh",
            "country": "VN",
        },
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert [hit["date"] for hit in detail["holidays"]] == ["2026-02-16", "2026-02-17", "2026-02-18"]
    assert "3" in detail["message"]


def test_a_range_ending_at_midnight_does_not_reach_the_next_day(client):
    """Ranges are half-open: ending exactly at 00:00 stays on the previous day."""
    response = client.post(
        "/api/schedules",
        json={
            "title": "Đêm giao thừa",
            "start_time": "2025-12-31T22:00:00",
            "end_time": "2026-01-01T00:00:00",
            "timezone": "Asia/Ho_Chi_Minh",
            "country": "VN",
        },
    )
    assert response.status_code == 201


def test_a_range_crossing_midnight_into_a_holiday_is_rejected(client):
    response = client.post(
        "/api/schedules",
        json={
            "title": "Qua giao thừa",
            "start_time": "2025-12-31T22:00:00",
            "end_time": "2026-01-01T00:30:00",
            "timezone": "Asia/Ho_Chi_Minh",
            "country": "VN",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["holidays"][0]["date"] == "2026-01-01"


# --------------------------------------------------------------------------
# Editing
# --------------------------------------------------------------------------


def put(client, schedule_id, day, country, start="09:00", end="10:00", tz="Asia/Ho_Chi_Minh"):
    return client.put(
        f"/api/schedules/{schedule_id}",
        json={
            "title": "Lịch",
            "start_time": f"{day}T{start}:00",
            "end_time": f"{day}T{end}:00",
            "timezone": tz,
            "country": country,
        },
    )


def test_moving_a_schedule_onto_a_holiday_is_rejected(client):
    schedule = create(client, day=WORKDAY, country="VN")
    response = put(client, schedule["id"], "2026-02-17", "VN")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "holiday_conflict"
    # The stored schedule is untouched.
    assert client.get(f"/api/schedules/{schedule['id']}").json()["start_time"].startswith(WORKDAY)


def test_adding_a_country_that_makes_the_existing_day_a_holiday_is_rejected(client):
    """The day was fine with no country; naming the country now blocks it."""
    schedule = create(client, day="2026-07-04")
    assert put(client, schedule["id"], "2026-07-04", "US").status_code == 409


def test_editing_a_schedule_on_a_working_day_still_succeeds(client):
    schedule = create(client, day=WORKDAY, country="VN")
    assert put(client, schedule["id"], WORKDAY, "VN", end="11:00").status_code == 200


def test_clearing_the_country_lifts_the_holiday_block(client):
    schedule = create(client, day=WORKDAY, country="US")
    assert put(client, schedule["id"], "2026-07-04", "US").status_code == 409
    response = put(client, schedule["id"], "2026-07-04", None)
    assert response.status_code == 200
    assert response.json()["country"] is None


# --------------------------------------------------------------------------
# Interaction with timezones and with overlap detection
# --------------------------------------------------------------------------


def test_the_holiday_day_is_the_local_day_not_the_utc_day(client):
    """08:00 on 1 Jan in Tokyo is still 31 Dec in UTC — the local day decides."""
    response = post(
        client, day="2026-01-01", country="JP", start="08:00", end="09:00", tz="Asia/Tokyo"
    )
    assert response.status_code == 409
    assert response.json()["detail"]["holidays"][0]["date"] == "2026-01-01"


def test_a_schedule_that_is_only_a_holiday_in_utc_is_allowed(client):
    """23:00 on 31 Dec in New York is 04:00 on 1 Jan UTC, but locally it is not yet a holiday."""
    response = client.post(
        "/api/schedules",
        json={
            "title": "Giao thừa New York",
            "start_time": "2025-12-31T23:00:00",
            "end_time": "2025-12-31T23:59:00",
            "timezone": "America/New_York",
            "country": "US",
        },
    )
    assert response.status_code == 201


def test_the_holiday_check_runs_before_the_overlap_check(client):
    """A holiday blocks the whole day, so it is the more useful message."""
    create(client, day="2026-07-04", country="VN", start="09:00", end="10:00")
    response = post(client, day="2026-07-04", country="US", start="09:00", end="10:00")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "holiday_conflict"


def test_overlap_is_still_reported_on_a_working_day(client):
    create(client, day=WORKDAY, country="VN")
    response = post(client, day=WORKDAY, country="VN", start="09:30", end="10:30")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "schedule_conflict"
