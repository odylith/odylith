"""Shared refresh-guard helpers for generated dashboard surfaces."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.common import generated_refresh_guard
from odylith.runtime.surfaces import dashboard_surface_bundle
from odylith.runtime.surfaces import source_bundle_mirror

_GENERATED_SURFACE_GUARD_NAMESPACE = "generated-refresh-guards"
_SYNC_SKIP_GENERATED_REFRESH_GUARD_ENV = "ODYLITH_SYNC_SKIP_GENERATED_REFRESH_GUARD"


def _resolved_live_path(*, repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _unique_paths(values: Sequence[Path]) -> tuple[Path, ...]:
    rows: list[Path] = []
    seen: set[Path] = set()
    for raw in values:
        path = Path(raw).resolve()
        if path in seen:
            continue
        seen.add(path)
        rows.append(path)
    return tuple(rows)


def surface_output_paths(
    *,
    repo_root: Path,
    output_path: Path,
    asset_prefix: str,
    extra_live_paths: Sequence[str | Path] = (),
    live_globs: Sequence[str] = (),
) -> tuple[dashboard_surface_bundle.SurfaceBundlePaths, tuple[Path, ...]]:
    bundle_paths = dashboard_surface_bundle.build_paths(
        output_path=output_path,
        asset_prefix=asset_prefix,
    )
    live_paths: list[Path] = [
        output_path.resolve(),
        bundle_paths.payload_js_path.resolve(),
        bundle_paths.control_js_path.resolve(),
    ]
    for raw in extra_live_paths:
        token = str(raw or "").strip()
        if not token:
            continue
        live_paths.append(_resolved_live_path(repo_root=repo_root, value=raw))
    for pattern in live_globs:
        for matched in sorted(output_path.parent.glob(str(pattern))):
            if matched.is_file():
                live_paths.append(matched.resolve())
    resolved_live_paths = _unique_paths(live_paths)
    output_paths = list(resolved_live_paths)
    if source_bundle_mirror.source_bundle_root(repo_root=repo_root).is_dir():
        for live_path in resolved_live_paths:
            output_paths.append(
                source_bundle_mirror.bundle_mirror_path(
                    repo_root=repo_root,
                    live_path=live_path,
                ).resolve()
            )
    return bundle_paths, _unique_paths(output_paths)


def should_skip_surface_rebuild(
    *,
    repo_root: Path,
    output_path: Path,
    asset_prefix: str,
    key: str,
    watched_paths: Sequence[str | Path],
    extra_live_paths: Sequence[str | Path] = (),
    live_globs: Sequence[str] = (),
    extra: Mapping[str, Any] | None = None,
) -> tuple[bool, str, dict[str, Any], dashboard_surface_bundle.SurfaceBundlePaths, tuple[Path, ...]]:
    bundle_paths, output_paths = surface_output_paths(
        repo_root=repo_root,
        output_path=output_path,
        asset_prefix=asset_prefix,
        extra_live_paths=extra_live_paths,
        live_globs=live_globs,
    )
    if str(os.environ.get(_SYNC_SKIP_GENERATED_REFRESH_GUARD_ENV, "")).strip() == "1":
        return False, "", {}, bundle_paths, output_paths
    skip_rebuild, input_fingerprint, cached_metadata = generated_refresh_guard.should_skip_rebuild(
        repo_root=repo_root,
        namespace=_GENERATED_SURFACE_GUARD_NAMESPACE,
        key=key,
        watched_paths=watched_paths,
        output_paths=output_paths,
        extra=extra,
    )
    return skip_rebuild, input_fingerprint, cached_metadata, bundle_paths, output_paths


def record_surface_rebuild(
    *,
    repo_root: Path,
    key: str,
    input_fingerprint: str,
    output_paths: Sequence[Path],
    metadata: Mapping[str, Any] | None = None,
) -> None:
    generated_refresh_guard.record_rebuild(
        repo_root=repo_root,
        namespace=_GENERATED_SURFACE_GUARD_NAMESPACE,
        key=key,
        input_fingerprint=input_fingerprint,
        output_paths=tuple(Path(path).resolve() for path in output_paths),
        metadata=metadata,
    )


__all__ = [
    "record_surface_rebuild",
    "should_skip_surface_rebuild",
    "surface_output_paths",
]
