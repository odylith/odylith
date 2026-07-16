"""First-path clause rendering for generated greenfield artifacts."""

from __future__ import annotations

import re
from typing import Any, Sequence

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import gerund_action_verb
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_first_path_common import MATERIAL_ACTION_RE
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clip_first_path_phrase as _clip_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_common import (
    lowercase_leading_article as _lowercase_leading_article,
)
from odylith.runtime.domain_intelligence.greenfield_actor_led_prefix import looks_like_actor_led_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathClauses
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathModel
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import actor_led_action_parts as _source_actor_led_action_parts
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import gerund_action_fragment as _gerund_action_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import outcome_capability_fragment as _outcome_capability_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_noun_compounds import action_word_inside_compound_noun
from odylith.runtime.domain_intelligence.greenfield_first_path_view import FirstPathStepView
from odylith.runtime.domain_intelligence.greenfield_first_path_view import first_path_semantic_view
from odylith.runtime.domain_intelligence.greenfield_first_path_view import first_path_step_view
from odylith.runtime.domain_intelligence.greenfield_first_path_step_roles import is_supporting_setup_step
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


def readable_action_chain_phrase(
    value: Any,
    *,
    fallback: str = "complete the accepted product path",
    limit: int = 220,
    max_steps: int = 4,
    include_visible_results: bool = False,
    include_system_steps: bool = False,
    preserve_source_actions: bool = False,
) -> str:
    """Return a step-view action phrase for prose fields that cannot carry long lists."""

    text = clean_first_path_text(value).strip(" ,.")
    fallback_text = clean_first_path_text(fallback).strip(" ,.")
    if not text:
        text = fallback_text
    if not text:
        return ""
    model = _model_for(text)
    rows = _readable_action_steps(
        model,
        max_steps=max_steps,
        include_visible_results=include_visible_results,
        include_system_steps=include_system_steps,
        preserve_source_actions=preserve_source_actions,
    )
    candidate = _join_step_rows_within_limit(rows, limit=limit)
    if candidate:
        return candidate
    fallback_fragment = _readable_action_step_fragment(
        text,
        preserve_source_action=preserve_source_actions,
    )
    return _clip_phrase(fallback_fragment, limit=limit).strip(" ,.") or fallback_text


def readable_action_chain_sentence(
    value: Any,
    *,
    fallback: str = "complete the accepted product path",
    limit: int = 220,
    max_steps: int = 4,
    include_visible_results: bool = False,
) -> str:
    """Return a prose-safe action chain for fields that are later split as lists."""

    text = clean_first_path_text(value).strip(" ,.")
    fallback_text = clean_first_path_text(fallback).strip(" ,.")
    if not text:
        text = fallback_text
    if not text:
        return ""
    model = _model_for(text)
    rows = _readable_action_steps(model, max_steps=max_steps, include_visible_results=include_visible_results)
    candidate = _join_fragments_within_limit(rows, limit=limit)
    if candidate:
        return candidate
    return _clip_phrase(_readable_action_step_fragment(text), limit=limit).strip(" ,.") or fallback_text


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
    setup_fallbacks: list[FirstPathStepView] = []
    primary_actor = view.primary_actor_signature
    included_visible_result = False
    if model.material_action:
        material_step = first_path_step_view(model.material_action)
        if not material_step.is_system_generated and not is_supporting_setup_step(material_step.text):
            selected.append(material_step)
            if material_step.visible_object and view.covers_visible_object(material_step.visible_object):
                included_visible_result = True
    selected_fragments = {step.fragment_key for step in selected if step.fragment_key}
    visible_seen = False
    for step in steps:
        fragment_key = step.fragment_key
        if step.is_dash_detail:
            continue
        if is_supporting_setup_step(step.text):
            setup_fallbacks.append(step)
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
    if not fragments and setup_fallbacks:
        fragments = _unique([_step_fragment(step, gerund=gerund) for step in setup_fallbacks[: max(1, max_fragments)]])
    if model.visible_outcome and not included_visible_result:
        visible_action = first_path_step_view(model.visible_outcome).fragment
        if visible_action and _fragment_already_present(visible_action, fragments):
            included_visible_result = True
    if model.visible_outcome and not included_visible_result:
        outcome = view.visible_outcome_object or clean_first_path_text(model.visible_outcome)
        if outcome:
            outcome_fragment = _outcome_capability_fragment(outcome)
            if gerund:
                outcome_fragment = re.sub(r"^(?i:see)\s+", "review ", outcome_fragment).strip(" .")
                outcome_fragment = _gerund_action_fragment(outcome_fragment)
            if not _fragment_already_present(outcome_fragment, fragments):
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
        if is_supporting_setup_step(step.text):
            if step.fragment and not fragments:
                fallback_fragments.append(step.fragment)
            visible_seen = visible_seen or step.is_visible_result
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
            if _is_context_setup_step(step):
                if not fragments:
                    fallback_fragments.append(fragment)
                visible_seen = visible_seen or step.is_visible_result
                continue
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


def _is_context_setup_step(step: FirstPathStepView) -> bool:
    if is_supporting_setup_step(step.text):
        return True
    text = clean_first_path_text(step.fragment or step.text).casefold()
    return bool(
        re.match(
            r"^(?:a|an|the)?\s*[a-z0-9 /'-]{0,60}\b(?:notice|notices|observe|observes|spot|spots|recognize|recognizes)\b",
            text,
        )
    )


def _step_fragment(step: FirstPathStepView, *, gerund: bool) -> str:
    if not gerund:
        return step.fragment
    _actor, actor_action = _source_actor_led_action_parts(step.text)
    if actor_action:
        compact = _gerund_action_fragment(actor_action)
        preserved = _gerund_action_fragment(actor_action, preserve_action_source=True)
        if _material_action_was_lost(actor_action, compact):
            return preserved
        return compact
    return _gerund_action_fragment(step.fragment or step.text)


def _material_action_was_lost(source: str, rendered: str) -> bool:
    """Keep an accepted action when result extraction treats an adjective as a verb."""

    rendered_terms = {term.casefold() for term in re.findall(r"[A-Za-z]+", rendered)}
    for match in MATERIAL_ACTION_RE.finditer(source):
        if action_word_inside_compound_noun(source, match.start()):
            continue
        gerund = gerund_action_verb(match.group(0))
        return bool(gerund and gerund not in rendered_terms)
    return False


def _readable_action_steps(
    model: FirstPathModel,
    *,
    max_steps: int,
    include_visible_results: bool = False,
    include_system_steps: bool = False,
    preserve_source_actions: bool = False,
) -> list[str]:
    view = first_path_semantic_view(model)
    rows: list[str] = []
    for step in view.steps:
        if step.is_trivial_start or step.is_dash_detail or is_supporting_setup_step(step.text):
            continue
        if step.is_system_generated and not include_system_steps:
            continue
        if step.is_visible_result and not include_visible_results:
            continue
        fragment_source = step.text if preserve_source_actions else step.fragment or step.text
        fragment = _readable_action_step_fragment(
            fragment_source,
            preserve_source_action=preserve_source_actions,
        )
        if fragment:
            rows.append(fragment)
        if len(rows) >= max(1, max_steps):
            break
    if rows:
        return _unique(rows)
    fallback = _readable_action_step_fragment(model.material_action)
    return [fallback] if fallback else []


def _readable_action_step_fragment(value: str, *, preserve_source_action: bool = False) -> str:
    text = clean_first_path_text(value).strip(" ,.")
    if not text:
        return ""
    if preserve_source_action:
        _actor, actor_action = _actor_led_action_parts(text)
        if actor_action:
            text = actor_action
        text = base_action_clause(text).strip(" ,.")
        return text
    if text.count(",") < 2:
        return text
    head = text.split(",", 1)[0].strip(" ,.")
    if not head:
        return _clip_phrase(text, limit=92).strip(" ,.")
    first = head.split(maxsplit=1)[0].casefold().strip(" ,.;:")
    if first in {
        "add",
        "capture",
        "choose",
        "configure",
        "describe",
        "enter",
        "import",
        "log",
        "provide",
        "record",
        "request",
        "select",
        "submit",
        "upload",
    }:
        return f"{head} and related inputs"
    return _clip_phrase(head, limit=92).strip(" ,.")


def _join_step_rows_within_limit(values: Sequence[str], *, limit: int) -> str:
    rows = [clean_first_path_text(value).strip(" ,.") for value in values if clean_first_path_text(value).strip(" ,.")]
    if not rows:
        return ""
    selected: list[str] = []
    for row in rows:
        candidate = "; ".join([*selected, row])
        if len(candidate) <= limit:
            selected.append(row)
            continue
        if selected:
            break
        return _clip_phrase(row, limit=limit).strip(" ,.")
    return "; ".join(selected).strip(" ,.")


def _actor_led_capability_fragments(fragments: list[str]) -> list[str]:
    if not fragments:
        return fragments
    actor, action = _actor_led_action_parts(fragments[0])
    if not actor or not action:
        return fragments
    return [f"{actor} can {action}", *fragments[1:]]


def _actor_led_action_parts(value: str) -> tuple[str, str]:
    words = clean_first_path_text(value).strip(" .").split()
    for index in range(1, min(len(words), 6)):
        prefix = " ".join(words[:index]).strip(" .")
        if not looks_like_actor_led_subject_prefix(prefix, value):
            continue
        candidate = " ".join(words[index:]).strip(" .")
        if not looks_like_finite_action(candidate):
            continue
        action = base_action_clause(candidate).strip(" .")
        if action and action.casefold() != candidate.casefold():
            return prefix, action
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


def _fragment_already_present(fragment: str, existing: Sequence[str]) -> bool:
    key = _fragment_key(fragment)
    return bool(key and any(_fragment_key(value) == key for value in existing))


def _fragment_key(value: str) -> tuple[str, ...]:
    text = clean_first_path_text(value).casefold().strip(" .")
    text = re.sub(r"^(?:reach|review|see|use)\s+(?:a|an|the|this|that|one)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:a|an|the|this|that|one)\s+", "", text, flags=re.IGNORECASE)
    return tuple(re.findall(r"[a-z0-9]+", text))




def _unique(values: Sequence[str]) -> list[str]:
    return list(unique_text(clean_first_path_text(value) for value in values))


__all__ = [
    "FirstPathClauses",
    "first_path_action_phrase",
    "first_path_capability_phrase",
    "first_path_clauses",
    "first_path_outcome_phrase",
    "readable_action_chain_phrase",
    "readable_action_chain_sentence",
]
