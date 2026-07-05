"""Action-split predicates for comma-delimited first-path clauses."""

from __future__ import annotations

from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms


def starts_subject_finite_action_clause(
    value: str,
    *,
    material_action_match,
) -> bool:
    """Return whether a comma piece starts a fresh subject-led finite action."""

    text = str(value or "").strip(" .")
    words = [word.strip(".,:;()[]{}") for word in text.split() if word.strip(".,:;()[]{}")]
    if len(words) < 3:
        return False
    subject = words[0].casefold()
    if subject in {"a", "an", "and", "or", "the", "then"}:
        return False
    action_tail = " ".join(words[1:])
    if not looks_like_finite_action(action_tail):
        return False
    if not material_action_match(action_tail):
        return False
    return bool(label_terms(subject))


__all__ = ["starts_subject_finite_action_clause"]
