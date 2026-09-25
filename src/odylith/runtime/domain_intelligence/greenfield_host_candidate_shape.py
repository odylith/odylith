"""Compact host candidate shape with one owner for each path event citation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    greenfield_authoring_schema,
)

HOST_CANDIDATE_FORMAT_VERSION = "odylith.greenfield.host-candidate-format.v4"
HOST_EVENT_CITATION_FIELD = "source_citation"
HOST_CONSTRAINT_NOT_ORDERING = "not_event_ordering"
HOST_CONSTRAINT_ORDERING = "event_ordering"


def greenfield_host_candidate_schema() -> dict[str, Any]:
    """Return the host shape without duplicate first-path citation ownership."""

    schema = greenfield_authoring_schema()
    schema["properties"]["version"]["enum"] = [HOST_CANDIDATE_FORMAT_VERSION]
    authored = schema["properties"]["result"]["anyOf"][0]
    facts = authored["properties"]["facts"]
    facts["required"] = [
        field for field in facts["required"] if field != "first_path"
    ]
    citation_schema = facts["properties"].pop("first_path")["items"]
    event = authored["properties"]["events"]["items"]
    event["required"] = [*event["required"], HOST_EVENT_CITATION_FIELD]
    event["properties"][HOST_EVENT_CITATION_FIELD] = {
        **citation_schema,
        "description": (
            "The exact source citation for this event. Each event owns exactly one "
            "citation; do not return a separate facts.first_path list."
        ),
    }
    authored["required"] = [
        field for field in authored["required"] if field != "source_precedence"
    ]
    precedence_schema = authored["properties"].pop("source_precedence")
    constraint_citations = facts["properties"]["operational_constraints"]
    citation = constraint_citations["items"]
    edge = precedence_schema["items"]
    facts["properties"]["operational_constraints"] = {
        "type": "array",
        "maxItems": constraint_citations["maxItems"],
        "description": (
            "Every accepted operational constraint owns its exact citation and "
            "its event-ordering meaning. Classify the constraint itself; do not "
            "return a separate source_precedence list."
        ),
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["source_citation", "ordering"],
            "properties": {
                "source_citation": citation,
                "ordering": {
                    "anyOf": [
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["status"],
                            "properties": {
                                "status": {
                                    "type": "string",
                                    "enum": [HOST_CONSTRAINT_NOT_ORDERING],
                                }
                            },
                        },
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["status", "edges"],
                            "properties": {
                                "status": {
                                    "type": "string",
                                    "enum": [HOST_CONSTRAINT_ORDERING],
                                },
                                "edges": {
                                    "type": "array",
                                    "minItems": 1,
                                    "maxItems": precedence_schema["maxItems"],
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "required": ["before_event", "after_event"],
                                        "properties": {
                                            "before_event": edge["properties"][
                                                "before_event"
                                            ],
                                            "after_event": edge["properties"][
                                                "after_event"
                                            ],
                                        },
                                    },
                                },
                            },
                        },
                    ]
                },
            },
        },
    }
    return schema


def canonical_greenfield_host_candidate(
    response: Mapping[str, Any],
) -> dict[str, Any]:
    """Project the compact host shape into the unchanged canonical validator shape."""

    candidate = deepcopy(dict(response))
    if candidate.get("version") != HOST_CANDIDATE_FORMAT_VERSION:
        raise ValueError("Greenfield host candidate format version is invalid")
    result = candidate.get("result")
    if not isinstance(result, Mapping):
        raise TypeError("Greenfield host candidate result must be an object")
    candidate["version"] = GREENFIELD_INTENT_AUTHORING_VERSION
    if result.get("status") == "clarification_required":
        return candidate
    if "source_precedence" in result:
        raise ValueError(
            "Greenfield host candidate must not duplicate constraint ordering authority"
        )
    facts = result.get("facts")
    events = result.get("events")
    if not isinstance(facts, Mapping) or "first_path" in facts:
        raise ValueError(
            "Greenfield host candidate must not duplicate first-path citation authority"
        )
    if (
        not isinstance(events, Sequence)
        or isinstance(events, (str, bytes, bytearray))
        or not events
    ):
        raise TypeError("Greenfield host candidate events must be a non-empty array")
    canonical_events: list[dict[str, Any]] = []
    path_citations: list[Any] = []
    for raw_event in events:
        if not isinstance(raw_event, Mapping):
            raise TypeError("Greenfield host candidate event must be an object")
        event = deepcopy(dict(raw_event))
        if HOST_EVENT_CITATION_FIELD not in event:
            raise ValueError("Greenfield host candidate event has no source citation")
        path_citations.append(event.pop(HOST_EVENT_CITATION_FIELD))
        canonical_events.append(event)
    raw_constraints = facts.get("operational_constraints")
    if (
        not isinstance(raw_constraints, Sequence)
        or isinstance(raw_constraints, (str, bytes, bytearray))
    ):
        raise TypeError("Greenfield host candidate constraints must be an array")
    canonical_constraints: list[Any] = []
    canonical_precedence: list[dict[str, int]] = []
    for constraint_index, raw_constraint in enumerate(raw_constraints, 1):
        if not isinstance(raw_constraint, Mapping) or set(raw_constraint) != {
            "source_citation",
            "ordering",
        }:
            raise ValueError("Greenfield host candidate constraint is invalid")
        canonical_constraints.append(deepcopy(raw_constraint["source_citation"]))
        ordering = raw_constraint["ordering"]
        if not isinstance(ordering, Mapping):
            raise TypeError("Greenfield host constraint ordering must be an object")
        status = ordering.get("status")
        if status == HOST_CONSTRAINT_NOT_ORDERING and set(ordering) == {"status"}:
            continue
        if status != HOST_CONSTRAINT_ORDERING or set(ordering) != {"status", "edges"}:
            raise ValueError("Greenfield host constraint ordering is invalid")
        edges = ordering.get("edges")
        if (
            not isinstance(edges, Sequence)
            or isinstance(edges, (str, bytes, bytearray))
            or not edges
        ):
            raise ValueError("Greenfield event-ordering constraint requires edges")
        for raw_edge in edges:
            if not isinstance(raw_edge, Mapping) or set(raw_edge) != {
                "before_event",
                "after_event",
            }:
                raise ValueError("Greenfield host constraint edge is invalid")
            canonical_precedence.append(
                {
                    "before_event": raw_edge["before_event"],
                    "after_event": raw_edge["after_event"],
                    "constraint_index": constraint_index,
                }
            )
    canonical_facts = deepcopy(dict(facts))
    canonical_facts["first_path"] = path_citations
    canonical_facts["operational_constraints"] = canonical_constraints
    canonical_result = deepcopy(dict(result))
    canonical_result["facts"] = canonical_facts
    canonical_result["events"] = canonical_events
    canonical_result["source_precedence"] = canonical_precedence
    candidate["result"] = canonical_result
    return candidate


__all__ = [
    "HOST_CANDIDATE_FORMAT_VERSION",
    "HOST_CONSTRAINT_NOT_ORDERING",
    "HOST_CONSTRAINT_ORDERING",
    "HOST_EVENT_CITATION_FIELD",
    "canonical_greenfield_host_candidate",
    "greenfield_host_candidate_schema",
]
