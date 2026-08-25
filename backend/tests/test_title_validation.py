"""BUG-01: a title of nothing but whitespace was accepted and stored verbatim.

The frontend trimmed before sending, so the form never showed the problem — but
the API is the contract, and it has to hold on its own.
"""

import pytest

SAIGON = "Asia/Ho_Chi_Minh"

BLANK = ["   ", "\t", "\n", " \t \n ", " "]


def payload(title, **extra):
    return {
        "title": title,
        "start_time": "2027-01-05T09:00:00",
        "end_time": "2027-01-05T10:00:00",
        "timezone": SAIGON,
        **extra,
    }


def create(client, title):
    return client.post("/api/schedules", json=payload(title))


@pytest.fixture()
def existing(client):
    response = create(client, "Lịch gốc")
    assert response.status_code == 201
    return response.json()


# --------------------------------------------------------------------------
# Rejecting a title that is not really there
# --------------------------------------------------------------------------


@pytest.mark.parametrize("title", BLANK)
def test_a_whitespace_only_title_is_rejected_on_create(client, title):
    response = create(client, title)
    assert response.status_code == 422, f"{title!r} was accepted"
    assert "at least 1 character" in response.text


@pytest.mark.parametrize("title", BLANK)
def test_a_whitespace_only_title_is_rejected_on_update(client, existing, title):
    """Create and update must agree; both inherit the same rule."""
    response = client.put(f"/api/schedules/{existing['id']}", json=payload(title))
    assert response.status_code == 422, f"{title!r} was accepted"


def test_an_empty_title_is_still_rejected(client):
    assert create(client, "").status_code == 422


def test_nothing_is_stored_when_the_title_is_refused(client):
    assert create(client, "   ").status_code == 422
    assert client.get("/api/schedules").json() == []


def test_a_refused_update_leaves_the_schedule_alone(client, existing):
    assert client.put(f"/api/schedules/{existing['id']}", json=payload("   ")).status_code == 422
    assert client.get(f"/api/schedules/{existing['id']}").json()["title"] == "Lịch gốc"


# --------------------------------------------------------------------------
# Trimming what the user did type
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sent", "stored"),
    [
        ("  Họp nhóm  ", "Họp nhóm"),
        ("\tHọp nhóm\n", "Họp nhóm"),
        ("Họp nhóm", "Họp nhóm"),
        ("  Họp   nhóm  ", "Họp   nhóm"),  # only the ends are touched
    ],
)
def test_surrounding_whitespace_is_trimmed(client, sent, stored):
    assert create(client, sent).json()["title"] == stored


def test_the_update_path_trims_too(client, existing):
    body = client.put(f"/api/schedules/{existing['id']}", json=payload("  Tên mới  ")).json()
    assert body["title"] == "Tên mới"


# --------------------------------------------------------------------------
# The length rule is unchanged — it just applies to the real title
# --------------------------------------------------------------------------


def test_a_title_of_exactly_the_limit_is_accepted(client):
    assert create(client, "x" * 200).status_code == 201


def test_a_title_over_the_limit_is_still_rejected(client):
    assert create(client, "x" * 201).status_code == 422


def test_padding_no_longer_pushes_a_valid_title_over_the_limit(client):
    """200 characters plus spaces used to be refused for a length nobody typed."""
    response = create(client, "  " + "x" * 200 + "  ")
    assert response.status_code == 201
    assert response.json()["title"] == "x" * 200


def test_a_title_that_is_too_long_only_after_trimming_is_still_rejected(client):
    assert create(client, "  " + "x" * 201 + "  ").status_code == 422
