"""Overlap rules for creating and updating schedules.

Existing schedule used throughout: 09:00 – 10:00 on 2026-09-01.
Touching ranges (one ends exactly when the other starts) are allowed.
"""

import pytest

DAY = "2026-09-01"


def make(client, start: str, end: str, title: str = "Lịch"):
    return client.post(
        "/api/schedules",
        json={"title": title, "start_time": f"{DAY}T{start}:00", "end_time": f"{DAY}T{end}:00"},
    )


@pytest.fixture()
def existing(client):
    response = make(client, "09:00", "10:00", title="Lịch có sẵn")
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize(
    ("start", "end", "case"),
    [
        ("09:00", "10:00", "cùng khoảng"),
        ("09:15", "09:45", "nằm trọn bên trong"),
        ("08:00", "11:00", "bao trùm"),
        ("08:30", "09:30", "chồng phần đầu"),
        ("09:30", "10:30", "chồng phần cuối"),
        ("08:59", "09:01", "chồng một phút"),
        ("09:59", "11:00", "chồng một phút ở cuối"),
    ],
)
def test_overlapping_create_is_rejected(client, existing, start, end, case):
    response = make(client, start, end)
    assert response.status_code == 409, case
    detail = response.json()["detail"]
    assert detail["code"] == "schedule_conflict"
    assert [item["id"] for item in detail["conflicts"]] == [existing["id"]]
    assert detail["conflicts"][0]["title"] == "Lịch có sẵn"


@pytest.mark.parametrize(
    ("start", "end", "case"),
    [
        ("08:00", "09:00", "kết thúc đúng lúc lịch cũ bắt đầu"),
        ("10:00", "11:00", "bắt đầu đúng lúc lịch cũ kết thúc"),
        ("07:00", "08:00", "hoàn toàn trước"),
        ("11:00", "12:00", "hoàn toàn sau"),
    ],
)
def test_non_overlapping_create_is_accepted(client, existing, start, end, case):
    assert make(client, start, end).status_code == 201, case


def test_conflict_does_not_persist_anything(client, existing):
    assert make(client, "09:30", "10:30").status_code == 409
    assert len(client.get("/api/schedules").json()) == 1


def test_overlap_on_a_different_day_is_not_a_conflict(client, existing):
    response = client.post(
        "/api/schedules",
        json={
            "title": "Hôm sau",
            "start_time": "2026-09-02T09:00:00",
            "end_time": "2026-09-02T10:00:00",
        },
    )
    assert response.status_code == 201


def test_all_overlapping_schedules_are_reported(client, existing):
    second = make(client, "11:00", "12:00", title="Lịch thứ hai").json()
    response = make(client, "09:30", "11:30")
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert [item["id"] for item in detail["conflicts"]] == [existing["id"], second["id"]]
    assert "2" in detail["message"]


def test_update_onto_another_schedule_is_rejected(client, existing):
    other = make(client, "14:00", "15:00", title="Lịch khác").json()
    response = client.put(
        f"/api/schedules/{other['id']}",
        json={
            "title": other["title"],
            "start_time": f"{DAY}T09:30:00",
            "end_time": f"{DAY}T10:30:00",
        },
    )
    assert response.status_code == 409
    assert [item["id"] for item in response.json()["detail"]["conflicts"]] == [existing["id"]]
    # The rejected edit left the record untouched.
    unchanged = client.get(f"/api/schedules/{other['id']}").json()
    assert unchanged["start_time"] == f"{DAY}T14:00:00+07:00"


def test_update_does_not_conflict_with_itself(client, existing):
    response = client.put(
        f"/api/schedules/{existing['id']}",
        json={
            "title": "Đổi tiêu đề, giữ nguyên giờ",
            "start_time": existing["start_time"],
            "end_time": existing["end_time"],
        },
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Đổi tiêu đề, giữ nguyên giờ"


def test_update_can_move_a_schedule_into_a_free_slot(client, existing):
    other = make(client, "14:00", "15:00", title="Lịch khác").json()
    response = client.put(
        f"/api/schedules/{other['id']}",
        json={
            "title": other["title"],
            "start_time": f"{DAY}T10:00:00",
            "end_time": f"{DAY}T11:00:00",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["start_time"] == f"{DAY}T10:00:00+07:00"


def test_update_may_shrink_a_schedule_onto_its_own_range(client, existing):
    response = client.put(
        f"/api/schedules/{existing['id']}",
        json={
            "title": existing["title"],
            "start_time": f"{DAY}T09:30:00",
            "end_time": f"{DAY}T09:45:00",
        },
    )
    assert response.status_code == 200


def test_invalid_range_is_still_rejected_before_the_conflict_check(client, existing):
    response = client.post(
        "/api/schedules",
        json={
            "title": "Sai giờ",
            "start_time": f"{DAY}T10:00:00",
            "end_time": f"{DAY}T09:00:00",
        },
    )
    assert response.status_code == 422
