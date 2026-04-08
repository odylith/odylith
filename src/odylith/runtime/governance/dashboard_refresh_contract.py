from __future__ import annotations

from pathlib import Path

from odylith.runtime.common.command_surface import display_command

DEFAULT_DASHBOARD_REFRESH_TIMEOUT_SECONDS = 45.0
COMPASS_FULL_REFRESH_TIMEOUT_SECONDS = 180.0
DEFAULT_COMPASS_REFRESH_PROFILE = "shell-safe"


def normalize_compass_refresh_profile(value: str, *, default: str = DEFAULT_COMPASS_REFRESH_PROFILE) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"full", "shell-safe"}:
        return normalized
    return str(default).strip().lower() or DEFAULT_COMPASS_REFRESH_PROFILE


def dashboard_refresh_timeout_seconds(*, surface: str, compass_refresh_profile: str) -> float:
    if str(surface).strip().lower() == "compass" and normalize_compass_refresh_profile(compass_refresh_profile) == "full":
        return COMPASS_FULL_REFRESH_TIMEOUT_SECONDS
    return DEFAULT_DASHBOARD_REFRESH_TIMEOUT_SECONDS


def dashboard_refresh_failure_command(*, surface: str, compass_refresh_profile: str) -> str:
    normalized_surface = str(surface).strip().lower()
    if normalized_surface == "compass":
        return display_command(
            "dashboard",
            "refresh",
            "--repo-root",
            ".",
            "--surfaces",
            "compass",
            "--compass-refresh-profile",
            normalize_compass_refresh_profile(compass_refresh_profile),
        )
    return display_command("dashboard", "refresh", "--repo-root", ".", "--surfaces", normalized_surface)


def mark_compass_refresh_failure(
    *,
    repo_root: Path,
    runtime_mode: str,
    requested_profile: str,
    rc: int,
    fallback_used: bool,
) -> bool:
    normalized_profile = normalize_compass_refresh_profile(requested_profile)
    if normalized_profile != "full":
        return False
    from odylith.runtime.surfaces import render_compass_dashboard

    reason = "timeout" if int(rc) == 124 else "render_failed"
    return render_compass_dashboard.record_failed_refresh_attempt(
        repo_root=repo_root,
        runtime_dir=repo_root / "odylith" / "compass" / "runtime",
        requested_profile=normalized_profile,
        runtime_mode=runtime_mode,
        reason=reason,
        fallback_used=fallback_used,
    )
