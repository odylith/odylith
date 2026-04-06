"""Shared dashboard display-time helpers.

The dashboard family stores freshness anchors in UTC-backed source contracts and
stable-generated payload metadata. Visible KPI cards, however, should reflect
the operator's San Francisco working day instead of the raw UTC calendar day.

Invariants:
- input values remain UTC-backed source tokens; this helper does not change
  stored contracts or rewrite source files.
- plain `YYYY-MM-DD` UTC stamps are interpreted as UTC midnight, which lets a
  UTC date bucket display as the corresponding Pacific calendar day.
- invalid or empty values fail calmly by returning the caller-provided default.
"""

from __future__ import annotations

import datetime as dt
import re
from zoneinfo import ZoneInfo

DASHBOARD_DISPLAY_TIMEZONE = "America/Los_Angeles"
_DASHBOARD_DISPLAY_TZ = ZoneInfo(DASHBOARD_DISPLAY_TIMEZONE)
_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NAIVE_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$"
)


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
    if _DATE_ONLY_RE.fullmatch(raw):
        candidate = f"{raw}T00:00:00+00:00"
    elif _NAIVE_DATETIME_RE.fullmatch(raw):
        candidate = f"{candidate}+00:00"
    elif candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"

    try:
        parsed = dt.datetime.fromisoformat(candidate)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def pacific_display_date_from_utc_token(value: object, *, default: str = "") -> str:
    """Return the Pacific calendar date for a UTC-backed dashboard token."""

    parsed = parse_utc_token(value)
    if parsed is None:
        return default
    return parsed.astimezone(_DASHBOARD_DISPLAY_TZ).date().isoformat()


def pacific_date_from_utc_token(value: object) -> dt.date | None:
    """Return the Pacific calendar date object for a UTC-backed dashboard token."""

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
