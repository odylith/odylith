"""Shared owned-surface refresh helpers for quick authoring workflows.

These helpers keep routine source-truth mutations on the smallest visible lane:
write truth, rerender the owned surface, and stop. The shared dashboard refresh
runtime already warms the projection compiler and the local memory backend, so
routing authoring commands through this helper keeps Compass/Radar/Registry/
Atlas/Casebook visibility in sync without widening into full governance sync.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
import io
from pathlib import Path

from odylith.runtime.common.command_surface import display_command
from odylith.runtime.surfaces import dashboard_shell_links


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
    "tooling_shell": OwnedSurfaceRefreshPolicy(
        surface="tooling_shell",
        retry_command=("dashboard", "refresh", "--repo-root", ".", "--surfaces", "shell"),
    ),
}


def refresh_owned_surface(*, repo_root: Path, surface: str) -> int:
    return refresh_owned_surfaces(repo_root=repo_root, surfaces=(surface,))


def refresh_owned_surfaces(*, repo_root: Path, surfaces: tuple[str, ...] | list[str]) -> int:
    from odylith.runtime.context_engine import odylith_context_engine_projection_search_runtime
    from odylith.runtime.governance import sync_workstream_artifacts

    policies = _policies_for_surfaces(surfaces)
    root = Path(repo_root).resolve()
    odylith_context_engine_projection_search_runtime.clear_runtime_process_caches(repo_root=root)
    return sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=root,
        surfaces=tuple(policy.surface for policy in policies),
        runtime_mode="auto",
        atlas_sync=any(policy.atlas_sync for policy in policies),
    )


def raise_for_failed_refresh(*, repo_root: Path, surface: str, operation_label: str, detail: str = "") -> None:
    raise_for_failed_refreshes(
        repo_root=repo_root,
        surfaces=(surface,),
        operation_label=operation_label,
        detail=detail,
    )


def raise_for_failed_refreshes(
    *,
    repo_root: Path,
    surfaces: tuple[str, ...] | list[str],
    operation_label: str,
    detail: str = "",
) -> None:
    policies = _policies_for_surfaces(surfaces)
    captured_output = io.StringIO()
    with contextlib.redirect_stdout(captured_output):
        refresh_rc = refresh_owned_surfaces(
            repo_root=repo_root,
            surfaces=tuple(policy.surface for policy in policies),
        )
    if refresh_rc == 0:
        return
    refresh_detail = " ".join(captured_output.getvalue().split())
    suffix = f" {detail.strip()}" if str(detail).strip() else ""
    output_suffix = f" Refresh output: {refresh_detail}" if refresh_detail else ""
    surface_names = ", ".join(policy.surface for policy in policies)
    retry_commands = "; ".join(display_command(*policy.retry_command) for policy in policies)
    raise RuntimeError(
        f"{operation_label.strip()} succeeded, but the {surface_names} surface refresh failed; "
        f"retry with `{retry_commands}`.{suffix}{output_suffix}"
    )


def dashboard_handoff(
    *,
    surface: str,
    workstream: str = "",
    component: str = "",
    diagram: str = "",
    bug: str = "",
) -> str:
    """Return the repo-local tooling-shell route for a newly changed surface item."""

    href = dashboard_shell_links.shell_href(
        tab=surface,
        workstream=workstream,
        component=component,
        diagram=diagram,
        bug=bug,
    )
    return f"odylith/index.html{href}"


def print_dashboard_handoff(
    *,
    surface: str,
    workstream: str = "",
    component: str = "",
    diagram: str = "",
    bug: str = "",
    dry_run: bool = False,
) -> None:
    """Print the one browser action an operator needs after a governance write."""

    if dry_run:
        return
    route = dashboard_handoff(
        surface=surface,
        workstream=workstream,
        component=component,
        diagram=diagram,
        bug=bug,
    )
    print(f"view: {route} (reload browser tab if already open)")


def _policy_for_surface(surface: str) -> OwnedSurfaceRefreshPolicy:
    token = str(surface or "").strip().lower()
    policy = _OWNED_SURFACE_REFRESH_POLICIES.get(token)
    if policy is None:
        raise ValueError(f"unknown owned surface `{surface}`")
    return policy


def _policies_for_surfaces(surfaces: tuple[str, ...] | list[str]) -> tuple[OwnedSurfaceRefreshPolicy, ...]:
    policies: list[OwnedSurfaceRefreshPolicy] = []
    seen: set[str] = set()
    for surface in surfaces:
        policy = _policy_for_surface(surface)
        if policy.surface in seen:
            continue
        policies.append(policy)
        seen.add(policy.surface)
    if not policies:
        raise ValueError("owned surface refresh requires at least one surface")
    return tuple(policies)


__all__ = [
    "OwnedSurfaceRefreshPolicy",
    "dashboard_handoff",
    "print_dashboard_handoff",
    "raise_for_failed_refresh",
    "raise_for_failed_refreshes",
    "refresh_owned_surface",
    "refresh_owned_surfaces",
]
