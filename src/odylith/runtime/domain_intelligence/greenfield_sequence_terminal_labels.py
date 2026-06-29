"""Terminal result-label decisions for greenfield first-path diagrams."""

from __future__ import annotations

from typing import AbstractSet

from odylith.runtime.domain_intelligence.greenfield_sequence_labeling import compact_text

_RESULT_WRAPPER_ACTION_TERMS = frozenset(
    {
        "display",
        "displays",
        "emit",
        "emits",
        "present",
        "presents",
        "produce",
        "produces",
        "publish",
        "publishes",
        "report",
        "reports",
        "return",
        "returns",
        "show",
        "shows",
    }
)


def terminal_step_prefers_visible_result(
    step_label: str,
    visible_result: str,
    *,
    step_terms: AbstractSet[str],
    visible_terms: AbstractSet[str],
) -> bool:
    """Return true when a long terminal step only wraps the visible result."""

    text = compact_text(step_label).strip(" .")
    outcome = compact_text(visible_result).strip(" .")
    if not text or not outcome:
        return False
    if not step_terms or not visible_terms or len(step_terms & visible_terms) < 2:
        return False
    if visible_terms <= step_terms and len(text) > len(outcome) and len(text) > 96:
        return True
    return bool(_label_words(text) & _RESULT_WRAPPER_ACTION_TERMS) and len(text) > 96


def terminal_step_loses_distinctive_tail(
    *,
    step_terms: AbstractSet[str],
    label_terms: AbstractSet[str],
) -> bool:
    if len(step_terms) < 2:
        return False
    return len(step_terms & label_terms) < min(2, len(step_terms))


def _label_words(value: object) -> set[str]:
    return {
        word.strip(".,:;()[]{}").casefold()
        for word in compact_text(str(value)).split()
        if word.strip(".,:;()[]{}")
    }


__all__ = ["terminal_step_loses_distinctive_tail", "terminal_step_prefers_visible_result"]
