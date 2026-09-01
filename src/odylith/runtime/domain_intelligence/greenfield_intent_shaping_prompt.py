"""Build deterministic proposal text from accepted Greenfield intent facts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


_SCALAR_FACTS = (
    ("title", "Product"),
    ("product_story", "Product story"),
    ("state_object", "State object"),
    ("first_path", "First complete path"),
    ("proof_boundary", "Proof boundary"),
    ("problem", "Problem"),
    ("customer", "Customer"),
    ("opportunity", "Opportunity"),
    ("product_view", "Product view"),
)
_LIST_FACTS = (
    ("human_actors", "Human actors"),
    ("external_systems", "External systems"),
    ("internal_systems", "Internal product systems"),
    ("assumptions", "Critical assumptions"),
    ("non_goals", "Non-goals"),
    ("success_metrics", "Success metrics"),
    ("evidence_requirements", "Evidence requirements"),
)


def accepted_intent_shaping_prompt(
    confirmed_intent: Mapping[str, Any],
    *,
    fallback_title: str,
) -> str:
    """Return proposal-shaping text from accepted intent facts only."""

    rows: list[str] = []
    for key, label in _SCALAR_FACTS:
        value = " ".join(str(confirmed_intent.get(key) or "").split()).strip()
        if value:
            rows.append(f"{label}: {value}")
    for key, label in _LIST_FACTS:
        values = confirmed_intent.get(key)
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            continue
        text = "; ".join(
            " ".join(str(item).split()).strip()
            for item in values
            if str(item).strip()
        )
        if text:
            rows.append(f"{label}: {text}")
    return "\n".join(rows).strip() or fallback_title


__all__ = ["accepted_intent_shaping_prompt"]
