"""CRUD endpoints for schedules.

Every datetime crossing this module is UTC: payload values are normalised to UTC
during validation (``app.schemas``), rows store UTC, and responses are rendered
back into each schedule's own timezone by ``ScheduleRead.from_model``.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import holiday_calendar
from app.db import get_session
from app.models import Schedule
from app.schemas import (
    ConflictDetail,
    HolidayDetail,
    HolidayHit,
    ScheduleCreate,
    ScheduleInput,
    ScheduleRead,
    ScheduleUpdate,
)

router = APIRouter(prefix="/api/schedules", tags=["schedules"])

SessionDep = Annotated[Session, Depends(get_session)]


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
    responses=CONFLICT_RESPONSE,
)
def create_schedule(payload: ScheduleCreate, session: SessionDep) -> ScheduleRead:
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


@router.put("/{schedule_id}", response_model=ScheduleRead, responses=CONFLICT_RESPONSE)
def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    session: SessionDep,
) -> ScheduleRead:
    schedule = _get_or_404(session, schedule_id)
    _reject_holidays(payload)
    _reject_conflicts(session, payload.start_time, payload.end_time, exclude_id=schedule_id)
    for field, value in payload.to_columns().items():
        setattr(schedule, field, value)
    session.commit()
    session.refresh(schedule)
    return ScheduleRead.from_model(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: int, session: SessionDep) -> None:
    schedule = _get_or_404(session, schedule_id)
    session.delete(schedule)
    session.commit()
