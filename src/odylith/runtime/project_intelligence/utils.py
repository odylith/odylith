"""Shared normalization helpers for Project intelligence."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common import display_text as shared_display_text


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
    text = re.sub(r"\bwhen the path is\.$", "when the path is incomplete.", text, flags=re.IGNORECASE)
    text = re.sub(r"\bverifies that The\b", "verifies that the", text)
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return text


def short(value: object, *, limit: int = 180, fallback: str = "") -> str:
    token = sentence(value, fallback)
    if len(token) <= limit:
        return token
    trimmed = token[: max(0, limit - 1)].rsplit(" ", 1)[0].rstrip(".,;:")
    trimmed = _remove_dangling_tail(trimmed)
    return f"{trimmed}."


def _remove_dangling_tail(value: str) -> str:
    text = sentence(value).rstrip(" ,;:")
    text = re.sub(
        r"(?:,?\s+)?\b(?:when|if|because|while|where|which|who|that)\b[^.!?]*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).rstrip(" ,;:")
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
        "must",
        "of",
        "on",
        "or",
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
    words = text.split()
    while words and words[-1].casefold().strip(".,;:") in trailing_tokens:
        words.pop()
    return " ".join(words).rstrip(" ,;:") or text


def strings(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [sentence(item) for item in value if sentence(item)]
