"""One-off migration to the timezone-aware schema (Round 2 -> Round 3).

Databases created before timezone support store naive *local* datetimes and have
no ``timezone`` column. This script adds the column and rewrites the stored
instants as UTC. It is idempotent: running it on an up-to-date database is a
no-op.

    python migrate.py [--timezone Asia/Ho_Chi_Minh]

``--timezone`` is the zone the existing rows were entered in; it defaults to
``DEFAULT_TIMEZONE`` from the environment.

This is a deliberate stopgap for a single schema change — reach for Alembic once
migrations become routine.
"""

import argparse
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import inspect, text

from app.config import settings
from app.db import engine

TIMESTAMP_COLUMNS = ("start_time", "end_time", "created_at", "updated_at")


def _needs_migration() -> bool:
    inspector = inspect(engine)
    if "schedules" not in inspector.get_table_names():
        return False
    return "timezone" not in {column["name"] for column in inspector.get_columns("schedules")}


def _local_to_utc(value: str, tz: ZoneInfo) -> str:
    parsed = datetime.fromisoformat(value).replace(tzinfo=tz)
    return parsed.astimezone(UTC).replace(tzinfo=None).isoformat(sep=" ")


def migrate(timezone_name: str) -> int:
    """Return the number of rows converted (0 when already migrated)."""
    if not _needs_migration():
        print("Database already uses the timezone-aware schema; nothing to do.")
        return 0

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
