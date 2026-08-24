"""Countries whose public holidays the app can check against."""

from fastapi import APIRouter

from app import holiday_calendar
from app.schemas import CountryRead

router = APIRouter(prefix="/api/countries", tags=["countries"])


@router.get("", response_model=list[CountryRead])
def list_countries() -> list[CountryRead]:
    """Every supported country, sorted by name — the frontend hard-codes none."""
    return [
        CountryRead(code=country.code, name=country.name)
        for country in holiday_calendar.supported_countries()
    ]
