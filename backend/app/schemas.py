"""Pydantic request/response schemas.

Time convention
---------------
* **Storage / comparison**: every instant is stored in UTC (see ``app.models``).
* **Input**: ``start_time`` / ``end_time`` accept either an offset-aware ISO-8601
  string (``2026-09-01T09:00:00+07:00``) or a naive one
  (``2026-09-01T09:00:00``). A naive value is read as wall-clock time in the
  request's ``timezone`` field — which is exactly what a browser's
  ``<input type="datetime-local">`` produces.
* **Output**: instants are rendered in the schedule's own timezone, offset
  included, so the wall-clock time the user typed is preserved verbatim;
  ``created_at`` / ``updated_at`` are rendered in UTC.
"""

from datetime import UTC, date, datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app import holiday_calendar
from app.config import settings


def resolve_timezone(name: str) -> ZoneInfo:
    """Return the IANA timezone called ``name``, or raise ValueError."""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError(f"Unknown timezone: {name!r}") from None


def to_utc(value: datetime, tz: ZoneInfo) -> datetime:
    """Convert an aware or naive datetime to a naive UTC datetime.

    A naive value is interpreted as wall-clock time in ``tz``.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=tz)
    return value.astimezone(UTC).replace(tzinfo=None)


def from_utc(value: datetime, tz: ZoneInfo) -> datetime:
    """Attach UTC to a stored naive datetime and convert it into ``tz``."""
    return value.replace(tzinfo=UTC).astimezone(tz)


class ScheduleFields(BaseModel):
    """Fields that carry no timezone semantics."""

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=200)


class ScheduleInput(ScheduleFields):
    """Incoming payload. Datetimes are normalised to UTC during validation."""

    start_time: datetime
    end_time: datetime
    timezone: str = Field(
        default_factory=lambda: settings.default_timezone,
        min_length=1,
        max_length=64,
        description="IANA timezone name, e.g. 'Asia/Ho_Chi_Minh'",
    )
    country: str | None = Field(
        default=None,
        max_length=2,
        description="ISO 3166-1 alpha-2 country whose public holidays apply",
    )

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        resolve_timezone(value)
        return value

    @field_validator("country")
    @classmethod
    def _known_country(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        code = holiday_calendar.normalise(value)
        if not holiday_calendar.is_supported(code):
            raise ValueError(f"Unknown country: {value!r}")
        return code

    def local_range(self) -> tuple[datetime, datetime]:
        """Start and end as aware datetimes in the schedule's own timezone."""
        tz = resolve_timezone(self.timezone)
        return from_utc(self.start_time, tz), from_utc(self.end_time, tz)

    @model_validator(mode="after")
    def _normalise(self):
        tz = resolve_timezone(self.timezone)
        self.start_time = to_utc(self.start_time, tz)
        self.end_time = to_utc(self.end_time, tz)
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self

    def to_columns(self) -> dict:
        """Values ready to be written to a ``Schedule`` row (start/end in UTC)."""
        return self.model_dump()


class ScheduleCreate(ScheduleInput):
    """Payload for creating a schedule."""


class ScheduleUpdate(ScheduleInput):
    """Payload for a full update of a schedule."""


class ScheduleRead(ScheduleFields):
    """Outgoing representation: start/end rendered in the schedule's timezone."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    start_time: datetime
    end_time: datetime
    timezone: str
    country: str | None
    created_at: datetime
    updated_at: datetime

    @field_serializer("start_time", "end_time", "created_at", "updated_at")
    def _explicit_offset(self, value: datetime) -> str:
        """Render every instant with a numeric offset, never the bare "Z" form."""
        return value.isoformat()

    @classmethod
    def from_model(cls, schedule) -> "ScheduleRead":
        tz = resolve_timezone(schedule.timezone)
        return cls(
            id=schedule.id,
            title=schedule.title,
            description=schedule.description,
            location=schedule.location,
            timezone=schedule.timezone,
            country=schedule.country,
            start_time=from_utc(schedule.start_time, tz),
            end_time=from_utc(schedule.end_time, tz),
            created_at=schedule.created_at.replace(tzinfo=UTC),
            updated_at=schedule.updated_at.replace(tzinfo=UTC),
        )


class ConflictDetail(BaseModel):
    """Body of a 409 response: the schedules the request would overlap with."""

    code: Literal["schedule_conflict"] = "schedule_conflict"
    message: str
    conflicts: list[ScheduleRead]


class HolidayHit(BaseModel):
    """One official holiday a schedule would fall on."""

    date: date
    name: str


class HolidayDetail(BaseModel):
    """Body of a 409 response: the schedule falls on a public holiday."""

    code: Literal["holiday_conflict"] = "holiday_conflict"
    message: str
    country: str
    holidays: list[HolidayHit]


class CountryRead(BaseModel):
    """A country whose public holidays can be checked."""

    code: str
    name: str
