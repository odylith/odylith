"""Validate Guidance Portability helpers for the Odylith governance layer."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from odylith.runtime.governance import validate_backlog_contract as backlog_contract

_BANNED_TOKENS: tuple[str, ...] = (
    "./.venv/bin/python",
    ".venv/bin/python",
    "./.venv/bin/pytest",
    ".venv/bin/pytest",
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith validate guidance-portability",
        description="Fail on maintained guidance that hardcodes repo-local .venv Python or pytest entrypoints.",
    )
    parser.add_argument("--repo-root", default=".")
    return parser.parse_args(argv)


def _iter_root_guidance(repo_root: Path) -> Iterable[Path]:
    for candidate in sorted(repo_root.iterdir()):
        if candidate.is_file() and candidate.name.endswith(".md"):
            yield candidate
    claude_root = repo_root / ".claude"
    if claude_root.is_dir():
        yield from sorted(path for path in claude_root.rglob("*.md") if path.is_file())
    root_agents = repo_root / "AGENTS.md"
    if root_agents.is_file():
        yield root_agents


def _iter_odylith_guidance(repo_root: Path) -> Iterable[Path]:
    odylith_root = repo_root / "odylith"
    if not odylith_root.is_dir():
        return
    for relative_root in (
        Path("agents-guidelines"),
        Path("maintainer"),
    ):
        target_root = odylith_root / relative_root
        if not target_root.is_dir():
            continue
        yield from sorted(path for path in target_root.rglob("*.md") if path.is_file())
    for candidate in sorted(odylith_root.glob("*.md")):
        if candidate.is_file():
            yield candidate
    odylith_agents = odylith_root / "AGENTS.md"
    if odylith_agents.is_file():
        yield odylith_agents
    radar_index = odylith_root / "radar" / "source" / "INDEX.md"
    if radar_index.is_file():
        yield radar_index
    technical_plan_index = odylith_root / "technical-plans" / "INDEX.md"
    if technical_plan_index.is_file():
        yield technical_plan_index
    registry_root = odylith_root / "registry" / "source" / "components"
    if registry_root.is_dir():
        yield from sorted(path for path in registry_root.rglob("CURRENT_SPEC.md") if path.is_file())
    bundle_root = repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith"
    if bundle_root.is_dir():
        yield from sorted(path for path in bundle_root.rglob("*.md") if path.is_file())


def _iter_active_radar_and_plans(repo_root: Path) -> Iterable[Path]:
    ideas_root = repo_root / "odylith" / "radar" / "source" / "ideas"
    if ideas_root.is_dir():
        ideas, _errors = backlog_contract._validate_idea_specs(ideas_root)
        for spec in sorted(ideas.values(), key=lambda row: str(row.path)):
            if spec.status in {"queued", "planning", "implementation"}:
                yield spec.path
    in_progress_root = repo_root / "odylith" / "technical-plans" / "in-progress"
    if in_progress_root.is_dir():
        yield from sorted(path for path in in_progress_root.rglob("*.md") if path.is_file())


def maintained_guidance_paths(*, repo_root: Path) -> list[Path]:
    seen: set[Path] = set()
    ordered: list[Path] = []
    for path in (
        *list(_iter_root_guidance(repo_root)),
        *list(_iter_odylith_guidance(repo_root)),
        *list(_iter_active_radar_and_plans(repo_root)),
    ):
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(resolved)
    return ordered


def find_portability_errors(*, repo_root: Path) -> list[str]:
    errors: list[str] = []
    for path in maintained_guidance_paths(repo_root=repo_root):
        text = path.read_text(encoding="utf-8")
        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            for token in _BANNED_TOKENS:
                if token in raw_line:
                    errors.append(f"{path}: line {line_number}: replace `{token}` with a portable launcher or `python -m ...` form")
    return errors


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    errors = find_portability_errors(repo_root=repo_root)
    if errors:
        print("guidance portability FAILED")
        for error in errors:
            print(f"- {error}")
        return 2
    print("guidance portability OK")
    print(f"- maintained guidance files checked: {len(maintained_guidance_paths(repo_root=repo_root))}")
    return 0
