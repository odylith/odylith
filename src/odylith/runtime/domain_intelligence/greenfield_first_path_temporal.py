"""Temporal first-path split predicates."""

from __future__ import annotations

from collections.abc import Callable
from collections.abc import Sequence
import re

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_common import MATERIAL_ACTION_RE
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import leading_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import visible_result_object


_STATE_TRANSITION_RE = re.compile(
    r"^(?:(?:a|an|the)\s+)?(?P<subject>[A-Za-z0-9][A-Za-z0-9'/-]*"
    r"(?:\s+[A-Za-z0-9][A-Za-z0-9'/-]*){0,4}?)\s+"
    r"(?:changes?|moves?|transitions?)\s+(?:from\s+\S+(?:\s+\S+){0,2}\s+)?to\s+\S+",
    flags=re.IGNORECASE,
)
_STATE_FIELD_RE = re.compile(
    r"^\s*(?:[-*]\s*)?state\s*:\s*(?P<transition>[^.!?\n]{3,160})",
    flags=re.IGNORECASE | re.MULTILINE,
)


def temporal_head_can_split(value: str, *, actor_led_subject_prefix: bool = False) -> bool:
    text = clean_first_path_text(value).strip(" .")
    if not text:
        return False
    return bool(
        MATERIAL_ACTION_RE.search(text)
        or actor_led_subject_prefix
        or leading_subject_prefix(text)
        or len(label_terms(text)) >= 4
    )


def base_from_gerund_action(value: str, *, material_action_match: Callable[[str], object] = MATERIAL_ACTION_RE.fullmatch) -> str:
    token = str(value or "").casefold().strip(".,;:")
    if not token.endswith("ing") or len(token) <= 5:
        return ""
    stem = token[:-3]
    candidates = [stem, f"{stem}e"]
    if len(stem) >= 3 and stem[-1:] == stem[-2:-1]:
        candidates.append(stem[:-1])
    for candidate in candidates:
        if material_action_match(candidate):
            return base_action_clause(candidate)
    return ""


def retain_ordered_path_row(accepted_rows: Sequence[str], candidate: str) -> bool:
    """Exclude an entailed state transition after an actor path already exposes its result."""

    if not accepted_rows or not any(visible_result_object(row) for row in accepted_rows):
        return True
    transition = _STATE_TRANSITION_RE.match(clean_first_path_text(candidate).strip(" ."))
    if not transition:
        return True
    subject_terms = set(label_terms(transition.group("subject")))
    accepted_terms = set(label_terms(". ".join(accepted_rows)))
    return not bool(subject_terms and subject_terms <= accepted_terms)


def source_state_transition(value: str) -> str:
    """Return one explicit state transition without turning it into a user-path event."""

    field = _STATE_FIELD_RE.search(str(value or ""))
    if field:
        return field.group("transition").strip(" .")
    for sentence in re.split(r"(?<=[.!?])\s+", clean_first_path_text(value)):
        candidate = sentence.strip(" .")
        if _STATE_TRANSITION_RE.match(candidate):
            return candidate
    return ""


def source_state_transition_subject(value: str) -> str:
    """Return the explicit state object's subject when the declaration names it."""

    transition = source_state_transition(value)
    match = _STATE_TRANSITION_RE.match(transition)
    if not match:
        return ""
    return re.sub(r"^(?:a|an|the)\s+", "", match.group("subject"), flags=re.IGNORECASE)


__all__ = [
    "base_from_gerund_action",
    "retain_ordered_path_row",
    "source_state_transition",
    "source_state_transition_subject",
    "temporal_head_can_split",
]
