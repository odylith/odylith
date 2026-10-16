"""Product Assets helpers for the Odylith common layer."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def bundled_product_root() -> Path:
    return Path(files("odylith.bundle").joinpath("assets", "odylith"))


def bundled_project_root_assets_root() -> Path:
    return Path(files("odylith.bundle").joinpath("assets", "project-root"))


def resolve_product_path(*, repo_root: Path, relative_path: str | Path) -> Path:
    relative = Path(str(relative_path).strip())
    candidate = (Path(repo_root).resolve() / relative).resolve()
    if candidate.exists():
        return candidate
    normalized = _normalized_relative_path(relative)
    if normalized.startswith("odylith/"):
        normalized = normalized.removeprefix("odylith/")
    return (bundled_product_root() / normalized).resolve()


def _normalized_relative_path(relative: Path) -> str:
    """Remove explicit current-directory prefixes without corrupting dotfiles."""

    token = relative.as_posix()
    while token.startswith("./"):
        token = token[2:]
    return token
