"""Rules the frontend needs to know, served from the one place they are defined."""

from fastapi import APIRouter

from app import google_calendar, timezones
from app.config import settings
from app.schemas import GoogleStatusRead, LimitsRead

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=LimitsRead)
def read_limits() -> LimitsRead:
    """Duration limits and timezone naming, so nothing is hard-coded client side.

    ``timezone_aliases`` is the backend's table of old zone names, served rather
    than duplicated in the frontend: both sides then agree on what a zone is
    called, which is the only way stored and displayed names can stay the same.
    """
    return LimitsRead(
        min_duration_minutes=settings.min_duration_minutes,
        max_duration_minutes=settings.max_duration_minutes,
        default_timezone=settings.default_timezone,
        timezone_aliases=timezones.RENAMED_ZONES,
    )


@router.get("/google", response_model=GoogleStatusRead)
def google_status() -> GoogleStatusRead:
    """Whether schedules can be synced, so the UI can explain instead of failing."""
    mode = settings.google_calendar_mode
    detail = None
    if mode == "disabled":
        detail = google_calendar.DisabledCalendarClient.MESSAGE
    elif mode == "google" and not settings.google_token_path.exists():
        detail = (
            f"No OAuth token at {settings.google_token_path}. "
            "Run 'python google_auth.py' in the backend directory to authorise."
        )
    elif mode == "memory":
        detail = "Local stand-in mode: events are kept in this process, not in Google Calendar."

    return GoogleStatusRead(
        mode=mode,
        enabled=google_calendar.is_enabled() and (mode != "google" or detail is None),
        calendar_id=settings.google_calendar_id,
        detail=detail,
    )
