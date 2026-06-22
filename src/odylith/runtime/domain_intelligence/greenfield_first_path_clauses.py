"""First-path clause rendering for generated greenfield artifacts."""

from __future__ import annotations

import re
from typing import Any, Sequence

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathClauses
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathModel
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import MATERIAL_ACTION_RE
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import action_chain_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import actor_signature as _actor_signature
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import clean_visible_result_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import clip_first_path_phrase as _clip_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import gerund_action_fragment as _gerund_action_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import is_system_generated_action
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import is_trivial_start
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import leading_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import looks_like_visible_result
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import lowercase_leading_article as _lowercase_leading_article
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import outcome_capability_fragment as _outcome_capability_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import primary_actor_signature as _primary_actor_signature
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import visible_result_object
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.greenfield_text import visible_words
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
    steps = [step for step in model.steps if step and not is_trivial_start(step)]
    selected: list[str] = []
    primary_actor = _primary_actor_signature(model)
    dash_detail_keys = _dash_detail_fragment_keys(model)
    if model.material_action and not is_system_generated_action(model.material_action):
        selected.append(model.material_action)
    selected_fragments = {action_chain_fragment(row).casefold() for row in selected if action_chain_fragment(row)}
    model_visible_object = visible_result_object(model.visible_outcome) or clean_first_path_text(model.visible_outcome)
    included_visible_result = False
    visible_seen = False
    for step in steps:
        fragment = action_chain_fragment(step)
        fragment_key = fragment.casefold()
        if fragment_key and fragment_key in dash_detail_keys:
            continue
        if fragment_key and fragment_key in selected_fragments:
            continue
        visible_object = visible_result_object(step)
        visible_step = bool(visible_object and looks_like_visible_result(step))
        if is_system_generated_action(step):
            visible_seen = visible_seen or visible_step
            continue
        if primary_actor and _actor_signature(step) and _actor_signature(step) != primary_actor and visible_seen:
            continue
        if len(selected) >= max(1, max_fragments):
            break
        if (fragment and _is_material_action_step(fragment)) or re.search(
            r"\b(?:display|displays|produce|produces|render|renders|return|returns|see|sees|show|shows|view|views|review|reviews|receive|receives)\b",
            step,
            re.IGNORECASE,
        ):
            selected.append(step)
            if visible_object and _visible_outcome_covered(visible_object, model_visible_object):
                included_visible_result = True
            if fragment_key:
                selected_fragments.add(fragment_key)
        visible_seen = visible_seen or visible_step
    fragmenter = _gerund_action_fragment if gerund else action_chain_fragment
    fragments = _unique([fragmenter(step) for step in selected])
    if model.visible_outcome and not included_visible_result:
        outcome = visible_result_object(model.visible_outcome) or clean_first_path_text(model.visible_outcome)
        if outcome:
            outcome_fragment = _outcome_capability_fragment(outcome)
            if gerund:
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
    visible = clean_first_path_text(model.visible_outcome).casefold()
    primary_actor = _primary_actor_signature(model)
    fragments: list[str] = []
    fallback_fragments: list[str] = []
    dash_detail_keys = _dash_detail_fragment_keys(model)
    visible_seen = False
    for step in model.steps:
        visible_object = clean_first_path_text(visible_result_object(step)).casefold()
        visible_step = bool(visible_object and looks_like_visible_result(step))
        if is_trivial_start(step):
            continue
        if is_system_generated_action(step):
            visible_seen = visible_seen or visible_step
            continue
        if visible_seen and fragments:
            continue
        if primary_actor and _actor_signature(step) and _actor_signature(step) != primary_actor and visible_seen:
            continue
        if fragments and (visible_object == visible or (looks_like_visible_result(step) and visible_object)):
            visible_seen = visible_seen or visible_step
            continue
        fragment = action_chain_fragment(step)
        if fragment.casefold() in dash_detail_keys:
            continue
        if fragment:
            if not _is_material_action_step(fragment):
                if not fragments:
                    fallback_fragments.append(fragment)
                visible_seen = visible_seen or visible_step
                continue
            if _is_named_product_launcher_fragment(fragment):
                if not fragments:
                    fallback_fragments.append(fragment)
                visible_seen = visible_seen or visible_step
                continue
            fragments.append(fragment)
        if len(fragments) >= max(1, max_fragments):
            break
        visible_seen = visible_seen or visible_step
    if not fragments and model.material_action:
        fragments.append(action_chain_fragment(model.material_action))
    if not fragments:
        fragments.extend(fallback_fragments[: max(1, max_fragments)])
    return _clip_phrase(_join_series(_unique(fragments)), limit=limit) or clean_first_path_text(fallback)


def _is_material_action_step(fragment: str) -> bool:
    return bool(looks_like_action_clause(fragment))


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


def _is_named_product_launcher_fragment(fragment: str) -> bool:
    return bool(
        re.match(
            r"^(?i:open|launch|start)\s+[A-Z][A-Za-z0-9_-]{2,40}\b\s*$",
            clean_first_path_text(fragment),
        )
    )


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


def _dash_detail_fragment_keys(model: FirstPathModel) -> set[str]:
    first_sentence = re.split(r"(?<=[.!?])\s+", clean_first_path_text(model.raw_path), maxsplit=1)[0]
    parts = re.split(r"\s+[–—-]\s+", first_sentence, maxsplit=1)
    if len(parts) != 2 or not MATERIAL_ACTION_RE.search(parts[0]):
        return set()
    keys: set[str] = set()
    for piece in re.split(r"\s*,\s*|\s+and\s+", parts[1]):
        fragment = action_chain_fragment(piece)
        if fragment:
            keys.add(fragment.casefold())
    return keys


def _visible_outcome_covered(visible_object: str, visible_outcome: str) -> bool:
    object_text = clean_first_path_text(visible_object).casefold()
    outcome_text = clean_first_path_text(visible_outcome).casefold()
    if not object_text or not outcome_text:
        return False
    if object_text == outcome_text:
        return True
    object_terms = _semantic_terms(object_text)
    outcome_terms = _semantic_terms(outcome_text)
    return bool(outcome_terms and outcome_terms <= object_terms)


def _semantic_terms(value: str) -> set[str]:
    return {
        word.casefold()
        for word in visible_words(value)
        if len(word) >= 4 and word.casefold() not in {"that", "this", "with", "when", "what"}
    }


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
