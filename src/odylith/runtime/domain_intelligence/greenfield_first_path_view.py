"""Structured first-path step semantics for confirmed greenfield renderers."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Sequence

from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_first_path_common import MATERIAL_ACTION_RE
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import action_chain_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import actor_signature
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import is_system_generated_action
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import is_trivial_start
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import looks_like_visible_result
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import primary_actor_signature
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import visible_result_object
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathModel
from odylith.runtime.domain_intelligence.greenfield_text import visible_words


@dataclass(frozen=True)
class FirstPathStepView:
    """Precomputed semantic facts for one accepted first-path step."""

    text: str
    fragment: str
    actor_signature: str
    visible_object: str
    is_trivial_start: bool
    is_system_generated: bool
    is_visible_result: bool
    is_material_action: bool
    is_named_product_launcher: bool
    is_dash_detail: bool

    @property
    def fragment_key(self) -> str:
        return self.fragment.casefold()

    @property
    def visible_object_key(self) -> str:
        return clean_first_path_text(self.visible_object).casefold()


@dataclass(frozen=True)
class FirstPathSemanticView:
    """Reusable first-path view shared by action, capability, and outcome renderers."""

    model: FirstPathModel
    steps: tuple[FirstPathStepView, ...]
    primary_actor_signature: str
    visible_outcome_text: str
    visible_outcome_object: str
    dash_detail_fragment_keys: frozenset[str]

    def covers_visible_object(self, value: str) -> bool:
        object_text = clean_first_path_text(value).casefold()
        outcome_text = clean_first_path_text(self.visible_outcome_object or self.visible_outcome_text).casefold()
        if not object_text or not outcome_text:
            return False
        if object_text == outcome_text:
            return True
        object_terms = _semantic_terms(object_text)
        outcome_terms = _semantic_terms(outcome_text)
        return bool(outcome_terms and outcome_terms <= object_terms)


def first_path_semantic_view(model: FirstPathModel) -> FirstPathSemanticView:
    dash_keys = frozenset(_dash_detail_fragment_keys(model))
    return FirstPathSemanticView(
        model=model,
        steps=tuple(first_path_step_view(step, dash_detail_fragment_keys=dash_keys) for step in model.steps),
        primary_actor_signature=primary_actor_signature(model),
        visible_outcome_text=clean_first_path_text(model.visible_outcome).casefold(),
        visible_outcome_object=visible_result_object(model.visible_outcome) or clean_first_path_text(model.visible_outcome),
        dash_detail_fragment_keys=dash_keys,
    )


def first_path_step_view(
    value: str,
    *,
    dash_detail_fragment_keys: frozenset[str] = frozenset(),
) -> FirstPathStepView:
    text = clean_first_path_text(value).strip(" .")
    fragment = action_chain_fragment(text)
    visible_object = visible_result_object(text)
    visible = bool(visible_object and looks_like_visible_result(text))
    return FirstPathStepView(
        text=text,
        fragment=fragment,
        actor_signature=actor_signature(text),
        visible_object=visible_object,
        is_trivial_start=is_trivial_start(text),
        is_system_generated=is_system_generated_action(text),
        is_visible_result=visible,
        is_material_action=bool(fragment and looks_like_action_clause(fragment)),
        is_named_product_launcher=_is_named_product_launcher_fragment(fragment),
        is_dash_detail=bool(fragment and fragment.casefold() in dash_detail_fragment_keys),
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


def _is_named_product_launcher_fragment(fragment: str) -> bool:
    return bool(
        re.match(
            r"^(?i:open|launch|start)\s+[A-Z][A-Za-z0-9_-]{2,40}\b\s*$",
            clean_first_path_text(fragment),
        )
    )


def _semantic_terms(value: str) -> set[str]:
    return {
        word.casefold()
        for word in visible_words(value)
        if len(word) >= 4 and word.casefold() not in {"that", "this", "with", "when", "what"}
    }


__all__ = [
    "FirstPathSemanticView",
    "FirstPathStepView",
    "first_path_semantic_view",
    "first_path_step_view",
]
