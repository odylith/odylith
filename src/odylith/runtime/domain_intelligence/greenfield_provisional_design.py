"""Closed provisional delivery design bound to verified source-event identities.

Design rows propose implementation ownership; their event references identify
the source actions they support, never actors or facts they may replace.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from graphlib import CycleError, TopologicalSorter
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_event_ordering import (
    FIRST_RUN_SCHEMA,
    validate_first_run,
)

PROVISIONAL_DESIGN_VERSION = "odylith.greenfield.provisional-design.v2"
PROVISIONAL_DESIGN_AUTHORITY_KIND = "provisional_design"
_TEXT = {"type": "string", "minLength": 1, "maxLength": 4000}
_KEY = {"type": "string", "minLength": 1, "maxLength": 80, "pattern": "^[a-z][a-z0-9-]*$"}
_COMPONENT_FIELDS = {
    "key": _KEY,
    "name": _TEXT,
    "responsibility": _TEXT,
    "supported_event_orders": {
        "type": "array", "minItems": 1, "maxItems": 32,
        "items": {"type": "integer", "minimum": 1, "maximum": 32},
    },
    "verification": _TEXT,
}
_WORKSTREAM_FIELDS = {
    "key": _KEY,
    "title": _TEXT,
    "component_keys": {"type": "array", "minItems": 1, "maxItems": 5, "items": _KEY},
    "depends_on": {"type": "array", "minItems": 0, "maxItems": 4, "items": _KEY},
    "deliverable": _TEXT,
    "verification": _TEXT,
}
_EXCHANGE_FIELDS = {"from_component": _KEY, "to_component": _KEY, "contract": _TEXT}


def _row_schema(fields: Mapping[str, Any], *, minimum: int, maximum: int) -> dict[str, Any]:
    return {
        "type": "array", "minItems": minimum, "maxItems": maximum,
        "items": {
            "type": "object", "additionalProperties": False,
            "required": list(fields), "properties": deepcopy(dict(fields)),
        },
    }


PROVISIONAL_DESIGN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["version", "authority_kind", "components", "workstreams", "exchanges", "first_run"],
    "properties": {
        "version": {"type": "string", "const": PROVISIONAL_DESIGN_VERSION},
        "authority_kind": {"type": "string", "const": PROVISIONAL_DESIGN_AUTHORITY_KIND},
        "components": _row_schema(_COMPONENT_FIELDS, minimum=4, maximum=5),
        "workstreams": _row_schema(_WORKSTREAM_FIELDS, minimum=4, maximum=5),
        "exchanges": _row_schema(_EXCHANGE_FIELDS, minimum=0, maximum=32),
        "first_run": FIRST_RUN_SCHEMA,
    },
}


def validate_provisional_design(
    value: Any, *, event_orders: Sequence[int],
    source_precedence: Sequence[Mapping[str, int]] = (), result_event_order: int | None = None,
) -> dict[str, Any]:
    """Validate structural design obligations without interpreting source prose."""

    if (
        not isinstance(value, Mapping)
        or set(value) != set(PROVISIONAL_DESIGN_SCHEMA["required"])
        or value.get("version") != PROVISIONAL_DESIGN_VERSION
        or value.get("authority_kind") != PROVISIONAL_DESIGN_AUTHORITY_KIND
    ):
        raise ValueError("Greenfield provisional design has an unsupported authority contract")
    if (
        not isinstance(event_orders, Sequence)
        or isinstance(event_orders, (str, bytes, bytearray))
        or not event_orders
        or any(type(order) is not int or not 1 <= order <= 32 for order in event_orders)
        or len(set(event_orders)) != len(event_orders)
    ):
        raise ValueError("Greenfield provisional design requires valid source-event orders")
    validate_first_run(
        value["first_run"], event_orders=event_orders,
        source_precedence=source_precedence, result_event_order=result_event_order,
    )
    components = _design_rows(value, "components", _COMPONENT_FIELDS, minimum=4, maximum=5)
    workstreams = _design_rows(value, "workstreams", _WORKSTREAM_FIELDS, minimum=4, maximum=5)
    exchanges = _design_rows(value, "exchanges", _EXCHANGE_FIELDS, minimum=0, maximum=32)
    _require_unique_identities(components, display_field="name", label="component")
    _require_unique_identities(workstreams, display_field="title", label="workstream")
    component_keys = {row["key"] for row in components}
    workstream_keys = {row["key"] for row in workstreams}
    accepted_orders = set(event_orders)
    supported_orders: set[int] = set()
    for row in components:
        orders = row["supported_event_orders"]
        if len(set(orders)) != len(orders) or not set(orders) <= accepted_orders:
            raise ValueError("Greenfield provisional component has invalid source-event references")
        supported_orders.update(orders)
    if supported_orders != accepted_orders:
        raise ValueError("Greenfield provisional design does not support every source action")
    assigned_components: set[str] = set()
    prerequisites: dict[str, list[str]] = {}
    for row in workstreams:
        keys, dependencies = row["component_keys"], row["depends_on"]
        if len(set(keys)) != len(keys) or not set(keys) <= component_keys:
            raise ValueError("Greenfield provisional workstream has invalid component references")
        if (
            len(set(dependencies)) != len(dependencies)
            or not set(dependencies) <= workstream_keys - {row["key"]}
        ):
            raise ValueError("Greenfield provisional workstream has invalid prerequisite references")
        assigned_components.update(keys)
        prerequisites[row["key"]] = dependencies
    if assigned_components != component_keys:
        raise ValueError("Greenfield provisional design leaves a component without delivery work")
    try:
        tuple(TopologicalSorter(prerequisites).static_order())
    except CycleError as exc:
        raise ValueError("Greenfield provisional workstream prerequisites contain a cycle") from exc
    seen_exchanges: set[tuple[str, str, str]] = set()
    for row in exchanges:
        origin, target = row["from_component"], row["to_component"]
        edge = (origin, target, _identity(row["contract"]))
        if origin not in component_keys or target not in component_keys or origin == target:
            raise ValueError("Greenfield provisional exchange must connect distinct internal components")
        if edge in seen_exchanges:
            raise ValueError("Greenfield provisional design contains a duplicate exchange")
        seen_exchanges.add(edge)
    return deepcopy(dict(value))


def provisional_design_from_intent(intent: Mapping[str, Any]) -> dict[str, Any]:
    """Read design only from the complete validated authored-semantic carrier."""

    from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
        AUTHORED_SEMANTICS_KEY,
        first_path_relations_from_intent,
    )

    relations = first_path_relations_from_intent(intent)
    semantics = intent.get(AUTHORED_SEMANTICS_KEY) if isinstance(intent, Mapping) else None
    return validate_provisional_design(
        semantics.get("provisional_design") if isinstance(semantics, Mapping) else None,
        event_orders=tuple(row["order"] for row in relations),
        source_precedence=semantics["source_precedence"],
        result_event_order=next(row["order"] for row in relations if row["visible_result_quote"]),
    )


def _design_rows(
    design: Mapping[str, Any], name: str, fields: Mapping[str, Any], *, minimum: int, maximum: int,
) -> list[Mapping[str, Any]]:
    rows = design[name]
    if not isinstance(rows, list) or not minimum <= len(rows) <= maximum:
        raise ValueError(f"Greenfield provisional {name} has an invalid row count")
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != set(fields):
            raise ValueError(f"Greenfield provisional {name} has invalid row fields")
        for field, schema in fields.items():
            raw = row[field]
            if schema["type"] == "string":
                if schema["maxLength"] == 80:
                    _require_key(raw)
                else:
                    _require_text(raw, maximum=schema["maxLength"])
            elif not isinstance(raw, list) or not schema["minItems"] <= len(raw) <= schema["maxItems"]:
                raise ValueError(f"Greenfield provisional {name}.{field} has an invalid list")
            elif schema["items"]["type"] == "integer":
                if any(type(item) is not int or not 1 <= item <= 32 for item in raw):
                    raise ValueError("Greenfield provisional design has invalid source-event orders")
            else:
                for item in raw:
                    _require_key(item)
    return rows


def _require_text(value: Any, *, maximum: int) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError("Greenfield provisional design fields must be bounded nonblank strings")


def _require_key(value: Any) -> None:
    _require_text(value, maximum=80)
    if value[0] not in "abcdefghijklmnopqrstuvwxyz" or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in value
    ):
        raise ValueError("Greenfield provisional design keys must be path-safe lowercase identifiers")


def _identity(value: str) -> str:
    return " ".join(value.split()).casefold()


def _require_unique_identities(rows: Sequence[Mapping[str, Any]], *, display_field: str, label: str) -> None:
    for field in ("key", display_field):
        identities = [_identity(row[field]) for row in rows]
        if len(set(identities)) != len(identities):
            raise ValueError(f"Greenfield provisional design contains duplicate {label} {field} identities")


__all__ = [
    "PROVISIONAL_DESIGN_AUTHORITY_KIND",
    "PROVISIONAL_DESIGN_SCHEMA",
    "PROVISIONAL_DESIGN_VERSION",
    "provisional_design_from_intent",
    "validate_provisional_design",
]
