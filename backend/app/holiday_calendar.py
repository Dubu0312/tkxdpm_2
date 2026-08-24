"""Public-holiday lookup — the single place that knows about holiday data.

Data source: the ``holidays`` package, which computes each country's official
holidays from rules (including moving feasts such as Tết or Easter) rather than
from a hand-maintained table. That keeps this repository free of holiday data,
works offline, and covers any year without a yearly update.

Adding a country is therefore a data question, not a code change: every country
the package supports is offered through ``supported_countries()``.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache

import holidays
from holidays.registry import COUNTRIES


@dataclass(frozen=True)
class Country:
    code: str
    name: str


@dataclass(frozen=True)
class HolidayHit:
    date: date
    name: str


def normalise(code: str) -> str:
    """Country codes are compared and stored upper-case."""
    return code.strip().upper()


@lru_cache(maxsize=1)
def _countries_by_code() -> dict[str, Country]:
    """ISO 3166-1 alpha-2 -> country, built from the package's own registry."""
    countries: dict[str, Country] = {}
    for key, entry in COUNTRIES.items():
        code = entry[1]
        if len(code) == 2:
            countries[code] = Country(code=code, name=key.replace("_", " ").title())
    return countries


def supported_countries() -> list[Country]:
    """Every country holidays can be checked for, sorted by name."""
    return sorted(_countries_by_code().values(), key=lambda country: country.name)


def is_supported(code: str) -> bool:
    return normalise(code) in _countries_by_code()


@lru_cache(maxsize=64)
def _calendar(code: str):
    """Cached holiday calendar; it expands years lazily as they are looked up."""
    return holidays.country_holidays(code)


def holiday_on(code: str, day: date) -> str | None:
    """Name of the official holiday on ``day``, or None."""
    return _calendar(normalise(code)).get(day)


def holidays_in_range(code: str, start_local: datetime, end_local: datetime) -> list[HolidayHit]:
    """Official holidays on the local days a schedule touches.

    The range is half-open — a schedule ending at midnight does not reach into
    the next day — and both bounds must already be expressed in the schedule's
    own timezone, so "which day is it" matches what the user sees.
    """
    first = start_local.date()
    last = max(first, (end_local - timedelta(microseconds=1)).date())

    hits: list[HolidayHit] = []
    day = first
    while day <= last:
        name = holiday_on(code, day)
        if name:
            hits.append(HolidayHit(date=day, name=name))
        day += timedelta(days=1)
    return hits
