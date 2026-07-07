"""Typed first-path coverage helpers for post-confirm package gates."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


def first_path_contract_coverage_candidates(
    first_path: Mapping[str, Any],
) -> tuple[str, ...]:
    """Return SemanticModelIR first-path facts that can prove projection coverage."""

    values: list[str] = []
    _append_candidate(values, first_path.get("raw_path"))
    _append_event_candidates(values, first_path.get("events"))
    return tuple(unique_text(values))


def first_path_contract_has_coverage(
    first_path: Mapping[str, Any],
    text: str,
    *,
    overlap_ratio,
    threshold: float,
) -> bool:
    """Return true when any typed first-path fact has enough projection overlap."""

    candidates = first_path_contract_coverage_candidates(first_path)
    if not candidates:
        return False
    return any(overlap_ratio(candidate, text) >= threshold for candidate in candidates)


def _append_candidate(values: list[str], value: Any) -> None:
    text = clean_text(value)
    if len(text.split()) >= 3:
        values.append(text)


def _append_event_candidates(values: list[str], events: Any) -> None:
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes, bytearray)):
        return
    for row in events:
        if not isinstance(row, Mapping):
            continue
        _append_candidate(values, row.get("text"))
        _append_candidate(values, row.get("action"))
        _append_candidate(values, row.get("visible_result"))


__all__ = ["first_path_contract_coverage_candidates", "first_path_contract_has_coverage"]
