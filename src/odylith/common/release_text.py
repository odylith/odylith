"""Shared release-text normalization helpers for install and runtime surfaces."""

from __future__ import annotations

import re
from typing import Any

_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_release_text(
    value: Any,
    *,
    limit: int | None = 240,
    strip_html: bool = True,
    strip_format_tokens: str = "*_`>#",
) -> str:
    """Strip markdown noise from release-facing copy and optionally truncate it."""
    token = str(value or "").strip()
    if not token:
        return ""
    token = _MARKDOWN_LINK_RE.sub(r"\1", token)
    if strip_html:
        token = _HTML_TAG_RE.sub("", token)
    if strip_format_tokens:
        token = re.sub(f"[{re.escape(strip_format_tokens)}]", "", token)
    token = _WHITESPACE_RE.sub(" ", token).strip(" -:")
    if limit is not None and len(token) > limit:
        token = token[: max(0, int(limit) - 3)].rstrip() + "..."
    return token


def normalize_release_version(value: Any) -> str:
    """Normalize version input so callers can pass either `0.x.y` or `v0.x.y`."""
    token = str(value or "").strip()
    return token[1:] if token.startswith("v") else token
