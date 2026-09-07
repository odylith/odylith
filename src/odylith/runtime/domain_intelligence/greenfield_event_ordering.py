"""Separate cited source precedence from one proposed first-run walkthrough.

Event identities follow the selected citation array, not execution order. Precedence refers
to the existing operational-constraint facts; this module owns only structural
integrity and never infers temporal meaning from citation text.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from graphlib import CycleError, TopologicalSorter
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_operating_envelope import MAX_AUTHORED_LIST_ITEMS

_EVENT_INDEX = {"type": "integer", "minimum": 1, "maximum": 32}
_PRECEDENCE_FIELDS = ("before_event", "after_event", "constraint_index")
SOURCE_PRECEDENCE_SCHEMA = {
    "type": "array",
    "maxItems": 64,
    "items": {
        "type": "object", "additionalProperties": False,
        "required": list(_PRECEDENCE_FIELDS),
        "properties": {
            "before_event": dict(_EVENT_INDEX), "after_event": dict(_EVENT_INDEX),
            "constraint_index": {"type": "integer", "minimum": 1, "maximum": MAX_AUTHORED_LIST_ITEMS},
        },
    },
}
FIRST_RUN_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["event_orders", "rationale"],
    "properties": {
        "event_orders": {
            "type": "array", "minItems": 1, "maxItems": 32,
            "items": dict(_EVENT_INDEX),
        },
        "rationale": {"type": "string", "minLength": 1, "maxLength": 1000},
    },
}


def validate_source_precedence(
    value: Any, *, event_orders: Sequence[int], operational_constraints: Sequence[str],
) -> tuple[dict[str, int], ...]:
    """Bind edges to existing cited constraints without creating source facts."""

    accepted = _event_identities(event_orders)
    if (
        not isinstance(operational_constraints, Sequence)
        or isinstance(operational_constraints, (str, bytes, bytearray))
        or len(operational_constraints) > MAX_AUTHORED_LIST_ITEMS
        or any(not isinstance(row, str) or not row.strip() for row in operational_constraints)
    ):
        raise ValueError("Greenfield source precedence requires existing operational constraints")
    return _validated_edges(value, accepted=accepted, constraint_count=len(operational_constraints))


def _validated_edges(
    value: Any, *, accepted: set[int], constraint_count: int,
) -> tuple[dict[str, int], ...]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or len(value) > SOURCE_PRECEDENCE_SCHEMA["maxItems"]
    ):
        raise ValueError("Greenfield source precedence has an invalid edge list")
    seen: set[tuple[int, int]] = set()
    prerequisites: dict[int, list[int]] = {order: [] for order in accepted}
    rows: list[dict[str, int]] = []
    for row in value:
        if not isinstance(row, Mapping) or set(row) != set(_PRECEDENCE_FIELDS):
            raise ValueError("Greenfield source precedence has invalid edge fields")
        before, after, constraint = (row[field] for field in _PRECEDENCE_FIELDS)
        if (
            any(type(index) is not int for index in (before, after, constraint))
            or before not in accepted or after not in accepted or before == after
            or not 1 <= constraint <= constraint_count
        ):
            raise ValueError("Greenfield source precedence has invalid event or constraint references")
        if (before, after) in seen:
            raise ValueError("Greenfield source precedence contains a duplicate edge")
        seen.add((before, after))
        prerequisites[after].append(before)
        rows.append(dict(row))
    try:
        tuple(TopologicalSorter(prerequisites).static_order())
    except CycleError as exc:
        raise ValueError("Greenfield source precedence contains a cycle") from exc
    return tuple(rows)


def validate_first_run(
    value: Any, *, event_orders: Sequence[int],
    source_precedence: Sequence[Mapping[str, int]], result_event_order: int | None,
) -> dict[str, Any]:
    """Validate one complete proposed walk, never infer a runtime ordering."""

    accepted = _event_identities(event_orders)
    if not isinstance(value, Mapping) or set(value) != set(FIRST_RUN_SCHEMA["required"]):
        raise ValueError("Greenfield first run has an invalid design contract")
    if _event_identities(value["event_orders"]) != accepted:
        raise ValueError("Greenfield first run must include every source event exactly once")
    rationale = value["rationale"]
    if (
        not isinstance(rationale, str) or not rationale.strip()
        or len(rationale) > FIRST_RUN_SCHEMA["properties"]["rationale"]["maxLength"]
    ):
        raise ValueError("Greenfield first run requires a bounded nonblank rationale")
    if result_event_order is not None and (
        type(result_event_order) is not int or result_event_order not in accepted
    ):
        raise ValueError("Greenfield first run has an invalid explicit result event")
    positions = {order: index for index, order in enumerate(value["event_orders"])}
    for edge in _validated_edges(
        source_precedence, accepted=accepted, constraint_count=MAX_AUTHORED_LIST_ITEMS,
    ):
        if positions[edge["before_event"]] >= positions[edge["after_event"]]:
            raise ValueError("Greenfield first run violates cited source precedence")
    return deepcopy(dict(value))


def _event_identities(value: Any) -> set[int]:
    if (
        not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray))
        or not value or len(value) > 32
        or any(type(order) is not int or not 1 <= order <= 32 for order in value)
        or len(set(value)) != len(value)
    ):
        raise ValueError("Greenfield event orders must be unique bounded source identities")
    return set(value)


__all__ = [
    "SOURCE_PRECEDENCE_SCHEMA", "FIRST_RUN_SCHEMA",
    "validate_source_precedence", "validate_first_run",
]
