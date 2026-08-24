"""Google Calendar integration — the single place that knows about Google.

Three modes, chosen with ``GOOGLE_CALENDAR_MODE``:

``disabled`` (default)
    No integration. The app runs normally and the sync endpoints report that it
    is not configured, so a checkout without credentials still works.
``memory``
    A local stand-in that behaves like the API (insert / update / delete, same
    duplicate rules) but keeps events in this process. It exists so the whole
    flow can be demoed and tested without credentials. It is **not** real sync.
``google``
    The real API, using OAuth credentials from disk.

Linking and duplicates
----------------------
Each schedule stores the id of its Google event. Syncing an already-linked
schedule updates that event instead of inserting a new one. On top of that the
event id is *derived from the schedule id*, so even a sync that has lost its
link cannot create a second event: the insert collides and is turned into an
update. Both directions are covered — a lost link, and an event deleted on the
Google side (which is re-created).

Times
-----
Start and end are sent as an ISO string with an explicit offset **plus** the
IANA zone name, exactly as the API renders them. Google therefore receives both
the real instant and the timezone the schedule was entered in.
"""

import logging
from datetime import datetime
from typing import Protocol

from app.config import settings
from app.models import Schedule, utcnow
from app.schemas import ScheduleRead

logger = logging.getLogger("app.google_calendar")

#: Google event ids may only use base32hex characters (0-9 and a-v).
_ID_ALPHABET = set("0123456789abcdefghijklmnopqrstuv")


class CalendarUnavailable(RuntimeError):
    """The integration is off, misconfigured, or the API could not be reached."""


class EventNotFound(LookupError):
    """The event is no longer on the Google side."""


class EventAlreadyExists(RuntimeError):
    """An event with this id already exists — the duplicate guard fired."""


class CalendarClient(Protocol):
    """The slice of Google Calendar this app uses."""

    def insert(self, calendar_id: str, event_id: str, body: dict) -> str: ...

    def update(self, calendar_id: str, event_id: str, body: dict) -> str: ...

    def delete(self, calendar_id: str, event_id: str) -> None: ...


class InMemoryCalendarClient:
    """A local stand-in with the same duplicate rules as the real API."""

    def __init__(self) -> None:
        self.events: dict[tuple[str, str], dict] = {}

    def insert(self, calendar_id: str, event_id: str, body: dict) -> str:
        if (calendar_id, event_id) in self.events:
            raise EventAlreadyExists(event_id)
        self.events[(calendar_id, event_id)] = dict(body)
        return event_id

    def update(self, calendar_id: str, event_id: str, body: dict) -> str:
        if (calendar_id, event_id) not in self.events:
            raise EventNotFound(event_id)
        self.events[(calendar_id, event_id)] = dict(body)
        return event_id

    def delete(self, calendar_id: str, event_id: str) -> None:
        if self.events.pop((calendar_id, event_id), None) is None:
            raise EventNotFound(event_id)


class GoogleApiCalendarClient:
    """The real client. Credentials are read from disk and never committed."""

    SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

    def __init__(self) -> None:
        self._service = None

    def _build(self):
        """Load stored OAuth credentials and build the API service."""
        # Imported lazily so the app still starts without the Google libraries.
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        token_path = settings.google_token_path
        if not token_path.exists():
            raise CalendarUnavailable(
                f"No OAuth token at {token_path}. Run 'python google_auth.py' first."
            )

        credentials = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)
        if not credentials.valid:
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                token_path.write_text(credentials.to_json())
            else:
                raise CalendarUnavailable("Stored OAuth token is invalid; re-run google_auth.py")
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)

    @property
    def service(self):
        if self._service is None:
            self._service = self._build()
        return self._service

    def _call(self, request):
        from googleapiclient.errors import HttpError

        try:
            return request.execute()
        except HttpError as error:  # pragma: no cover - needs the real API
            status = getattr(error.resp, "status", None)
            if status == 404:
                raise EventNotFound(str(error)) from error
            if status == 409:
                raise EventAlreadyExists(str(error)) from error
            raise CalendarUnavailable(str(error)) from error

    def insert(self, calendar_id: str, event_id: str, body: dict) -> str:  # pragma: no cover
        payload = {**body, "id": event_id}
        created = self._call(self.service.events().insert(calendarId=calendar_id, body=payload))
        return created["id"]

    def update(self, calendar_id: str, event_id: str, body: dict) -> str:  # pragma: no cover
        updated = self._call(
            self.service.events().update(calendarId=calendar_id, eventId=event_id, body=body)
        )
        return updated["id"]

    def delete(self, calendar_id: str, event_id: str) -> None:  # pragma: no cover
        self._call(self.service.events().delete(calendarId=calendar_id, eventId=event_id))


class DisabledCalendarClient:
    """Refuses every call with the same clear message."""

    MESSAGE = (
        "Google Calendar integration is disabled. Set GOOGLE_CALENDAR_MODE and the "
        "credential paths (see README) to turn it on."
    )

    def insert(self, calendar_id: str, event_id: str, body: dict) -> str:
        raise CalendarUnavailable(self.MESSAGE)

    def update(self, calendar_id: str, event_id: str, body: dict) -> str:
        raise CalendarUnavailable(self.MESSAGE)

    def delete(self, calendar_id: str, event_id: str) -> None:
        raise CalendarUnavailable(self.MESSAGE)


_client: CalendarClient | None = None


def get_client() -> CalendarClient:
    """The client for the configured mode, built once per process."""
    global _client
    if _client is None:
        if settings.google_calendar_mode == "google":
            _client = GoogleApiCalendarClient()
        elif settings.google_calendar_mode == "memory":
            _client = InMemoryCalendarClient()
        else:
            _client = DisabledCalendarClient()
    return _client


def reset_client() -> None:
    """Drop the cached client (used by tests and after re-configuring)."""
    global _client
    _client = None


def is_enabled() -> bool:
    return settings.google_calendar_mode in {"memory", "google"}


def event_id_for(schedule: Schedule) -> str:
    """A stable Google event id for this schedule.

    Deriving it from the schedule id is what makes syncing idempotent: the same
    schedule always maps to the same event, so a repeated sync can never create
    a second one.
    """
    candidate = f"{settings.google_event_id_prefix}{schedule.id}".lower()
    if not set(candidate) <= _ID_ALPHABET or len(candidate) < 5:
        raise ValueError(
            f"GOOGLE_EVENT_ID_PREFIX must make a valid Google event id (0-9, a-v, "
            f"at least 5 characters); got {candidate!r}"
        )
    return candidate


def event_body(schedule: Schedule) -> dict:
    """The Google event payload for a schedule.

    ``dateTime`` carries the instant (offset included) and ``timeZone`` carries
    the zone the schedule was entered in, so neither is lost in translation.
    """
    view = ScheduleRead.from_model(schedule)
    body = {
        "summary": schedule.title,
        "start": {"dateTime": view.start_time.isoformat(), "timeZone": schedule.timezone},
        "end": {"dateTime": view.end_time.isoformat(), "timeZone": schedule.timezone},
    }
    if schedule.description:
        body["description"] = schedule.description
    if schedule.location:
        body["location"] = schedule.location
    if schedule.reminder_minutes is not None:
        body["reminders"] = {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": schedule.reminder_minutes}],
        }
    return body


def push(schedule: Schedule) -> tuple[str, datetime]:
    """Create or update the Google event for a schedule; returns (event_id, when).

    This is the only place events are written, so the duplicate rules live in
    one function rather than being repeated per call site.
    """
    if not is_enabled():
        raise CalendarUnavailable(DisabledCalendarClient.MESSAGE)

    client = get_client()
    calendar_id = settings.google_calendar_id
    body = event_body(schedule)
    event_id = schedule.google_event_id or event_id_for(schedule)

    if schedule.google_event_id:
        try:
            client.update(calendar_id, event_id, body)
        except EventNotFound:
            # Removed on the Google side: put it back rather than losing the link.
            logger.info("Event %s missing on Google; recreating it", event_id)
            client.insert(calendar_id, event_id, body)
    else:
        try:
            client.insert(calendar_id, event_id, body)
        except EventAlreadyExists:
            # A previous sync created it and we lost the link: adopt it.
            logger.info("Event %s already exists; updating instead of duplicating", event_id)
            client.update(calendar_id, event_id, body)

    return event_id, utcnow()


def remove(schedule: Schedule) -> None:
    """Delete the Google event for a schedule. Already gone counts as done."""
    if not schedule.google_event_id:
        return
    if not is_enabled():
        raise CalendarUnavailable(DisabledCalendarClient.MESSAGE)
    try:
        get_client().delete(settings.google_calendar_id, schedule.google_event_id)
    except EventNotFound:
        logger.info("Event %s already gone on Google", schedule.google_event_id)
