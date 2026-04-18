"""Pure payload builders for the tooling dashboard renderer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from collections.abc import Mapping

from odylith.runtime.surfaces import dashboard_surface_bundle
from odylith.runtime.surfaces import surface_path_helpers


@dataclass(frozen=True)
class ToolingDashboardSurfacePaths:
    """Concrete HTML output paths for the tooling dashboard and linked surfaces."""
    output_path: Path
    radar_path: Path
    atlas_path: Path
    compass_path: Path
    registry_path: Path
    casebook_path: Path


@dataclass(frozen=True)
class ToolingDashboardBuildResult:
    """Runtime payload bundle returned by the tooling dashboard builder."""
    runtime_payload: dict[str, Any]


def _shell_repo_name(*, repo_root: Path) -> str:
    """Return the shell repo label shown in the tooling dashboard chrome."""
    root = Path(repo_root).resolve()
    if (root / "src" / "odylith").is_dir() and (root / "odylith").is_dir() and (root / "pyproject.toml").is_file():
        return "odylith"
    return str(root.name).strip()


def _rendered_surface_files(*, surface_html: Path) -> list[Path]:
    """Collect rendered files that contribute to one surface version token."""
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
    """Return the max mtime token across the rendered files for one surface."""
    mtimes = [
        path.stat().st_mtime_ns
        for path in _rendered_surface_files(surface_html=surface_html)
        if path.exists()
    ]
    if not mtimes:
        return ""
    return str(max(mtimes))


def _versioned_surface_href(*, output_path: Path, target: Path) -> str:
    """Append a cache-busting version token to one linked surface href."""
    href = surface_path_helpers.relative_href(output_path=output_path, target=target)
    version = _surface_version_token(surface_html=target)
    return dashboard_surface_bundle.append_query_param(href=href, name="v", value=version)


def _surface_checks(paths: ToolingDashboardSurfacePaths) -> tuple[tuple[str, Path], ...]:
    """Return the named surface html files that must exist for the dashboard."""
    return (
        ("radar", paths.radar_path),
        ("atlas", paths.atlas_path),
        ("compass", paths.compass_path),
        ("registry", paths.registry_path),
        ("casebook", paths.casebook_path),
    )


def validate_surface_paths(paths: ToolingDashboardSurfacePaths) -> list[str]:
    """Validate that all linked tooling-dashboard surface html files exist."""
    errors: list[str] = []
    for label, path in _surface_checks(paths):
        if not path.is_file():
            errors.append(f"missing {label} html: {path}")
    return errors


def build_runtime_payload(
    *,
    repo_root: Path,
    surface_paths: ToolingDashboardSurfacePaths,
    welcome_state: Mapping[str, Any],
    release_spotlight: Mapping[str, Any],
    version_story: Mapping[str, Any],
    shell_source_payload: Mapping[str, Any],
    self_host_payload: Mapping[str, Any],
    brand_payload: Mapping[str, Any],
    shell_version_label: str,
) -> ToolingDashboardBuildResult:
    """Build the runtime payload consumed by the tooling dashboard shell."""
    spotlight_payload = dict(release_spotlight)
    version_story_payload = dict(version_story)

    runtime_payload: dict[str, Any] = {
        "radar_href": _versioned_surface_href(output_path=surface_paths.output_path, target=surface_paths.radar_path),
        "atlas_href": _versioned_surface_href(output_path=surface_paths.output_path, target=surface_paths.atlas_path),
        "compass_href": _versioned_surface_href(output_path=surface_paths.output_path, target=surface_paths.compass_path),
        "registry_href": _versioned_surface_href(output_path=surface_paths.output_path, target=surface_paths.registry_path),
        "casebook_href": _versioned_surface_href(output_path=surface_paths.output_path, target=surface_paths.casebook_path),
        "case_queue": [],
        "components": {},
        "diagrams": {},
        "workstreams": {},
        "welcome_state": dict(welcome_state),
        "release_spotlight": spotlight_payload,
        "version_story": version_story_payload,
        **dict(shell_source_payload),
        "self_host": dict(self_host_payload),
        **dict(brand_payload),
        "shell_repo_name": _shell_repo_name(repo_root=repo_root),
        "shell_version_label": str(shell_version_label).strip(),
    }
    return ToolingDashboardBuildResult(
        runtime_payload=runtime_payload,
    )
