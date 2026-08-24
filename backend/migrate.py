"""Bring an existing database up to the current schema.

Two upgrades are handled, both idempotent — running this on an up-to-date
database is a no-op:

1. **Timezone support** (Round 3): databases created earlier store naive *local*
   datetimes and have no ``timezone`` column. The column is added and the stored
   instants are rewritten as UTC.
2. **Holiday validation** (Round 4): adds the nullable ``country`` column.

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

    if not applied:
        print("Database is already up to date; nothing to do.")
    return converted


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
