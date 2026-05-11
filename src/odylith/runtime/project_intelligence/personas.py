"""Persona-card generation for Project intelligence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.project_intelligence.utils import humanize, sentence


def source_persona_cards(
    *,
    audience_emphasis: object,
    repo_role: str,
    work_mode: str,
    evidence_sources: Sequence[str],
    critical_count: int,
) -> list[tuple[str, str, str]]:
    """Return concise human roles from graph-owned audience posture."""

    cards: list[tuple[str, str, str]] = []
    for row in _rows(audience_emphasis):
        role = sentence(row.get("role") or row.get("audience"))
        if not role:
            continue
        body = sentence(row.get("responsibility") or row.get("emphasis"))
        if body:
            cards.append(("", role, body))
    if cards:
        return _dedupe(cards)[:6]
    return [
        (
            "",
            _fallback_role(repo_role),
            f"Moves {sentence(work_mode, 'current').lower()} work forward with {_evidence_phrase(evidence_sources)}.",
        )
    ]


def audience_emphasis_rows(
    *,
    work_mode: str,
    topology_profile: Sequence[str],
    evidence_sources: Sequence[str],
    critical_count: int,
) -> list[dict[str, str]]:
    """Build graph-level persona responsibilities from current project posture."""

    mode = sentence(work_mode, "current").lower()
    evidence = _evidence_phrase(evidence_sources)
    operator = f"Moves {mode} work forward by choosing the next action and clearing blockers."
    maintainer = f"Changes source or governance records only after checking {evidence}."
    reviewer = (
        "Checks risk ownership, validation gaps, and contradiction paths."
        if critical_count or "risk-heavy" in topology_profile
        else "Checks source freshness, topology links, and claim evidence."
    )
    return [
        {"role": "Operator", "responsibility": operator},
        {"role": "Maintainer", "responsibility": maintainer},
        {"role": "Reviewer", "responsibility": reviewer},
    ]


def _rows(value: object) -> list[Mapping[str, Any]]:
    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, Sequence) else []


def _fallback_role(repo_role: str) -> str:
    token = str(repo_role or "").strip().lower().replace("-", "_")
    if token == "repo" or token.endswith("_repo"):
        return "Repository operator"
    return humanize(repo_role, "Project operator")


def _evidence_phrase(evidence_sources: Sequence[str]) -> str:
    names = [sentence(source) for source in evidence_sources if sentence(source)]
    if not names:
        return "available project evidence"
    if len(names) == 1:
        return f"{names[0]} evidence"
    if len(names) == 2:
        return f"{names[0]} and {names[1]} evidence"
    return f"{', '.join(names[:-1])}, and {names[-1]} evidence"


def _dedupe(cards: Sequence[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    result: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for card in cards:
        key = card[1].strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(card)
    return result
