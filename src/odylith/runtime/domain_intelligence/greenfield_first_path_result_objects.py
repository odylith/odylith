"""Result-object helpers for first-path visible outcome extraction."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_text import clean_text

_HANDOFF_RESULT_OBJECT_TERMS = frozenset(
    "approval approvals blocker blockers decision decisions evidence handoff handoffs queue readiness record records result results review status".split()
)
_HANDOFF_RESULT_MODIFIER_TERMS = frozenset(
    "accepted approved blocked captured final ready reviewed source-backed traceable validated versioned".split()
)
_HANDOFF_DESTINATION_TERMS = frozenset(
    "backlog board console desk inbox list portal queue register service system view workspace".split()
)


def handoff_visible_result_object(value: str) -> str:
    """Return the result object from a reviewed handoff into a product destination."""

    text = clean_text(value).strip(" .")
    match = re.search(r"\bhands?\s+(?P<object>.+?)\s+to\s+(?P<destination>[^.;,]+)$", text, flags=re.IGNORECASE)
    if not match:
        return ""
    raw_result_object = clean_text(match.group("object")).strip(" .")
    result_object = re.sub(r"^(?:(?:a|an|the)\s+)?reviewed\s+", "the ", raw_result_object, flags=re.IGNORECASE)
    result_object = clean_text(result_object).strip(" .")
    destination = clean_text(match.group("destination")).strip(" .")
    if not result_object or not destination:
        return ""
    object_terms = _terms(result_object)
    raw_object_terms = _terms(raw_result_object)
    destination_terms = _terms(destination)
    if not object_terms & _HANDOFF_RESULT_OBJECT_TERMS and not (
        raw_object_terms & _HANDOFF_RESULT_MODIFIER_TERMS and destination_terms & _HANDOFF_DESTINATION_TERMS
    ):
        return ""
    return f"the {_drop_leading_article(result_object)} to {destination}".strip(" .")


def saved_destination_result_object(verb: str, value: str) -> str:
    """Return a readable result object for clauses like "save X to history"."""

    participle = {
        "save": "saved",
        "saves": "saved",
    }.get(verb.casefold().strip(".,:;"))
    if not participle:
        return ""
    clean_value = clean_text(value).strip(" .")
    as_result = _saved_as_result_object(participle, clean_value)
    if as_result:
        return as_result
    match = re.match(
        r"(?P<object>.+?)\s+(?:to|in)\s+(?P<destination>history|log|ledger|journal|timeline|archive)\b(?P<tail>.*)$",
        clean_value,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    item = _drop_leading_article(match.group("object")).strip(" .")
    tail = clean_text(match.group("tail")).strip(" .")
    suffix = f" {tail}" if tail else ""
    return f"{participle} {item} in {match.group('destination').casefold()}{suffix}".strip()


def is_routing_pronoun_result(verb: str, value: str) -> bool:
    if not re.fullmatch(r"(?:sends?|returns?|delivers?)", str(verb or ""), flags=re.IGNORECASE):
        return False
    return bool(
        re.match(
            r"^(?:it|them|this|that)\s+(?:back\s+)?(?:for|to|via|through|into|with)\b",
            clean_text(value).strip(" ."),
            flags=re.IGNORECASE,
        )
    )


def drop_result_recipient(value: str) -> str:
    """Remove a short recipient phrase before the actual visible result object."""

    text = clean_text(value).strip(" .")
    if not text:
        return ""
    if re.match(
        r"^(?:a|an|the)\s+(?:[A-Za-z][A-Za-z0-9'-]*\s+){0,3}"
        r"(?:decision|event|outcome|readout|record|report|result|summary|view)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return text
    words = text.split()
    for index, word in enumerate(words[:5]):
        if index > 0 and re.match(r"^[A-Za-z][A-Za-z0-9'-]*'s$", word):
            return " ".join(words[index:]).strip(" .")
    text = re.sub(
        r"^(?:the\s+)?[A-Za-z][A-Za-z0-9'-]*(?:\s+[A-Za-z][A-Za-z0-9'-]*){0,3}\s+"
        r"(?=(?:a|an|the|their|its|what|whether|when|where|why|[A-Za-z][A-Za-z0-9'-]*'s)\b)",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    ).strip(" .")
    return text


def _drop_leading_article(value: str) -> str:
    first, separator, rest = clean_text(value).strip(" .").partition(" ")
    if separator and first.casefold() in {"a", "an", "the"}:
        return rest.strip()
    return clean_text(value).strip(" .")


def _terms(value: str) -> set[str]:
    return {word.casefold() for word in re.findall(r"[A-Za-z][A-Za-z0-9'-]*", clean_text(value))}


def _saved_as_result_object(participle: str, value: str) -> str:
    match = re.match(r"(?P<object>.+?)\s+as\s+(?P<target>.+)$", clean_text(value).strip(" ."), flags=re.IGNORECASE)
    if not match:
        return ""
    item = _drop_leading_article(match.group("object")).strip(" .")
    target = _drop_leading_article(match.group("target")).strip(" .")
    if not item or not target:
        return ""
    if item.casefold() in {"artifact", "artifacts", "output", "outputs", "outcome", "outcomes", "result", "results"}:
        return f"{participle} {target}".strip()
    return f"{participle} {item} as {target}".strip()


__all__ = [
    "drop_result_recipient",
    "handoff_visible_result_object",
    "is_routing_pronoun_result",
    "saved_destination_result_object",
]
