"""Pure payload builders for the tooling dashboard renderer."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from collections.abc import Mapping

from odylith.runtime.surfaces import dashboard_surface_bundle


@dataclass(frozen=True)
class ToolingDashboardSurfacePaths:
    output_path: Path
    radar_path: Path
    atlas_path: Path
    compass_path: Path
    registry_path: Path
    casebook_path: Path


@dataclass(frozen=True)
class ToolingDashboardBuildResult:
    runtime_payload: dict[str, Any]
    release_notes_path: Path | None


def _shell_repo_name(*, repo_root: Path) -> str:
    root = Path(repo_root).resolve()
    if (root / "src" / "odylith").is_dir() and (root / "odylith").is_dir() and (root / "pyproject.toml").is_file():
        return "odylith"
    return str(root.name).strip()


def _as_href(*, output_path: Path, target: Path) -> str:
    rel = os.path.relpath(str(target), start=str(output_path.parent))
    return Path(rel).as_posix()


def _rendered_surface_files(*, surface_html: Path) -> list[Path]:
    files: list[Path] = []
    if surface_html.is_file():
        files.append(surface_html)
    surface_dir = surface_html.parent
    if not surface_dir.is_dir():
        return files
    for candidate in surface_dir.iterdir():
        if candidate == surface_html:
            continue
        if candidate.is_file() and candidate.suffix.lower() in {".html", ".js", ".css", ".json"}:
            files.append(candidate)
            continue
        if candidate.is_dir() and candidate.name == "runtime":
            for runtime_file in candidate.rglob("*"):
                if runtime_file.is_file() and runtime_file.suffix.lower() in {".js", ".json"}:
                    files.append(runtime_file)
    return files


def _surface_version_token(*, surface_html: Path) -> str:
    mtimes = [
        path.stat().st_mtime_ns
        for path in _rendered_surface_files(surface_html=surface_html)
        if path.exists()
    ]
    if not mtimes:
        return ""
    return str(max(mtimes))


def _versioned_surface_href(*, output_path: Path, target: Path) -> str:
    href = _as_href(output_path=output_path, target=target)
    version = _surface_version_token(surface_html=target)
    return dashboard_surface_bundle.append_query_param(href=href, name="v", value=version)


def validate_surface_paths(paths: ToolingDashboardSurfacePaths) -> list[str]:
    errors: list[str] = []
    if not paths.radar_path.is_file():
        errors.append(f"missing radar html: {paths.radar_path}")
    if not paths.atlas_path.is_file():
        errors.append(f"missing atlas html: {paths.atlas_path}")
    if not paths.compass_path.is_file():
        errors.append(f"missing compass html: {paths.compass_path}")
    if not paths.registry_path.is_file():
        errors.append(f"missing registry html: {paths.registry_path}")
    if not paths.casebook_path.is_file():
        errors.append(f"missing casebook html: {paths.casebook_path}")
    return errors


def release_notes_output_path(*, output_path: Path, spotlight: Mapping[str, Any]) -> Path:
    version_token = str(spotlight.get("to_version", "")).strip() or str(spotlight.get("release_tag", "")).strip() or "latest"
    slug = re.sub(r"[^0-9A-Za-z._-]+", "-", version_token).strip("-").lower() or "latest"
    return output_path.parent / "release-notes" / f"{slug}.html"


def build_runtime_payload(
    *,
    repo_root: Path,
    surface_paths: ToolingDashboardSurfacePaths,
    shell_payload: Mapping[str, Any],
    welcome_state: Mapping[str, Any],
    release_spotlight: Mapping[str, Any],
    version_story: Mapping[str, Any],
    benchmark_story: Mapping[str, Any],
    shell_source_payload: Mapping[str, Any],
    self_host_payload: Mapping[str, Any],
    brand_payload: Mapping[str, Any],
    shell_version_label: str,
) -> ToolingDashboardBuildResult:
    spotlight_payload = dict(release_spotlight)
    version_story_payload = dict(version_story)
    release_notes_path: Path | None = None
    release_story_payload = spotlight_payload if bool(spotlight_payload.get("show")) else version_story_payload
    if bool(release_story_payload.get("show")):
        release_notes_path = release_notes_output_path(
            output_path=surface_paths.output_path,
            spotlight=release_story_payload,
        )
        notes_href = _as_href(output_path=surface_paths.output_path, target=release_notes_path)
        if spotlight_payload:
            spotlight_payload["notes_href"] = notes_href
        if version_story_payload:
            version_story_payload["notes_href"] = notes_href

    runtime_payload: dict[str, Any] = {
        **dict(shell_payload),
        "radar_href": _versioned_surface_href(output_path=surface_paths.output_path, target=surface_paths.radar_path),
        "atlas_href": _versioned_surface_href(output_path=surface_paths.output_path, target=surface_paths.atlas_path),
        "compass_href": _versioned_surface_href(output_path=surface_paths.output_path, target=surface_paths.compass_path),
        "registry_href": _versioned_surface_href(output_path=surface_paths.output_path, target=surface_paths.registry_path),
        "casebook_href": _versioned_surface_href(output_path=surface_paths.output_path, target=surface_paths.casebook_path),
        "welcome_state": dict(welcome_state),
        "release_spotlight": spotlight_payload,
        "version_story": version_story_payload,
        "benchmark_story": dict(benchmark_story),
        **dict(shell_source_payload),
        "self_host": dict(self_host_payload),
        **dict(brand_payload),
        "shell_repo_name": _shell_repo_name(repo_root=repo_root),
        "shell_version_label": str(shell_version_label).strip(),
    }
    return ToolingDashboardBuildResult(
        runtime_payload=runtime_payload,
        release_notes_path=release_notes_path,
    )


def build_release_notes_payload(
    *,
    runtime_payload: Mapping[str, Any],
    brand_payload: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        **dict(runtime_payload),
        **dict(brand_payload),
    }
