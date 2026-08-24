"""Rules the frontend needs to know, served from the one place they are defined."""

from fastapi import APIRouter

from app.config import settings
from app.schemas import LimitsRead

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=LimitsRead)
def read_limits() -> LimitsRead:
    """Duration limits and the default timezone, so nothing is hard-coded client side."""
    return LimitsRead(
        min_duration_minutes=settings.min_duration_minutes,
        max_duration_minutes=settings.max_duration_minutes,
        default_timezone=settings.default_timezone,
    )
