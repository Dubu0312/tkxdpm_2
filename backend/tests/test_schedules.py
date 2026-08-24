# Times are sent as naive wall-clock values plus an explicit timezone; responses
# come back in that same timezone, offset included.
TZ = "Asia/Ho_Chi_Minh"
OFFSET = "+07:00"

PAYLOAD = {
    "title": "Họp nhóm",
    "description": "Review sprint",
    "location": "Phòng A1",
    "start_time": "2026-09-01T09:00:00",
    "end_time": "2026-09-01T10:30:00",
    "timezone": TZ,
}


def create(client, **overrides):
    response = client.post("/api/schedules", json={**PAYLOAD, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


def test_list_is_empty_initially(client):
    response = client.get("/api/schedules")
    assert response.status_code == 200
    assert response.json() == []


def test_create_returns_full_record(client):
    body = create(client)
    assert body["id"] > 0
    assert body["title"] == PAYLOAD["title"]
    assert body["description"] == PAYLOAD["description"]
    assert body["location"] == PAYLOAD["location"]
    assert body["start_time"] == f"{PAYLOAD['start_time']}{OFFSET}"
    assert body["end_time"] == f"{PAYLOAD['end_time']}{OFFSET}"
    assert body["timezone"] == TZ
    # Timestamps are server-side UTC, rendered with an explicit offset.
    assert body["created_at"].endswith("+00:00")
    assert body["updated_at"].endswith("+00:00")


def test_optional_fields_may_be_omitted(client):
    response = client.post(
        "/api/schedules",
        json={
            "title": "Khám răng",
            "start_time": "2026-09-02T08:00:00",
            "end_time": "2026-09-02T08:30:00",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["description"] is None
    assert body["location"] is None


def test_list_is_sorted_by_start_time(client):
    create(client, title="Muộn", start_time="2026-09-03T15:00:00", end_time="2026-09-03T16:00:00")
    create(client, title="Sớm", start_time="2026-09-03T08:00:00", end_time="2026-09-03T09:00:00")

    titles = [item["title"] for item in client.get("/api/schedules").json()]
    assert titles == ["Sớm", "Muộn"]


def test_get_detail(client):
    created = create(client)
    response = client.get(f"/api/schedules/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_missing_returns_404(client):
    response = client.get("/api/schedules/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Schedule not found"


def test_update(client):
    created = create(client)
    response = client.put(
        f"/api/schedules/{created['id']}",
        json={**PAYLOAD, "title": "Họp nhóm (dời giờ)", "end_time": "2026-09-01T11:00:00"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["title"] == "Họp nhóm (dời giờ)"
    assert body["end_time"] == f"2026-09-01T11:00:00{OFFSET}"
    assert client.get(f"/api/schedules/{created['id']}").json()["title"] == "Họp nhóm (dời giờ)"


def test_update_missing_returns_404(client):
    response = client.put("/api/schedules/999", json=PAYLOAD)
    assert response.status_code == 404


def test_delete(client):
    created = create(client)
    assert client.delete(f"/api/schedules/{created['id']}").status_code == 204
    assert client.get(f"/api/schedules/{created['id']}").status_code == 404
    assert client.get("/api/schedules").json() == []


def test_delete_missing_returns_404(client):
    assert client.delete("/api/schedules/999").status_code == 404


def test_end_before_start_is_rejected(client):
    response = client.post(
        "/api/schedules",
        json={**PAYLOAD, "start_time": "2026-09-01T10:00:00", "end_time": "2026-09-01T09:00:00"},
    )
    assert response.status_code == 422
    assert "end_time must be after start_time" in response.text


def test_equal_start_and_end_is_rejected(client):
    response = client.post(
        "/api/schedules",
        json={**PAYLOAD, "start_time": "2026-09-01T10:00:00", "end_time": "2026-09-01T10:00:00"},
    )
    assert response.status_code == 422


def test_empty_title_is_rejected(client):
    response = client.post("/api/schedules", json={**PAYLOAD, "title": ""})
    assert response.status_code == 422


def test_response_uses_the_schedule_timezone(client):
    body = create(client)
    assert body["start_time"].endswith(OFFSET)
    assert body["timezone"] == TZ
