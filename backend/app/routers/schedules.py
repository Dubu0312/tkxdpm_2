"""CRUD endpoints for schedules."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Schedule
from app.schemas import ScheduleCreate, ScheduleRead, ScheduleUpdate

router = APIRouter(prefix="/api/schedules", tags=["schedules"])

SessionDep = Annotated[Session, Depends(get_session)]


def _get_or_404(session: Session, schedule_id: int) -> Schedule:
    schedule = session.get(Schedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    return schedule


@router.get("", response_model=list[ScheduleRead])
def list_schedules(session: SessionDep) -> list[Schedule]:
    """Return every schedule, earliest start first."""
    stmt = select(Schedule).order_by(Schedule.start_time, Schedule.id)
    return list(session.scalars(stmt))


@router.post("", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule(payload: ScheduleCreate, session: SessionDep) -> Schedule:
    schedule = Schedule(**payload.model_dump())
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return schedule


@router.get("/{schedule_id}", response_model=ScheduleRead)
def get_schedule(schedule_id: int, session: SessionDep) -> Schedule:
    return _get_or_404(session, schedule_id)


@router.put("/{schedule_id}", response_model=ScheduleRead)
def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    session: SessionDep,
) -> Schedule:
    schedule = _get_or_404(session, schedule_id)
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
