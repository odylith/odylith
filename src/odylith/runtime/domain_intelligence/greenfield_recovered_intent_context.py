"""Apply explicit operator and reviewer context to recovered product intent."""

from __future__ import annotations

import re
from collections.abc import Sequence

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import clean_text


def unique_actor_rows(rows: Sequence[str]) -> list[str]:
    unique: list[str] = []
    seen_labels: set[str] = set()
    for row in rows:
        text = clean_text(row)
        label = text.split(":", 1)[0].casefold()
        if not text or not label or label in seen_labels:
            continue
        seen_labels.add(label)
        unique.append(text)
    return unique


def localize_direct_actor(value: str, *, original: str, localized: str) -> str:
    """Keep a localized generic role consistent with its first path."""

    text = clean_text(value).strip()
    source = clean_text(original).strip(" .")
    target = clean_text(localized).strip(" .")
    if not text or not source or not target or source.casefold() == target.casefold():
        return text
    return re.sub(
        rf"^(?:(?:a|an|the)\s+)?{re.escape(source)}(?=\s)",
        target,
        text,
        count=1,
        flags=re.IGNORECASE,
    )


def proof_with_reviewer_obligations(proof: str, obligations: Sequence[str]) -> str:
    base = clean_text(proof).strip(" .")
    obligation_text = "; ".join(
        clean_text(row).strip(" .") for row in obligations if clean_text(row).strip(" .")
    )
    if not obligation_text or obligation_text.casefold() in base.casefold():
        return base
    return f"{base}. Reviewer obligations: {obligation_text}."


def story_with_operator_context(story: str, *, context: str) -> str:
    """Keep a user-stated target context visible in product truth."""

    clean_story = clean_text(story).strip()
    clean_context = clean_text(context).strip(" .")
    if not clean_context or clean_context.casefold() in clean_story.casefold():
        return clean_story
    return f"{clean_story.rstrip(' .')}. The initial product scope serves {clean_context}."


def assumptions_with_reviewer_obligations(
    assumptions: Sequence[str],
    obligations: Sequence[str],
) -> tuple[str, ...]:
    rows = [clean_text(row).strip(" .") for row in assumptions if clean_text(row).strip(" .")]
    seen = {row.casefold() for row in rows}
    for obligation in obligations:
        cleaned = clean_text(obligation).strip(" .")
        if cleaned and cleaned.casefold() not in seen:
            seen.add(cleaned.casefold())
            rows.append(cleaned)
    return tuple(rows)


__all__ = [
    "assumptions_with_reviewer_obligations",
    "localize_direct_actor",
    "proof_with_reviewer_obligations",
    "story_with_operator_context",
    "unique_actor_rows",
]
