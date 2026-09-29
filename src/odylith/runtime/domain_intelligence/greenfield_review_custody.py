"""Validate and project the independent reviewer's accepted-source custody."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_json import (
    encode_greenfield_model_value,
)
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelAuthoringError,
)
from odylith.runtime.domain_intelligence.greenfield_model_source_citations import (
    resolve_source_citation,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    MAX_AUTHORED_FIELD_VALUE_CHARS,
)

REVIEW_INPUT_SOURCE_FIELDS = frozenset(
    (
        "status",
        "facts",
        "events",
        "terminal",
        "source_precedence",
        "consistency",
        "ambiguities",
    )
)
FINAL_SOURCE_FIELDS = REVIEW_INPUT_SOURCE_FIELDS | {"components"}
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
_SOURCE_CITATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["quote", "occurrence"],
    "properties": {
        "quote": {
            "type": "string",
            "minLength": 1,
            "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS,
        },
        "occurrence": {"type": "integer", "minimum": 1},
    },
}
COMPONENT_CUSTODY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["event_responsibilities", "additional_responsibilities"],
    "properties": {
        "event_responsibilities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["event_order", "responsibility_citation"],
                "properties": {
                    "event_order": {"type": "integer", "minimum": 1},
                    "responsibility_citation": deepcopy(_SOURCE_CITATION_SCHEMA),
                },
            },
        },
        "additional_responsibilities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["owner_fact", "responsibility_citation"],
                "properties": {
                    "owner_fact": deepcopy(_PRODUCT_OWNER_SCHEMA),
                    "responsibility_citation": deepcopy(_SOURCE_CITATION_SCHEMA),
                },
            },
        },
    },
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
                    "owner_fact": deepcopy(_PRODUCT_OWNER_SCHEMA),
                },
            },
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["constraint_index", "kind", "actor_fact"],
                "properties": {
                    "constraint_index": {"type": "integer", "minimum": 1},
                    "kind": {"type": "string", "const": "participant_only"},
                    "actor_fact": deepcopy(_PARTICIPANT_ACTOR_SCHEMA),
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
    """Partition either the closed review input or final projected candidate."""

    fields = set(candidate)
    review_fields = REVIEW_INPUT_SOURCE_FIELDS | CANDIDATE_PROPOSED_FIELDS
    final_fields = FINAL_SOURCE_FIELDS | CANDIDATE_PROPOSED_FIELDS
    if fields == review_fields:
        source_fields = REVIEW_INPUT_SOURCE_FIELDS
    elif fields == final_fields:
        source_fields = FINAL_SOURCE_FIELDS
    else:
        raise ValueError("Greenfield candidate has unclassified or missing authority fields")
    return {
        "accepted_source": {
            key: deepcopy(candidate[key]) for key in sorted(source_fields)
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


def candidate_for_pre_review_validation(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Supply the canonical validator's final-only component field ephemerally."""

    if set(candidate) != REVIEW_INPUT_SOURCE_FIELDS | CANDIDATE_PROPOSED_FIELDS:
        raise ValueError("Greenfield review input candidate has an invalid shape")
    validation_candidate = deepcopy(dict(candidate))
    validation_candidate["components"] = []
    return validation_candidate


def component_custody_shape_issues(value: Any) -> tuple[str, ...]:
    """Validate the closed retained component-custody witness shape."""

    if not isinstance(value, Mapping) or set(value) != {
        "event_responsibilities",
        "additional_responsibilities",
    }:
        return ("component custody witness shape is invalid",)
    event_rows = value.get("event_responsibilities")
    additional_rows = value.get("additional_responsibilities")
    if not isinstance(event_rows, list) or not isinstance(additional_rows, list):
        return ("component custody witness shape is invalid",)
    for row in event_rows:
        if (
            not isinstance(row, Mapping)
            or set(row) != {"event_order", "responsibility_citation"}
            or type(row.get("event_order")) is not int
            or row["event_order"] < 1
            or not _valid_source_citation_shape(row.get("responsibility_citation"))
        ):
            return ("component custody event witness shape is invalid",)
    for row in additional_rows:
        if (
            not isinstance(row, Mapping)
            or set(row) != {"owner_fact", "responsibility_citation"}
            or not _valid_fact_selection(row.get("owner_fact"), allowed={"title", "internal_systems"})
            or not _valid_source_citation_shape(row.get("responsibility_citation"))
        ):
            return ("component custody additional witness shape is invalid",)
    return ()


def validated_component_custody(
    value: Any,
    *,
    candidate: Mapping[str, Any],
    evidence_text: str,
) -> dict[str, tuple[dict[str, Any], ...]]:
    """Bind every reviewer-selected component responsibility to exact source bytes."""

    if component_custody_shape_issues(value):
        raise RuntimeError("Greenfield candidate review returned invalid component custody")
    assert isinstance(value, Mapping)
    facts = candidate.get("facts")
    events = candidate.get("events")
    first_path = facts.get("first_path") if isinstance(facts, Mapping) else None
    constraints = facts.get("operational_constraints") if isinstance(facts, Mapping) else None
    if (
        not isinstance(facts, Mapping)
        or not isinstance(events, Sequence)
        or isinstance(events, (str, bytes, bytearray))
        or not isinstance(first_path, Sequence)
        or isinstance(first_path, (str, bytes, bytearray))
        or not isinstance(constraints, Sequence)
        or isinstance(constraints, (str, bytes, bytearray))
    ):
        raise RuntimeError("Greenfield candidate review returned invalid component custody")

    evidence = evidence_text.encode("utf-8")
    path_citations = _distinct_citation_ranges(evidence, first_path)
    if len(path_citations) != len(events):
        raise RuntimeError("Greenfield candidate review returned invalid component custody")

    expected_event_orders = [
        order
        for order, event in enumerate(events, start=1)
        if isinstance(event, Mapping)
        and _fact_quote(
            facts,
            event.get("actor_fact"),
            allowed={"title", "internal_systems"},
        )
    ]
    event_rows = value["event_responsibilities"]
    if [row["event_order"] for row in event_rows] != expected_event_orders:
        raise RuntimeError("Greenfield candidate review returned invalid component custody")

    constraint_ranges = tuple(
        _citation_range(evidence, constraint) for constraint in constraints
    )
    used_ranges: dict[tuple[int, int], str] = {}
    validated_events: list[dict[str, Any]] = []
    for row in event_rows:
        event_order = row["event_order"]
        event = events[event_order - 1]
        _, event_range = path_citations[event_order - 1]
        assert isinstance(event, Mapping)
        owner = _fact_quote(
            facts,
            event.get("actor_fact"),
            allowed={"title", "internal_systems"},
        )
        citation = deepcopy(dict(row["responsibility_citation"]))
        responsibility_range = _citation_range(evidence, citation)
        if not owner or not _range_contains(
            event_range, responsibility_range
        ):
            raise RuntimeError("Greenfield candidate review returned invalid component custody")
        _require_unique_non_constraint_range(
            responsibility_range,
            owner=owner,
            used_ranges=used_ranges,
            # One source clause may carry both a product event and an
            # operational constraint. Those typed meanings remain distinct.
            constraint_ranges=(),
        )
        validated_events.append(
            {
                "event_order": event_order,
                "owner_quote": owner,
                "responsibility_citation": citation,
            }
        )

    validated_additional: list[dict[str, Any]] = []
    prior_source_start = -1
    for row in value["additional_responsibilities"]:
        owner_fact = deepcopy(dict(row["owner_fact"]))
        owner = _fact_quote(
            facts,
            owner_fact,
            allowed={"title", "internal_systems"},
        )
        citation = deepcopy(dict(row["responsibility_citation"]))
        responsibility_range = _citation_range(evidence, citation)
        if not owner or responsibility_range[0] < prior_source_start:
            raise RuntimeError("Greenfield candidate review returned invalid component custody")
        prior_source_start = responsibility_range[0]
        _require_unique_non_constraint_range(
            responsibility_range,
            owner=owner,
            used_ranges=used_ranges,
            constraint_ranges=constraint_ranges,
        )
        validated_additional.append(
            {
                "owner_fact": owner_fact,
                "owner_quote": owner,
                "responsibility_citation": citation,
            }
        )
    return {
        "event_responsibilities": tuple(validated_events),
        "additional_responsibilities": tuple(validated_additional),
    }


def constraint_custody_shape_issues(value: Any) -> tuple[str, ...]:
    """Validate the closed retained constraint-custody witness shape."""

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
        if set(row) != fields or not _valid_fact_selection(fact, allowed=accepted):
            return ("constraint custody witness shape is invalid",)
    return ()


def validated_constraint_custody(
    value: Any,
    *,
    candidate: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Bind every ordered constraint row to accepted facts or source precedence."""

    if constraint_custody_shape_issues(value):
        raise RuntimeError("Greenfield candidate review returned invalid constraint custody")
    assert isinstance(value, list)
    facts = candidate.get("facts")
    constraints = facts.get("operational_constraints") if isinstance(facts, Mapping) else None
    if (
        not isinstance(facts, Mapping)
        or not isinstance(constraints, Sequence)
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


def project_reviewed_custody(
    candidate: Mapping[str, Any],
    *,
    component_custody: Any,
    constraint_custody: Any,
    evidence_text: str,
) -> dict[str, Any]:
    """Project reviewed components first and product-owned constraints second."""

    if set(candidate) != REVIEW_INPUT_SOURCE_FIELDS | CANDIDATE_PROPOSED_FIELDS:
        raise RuntimeError("Greenfield candidate review cannot project reviewed custody")
    component_rows = validated_component_custody(
        component_custody,
        candidate=candidate,
        evidence_text=evidence_text,
    )
    constraint_rows = validated_constraint_custody(
        constraint_custody,
        candidate=candidate,
    )
    projected = deepcopy(dict(candidate))
    facts = projected.get("facts")
    assert isinstance(facts, Mapping)
    components: list[dict[str, Any]] = []
    components_by_owner: dict[str, dict[str, Any]] = {}

    for collection in (
        component_rows["event_responsibilities"],
        component_rows["additional_responsibilities"],
    ):
        for row in collection:
            owner = row["owner_quote"]
            component = components_by_owner.get(owner)
            if component is None:
                component = {"owner_fact_quote": owner, "responsibilities": []}
                components_by_owner[owner] = component
                components.append(component)
            component["responsibilities"].append(
                deepcopy(row["responsibility_citation"])
            )

    constraints = facts.get("operational_constraints")
    assert isinstance(constraints, Sequence)
    for row in constraint_rows:
        if row["kind"] != "product_owned":
            continue
        owner = _fact_quote(
            facts,
            row["owner_fact"],
            allowed={"title", "internal_systems"},
        )
        component = components_by_owner.get(owner)
        if component is None:
            component = {"owner_fact_quote": owner, "responsibilities": []}
            components_by_owner[owner] = component
            components.append(component)
        constraint = deepcopy(dict(constraints[row["constraint_index"] - 1]))
        if constraint in component["responsibilities"]:
            # The exact dual-role clause already has its component relation;
            # constraint custody remains independently sealed in the witness.
            continue
        if any(
            constraint in other["responsibilities"]
            for other_owner, other in components_by_owner.items()
            if other_owner != owner
        ):
            raise RuntimeError(
                "Greenfield constraint custody conflicts with component ownership"
            )
        component["responsibilities"].append(constraint)

    projected["components"] = components
    return projected


def finalize_admitted_review(
    receipt: Mapping[str, Any],
    *,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind an admitted review to the validated final projected candidate."""

    if receipt.get("status") != "admitted" or "candidate_sha256" in receipt:
        raise RuntimeError("Greenfield candidate review cannot seal its final candidate")
    if set(candidate) != FINAL_SOURCE_FIELDS | CANDIDATE_PROPOSED_FIELDS:
        raise RuntimeError("Greenfield candidate review cannot seal a non-final candidate")
    finalized = deepcopy(dict(receipt))
    finalized["candidate_sha256"] = candidate_review_sha256(candidate)
    return finalized


def _valid_source_citation_shape(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == {"quote", "occurrence"}
        and isinstance(value.get("quote"), str)
        and bool(value["quote"])
        and len(value["quote"]) <= MAX_AUTHORED_FIELD_VALUE_CHARS
        and type(value.get("occurrence")) is int
        and value["occurrence"] >= 1
    )


def _valid_fact_selection(value: Any, *, allowed: set[str]) -> bool:
    if (
        not isinstance(value, Mapping)
        or set(value) != {"field", "row"}
        or value.get("field") not in allowed
        or type(value.get("row")) is not int
        or value["row"] < 1
    ):
        return False
    return value.get("field") != "title" or value["row"] == 1


def _fact_quote(
    facts: Mapping[str, Any],
    fact: Any,
    *,
    allowed: set[str],
) -> str:
    if not _valid_fact_selection(fact, allowed=allowed):
        return ""
    field = fact["field"]
    row = fact["row"]
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


def _citation_range(
    evidence: bytes,
    citation: Any,
) -> tuple[int, int]:
    if not isinstance(citation, Mapping):
        raise RuntimeError("Greenfield candidate review returned invalid component custody")
    try:
        quote, start = resolve_source_citation(evidence, citation)
    except (GreenfieldModelAuthoringError, TypeError, ValueError) as exc:
        raise RuntimeError(
            "Greenfield candidate review returned invalid component custody"
        ) from exc
    quote_bytes = quote.encode("utf-8")
    occurrence = citation.get("occurrence")
    matches: list[int] = []
    cursor = 0
    while (found := evidence.find(quote_bytes, cursor)) >= 0:
        matches.append(found)
        cursor = found + 1
    if (
        type(occurrence) is not int
        or occurrence > len(matches)
        or matches[occurrence - 1] != start
    ):
        raise RuntimeError("Greenfield candidate review returned invalid component custody")
    return start, start + len(quote.encode("utf-8"))


def _distinct_citation_ranges(
    evidence: bytes,
    citations: Sequence[Any],
) -> tuple[tuple[dict[str, Any], tuple[int, int]], ...]:
    """Collapse only byte-identical repeated selections, preserving source order."""

    distinct: list[tuple[dict[str, Any], tuple[int, int]]] = []
    seen: set[tuple[int, int]] = set()
    for citation in citations:
        if not isinstance(citation, Mapping):
            raise RuntimeError("Greenfield candidate review returned invalid component custody")
        citation_range = _accepted_citation_range(evidence, citation)
        if citation_range in seen:
            continue
        seen.add(citation_range)
        distinct.append((deepcopy(dict(citation)), citation_range))
    return tuple(distinct)


def _accepted_citation_range(
    evidence: bytes,
    citation: Mapping[str, Any],
) -> tuple[int, int]:
    """Resolve an author citation under the canonical validator's unique-match law."""

    try:
        quote, start = resolve_source_citation(evidence, citation)
    except (GreenfieldModelAuthoringError, TypeError, ValueError) as exc:
        raise RuntimeError(
            "Greenfield candidate review returned invalid component custody"
        ) from exc
    return start, start + len(quote.encode("utf-8"))


def _range_contains(outer: tuple[int, int], inner: tuple[int, int]) -> bool:
    return outer[0] <= inner[0] and inner[1] <= outer[1]


def _ranges_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def _require_unique_non_constraint_range(
    responsibility_range: tuple[int, int],
    *,
    owner: str,
    used_ranges: dict[tuple[int, int], str],
    constraint_ranges: Sequence[tuple[int, int]],
) -> None:
    if responsibility_range in used_ranges or any(
        _ranges_overlap(responsibility_range, constraint_range)
        for constraint_range in constraint_ranges
    ):
        raise RuntimeError("Greenfield candidate review returned invalid component custody")
    used_ranges[responsibility_range] = owner


def _precedence_binds_constraint(value: Any, constraint_index: int) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ) and any(
        isinstance(row, Mapping) and row.get("constraint_index") == constraint_index
        for row in value
    )


__all__ = [
    "CANDIDATE_PROPOSED_FIELDS",
    "COMPONENT_CUSTODY_SCHEMA",
    "CONSTRAINT_CUSTODY_SCHEMA",
    "FINAL_SOURCE_FIELDS",
    "REVIEW_INPUT_SOURCE_FIELDS",
    "candidate_for_pre_review_validation",
    "candidate_review_sha256",
    "candidate_review_value",
    "component_custody_shape_issues",
    "constraint_custody_shape_issues",
    "finalize_admitted_review",
    "project_reviewed_custody",
    "validated_component_custody",
    "validated_constraint_custody",
]
