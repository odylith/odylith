"""Dirty Overlap helpers for the Odylith common layer."""

from __future__ import annotations

from collections import Counter
from typing import Sequence


def _dirty_overlap_path(line: str) -> str:
    token = str(line or "").rstrip()
    if not token:
        return ""
    if "\t" in token:
        return token.rsplit("\t", 1)[-1].strip()
    parts = token.split(None, 1)
    if len(parts) == 2:
        return parts[1].strip()
    return token


def _dirty_overlap_area(path: str) -> str:
    normalized = str(path or "").strip()
    if not normalized:
        return "other"
    if normalized.startswith(".odylith/"):
        return "runtime_state"
    if (
        normalized in {"AGENTS.md", "CLAUDE.md", ".gitignore"}
        or normalized.startswith(".claude/")
        or normalized.startswith(("odylith/AGENTS.md", "odylith/CLAUDE.md"))
        or (normalized.startswith("odylith/") and normalized.endswith(("/AGENTS.md", "/CLAUDE.md")))
    ):
        return "managed_guidance"
    if normalized.startswith("odylith/agents-guidelines/") or normalized.startswith("odylith/skills/"):
        return "managed_guidance"
    if normalized.startswith(("odylith/runtime/source/", "odylith/radar/source/", "odylith/technical-plans/", "odylith/registry/source/", "odylith/atlas/source/", "odylith/casebook/bugs/")):
        return "repo_truth"
    if normalized.startswith("odylith/"):
        return "generated_surfaces"
    return "other"


def summarize_dirty_overlap(
    lines: Sequence[str],
    *,
    verbose: bool,
    sample_size: int = 4,
) -> tuple[str, ...]:
    normalized = tuple(str(line).rstrip() for line in lines if str(line).strip())
    if not normalized:
        return ()
    if verbose or len(normalized) <= sample_size:
        return normalized
    sample = normalized[:sample_size]
    hidden = len(normalized) - len(sample)
    area_counts = Counter(_dirty_overlap_area(_dirty_overlap_path(line)) for line in normalized)
    area_summary = ", ".join(
        f"{area}={count}"
        for area, count in sorted(area_counts.items(), key=lambda item: (-item[1], item[0]))
        if count > 0
    )
    return (
        f"{len(normalized)} local worktree entries overlap this mutation plan.",
        f"By area: {area_summary}.",
        *sample,
        f"... {hidden} more overlap entries hidden; rerun with --verbose to show the full set.",
    )
