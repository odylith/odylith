from __future__ import annotations

import datetime as dt

from odylith.runtime.surfaces import dashboard_time


def test_pacific_display_date_from_utc_date_only_token_rolls_back_calendar_day() -> None:
    assert dashboard_time.pacific_display_date_from_utc_token("2026-03-11") == "2026-03-10"


def test_pacific_display_date_from_utc_timestamp_rolls_back_calendar_day() -> None:
    assert dashboard_time.pacific_display_date_from_utc_token("2026-03-11T01:15:00Z") == "2026-03-10"


def test_pacific_display_date_from_utc_token_handles_invalid_input() -> None:
    assert dashboard_time.pacific_display_date_from_utc_token("not-a-date", default="-") == "-"


def test_pacific_date_from_utc_token_returns_calendar_date() -> None:
    assert dashboard_time.pacific_date_from_utc_token("2026-03-11T01:15:00Z") == dt.date(2026, 3, 10)


def test_dashboard_display_today_uses_pacific_calendar_day() -> None:
    now = dt.datetime(2026, 3, 11, 1, 15, tzinfo=dt.timezone.utc)
    assert dashboard_time.dashboard_display_today(now=now) == dt.date(2026, 3, 10)
