"""Recover a concrete place context when a request starts with a generic product noun."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_actor_terms import word_has_actor_role_signal
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


_GENERIC_PRODUCT_TERMS = frozenset(
    {"app", "application", "platform", "product", "service", "system", "tool", "utility", "workspace"}
)
_PLACE_TERMS = frozenset(
    {"building", "clinic", "facility", "home", "library", "room", "station", "studio", "venue", "workshop"}
)
_REQUEST_COMMAND_TERMS = frozenset(
    {"build", "create", "design", "draft", "develop", "make", "plan", "propose", "set", "up"}
)
_CONTEXTUAL_ROLE_TERMS = frozenset({"tenant"})


def contextual_product_title(value: str) -> str:
    """Return a place-qualified product title when the request carries one."""

    for sentence in _sentences(value):
        match = re.search(
            r"\bfor\s+(?:a|an|the)\s+(?P<context>[A-Za-z][A-Za-z0-9'-]*(?:\s+[A-Za-z][A-Za-z0-9'-]*){0,4}?)\s+"
            r"(?:where|that|which)\b",
            sentence,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        context = match.group("context").strip(" .")
        context_words = _words(context)
        if not context_words or context_words[-1] not in _PLACE_TERMS:
            continue
        product = _role_qualified_generic_product_term(sentence[: match.start()])
        if product:
            return f"{context} {product}"
    return ""


def _role_qualified_generic_product_term(value: str) -> str:
    words = _words(value)
    for index in range(len(words) - 1, -1, -1):
        product = words[index]
        if product not in _GENERIC_PRODUCT_TERMS:
            continue
        qualifiers = [
            word
            for word in words[:index]
            if word not in _REQUEST_COMMAND_TERMS and word not in {"a", "an", "the"}
        ]
        if qualifiers and all(_is_role_qualifier(word) for word in qualifiers):
            return product
    return ""


def _is_role_qualifier(value: str) -> bool:
    return value in _CONTEXTUAL_ROLE_TERMS or word_has_actor_role_signal(value)


def _sentences(value: str) -> tuple[str, ...]:
    return tuple(
        sentence.strip(" .")
        for sentence in re.split(r"(?<=[.!?])\s+", clean_markdown_text(value).strip())
        if sentence.strip(" .")
    )


def _words(value: str) -> list[str]:
    return [word.casefold() for word in re.findall(r"[A-Za-z][A-Za-z0-9'-]*", value)]


__all__ = ["contextual_product_title"]
