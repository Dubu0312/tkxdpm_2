"""ORM models.

Storage convention: ``start_time``, ``end_time``, ``created_at`` and
``updated_at`` are naive datetimes holding **UTC** — SQLite has no timezone-aware
type, so the offset is normalised away on write and re-attached on read. The
schedule's own timezone is kept separately in ``timezone`` (IANA name) so the
wall-clock time the user typed can be reproduced exactly.
"""

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    """Current UTC time as a naive datetime, matching the storage convention."""
    return datetime.now(UTC).replace(tzinfo=None)


class Schedule(Base):
    """A single scheduled entry (an appointment / event)."""

    __tablename__ = "schedules"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_schedules_end_after_start"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    #: Instant the schedule starts, in UTC.
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    #: Instant the schedule ends, in UTC.
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    #: IANA timezone the schedule was entered in, e.g. "Asia/Ho_Chi_Minh".
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )
