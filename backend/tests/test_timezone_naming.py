"""One zone, one name.

Round 12, BUG-06. ``Asia/Saigon`` and ``Asia/Ho_Chi_Minh`` are the same zone
under two spellings, and the two ends of this app disagreed about which to use:
the browser reports the first, the backend's default is the second. Whichever
name a schedule happened to arrive with was stored verbatim, so the database
ended up describing one zone in two ways — and the interface, which compares
those names to decide whether a schedule is "somewhere else", believed it.

The backend settles the spelling on the way in and serves the table it used, so
the frontend can name zones the same way without keeping its own copy.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app import timezones
from app.config import settings
from app.models import Schedule

SAIGON_OLD = "Asia/Saigon"
SAIGON = "Asia/Ho_Chi_Minh"


def post(client, timezone, start="2026-09-01T09:00:00", end="2026-09-01T10:00:00", title="Lịch"):
    return client.post(
        "/api/schedules",
        json={"title": title, "start_time": start, "end_time": end, "timezone": timezone},
    )


# --------------------------------------------------------------------------
# The table itself
# --------------------------------------------------------------------------


def test_canonical_resolves_a_renamed_zone(client):
    assert timezones.canonical(SAIGON_OLD) == SAIGON


def test_canonical_leaves_an_ordinary_name_alone(client):
    assert timezones.canonical("Asia/Tokyo") == "Asia/Tokyo"
    assert timezones.canonical("UTC") == "UTC"


def test_canonical_passes_an_unknown_name_through(client):
    """Reporting "unknown timezone" is `resolve`'s job, under the name given."""
    assert timezones.canonical("Mars/Olympus") == "Mars/Olympus"


def test_every_name_in_the_table_is_a_real_zone(client):
    for old, new in timezones.RENAMED_ZONES.items():
        assert isinstance(timezones.resolve(old), ZoneInfo), old
        assert isinstance(timezones.resolve(new), ZoneInfo), new


def test_canonical_names_are_final(client):
    """No entry may point at another entry, or canonicalising would need a loop."""
    for new in timezones.RENAMED_ZONES.values():
        assert new not in timezones.RENAMED_ZONES
        assert timezones.canonical(new) == new


def test_each_pair_really_is_the_same_zone(client):
    """A rename must not quietly move a schedule to different rules."""
    probes = [datetime(2026, 1, 15, 12), datetime(2026, 7, 15, 12)]
    for old, new in timezones.RENAMED_ZONES.items():
        for probe in probes:
            before = probe.replace(tzinfo=ZoneInfo(old)).utcoffset()
            after = probe.replace(tzinfo=ZoneInfo(new)).utcoffset()
            assert before == after, f"{old} != {new} at {probe}"


def test_resolve_accepts_either_spelling(client):
    assert timezones.resolve(SAIGON_OLD) == timezones.resolve(SAIGON)


def test_an_unknown_zone_is_still_rejected_by_name(client):
    response = post(client, "Mars/Olympus")
    assert response.status_code == 422
    assert "Mars/Olympus" in response.text


# --------------------------------------------------------------------------
# New data is stored under one name whichever name it arrived with
# --------------------------------------------------------------------------


def test_creating_with_the_old_name_stores_the_canonical_one(client, db):
    body = post(client, SAIGON_OLD)
    assert body.status_code == 201, body.text
    assert body.json()["timezone"] == SAIGON
    with db() as session:
        assert session.scalars(select(Schedule)).one().timezone == SAIGON


def test_the_instant_is_untouched_by_the_rename(client):
    """Same wall clock, same offset, same instant — only the label changes."""
    body = post(client, SAIGON_OLD).json()
    assert body["start_time"] == "2026-09-01T09:00:00+07:00"


def test_both_spellings_produce_the_same_stored_name(client):
    first = post(client, SAIGON_OLD, title="Cũ").json()
    second = post(
        client, SAIGON, "2026-09-02T09:00:00", "2026-09-02T10:00:00", title="Mới"
    ).json()
    assert first["timezone"] == second["timezone"] == SAIGON


def test_editing_with_the_old_name_stores_the_canonical_one(client):
    created = post(client, SAIGON).json()
    response = client.put(
        f"/api/schedules/{created['id']}",
        json={
            "title": "Đổi",
            "start_time": "2026-09-01T09:00:00",
            "end_time": "2026-09-01T10:00:00",
            "timezone": SAIGON_OLD,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["timezone"] == SAIGON


def test_the_configured_default_is_canonical(client):
    assert settings.default_timezone == timezones.canonical(settings.default_timezone)


# --------------------------------------------------------------------------
# The frontend is told the table rather than keeping its own
# --------------------------------------------------------------------------


def test_config_serves_the_alias_table(client):
    body = client.get("/api/config").json()
    assert body["timezone_aliases"][SAIGON_OLD] == SAIGON
    assert body["timezone_aliases"] == timezones.RENAMED_ZONES


def test_config_default_timezone_is_canonical(client):
    body = client.get("/api/config").json()
    assert body["default_timezone"] not in body["timezone_aliases"]


# --------------------------------------------------------------------------
# Rows written before the naming was settled
# --------------------------------------------------------------------------


def test_an_old_row_is_still_served_and_readable(client, db):
    """Nothing is rewritten behind the user's back on read."""
    with db() as session:
        session.add(
            Schedule(
                title="Lịch cũ",
                start_time=datetime(2026, 9, 1, 2),
                end_time=datetime(2026, 9, 1, 3),
                timezone=SAIGON_OLD,
            )
        )
        session.commit()
    body = client.get("/api/schedules").json()[0]
    assert body["timezone"] == SAIGON_OLD
    assert body["start_time"] == "2026-09-01T09:00:00+07:00"


def test_the_migration_renames_old_rows(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.db as db_module
    import migrate

    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    db_module.Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        session.add_all(
            [
                Schedule(
                    title="Cũ",
                    start_time=datetime(2026, 9, 1, 2),
                    end_time=datetime(2026, 9, 1, 3),
                    timezone=SAIGON_OLD,
                ),
                Schedule(
                    title="Mới",
                    start_time=datetime(2026, 9, 2, 2),
                    end_time=datetime(2026, 9, 2, 3),
                    timezone=SAIGON,
                ),
            ]
        )
        session.commit()

    monkeypatch.setattr(migrate, "engine", engine)
    migrate.migrate(SAIGON)

    with session_factory() as session:
        rows = session.scalars(select(Schedule).order_by(Schedule.id)).all()
        assert [row.timezone for row in rows] == [SAIGON, SAIGON]
        # Renaming the zone must not move anything in time.
        assert rows[0].start_time == datetime(2026, 9, 1, 2)

    assert migrate._canonicalise_timezones() == 0  # idempotent
    engine.dispose()
