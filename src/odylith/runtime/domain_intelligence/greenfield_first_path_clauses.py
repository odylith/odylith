"""First-path clause rendering for generated greenfield artifacts."""

from __future__ import annotations

import re
from typing import Any, Sequence

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
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    nominal_visible_result_object as _nominal_visible_result_object,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import outcome_capability_fragment as _outcome_capability_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import primary_actor_signature as _primary_actor_signature
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import visible_result_object
from odylith.runtime.domain_intelligence.greenfield_text import unique_text




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
    included_visible_result = False
    visible_seen = False
    for step in steps:
        fragment_key = action_chain_fragment(step).casefold()
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
        if visible_object and clean_first_path_text(visible_object).casefold() == clean_first_path_text(model.visible_outcome).casefold():
            included_visible_result = True
        if len(selected) >= max(1, max_fragments):
            break
        if MATERIAL_ACTION_RE.search(step) or re.search(
            r"\b(?:display|displays|produce|produces|render|renders|return|returns|see|sees|show|shows|view|views|review|reviews|receive|receives)\b",
            step,
            re.IGNORECASE,
        ):
            selected.append(step)
            if fragment_key:
                selected_fragments.add(fragment_key)
        visible_seen = visible_seen or visible_step
    fragmenter = _gerund_action_fragment if gerund else action_chain_fragment
    fragments = _unique([fragmenter(step) for step in selected])
    if not gerund and model.visible_outcome and not included_visible_result:
        outcome = visible_result_object(model.visible_outcome) or clean_first_path_text(model.visible_outcome)
        if outcome:
            fragments.append(_outcome_capability_fragment(outcome))
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
        if primary_actor and _actor_signature(step) and _actor_signature(step) != primary_actor and visible_seen:
            continue
        if fragments and (visible_object == visible or (looks_like_visible_result(step) and visible_object)):
            visible_seen = visible_seen or visible_step
            continue
        fragment = action_chain_fragment(step)
        if fragment.casefold() in dash_detail_keys:
            continue
        if fragment:
            fragments.append(fragment)
        if len(fragments) >= max(1, max_fragments):
            break
        visible_seen = visible_seen or visible_step
    if not fragments and model.material_action:
        fragments.append(action_chain_fragment(model.material_action))
    return _clip_phrase(_join_series(_unique(fragments)), limit=limit) or clean_first_path_text(fallback)


def _first_path_outcome_text(
    model: FirstPathModel,
    *,
    proof_boundary: Any,
    fallback: str,
    limit: int,
) -> str:
    visible = clean_first_path_text(model.visible_outcome)
    proof = clean_first_path_text(proof_boundary)
    text = proof if _is_low_information_visible_outcome(visible) and proof else visible or proof or clean_first_path_text(model.raw_path)
    text = visible_result_object(text) or action_chain_fragment(text) or text
    if _starts_with_unanchored_result_pronoun(text) and proof:
        proof_result = visible_result_object(proof) or action_chain_fragment(proof) or proof
        proof_result = _visible_proof_result_clause(proof_result)
        if proof_result and not _starts_with_unanchored_result_pronoun(proof_result):
            text = proof_result
    text = _nominal_visible_result_object(text)
    text = re.sub(r"^(?:her|his|its|our|their|your)\s+", "", text, flags=re.IGNORECASE)
    text = _lowercase_leading_article(text)
    text = re.sub(r"^(?:Her|His|Its|It|Our|Them|Their|They|This|That|Your)\b", lambda match: match.group(0).casefold(), text)
    return _clip_phrase(text, limit=limit) or clean_first_path_text(fallback)


def _is_low_information_visible_outcome(value: str) -> bool:
    text = clean_first_path_text(value).casefold().strip(" .")
    return text in {
        "next action",
        "next step",
        "the next action",
        "the next step",
        "what happened next",
        "what happens next",
    }


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


def _starts_with_unanchored_result_pronoun(value: str) -> bool:
    return bool(re.match(r"^(?:it|them|they|this|that)\b", clean_first_path_text(value), flags=re.IGNORECASE))


def _visible_proof_result_clause(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    for marker in (", and ", "; and ", ". And "):
        if marker not in text:
            continue
        head, tail = text.split(marker, 1)
        if _looks_like_state_or_recovery_clause(tail):
            return head.strip(" ,.;")
    return text


def _looks_like_state_or_recovery_clause(value: str) -> bool:
    words = {word.strip(".,;:").casefold() for word in clean_first_path_text(value).split()}
    return bool(
        words
        & {
            "blocked",
            "corrected",
            "correction",
            "degraded",
            "fallback",
            "missing",
            "recover",
            "recovery",
            "remain",
            "remains",
            "replay",
            "replayed",
            "replayable",
            "understandable",
        }
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
