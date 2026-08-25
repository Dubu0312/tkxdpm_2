"""Bring an existing database up to the current schema.

Two upgrades are handled, both idempotent — running this on an up-to-date
database is a no-op:

1. **Timezone support** (Round 3): databases created earlier store naive *local*
   datetimes and have no ``timezone`` column. The column is added and the stored
   instants are rewritten as UTC.
2. **Holiday validation** (Round 4): adds the nullable ``country`` column.
3. **Timezone naming** (Round 12): rewrites stored zone names that have since
   been renamed (``Asia/Saigon`` -> ``Asia/Ho_Chi_Minh``), so old rows are
   spelled the way new ones are.

    python migrate.py [--timezone Asia/Ho_Chi_Minh]

``--timezone`` is the zone the existing rows were entered in; it defaults to
``DEFAULT_TIMEZONE`` from the environment. It only matters for upgrade 1.

This is a deliberate stopgap for a handful of schema changes — reach for Alembic
once migrations become routine.
"""

import argparse
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import inspect, text

from app import timezones
from app.config import settings
from app.db import engine

TIMESTAMP_COLUMNS = ("start_time", "end_time", "created_at", "updated_at")


def _columns() -> set[str] | None:
    """Column names of the schedules table, or None when it does not exist yet."""
    inspector = inspect(engine)
    if "schedules" not in inspector.get_table_names():
        return None
    return {column["name"] for column in inspector.get_columns("schedules")}


def _local_to_utc(value: str, tz: ZoneInfo) -> str:
    parsed = datetime.fromisoformat(value).replace(tzinfo=tz)
    return parsed.astimezone(UTC).replace(tzinfo=None).isoformat(sep=" ")


def _add_timezone_column(timezone_name: str) -> int:
    """Add `timezone` and rewrite local datetimes as UTC. Returns rows converted."""
    tz = ZoneInfo(timezone_name)
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE schedules "
                f"ADD COLUMN timezone VARCHAR(64) NOT NULL DEFAULT '{timezone_name}'"
            )
        )
        rows = conn.execute(text(f"SELECT id, {', '.join(TIMESTAMP_COLUMNS)} FROM schedules")).all()
        for row in rows:
            values = {
                column: _local_to_utc(str(getattr(row, column)), tz)
                for column in TIMESTAMP_COLUMNS
            }
            assignments = ", ".join(f"{column} = :{column}" for column in TIMESTAMP_COLUMNS)
            conn.execute(
                text(f"UPDATE schedules SET {assignments} WHERE id = :id"),
                {**values, "id": row.id},
            )

    print(f"Migrated {len(rows)} schedule(s) from {timezone_name} local time to UTC.")
    return len(rows)


def _add_country_column() -> None:
    """Add the nullable `country` column used by holiday validation."""
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE schedules ADD COLUMN country VARCHAR(2)"))
    print("Added the 'country' column (existing schedules keep no country).")


def _add_reminder_columns() -> None:
    """Add the nullable columns used by reminder notifications."""
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE schedules ADD COLUMN reminder_minutes INTEGER"))
        conn.execute(text("ALTER TABLE schedules ADD COLUMN notified_at DATETIME"))
    print("Added the reminder columns (existing schedules keep no reminder).")


def _add_google_columns() -> None:
    """Add the nullable columns linking a schedule to its Google event."""
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE schedules ADD COLUMN google_event_id VARCHAR(1024)"))
        conn.execute(text("ALTER TABLE schedules ADD COLUMN google_calendar_id VARCHAR(255)"))
        conn.execute(text("ALTER TABLE schedules ADD COLUMN google_synced_at DATETIME"))
    print("Added the Google Calendar columns (existing schedules are unlinked).")


def _canonicalise_timezones() -> int:
    """Rewrite stored zone names the API now spells differently.

    Rows written before the spelling was settled can say ``Asia/Saigon`` where a
    row written today says ``Asia/Ho_Chi_Minh``. It is the same zone, so no
    instant moves — but the name is what the interface compares by when it
    decides whether a schedule is "in another timezone", so one zone under two
    names shows up as two.
    """
    with engine.begin() as conn:
        stored = conn.execute(text("SELECT DISTINCT timezone FROM schedules")).scalars().all()
        renames = {name: timezones.canonical(name) for name in stored}
        rewritten = 0
        for old, new in renames.items():
            if old == new:
                continue
            result = conn.execute(
                text("UPDATE schedules SET timezone = :new WHERE timezone = :old"),
                {"new": new, "old": old},
            )
            rewritten += result.rowcount
            print(f"Renamed timezone {old} -> {new} on {result.rowcount} schedule(s).")
    return rewritten


def _create_missing_indexes() -> None:
    """Add indexes a migrated database would otherwise never get.

    ``ALTER TABLE`` only adds columns, so a database upgraded step by step ended
    up without the index ``create_all`` puts on ``start_time`` — the column every
    conflict check and the listing order rely on.
    """
    with engine.begin() as conn:
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_schedules_start_time ON schedules (start_time)")
        )


def migrate(timezone_name: str) -> int:
    """Apply every pending upgrade. Returns the number of rows converted to UTC."""
    columns = _columns()
    if columns is None:
        print("No 'schedules' table yet; it will be created when the app starts.")
        return 0

    converted = 0
    applied = False
    if "timezone" not in columns:
        converted = _add_timezone_column(timezone_name)
        applied = True
    if "country" not in columns:
        _add_country_column()
        applied = True
    if "reminder_minutes" not in columns:
        _add_reminder_columns()
        applied = True
    if "google_event_id" not in columns:
        _add_google_columns()
        applied = True

    if _canonicalise_timezones():
        applied = True

    indexes_before = _index_names()
    _create_missing_indexes()
    if _index_names() != indexes_before:
        print("Created the missing index on schedules.start_time.")
        applied = True

    if not applied:
        print("Database is already up to date; nothing to do.")
    return converted


def _index_names() -> set[str]:
    inspector = inspect(engine)
    return {index["name"] for index in inspector.get_indexes("schedules")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timezone",
        default=settings.default_timezone,
        help="IANA timezone the existing rows were entered in",
    )
    args = parser.parse_args()
    migrate(args.timezone)


if __name__ == "__main__":
    main()
