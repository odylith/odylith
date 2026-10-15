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
_AMBIGUOUS_CONTEXT = (
    "Greenfield authoring cited source context that is absent or ambiguous; no records were created."
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


def canonical_citation_from_host_selection(
    evidence: bytes,
    citation: Mapping[str, Any],
    *,
    state_object: bool = False,
    mention_selection: bool = False,
) -> dict[str, Any]:
    """Project one host-selected quote into the legacy canonical address.

    Context must be an exact unique source excerpt. Ordinary citations require
    one quote match inside it. Nonperformer mention selection requires an explicit
    ordinal over overlapping matches, even for a sole match. Context locates the
    selection and never enlarges its meaning.
    """

    if (
        not isinstance(citation, Mapping)
        or set(citation) != ({"quote", "context", "mention_ordinal"} if mention_selection else {"quote", "context"})
        or (mention_selection and state_object)
    ):
        raise GreenfieldModelAuthoringError(_INVALID_CITATION)
    quote = exact_quote(citation.get("quote"))
    context = exact_quote(citation.get("context"))
    if not quote or not context:
        raise GreenfieldModelAuthoringError(_INVALID_CITATION)
    if mention_selection and (
        type(citation["mention_ordinal"]) is not int
        or not 1 <= citation["mention_ordinal"] <= MAX_AUTHORED_FIELD_VALUE_CHARS
        or not quote.strip() or not context.strip()
    ):
        raise GreenfieldModelAuthoringError(_INVALID_CITATION)

    quote_bytes = quote.encode("utf-8")
    quote_starts = _overlapping_match_starts(evidence, quote_bytes)
    context_bytes = context.encode("utf-8")
    context_starts = _overlapping_match_starts(evidence, context_bytes)
    quote_offsets = _overlapping_match_starts(context_bytes, quote_bytes)
    if len(context_starts) != 1 or (not mention_selection and len(quote_offsets) != 1):
        raise GreenfieldModelAuthoringError(_AMBIGUOUS_CONTEXT)
    if mention_selection and citation["mention_ordinal"] > len(quote_offsets):
        raise GreenfieldModelAuthoringError(_MISSING_OCCURRENCE)

    context_start = context_starts[0]
    # Fresh nonperformers select explicitly, even when only one match exists.
    # Never enter the legacy sole-match normalization for a supplied ordinal.
    offset = quote_offsets[citation["mention_ordinal"] - 1] if mention_selection else quote_offsets[0]
    quote_start = context_start + offset
    if evidence[quote_start : quote_start + len(quote_bytes)] != quote_bytes:
        raise GreenfieldModelAuthoringError(_INVALID_CITATION)

    if len(quote_starts) == 1:
        if state_object:
            return {"prefix": "", "quote": quote, "anchor_occurrence": 1}
        return {"quote": quote, "occurrence": 1}

    if state_object:
        prefix_bytes = context_bytes[: quote_offsets[0]]
        anchor_bytes = prefix_bytes + quote_bytes
        anchor_starts = _overlapping_match_starts(evidence, anchor_bytes)
        try:
            anchor_occurrence = anchor_starts.index(context_start) + 1
        except ValueError as exc:
            raise GreenfieldModelAuthoringError(_INVALID_CITATION) from exc
        return {
            "prefix": prefix_bytes.decode("utf-8"),
            "quote": quote,
            "anchor_occurrence": anchor_occurrence,
        }

    try:
        occurrence = quote_starts.index(quote_start) + 1
    except ValueError as exc:
        raise GreenfieldModelAuthoringError(_INVALID_CITATION) from exc
    return {"quote": quote, "occurrence": occurrence}


def canonical_citation_from_source_span(evidence: bytes, *, start: int, end: int) -> dict[str, Any]:
    """Encode an already authenticated fixed address in the existing citation format."""
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(evidence):
        raise GreenfieldModelAuthoringError(_INVALID_CITATION)
    quote = exact_quote(evidence[start:end].decode("utf-8"))
    starts = _overlapping_match_starts(evidence, quote.encode("utf-8"))
    if start not in starts:
        raise GreenfieldModelAuthoringError(_INVALID_CITATION)
    citation = {"quote": quote, "occurrence": starts.index(start) + 1}
    if resolve_source_citation(evidence, citation) != (quote, start):
        raise GreenfieldModelAuthoringError(_INVALID_CITATION)
    return citation


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


__all__ = [
    "canonical_citation_from_host_selection",
    "exact_occurrence_start",
    "exact_quote",
    "resolve_source_citation",
]
