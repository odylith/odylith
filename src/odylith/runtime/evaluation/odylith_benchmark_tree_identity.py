"""Helpers for stable benchmark report tree-identity inputs."""

from __future__ import annotations

from collections.abc import Iterable


def stable_snapshot_overlay_path(token: object) -> str:
    path = str(token).strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    if not path or path == ".odylith" or path.startswith(".odylith/"):
        return ""
    return path


def stable_snapshot_overlay_paths(tokens: Iterable[object]) -> list[str]:
    return [path for token in tokens if (path := stable_snapshot_overlay_path(token))]
