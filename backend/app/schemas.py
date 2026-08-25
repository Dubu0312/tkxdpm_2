"""Pydantic request/response schemas.

Time convention
---------------
* **Storage / comparison**: every instant is stored in UTC (see ``app.models``).
* **Input**: ``start_time`` / ``end_time`` accept either an offset-aware ISO-8601
  string (``2026-09-01T09:00:00+07:00``) or a naive one
  (``2026-09-01T09:00:00``). A naive value is read as wall-clock time in the
  request's ``timezone`` field — which is exactly what a browser's
  ``<input type="datetime-local">`` produces. A wall-clock time that a daylight
  saving jump skipped over is refused, not moved (see ``app.timezones``).
* **Output**: *every* datetime belonging to a schedule is rendered in that
  schedule's own timezone, offset always included. One rule with no exceptions:
  the wall-clock time the user typed comes back verbatim, and the bookkeeping
  timestamps beside it — ``notified_at``, ``google_synced_at``, ``created_at``,
  ``updated_at`` — are read against the same clock rather than a second, silent
  one. Each value still names an unambiguous instant, so a client that only
  cares about the instant can ignore the zone entirely.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from app import holiday_calendar, timezones
from app.config import settings
from app.models import reminder_status

# Timezone identity and conversion live in ``app.timezones``; these names keep
# working for the callers that already import them from here.
resolve_timezone = timezones.resolve
to_utc = timezones.to_utc
from_utc = timezones.from_utc


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

    # Declared before the two datetimes on purpose: pydantic validates fields in
    # declaration order, and a wall-clock value cannot be turned into an instant
    # until the zone it was written in is known and valid.
    timezone: str = Field(
        default_factory=lambda: settings.default_timezone,
        min_length=1,
        max_length=64,
        description="IANA timezone name, e.g. 'Asia/Ho_Chi_Minh'",
    )
    start_time: datetime
    end_time: datetime
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
        """Accept any spelling of a real zone, keep the canonical one.

        Clients disagree about what a zone is called — a browser reporting
        ``Asia/Saigon`` and this app's default ``Asia/Ho_Chi_Minh`` name the
        same place — so the spelling is settled here, once, on the way in. Every
        schedule then stores the same name for the same zone whatever created it.
        """
        timezones.resolve(value)
        return timezones.canonical(value)

    @field_validator("start_time", "end_time")
    @classmethod
    def _as_utc(cls, value: datetime, info) -> datetime:
        """Read a wall-clock value in the schedule's zone and store it as UTC."""
        name = info.data.get("timezone")
        if name is None:
            # The zone itself was rejected; that error is the one worth reporting.
            return value
        try:
            return timezones.to_utc(value, timezones.resolve(name), name)
        except timezones.NonexistentLocalTime as error:
            # A typed error rather than a bare message: the frontend can explain
            # the daylight-saving jump in its own words instead of echoing this.
            raise PydanticCustomError(
                "nonexistent_local_time",
                "{reason}",
                {
                    "reason": str(error),
                    "timezone": error.timezone,
                    "local_time": error.value.isoformat(),
                    "gap_minutes": error.gap_minutes,
                    "next_valid": error.shifted.isoformat(),
                },
            ) from None

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
    def _ends_after_it_starts(self):
        # Compared as instants, so an overnight schedule and one crossing a
        # daylight-saving change are both judged by real elapsed time.
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
    #: Instant the reminder fires; null when there is no reminder.
    notify_at: datetime | None
    #: When the reminder was delivered; null while it is still pending.
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
                None if schedule.notified_at is None else from_utc(schedule.notified_at, tz)
            ),
            reminder_status=reminder_status(schedule),
            google_event_id=schedule.google_event_id,
            google_calendar_id=schedule.google_calendar_id,
            google_synced_at=(
                None
                if schedule.google_synced_at is None
                else from_utc(schedule.google_synced_at, tz)
            ),
            google_out_of_date=schedule.google_out_of_date,
            created_at=from_utc(schedule.created_at, tz),
            updated_at=from_utc(schedule.updated_at, tz),
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
    #: All three are rendered in the schedule's own timezone, like ``ScheduleRead``.
    notify_at: datetime
    start_time: datetime
    #: When it was delivered; null while still pending.
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
                None if schedule.notified_at is None else from_utc(schedule.notified_at, tz)
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
    #: Old zone names mapped to the spelling this API stores, so the interface
    #: names a zone the same way the database does without keeping its own copy
    #: of the list (see ``app.timezones``).
    timezone_aliases: dict[str, str]


class GoogleStatusRead(BaseModel):
    """Whether the Google Calendar integration is usable, and how."""

    mode: str
    enabled: bool
    calendar_id: str
    #: Present only when something must be configured before syncing works.
    detail: str | None = None
