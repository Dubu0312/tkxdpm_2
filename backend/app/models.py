"""ORM models.

Storage convention: ``start_time``, ``end_time``, ``created_at`` and
``updated_at`` are naive datetimes holding **UTC** — SQLite has no timezone-aware
type, so the offset is normalised away on write and re-attached on read. The
schedule's own timezone is kept separately in ``timezone`` (IANA name) so the
wall-clock time the user typed can be reproduced exactly.
"""

from datetime import UTC, datetime, timedelta

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
    #: ISO 3166-1 alpha-2 country whose public holidays apply; None = no check.
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    #: Minutes before the start to send a reminder; None = no reminder.
    reminder_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: When the reminder was actually delivered (UTC); None = not sent yet.
    notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    #: Id of the linked Google Calendar event; None = never synced.
    google_event_id: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    #: Calendar the event lives in (Google allows more than one).
    google_calendar_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    #: Last successful push to Google (UTC).
    google_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    @property
    def notify_at(self) -> datetime | None:
        """Instant the reminder is due (UTC), derived from the start time.

        Deriving rather than storing it is what keeps reminders honest: editing
        the schedule moves the reminder with it, and deleting the schedule takes
        the reminder with it. There is nothing to keep in sync.
        """
        if self.reminder_minutes is None:
            return None
        return self.start_time - timedelta(minutes=self.reminder_minutes)

    @property
    def google_out_of_date(self) -> bool:
        """True when the schedule changed after its last push to Google.

        Lets the UI say "needs re-syncing" instead of quietly drifting when a
        push fails.
        """
        if self.google_event_id is None or self.google_synced_at is None:
            return False
        return self.updated_at > self.google_synced_at
