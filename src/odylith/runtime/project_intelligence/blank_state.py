"""Blank Project tab projection for repos without an accepted project definition."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.project_intelligence.utils import humanize, sentence


def should_render_blank_project(
    *,
    components: Sequence[Mapping[str, Any]],
    backlog: Mapping[str, Any],
    plans: Mapping[str, Any],
    atlas: Mapping[str, Any],
    casebook: Mapping[str, Any],
    compass: Mapping[str, Any],
) -> bool:
    """Return true when runtime state exists but no project definition has been accepted."""

    if components:
        return False
    if _count(backlog, "queued_count") or _count(backlog, "execution_count") or _count(backlog, "finished_count"):
        return False
    if _count(plans, "active_count") or _count(plans, "parked_count") or _count(plans, "completed_recent_count"):
        return False
    if _count(atlas, "active_count") or _count(casebook, "open_count") or _count(casebook, "critical_count"):
        return False
    release = _mapping(_mapping(compass.get("release_summary")).get("current_release"))
    focus = _mapping(_mapping(compass.get("execution_focus")).get("global"))
    if _strings(release.get("active_workstreams")) or _strings(focus.get("workstreams")):
        return False
    return True


def build_blank_project_payload(*, repo_root: Path, shell_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Build the minimal Project tab shown before source or proposal truth exists."""

    repo_name = sentence(shell_payload.get("shell_repo_name")) or Path(repo_root).resolve().name
    project_title = humanize(repo_name, "Project")
    welcome = _mapping(shell_payload.get("welcome_state"))
    repo_readout = _strings(welcome.get("repo_readout") or welcome.get("repo_facts"))[:3]
    starter_prompt = sentence(welcome.get("starter_prompt"), "Odylith, show me what you can do.")
    return {
        "mode": "blank",
        "title": project_title,
        "eyebrow": "Project not defined yet",
        "intro": (
            "Odylith is installed, but this repository does not yet have an accepted project definition, "
            "greenfield proposal, work boundary, component ownership, or architecture map."
        ),
        "chips": ["Blank project state"],
        "blank_title": "Start with the project",
        "blank_note": (
            "Define what this repo is meant to become, then Odylith can derive work items, "
            "component boundaries, architecture views, risks, and proof from that source of truth."
        ),
        "blank_actions": [
            {
                "title": "Draft a greenfield proposal",
                "body": (
                    "Use this when the product does not exist yet. Odylith previews the project story, "
                    "first path, components, diagrams, risks, and validation gates before writing records."
                ),
                "command": 'odylith greenfield propose --repo-root . --prompt "<what you want to build>"',
            },
            {
                "title": "Ground an existing repo",
                "body": (
                    "Use this when source already exists. The first response should explain what it can see, "
                    "then propose the first governed slice instead of inventing a project definition."
                ),
                "command": starter_prompt,
            },
        ],
        "blank_preview_title": "What will appear after the project is defined",
        "blank_preview": [
            {
                "title": "Product story",
                "body": "A human explanation of the project, actors, first path, and intended outcome.",
            },
            {
                "title": "Governance spine",
                "body": "How project decisions, work items, component boundaries, architecture views, risks, and proof connect.",
            },
            {
                "title": "Execution boundary",
                "body": "What is included now, what is excluded, and what must be proven next.",
            },
        ],
        "blank_readout": repo_readout,
        "sections": ["empty_state"],
        "sources": {},
    }


def _count(payload: Mapping[str, Any], key: str) -> int:
    try:
        return int(payload.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _rows(value: object) -> list[Mapping[str, Any]]:
    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, Sequence) else []


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if not isinstance(value, Sequence):
        return []
    return [str(item).strip() for item in value if str(item or "").strip()]
