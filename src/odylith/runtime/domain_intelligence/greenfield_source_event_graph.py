"""Own the versioned complete source-event graph and deterministic path projection."""

from __future__ import annotations
from collections.abc import Mapping, Sequence
from copy import deepcopy
import hashlib
import json
from typing import Any
from odylith.runtime.domain_intelligence.greenfield_authored_relation_validation import (
    FIRST_PATH_RELATION_FIELDS, GreenfieldAuthoredSemanticsError,
)
from odylith.runtime.domain_intelligence.greenfield_provisional_design import validate_provisional_design

AUTHORED_SEMANTICS_VERSION = "odylith.greenfield.authored-semantics.v19"
PASSIVE_AUTHORED_SEMANTICS_VERSION = "odylith.greenfield.authored-semantics.v18"
VERIFIED_COMPONENT_PROVENANCE_FIELDS = frozenset({"source_duty_id", "decision_set_sha256"})

FIRST_PATH_CONTEXT_RELATION_FIELDS = frozenset(
    {
        "context_kind",
        "fact_path",
        "fact_quote",
        "source_start_byte",
        "source_end_byte",
        "first_path_event_order",
    }
)
COMPONENT_RESPONSIBILITY_RELATION_FIELDS = frozenset(
    {
        "responsibility_path",
        "responsibility_quote",
        "owner_system_path",
        "owner_system_quote",
        "first_path_event_order",
        "responsibility_source",
    }
)
def source_event_relation_key(version: str) -> str:
    """Select only an exact current or retained historical contract shape."""
    if version == AUTHORED_SEMANTICS_VERSION:
        return "source_event_relations"
    if version == PASSIVE_AUTHORED_SEMANTICS_VERSION:
        return "first_path_relations"
    raise GreenfieldAuthoredSemanticsError("Greenfield authored semantics version is unsupported")


def declared_source_path(
    relations: Sequence[Mapping[str, Any]], source_duty: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], ...]:
    """Select source-declared path identities without copying semantic authority."""
    if source_duty is None:
        return tuple(dict(row) for row in relations)
    binding = source_duty.get("binding")
    rows = binding.get("first_path_actions") if isinstance(binding, Mapping) else None
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)) or not rows:
        raise GreenfieldAuthoredSemanticsError("Greenfield source-duty path binding is malformed")
    orders = tuple(row.get("event_order") for row in rows if isinstance(row, Mapping))
    by_order = {row["order"]: row for row in relations}
    if (len(orders) != len(rows) or len(set(orders)) != len(orders)
            or any(type(order) is not int or order not in by_order for order in orders)):
        raise GreenfieldAuthoredSemanticsError("Greenfield source-duty path binding is malformed")
    return tuple(dict(by_order[order]) for order in orders)


def source_event_reference(semantics_version: str, order: int) -> str:
    """Address a stable source ID through its exact version-owned graph key."""
    key = source_event_relation_key(semantics_version)
    if type(order) is not int or not 1 <= order <= 32:
        raise GreenfieldAuthoredSemanticsError("Greenfield source-event reference is invalid")
    return f"/authored_semantics/{key}/{order - 1}"


def authored_semantics_mapping(
    relations: Sequence[Mapping[str, Any]],
    component_responsibility_relations: Sequence[Mapping[str, Any]] = (),
    *,
    first_path_context_relations: Sequence[Mapping[str, Any]] = (),
    source_precedence: Sequence[Mapping[str, Any]] = (),
    provisional_design: Mapping[str, Any],
    source_duty: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Serialize source relations and tagged design without replacing source facts."""

    return {
        "version": AUTHORED_SEMANTICS_VERSION,
        "source_event_relations": [dict(row) for row in relations],
        "first_path_context_relations": [
            dict(row) for row in first_path_context_relations
        ],
        "component_responsibility_relations": [
            dict(row) for row in component_responsibility_relations
        ],
        "source_precedence": [dict(row) for row in source_precedence],
        "source_duty": deepcopy(dict(source_duty)) if source_duty is not None else None,
        "provisional_design": validate_provisional_design(
            provisional_design, event_orders=tuple(row["order"] for row in relations),
            source_precedence=source_precedence,
            result_event_order=next((row["order"] for row in relations if row["visible_result_quote"]), None),
        ),
    }


def authored_relation_set_sha256(
    relations: Sequence[Mapping[str, Any]],
    component_responsibility_relations: Sequence[Mapping[str, Any]] = (),
    *,
    first_path_context_relations: Sequence[Mapping[str, Any]] = (),
    source_precedence: Sequence[Mapping[str, Any]] = (),
    provisional_design: Mapping[str, Any] | None = None,
    source_duty: Mapping[str, Any] | None = None,
    semantics_version: str = AUTHORED_SEMANTICS_VERSION,
) -> str:
    """Bind source relations and provisional design in one semantic custody hash."""

    if isinstance(relations, (str, bytes, bytearray)):
        raise GreenfieldAuthoredSemanticsError("Greenfield authored relation custody is malformed")
    first_path_payload: list[dict[str, Any]] = []
    for relation in relations:
        if not isinstance(relation, Mapping) or set(relation) != FIRST_PATH_RELATION_FIELDS:
            raise GreenfieldAuthoredSemanticsError("Greenfield authored relation custody is malformed")
        first_path_payload.append(dict(relation))
    component_payload: list[dict[str, Any]] = []
    for relation in component_responsibility_relations:
        if (
            not isinstance(relation, Mapping)
            or set(relation) not in (COMPONENT_RESPONSIBILITY_RELATION_FIELDS,
                                    COMPONENT_RESPONSIBILITY_RELATION_FIELDS | VERIFIED_COMPONENT_PROVENANCE_FIELDS)
        ):
            raise GreenfieldAuthoredSemanticsError("Greenfield authored relation custody is malformed")
        component_payload.append(dict(relation))
    context_payload: list[dict[str, Any]] = []
    for relation in first_path_context_relations:
        if (
            not isinstance(relation, Mapping)
            or set(relation) != FIRST_PATH_CONTEXT_RELATION_FIELDS
        ):
            raise GreenfieldAuthoredSemanticsError("Greenfield authored relation custody is malformed")
        context_payload.append(dict(relation))
    precedence_payload = []
    for row in source_precedence:
        if not isinstance(row, Mapping) or set(row) != {"before_event", "after_event", "constraint_index"}:
            raise GreenfieldAuthoredSemanticsError("Greenfield source precedence custody is malformed")
        precedence_payload.append(dict(row))
    if not first_path_payload and (component_payload or context_payload or precedence_payload or provisional_design is not None or source_duty is not None):
        raise GreenfieldAuthoredSemanticsError("Greenfield authored design requires source relations")
    if source_duty is not None and (
        not isinstance(source_duty, Mapping)
        or set(source_duty) != {"ledger_receipt", "binding", "lifecycle"}
    ):
        raise GreenfieldAuthoredSemanticsError("Greenfield source-duty custody is malformed")
    design_payload = validate_provisional_design(
        provisional_design, event_orders=tuple(row["order"] for row in first_path_payload),
        source_precedence=precedence_payload,
        result_event_order=next((row["order"] for row in first_path_payload if row["visible_result_quote"]), None),
    ) if first_path_payload else None
    canonical = json.dumps(
        {
            "version": semantics_version,
            source_event_relation_key(semantics_version): first_path_payload,
            "first_path_context_relations": context_payload,
            "component_responsibility_relations": component_payload,
            "source_precedence": precedence_payload,
            "source_duty": deepcopy(dict(source_duty)) if source_duty is not None else None,
            "provisional_design": design_payload,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()


