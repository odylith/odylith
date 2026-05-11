"""Shared normalization helpers for Project intelligence."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


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
    token = " ".join(str(value or "").strip().split())
    return token or fallback


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
