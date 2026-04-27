"""Shared owned-surface refresh helpers for quick authoring workflows.

These helpers keep routine source-truth mutations on the smallest visible lane:
write truth, rerender the owned surface, and stop. The shared dashboard refresh
runtime already warms the projection compiler and the local memory backend, so
routing authoring commands through this helper keeps Compass/Radar/Registry/
Atlas/Casebook visibility in sync without widening into full governance sync.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from odylith.runtime.common.command_surface import display_command


@dataclass(frozen=True)
class OwnedSurfaceRefreshPolicy:
    surface: str
    runtime_mode: str = "auto"
    atlas_sync: bool = False
    retry_command: tuple[str, ...] = ()


_OWNED_SURFACE_REFRESH_POLICIES: dict[str, OwnedSurfaceRefreshPolicy] = {
    "radar": OwnedSurfaceRefreshPolicy(
        surface="radar",
        retry_command=("radar", "refresh", "--repo-root", "."),
    ),
    "registry": OwnedSurfaceRefreshPolicy(
        surface="registry",
        retry_command=("registry", "refresh", "--repo-root", "."),
    ),
    "casebook": OwnedSurfaceRefreshPolicy(
        surface="casebook",
        retry_command=("casebook", "refresh", "--repo-root", "."),
    ),
    "atlas": OwnedSurfaceRefreshPolicy(
        surface="atlas",
        atlas_sync=True,
        retry_command=("atlas", "refresh", "--repo-root", ".", "--atlas-sync"),
    ),
    "compass": OwnedSurfaceRefreshPolicy(
        surface="compass",
        retry_command=("compass", "refresh", "--repo-root", ".", "--wait"),
    ),
}


def refresh_owned_surface(*, repo_root: Path, surface: str) -> int:
    from odylith.runtime.governance import sync_workstream_artifacts

    policy = _policy_for_surface(surface)
    return sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=Path(repo_root).resolve(),
        surfaces=(policy.surface,),
        runtime_mode=policy.runtime_mode,
        atlas_sync=policy.atlas_sync,
    )


def raise_for_failed_refresh(*, repo_root: Path, surface: str, operation_label: str, detail: str = "") -> None:
    policy = _policy_for_surface(surface)
    refresh_rc = refresh_owned_surface(repo_root=repo_root, surface=policy.surface)
    if refresh_rc == 0:
        return
    suffix = f" {detail.strip()}" if str(detail).strip() else ""
    retry_command = display_command(*policy.retry_command)
    raise RuntimeError(
        f"{operation_label.strip()} succeeded, but the {policy.surface} surface refresh failed; "
        f"retry with `{retry_command}`.{suffix}"
    )


def _policy_for_surface(surface: str) -> OwnedSurfaceRefreshPolicy:
    token = str(surface or "").strip().lower()
    policy = _OWNED_SURFACE_REFRESH_POLICIES.get(token)
    if policy is None:
        raise ValueError(f"unknown owned surface `{surface}`")
    return policy


__all__ = ["OwnedSurfaceRefreshPolicy", "raise_for_failed_refresh", "refresh_owned_surface"]
