"""Title extraction helpers for confirmed Product Intent Confirmation text."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


def title_from_product_intent_line(value: object) -> str:
    """Return a product title from a title-like Product Intent Confirmation line."""

    text = clean_markdown_text(value)
    if not text or "product intent confirmation" not in text.casefold():
        return ""
    match = re.match(r"(.+?)\s+[—-]\s+Product Intent Confirmation$", text)
    if match:
        return clean_markdown_text(match.group(1))
    candidate = clean_markdown_text(re.sub(r"product intent confirmation", "", text, flags=re.IGNORECASE))
    if not candidate or looks_like_confirmation_action(candidate):
        return ""
    return candidate


def looks_like_confirmation_instruction(value: object) -> bool:
    """Return true for action/instruction lines that must not seed product titles."""

    text = str(value or "").strip()
    return bool(text) and (
        bool(re.match(r"^(?:[-*•]|\d+[.)])\s+", text)) or looks_like_confirmation_action(text)
    )


def looks_like_confirmation_action(value: object) -> bool:
    text = clean_markdown_text(str(value or "").lstrip("-*•0123456789.) ").strip())
    if not text:
        return False
    return text.casefold().startswith(
        (
            "confirm:",
            "edit:",
            "reject:",
            "confirm ",
            "edit ",
            "reject ",
            "confirmed cli after confirmation:",
            "next step",
        )
    )


__all__ = [
    "looks_like_confirmation_instruction",
    "title_from_product_intent_line",
]
