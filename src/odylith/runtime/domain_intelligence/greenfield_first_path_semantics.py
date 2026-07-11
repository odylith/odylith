"""First-path parsing for confirmed greenfield generation."""

from __future__ import annotations

import re
from typing import Any, Sequence

from odylith.runtime.domain_intelligence.greenfield_status_modifiers import RESULT_STATE_MODIFIER_CONTEXT_TERMS
from odylith.runtime.domain_intelligence.greenfield_status_modifiers import RESULT_STATE_MODIFIER_LEADS
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.common.prose_grammar import repair_modal_base_form_drift
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_common import MATERIAL_ACTION_RE as _MATERIAL_ACTION_RE
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text as _clean
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import drop_requirement_control_steps as _drop_requirement_control_steps
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import is_scope_or_deferred_statement as _is_scope_or_deferred_statement
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import strip_requirement_control_tail as _strip_requirement_control_tail
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import action_chain_fragment as _action_chain_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import actor_led_action_parts as _actor_led_action_parts
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    clean_visible_result_phrase as _clean_visible_result_phrase,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_noun_compounds import action_word_inside_compound_noun as _action_word_inside_compound_noun
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import is_trivial_start as _is_trivial_start
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    looks_like_visible_result as _looks_like_visible_result,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    nominal_visible_result_object as _nominal_visible_result_object,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    strip_action_subject as _strip_action_subject,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    visible_action_clause as _visible_action_clause,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    visible_result_object as _visible_result_object,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_action_split import (
    connector_core_starts_action_clause as _connector_core_starts_action_clause,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_action_split import (
    normalize_role_can_step as _normalize_role_can_step,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_action_split import (
    normalize_subjectless_action_step as _normalize_subjectless_action_step,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_action_split import (
    split_action_pieces as _split_action_pieces,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_review_outcome import (
    review_step_visible_result as _review_step_visible_result,
)
from odylith.runtime.domain_intelligence import greenfield_first_path_purpose_context as _purpose_context
from odylith.runtime.domain_intelligence.greenfield_first_path_step_roles import drop_release_proof_control_steps
from odylith.runtime.domain_intelligence.greenfield_first_path_step_roles import is_supporting_setup_step
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathModel
from odylith.runtime.domain_intelligence.greenfield_first_path_visible_results import (
    prefer_visible_result_object as _prefer_visible_result_object,
)
from odylith.runtime.domain_intelligence.greenfield_text import normalize_visible_result_language as _normalize_visible_result_language
from odylith.runtime.domain_intelligence.greenfield_text import unique_text

_PREFERRED_VISIBLE_RESULT_ACTION_RE = re.compile(
    r"\b(?:compare|compares|deliver|delivers|display|displays|find|finds|produce|produces|publish|publishes|"
    r"recompute|recomputes|report|reports|render|renders|return|returns|review|reviews|save|saves|see|sees|"
    r"show|shows|update|updates|view|views|receive|receives)\b",
    flags=re.IGNORECASE,
)
_OPEN_PLUS_MATERIAL_RE = re.compile(
    r"^\s*(?P<subject>(?:a|an|the)?\s*[^,.;]{0,80}?)\b(?:open|opens|launch|launches)\b"
    r"(?P<object>\s+[^,.;]{1,80}?)\s+\band\b\s+(?P<material>.+)$",
    re.IGNORECASE,
)

_FIRST_PATH_PREFIXES = (
    r"^the first complete path (?:the product )?(?:must|should) prove (?:before broader scope )?is\s+",
    r"^the first complete path starts? (?:when|with)\s+",
    r"^first complete path starts? (?:when|with)\s+",
    r"^the first complete path to prove should be\s*:?\s*",
    r"^first complete path to prove should be\s*:?\s*",
    r"^the first path starts? (?:when|with)\s+",
    r"^first path starts? (?:when|with)\s+",
    r"^the first path is\s+",
    r"^first path\s*:?\s*",
)

def first_path_model(value: Any) -> FirstPathModel:
    raw = _clean(value)
    steps = tuple(_first_path_steps(raw))
    material = _material_action(steps) or (steps[0] if steps else "")
    visible = _visible_outcome(steps)
    recovery = _recovery_action(steps)
    return FirstPathModel(
        raw_path=raw,
        steps=steps,
        material_action=material,
        visible_outcome=visible,
        recovery_action=recovery,
    )

def material_first_path_action(value: Any, *, fallback: str = "") -> str:
    model = first_path_model(value)
    return model.material_action or _clean(fallback)

def first_path_steps(value: Any) -> tuple[str, ...]:
    return first_path_model(value).steps

def _first_path_steps(value: str) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    text = _strip_first_path_frame(text)
    text = _purpose_context.carry_semicolon_context_to_first_action(
        text, split_action_pieces=_split_action_pieces, step_has_action_signal=_step_has_action_signal
    )
    text = re.sub(r"\bthat\s+single\s+loop\s*[–—-]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(?:^|(?<=[.!?])\s+)(?:this|that)\s+(?:single\s+)?(?:path|loop|journey|flow)\s+[–—-]\s*.*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    value_tail = ""
    value_match = re.search(
        r"\bso\s+the\s+(?:first\s+)?(?:end-to-end\s+)?value\s+is\s*:\s*(?P<tail>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if value_match:
        value_tail = value_match.group("tail")
        text = text[: value_match.start()].strip(" ,.;:")
    if not re.search(r"\b\d+[.)]\s*", text):
        text = re.sub(r"\s+(?:flow|journey|path)\s*:\s*.*$", "", text, flags=re.IGNORECASE)
    numbered = [part.strip(" .") for part in re.split(r"(?:^|\s)\d+[.)]\s*", text) if part.strip(" .")]
    if len(numbered) > 1:
        pieces = numbered
        if ":" in pieces[0]:
            pieces[0] = pieces[0].rsplit(":", 1)[-1].strip(" .")
    else:
        pieces = _split_action_pieces(text)
    normalized: list[str] = []
    for piece in pieces:
        cleaned = _clean_step(piece)
        if _valid_step(cleaned):
            normalized.append(cleaned)
    if value_tail:
        for piece in _split_action_pieces(value_tail):
            cleaned = _clean_step(piece)
            if _valid_step(cleaned) and re.search(
                r"\b(?:see|sees|show|shows|view|views|review|reviews|receive|receives)\b",
                cleaned,
                re.IGNORECASE,
            ):
                normalized.append(cleaned)
    if len(normalized) > 1 and _is_trivial_start(normalized[0]):
        normalized = normalized[1:]
    merged = _merge_leading_modifier_steps(normalized)
    without_context = _drop_leading_context_fragments(merged)
    without_requirements = _drop_requirement_control_steps(without_context)
    return _unique(drop_release_proof_control_steps(without_requirements))

def _merge_leading_modifier_steps(steps: Sequence[str]) -> list[str]:
    """Attach comma-split modifier tails back to the result they qualify."""

    merged: list[str] = []
    for step in steps:
        cleaned = _clean(step).strip(" .")
        if not cleaned:
            continue
        if merged and _is_result_modifier_for_previous(cleaned, previous=merged[-1]):
            merged[-1] = _append_result_modifier(merged[-1], cleaned)
            continue
        merged.append(cleaned)
    return merged

def _drop_leading_context_fragments(steps: Sequence[str]) -> list[str]:
    rows = list(steps)
    while len(rows) > 1 and _is_leading_context_fragment(rows[0]) and any(
        _step_has_action_signal(step) for step in rows[1:]
    ):
        rows.pop(0)
    return rows

def _is_leading_context_fragment(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text:
        return False
    if is_contextual_gerund_phrase(text):
        return True
    if _step_has_action_signal(text):
        return False
    return len(label_terms(text)) <= 6


def is_contextual_gerund_phrase(value: str) -> bool:
    """Return true for a descriptive participant phrase, not a product action."""

    text = _clean(value).strip(" .")
    if not text or re.search(r"\b(?:is|are|was|were|can|must|will)\b", text, flags=re.IGNORECASE):
        return False
    return bool(
        re.match(
            r"^(?:[A-Za-z][A-Za-z'-]*\s+){0,4}[A-Za-z][A-Za-z'-]*ing\b"
            r"(?:\s+[A-Za-z][A-Za-z'-]*){0,5}\s+"
            r"(?:to|through|with|from|at|in|near|between)\b",
            text,
            flags=re.IGNORECASE,
        )
    )
def _step_has_action_signal(value: str) -> bool:
    text = _clean(value).strip(" .")
    return bool(text) and (
        bool(_MATERIAL_ACTION_RE.search(text))
        or (not _MATERIAL_ACTION_RE.search(text) and bool(_actor_led_action_parts(text)[1]))
        or _looks_like_visible_result(text)
        or _connector_core_starts_action_clause(text)
        or looks_like_finite_action(text)
    )

def _is_leading_modifier_step(value: str) -> bool:
    return bool(
        re.match(
            r"^(?:alongside|as|at|by|during|for|from|including|inside|into|on|through|to|toward|towards|using|via|while|with|without)\b",
            _clean(value),
            flags=re.IGNORECASE,
        )
    )

def _is_result_modifier_for_previous(value: str, *, previous: str) -> bool:
    text = _clean(value).strip(" .")
    if not text:
        return False
    if _is_leading_modifier_step(text):
        return True
    if not (_looks_like_visible_result(previous) or _looks_like_visible_result(text)):
        return False
    words = [word.strip(".,:;()[]{}").casefold() for word in text.split() if word.strip(".,:;()[]{}")]
    if not words:
        return False
    first = words[0]
    if first == "and" and len(words) > 1:
        first = words[1]
    if first not in RESULT_STATE_MODIFIER_LEADS and not (len(first) > 4 and first.endswith("ed")):
        return False
    terms = {word for word in words if len(word) >= 4}
    return len(words) <= 8 or bool(terms & RESULT_STATE_MODIFIER_CONTEXT_TERMS)

def _append_result_modifier(previous: str, modifier: str) -> str:
    previous_text = _clean(previous).strip(" .")
    modifier_text = _lower_initial(_clean(modifier).strip(" ."))
    if not previous_text:
        return modifier_text
    if _is_leading_modifier_step(modifier_text):
        return f"{previous_text} {modifier_text}".strip()
    return f"{previous_text}, {modifier_text}".strip()

def _lower_initial(value: str) -> str:
    text = _clean(value)
    return text[:1].casefold() + text[1:] if text else ""

def _strip_first_path_frame(value: str) -> str:
    text = _clean(value).strip()
    for pattern in _FIRST_PATH_PREFIXES:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
    if ":" not in text:
        return text
    head, tail = text.split(":", 1)
    if _first_path_frame_head(head) and len(label_terms(tail)) >= 3:
        return tail.strip(" .:")
    return text

def _first_path_frame_head(value: str) -> bool:
    words = {
        word.strip(".,:;()[]{}").casefold()
        for word in _clean(value).replace("-", " ").split()
        if word.strip(".,:;()[]{}")
    }
    if "path" not in words:
        return False
    if not words & {"first", "release", "complete", "accepted"}:
        return False
    return bool(words & {"prove", "proves", "proven", "show", "shows", "demonstrate", "demonstrates", "validate", "validates"})

def _material_action(steps: Sequence[str]) -> str:
    if not steps:
        return ""
    setup_fallback = ""
    for step in steps:
        if _is_trivial_start(step):
            continue
        if is_supporting_setup_step(step):
            setup_fallback = setup_fallback or step
            continue
        match = _OPEN_PLUS_MATERIAL_RE.match(step)
        if match and _MATERIAL_ACTION_RE.search(match.group("material")):
            return _sentence_case(_action_chain_fragment(step))
        if _MATERIAL_ACTION_RE.search(step):
            return _sentence_case(_action_chain_fragment(step))
        actor, action = _actor_led_action_parts(step)
        if actor and action:
            return _sentence_case(f"{actor} {action}")
    if setup_fallback:
        return _sentence_case(_action_chain_fragment(setup_fallback))
    return _sentence_case(_action_chain_fragment(steps[0]))

def _visible_outcome(steps: Sequence[str]) -> str:
    terminal_choice = _terminal_choice_outcome(steps)
    if terminal_choice:
        return _sentence_case(_normalize_visible_result_language(terminal_choice) or terminal_choice)
    preferred: list[str] = []
    fallback: list[str] = []
    for step in reversed(steps):
        if _is_meta_visible_result_summary(step) or _is_scope_or_deferred_statement(step):
            continue
        if _is_routing_handoff_step(step):
            continue
        review_visible = _review_step_visible_result(step)
        if review_visible:
            preferred.append(review_visible)
            continue
        if _looks_like_visible_result(step):
            cleaned = _clean_visible_result_phrase(step) or step
            action_visible = _visible_action_clause(cleaned)
            object_visible = _visible_result_object(cleaned)
            visible_choice = (
                object_visible
                if _prefer_visible_result_object(object_visible, action_visible)
                else action_visible or object_visible or cleaned
            )
            if _has_preferred_visible_result_action(cleaned) and not re.search(
                r"\b(?:accept|accepts|click|clicks|choose|chooses|dismiss|dismisses)\b",
                cleaned,
                flags=re.IGNORECASE,
            ):
                preferred.append(visible_choice)
            else:
                fallback.append(visible_choice)
    if preferred:
        return _sentence_case(_normalize_visible_result_language(preferred[0]) or preferred[0])
    if fallback:
        return _sentence_case(_normalize_visible_result_language(fallback[0]) or fallback[0])
    for step in reversed(steps):
        if not _is_scope_or_deferred_statement(step):
            outcome = _nominal_material_outcome(step) or step
            return _sentence_case(_normalize_visible_result_language(outcome) or outcome)
    return ""

def _has_preferred_visible_result_action(value: str) -> bool:
    text = _clean(value)
    for match in _PREFERRED_VISIBLE_RESULT_ACTION_RE.finditer(text):
        if _action_word_inside_compound_noun(text, match.start()):
            continue
        return True
    return False

def _nominal_material_outcome(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    stripped = _strip_action_subject(text).strip(" .")
    if not stripped or not _MATERIAL_ACTION_RE.search(stripped):
        return ""
    nominal = _nominal_visible_result_object(stripped).strip(" .")
    return nominal if nominal and nominal != stripped else ""

def _terminal_choice_outcome(steps: Sequence[str]) -> str:
    for step in reversed(steps):
        text = _clean(step).strip(" .")
        if not text or _is_scope_or_deferred_statement(text) or _is_routing_handoff_step(text):
            continue
        match = re.match(
            r"^(?:(?:a|an|the|one|this|that|each|another)\s+)?"
            r"(?:[A-Za-z][A-Za-z0-9'/-]*\s+){0,5}?"
            r"(?:choose|chooses|select|selects)\s+(?P<object>.+)$",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            return ""
        result_object = re.sub(r"^(?:a|an|the)\s+", "", _clean(match.group("object")).strip(" ."), flags=re.IGNORECASE)
        return f"selected {result_object}" if result_object else ""
    return ""

def _is_routing_handoff_step(value: str) -> bool:
    words = {
        word.strip(".,:;").casefold()
        for word in _clean(value).replace("-", " ").split()
        if word.strip(".,:;")
    }
    return bool(words & {"route", "routed", "routes", "send", "sends"} and "to" in words)

def _is_meta_visible_result_summary(value: str) -> bool:
    """Return whether a step only names the parser's visible-result marker."""

    text = _clean(value)
    if not text:
        return False
    lowered = text.casefold()
    if _is_meta_loop_summary(text):
        return True
    if "visible-result event" in lowered:
        return True
    return bool(re.match(r"^(?:this|the)\s+.+\bis\s+the\s+visible\s+result\b", text, flags=re.IGNORECASE))

def _is_meta_loop_summary(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text:
        return False
    lowered = text.casefold()
    if re.match(r"^(?:this|that)\s+(?:single\s+)?(?:path|loop|journey|flow)\b", lowered):
        return True
    return bool(
        re.search(
            r"\b(?:smallest\s+version\s+of\s+the\s+whole\s+product|whole\s+product\s+working\s+end\s+to\s+end)\b",
            lowered,
        )
        and re.search(r"\b(?:path|loop|journey|flow)\b", lowered)
    )

def _recovery_action(steps: Sequence[str]) -> str:
    for step in reversed(steps):
        if re.search(r"\b(?:edit|edits|correct|corrects|recover|recovers|retry|retries|delete|deletes|revise|revises)\b", step, re.IGNORECASE):
            return _sentence_case(step)
    return ""

def _clean_step(value: str) -> str:
    text = _strip_requirement_control_tail(_clean(value)).strip(" .,;:")
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"^(?:(?:release\s+\S+|the\s+first\s+release|first\s+release)\s+)?"
        r"(?:succeeds?|is\s+trusted|is\s+proven|works)\s+when\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^\d+[.)]\s*", "", text)
    text = re.sub(r"\bthat single loop\b\s*[–—-]?\s*", "", text, flags=re.IGNORECASE)
    if _is_meta_visible_result_summary(text):
        return ""
    text = _clean_visible_result_phrase(text) or text
    text = re.sub(
        r",?\s+and\s+(?:completes?|ends?|finishes?)\s+(?:the\s+)?(?:flow|journey|loop|moment|path|session)\b.*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .,;:")
    text = _normalize_role_can_step(text)
    text = _normalize_subjectless_action_step(text)
    text = repair_modal_base_form_drift(text)
    text = _strip_dangling_step_tail(text)
    return _sentence_case(text.strip(" .,;:"))

def _strip_dangling_step_tail(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    words = text.split()
    dangling = {"against", "alongside", "as", "at", "by", "for", "from", "in", "into", "of", "on", "to", "with", "without"}
    while len(words) > 3 and words[-1].casefold().strip(".,;:") in dangling:
        words.pop()
    return " ".join(words).strip(" .")


def _valid_step(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text:
        return False
    if re.match(r"^(?:this|that)\s+is\s+one\s+full\s+loop\b", text, flags=re.IGNORECASE):
        return False
    if re.match(r"^one\s+full\s+loop\s+from\b", text, flags=re.IGNORECASE):
        return False
    if _is_meta_loop_summary(text):
        return False
    if _is_scope_or_deferred_statement(text):
        return False
    token_count = len(label_terms(text))
    if token_count < 2:
        return False
    if token_count <= 3 and not _MATERIAL_ACTION_RE.search(text):
        return False
    if re.fullmatch(r"(?:capture|view|edit|create|done|path|mean|person)(?:\s*,\s*(?:capture|view|edit|create|done|path|mean|person))*", text, re.IGNORECASE):
        return False
    return True

def _sentence_case(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    return text[:1].upper() + text[1:]

def _unique(values: Sequence[str]) -> list[str]:
    return list(unique_text(_clean(value) for value in values))

__all__ = [
    "FirstPathModel",
    "first_path_model",
    "first_path_steps",
    "is_contextual_gerund_phrase",
    "material_first_path_action",
]
