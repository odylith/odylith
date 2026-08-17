"""Exact byte-citation custody shared by Greenfield semantic contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from typing import Any


SEMANTIC_SOURCE_IDS = ("operator_prompt", "operator_edit")


def semantic_source_ref_schema() -> dict[str, Any]:
    """Return the sole public schema for one exact evidence citation."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["source_id", "quote", "occurrence"],
        "properties": {
            "source_id": {"type": "string", "enum": list(SEMANTIC_SOURCE_IDS)},
            "quote": {"type": "string", "minLength": 1, "maxLength": 4000},
            "occurrence": {"type": "integer", "minimum": 1},
        },
    }


def require_semantic_source_refs(
    value: Any,
    *,
    evidence_sources: Mapping[str, str],
    allow_empty: bool = False,
    maximum: int = 8,
) -> list[dict[str, Any]]:
    """Validate citations against exact source bytes and return canonical rows."""

    rows = _sequence(value, maximum)
    if not rows and not allow_empty:
        raise ValueError("Semantic Intent fact lacks source citations")
    result: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, Mapping) or set(raw) != {
            "source_id", "quote", "occurrence",
        }:
            raise ValueError("Semantic Intent source ref has an invalid structure")
        resolve_semantic_source_ref(raw, evidence_sources=evidence_sources)
        result.append(dict(raw))
    return result


def semantic_source_ref_selection_schema(
    value: Any,
    *,
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Constrain a model to provider-safe handles for accepted citations."""

    catalog = semantic_source_ref_catalog(
        value,
        evidence_sources=evidence_sources,
    )
    return {
        "anyOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["ref_id"],
                "properties": {
                    "ref_id": {"type": "string", "enum": [ref_id]},
                },
            }
            for ref_id in catalog
        ]
    }


def semantic_source_ref_catalog(
    value: Any,
    *,
    evidence_sources: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    """Return deterministic handles for exact accepted citations."""

    rows = require_semantic_source_refs(
        value,
        evidence_sources=evidence_sources,
        maximum=80,
    )
    catalog: dict[str, dict[str, Any]] = {}
    for row in rows:
        encoded = json.dumps(
            row,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
        ref_id = f"source_ref_{hashlib.sha256(encoded).hexdigest()}"
        catalog[ref_id] = row
    return catalog


def bind_semantic_source_ref_selections(
    value: Any,
    *,
    catalog: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Decode provider-safe handles into canonical exact citations."""

    rows = _sequence(value, 8)
    if not rows:
        return []
    result: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, Mapping) or set(raw) != {"ref_id"}:
            raise ValueError("Semantic Intent source ref selection is malformed")
        ref_id = raw.get("ref_id")
        if not isinstance(ref_id, str) or ref_id not in catalog:
            raise ValueError("Semantic Intent source ref selection is outside its catalog")
        result.append(dict(catalog[ref_id]))
    return result


def resolve_semantic_source_ref(
    value: Mapping[str, Any],
    *,
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Resolve one citation to exact character coordinates and a byte hash."""

    source_id = value.get("source_id")
    if not isinstance(source_id, str) or source_id not in SEMANTIC_SOURCE_IDS:
        raise ValueError("Semantic Intent source citation references an unknown source")
    if source_id not in evidence_sources or not isinstance(evidence_sources[source_id], str):
        raise ValueError("Semantic Intent source citation references an unknown source")
    quote = value.get("quote")
    if not isinstance(quote, str) or not quote or len(quote) > 4000:
        raise ValueError("Semantic Intent source citation has an invalid quote")
    occurrence = value.get("occurrence")
    if not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 1:
        raise ValueError("Semantic Intent source citation has an invalid occurrence")
    start = _nth_occurrence(evidence_sources[source_id], quote, occurrence)
    if start < 0:
        raise ValueError("Semantic Intent source citation does not match exact evidence bytes")
    return {
        "source_id": source_id,
        "occurrence": occurrence,
        "char_start": start,
        "char_end": start + len(quote),
        "text_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
    }


def resolved_semantic_source_refs(
    value: Mapping[str, Any],
    *,
    evidence_sources: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Resolve and deduplicate every citation nested in a semantic contract."""

    refs: dict[tuple[str, int, int], dict[str, Any]] = {}
    for source_ref in _all_source_refs(value):
        resolved = resolve_semantic_source_ref(
            source_ref,
            evidence_sources=evidence_sources,
        )
        key = (resolved["source_id"], resolved["char_start"], resolved["char_end"])
        refs[key] = resolved
    return [refs[key] for key in sorted(refs)]


def _all_source_refs(value: Any) -> list[Mapping[str, Any]]:
    refs: list[Mapping[str, Any]] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key == "source_refs":
                refs.extend(
                    row
                    for row in _sequence(nested, 256)
                    if isinstance(row, Mapping)
                )
            else:
                refs.extend(_all_source_refs(nested))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            refs.extend(_all_source_refs(nested))
    return refs


def _sequence(value: Any, maximum: int) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("Semantic Intent source refs are malformed")
    rows = list(value)
    if len(rows) > maximum:
        raise ValueError("Semantic Intent source refs exceed their operating limit")
    return rows


def _nth_occurrence(source: str, quote: str, occurrence: int) -> int:
    start = -1
    cursor = 0
    for _ in range(occurrence):
        start = source.find(quote, cursor)
        if start < 0:
            return -1
        cursor = start + 1
    return start


__all__ = [
    "SEMANTIC_SOURCE_IDS",
    "bind_semantic_source_ref_selections",
    "require_semantic_source_refs",
    "resolve_semantic_source_ref",
    "resolved_semantic_source_refs",
    "semantic_source_ref_schema",
    "semantic_source_ref_catalog",
    "semantic_source_ref_selection_schema",
]
