"""CRUD endpoints for schedules."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Schedule
from app.schemas import ConflictDetail, ScheduleCreate, ScheduleRead, ScheduleUpdate

router = APIRouter(prefix="/api/schedules", tags=["schedules"])

SessionDep = Annotated[Session, Depends(get_session)]


CONFLICT_RESPONSE = {
    status.HTTP_409_CONFLICT: {
        "model": ConflictDetail,
        "description": "The time range overlaps one or more existing schedules",
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
    """Schedules whose time range overlaps [start_time, end_time).

    Two ranges overlap when each one starts before the other ends. Touching
    ranges (one ends exactly when the next begins) are therefore not conflicts.
    ``exclude_id`` keeps a schedule from conflicting with itself while editing.
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
        conflicts=[ScheduleRead.model_validate(item) for item in conflicts],
    )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail.model_dump(mode="json"),
    )


@router.get("", response_model=list[ScheduleRead])
def list_schedules(session: SessionDep) -> list[Schedule]:
    """Return every schedule, earliest start first."""
    stmt = select(Schedule).order_by(Schedule.start_time, Schedule.id)
    return list(session.scalars(stmt))


@router.post(
    "",
    response_model=ScheduleRead,
    status_code=status.HTTP_201_CREATED,
    responses=CONFLICT_RESPONSE,
)
def create_schedule(payload: ScheduleCreate, session: SessionDep) -> Schedule:
    _reject_conflicts(session, payload.start_time, payload.end_time)
    schedule = Schedule(**payload.model_dump())
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return schedule


@router.get("/{schedule_id}", response_model=ScheduleRead)
def get_schedule(schedule_id: int, session: SessionDep) -> Schedule:
    return _get_or_404(session, schedule_id)


@router.put("/{schedule_id}", response_model=ScheduleRead, responses=CONFLICT_RESPONSE)
def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    session: SessionDep,
) -> Schedule:
    schedule = _get_or_404(session, schedule_id)
    _reject_conflicts(session, payload.start_time, payload.end_time, exclude_id=schedule_id)
    for field, value in payload.model_dump().items():
        setattr(schedule, field, value)
    session.commit()
    session.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: int, session: SessionDep) -> None:
    schedule = _get_or_404(session, schedule_id)
    session.delete(schedule)
    session.commit()
