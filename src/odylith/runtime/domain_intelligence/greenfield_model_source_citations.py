"""Resolve model-authored source citations to exact byte locations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelAuthoringError,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    MAX_AUTHORED_FIELD_VALUE_CHARS,
)

_INVALID_CITATION = (
    "Greenfield authoring returned invalid source citations; no records were created."
)
_MISSING_OCCURRENCE = (
    "Greenfield authoring cited a quote occurrence that is not present; no records were created."
)


def exact_quote(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    if len(value) > MAX_AUTHORED_FIELD_VALUE_CHARS:
        raise GreenfieldModelAuthoringError(
            "Greenfield authoring exceeded the declared intent size; no records were created."
        )
    return value


def exact_occurrence_start(haystack: bytes, needle: bytes, occurrence: Any) -> int:
    """Resolve a legacy citation, retaining its unique-match normalization."""

    count = _positive_occurrence(occurrence)
    if count == 0 or not needle:
        raise GreenfieldModelAuthoringError(_INVALID_CITATION)
    matches = _overlapping_match_starts(haystack, needle)
    if count <= len(matches):
        return matches[count - 1]
    if len(matches) == 1:
        return matches[0]
    raise GreenfieldModelAuthoringError(_MISSING_OCCURRENCE)


def resolve_source_citation(
    evidence: bytes,
    citation: Mapping[str, Any],
    *,
    state_object: bool = False,
) -> tuple[str, int]:
    """Validate one closed citation shape and return its quote and byte start."""

    if not isinstance(citation, Mapping):
        raise GreenfieldModelAuthoringError(_INVALID_CITATION)
    if not state_object:
        if set(citation) != {"quote", "occurrence"}:
            raise GreenfieldModelAuthoringError(_INVALID_CITATION)
        quote = exact_quote(citation.get("quote"))
        occurrence = citation.get("occurrence")
        if not quote or not _positive_occurrence(occurrence):
            raise GreenfieldModelAuthoringError(_INVALID_CITATION)
        return quote, exact_occurrence_start(evidence, quote.encode("utf-8"), occurrence)

    if set(citation) != {"quote", "prefix", "anchor_occurrence"}:
        raise GreenfieldModelAuthoringError(_INVALID_CITATION)
    quote = exact_quote(citation.get("quote"))
    prefix = citation.get("prefix")
    anchor_occurrence = citation.get("anchor_occurrence")
    if not quote or not isinstance(prefix, str) or not _positive_occurrence(anchor_occurrence):
        raise GreenfieldModelAuthoringError(_INVALID_CITATION)

    quote_bytes = quote.encode("utf-8")
    anchor_bytes = exact_quote(prefix + quote).encode("utf-8")
    anchor_start = _strict_occurrence_start(
        evidence,
        anchor_bytes,
        anchor_occurrence,
    )
    anchor_end = anchor_start + len(anchor_bytes)
    if evidence[anchor_start:anchor_end] != anchor_bytes:
        raise GreenfieldModelAuthoringError(_INVALID_CITATION)
    # The authored split selects the quote, even when it also occurs in the prefix.
    # Locator context cannot enlarge its meaning or rebind a wrong selection.
    start = anchor_start + len(prefix.encode("utf-8"))
    end = start + len(quote_bytes)
    if evidence[start:end] != quote_bytes:
        raise GreenfieldModelAuthoringError(_INVALID_CITATION)
    return quote, start


def _positive_occurrence(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 1 else 0


def _overlapping_match_starts(haystack: bytes, needle: bytes) -> list[int]:
    matches: list[int] = []
    cursor = 0
    while True:
        found = haystack.find(needle, cursor)
        if found < 0:
            return matches
        matches.append(found)
        cursor = found + 1


def _strict_occurrence_start(haystack: bytes, needle: bytes, occurrence: Any) -> int:
    count = _positive_occurrence(occurrence)
    if count == 0 or not needle:
        raise GreenfieldModelAuthoringError(_INVALID_CITATION)
    matches = _overlapping_match_starts(haystack, needle)
    if count <= len(matches):
        return matches[count - 1]
    raise GreenfieldModelAuthoringError(_MISSING_OCCURRENCE)


__all__ = ["exact_occurrence_start", "exact_quote", "resolve_source_citation"]
