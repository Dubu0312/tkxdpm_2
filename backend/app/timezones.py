"""Timezone identity and conversion — the one place both are decided.

Two separate jobs live here because both are about "which instant is this,
really", and splitting them was what let the two bugs in Round 12 appear.

**Identity.** An IANA zone can have more than one name: ``Asia/Saigon`` and
``Asia/Ho_Chi_Minh`` are the same rules under two spellings. Different runtimes
disagree about which spelling is canonical — this project's browser reports
``Asia/Saigon``, Python's ``zoneinfo`` and the IANA database call it
``Asia/Ho_Chi_Minh`` — so a schedule's timezone was stored differently depending
on where it came from. ``canonical`` settles it: the backend picks the name, on
the way in, for every schedule regardless of the client. The table is served to
the frontend by ``GET /api/config`` so the interface spells zones the same way
rather than keeping a second copy of this list.

**Conversion.** A wall-clock time plus a zone is not always one instant, and
sometimes it is none at all. ``to_utc`` refuses the "none at all" case instead of
quietly moving the schedule (see ``NonexistentLocalTime``).
"""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

#: Zone names that the IANA database keeps only for backwards compatibility,
#: mapped to the name it prefers today.
#:
#: Every entry is a *rename of the same place* — a respelling
#: (``Asia/Calcutta`` → ``Asia/Kolkata``), a city renamed (``Europe/Kiev`` →
#: ``Europe/Kyiv``), or a move into a sub-region (``America/Jujuy`` →
#: ``America/Argentina/Jujuy``). Links that merge *different* places which
#: happen to share rules are deliberately left out: ``Europe/Vatican`` points at
#: ``Europe/Rome`` in the database, but rewriting a user's Vatican schedule to
#: say Rome would be changing what they told us, not tidying a spelling.
#:
#: To extend: check that the two names really are the same location, that both
#: resolve (``test_canonical_timezone`` enforces this), then add the pair.
RENAMED_ZONES: dict[str, str] = {
    "Africa/Asmera": "Africa/Asmara",
    "America/Buenos_Aires": "America/Argentina/Buenos_Aires",
    "America/Catamarca": "America/Argentina/Catamarca",
    "America/Coral_Harbour": "America/Atikokan",
    "America/Cordoba": "America/Argentina/Cordoba",
    "America/Godthab": "America/Nuuk",
    "America/Indianapolis": "America/Indiana/Indianapolis",
    "America/Jujuy": "America/Argentina/Jujuy",
    "America/Louisville": "America/Kentucky/Louisville",
    "America/Mendoza": "America/Argentina/Mendoza",
    "Asia/Calcutta": "Asia/Kolkata",
    "Asia/Katmandu": "Asia/Kathmandu",
    "Asia/Rangoon": "Asia/Yangon",
    "Asia/Saigon": "Asia/Ho_Chi_Minh",
    "Atlantic/Faeroe": "Atlantic/Faroe",
    "Europe/Kiev": "Europe/Kyiv",
    "Pacific/Enderbury": "Pacific/Kanton",
    "Pacific/Ponape": "Pacific/Pohnpei",
    "Pacific/Truk": "Pacific/Chuuk",
}


def canonical(name: str) -> str:
    """The preferred spelling of ``name``, unchanged if it has only one.

    Comparing or storing canonical names is what keeps one zone from appearing
    as two. An unknown name is returned as given — deciding whether it is a real
    zone is ``resolve``'s job, and reporting "unknown timezone" is clearer than
    reporting it under a name the caller never used.
    """
    return RENAMED_ZONES.get(name, name)


def resolve(name: str) -> ZoneInfo:
    """Return the timezone called ``name``, or raise ValueError."""
    try:
        return ZoneInfo(canonical(name))
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError(f"Unknown timezone: {name!r}") from None


class NonexistentLocalTime(ValueError):
    """A wall-clock time that a daylight-saving jump skipped over.

    When the clocks go forward, the local times inside the jump never happen:
    in ``America/New_York`` on 2026-03-08 the clock goes straight from 02:00 to
    03:00, so 02:30 is not a time that exists there. Python will happily
    interpret it anyway and land on 03:30 — an instant an hour away from the one
    the user meant, which silently changes both the start of the schedule and
    its duration. Refusing is the honest answer: only the user can say whether
    they meant before the jump or after it.
    """

    def __init__(self, value: datetime, timezone: str, shifted: datetime, gap: timedelta) -> None:
        self.value = value
        self.timezone = timezone
        #: What the value would silently have become — a time that does exist.
        self.shifted = shifted
        self.gap_minutes = round(gap.total_seconds() / 60)
        super().__init__(
            f"{value.isoformat()} does not exist in {timezone}: the clock jumps "
            f"{self.gap_minutes} minutes forward for daylight saving time. "
            f"Pick a time before the jump, or from {shifted.isoformat()} onwards."
        )


def _skipped(value: datetime, tz: ZoneInfo) -> datetime | None:
    """The time ``value`` would turn into if it does not exist in ``tz``.

    A wall-clock time exists exactly when converting it to UTC and back gives it
    again. Inside a forward jump the round trip lands somewhere else, which is
    both the test and the suggestion to offer. Ambiguous times (the hour a
    backward jump repeats) do round-trip, so they are not caught here.
    """
    landed = value.replace(tzinfo=tz).astimezone(UTC).astimezone(tz).replace(tzinfo=None)
    return None if landed == value else landed


def to_utc(value: datetime, tz: ZoneInfo, timezone_name: str | None = None) -> datetime:
    """Convert an aware or naive datetime to a naive UTC datetime.

    A naive value is read as wall-clock time in ``tz``, and is rejected with
    ``NonexistentLocalTime`` if no such moment exists there. An hour repeated by
    a backward jump is accepted as its *first* occurrence, matching what a
    calendar shows when you scroll through that day; the offset in the response
    says which one was chosen.
    """
    if value.tzinfo is None:
        landed = _skipped(value, tz)
        if landed is not None:
            name = timezone_name or str(tz)
            gap = landed - value
            raise NonexistentLocalTime(value, name, landed, gap)
        value = value.replace(tzinfo=tz)
    return value.astimezone(UTC).replace(tzinfo=None)


def from_utc(value: datetime, tz: ZoneInfo) -> datetime:
    """Attach UTC to a stored naive datetime and convert it into ``tz``."""
    return value.replace(tzinfo=UTC).astimezone(tz)
