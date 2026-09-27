"""Shared dashboard display-time helpers.

The dashboard family stores both calendar dates and UTC-backed freshness
timestamps. Calendar dates are already product truth; timestamps are converted
to the operator's San Francisco working day.

Invariants:
- input values remain source tokens; this helper does not change stored
  contracts or rewrite source files.
- plain `YYYY-MM-DD` values remain the same calendar date in every timezone.
- timestamps are interpreted as UTC when no offset is present, then converted.
- invalid or empty values fail calmly by returning the caller-provided default.
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

DASHBOARD_DISPLAY_TIMEZONE = "America/Los_Angeles"
_DASHBOARD_DISPLAY_TZ = ZoneInfo(DASHBOARD_DISPLAY_TIMEZONE)


def _calendar_date_token(value: object) -> dt.date | None:
    raw = str(value or "").strip()
    try:
        parsed = dt.date.fromisoformat(raw)
    except ValueError:
        return None
    return parsed if raw == parsed.isoformat() else None


def parse_utc_token(value: object) -> dt.datetime | None:
    """Parse a UTC-backed dashboard token into an aware UTC datetime.

    Accepted inputs:
    - `YYYY-MM-DD` date buckets, interpreted as `00:00:00Z`
    - ISO timestamps with `Z` or explicit offsets
    - naive `YYYY-MM-DD HH:MM[:SS[.ffffff]]` / `T` variants, interpreted as UTC
    """

    raw = str(value or "").strip()
    if not raw:
        return None

    candidate = raw.replace(" ", "T")
    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"

    try:
        parsed = dt.datetime.fromisoformat(candidate)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def pacific_display_date_from_utc_token(value: object, *, default: str = "") -> str:
    """Return a calendar date unchanged or convert a timestamp to Pacific."""

    calendar_date = _calendar_date_token(value)
    if calendar_date is not None:
        return calendar_date.isoformat()

    parsed = parse_utc_token(value)
    if parsed is None:
        return default
    return parsed.astimezone(_DASHBOARD_DISPLAY_TZ).date().isoformat()


def pacific_date_from_utc_token(value: object) -> dt.date | None:
    """Return a calendar date unchanged or convert a timestamp to Pacific."""

    calendar_date = _calendar_date_token(value)
    if calendar_date is not None:
        return calendar_date

    parsed = parse_utc_token(value)
    if parsed is None:
        return None
    return parsed.astimezone(_DASHBOARD_DISPLAY_TZ).date()


def dashboard_display_today(*, now: dt.datetime | None = None) -> dt.date:
    """Return today's date in the dashboard display timezone."""

    current = now or dt.datetime.now(dt.timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=dt.timezone.utc)
    return current.astimezone(_DASHBOARD_DISPLAY_TZ).date()


__all__ = [
    "DASHBOARD_DISPLAY_TIMEZONE",
    "dashboard_display_today",
    "pacific_date_from_utc_token",
    "pacific_display_date_from_utc_token",
    "parse_utc_token",
]
