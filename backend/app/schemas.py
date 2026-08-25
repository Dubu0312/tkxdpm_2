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
from app.models import reminder_status


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

    @field_validator("title", mode="before")
    @classmethod
    def _trim_title(cls, value):
        """Trim before validating, so the length rules apply to the real title.

        Runs *before* the constraints on purpose: a title of only spaces then
        fails ``min_length`` instead of being stored as blank, and one that is
        200 characters plus surrounding spaces is no longer rejected for a
        length the user did not type. The limits themselves are unchanged, and
        both create and update inherit this because both extend this class.
        """
        return value.strip() if isinstance(value, str) else value


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
    reminder_minutes: int | None = Field(
        default=None,
        ge=1,
        le=40320,  # four weeks
        description="Minutes before the start to send a reminder; omit for none",
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
    reminder_minutes: int | None
    #: Instant the reminder fires, rendered in the schedule's timezone.
    notify_at: datetime | None
    #: When the reminder was delivered (UTC); null while it is still pending.
    notified_at: datetime | None
    #: What became of the reminder: none / scheduled / sent / missed.
    reminder_status: Literal["none", "scheduled", "sent", "missed"]
    #: Linked Google Calendar event, if the schedule has been synced.
    google_event_id: str | None
    google_calendar_id: str | None
    google_synced_at: datetime | None
    #: True when the schedule changed after its last successful push.
    google_out_of_date: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer(
        "start_time",
        "end_time",
        "notify_at",
        "notified_at",
        "google_synced_at",
        "created_at",
        "updated_at",
    )
    def _explicit_offset(self, value: datetime | None) -> str | None:
        """Render every instant with a numeric offset, never the bare "Z" form."""
        return None if value is None else value.isoformat()

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
            reminder_minutes=schedule.reminder_minutes,
            start_time=from_utc(schedule.start_time, tz),
            end_time=from_utc(schedule.end_time, tz),
            notify_at=None if schedule.notify_at is None else from_utc(schedule.notify_at, tz),
            notified_at=(
                None if schedule.notified_at is None else schedule.notified_at.replace(tzinfo=UTC)
            ),
            reminder_status=reminder_status(schedule),
            google_event_id=schedule.google_event_id,
            google_calendar_id=schedule.google_calendar_id,
            google_synced_at=(
                None
                if schedule.google_synced_at is None
                else schedule.google_synced_at.replace(tzinfo=UTC)
            ),
            google_out_of_date=schedule.google_out_of_date,
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


class NotificationRead(BaseModel):
    """A reminder, identified by the schedule it belongs to.

    There is no notification record of its own — ``notify_at`` is derived from
    the schedule, so this view is always consistent with it.
    """

    schedule_id: int
    title: str
    timezone: str
    reminder_minutes: int
    #: Instant the reminder fires and the schedule starts, in its own timezone.
    notify_at: datetime
    start_time: datetime
    #: When it was delivered (UTC); null while still pending.
    notified_at: datetime | None

    @field_serializer("notify_at", "start_time", "notified_at")
    def _explicit_offset(self, value: datetime | None) -> str | None:
        return None if value is None else value.isoformat()

    @classmethod
    def from_model(cls, schedule) -> "NotificationRead":
        tz = resolve_timezone(schedule.timezone)
        return cls(
            schedule_id=schedule.id,
            title=schedule.title,
            timezone=schedule.timezone,
            reminder_minutes=schedule.reminder_minutes,
            notify_at=from_utc(schedule.notify_at, tz),
            start_time=from_utc(schedule.start_time, tz),
            notified_at=(
                None if schedule.notified_at is None else schedule.notified_at.replace(tzinfo=UTC)
            ),
        )


class DurationDetail(BaseModel):
    """Body of a 422 response: the schedule is too short or too long."""

    code: Literal["duration_out_of_range"] = "duration_out_of_range"
    message: str
    duration_minutes: int
    min_minutes: int
    max_minutes: int


class LimitsRead(BaseModel):
    """Rules the frontend needs to know about, served rather than hard-coded."""

    min_duration_minutes: int
    max_duration_minutes: int
    default_timezone: str


class GoogleStatusRead(BaseModel):
    """Whether the Google Calendar integration is usable, and how."""

    mode: str
    enabled: bool
    calendar_id: str
    #: Present only when something must be configured before syncing works.
    detail: str | None = None
