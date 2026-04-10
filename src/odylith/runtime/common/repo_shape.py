"""Cheap local product-repo shape detection for hot-path callers.

This module intentionally avoids importing the install manager. Some runtime
and CLI paths only need to know whether the current checkout is the Odylith
product repo, and paying the full install surface import cost there adds
avoidable latency.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import tomllib
from typing import Any, Mapping

PRODUCT_REPO_ROLE = "product_repo"
CONSUMER_REPO_ROLE = "consumer_repo"


def _pyproject_project_name(*, repo_root: Path) -> str:
    pyproject_path = (Path(repo_root).expanduser().resolve() / "pyproject.toml").resolve()
    if not pyproject_path.is_file():
        return ""
    try:
        payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return ""
    project = payload.get("project")
    if not isinstance(project, Mapping):
        return ""
    return str(project.get("name") or "").strip().lower()


@lru_cache(maxsize=32)
def _repo_role_from_resolved_root(resolved_repo_root: str) -> str:
    root = Path(str(resolved_repo_root)).expanduser().resolve()
    has_product_shape = (
        _pyproject_project_name(repo_root=root) == "odylith"
        and (root / "src" / "odylith").is_dir()
        and (root / "odylith" / "registry" / "source" / "component_registry.v1.json").is_file()
        and (root / "odylith" / "radar" / "source" / "INDEX.md").is_file()
    )
    return PRODUCT_REPO_ROLE if has_product_shape else CONSUMER_REPO_ROLE


def repo_role_from_local_shape(*, repo_root: str | Path) -> str:
    return _repo_role_from_resolved_root(str(Path(repo_root).expanduser().resolve()))


def is_product_repo_shape(*, repo_root: str | Path) -> bool:
    return repo_role_from_local_shape(repo_root=repo_root) == PRODUCT_REPO_ROLE


__all__ = [
    "CONSUMER_REPO_ROLE",
    "PRODUCT_REPO_ROLE",
    "is_product_repo_shape",
    "repo_role_from_local_shape",
]
