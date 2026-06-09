"""Semantic-model compiler for confirmed greenfield apply payloads."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_model import build_greenfield_semantic_model
from odylith.runtime.domain_intelligence.greenfield_semantic_model import semantic_model_mapping
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values


def ensure_apply_semantic_model(proposal: dict[str, Any], *, refresh: bool = False) -> dict[str, Any]:
    """Compile legacy confirmed apply payloads into the post-confirm semantic model."""

    if not refresh and isinstance(proposal.get("semantic_model"), Mapping):
        return proposal
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    brief = proposal.get("project_brief") if isinstance(proposal.get("project_brief"), Mapping) else {}
    release_plan = proposal.get("release_plan") if isinstance(proposal.get("release_plan"), Mapping) else {}
    backlog_rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    title = clean_text(intent.get("title")) or clean_text(proposal.get("title")) or "Greenfield Project"
    state_object = clean_text(intent.get("state_object")) or clean_text(brief.get("state_object")) or f"{title} state"
    first_path = _first_path_text(title=title, intent=intent, brief=brief, backlog_rows=backlog_rows)
    proof_boundary = (
        clean_text(intent.get("proof_boundary"))
        or clean_text(brief.get("proof"))
        or clean_text(release_plan.get("promotion_criteria"))
        or " ".join(clean_text(value) for value in text_values(proposal.get("validation_strategy")) if clean_text(value))
        or f"{title} proof links state, visible result, validation, and release evidence"
    )
    proposal["semantic_model"] = semantic_model_mapping(
        build_greenfield_semantic_model(
            title=title,
            state_object=state_object,
            first_path=first_path,
            proof_boundary=proof_boundary,
            components=[row for row in proposal.get("components", []) if isinstance(row, Mapping)],
            human_actors=text_values(intent.get("human_actors")),
            internal_systems=text_values(intent.get("internal_systems")),
            external_systems=text_values(intent.get("external_systems")),
            non_goals=text_values(proposal.get("non_goals") or intent.get("non_goals")),
            workstreams=backlog_rows,
        )
    )
    return proposal


def _first_path_text(*, title: str, intent: Mapping[str, Any], brief: Mapping[str, Any], backlog_rows: list[Mapping[str, Any]]) -> str:
    first_path = (
        clean_text(intent.get("first_path"))
        or clean_text(brief.get("first_path"))
        or _first_nonempty_backlog_value(backlog_rows, "recommended_first_slice")
        or _first_nonempty_backlog_value(backlog_rows, "product_view")
        or clean_text(intent.get("summary"))
        or f"{title} creates, preserves, and reviews the accepted first-path result"
    )
    if not _VISIBLE_RESULT_RE.search(first_path):
        first_path = f"{first_path}, then shows the accepted result for review."
    return first_path


def _first_nonempty_backlog_value(rows: list[Mapping[str, Any]], key: str) -> str:
    for row in rows:
        value = clean_text(row.get(key))
        if value:
            return value
    return ""


_VISIBLE_RESULT_RE = re.compile(
    r"\b(?:available|choose|chooses|compare|compares|find|finds|highlight|highlights|inspect|inspects|ready|report|reports|save|saves|saved|see|sees|select|selects|show|shows|view|views|viewable|review|reviews|receive|receives|publish|publishes|restored)\b",
    re.IGNORECASE,
)


__all__ = ["ensure_apply_semantic_model"]
