"""Result-object helpers for first-path visible outcome extraction."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_text import clean_text


def saved_destination_result_object(verb: str, value: str) -> str:
    """Return a readable result object for clauses like "save X to history"."""

    participle = {
        "save": "saved",
        "saves": "saved",
    }.get(verb.casefold().strip(".,:;"))
    if not participle:
        return ""
    match = re.match(
        r"(?P<object>.+?)\s+(?:to|in)\s+(?P<destination>history|log|ledger|journal|timeline|archive)\b(?P<tail>.*)$",
        clean_text(value).strip(" ."),
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    item = _drop_leading_article(match.group("object")).strip(" .")
    tail = clean_text(match.group("tail")).strip(" .")
    suffix = f" {tail}" if tail else ""
    return f"{participle} {item} in {match.group('destination').casefold()}{suffix}".strip()


def _drop_leading_article(value: str) -> str:
    first, separator, rest = clean_text(value).strip(" .").partition(" ")
    if separator and first.casefold() in {"a", "an", "the"}:
        return rest.strip()
    return clean_text(value).strip(" .")


__all__ = ["saved_destination_result_object"]
