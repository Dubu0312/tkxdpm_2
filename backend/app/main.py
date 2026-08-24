"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import check_connection, init_db
from app.routers import countries, schedules


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


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
