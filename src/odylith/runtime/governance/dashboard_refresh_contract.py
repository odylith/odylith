"""Dashboard Refresh Contract helpers for the Odylith governance layer."""

from __future__ import annotations

from odylith.runtime.common.command_surface import display_command

DEFAULT_DASHBOARD_REFRESH_TIMEOUT_SECONDS = 45.0


def dashboard_refresh_timeout_seconds(*, surface: str) -> float:
    del surface
    return DEFAULT_DASHBOARD_REFRESH_TIMEOUT_SECONDS


def dashboard_refresh_failure_command(*, surface: str) -> str:
    normalized_surface = str(surface).strip().lower()
    if normalized_surface == "compass":
        return display_command("dashboard", "refresh", "--repo-root", ".", "--surfaces", "compass")
    return display_command("dashboard", "refresh", "--repo-root", ".", "--surfaces", normalized_surface)
