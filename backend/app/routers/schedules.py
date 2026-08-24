"""CRUD endpoints for schedules.

Every datetime crossing this module is UTC: payload values are normalised to UTC
during validation (``app.schemas``), rows store UTC, and responses are rendered
back into each schedule's own timezone by ``ScheduleRead.from_model``.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import google_calendar, holiday_calendar, notifications
from app.config import settings
from app.db import get_session
from app.models import Schedule, preserve_updated_at
from app.schemas import (
    ConflictDetail,
    DurationDetail,
    HolidayDetail,
    HolidayHit,
    ScheduleCreate,
    ScheduleInput,
    ScheduleRead,
    ScheduleUpdate,
)

logger = logging.getLogger("app.schedules")

router = APIRouter(prefix="/api/schedules", tags=["schedules"])

SessionDep = Annotated[Session, Depends(get_session)]


DURATION_RESPONSE = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": DurationDetail,
        "description": "The schedule is shorter or longer than the configured limits",
    }
}

CONFLICT_RESPONSE = {
    status.HTTP_409_CONFLICT: {
        "model": ConflictDetail | HolidayDetail,
        "description": (
            "The time range overlaps an existing schedule, or falls on a public "
            "holiday of the schedule's country"
        ),
    }
}


def _get_or_404(session: Session, schedule_id: int) -> Schedule:
    schedule = session.get(Schedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    return schedule


def find_conflicts(
    session: Session,
    start_time: datetime,
    end_time: datetime,
    exclude_id: int | None = None,
) -> list[Schedule]:
    """Schedules whose time range overlaps [start_time, end_time), all in UTC.

    Two ranges overlap when each one starts before the other ends. Touching
    ranges (one ends exactly when the next begins) are therefore not conflicts.
    ``exclude_id`` keeps a schedule from conflicting with itself while editing.

    Comparing in UTC is what makes this correct across timezones: two schedules
    entered in different zones conflict exactly when their real instants overlap.
    """
    stmt = select(Schedule).where(
        Schedule.start_time < end_time,
        Schedule.end_time > start_time,
    )
    if exclude_id is not None:
        stmt = stmt.where(Schedule.id != exclude_id)
    return list(session.scalars(stmt.order_by(Schedule.start_time, Schedule.id)))


def _reject_conflicts(
    session: Session,
    start_time: datetime,
    end_time: datetime,
    exclude_id: int | None = None,
) -> None:
    """Raise 409 if the given range overlaps an existing schedule."""
    conflicts = find_conflicts(session, start_time, end_time, exclude_id)
    if not conflicts:
        return
    detail = ConflictDetail(
        message=(
            f"Time range overlaps {len(conflicts)} existing "
            f"schedule{'s' if len(conflicts) > 1 else ''}"
        ),
        conflicts=[ScheduleRead.from_model(item) for item in conflicts],
    )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail.model_dump(mode="json"),
    )


def _reject_bad_duration(payload: ScheduleInput) -> None:
    """Raise 422 if the schedule is shorter or longer than the configured limits.

    The length is measured between the two instants, so it is the real elapsed
    time: unaffected by the timezone the schedule was entered in, by running
    past midnight, and correct across a DST change where the wall clock lies.

    The limits themselves live in ``settings`` and are served to the frontend by
    ``GET /api/config`` — they are not written down anywhere else.
    """
    length = payload.end_time - payload.start_time
    low, high = settings.min_duration_minutes, settings.max_duration_minutes
    if timedelta(minutes=low) <= length <= timedelta(minutes=high):
        return

    # Compare the exact interval, not a rounded number of minutes: 14m31s would
    # otherwise round up to 15 and slip past a 15 minute minimum. The reported
    # figure is rounded away from the bound it broke so the message stays true.
    exact = length.total_seconds() / 60
    too_short = length < timedelta(minutes=low)
    minutes = math.floor(exact) if too_short else math.ceil(exact)
    bound = f"below the minimum of {low}" if too_short else f"above the maximum of {high}"
    detail = DurationDetail(
        message=f"Schedule lasts {minutes} minutes, {bound}",
        duration_minutes=minutes,
        min_minutes=low,
        max_minutes=high,
    )
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=detail.model_dump(mode="json"),
    )


def _reject_holidays(payload: ScheduleInput) -> None:
    """Raise 409 if the schedule falls on a public holiday of its country.

    Days are resolved in the schedule's own timezone, so the check matches the
    calendar the user is looking at rather than UTC.
    """
    if payload.country is None:
        return
    start_local, end_local = payload.local_range()
    hits = holiday_calendar.holidays_in_range(payload.country, start_local, end_local)
    if not hits:
        return
    detail = HolidayDetail(
        message=(
            f"{payload.country} observes {len(hits)} public "
            f"holiday{'s' if len(hits) > 1 else ''} in this time range"
        ),
        country=payload.country,
        holidays=[HolidayHit(date=hit.date, name=hit.name) for hit in hits],
    )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail.model_dump(mode="json"),
    )


@router.get("", response_model=list[ScheduleRead])
def list_schedules(session: SessionDep) -> list[ScheduleRead]:
    """Return every schedule, earliest start first (ordered by real instant)."""
    stmt = select(Schedule).order_by(Schedule.start_time, Schedule.id)
    return [ScheduleRead.from_model(item) for item in session.scalars(stmt)]


@router.post(
    "",
    response_model=ScheduleRead,
    status_code=status.HTTP_201_CREATED,
    responses={**CONFLICT_RESPONSE, **DURATION_RESPONSE},
)
def create_schedule(payload: ScheduleCreate, session: SessionDep) -> ScheduleRead:
    _reject_bad_duration(payload)
    _reject_holidays(payload)
    _reject_conflicts(session, payload.start_time, payload.end_time)
    schedule = Schedule(**payload.to_columns())
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return ScheduleRead.from_model(schedule)


@router.get("/{schedule_id}", response_model=ScheduleRead)
def get_schedule(schedule_id: int, session: SessionDep) -> ScheduleRead:
    return ScheduleRead.from_model(_get_or_404(session, schedule_id))


@router.put(
    "/{schedule_id}",
    response_model=ScheduleRead,
    responses={**CONFLICT_RESPONSE, **DURATION_RESPONSE},
)
def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    session: SessionDep,
) -> ScheduleRead:
    schedule = _get_or_404(session, schedule_id)
    _reject_bad_duration(payload)
    _reject_holidays(payload)
    _reject_conflicts(session, payload.start_time, payload.end_time, exclude_id=schedule_id)
    # Compare against the stored values before overwriting them.
    notifications.reset_if_rescheduled(schedule, payload.start_time, payload.reminder_minutes)
    for field, value in payload.to_columns().items():
        setattr(schedule, field, value)
    session.commit()
    session.refresh(schedule)
    _push_google_update(schedule, session)
    return ScheduleRead.from_model(schedule)


def _push_google_update(schedule: Schedule, session: Session) -> None:
    """Keep a linked Google event in step with an edited schedule.

    Only already-linked schedules are pushed — syncing is opt-in per schedule.
    A failure is not fatal: the edit stands and ``google_out_of_date`` turns
    true, so the UI can offer to sync again rather than drifting in silence.
    """
    if not schedule.google_event_id:
        return
    try:
        event_id, synced_at = google_calendar.push(schedule)
    except google_calendar.CalendarUnavailable as error:
        logger.warning("Could not update Google event %s: %s", schedule.google_event_id, error)
        return
    _save_google_link(session, schedule, event_id, synced_at)


def _save_google_link(
    session: Session,
    schedule: Schedule,
    event_id: str | None,
    synced_at: datetime | None,
) -> None:
    """Store the link without counting the sync as a change to the schedule."""
    schedule.google_event_id = event_id
    schedule.google_calendar_id = settings.google_calendar_id if event_id else None
    schedule.google_synced_at = synced_at
    preserve_updated_at(schedule)
    session.commit()
    session.refresh(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: int, session: SessionDep) -> None:
    schedule = _get_or_404(session, schedule_id)
    _remove_google_event(schedule)
    session.delete(schedule)
    session.commit()


def _remove_google_event(schedule: Schedule) -> None:
    """Best-effort removal of the linked Google event.

    A calendar that cannot be reached must not stop someone deleting their own
    schedule, so a failure is logged and the local delete goes ahead. The trade
    off is a possible orphan event on the Google side.
    """
    if not schedule.google_event_id:
        return
    try:
        google_calendar.remove(schedule)
    except google_calendar.CalendarUnavailable as error:
        logger.warning("Could not delete Google event %s: %s", schedule.google_event_id, error)


@router.post("/{schedule_id}/google", response_model=ScheduleRead)
def sync_to_google(schedule_id: int, session: SessionDep) -> ScheduleRead:
    """Create or update this schedule's Google Calendar event.

    Safe to call repeatedly: the event id is derived from the schedule, so a
    second call updates the same event instead of making another one.
    """
    schedule = _get_or_404(session, schedule_id)
    try:
        event_id, synced_at = google_calendar.push(schedule)
    except google_calendar.CalendarUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error

    _save_google_link(session, schedule, event_id, synced_at)
    return ScheduleRead.from_model(schedule)


@router.delete("/{schedule_id}/google", response_model=ScheduleRead)
def unlink_from_google(schedule_id: int, session: SessionDep) -> ScheduleRead:
    """Delete the Google event and forget the link, keeping the schedule."""
    schedule = _get_or_404(session, schedule_id)
    try:
        google_calendar.remove(schedule)
    except google_calendar.CalendarUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error

    _save_google_link(session, schedule, None, None)
    return ScheduleRead.from_model(schedule)
