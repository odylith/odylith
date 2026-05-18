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


def short(value: object, *, limit: int = 180, fallback: str = "") -> str:
    token = sentence(value, fallback)
    if len(token) <= limit:
        return token
    trimmed = token[: max(0, limit - 1)].rsplit(" ", 1)[0].rstrip(".,;:")
    return f"{trimmed}."


def strings(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [sentence(item) for item in value if sentence(item)]
