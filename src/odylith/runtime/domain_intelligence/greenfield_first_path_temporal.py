"""Temporal first-path split predicates."""

from __future__ import annotations

from collections.abc import Callable

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_common import MATERIAL_ACTION_RE
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import leading_subject_prefix


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


__all__ = ["base_from_gerund_action", "temporal_head_can_split"]
