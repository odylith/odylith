"""Exact evidence custody between Greenfield authoring partitions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


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
            "boundary": dict(boundary),
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
]
