"""Coverage facts expected in generated Atlas first-path projections."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_text import clean_text


def atlas_first_path_contract_coverage_text(semantic_model: Mapping[str, Any]) -> str:
    """Return the structured FirstPathContract facts Atlas is expected to expose."""

    first_path = semantic_model.get("first_path_contract")
    if not isinstance(first_path, Mapping):
        return ""
    values: list[str] = []
    for key in ("action", "entity", "mutation", "visible_result", "recovery_path"):
        _append(values, first_path.get(key))
    events = first_path.get("events")
    if isinstance(events, list):
        for row in events:
            if not isinstance(row, Mapping):
                continue
            for key in ("action", "target_entity", "mutation", "text"):
                _append(values, row.get(key))
    if not values:
        _append(values, first_path.get("capability") or first_path.get("raw_path"))
    return clean_text(" ".join(values))


def _append(values: list[str], value: object) -> None:
    text = clean_text(value)
    if text:
        values.append(text)


__all__ = ["atlas_first_path_contract_coverage_text"]
