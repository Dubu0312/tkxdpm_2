"""Inspecting and dispatching schedule reminders."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import notifications
from app.db import get_session
from app.schemas import NotificationRead

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[NotificationRead])
def list_pending(session: SessionDep) -> list[NotificationRead]:
    """Reminders that can still fire, earliest schedule first."""
    return [NotificationRead.from_model(item) for item in notifications.pending(session)]


@router.get("/due", response_model=list[NotificationRead])
def list_due(session: SessionDep) -> list[NotificationRead]:
    """Reminders whose moment has arrived but which have not been sent yet."""
    return [NotificationRead.from_model(item) for item in notifications.due(session)]


@router.post("/dispatch", response_model=list[NotificationRead])
def dispatch(session: SessionDep) -> list[NotificationRead]:
    """Send every due reminder now and return what went out.

    The background poller calls the same function; this endpoint exists so a
    demo does not have to wait for the next tick.
    """
    return [NotificationRead.from_model(item) for item in notifications.dispatch_due(session)]
