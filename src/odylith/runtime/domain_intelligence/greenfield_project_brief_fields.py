"""Structured field builders for confirmed greenfield project briefs."""

from __future__ import annotations

import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_actor_labels import actor_display_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import is_deferred_actor
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import boundary_clause_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_confirmed_items
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import state_detail_restates_label_with_finite_action
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import state_detail_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count


def actor_boundary_text(items: list[str] | None, *, project_focus: str = "", limit: int = 4) -> str:
    values = [actor_boundary_item(item, project_focus=project_focus) for item in (items or []) if str(item or "").strip()]
    return join_confirmed_items([value for value in values if value][:limit])


def actor_boundary_item(value: str, *, project_focus: str = "") -> str:
    text = compact_text(value).strip(" .")
    if not text:
        return ""
    label, separator, _body = split_actor_boundary_item(text)
    if separator and label:
        label = actor_display_label(text, project_focus=project_focus) or label
        if is_deferred_actor(text):
            return f"{label} deferred from the first path"
        return label
    return actor_display_label(text, project_focus=project_focus) or boundary_clause_text([text])


def split_actor_boundary_item(value: str) -> tuple[str, str, str]:
    for separator in (":", " \u2014 ", " \u2013 ", " - "):
        head, matched, body = value.partition(separator)
        label = compact_text(head).strip(" .:-")
        detail = compact_text(body).strip(" .")
        if matched and label and word_count(label) <= 10:
            return label, matched, detail
    return "", "", ""


def brief_option(identifier: str, decision: str, recommended: str, impact: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "decision": decision,
        "recommended": recommended,
        "choices": ["accept default", "revise before apply", "defer from first release"],
        "impact": impact,
    }


def state_reference_text(state_object: str, *, state_label: str) -> str:
    text = compact_text(state_object)
    if text and ":" not in text:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        if len(sentences) <= 1:
            detail = state_detail_summary(text, state_label=state_label, limit=220)
            if (
                detail
                and not detail.casefold().endswith((" and", " for", " of", " through", " with"))
                and not state_detail_restates_label_with_finite_action(detail, state_label=state_label)
            ):
                return sentence_label(detail)
    return sentence_label(state_label)


def checkpoint(name: str, question: str) -> dict[str, str]:
    done_when_by_name = {
        "product story accepted": "Done when the accepted brief names the user, problem, first path, and deferred scope in one readable story.",
        "state ownership accepted": (
            "Done when one named component is accountable for accepted state, version history, "
            "and review responsibility clearly enough to plan implementation."
        ),
        "evidence path accepted": "Done when reviewers can tell which evidence proves the result without relying on implementation prose.",
        "release proof accepted": "Done when release gates block promotion unless the promised result, replay evidence, and review evidence are present.",
    }
    return {
        "checkpoint": name,
        "operator_question": question,
        "done_when": done_when_by_name.get(
            name.casefold(),
            "Done when the accepted proposal gives this checkpoint a named owner, decision, and verification target.",
        ),
    }


__all__ = ["actor_boundary_text", "brief_option", "checkpoint", "state_reference_text"]
