"""FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import notifications
from app.config import settings
from app.db import SessionLocal, check_connection, init_db
from app.routers import countries, schedules
from app.routers import notifications as notifications_router

logger = logging.getLogger("app")


def _configure_logging() -> None:
    """Make the app's own INFO logs visible however the server was started.

    Uvicorn only configures its own loggers, so without this a delivered
    reminder would be logged into a void — which is exactly the thing this
    feature is supposed to show.
    """
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s - %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


async def _reminder_poller(interval: int) -> None:
    """Deliver due reminders every `interval` seconds until cancelled."""
    logger.info("Reminder poller started (every %ss)", interval)
    while True:
        await asyncio.sleep(interval)
        try:
            with SessionLocal() as session:
                await asyncio.to_thread(notifications.dispatch_due, session)
        except Exception:  # pragma: no cover - a bad tick must not kill the loop
            logger.exception("Reminder dispatch failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    init_db()

    poller = None
    if settings.notifications_enabled and settings.notification_poll_seconds > 0:
        poller = asyncio.create_task(_reminder_poller(settings.notification_poll_seconds))

    yield

    if poller is not None:
        poller.cancel()
        with suppress(asyncio.CancelledError):
            await poller


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(schedules.router)
app.include_router(countries.router)
app.include_router(notifications_router.router)


@app.get("/")
def root() -> dict:
    return {"app": settings.app_name, "environment": settings.environment}


@app.get("/health")
def health() -> dict:
    try:
        database_ok = check_connection()
        detail = None
    except Exception as exc:  # pragma: no cover - surfaced through the response
        database_ok = False
        detail = str(exc)
    return {
        "status": "ok" if database_ok else "degraded",
        "database": "ok" if database_ok else "error",
        "detail": detail,
    }
