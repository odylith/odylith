"""Dashboard Refresh Contract helpers for the Odylith governance layer."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
import sys

from odylith.runtime.common.command_surface import display_command

DEFAULT_DASHBOARD_REFRESH_TIMEOUT_SECONDS = 45.0
DEFAULT_ATLAS_REFRESH_TIMEOUT_SECONDS = 180.0
FIRST_RUN_SURFACE_OUTPUTS = (
    Path("odylith/index.html"),
    Path("odylith/radar/radar.html"),
    Path("odylith/atlas/atlas.html"),
    Path("odylith/compass/compass.html"),
    Path("odylith/registry/registry.html"),
    Path("odylith/casebook/casebook.html"),
)


def activate_initial_dashboard_baseline(*, repo_root: Path) -> int:
    """Complete initial publication under the caller's admitted writer lock."""
    from odylith.runtime.domain_intelligence import greenfield_create_baseline, greenfield_generation_state

    try:
        # Existing publications settle through the owning writer's successor path.
        if greenfield_generation_state.read_active_publication(repo_root) is None:
            greenfield_create_baseline.activate_completed_greenfield_baseline_locked(
                repo_root=repo_root, required_surface_outputs=FIRST_RUN_SURFACE_OUTPUTS,
            )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Odylith baseline activation needs recovery: {exc}", file=sys.stderr)
        return 1
    return 0


def complete_dashboard_refresh(
    *, results: Sequence[Mapping[str, object]], selected: Sequence[str],
    elapsed: float, runtime_fallback_used: bool, on_completed: Callable[[], int] | None,
) -> int:
    """Report renderer outcomes and admit completion only with full terminal coverage."""
    failures = [result for result in results if result.get("status") == "failed"]
    queued = [result for result in results if result.get("status") == "queued"]
    passed_surfaces = [result.get("surface") for result in results if result.get("status") == "passed"]
    complete = bool(selected) and len(results) == len(selected) and all(passed_surfaces.count(surface) == 1 for surface in selected)
    invalid_completion = on_completed is not None and not complete and not queued
    print("dashboard refresh completed")
    if failures or invalid_completion:
        print("- outcome: failed")
    elif queued:
        print("- outcome: queued")
    else:
        print("- outcome: passed")
    print(f"- elapsed_seconds: {elapsed:.1f}")
    fallback_used = runtime_fallback_used or any(result.get("fallback_used") for result in results)
    print(f"- runtime_fallback_used: {'yes' if fallback_used else 'no'}")
    for result in results:
        surface = str(result.get("surface", "")).strip()
        status = str(result.get("status", "")).strip() or "failed"
        suffix = " (standalone fallback used)" if result.get("fallback_used") else ""
        if result.get("cache_hit"):
            suffix += " (fingerprint reuse)"
        print(f"- {surface}: {status}{suffix}")
        if status not in {"passed", "queued"}:
            failed_step = str(result.get("failed_step", "")).strip()
            if failed_step:
                print(f"  failed_step: {failed_step}")
        if status != "passed":
            next_command = str(result.get("next_command", "")).strip()
            if next_command:
                print(f"  next: {next_command}")
    if failures or invalid_completion:
        return 2
    if on_completed is not None:
        return 1 if queued else on_completed()
    return 0


def dashboard_refresh_timeout_seconds(*, surface: str) -> float:
    normalized_surface = str(surface).strip().lower()
    if normalized_surface == "atlas":
        return DEFAULT_ATLAS_REFRESH_TIMEOUT_SECONDS
    return DEFAULT_DASHBOARD_REFRESH_TIMEOUT_SECONDS


def dashboard_refresh_failure_command(*, surface: str) -> str:
    normalized_surface = str(surface).strip().lower()
    if normalized_surface == "compass":
        return display_command("dashboard", "refresh", "--repo-root", ".", "--surfaces", "compass")
    return display_command("dashboard", "refresh", "--repo-root", ".", "--surfaces", normalized_surface)
