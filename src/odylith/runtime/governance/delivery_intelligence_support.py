"""Shared support helpers for delivery-intelligence entrypoints.

The delivery-intelligence engine and its refresh shim both need the same small
set of deterministic repository facts: the current local HEAD and the registry
spec files that should invalidate cached delivery posture. Keeping those rules
here prevents drift between the full builder and the fast refresh path.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

from odylith.runtime.common import repo_path_resolver


def current_local_head(repo_root: Path) -> str:
    """Return the current local Git HEAD for cache invalidation context."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return str(completed.stdout or "").strip()


def registry_delivery_watched_paths(repo_root: Path) -> tuple[str, ...]:
    """Return the Registry files that should invalidate delivery intelligence."""

    root = Path(repo_root).resolve()
    specs_root = (root / "odylith" / "registry" / "source" / "components").resolve()
    current_specs = sorted(
        repo_path_resolver.display_repo_path(repo_root=root, value=path)
        for path in specs_root.glob("*/CURRENT_SPEC.md")
        if path.is_file()
    )
    return ("odylith/registry/source/component_registry.v1.json", *current_specs)


__all__ = ["current_local_head", "registry_delivery_watched_paths"]
