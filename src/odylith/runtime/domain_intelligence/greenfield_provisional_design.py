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

PROVISIONAL_DESIGN_VERSION = "odylith.greenfield.provisional-design.v4"
PROVISIONAL_DESIGN_AUTHORITY_KIND = "provisional_design"
_TEXT = {"type": "string", "minLength": 1, "maxLength": 4000}
_KEY = {"type": "string", "minLength": 1, "maxLength": 80, "pattern": "^[a-z][a-z0-9-]*$"}
_EVENT_ORDERS = {
    "type": "array", "minItems": 1, "maxItems": 32,
    "items": {"type": "integer", "minimum": 1, "maximum": 32},
}
_COMPONENT_FIELDS = {
    "key": _KEY,
    "name": _TEXT,
    "responsibility": _TEXT,
    "supported_event_orders": {
        "description": (
            "One-based source-event identities supported by this component. Across all "
            "components, cover every source event exactly as authored, including human "
            "actions; support does not transfer a human action to the component."
        ),
        **_EVENT_ORDERS,
    },
    "verification": _TEXT,
    "verification_event_orders": {
        "description": (
            "Source-event identities whose outcome this component verification checks. "
            "They must be supported by this component and remain proposed verification scope."
        ),
        **_EVENT_ORDERS,
    },
}
_WORKSTREAM_FIELDS = {
    "key": _KEY,
    "title": _TEXT,
    "component_keys": {"type": "array", "minItems": 1, "maxItems": 5, "items": _KEY},
    "depends_on": {"type": "array", "minItems": 0, "maxItems": 4, "items": _KEY},
    "deliverable": _TEXT,
    "verification": _TEXT,
    "verification_event_orders": {
        "description": (
            "Source-event identities whose outcome this workstream acceptance checks. "
            "They must be supported by one of the workstream's components."
        ),
        **_EVENT_ORDERS,
    },
}
_EXCHANGE_FIELDS = {"from_component": _KEY, "to_component": _KEY, "contract": _TEXT}
_RISK_CATEGORIES = (
    "abuse",
    "accessibility",
    "compliance",
    "data_retention",
    "operational",
    "privacy",
    "product",
    "security",
)
_RISK_ITEM_FIELDS = {
    "key": _KEY,
    "category": {"type": "string", "enum": list(_RISK_CATEGORIES)},
    "statement": _TEXT,
    "trigger": _TEXT,
    "mitigation": _TEXT,
    "verification": _TEXT,
    "component_keys": {"type": "array", "minItems": 1, "maxItems": 5, "items": _KEY},
    "workstream_keys": {"type": "array", "minItems": 1, "maxItems": 5, "items": _KEY},
    "related_event_orders": {
        "type": "array", "minItems": 0, "maxItems": 32,
        "items": {"type": "integer", "minimum": 1, "maximum": 32},
    },
}
_RISK_POSTURE_SCHEMA = {
    "type": "object",
    "description": (
        "A proportional reviewed implementation-risk posture. Identify material product, "
        "operational, security, privacy, abuse, accessibility, retention, or compliance "
        "exposure when present; otherwise explain why none is material for this project."
    ),
    "additionalProperties": False,
    "required": ["status", "rationale", "items"],
    "properties": {
        "status": {
            "type": "string",
            "enum": ["material_risks_identified", "no_material_risks_identified"],
        },
        "rationale": _TEXT,
        "items": {
            "type": "array",
            "minItems": 0,
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": list(_RISK_ITEM_FIELDS),
                "properties": deepcopy(_RISK_ITEM_FIELDS),
            },
        },
    },
}


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
    "required": [
        "version", "authority_kind", "components", "workstreams", "exchanges", "first_run",
        "risk_posture",
    ],
    "properties": {
        "version": {"type": "string", "const": PROVISIONAL_DESIGN_VERSION},
        "authority_kind": {"type": "string", "const": PROVISIONAL_DESIGN_AUTHORITY_KIND},
        "components": _row_schema(_COMPONENT_FIELDS, minimum=4, maximum=5),
        "workstreams": _row_schema(_WORKSTREAM_FIELDS, minimum=4, maximum=5),
        "exchanges": _row_schema(_EXCHANGE_FIELDS, minimum=0, maximum=32),
        "first_run": FIRST_RUN_SCHEMA,
        "risk_posture": _RISK_POSTURE_SCHEMA,
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
    component_verified_orders: set[int] = set()
    components_by_key = {row["key"]: row for row in components}
    for row in components:
        orders = row["supported_event_orders"]
        if len(set(orders)) != len(orders) or not set(orders) <= accepted_orders:
            raise ValueError("Greenfield provisional component has invalid source-event references")
        verification_orders = row["verification_event_orders"]
        if (
            len(set(verification_orders)) != len(verification_orders)
            or not set(verification_orders) <= set(orders)
        ):
            raise ValueError("Greenfield provisional component has invalid verification references")
        supported_orders.update(orders)
        component_verified_orders.update(verification_orders)
    if supported_orders != accepted_orders:
        raise ValueError("Greenfield provisional design does not support every source action")
    if component_verified_orders != accepted_orders:
        raise ValueError("Greenfield provisional design does not verify every source action")
    assigned_components: set[str] = set()
    workstream_verified_orders: set[int] = set()
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
        verification_orders = row["verification_event_orders"]
        supported_by_workstream = {
            order for key in keys for order in components_by_key[key]["supported_event_orders"]
        }
        if (
            len(set(verification_orders)) != len(verification_orders)
            or not set(verification_orders) <= supported_by_workstream
        ):
            raise ValueError("Greenfield provisional workstream has invalid verification references")
        assigned_components.update(keys)
        workstream_verified_orders.update(verification_orders)
        prerequisites[row["key"]] = dependencies
    if assigned_components != component_keys:
        raise ValueError("Greenfield provisional design leaves a component without delivery work")
    if workstream_verified_orders != accepted_orders:
        raise ValueError("Greenfield provisional workstreams do not verify every source action")
    proof_event_order = result_event_order or value["first_run"]["event_orders"][-1]
    if (
        proof_event_order not in component_verified_orders
        or proof_event_order not in workstream_verified_orders
    ):
        raise ValueError("Greenfield provisional design does not verify its proof outcome")
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
    _validate_risk_posture(
        value["risk_posture"],
        component_keys=component_keys,
        workstream_keys=workstream_keys,
        component_keys_by_workstream={
            row["key"]: set(row["component_keys"]) for row in workstreams
        },
        supported_orders_by_component={
            row["key"]: set(row["supported_event_orders"]) for row in components
        },
        accepted_orders=accepted_orders,
    )
    return deepcopy(dict(value))


def _validate_risk_posture(
    value: Any,
    *,
    component_keys: set[str],
    workstream_keys: set[str],
    component_keys_by_workstream: Mapping[str, set[str]],
    supported_orders_by_component: Mapping[str, set[int]],
    accepted_orders: set[int],
) -> None:
    if not isinstance(value, Mapping) or set(value) != {"status", "rationale", "items"}:
        raise ValueError("Greenfield provisional risk posture has invalid fields")
    status = value.get("status")
    if status not in {"material_risks_identified", "no_material_risks_identified"}:
        raise ValueError("Greenfield provisional risk posture has an invalid status")
    _require_text(value.get("rationale"), maximum=4000)
    items = _design_rows(value, "items", _RISK_ITEM_FIELDS, minimum=0, maximum=8)
    if (status == "material_risks_identified") != bool(items):
        raise ValueError("Greenfield provisional risk posture status does not match its items")
    _require_unique_identities(items, display_field="statement", label="risk")
    for row in items:
        if row["category"] not in _RISK_CATEGORIES:
            raise ValueError("Greenfield provisional risk has an invalid category")
        if (
            len(set(row["component_keys"])) != len(row["component_keys"])
            or not set(row["component_keys"]) <= component_keys
            or len(set(row["workstream_keys"])) != len(row["workstream_keys"])
            or not set(row["workstream_keys"]) <= workstream_keys
        ):
            raise ValueError("Greenfield provisional risk has invalid design references")
        risk_component_keys = set(row["component_keys"])
        risk_workstream_keys = set(row["workstream_keys"])
        owned_risk_components = {
            component_key
            for workstream_key in risk_workstream_keys
            for component_key in component_keys_by_workstream[workstream_key]
            if component_key in risk_component_keys
        }
        if (
            owned_risk_components != risk_component_keys
            or any(
                not component_keys_by_workstream[workstream_key] & risk_component_keys
                for workstream_key in risk_workstream_keys
            )
        ):
            raise ValueError(
                "Greenfield provisional risk has incoherent component/workstream allocation"
            )
        event_orders = row["related_event_orders"]
        if len(set(event_orders)) != len(event_orders) or not set(event_orders) <= accepted_orders:
            raise ValueError("Greenfield provisional risk has invalid source-event references")
        supported_risk_orders = {
            event_order
            for component_key in risk_component_keys
            for event_order in supported_orders_by_component[component_key]
        }
        if not set(event_orders) <= supported_risk_orders:
            raise ValueError(
                "Greenfield provisional risk source events are not supported by its components"
            )


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
        result_event_order=next(
            (row["order"] for row in relations if row["visible_result_quote"]),
            None,
        ),
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
                if "enum" in schema:
                    if raw not in schema["enum"]:
                        raise ValueError(f"Greenfield provisional {name}.{field} has an invalid value")
                elif schema["maxLength"] == 80:
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
