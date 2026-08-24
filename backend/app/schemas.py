"""Pydantic request/response schemas.

Time convention: all datetimes are naive local wall-clock time, matching what the
browser's ``<input type="datetime-local">`` produces. Timezone-aware input is
converted to local time and stripped of its offset so stored values stay
comparable.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _to_naive_local(value: datetime) -> datetime:
    if value.tzinfo is not None:
        value = value.astimezone().replace(tzinfo=None)
    return value


class ScheduleBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=200)
    start_time: datetime
    end_time: datetime

    @field_validator("start_time", "end_time", mode="after")
    @classmethod
    def _normalise_datetime(cls, value: datetime) -> datetime:
        return _to_naive_local(value)

    @model_validator(mode="after")
    def _check_time_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class ScheduleCreate(ScheduleBase):
    """Payload for creating a schedule."""


class ScheduleUpdate(ScheduleBase):
    """Payload for a full update of a schedule."""


class ScheduleRead(ScheduleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ConflictDetail(BaseModel):
    """Body of a 409 response: the schedules the request would overlap with."""

    code: Literal["schedule_conflict"] = "schedule_conflict"
    message: str
    conflicts: list[ScheduleRead]
