from __future__ import annotations

from pathlib import Path


ROOT_GUIDANCE_FILENAMES = frozenset({"AGENTS.md", "CLAUDE.md"})
PROJECT_CLAUDE_GUIDANCE_RELATIVE = Path(".claude/CLAUDE.md")
TOP_LEVEL_GUIDANCE_RELATIVE_PATHS: tuple[Path, ...] = (
    Path("AGENTS.md"),
    Path("CLAUDE.md"),
)
PROJECT_GUIDANCE_RELATIVE_PATHS: tuple[Path, ...] = (
    *TOP_LEVEL_GUIDANCE_RELATIVE_PATHS,
    PROJECT_CLAUDE_GUIDANCE_RELATIVE,
)
PROJECT_GUIDANCE_DISPLAY = "AGENTS.md, CLAUDE.md, or .claude/CLAUDE.md"


def existing_project_guidance_paths(*, repo_root: Path) -> tuple[Path, ...]:
    root = Path(repo_root).resolve()
    return tuple(
        path
        for relative in PROJECT_GUIDANCE_RELATIVE_PATHS
        if (path := root / relative).is_file()
    )


def has_project_guidance(*, repo_root: Path) -> bool:
    return bool(existing_project_guidance_paths(repo_root=repo_root))


def existing_top_level_guidance_paths(*, repo_root: Path) -> tuple[Path, ...]:
    root = Path(repo_root).resolve()
    return tuple(
        path
        for relative in TOP_LEVEL_GUIDANCE_RELATIVE_PATHS
        if (path := root / relative).is_file()
    )
