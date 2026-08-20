"""Exact evidence custody between Greenfield authoring partitions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any


def require_discarded_evidence_separation(
    discarded_value: Any,
    *product_values: Any,
) -> None:
    """Keep exact discarded labels and citations outside all product truth."""

    if not isinstance(discarded_value, Sequence) or isinstance(
        discarded_value, (str, bytes, bytearray)
    ):
        raise ValueError("Semantic discarded evidence is malformed")
    labels: set[str] = set()
    refs: set[tuple[str, str, int]] = set()
    for raw in discarded_value:
        if not isinstance(raw, Mapping):
            raise ValueError("Semantic discarded evidence is malformed")
        label = raw.get("label")
        source_refs = raw.get("source_refs")
        if not isinstance(label, str) or not label or not isinstance(source_refs, list):
            raise ValueError("Semantic discarded evidence is malformed")
        labels.add(label)
        refs.update(_source_ref_keys(source_refs))
    for value in product_values:
        if refs & _nested_source_ref_keys(value):
            raise ValueError("Semantic product truth cites discarded evidence")
        strings = tuple(_nested_strings(value))
        if any(label in text for label in labels for text in strings):
            raise ValueError("Semantic product truth contains a discarded label")


def completion_without_discarded_citations(
    discarded_value: Any,
    completion_value: Any,
) -> dict[str, Any]:
    """Remove completion over-citation without weakening source-fact custody."""

    discarded_refs = _discarded_source_ref_keys(discarded_value)

    def filtered(value: Any) -> Any:
        if isinstance(value, Mapping):
            result: dict[str, Any] = {}
            for key, nested in value.items():
                if key != "source_refs":
                    result[str(key)] = filtered(nested)
                    continue
                refs = list(nested) if isinstance(nested, list) else nested
                keys = _source_ref_keys(refs)
                kept = [
                    deepcopy(ref)
                    for ref in refs
                    if _source_ref_keys([ref]).isdisjoint(discarded_refs)
                ]
                if keys and not kept:
                    raise ValueError(
                        "Semantic completion cites only discarded evidence"
                    )
                result[str(key)] = kept
            return result
        if isinstance(value, Sequence) and not isinstance(
            value, (str, bytes, bytearray)
        ):
            return [filtered(nested) for nested in value]
        return deepcopy(value)

    completion = filtered(completion_value)
    if not isinstance(completion, dict):
        raise ValueError("Semantic completion is malformed")
    require_discarded_evidence_separation(discarded_value, completion)
    return completion


def _discarded_source_ref_keys(value: Any) -> set[tuple[str, str, int]]:
    if not isinstance(value, Sequence) or isinstance(
        value, (str, bytes, bytearray)
    ):
        raise ValueError("Semantic discarded evidence is malformed")
    refs: set[tuple[str, str, int]] = set()
    for row in value:
        if not isinstance(row, Mapping):
            raise ValueError("Semantic discarded evidence is malformed")
        refs.update(_source_ref_keys(row.get("source_refs")))
    return refs


def _source_ref_keys(value: Any) -> set[tuple[str, str, int]]:
    if not isinstance(value, Sequence) or isinstance(
        value, (str, bytes, bytearray)
    ):
        raise ValueError("Semantic discarded evidence citations are malformed")
    result: set[tuple[str, str, int]] = set()
    for raw in value:
        if not isinstance(raw, Mapping) or set(raw) != {
            "source_id", "quote", "occurrence",
        }:
            raise ValueError("Semantic discarded evidence citations are malformed")
        source_id = raw.get("source_id")
        quote = raw.get("quote")
        occurrence = raw.get("occurrence")
        if (
            not isinstance(source_id, str) or not source_id
            or not isinstance(quote, str) or not quote
            or not isinstance(occurrence, int) or isinstance(occurrence, bool)
        ):
            raise ValueError("Semantic discarded evidence citations are malformed")
        result.add((source_id, quote, occurrence))
    return result


def _nested_source_ref_keys(value: Any) -> set[tuple[str, str, int]]:
    if isinstance(value, Mapping):
        if set(value) == {"source_id", "quote", "occurrence"}:
            return _source_ref_keys([value])
        result: set[tuple[str, str, int]] = set()
        for nested in value.values():
            result.update(_nested_source_ref_keys(nested))
        return result
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        result: set[tuple[str, str, int]] = set()
        for nested in value:
            result.update(_nested_source_ref_keys(nested))
        return result
    return set()


def _nested_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for nested in value.values():
            yield from _nested_strings(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        for nested in value:
            yield from _nested_strings(nested)


def accepted_partitioned_evidence_catalog(
    value: Any,
    *,
    catalog: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Return source-bound evidence and reject completion-only citations."""

    core = _mapping(value, "Semantic partitioned graph core")
    if set(core) != {"version", "source", "completion"}:
        raise ValueError("Semantic partitioned graph core is malformed")
    accepted = accepted_source_evidence_catalog(core.get("source"), catalog=catalog)
    source_ids = set(accepted)
    completion_ids = _reference_ids(core.get("completion"), catalog=catalog)
    if not completion_ids <= source_ids:
        raise ValueError("Semantic completion cites evidence not bound to source truth")
    return accepted


def accepted_source_evidence_catalog(
    value: Any,
    *,
    catalog: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Return exactly the evidence referenced by one typed source graph."""

    source = _mapping(value, "Semantic source graph")
    if set(source) == {"version", "path", "boundary"}:
        boundary = _mapping(source["boundary"], "Semantic source boundary")
        source = {
            "path": source["path"],
            "boundary": {
                key: nested
                for key, nested in boundary.items()
                if key != "discarded_evidence"
            },
        }
    source_ids = _reference_ids(source, catalog=catalog)
    if not source_ids:
        raise ValueError("Semantic source graph has no evidence custody")
    return {
        ref_id: dict(source_ref)
        for ref_id, source_ref in catalog.items()
        if ref_id in source_ids
    }


def _reference_ids(
    value: Any, *, catalog: Mapping[str, Mapping[str, Any]]
) -> set[str]:
    if isinstance(value, Mapping):
        if set(value) == {"ref_id"}:
            ref_id = value.get("ref_id")
            if not isinstance(ref_id, str) or ref_id not in catalog:
                raise ValueError("Semantic evidence block handle is malformed")
            return {ref_id}
        if set(value) == {"source_id", "quote", "occurrence"}:
            matches = [
                ref_id
                for ref_id, source_ref in catalog.items()
                if dict(source_ref) == dict(value)
            ]
            if len(matches) != 1:
                raise ValueError("Semantic source citation is outside its catalog")
            return {matches[0]}
        result: set[str] = set()
        for nested in value.values():
            result.update(_reference_ids(nested, catalog=catalog))
        return result
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        result = set()
        for nested in value:
            result.update(_reference_ids(nested, catalog=catalog))
        return result
    return set()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} is malformed")
    return dict(value)


__all__ = [
    "accepted_partitioned_evidence_catalog",
    "accepted_source_evidence_catalog",
    "completion_without_discarded_citations",
    "require_discarded_evidence_separation",
]
