"""Exact source spans for typed Greenfield Product Intent evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


def typed_product_claim_spans(
    *,
    facts: Mapping[str, Any],
    source_text: str,
    source_format: str,
    typed_source_formats: Sequence[str],
) -> dict[str, list[dict[str, Any]]]:
    """Return claim spans only for facts exactly present in a typed JSON source."""

    if source_format not in typed_source_formats or not source_text:
        return {}
    try:
        payload = json.loads(source_text)
    except (TypeError, json.JSONDecodeError):
        return {}
    source_facts = _source_facts(payload)
    if source_facts is None:
        return {}

    result: dict[str, list[dict[str, Any]]] = {}
    for key, fact_value in facts.items():
        if key not in source_facts or not _same_fact(source_facts.get(key), fact_value):
            continue
        rows = _fact_rows(fact_value)
        if not rows:
            continue
        result[key] = [
            {
                "span_id": f"{key}:typed-source:{index}",
                "section_key": key,
                "row_index": index,
                "classification": "product_claim",
                "text": row,
            }
            for index, row in enumerate(rows, start=1)
        ]
    return result


def append_typed_product_claim_spans(
    *,
    facts: Mapping[str, Any],
    source_text: str,
    source_format: str,
    typed_source_formats: Sequence[str],
    spans: list[dict[str, Any]],
    source_span_ids_by_field: dict[str, list[str]],
    product_claim_span_ids_by_field: dict[str, list[str]],
) -> None:
    """Append exact typed spans without overriding more specific source custody."""

    typed_spans = typed_product_claim_spans(
        facts=facts,
        source_text=source_text,
        source_format=source_format,
        typed_source_formats=typed_source_formats,
    )
    for key, rows in typed_spans.items():
        if source_span_ids_by_field.get(key):
            continue
        spans.extend(rows)
        span_ids = [str(row["span_id"]) for row in rows]
        source_span_ids_by_field[key] = span_ids
        product_claim_span_ids_by_field[key] = span_ids


def _source_facts(value: Any) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    for key in ("product_facts", "intent"):
        nested = value.get(key)
        if isinstance(nested, Mapping):
            return nested
    return value


def _same_fact(source_value: Any, fact_value: Any) -> bool:
    if _is_row_sequence(fact_value):
        return _casefold_rows(source_value) == _casefold_rows(fact_value)
    return clean_markdown_text(source_value).casefold() == clean_markdown_text(fact_value).casefold()


def _casefold_rows(value: Any) -> list[str]:
    return [row.casefold() for row in confirmed_text_values(value)]


def _fact_rows(value: Any) -> list[str]:
    if _is_row_sequence(value):
        return confirmed_text_values(value)
    text = clean_markdown_text(value)
    return [text] if text else []


def _is_row_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


__all__ = ["append_typed_product_claim_spans", "typed_product_claim_spans"]
