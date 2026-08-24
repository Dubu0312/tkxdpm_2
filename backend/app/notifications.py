"""Reminder notifications — the single place that decides when to notify.

A reminder is **derived**, never stored as its own record: a schedule with
``reminder_minutes`` set is due at ``start_time - reminder_minutes``. Because
that is computed from the schedule's instant in UTC, it is correct whatever
timezone the schedule was entered in and however it straddles midnight — the
notification follows the real moment, not the wall clock or the calendar day.

Only ``notified_at`` is stored, so a reminder is not delivered twice.

Delivery here writes a log line: enough to demo and to test, and the one place
to swap for email or push later.
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Schedule, utcnow

logger = logging.getLogger("app.notifications")


def _armed(session: Session) -> list[Schedule]:
    """Schedules with a reminder that has not been delivered yet."""
    stmt = (
        select(Schedule)
        .where(Schedule.reminder_minutes.is_not(None), Schedule.notified_at.is_(None))
        .order_by(Schedule.start_time, Schedule.id)
    )
    return list(session.scalars(stmt))


def pending(session: Session, now: datetime | None = None) -> list[Schedule]:
    """Reminders that can still fire: not sent, and the schedule has not started.

    A reminder whose schedule has already begun is past being useful, so it
    silently drops out instead of firing late. Nothing needs to be cleaned up.
    """
    moment = now or utcnow()
    return [schedule for schedule in _armed(session) if schedule.start_time > moment]


def due(session: Session, now: datetime | None = None) -> list[Schedule]:
    """Reminders whose moment has arrived: ``notify_at <= now < start_time``."""
    moment = now or utcnow()
    return [
        schedule
        for schedule in pending(session, moment)
        if schedule.notify_at is not None and schedule.notify_at <= moment
    ]


def deliver(schedule: Schedule) -> None:
    """Hand one reminder to the notification channel (a log line, for now)."""
    logger.info(
        "Reminder: %r starts at %s UTC (in %s minutes)",
        schedule.title,
        schedule.start_time.isoformat(sep=" ", timespec="seconds"),
        schedule.reminder_minutes,
    )


def dispatch_due(session: Session, now: datetime | None = None) -> list[Schedule]:
    """Deliver every due reminder, mark it sent, and return what went out."""
    moment = now or utcnow()
    delivered = due(session, moment)
    for schedule in delivered:
        deliver(schedule)
        schedule.notified_at = moment
    if delivered:
        session.commit()
    return delivered


def reset_if_rescheduled(schedule: Schedule, start_time: datetime, reminder: int | None) -> None:
    """Re-arm the reminder when an edit moves it; leave it alone otherwise.

    Editing only the title must not resend a reminder that already went out,
    but moving the schedule (or changing the lead time) makes the delivered
    reminder wrong, so that one is armed again for the new moment.
    """
    if schedule.start_time != start_time or schedule.reminder_minutes != reminder:
        schedule.notified_at = None
