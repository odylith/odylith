"""Semantic compiler checks for confirmed greenfield generation.

The compiler separates product-result facts from proof-boundary facts before
renderers project Radar, Registry, Atlas, and Compass artifacts. That boundary
is the invariant that keeps a release proof sentence from becoming the user
visible result.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import re
from typing import Any

from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_actor_roles import has_actor_role_word
from odylith.runtime.domain_intelligence.greenfield_actor_terms import word_has_actor_role_signal
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clip_first_path_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_common import lowercase_leading_article
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import contains_word_sense_metadata_clause
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import is_declarative_visible_result_prefix
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import is_requirement_control_step
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import is_scope_or_deferred_statement
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import strip_requirement_control_tail
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    action_chain_fragment,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    actor_signature,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    nominal_visible_result_object,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    nominal_action_result_object,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    visible_result_object,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathModel
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import object_reference_phrase
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_release_scope_limits import strip_release_scope_limit_text
from odylith.runtime.domain_intelligence.greenfield_semantic_projection_surfaces import projection_text_values
from odylith.runtime.domain_intelligence.greenfield_semantic_projection_surfaces import semantic_projection_values
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import normalize_visible_result_language
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import word_count

SEMANTIC_COMPILER_VERSION = "odylith.greenfield.semantic_compiler.v1"
_NON_HUMAN_WORKFLOW_SUBJECT_TERMS = frozenset(
    """
    approval case claim decision evidence finding handoff note notes proof recommendation record report result review state
    status summary view workflow
    """.split()
)
_FINITE_ACTION_PATTERN = action_verb_pattern(include_base=False, include_finite=True)


@dataclass(frozen=True)
class GreenfieldSemanticCandidate:
    role: str
    text: str
    source_kind: str
    source_path: str
    confidence: float
    provenance: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GreenfieldSemanticCounterexample:
    code: str
    path: str
    message: str
    severity: str
    repair_hint: str

    def to_issue(self) -> str:
        return f"GreenfieldSemanticCompiler {self.path}: {self.message}"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class GreenfieldSemanticCompilerReport:
    version: str
    status: str
    visible_result: GreenfieldSemanticCandidate
    counterexamples: tuple[GreenfieldSemanticCounterexample, ...]
    quality_scores: Mapping[str, float]

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "status": self.status,
            "visible_result": self.visible_result.to_dict(),
            "counterexamples": [item.to_dict() for item in self.counterexamples],
            "quality_scores": dict(self.quality_scores),
        }


def has_visible_object_list_result(value: Any) -> bool:
    """Return whether source text carries a coordinated, reviewable result object list."""

    return _is_visible_object_list_result(clean_first_path_text(value))


def select_visible_result_candidate(
    first_path: Any,
    *,
    proof_boundary: Any = "",
    product_view: Any = "",
    state_object: Any = "",
    model: FirstPathModel | None = None,
    fallback: str = "the promised user-visible result",
    limit: int = 220,
) -> GreenfieldSemanticCandidate:
    """Choose the product result from first-path events before proof text."""

    path_model = model or first_path_model(first_path)
    proof = clean_first_path_text(proof_boundary)
    candidates: list[GreenfieldSemanticCandidate] = []
    proof_candidate: GreenfieldSemanticCandidate | None = None
    first_path_text = clean_first_path_text(first_path)
    visible_source = (
        first_path_text
        if _is_visible_object_list_result(first_path_text)
        and not any(
            _is_actor_led_material_action_candidate(step)
            or _actor_text_has_human_signal(actor_signature(step))
            for step in path_model.steps
        )
        else path_model.visible_outcome
    )
    visible = _product_result_from_visible_outcome(visible_source)
    if visible:
        candidates.append(
            _candidate(
                text=visible,
                source_kind="first_path_event",
                source_path="first_path.visible_result",
                confidence=_candidate_confidence(visible, source_kind="first_path_event")
                + _terminal_visible_outcome_bonus(visible),
                provenance=(visible_source,),
                limit=limit,
            )
        )
    for index, step in reversed(tuple(enumerate(path_model.steps, start=1))):
        result = _product_result_from_visible_outcome(step)
        if (is_requirement_control_step(step) or is_scope_or_deferred_statement(step)) and not (
            result and _candidate_is_product_result(result) and _clause_carries_material_result(step, result)
        ):
            continue
        if not result:
            continue
        candidates.append(
            _candidate(
                text=result,
                source_kind="first_path_event",
                source_path=f"first_path.events.{index}",
                confidence=_step_visible_result_confidence(result, step=step, path_model=path_model),
                provenance=(step,),
                limit=limit,
            )
        )
    context_result, context_source, context_provenance = _product_result_from_intent_context(
        product_view=product_view,
        state_object=state_object,
    )
    if context_result:
        candidates.append(
            _candidate(
                text=context_result,
                source_kind="intent_context",
                source_path=context_source,
                confidence=_candidate_confidence(context_result, source_kind="intent_context"),
                provenance=context_provenance,
                limit=limit,
            )
        )
    proof_result = _product_result_from_proof_boundary(proof)
    if proof_result:
        proof_candidate = _candidate(
            text=proof_result,
            source_kind="proof_boundary",
            source_path="proof_boundary",
            confidence=_candidate_confidence(proof_result, source_kind="proof_boundary"),
            provenance=(proof,),
            limit=limit,
        )
        candidates.append(proof_candidate)
    accepted = [candidate for candidate in candidates if _candidate_is_product_result(candidate.text)]
    if accepted:
        accepted.sort(
            key=lambda item: (
                _candidate_source_priority(item),
                _candidate_semantic_priority(item),
                item.confidence,
                _candidate_event_ordinal(item),
            ),
            reverse=True,
        )
        best = accepted[0]
        if proof_candidate and _proof_candidate_refines_pronoun_result(best, proof_candidate, path_model=path_model):
            return _refined_pronoun_result_candidate(best, proof_candidate)
        return best
    return _candidate(
        text=clean_first_path_text(fallback),
        source_kind="fallback",
        source_path="fallback",
        confidence=0.1,
        provenance=(),
        limit=limit,
    )


def select_visible_result_text(
    first_path: Any,
    *,
    proof_boundary: Any = "",
    product_view: Any = "",
    state_object: Any = "",
    model: FirstPathModel | None = None,
    fallback: str = "the promised user-visible result",
    limit: int = 220,
) -> str:
    return select_visible_result_candidate(
        first_path,
        proof_boundary=proof_boundary,
        product_view=product_view,
        state_object=state_object,
        model=model,
        fallback=fallback,
        limit=limit,
    ).text


def compile_greenfield_semantics(proposal: Mapping[str, Any]) -> GreenfieldSemanticCompilerReport:
    intent = _intent_mapping(proposal)
    semantic = proposal.get("semantic_model") if isinstance(proposal.get("semantic_model"), Mapping) else {}
    first_path = _first_nonempty(intent.get("first_path"))
    proof = _first_nonempty(intent.get("proof_boundary"))
    visible = select_visible_result_candidate(
        first_path,
        proof_boundary=proof,
        product_view=intent.get("product_view"),
        state_object=intent.get("state_object"),
    )
    counterexamples: list[GreenfieldSemanticCounterexample] = []
    counterexamples.extend(_intent_fact_counterexamples(first_path=first_path, proof_boundary=proof))
    counterexamples.extend(
        _first_path_subject_counterexamples(
            first_path,
            human_actors=text_values(intent.get("human_actors")),
        )
    )
    counterexamples.extend(_visible_result_counterexamples(semantic, visible, proof=proof))
    counterexamples.extend(_projection_counterexamples(proposal, visible, proof=proof))
    counterexamples = list(_unique_counterexamples(counterexamples))
    return GreenfieldSemanticCompilerReport(
        version=SEMANTIC_COMPILER_VERSION,
        status="failed" if counterexamples else "passed",
        visible_result=visible,
        counterexamples=tuple(counterexamples),
        quality_scores=_quality_scores(visible, counterexamples),
    )


def semantic_compiler_issues(proposal: Mapping[str, Any]) -> list[str]:
    return [counterexample.to_issue() for counterexample in compile_greenfield_semantics(proposal).counterexamples]


def repair_greenfield_semantic_projections(proposal: dict[str, Any]) -> bool:
    """Clear poisoned generated fields so existing completion owners rebuild them."""

    changed = False
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), dict) else proposal
    if isinstance(intent, dict):
        changed |= repair_confirmed_intent_semantic_projections(intent)
    if isinstance(proposal.get("backlog"), list):
        intent_map = _intent_mapping(proposal)
        first_path = _first_nonempty(intent_map.get("first_path"), _project_brief_value(proposal, "first_path"))
        proof = _first_nonempty(intent_map.get("proof_boundary"), _project_brief_value(proposal, "proof"))
        visible = select_visible_result_candidate(
            first_path,
            proof_boundary=proof,
            product_view=intent_map.get("product_view"),
            state_object=intent_map.get("state_object"),
        )
        for row in proposal["backlog"]:
            if isinstance(row, dict):
                changed |= _clear_bad_projection_fields(row, visible=visible, proof=proof)
    changed |= _repair_bad_project_brief_projection(proposal)
    return changed


def repair_confirmed_intent_semantic_projections(intent: dict[str, Any]) -> bool:
    first_path = clean_text(intent.get("first_path"))
    proof = clean_text(intent.get("proof_boundary"))
    if not first_path:
        return False
    visible = select_visible_result_candidate(
        first_path,
        proof_boundary=proof,
        product_view=intent.get("product_view"),
        state_object=intent.get("state_object"),
    )
    return _clear_bad_projection_fields(intent, visible=visible, proof=proof)


def projection_uses_proof_boundary_as_result(value: Any, *, visible_result: str, proof_boundary: str) -> bool:
    text = clean_text(value)
    proof = clean_text(proof_boundary)
    visible = clean_text(visible_result)
    if not text or not proof:
        return "visible result produced by" in text.casefold()
    lowered = text.casefold()
    if "visible result produced by" in lowered:
        return True
    if _projection_couples_visible_result_to_proof(text, visible_result=visible, proof_boundary=proof):
        return True
    if _contains_proof_control_claim(text) and _term_overlap_ratio(proof, text) >= 0.42:
        return not visible or _term_overlap_ratio(visible, text) < _term_overlap_ratio(proof, text)
    return False


def _candidate(
    *,
    text: str,
    source_kind: str,
    source_path: str,
    confidence: float,
    provenance: tuple[str, ...],
    limit: int,
) -> GreenfieldSemanticCandidate:
    return GreenfieldSemanticCandidate(
        role="visible_result",
        text=clip_first_path_phrase(text, limit=limit) or clean_first_path_text(text),
        source_kind=source_kind,
        source_path=source_path,
        confidence=round(max(0.0, min(1.0, confidence)), 3),
        provenance=tuple(clean_first_path_text(value) for value in provenance if clean_first_path_text(value)),
    )


def _product_result_from_visible_outcome(value: Any) -> str:
    text = clean_first_path_text(value)
    if not text:
        return ""
    if contains_word_sense_metadata_clause(text):
        text = clean_first_path_text(strip_requirement_control_tail(text))
        if not text or is_declarative_visible_result_prefix(text):
            return ""
    state_update = _finite_state_update_visible_result(text)
    if state_update:
        return state_update
    visible_object = visible_result_object(text)
    if _starts_with_connector(visible_object) and _is_visible_object_list_result(text):
        visible_object = text
    binary_result = _binary_actor_action_result_object(text)
    action_result = nominal_action_result_object(text, visible_object)
    if not action_result and (not visible_object or actor_signature(visible_object)):
        action_result = _single_action_state_result_object(text) or nominal_action_result_object(text, "")
    candidate = binary_result or action_result or visible_object or nominal_visible_result_object(text) or text
    if word_count(candidate) < 2:
        candidate = nominal_action_result_object(text, candidate) or candidate
    candidate = _confirmed_result_object(source=text, result=candidate)
    candidate = _binary_actor_action_result_object(candidate) or candidate
    candidate = _resolve_result_anaphora(candidate)
    candidate = nominal_visible_result_object(candidate) or candidate
    candidate = normalize_visible_result_language(candidate) or candidate
    candidate = strip_release_scope_limit_text(candidate) or candidate
    return lowercase_leading_article(candidate).strip(" .")


def _finite_state_update_visible_result(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    match = re.match(
        r"^(?P<subject>(?:(?:a|an|the|this|that|one)\s+)?(?:[A-Za-z][A-Za-z0-9/&'-]*\s+){1,7})"
        r"(?P<verb>changes?|clears?|closes?|completes?|confirms?|displays?|emits?|establishes?|finishes?|"
        r"keeps?|passes?|publishes?|refreshes?|resolves?|settles?|shows?|surfaces?|updates?)\b"
        r"(?P<tail>\s+.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    subject = clean_text(match.group("subject")).casefold()
    if not any(term in subject.split() for term in _NON_HUMAN_WORKFLOW_SUBJECT_TERMS):
        return ""
    return lowercase_leading_article(text).strip(" .")


def _product_result_from_proof_boundary(value: Any) -> str:
    text = clean_first_path_text(value)
    if not text:
        return ""
    if contains_word_sense_metadata_clause(text):
        text = clean_first_path_text(strip_requirement_control_tail(text))
        if not text or is_declarative_visible_result_prefix(text):
            return ""
    candidate = visible_result_object(text) or action_chain_fragment(text) or text
    candidate = _strip_proof_leading_clause(candidate)
    candidate = _binary_actor_action_result_object(candidate) or candidate
    candidate = _resolve_result_anaphora(candidate)
    return lowercase_leading_article(nominal_visible_result_object(candidate) or candidate).strip(" .")


def _product_result_from_intent_context(
    *,
    product_view: Any,
    state_object: Any,
) -> tuple[str, str, tuple[str, ...]]:
    declared_result = _declared_visible_result(product_view)
    if declared_result:
        candidate = _product_result_from_visible_outcome(declared_result)
        if candidate:
            return candidate, "intent.product_view.visible_result", (clean_text(product_view),)
    state_text = clean_text(state_object)
    state_label = compact_domain_object_label(state_text, fallback="") if state_text else ""
    state_reference = object_reference_phrase(state_label) or state_label
    if word_count(state_reference) >= 2:
        candidate = normalize_visible_result_language(state_reference) or state_reference
        return lowercase_leading_article(candidate).strip(" ."), "intent.state_object", (state_text,)
    return "", "", ()

def _declared_visible_result(value: Any) -> str:
    text = clean_first_path_text(value)
    lowered = text.casefold()
    if not text or "visible result" not in lowered:
        return ""
    markers = (
        "visible result is ",
        "visible result are ",
        "visible result: ",
    )
    marker_index = -1
    marker_length = 0
    for marker in markers:
        index = lowered.find(marker)
        if index >= 0 and (marker_index < 0 or index < marker_index):
            marker_index = index
            marker_length = len(marker)
    if marker_index < 0:
        return ""
    tail = text[marker_index + marker_length :].strip(" .")
    return _first_declaration_sentence(tail)


def _first_declaration_sentence(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    boundaries = [index for index in (text.find(". "), text.find("; "), text.find("\n")) if index >= 0]
    if boundaries:
        text = text[: min(boundaries)]
    return text.strip(" .")


def _clause_carries_material_result(step: Any, result: str) -> bool:
    text = clean_first_path_text(step)
    if not text or not result:
        return False
    if _contains_proof_control_claim(text):
        return False
    if nominal_action_result_object(text, ""):
        return True
    return bool(visible_result_object(text) and _term_overlap_ratio(text, result) >= 0.35)


_BINARY_RESULT_PARTICIPLES = {
    "accept": "accepted",
    "accepts": "accepted",
    "approve": "approved",
    "approves": "approved",
    "block": "blocked",
    "blocks": "blocked",
    "decline": "declined",
    "declines": "declined",
    "deny": "denied",
    "denies": "denied",
    "dismiss": "dismissed",
    "dismisses": "dismissed",
    "reject": "rejected",
    "rejects": "rejected",
}


def _binary_actor_action_result_object(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    action_result = _binary_action_result_object_from_clause(action_chain_fragment(text))
    if action_result:
        return action_result
    action_result = _binary_action_result_object_from_clause(text)
    if action_result:
        return action_result
    action = "|".join(re.escape(verb) for verb in sorted(_BINARY_RESULT_PARTICIPLES, key=len, reverse=True))
    match = re.match(
        rf"^(?:(?:a|an|the)\s+)?[A-Za-z][A-Za-z0-9'-]*(?:\s+[A-Za-z][A-Za-z0-9'-]*){{0,4}}\s+"
        rf"(?P<left>{action})\s+or\s+(?P<right>{action})\s+(?P<object>[^.;]+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    left = _BINARY_RESULT_PARTICIPLES.get(match.group("left").casefold(), "")
    right = _BINARY_RESULT_PARTICIPLES.get(match.group("right").casefold(), "")
    result_object = re.sub(r"^(?:a|an|the)\s+", "", match.group("object").strip(" ."), flags=re.IGNORECASE)
    if not left or not right or not result_object:
        return ""
    return f"the {left} or {right} {result_object}".strip(" .")


def _binary_action_result_object_from_clause(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    action = "|".join(re.escape(verb) for verb in sorted(_BINARY_RESULT_PARTICIPLES, key=len, reverse=True))
    match = re.match(rf"^(?P<left>{action})\s+or\s+(?P<right>{action})\s+(?P<object>[^.;]+)$", text, flags=re.IGNORECASE)
    if not match:
        return ""
    left = _BINARY_RESULT_PARTICIPLES.get(match.group("left").casefold(), "")
    right = _BINARY_RESULT_PARTICIPLES.get(match.group("right").casefold(), "")
    result_object = re.sub(r"^(?:a|an|the)\s+", "", match.group("object").strip(" ."), flags=re.IGNORECASE)
    if not left or not right or not result_object:
        return ""
    return f"the {left} or {right} {result_object}".strip(" .")


def _single_action_state_result_object(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    action = action_chain_fragment(text).strip(" .") if text else ""
    if not action:
        return ""
    actor_terminal = re.match(
        r"^(?:(?:a|an|the)\s+)?[A-Za-z][A-Za-z0-9'-]*(?:\s+[A-Za-z][A-Za-z0-9'-]*){0,4}\s+"
        r"(?P<verb>accepts?|approves?|blocks?|declines?|denies?|dismisses?|rejects?)\s+(?P<object>[^.;]+)$",
        action,
        flags=re.IGNORECASE,
    )
    if actor_terminal:
        participle = _BINARY_RESULT_PARTICIPLES.get(actor_terminal.group("verb").casefold(), "")
        result_object = re.sub(
            r"^(?:only|just|a|an|the)\s+",
            "",
            actor_terminal.group("object").strip(" ."),
            flags=re.IGNORECASE,
        )
        if participle and word_count(result_object) >= 2:
            return f"the {participle} {result_object}"
    binary = _binary_action_result_object_from_clause(action)
    if binary:
        return binary
    action = re.sub(r"^(?:can|may|must|should|will|would|could)\s+", "", action, flags=re.IGNORECASE).strip(" .")
    action = re.sub(r"^(?:only|just)\s+", "", action, flags=re.IGNORECASE).strip(" .")
    verb_pattern = "|".join(re.escape(verb) for verb in sorted(_BINARY_RESULT_PARTICIPLES, key=len, reverse=True))
    match = re.match(rf"^(?P<verb>{verb_pattern})\s+(?P<object>[^.;]+)$", action, flags=re.IGNORECASE)
    if not match:
        return ""
    participle = _BINARY_RESULT_PARTICIPLES.get(match.group("verb").casefold(), "")
    result_object = clean_first_path_text(match.group("object")).strip(" .")
    result_object = re.sub(r"^(?:only|just)\s+", "", result_object, flags=re.IGNORECASE).strip(" .")
    result_object = re.split(
        r"\s+\b(?:without|while|unless|except|before|after)\b\s+",
        result_object,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" .")
    if not participle or word_count(result_object) < 2:
        return ""
    result_object = re.sub(r"^(?:a|an|the)\s+", "", result_object, flags=re.IGNORECASE).strip(" .")
    return f"the {participle} {result_object}".strip(" .")


def _resolve_result_anaphora(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    had_demonstrative = bool(re.match(r"^(?:that|this|it|they|them)\b", text, flags=re.IGNORECASE))
    text = re.sub(r"^(?:that|this)\s+same\s+", "same ", text, count=1, flags=re.IGNORECASE)
    text = re.sub(r"^(?:that|this|it|they|them)\s+", "", text, count=1, flags=re.IGNORECASE).strip(" .")
    if had_demonstrative:
        text = _nominalize_result_state_transition(text)
        text = _strip_trailing_completion_time(text)
    return text


_RESULT_STATE_PAST = {
    "advance": "advanced",
    "advances": "advanced",
    "become": "became",
    "becomes": "became",
    "change": "changed",
    "changes": "changed",
    "finish": "finished",
    "finishes": "finished",
    "move": "moved",
    "moves": "moved",
    "remain": "remained",
    "remains": "remained",
    "settle": "settled",
    "settles": "settled",
    "turn": "turned",
    "turns": "turned",
}


def _nominalize_result_state_transition(value: str) -> str:
    words = clean_first_path_text(value).split()
    if len(words) < 3:
        return " ".join(words)
    for index, word in enumerate(words[:7]):
        verb = _RESULT_STATE_PAST.get(word.casefold().strip(".,:;"))
        if verb:
            return " ".join([*words[:index], verb, *words[index + 1 :]]).strip(" .")
    return " ".join(words)


def _strip_trailing_completion_time(value: str) -> str:
    words = clean_first_path_text(value).split()
    if len(words) >= 3 and [word.casefold().strip(".,:;") for word in words[-2:]] == ["after", "completion"]:
        return " ".join(words[:-2]).strip(" .")
    return " ".join(words)


def _strip_proof_leading_clause(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    text = re.sub(
        r"^(?:release|version)\s+[A-Za-z0-9_.-]+\s+(?:succeeds|works|is\s+proven|is\s+trusted)\s+(?:only\s+)?when\s+",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^(?:the\s+)?(?:release|first\s+release)\s+(?:succeeds|works|is\s+proven|is\s+trusted)\s+(?:only\s+)?when\s+",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    return text.strip(" .")


def _candidate_confidence(value: str, *, source_kind: str) -> float:
    if not value:
        return 0.0
    score = 0.72 if source_kind == "first_path_event" else 0.38
    if _candidate_is_product_result(value):
        score += 0.18
    if _contains_proof_control_claim(value):
        score -= 0.35
    if "confirmed" in clean_text(value).casefold().split():
        score += 0.08
    if re.search(r"\bavailable\s+for\s+[^.]{0,60}\breview\b", clean_text(value), flags=re.IGNORECASE):
        score -= 0.18
    if _is_supporting_evidence_artifact(value):
        score -= 0.12
    if _is_capability_action_candidate(value):
        score -= 0.12
    if word_count(value) >= 4:
        score += 0.05
    return score


def _candidate_source_priority(candidate: GreenfieldSemanticCandidate) -> int:
    if candidate.source_path == "first_path.visible_result":
        if _is_placeholder_visible_result(candidate.text):
            return 0
        if _is_supporting_evidence_artifact(candidate.text):
            return 1
        if _is_supporting_evidence_list(candidate.text):
            return 1
        return 3
    if candidate.source_kind.startswith("first_path"):
        return 2
    if candidate.source_kind == "intent_context":
        return 1
    if candidate.source_kind == "proof_boundary":
        return 0
    return 0


def _candidate_semantic_priority(candidate: GreenfieldSemanticCandidate) -> int:
    if _is_storage_evidence_result(candidate.text):
        return 0
    if _is_finalized_action_state_result(candidate.text):
        return 3
    if _is_action_state_result(candidate.text):
        return 2
    return 0 if _is_supporting_evidence_artifact(candidate.text) else 1


def _is_storage_evidence_result(value: str) -> bool:
    return bool(
        re.match(
            r"^(?:captured|preserved|recorded|saved|stored)\b.+\b(?:audit|evidence|proof|replay)\b",
            clean_text(value),
            flags=re.IGNORECASE,
        )
    )


def _candidate_event_ordinal(candidate: GreenfieldSemanticCandidate) -> int:
    match = re.search(r"\.events\.(?P<index>\d+)$", candidate.source_path)
    return int(match.group("index")) if match else 0


def _step_visible_result_confidence(result: str, *, step: str, path_model: FirstPathModel) -> float:
    score = _candidate_confidence(result, source_kind="first_path_event") - 0.05
    if (
        clean_first_path_text(path_model.visible_outcome)
        and clean_first_path_text(step).casefold() != clean_first_path_text(path_model.visible_outcome).casefold()
        and actor_signature(step)
        and not _step_result_preserves_model_visible_outcome(result, path_model=path_model)
    ):
        score -= 0.3
    return score


def _step_result_preserves_model_visible_outcome(result: str, *, path_model: FirstPathModel) -> bool:
    visible = clean_first_path_text(path_model.visible_outcome)
    candidate = clean_first_path_text(result)
    if not visible or not candidate:
        return False
    return _term_overlap_ratio(visible, candidate) >= 0.8


def _terminal_visible_outcome_bonus(value: str) -> float:
    text = clean_text(value).casefold()
    if not text or text in {"next action", "next step", "what happens next", "what happened next"}:
        return 0.0
    if re.search(r"\bavailable\s+for\s+[^.]{0,60}\breview\b", text):
        return 0.0
    if _is_supporting_evidence_artifact(text):
        return 0.0
    return 0.12


def _is_supporting_evidence_artifact(value: str) -> bool:
    text = clean_text(value).casefold()
    if not text:
        return False
    if _is_visible_object_list_result(text):
        return False
    if any(term in text for term in ("summary", "report", "decision", "recommendation", "route", "result", "status", "view")):
        return False
    return bool(
        re.search(
            r"\b(?:audit\s+trail|comparison\s+evidence|evidence\s+packet|evidence\s+record|proof\s+record|replay\s+output)\b",
            text,
        )
        or re.search(r"\b(?:audit|evidence|proof|replay)\b", text)
    )


def _is_capability_action_candidate(value: str) -> bool:
    text = clean_text(value).casefold()
    return bool(
        re.search(
            r"\b(?:allows?|enables?|lets?)\b.{0,80}\b(?:choose|enter|open|select|submit|update)\b",
            text,
        )
    )


def _confirmed_result_object(*, source: str, result: str) -> str:
    if not re.search(r"\bconfirms?\b", clean_first_path_text(source), flags=re.IGNORECASE):
        return result
    text = clean_first_path_text(result).strip(" .")
    if not text:
        return ""
    text = re.sub(r"^(?:a|an|the)\s+", "", text, flags=re.IGNORECASE).strip(" .")
    return f"a confirmed {text}" if text else result


def _candidate_is_product_result(value: str) -> bool:
    text = clean_text(value)
    if word_count(text) < 2:
        return False
    finite_state_update = bool(_finite_state_update_visible_result(text))
    object_list_result = _is_visible_object_list_result(text)
    if (
        actor_signature(text)
        and not finite_state_update
        and not visible_result_object(text)
        and not _is_predicate_result_state(text)
        and not _is_action_state_result(text)
        and not object_list_result
    ):
        return False
    if _is_internal_action_candidate(text) and not visible_result_object(text) and not _is_predicate_result_state(text):
        return False
    if _is_actor_led_material_action_candidate(text):
        return False
    if _starts_with_connector(text):
        return False
    if _starts_with_result_modifier(text):
        return False
    if _contains_proof_control_claim(text):
        return False
    lowered = text.casefold()
    if lowered in {"next action", "next step", "what happens next", "what happened next"}:
        return False
    return True


def _is_actor_led_material_action_candidate(value: str) -> bool:
    text = clean_text(value).strip(" .")
    if not text:
        return False
    if _is_release_readiness_result(text):
        return False
    if visible_result_object(text) or _is_predicate_result_state(text) or _is_action_state_result(text):
        return False
    match = re.search(
        rf"(?<![A-Za-z0-9_-])(?:{_FINITE_ACTION_PATTERN})(?![A-Za-z0-9_-])",
        text,
        flags=re.IGNORECASE,
    )
    if not match or match.start() <= 0:
        return False
    subject = text[: match.start()].strip(" ,")
    if not 1 <= word_count(subject) <= 5:
        return False
    if re.search(r"\b(?:result|status|summary|view|report|record|recommendation|decision|proof|evidence)\b", subject, flags=re.IGNORECASE):
        return False
    return True


def _is_release_readiness_result(value: str) -> bool:
    return bool(re.match(r"^release\s+readiness\s+(?:for|in|of|with)\b", clean_text(value), flags=re.IGNORECASE))


_VISIBLE_OBJECT_RESULT_TERMS = frozenset(
    {
        "approval",
        "approvals",
        "blocker",
        "blockers",
        "boundary",
        "boundaries",
        "case",
        "cases",
        "claim",
        "claims",
        "confidence",
        "decision",
        "decisions",
        "evidence",
        "exception",
        "exceptions",
        "fault",
        "handoff",
        "handoffs",
        "hypotheses",
        "hypothesis",
        "limit",
        "limits",
        "plan",
        "readiness",
        "record",
        "records",
        "report",
        "reports",
        "result",
        "results",
        "review",
        "risk",
        "signoff",
        "state",
        "status",
        "summary",
        "timeline",
        "trend",
        "version",
        "view",
    }
)


def _is_visible_object_list_result(value: str) -> bool:
    text = clean_text(value).strip(" .")
    if not text or _contains_proof_control_claim(text):
        return False
    lowered = text.casefold()
    if not ("," in text or " and " in lowered or " or " in lowered):
        return False
    if _is_internal_action_candidate(text):
        return False
    subject = actor_signature(text)
    if subject and _has_human_subject_signal(subject) and not _is_reviewable_result_state(text):
        return False
    tokens = [token.casefold() for token in re.findall(r"[A-Za-z][A-Za-z0-9'-]*", text)]
    if len(tokens) < 3:
        return False
    return bool(set(tokens) & _VISIBLE_OBJECT_RESULT_TERMS)


def _is_reviewable_result_state(value: str) -> bool:
    return bool(
        re.search(
            r"\b(?:is|are|be|being|been|must\s+be|should\s+be|will\s+be)\s+reviewable\b",
            clean_text(value),
            flags=re.IGNORECASE,
        )
    )


def _has_human_subject_signal(value: str) -> bool:
    return has_actor_role_word(value) or any(word_has_actor_role_signal(word) for word in clean_text(value).split())


def _is_predicate_result_state(value: str) -> bool:
    text = clean_text(value).strip(" .")
    if not text:
        return False
    lowered = text.casefold()
    if not re.match(r"^(?:a|an|the|this|that|one)\s+", lowered):
        return False
    return bool(
        re.search(
            r"\b(?:became|blocked|changed|cleared|completed|decreased|established|failed|finished|improved|increased|passed|ready|reduced|remained|resolved|reviewable|safe|settled|trusted|visible)\b",
            lowered,
        )
    )


def _is_action_state_result(value: str) -> bool:
    return bool(
        re.match(
            r"^(?:(?:a|an|the)\s+)?"
            r"(?:accepted|approved|blocked|captured|closed|compared|confirmed|coordinated|correlated|emitted|exported|preserved|proven|published|recorded|reported|saved|selected|stored)\b",
            clean_text(value),
            flags=re.IGNORECASE,
        )
    )


def _is_finalized_action_state_result(value: str) -> bool:
    return bool(
        re.match(
            r"^(?:(?:a|an|the)\s+)?(?:accepted|approved|confirmed|published)\b",
            clean_text(value),
            flags=re.IGNORECASE,
        )
    )


def _is_placeholder_visible_result(value: str) -> bool:
    return clean_text(value).casefold().strip(" .") in {
        "next action",
        "next step",
        "what happens next",
        "what happened next",
    }


def _is_supporting_evidence_list(value: str) -> bool:
    lowered = clean_text(value).casefold()
    terms = _terms(value)
    if "evidence" not in lowered and "proof" not in lowered:
        return False
    result_terms = {
        "approval",
        "approvals",
        "blocker",
        "blockers",
        "claim",
        "claims",
        "decision",
        "decisions",
        "handoff",
        "hypotheses",
        "hypothesis",
        "outcome",
        "readiness",
        "readout",
        "recommendation",
        "report",
        "reports",
        "result",
        "risk",
        "signoff",
        "state",
        "status",
        "summary",
        "view",
    }
    primary_result_terms = {"decision", "outcome", "readout", "recommendation", "report", "result", "status", "summary", "view"}
    primary_pattern = "|".join(sorted(primary_result_terms))
    if terms & primary_result_terms or re.search(rf"\b(?:{primary_pattern})s?\b", lowered):
        return False
    if _is_visible_object_list_result(value):
        return len(terms & result_terms) < 2
    return not bool(terms & result_terms)


def _is_internal_action_candidate(value: str) -> bool:
    return bool(
        re.match(
            r"^(?:the\s+)?(?:app|application|dashboard|engine|model|pipeline|platform|product|service|system|tool|view|workspace)\s+\w+",
            clean_text(value),
            flags=re.IGNORECASE,
        )
    )


def _starts_with_connector(value: str) -> bool:
    words = clean_text(value).split()
    return bool(words and words[0].casefold().strip(".,:;") in {"and", "or", "then"})


def _starts_with_result_modifier(value: str) -> bool:
    return bool(
        re.match(
            r"^(?:alongside|as|at|by|during|for|from|including|inside|into|on|through|to|toward|towards|using|via|while|with|without)\b",
            clean_text(value),
            flags=re.IGNORECASE,
        )
    )


def _refined_pronoun_result_candidate(
    best: GreenfieldSemanticCandidate,
    proof_candidate: GreenfieldSemanticCandidate,
) -> GreenfieldSemanticCandidate:
    return GreenfieldSemanticCandidate(
        role=best.role,
        text=proof_candidate.text,
        source_kind="first_path_event_refined_by_proof_boundary",
        source_path=f"{best.source_path}+proof_boundary",
        confidence=round(max(proof_candidate.confidence, best.confidence - 0.02), 3),
        provenance=tuple(dict.fromkeys((*best.provenance, *proof_candidate.provenance))),
    )


def _proof_candidate_refines_pronoun_result(
    best: GreenfieldSemanticCandidate,
    proof_candidate: GreenfieldSemanticCandidate,
    *,
    path_model: FirstPathModel,
) -> bool:
    if best.source_kind != "first_path_event" or proof_candidate.source_kind != "proof_boundary":
        return False
    if not _visible_outcome_uses_pronoun(path_model.visible_outcome):
        return False
    best_terms = _terms(best.text)
    proof_terms = _terms(proof_candidate.text)
    if len(best_terms) > 3 and word_count(best.text) > 6:
        return False
    if len(proof_terms) < len(best_terms) + 2:
        return False
    if best_terms and len(best_terms & proof_terms) / max(1, len(best_terms)) < 0.5:
        return False
    return _candidate_is_product_result(proof_candidate.text)


def _visible_outcome_uses_pronoun(value: Any) -> bool:
    text = clean_text(value).casefold()
    if not text:
        return False
    return bool(re.search(r"\b(?:it|its|them|they|that|this|those|these|both points)\b", text))


def _contains_proof_control_claim(value: Any) -> bool:
    text = clean_text(value)
    if not text:
        return False
    lowered = text.casefold()
    if re.search(r"\b(?:release|version)\s+[a-z0-9_.-]+\s+(?:succeeds|works|is\s+proven|is\s+trusted)\s+when\b", lowered):
        return True
    if re.search(r"\b(?:is\s+proven|proven\s+when|succeeds\s+when|trusted\s+when|proof\s+boundary)\b", lowered):
        return True
    if lowered.startswith(("release proof", "version proof")):
        return True
    return bool(re.match(r"^release\s+readiness\s+(?:depends|fails|passes|requires?|when|is\s+blocked)\b", lowered))


def _first_path_subject_counterexamples(
    first_path: Any,
    *,
    human_actors: Sequence[Any] = (),
) -> list[GreenfieldSemanticCounterexample]:
    text = clean_first_path_text(first_path)
    if not text or _first_path_has_human_actor(text, human_actors=human_actors):
        return []
    model = first_path_model(text)
    for index, step in enumerate(model.steps, start=1):
        if _step_starts_with_non_human_workflow_subject(step):
            return [
                _counterexample(
                    code="first_path.non_human_workflow_subject",
                    path=f"intent.first_path.events.{index}",
                    message="starts the accepted workflow with a state, result, or record object instead of a human actor",
                    repair_hint="recover a human actor path or fall back to a representative user first path before rendering artifacts",
                )
            ]
    return []


def _intent_fact_counterexamples(*, first_path: str, proof_boundary: str) -> list[GreenfieldSemanticCounterexample]:
    issues: list[GreenfieldSemanticCounterexample] = []
    if not clean_first_path_text(first_path):
        issues.append(
            _counterexample(
                code="intent.first_path_missing",
                path="intent.first_path",
                message="missing confirmed first-path fact; generated project-brief prose is not product authority",
                repair_hint="recover first_path from confirmed product intent before semantic compilation",
            )
        )
    if not clean_first_path_text(proof_boundary):
        issues.append(
            _counterexample(
                code="intent.proof_boundary_missing",
                path="intent.proof_boundary",
                message="missing confirmed proof-boundary fact; generated project-brief prose is not product authority",
                repair_hint="recover proof_boundary from confirmed product intent before semantic compilation",
            )
        )
    return issues


def _first_path_has_human_actor(value: str, *, human_actors: Sequence[Any] = ()) -> bool:
    if _actor_is_confirmed_human(actor_signature(value), human_actors=human_actors):
        return True
    model = first_path_model(value)
    return any(
        _actor_is_confirmed_human(actor_signature(step), human_actors=human_actors)
        for step in model.steps
    )


def _actor_is_confirmed_human(value: str, *, human_actors: Sequence[Any]) -> bool:
    if _actor_text_has_human_signal(value):
        return True
    actor_terms = _terms(value)
    return bool(
        actor_terms
        and any(
            actor_terms == _terms(clean_text(row).partition(":")[0])
            for row in human_actors
        )
    )


def _step_starts_with_non_human_workflow_subject(value: Any) -> bool:
    text = clean_first_path_text(value)
    if not text or _is_visible_object_list_result(text):
        return False
    actor = actor_signature(text)
    if not actor or _actor_text_has_human_signal(actor):
        return False
    terms = _terms(actor)
    if not terms & _NON_HUMAN_WORKFLOW_SUBJECT_TERMS:
        return False
    action = action_chain_fragment(text)
    return bool(action and not _is_visible_object_list_result(action))


def _actor_text_has_human_signal(value: str) -> bool:
    text = clean_text(value)
    if not text:
        return False
    return bool(has_actor_role_word(text) or any(word_has_actor_role_signal(word) for word in text.split()))


def _visible_result_counterexamples(
    semantic: Mapping[str, Any],
    visible: GreenfieldSemanticCandidate,
    *,
    proof: str,
) -> list[GreenfieldSemanticCounterexample]:
    issues: list[GreenfieldSemanticCounterexample] = []
    first_path = semantic.get("first_path_contract") if isinstance(semantic.get("first_path_contract"), Mapping) else {}
    model_visible = clean_text(first_path.get("visible_result") if isinstance(first_path, Mapping) else "")
    if model_visible and projection_uses_proof_boundary_as_result(model_visible, visible_result=visible.text, proof_boundary=proof):
        issues.append(
            _counterexample(
                code="visible_result.proof_boundary_source",
                path="semantic_model.first_path_contract.visible_result",
                message="uses proof-boundary language as the product visible result",
                repair_hint="select the visible result from a FirstPathEvent, then let proof obligations reference it",
            )
        )
    if visible.source_kind == "proof_boundary":
        issues.append(
            _counterexample(
                code="visible_result.missing_event_source",
                path="semantic_model.first_path_contract.visible_result",
                message="fell back to the proof boundary because no product-result event was selected",
                repair_hint="compile a visible-result event from the accepted first path before rendering artifacts",
            )
        )
    return issues


def _projection_counterexamples(
    proposal: Mapping[str, Any],
    visible: GreenfieldSemanticCandidate,
    *,
    proof: str,
) -> list[GreenfieldSemanticCounterexample]:
    issues: list[GreenfieldSemanticCounterexample] = []
    for path, value in _projection_values(proposal):
        if _projection_uses_proof_boundary_as_product_result(
            path,
            value,
            visible_result=visible.text,
            proof_boundary=proof,
        ):
            issues.append(
                _counterexample(
                    code="projection.proof_boundary_source",
                    path=path,
                    message="uses proof-boundary language as a product-result projection",
                    repair_hint="rebuild the field from the compiled visible result and keep release proof in proof-only fields",
                )
            )
    return issues


def _projection_uses_proof_boundary_as_product_result(
    path: str,
    value: Any,
    *,
    visible_result: str,
    proof_boundary: str,
) -> bool:
    if _is_primary_product_projection_path(path):
        return projection_uses_proof_boundary_as_result(
            value,
            visible_result=visible_result,
            proof_boundary=proof_boundary,
        )
    text = clean_text(value)
    if not text:
        return False
    lowered = text.casefold()
    if "visible result produced by" in lowered:
        return True
    if "proof boundary" in lowered and re.search(r"\b(?:visible|product|user-visible)\s+result\b", lowered):
        return projection_uses_proof_boundary_as_result(
            value,
            visible_result=visible_result,
            proof_boundary=proof_boundary,
        )
    return False


def _projection_couples_visible_result_to_proof(
    value: str,
    *,
    visible_result: str,
    proof_boundary: str,
) -> bool:
    text = clean_text(value)
    visible = clean_text(visible_result)
    if not text or not visible:
        return False
    visible_terms = _terms(visible)
    text_terms = _terms(text)
    if not visible_terms or len(visible_terms & text_terms) / max(1, len(visible_terms)) < 0.5:
        return False
    lowered = text.casefold()
    proofish = re.search(
        r"\b(?:proven|validated|verified|certified)\s+(?:by|with|from|through)\b"
        r"[^.!?]{0,120}\b(?:release|version|proof|evidence|validation)\b",
        lowered,
    )
    if proofish:
        return True
    if re.search(r"\b(?:release|version)\s+(?:proof|evidence|validation)\b", lowered):
        return bool(re.search(r"\b(?:proven|validated|verified|certified)\b", lowered))
    return False


def _is_primary_product_projection_path(path: str) -> bool:
    return bool(
        re.fullmatch(
            r"(?:intent|backlog\.\d+)\.(?:problem|opportunity|product_view|success_metrics)(?:\.\d+)?",
            str(path or ""),
        )
    )


def _projection_values(proposal: Mapping[str, Any]) -> list[tuple[str, Any]]:
    return semantic_projection_values(proposal, _intent_mapping(proposal))


def _clear_bad_projection_fields(row: dict[str, Any], *, visible: GreenfieldSemanticCandidate, proof: str) -> bool:
    changed = False
    for key in ("problem", "opportunity", "product_view"):
        if projection_uses_proof_boundary_as_result(row.get(key), visible_result=visible.text, proof_boundary=proof):
            row[key] = ""
            changed = True
    metrics = row.get("success_metrics")
    if projection_uses_proof_boundary_as_result(metrics, visible_result=visible.text, proof_boundary=proof) or any(
        projection_uses_proof_boundary_as_result(value, visible_result=visible.text, proof_boundary=proof)
        for value in text_values(metrics)
    ):
        row["success_metrics"] = []
        changed = True
    return changed


def _repair_bad_project_brief_projection(proposal: dict[str, Any]) -> bool:
    from odylith.runtime.domain_intelligence.greenfield_confirmed_project_brief import confirmed_project_brief

    brief = proposal.get("project_brief")
    if not isinstance(brief, dict):
        return False
    intent = _intent_mapping(proposal)
    first_path = _first_nonempty(intent.get("first_path"), brief.get("first_path"))
    proof = _first_nonempty(intent.get("proof_boundary"), brief.get("proof"), brief.get("project_outcome"))
    visible = select_visible_result_candidate(
        first_path,
        proof_boundary=proof,
        product_view=intent.get("product_view"),
        state_object=intent.get("state_object"),
    )
    if not any(
        _projection_uses_proof_boundary_as_product_result(
            path,
            value,
            visible_result=visible.text,
            proof_boundary=proof,
        )
        for path, value in projection_text_values("project_brief", brief)
    ):
        return False
    component_labels = [
        clean_text(row.get("label"))
        for row in mapping_rows(proposal.get("components"))
        if clean_text(row.get("label"))
    ]
    proposal["project_brief"] = confirmed_project_brief(
        label=_first_nonempty(intent.get("title"), proposal.get("title"), "Greenfield Project"),
        prompt=_first_nonempty(proposal.get("command_prompt"), proposal.get("prompt"), intent.get("product_story")),
        release=_first_nonempty(proposal.get("release"), proposal.get("release_selector"), "0.0.1"),
        state_object=_first_nonempty(intent.get("state_object"), proposal.get("state_object"), "Project state record"),
        evidence_record=_first_nonempty(intent.get("evidence_record"), proposal.get("evidence_record"), "Release proof record"),
        product_story=_first_nonempty(intent.get("product_story"), proposal.get("product_story")),
        first_path=first_path,
        proof_boundary=proof,
        problem=_first_nonempty(intent.get("problem"), proposal.get("problem")),
        human_actors=[clean_text(value) for value in text_values(intent.get("human_actors")) if clean_text(value)],
        internal_systems=[clean_text(value) for value in text_values(intent.get("internal_systems")) if clean_text(value)],
        component_labels=component_labels,
        external_systems=[clean_text(value) for value in text_values(intent.get("external_systems")) if clean_text(value)],
        assumptions=[clean_text(value) for value in text_values(intent.get("assumptions")) if clean_text(value)],
        ambiguities=[clean_text(value) for value in text_values(intent.get("ambiguities")) if clean_text(value)],
        non_goals=[clean_text(value) for value in text_values(intent.get("non_goals")) if clean_text(value)],
        operational_constraints=[
            clean_text(value) for value in text_values(intent.get("operational_constraints")) if clean_text(value)
        ],
    )
    return True


def _counterexample(*, code: str, path: str, message: str, repair_hint: str) -> GreenfieldSemanticCounterexample:
    return GreenfieldSemanticCounterexample(
        code=code,
        path=path,
        message=message,
        severity="error",
        repair_hint=repair_hint,
    )


def _unique_counterexamples(
    values: Sequence[GreenfieldSemanticCounterexample],
) -> tuple[GreenfieldSemanticCounterexample, ...]:
    seen: set[tuple[str, str, str]] = set()
    rows: list[GreenfieldSemanticCounterexample] = []
    for item in values:
        key = (item.code, item.path, item.message)
        if key in seen:
            continue
        seen.add(key)
        rows.append(item)
    return tuple(rows)


def _quality_scores(
    visible: GreenfieldSemanticCandidate,
    counterexamples: Sequence[GreenfieldSemanticCounterexample],
) -> dict[str, float]:
    hard_penalty = min(1.0, len(counterexamples) * 0.25)
    return {
        "visible_result_confidence": visible.confidence,
        "semantic_soundness": round(max(0.0, 1.0 - hard_penalty), 3),
        "proof_result_separation": 0.0 if visible.source_kind == "proof_boundary" else 1.0,
    }


def _term_overlap_ratio(left: str, right: str) -> float:
    left_terms = _terms(left)
    if not left_terms:
        return 0.0
    right_terms = _terms(right)
    return len(left_terms & right_terms) / max(1, len(left_terms))


def _terms(value: str) -> set[str]:
    return set(ordered_terms(clean_text(value), minimum=4, stem_ing=True, stopwords=_SEMANTIC_STOPWORDS))


def _intent_mapping(proposal: Mapping[str, Any]) -> Mapping[str, Any]:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return intent


def _project_brief_value(proposal: Mapping[str, Any], key: str) -> str:
    brief = proposal.get("project_brief") if isinstance(proposal.get("project_brief"), Mapping) else {}
    return clean_text(brief.get(key) if isinstance(brief, Mapping) else "")


def _first_nonempty(*values: Any) -> str:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return ""


_SEMANTIC_STOPWORDS = frozenset(
    {
        "accepted",
        "action",
        "boundary",
        "complete",
        "evidence",
        "first",
        "product",
        "proof",
        "release",
        "result",
        "state",
        "that",
        "this",
        "user",
        "version",
        "visible",
    }
)


__all__ = [
    "GreenfieldSemanticCandidate",
    "GreenfieldSemanticCompilerReport",
    "GreenfieldSemanticCounterexample",
    "compile_greenfield_semantics",
    "has_visible_object_list_result",
    "projection_uses_proof_boundary_as_result",
    "repair_confirmed_intent_semantic_projections",
    "repair_greenfield_semantic_projections",
    "select_visible_result_candidate",
    "select_visible_result_text",
    "semantic_compiler_issues",
]
