"""Shared normalization helpers for Project intelligence."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common import display_text as shared_display_text
from odylith.runtime.common.prose_grammar import strip_clipped_terminal_fragment
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import (
    capitalize_sentence_start_preserving_source_terms,
)


def dict_value(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def humanize(value: object, fallback: str = "") -> str:
    token = str(value or "").strip()
    if not token:
        return fallback
    return " ".join(part[:1].upper() + part[1:] for part in re.split(r"[-_\s.]+", token) if part)


def list_value(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def sentence(value: object, fallback: str = "") -> str:
    token = str(value or "").strip()
    token = shared_display_text.strip_inline_markdown_emphasis_tokens(token).replace("`", "")
    token = re.sub(r"\s+([,.;:?!])", r"\1", token)
    token = " ".join(token.split())
    return token or fallback


def display_text(value: object, fallback: str = "") -> str:
    """Normalize human-facing prose before it reaches rendered project surfaces."""

    token = sentence(value, fallback)
    if not token:
        return fallback
    return sentence(token, fallback)


def sanitize_actor_body(value: object) -> str:
    """Remove full-sentence first-path splices from actor descriptions."""

    text = display_text(value)
    if not text:
        return ""
    text = re.sub(
        r"\bto\s+complete\s+(?:a|an|the)\s+[a-z][^,.;!?]*(?:[.!?]\s+[A-Z][^,.;!?]*)*",
        "to complete the accepted first path",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bcontributes\s+information,\s+review,\s+or\s+action\s+needed\s+for\s+the\s+first\s+product\s+outcome\s+and\s+needs\s+the\s+result,\s+limits,\s+and\s+next\s+step\s+to\s+stay\s+understandable\b",
        "supplies context, reviews the result, or takes the next step named by the first release",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bcontributes\s+information,\s+review,\s+or\s+action\s+needed\b",
        "supplies context or reviews the result",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bwhen the path is\.$", "when the path is incomplete.", text, flags=re.IGNORECASE)
    text = re.sub(r"\bverifies that The\b", "verifies that the", text)
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return text


def short(value: object, *, limit: int = 180, fallback: str = "") -> str:
    """Return complete public sentences within a soft length preference."""

    token = sentence(value, fallback)
    if len(token) <= limit:
        return token
    sentences = [row.strip() for row in re.split(r"(?<=[.!?])\s+", token) if row.strip()]
    if len(sentences) <= 1:
        return token
    selected: list[str] = []
    total = 0
    for row in sentences:
        next_total = total + len(row) + (1 if selected else 0)
        if selected and next_total > limit:
            break
        selected.append(row)
        total = next_total
        if total >= limit:
            break
    return " ".join(selected) if selected else token


def complete_text(value: object, *, limit: int = 180, fallback: str = "") -> str:
    """Explicit complete-copy alias for callers that need to signal intent."""

    return short(value, limit=limit, fallback=fallback)


def tidy_fragment(value: object) -> str:
    """Return a compact fragment without dangling grammar."""

    text = sentence(value).strip(" .")
    text = re.sub(
        r"\b(?:accepted|proposed)\s+first\s+path\b",
        "first path",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:user-stated|source-backed|reviewable|visible)\s+evidence\b",
        "evidence",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:and|or|for|with|which|that|the|a|an|before|after|until)$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" ,;:.")
    text = _remove_dangling_tail(text).strip(" .")
    return capitalize_sentence_start_preserving_source_terms(text)


def _remove_dangling_tail(value: str) -> str:
    text = sentence(value).rstrip(" ,;:")
    trailing_tokens = {
        "a",
        "an",
        "and",
        "as",
        "at",
        "be",
        "been",
        "being",
        "by",
        "can",
        "could",
        "for",
        "from",
        "had",
        "has",
        "have",
        "in",
        "is",
        "include",
        "includes",
        "keep",
        "keeps",
        "must",
        "of",
        "on",
        "or",
        "remain",
        "remains",
        "return",
        "returns",
        "should",
        "the",
        "to",
        "was",
        "were",
        "will",
        "with",
        "without",
        "would",
    }
    while True:
        original = text
        text = strip_clipped_terminal_fragment(text)
        words = text.split()
        while words and words[-1].casefold().strip(".,;:") in trailing_tokens:
            words.pop()
        text = " ".join(words).rstrip(" ,;:")
        stripped = _strip_open_subordinate_tail(text, dangling_words=trailing_tokens)
        if stripped != text:
            text = stripped
            continue
        if text == original:
            return text or sentence(value).rstrip(" ,;:")


def _strip_open_subordinate_tail(value: str, *, dangling_words: set[str]) -> str:
    text = sentence(value).rstrip(" ,;:")
    match = re.search(r"(?:,?\s+)?\b(?P<connector>when|if|because|while|where|which|who|that)\b(?P<tail>[^.!?]*)$", text, flags=re.IGNORECASE)
    if not match:
        return text
    tail_words = [word.casefold().strip(".,;:") for word in match.group("tail").split() if word.strip(".,;:")]
    if len(tail_words) >= 5 and tail_words[-1] not in dangling_words:
        return text
    return text[: match.start()].rstrip(" ,;:")


def strings(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [sentence(item) for item in value if sentence(item)]
