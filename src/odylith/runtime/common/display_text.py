"""Shared cleanup for text that Odylith generates into consumer-visible records."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any


_INLINE_EMPHASIS_TOKEN_RE = re.compile(r"(?<!\*)\*\*(?!\*)|(?<!_)__(?!_)")


def strip_inline_markdown_emphasis_tokens(value: object) -> str:
    """Remove Markdown emphasis markers without changing caller-owned spacing."""

    return _INLINE_EMPHASIS_TOKEN_RE.sub("", str(value or ""))


def strip_inline_markdown_emphasis(value: object) -> str:
    """Remove emphasis markers from plain-text display values."""

    cleaned = strip_inline_markdown_emphasis_tokens(value)
    return " ".join(cleaned.split())


def strip_inline_markdown_emphasis_tree(value: object) -> Any:
    """Return ``value`` with inline emphasis tokens stripped from nested strings."""

    if isinstance(value, str):
        return strip_inline_markdown_emphasis_tokens(value)
    if isinstance(value, Mapping):
        return {key: strip_inline_markdown_emphasis_tree(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(strip_inline_markdown_emphasis_tree(item) for item in value)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [strip_inline_markdown_emphasis_tree(item) for item in value]
    return value
