"""Read exact canonical Greenfield intent facts without semantic inference."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from typing import Any

TERMINAL_RESULT_FACT_FIELDS = (
    "first_path",
    "product_story",
    "opportunity",
    "product_view",
    "success_metrics",
    "proof_boundary",
)
CONSISTENCY_SOURCE_SPAN_FIELDS = frozenset(
    {
        "span_id",
        "section_key",
        "row_index",
        "classification",
        "text",
        "source_start_byte",
        "source_end_byte",
        "quote_sha256",
    }
)

def intent_text_at_path(intent: Mapping[str, Any], path: str) -> str:
    """Return the exact string at one root or one-index-deep intent path."""

    if not path.startswith("/"):
        return ""
    parts = path.removeprefix("/").split("/")
    value = intent.get(parts[0])
    if len(parts) == 1:
        return value if isinstance(value, str) else ""
    if (
        len(parts) != 2
        or not parts[1].isdigit()
        or not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
    ):
        return ""
    index = int(parts[1])
    return value[index] if index < len(value) and isinstance(value[index], str) else ""


def intent_text_rows(value: Any) -> tuple[str, ...]:
    """Return non-empty string rows from an optional intent list value."""

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(str(row) for row in value if str(row))


def intent_terminal_result_values(intent: Mapping[str, Any]) -> tuple[str, ...]:
    """Return exact selected output, path, and proof facts eligible as results."""

    values: list[str] = []
    for field in TERMINAL_RESULT_FACT_FIELDS:
        value = intent.get(field)
        if isinstance(value, str):
            if value:
                values.append(value)
        else:
            values.extend(intent_text_rows(value))
    return tuple(values)


def event_target_is_source_bound(*, event_quote: str, target_quote: str) -> bool:
    """Accept only a target quoted inside its exact source-bound event."""

    return not target_quote or target_quote in event_quote


def missing_source_fact_notice(subject: str) -> str:
    """Render an explicit evidence gap without inventing product meaning."""

    return f"The source does not state {subject}. Validate this gap before implementation."


def consistency_source_span_receipts_valid(
    value: Any,
    *,
    minimum: int,
    maximum: int = 4,
) -> bool:
    """Validate the product-owned consistency-span receipt contract."""

    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or not minimum <= len(value) <= maximum
    ):
        return False
    seen_ranges: set[tuple[int, int]] = set()
    for expected_index, span in enumerate(value, start=1):
        if not isinstance(span, Mapping) or set(span) != CONSISTENCY_SOURCE_SPAN_FIELDS:
            return False
        text = span.get("text")
        row_index = span.get("row_index")
        start = span.get("source_start_byte")
        end = span.get("source_end_byte")
        if (
            not isinstance(text, str)
            or not text
            or row_index != expected_index
            or not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 0
            or end != start + len(text.encode("utf-8"))
            or (start, end) in seen_ranges
            or span.get("span_id") != f"authoring:consistency:{expected_index}"
            or span.get("section_key") != "ambiguities"
            or span.get("classification") != "supporting_evidence"
            or span.get("quote_sha256")
            != hashlib.sha256(text.encode("utf-8")).hexdigest()
        ):
            return False
        seen_ranges.add((start, end))
    return True


__all__ = [
    "CONSISTENCY_SOURCE_SPAN_FIELDS",
    "TERMINAL_RESULT_FACT_FIELDS",
    "consistency_source_span_receipts_valid",
    "event_target_is_source_bound",
    "intent_terminal_result_values",
    "intent_text_at_path",
    "intent_text_rows",
    "missing_source_fact_notice",
]
