"""Load one disclosed Greenfield case without exposing expected annotations."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any


def case_prompt(*, corpus_path: Path, case_id: str) -> str:
    """Return the exact prompt for one uniquely identified development case."""

    corpus = _mapping(json.loads(corpus_path.read_text(encoding="utf-8")), "corpus")
    cases = _rows(corpus.get("cases"), "corpus cases")
    matches = [row for row in cases if row.get("case_id") == case_id]
    if len(matches) != 1:
        raise RuntimeError(f"development corpus does not contain one case: {case_id}")
    prompt = str(matches[0].get("prompt") or "").strip()
    if not prompt:
        raise RuntimeError("development case prompt is empty")
    return prompt


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be a JSON object")
    return dict(value)


def _rows(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise RuntimeError(f"{label} must be a JSON object array")
    return [dict(row) for row in value]


__all__ = ["case_prompt"]
