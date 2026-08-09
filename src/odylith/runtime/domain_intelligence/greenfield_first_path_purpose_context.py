"""Purpose-context custody for confirmed first-path text."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text as _clean


def carry_semicolon_context_to_first_action(
    value: str,
    *,
    split_action_pieces: Callable[[str], Sequence[str]],
    step_has_action_signal: Callable[[str], bool],
    head_has_subject_action: Callable[[str], bool],
) -> str:
    text = _clean(value).strip(" .")
    if ";" not in text:
        return text
    head, tail = (part.strip(" ,.;:") for part in text.split(";", 1))
    if not head or not tail:
        return text
    head_terms = set(label_terms(head))
    if not head_terms or len(head_terms) > 6:
        return text
    if head_has_subject_action(head):
        return text
    tail_pieces = tuple(split_action_pieces(tail))
    if not tail_pieces or not step_has_action_signal(tail_pieces[0]):
        return text
    if head_terms <= set(label_terms(tail_pieces[0])):
        return text
    return "; ".join((f"{tail_pieces[0]} for {head}", *tail_pieces[1:]))


__all__ = ["carry_semicolon_context_to_first_action"]
