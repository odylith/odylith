"""Validate and project reviewer-owned operational-constraint custody."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_json import (
    encode_greenfield_model_value,
)

CANDIDATE_SOURCE_FIELDS = frozenset(
    (
        "status",
        "facts",
        "events",
        "components",
        "terminal",
        "source_precedence",
        "consistency",
        "ambiguities",
    )
)
CANDIDATE_PROPOSED_FIELDS = frozenset(("assumptions", "provisional_design"))

_PRODUCT_OWNER_SCHEMA = {
    "anyOf": [
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["field", "row"],
            "properties": {
                "field": {"type": "string", "const": "title"},
                "row": {"type": "integer", "const": 1},
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["field", "row"],
            "properties": {
                "field": {"type": "string", "const": "internal_systems"},
                "row": {"type": "integer", "minimum": 1},
            },
        },
    ]
}
_PARTICIPANT_ACTOR_SCHEMA = {
    "anyOf": [
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["field", "row"],
            "properties": {
                "field": {"type": "string", "const": "human_actors"},
                "row": {"type": "integer", "minimum": 1},
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["field", "row"],
            "properties": {
                "field": {"type": "string", "const": "external_systems"},
                "row": {"type": "integer", "minimum": 1},
            },
        },
    ]
}
CONSTRAINT_CUSTODY_SCHEMA = {
    "type": "array",
    "items": {
        "anyOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["constraint_index", "kind", "owner_fact"],
                "properties": {
                    "constraint_index": {"type": "integer", "minimum": 1},
                    "kind": {"type": "string", "const": "product_owned"},
                    "owner_fact": _PRODUCT_OWNER_SCHEMA,
                },
            },
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["constraint_index", "kind", "actor_fact"],
                "properties": {
                    "constraint_index": {"type": "integer", "minimum": 1},
                    "kind": {"type": "string", "const": "participant_only"},
                    "actor_fact": _PARTICIPANT_ACTOR_SCHEMA,
                },
            },
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["constraint_index", "kind"],
                "properties": {
                    "constraint_index": {"type": "integer", "minimum": 1},
                    "kind": {"type": "string", "const": "workflow_order"},
                },
            },
        ]
    },
}


def candidate_review_value(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Partition the canonical candidate without changing any value."""

    if set(candidate) != CANDIDATE_SOURCE_FIELDS | CANDIDATE_PROPOSED_FIELDS:
        raise ValueError("Greenfield candidate has unclassified or missing authority fields")
    return {
        "accepted_source": {
            key: deepcopy(candidate[key]) for key in sorted(CANDIDATE_SOURCE_FIELDS)
        },
        "proposed_decisions": {
            key: deepcopy(candidate[key]) for key in sorted(CANDIDATE_PROPOSED_FIELDS)
        },
    }


def candidate_review_sha256(candidate: Mapping[str, Any]) -> str:
    """Hash the exact partitioned candidate value used by review receipts."""

    return hashlib.sha256(
        encode_greenfield_model_value(candidate_review_value(candidate))
    ).hexdigest()


def constraint_custody_shape_issues(value: Any) -> tuple[str, ...]:
    """Validate the closed retained witness shape without candidate context."""

    if not isinstance(value, list):
        return ("constraint custody witness shape is invalid",)
    for expected_index, row in enumerate(value, start=1):
        if (
            not isinstance(row, Mapping)
            or type(row.get("constraint_index")) is not int
            or row.get("constraint_index") != expected_index
        ):
            return ("constraint custody witness order is invalid",)
        kind = row.get("kind")
        if kind == "product_owned":
            fact = row.get("owner_fact")
            fields = {"constraint_index", "kind", "owner_fact"}
            accepted = {"title", "internal_systems"}
        elif kind == "participant_only":
            fact = row.get("actor_fact")
            fields = {"constraint_index", "kind", "actor_fact"}
            accepted = {"human_actors", "external_systems"}
        elif kind == "workflow_order":
            if set(row) != {"constraint_index", "kind"}:
                return ("constraint custody witness shape is invalid",)
            continue
        else:
            return ("constraint custody witness shape is invalid",)
        if (
            set(row) != fields
            or not isinstance(fact, Mapping)
            or set(fact) != {"field", "row"}
            or fact.get("field") not in accepted
            or type(fact.get("row")) is not int
            or fact["row"] < 1
            or (fact.get("field") == "title" and fact["row"] != 1)
        ):
            return ("constraint custody witness shape is invalid",)
    return ()


def validated_constraint_custody(
    value: Any,
    *,
    candidate: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Bind every ordered custody row to accepted facts or source precedence."""

    if constraint_custody_shape_issues(value):
        raise RuntimeError("Greenfield candidate review returned invalid constraint custody")
    assert isinstance(value, list)
    facts = candidate.get("facts")
    constraints = facts.get("operational_constraints") if isinstance(facts, Mapping) else None
    if (
        not isinstance(constraints, Sequence)
        or isinstance(constraints, (str, bytes, bytearray))
        or len(value) != len(constraints)
    ):
        raise RuntimeError("Greenfield candidate review returned invalid constraint custody")
    precedence = candidate.get("source_precedence")
    for row in value:
        kind = row["kind"]
        constraint_index = row["constraint_index"]
        if kind == "product_owned":
            bound = _fact_quote(facts, row["owner_fact"], allowed={"title", "internal_systems"})
        elif kind == "participant_only":
            bound = _fact_quote(
                facts,
                row["actor_fact"],
                allowed={"human_actors", "external_systems"},
            )
        else:
            bound = _precedence_binds_constraint(precedence, constraint_index)
        if not bound:
            raise RuntimeError("Greenfield candidate review returned invalid constraint custody")
    return tuple(deepcopy(dict(row)) for row in value)


def project_constraint_custody(
    candidate: Mapping[str, Any],
    *,
    custody: Any,
) -> dict[str, Any]:
    """Project only reviewed product-owned constraints into canonical components."""

    rows = validated_constraint_custody(custody, candidate=candidate)
    projected = deepcopy(dict(candidate))
    facts = projected.get("facts")
    components = projected.get("components")
    if not isinstance(facts, Mapping) or not isinstance(components, list):
        raise RuntimeError("Greenfield candidate review cannot project constraint custody")
    constraints = facts.get("operational_constraints")
    assert isinstance(constraints, Sequence)
    components_by_owner: dict[str, dict[str, Any]] = {}
    for component in components:
        if not isinstance(component, dict):
            raise RuntimeError("Greenfield candidate review cannot project constraint custody")
        owner = str(component.get("owner_fact_quote") or "")
        responsibilities = component.get("responsibilities")
        if not owner or not isinstance(responsibilities, list) or owner in components_by_owner:
            raise RuntimeError("Greenfield candidate review cannot project constraint custody")
        components_by_owner[owner] = component
    constraint_values = [deepcopy(dict(row)) for row in constraints if isinstance(row, Mapping)]
    if len(constraint_values) != len(constraints):
        raise RuntimeError("Greenfield candidate review cannot project constraint custody")
    if any(
        constraint in component["responsibilities"]
        for constraint in constraint_values
        for component in components
    ):
        raise RuntimeError("Greenfield operational constraint was authored as a component responsibility")
    for row in rows:
        if row["kind"] != "product_owned":
            continue
        owner = _fact_quote(
            facts,
            row["owner_fact"],
            allowed={"title", "internal_systems"},
        )
        constraint = constraint_values[row["constraint_index"] - 1]
        component = components_by_owner.get(owner)
        if component is None:
            component = {"owner_fact_quote": owner, "responsibilities": []}
            components_by_owner[owner] = component
            components.append(component)
        if constraint in component["responsibilities"]:
            raise RuntimeError(
                "Greenfield constraint custody would duplicate a component responsibility"
            )
        component["responsibilities"].append(constraint)
    return projected


def finalize_admitted_review(
    receipt: Mapping[str, Any],
    *,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind an admitted review to the validated final projected candidate."""

    if receipt.get("status") != "admitted" or "candidate_sha256" in receipt:
        raise RuntimeError("Greenfield candidate review cannot seal its final candidate")
    finalized = deepcopy(dict(receipt))
    finalized["candidate_sha256"] = candidate_review_sha256(candidate)
    return finalized


def _fact_quote(
    facts: Mapping[str, Any],
    fact: Any,
    *,
    allowed: set[str],
) -> str:
    if not isinstance(fact, Mapping) or set(fact) != {"field", "row"}:
        return ""
    field = fact.get("field")
    row = fact.get("row")
    if field not in allowed or type(row) is not int or row < 1:
        return ""
    selected = facts.get(field)
    if field == "title":
        citation = selected if row == 1 and isinstance(selected, Mapping) else None
    else:
        citation = (
            selected[row - 1]
            if isinstance(selected, Sequence)
            and not isinstance(selected, (str, bytes, bytearray))
            and row <= len(selected)
            and isinstance(selected[row - 1], Mapping)
            else None
        )
    return str(citation.get("quote") or "") if isinstance(citation, Mapping) else ""


def _precedence_binds_constraint(value: Any, constraint_index: int) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ) and any(
        isinstance(row, Mapping) and row.get("constraint_index") == constraint_index
        for row in value
    )


__all__ = [
    "CANDIDATE_PROPOSED_FIELDS",
    "CANDIDATE_SOURCE_FIELDS",
    "CONSTRAINT_CUSTODY_SCHEMA",
    "candidate_review_sha256",
    "candidate_review_value",
    "constraint_custody_shape_issues",
    "finalize_admitted_review",
    "project_constraint_custody",
    "validated_constraint_custody",
]
