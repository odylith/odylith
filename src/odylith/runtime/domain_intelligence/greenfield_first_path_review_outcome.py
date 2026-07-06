"""Visible-result selection for review-like first-path terminal steps."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import strip_action_subject
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import visible_result_object


def review_step_visible_result(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    stripped = strip_action_subject(text).strip(" .")
    if not re.match(r"^(?:compare|compares|inspect|inspects|read|reads|review|reviews|view|views)\b", stripped, re.IGNORECASE):
        return ""
    if re.search(r"\b(?:blocker|blockers|next\s+step)\b", stripped, flags=re.IGNORECASE):
        return ""
    if not re.search(
        r"\b(?:decision|evidence|output|prediction|proof|readout|recommendation|report|result|results|standing|standings|status|summary|view)\b",
        stripped,
        flags=re.IGNORECASE,
    ):
        return ""
    return visible_result_object(stripped).strip(" .")


__all__ = ["review_step_visible_result"]
