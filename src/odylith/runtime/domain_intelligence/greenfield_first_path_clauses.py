"""First-path clause rendering for generated greenfield artifacts."""

from __future__ import annotations

import re
from typing import Any, Sequence

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathClauses
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathModel
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import clip_first_path_phrase as _clip_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import gerund_action_fragment as _gerund_action_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import lowercase_leading_article as _lowercase_leading_article
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import outcome_capability_fragment as _outcome_capability_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_view import FirstPathStepView
from odylith.runtime.domain_intelligence.greenfield_first_path_view import first_path_semantic_view
from odylith.runtime.domain_intelligence.greenfield_first_path_view import first_path_step_view
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import select_visible_result_text




def first_path_capability_phrase(
    value: Any,
    *,
    fallback: str = "accepted first path",
    limit: int = 180,
    gerund: bool = False,
    max_fragments: int = 4,
) -> str:
    """Return a compact action-chain phrase for Radar and project-story prose."""

    model = _model_for(value)
    text = _first_path_capability_text(model, fallback=fallback, limit=limit, gerund=gerund, max_fragments=max_fragments)
    return text or clean_first_path_text(fallback)


def first_path_clauses(
    value: Any,
    *,
    proof_boundary: Any = "",
    action_fallback: str = "complete the first product action",
    capability_fallback: str = "accepted first path",
    outcome_fallback: str = "the promised user-visible result",
    action_limit: int = 220,
    capability_limit: int = 220,
    outcome_limit: int = 220,
) -> FirstPathClauses:
    """Compile a first path once into the clauses shared by all renderers."""

    model = _model_for(value)
    return FirstPathClauses(
        model=model,
        action_chain=_first_path_action_text(model, fallback=action_fallback, limit=action_limit, max_fragments=3),
        capability_chain=_first_path_capability_text(
            model,
            fallback=capability_fallback,
            limit=capability_limit,
            gerund=False,
            max_fragments=7,
        ),
        visible_result=_first_path_outcome_text(
            model,
            proof_boundary=proof_boundary,
            fallback=outcome_fallback,
            limit=outcome_limit,
        ),
    )


def first_path_action_phrase(
    value: Any,
    *,
    fallback: str = "complete the first product action",
    limit: int = 220,
    max_fragments: int = 3,
) -> str:
    """Return only the user-side action chain from a first path."""

    model = _model_for(value)
    return _first_path_action_text(model, fallback=fallback, limit=limit, max_fragments=max_fragments)


def first_path_outcome_phrase(
    value: Any,
    *,
    proof_boundary: Any = "",
    fallback: str = "the promised user-visible result",
    limit: int = 220,
) -> str:
    """Return the object/result a participant can use after the first path."""

    model = _model_for(value)
    return _first_path_outcome_text(model, proof_boundary=proof_boundary, fallback=fallback, limit=limit)


def _model_for(value: Any) -> FirstPathModel:
    from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model

    return first_path_model(value)


def _first_path_capability_text(
    model: FirstPathModel,
    *,
    fallback: str,
    limit: int,
    gerund: bool,
    max_fragments: int,
) -> str:
    view = first_path_semantic_view(model)
    steps = [step for step in view.steps if step.text and not step.is_trivial_start]
    selected: list[FirstPathStepView] = []
    primary_actor = view.primary_actor_signature
    if model.material_action:
        material_step = first_path_step_view(model.material_action)
        if not material_step.is_system_generated:
            selected.append(material_step)
    selected_fragments = {step.fragment_key for step in selected if step.fragment_key}
    included_visible_result = False
    visible_seen = False
    for step in steps:
        fragment_key = step.fragment_key
        if step.is_dash_detail:
            continue
        if fragment_key and fragment_key in selected_fragments:
            continue
        if step.is_system_generated:
            visible_seen = visible_seen or step.is_visible_result
            continue
        step_actor = step.actor_signature
        if step.is_visible_result and primary_actor and step_actor and step_actor != primary_actor:
            if step.visible_object and view.covers_visible_object(step.visible_object):
                included_visible_result = True
            visible_seen = True
            continue
        if primary_actor and step_actor and step_actor != primary_actor and visible_seen:
            continue
        if len(selected) >= max(1, max_fragments):
            break
        if step.is_material_action or step.is_visible_result:
            selected.append(step)
            if step.visible_object and view.covers_visible_object(step.visible_object):
                included_visible_result = True
            if fragment_key:
                selected_fragments.add(fragment_key)
        visible_seen = visible_seen or step.is_visible_result
    fragments = _unique([_step_fragment(step, gerund=gerund) for step in selected])
    if model.visible_outcome and not included_visible_result:
        outcome = view.visible_outcome_object or clean_first_path_text(model.visible_outcome)
        if outcome:
            outcome_fragment = _outcome_capability_fragment(outcome)
            if gerund:
                outcome_fragment = re.sub(r"^(?i:see)\s+", "review ", outcome_fragment).strip(" .")
                outcome_fragment = _gerund_action_fragment(outcome_fragment)
            fragments.append(outcome_fragment)
    if not gerund:
        fragments = _actor_led_capability_fragments(fragments)
    text = _join_fragments_within_limit(fragments[: max(1, max_fragments)], limit=limit) or clean_first_path_text(fallback)
    return _clip_phrase(text, limit=limit) or clean_first_path_text(fallback)


def _first_path_action_text(
    model: FirstPathModel,
    *,
    fallback: str,
    limit: int,
    max_fragments: int,
) -> str:
    view = first_path_semantic_view(model)
    visible = view.visible_outcome_text
    primary_actor = view.primary_actor_signature
    fragments: list[str] = []
    fallback_fragments: list[str] = []
    visible_seen = False
    for step in view.steps:
        visible_object = step.visible_object_key
        if step.is_trivial_start:
            continue
        if step.is_system_generated:
            visible_seen = visible_seen or step.is_visible_result
            continue
        if visible_seen and fragments:
            continue
        if primary_actor and step.actor_signature and step.actor_signature != primary_actor and visible_seen:
            continue
        if fragments and (visible_object == visible or (step.is_visible_result and visible_object)):
            visible_seen = visible_seen or step.is_visible_result
            continue
        fragment = step.fragment
        if step.is_dash_detail:
            continue
        if fragment:
            if not step.is_material_action:
                if not fragments:
                    fallback_fragments.append(fragment)
                visible_seen = visible_seen or step.is_visible_result
                continue
            if step.is_named_product_launcher:
                if not fragments:
                    fallback_fragments.append(fragment)
                visible_seen = visible_seen or step.is_visible_result
                continue
            fragments.append(fragment)
        if len(fragments) >= max(1, max_fragments):
            break
        visible_seen = visible_seen or step.is_visible_result
    if not fragments and model.material_action:
        fragments.append(first_path_step_view(model.material_action).fragment)
    if not fragments:
        fragments.extend(fallback_fragments[: max(1, max_fragments)])
    return _clip_phrase(_join_series(_unique(fragments)), limit=limit) or clean_first_path_text(fallback)


def _step_fragment(step: FirstPathStepView, *, gerund: bool) -> str:
    return _gerund_action_fragment(step.text) if gerund else step.fragment


def _actor_led_capability_fragments(fragments: list[str]) -> list[str]:
    if len(fragments) < 2:
        return fragments
    actor, action = _actor_led_action_parts(fragments[0])
    if not actor or not action:
        return fragments
    return [f"{actor} can {action}", *fragments[1:]]


def _actor_led_action_parts(value: str) -> tuple[str, str]:
    words = clean_first_path_text(value).strip(" .").split()
    for index in range(1, min(len(words), 6)):
        candidate = " ".join(words[index:]).strip(" .")
        if not looks_like_finite_action(candidate):
            continue
        action = base_action_clause(candidate).strip(" .")
        if action and action.casefold() != candidate.casefold():
            return " ".join(words[:index]).strip(" ."), action
    return "", ""


def _first_path_outcome_text(
    model: FirstPathModel,
    *,
    proof_boundary: Any,
    fallback: str,
    limit: int,
) -> str:
    return select_visible_result_text(
        model.raw_path,
        proof_boundary=proof_boundary,
        model=model,
        fallback=fallback,
        limit=limit,
    )


def _join_series(values: Sequence[str]) -> str:
    rows = [clean_first_path_text(value).strip(" .") for value in values if clean_first_path_text(value).strip(" .")]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def _join_fragments_within_limit(values: Sequence[str], *, limit: int) -> str:
    rows = [clean_first_path_text(value).strip(" .") for value in values if clean_first_path_text(value).strip(" .")]
    if not rows:
        return ""
    selected: list[str] = []
    for row in rows:
        candidate = _join_series([*selected, row])
        if len(candidate) <= limit:
            selected.append(row)
            continue
        if selected:
            break
        return _clip_phrase(row, limit=limit)
    return _join_series(selected) or _clip_phrase(rows[0], limit=limit)




def _unique(values: Sequence[str]) -> list[str]:
    return list(unique_text(clean_first_path_text(value) for value in values))


__all__ = [
    "FirstPathClauses",
    "first_path_action_phrase",
    "first_path_capability_phrase",
    "first_path_clauses",
    "first_path_outcome_phrase",
]
