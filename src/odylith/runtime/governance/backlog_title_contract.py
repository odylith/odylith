"""Backlog Title Contract helpers for the Odylith governance layer."""

from __future__ import annotations

from pathlib import Path
import re
import tomllib

_PRODUCT_TITLE_PREFIX_RE = re.compile(r"^odylith\s+(?=\S)", re.IGNORECASE)


def infer_repo_root_from_ideas_root(ideas_root: Path) -> Path | None:
    root = Path(ideas_root).resolve()
    if (
        root.name == "ideas"
        and root.parent.name == "source"
        and root.parent.parent.name == "radar"
        and root.parent.parent.parent.name == "odylith"
    ):
        return root.parent.parent.parent.parent
    return None


def is_product_repo(repo_root: Path | None) -> bool:
    if repo_root is None:
        return False
    root = Path(repo_root).resolve()
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.is_file():
        return False
    try:
        payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return False
    project = payload.get("project")
    project_name = str(project.get("name") or "").strip().lower() if isinstance(project, dict) else ""
    return (
        project_name == "odylith"
        and (root / "src" / "odylith").is_dir()
        and (root / "odylith" / "registry" / "source" / "component_registry.v1.json").is_file()
        and (root / "odylith" / "radar" / "source" / "INDEX.md").is_file()
    )


def normalize_workstream_title(*, title: str, repo_root: Path | None) -> str:
    token = str(title or "").strip()
    if not token:
        return ""
    if not is_product_repo(repo_root):
        return token
    normalized = _PRODUCT_TITLE_PREFIX_RE.sub("", token, count=1).strip()
    return normalized or token


def validate_workstream_title(
    *,
    title: str,
    path: Path,
    repo_root: Path | None,
) -> list[str]:
    token = str(title or "").strip()
    if not token or not is_product_repo(repo_root):
        return []
    normalized = normalize_workstream_title(title=token, repo_root=repo_root)
    if normalized == token:
        return []
    return [
        f"{path}: product-repo Radar `title` must not start with `Odylith`; use `{normalized}` instead"
    ]
