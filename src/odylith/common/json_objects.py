"""Shared JSON-object loading helpers for Odylith contracts and surfaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonObjectLoadError(ValueError):
    """Raised when a required JSON object cannot be loaded from disk."""

    def __init__(self, *, code: str, path: Path, detail: str = "") -> None:
        self.code = str(code or "").strip() or "invalid_json"
        self.path = Path(path)
        self.detail = str(detail or "").strip()
        super().__init__(self.default_message)

    @property
    def default_message(self) -> str:
        """Return the default operator-facing error string for this failure."""
        if self.code == "missing":
            return f"JSON object source is missing: {self.path}"
        if self.code == "not_object":
            return f"JSON object source must be a JSON object: {self.path}"
        detail = f": {self.detail}" if self.detail else ""
        return f"JSON object source is not valid JSON: {self.path}{detail}"


def read_json_object(path: Path) -> dict[str, Any]:
    """Load one JSON object from disk or raise a typed load error."""
    if not path.is_file():
        raise JsonObjectLoadError(code="missing", path=path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise JsonObjectLoadError(code="invalid_json", path=path, detail=str(exc)) from exc
    if not isinstance(payload, dict):
        raise JsonObjectLoadError(code="not_object", path=path)
    return payload


def load_json_object(path: Path) -> dict[str, Any]:
    """Load one JSON object from disk and fail open to an empty mapping."""
    try:
        return read_json_object(path)
    except JsonObjectLoadError:
        return {}


def load_json_object_or_none(path: Path) -> dict[str, Any] | None:
    """Load one JSON object from disk and return `None` when unavailable."""
    try:
        return read_json_object(path)
    except JsonObjectLoadError:
        return None
