"""Source-backed answer-card generation for Project intelligence."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.project_intelligence.summary import (
    action_sentence,
    action_title,
    concise_text,
    source_text,
    state_object,
)
from odylith.runtime.project_intelligence.utils import humanize, sentence


def source_answer_cards(
    *,
    project_title: str,
    repo_role: str,
    root_component: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
    current_focus: str,
    next_title: str,
    next_action_text: str,
    critical_count: int,
    blockers: Sequence[tuple[str, str, str]],
    evidence_sources: Sequence[str],
    consumer_lane: bool = False,
) -> list[tuple[str, str, str]]:
    """Build concise project-answer cards from source-backed project facts."""

    source = source_text(root_component=root_component, components=components)
    state = state_object(
        root_component=root_component,
        components=components,
        fallback=humanize(root_component.get("category"), "project"),
    )
    return [
        (f"Who uses {project_title}?", _user_title(source, repo_role), _user_body(project_title, source, repo_role)),
        (f"What changes in {project_title}?", state, _change_body(source, current_focus)),
        (f"What matters now for {project_title}?", _next_title(next_title), _next_body(next_action_text)),
        (f"What risk matters for {project_title}?", _risk_title(project_title, blockers), _risk_body(critical_count, blockers)),
        (
            f"What proves {project_title}?",
            _proof_title(evidence_sources, consumer_lane=consumer_lane),
            _proof_body(evidence_sources, consumer_lane=consumer_lane),
        ),
    ]


def _user_title(source: str, repo_role: str) -> str:
    role = _repo_actor_label(repo_role)
    if "agent" in source and any(token in source for token in ("repo", "repository", "coding", "code")):
        return f"{role} operators and coding agents"
    return f"{role} operators"


def _user_body(project_title: str, source: str, repo_role: str) -> str:
    role = _repo_actor_label(repo_role)
    if "agent" in source and any(token in source for token in ("repo", "repository", "coding", "code")):
        return f"Operators request repo work; agents execute it under {project_title} controls."
    return f"Work is scoped to this {role}."


def _change_body(source: str, current_focus: str) -> str:
    qualities = _work_qualities(source)
    if "agent" in source and any(token in source for token in ("code", "coding", "repo", "repository")) and qualities:
        return f"Work moves from request to action with {_join_lower(qualities)}."
    if qualities:
        return f"Work moves toward an outcome with {_join_lower(qualities)}."
    return concise_text(current_focus, limit=120)


def _next_title(value: object) -> str:
    return action_title(value)


def _next_body(value: object) -> str:
    return action_sentence(value)


def _risk_title(project_title: str, blockers: Sequence[tuple[str, str, str]]) -> str:
    if not blockers:
        return "No current blocker"
    title = concise_text(blockers[0][0], limit=90, fallback="Open risk")
    title = re.sub(r"^(greenfield|legacy|current)\s+", "", title, flags=re.IGNORECASE)
    title = re.sub(re.escape(project_title), "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip(" -:;.,")
    title = re.sub(r"\bmodeled\b", "model", title, flags=re.IGNORECASE)
    return concise_text(title, limit=80, fallback="Open risk")


def _work_qualities(source: str) -> list[str]:
    candidates = [
        (("context", "ground", "retrieval"), "grounding"),
        (("govern", "admiss", "control", "tribunal"), "governance"),
        (("validat", "proof", "test", "benchmark"), "validation"),
        (("memory", "history", "casebook", "compass"), "memory"),
    ]
    qualities: list[str] = []
    for tokens, label in candidates:
        if any(token in source for token in tokens):
            qualities.append(label)
    return qualities


def _risk_body(critical_count: int, blockers: Sequence[tuple[str, str, str]]) -> str:
    if critical_count:
        noun = "blocker" if critical_count == 1 else "blockers"
        return f"{critical_count} critical {noun} remain open."
    if blockers:
        return concise_text(blockers[0][1], limit=90, fallback="Open risk remains unresolved.")
    return "No current blocker is recorded."


def _proof_title(evidence_sources: Sequence[str], *, consumer_lane: bool = False) -> str:
    if consumer_lane:
        return "Reviewer-visible product evidence"
    roles = _proof_roles(evidence_sources)
    if roles:
        return _capitalize(f"{_join_lower(roles)} evidence")
    return "Available evidence"


def _proof_body(evidence_sources: Sequence[str], *, consumer_lane: bool = False) -> str:
    if consumer_lane:
        return (
            "A reviewer can follow the current state, active workflow, ownership boundary, risks, "
            "and validation evidence without relying on implementation-only context."
        )
    if not evidence_sources:
        return "Claims are limited to available project records."
    clauses = _proof_clauses(evidence_sources)
    if clauses:
        return f"{'; '.join(clauses)}."
    return f"{_join(evidence_sources)} provide project evidence."


def _proof_roles(evidence_sources: Sequence[str]) -> list[str]:
    sources = {sentence(source) for source in evidence_sources if sentence(source)}
    roles: list[str] = []
    if "Compass" in sources:
        roles.append("state")
    if "Radar" in sources or "Plans" in sources:
        roles.append("work")
    if "Registry" in sources or "Atlas" in sources:
        roles.append("shape")
    if "Casebook" in sources:
        roles.append("risk")
    return roles


def _proof_clauses(evidence_sources: Sequence[str]) -> list[str]:
    sources = {sentence(source) for source in evidence_sources if sentence(source)}
    clauses: list[str] = []
    if "Compass" in sources:
        clauses.append("Compass shows state")
    if "Radar" in sources and "Plans" in sources:
        clauses.append("Radar and Plans show active work")
    elif "Radar" in sources:
        clauses.append("Radar shows active work")
    elif "Plans" in sources:
        clauses.append("Plans show planned work")
    if "Registry" in sources and "Atlas" in sources:
        clauses.append("Registry and Atlas show shape and topology")
    elif "Registry" in sources:
        clauses.append("Registry shows component shape")
    elif "Atlas" in sources:
        clauses.append("Atlas shows topology")
    if "Casebook" in sources:
        clauses.append("Casebook shows open risks")
    known = {"Compass", "Radar", "Plans", "Registry", "Atlas", "Casebook"}
    clauses.extend(f"{source} provides source evidence" for source in sorted(sources - known))
    return clauses


def _capitalize(value: str) -> str:
    return f"{value[:1].upper()}{value[1:]}" if value else value


def _repo_actor_label(repo_role: str) -> str:
    token = str(repo_role or "").strip().lower().replace("-", "_")
    if token == "repo" or token.endswith("_repo"):
        return "repository"
    return humanize(repo_role, "project").lower()


def _join(values: Sequence[str]) -> str:
    items = [sentence(value) for value in values if sentence(value)]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _join_lower(values: Sequence[str]) -> str:
    items = [str(value).strip() for value in values if str(value).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"
