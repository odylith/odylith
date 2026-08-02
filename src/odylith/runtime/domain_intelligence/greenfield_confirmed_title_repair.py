"""Canonical title repair for confirmed greenfield completion."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_generated_text as _clean
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import normalize_project_title
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.project_intelligence_binding import attach_project_intelligence_bindings


def repair_project_title(proposal: dict[str, Any]) -> bool:
    """Repair canonical project identity without asking the operator to clean generated prose."""

    intent = proposal.get("intent")
    if not isinstance(intent, dict):
        return False
    current = _clean(intent.get("title"))
    if not current:
        return False
    if not _project_title_needs_repair(current):
        return False
    existing_candidate = _existing_project_title_candidate(proposal, current=current)
    seed = {
        "title": existing_candidate or current,
        "product_story": intent.get("product_story") or _project_intelligence_first_row(proposal, "intent"),
        "state_object": _state_object(proposal),
        "first_path": _first_path(proposal),
        "proof_boundary": _proof_boundary(proposal),
        "human_actors": _project_intelligence_rows(proposal, "operators"),
        "internal_systems": _component_system_rows(proposal),
        "assumptions": text_values(proposal.get("assumptions")),
        "ambiguities": text_values(proposal.get("open_questions")),
        "non_goals": text_values(proposal.get("non_goals")),
    }
    repaired = complete_confirmed_intent(seed)
    replacement = _clean(repaired.get("title"))
    if not replacement or replacement == current:
        return False
    _replace_title_text(proposal, current=current, replacement=replacement)
    repaired_intent = proposal.get("intent")
    if isinstance(repaired_intent, dict):
        repaired_intent["title"] = replacement
        repaired_intent["project_slug"] = slugify(replacement)
    rebound = attach_project_intelligence_bindings(proposal)
    proposal.clear()
    proposal.update(rebound)
    return True


def _project_title_needs_repair(value: str) -> bool:
    text = _clean(value)
    if normalize_project_title(text).changed:
        return True
    words = label_terms(text)
    if not text or not words:
        return True
    if text.casefold() in {"greenfield project", "confirmed project"}:
        return True
    if words[-1].casefold() in {"a", "an", "and", "for", "from", "in", "of", "on", "or", "the", "to", "with"}:
        return True
    if re.match(r"^(?:build|create|design|develop|draft|launch|make|plan)\b", text, re.IGNORECASE):
        return True
    return len(words) > 10 and bool(
        re.search(r"\b(?:that|what|so|because|captures?|follows?|makes?|buying|doing|needs?|wants?)\b", text, re.IGNORECASE)
    )


def _existing_project_title_candidate(proposal: Mapping[str, Any], *, current: str) -> str:
    candidates: list[str] = []
    for row in mapping_rows(proposal.get("backlog")):
        candidates.extend(_title_candidates_from_text(row.get("title")))
    release_plan = proposal.get("release_plan")
    if isinstance(release_plan, Mapping):
        candidates.extend(_title_candidates_from_text(release_plan.get("label")))
        candidates.extend(_title_candidates_from_text(release_plan.get("strategy")))
    project_brief = proposal.get("project_brief")
    if isinstance(project_brief, Mapping):
        candidates.extend(_title_candidates_from_text(project_brief.get("purpose")))
        candidates.extend(_title_candidates_from_text(project_brief.get("project_outcome")))
    intelligence = proposal.get("project_intelligence")
    if isinstance(intelligence, Mapping):
        candidates.extend(_title_candidates_from_text(intelligence.get("purpose")))
        candidates.extend(_title_candidates_from_text(intelligence.get("coding_posture")))
    for candidate in candidates:
        if _title_candidate_is_better(candidate, current=current):
            return candidate
    return ""


def _title_candidates_from_text(value: Any) -> list[str]:
    text = _clean(value).strip(" .")
    if not text:
        return []
    rows: list[str] = []
    patterns = (
        r"^Govern\s+(?P<title>.+?)$",
        r"^Ship\s+(?P<title>.+?)\s+First\s+Release$",
        r"^(?P<title>.+?)\s+\d+(?:\.\d+){1,2}\s+first\s+path\b",
        r"^(?P<title>.+?)\s+first[-\s]path\s+proof\b",
        r"^(?P<title>.+?)\s+state\s+and\s+evidence\s+boundary\b",
        r"^(?P<title>.+?)\s+release\s+review\b",
        r"^(?P<title>.+?)\s+translates\s+the\s+accepted\b",
        r"^Promote\s+(?P<title>.+?)\s+only\s+after\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            rows.append(_clean(match.group("title")))
    return rows


def _title_candidate_is_better(value: str, *, current: str) -> bool:
    candidate = _clean(value).strip(" .")
    if not candidate or candidate == current:
        return False
    words = label_terms(candidate)
    if not 2 <= len(words) <= 8:
        return False
    if words[-1].casefold() in {"a", "an", "and", "for", "from", "in", "of", "on", "or", "the", "to", "with"}:
        return False
    lowered = candidate.casefold()
    if lowered in {"greenfield project", "confirmed project"}:
        return False
    if re.search(r"\b(?:that|what|so that|because|captures?|follows?|make money)\b", lowered):
        return False
    return True


def _project_intelligence_rows(proposal: Mapping[str, Any], key: str) -> tuple[str, ...]:
    intelligence = proposal.get("project_intelligence")
    if not isinstance(intelligence, Mapping):
        return ()
    return text_values(intelligence.get(key))


def _project_intelligence_first_row(proposal: Mapping[str, Any], key: str) -> str:
    rows = _project_intelligence_rows(proposal, key)
    return rows[0] if rows else ""


def _component_system_rows(proposal: Mapping[str, Any]) -> tuple[str, ...]:
    rows: list[str] = []
    for component in mapping_rows(proposal.get("components")):
        label = _clean(component.get("label"))
        description = _clean(component.get("source_system_description")) or _clean(component.get("responsibility"))
        if label and description:
            rows.append(f"{label} - {description}")
        elif label:
            rows.append(label)
    return tuple(rows)


def _replace_title_text(value: Any, *, current: str, replacement: str) -> None:
    if isinstance(value, dict):
        for key, nested in list(value.items()):
            if isinstance(nested, str):
                value[key] = re.sub(re.escape(current), replacement, nested, flags=re.IGNORECASE)
            else:
                _replace_title_text(nested, current=current, replacement=replacement)
    elif isinstance(value, list):
        for index, nested in enumerate(list(value)):
            if isinstance(nested, str):
                value[index] = re.sub(re.escape(current), replacement, nested, flags=re.IGNORECASE)
            else:
                _replace_title_text(nested, current=current, replacement=replacement)


def _first_path(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent")
    if isinstance(intent, Mapping):
        value = _clean(intent.get("first_path"))
        if value:
            return value
    return "One accepted user path completes with state and evidence."


def _proof_boundary(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent")
    if isinstance(intent, Mapping):
        value = _clean(intent.get("proof_boundary"))
        if value:
            return value
    return "Release readiness requires state, validation, replay, and review evidence."


def _state_object(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent")
    if isinstance(intent, Mapping):
        value = _clean(intent.get("state_object"))
        if value:
            return value
    return "accepted product state"


__all__ = ["repair_project_title"]
