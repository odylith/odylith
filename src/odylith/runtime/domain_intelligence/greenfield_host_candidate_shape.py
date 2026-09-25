"""Compact host candidate shape with one owner for each path event citation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    greenfield_authoring_schema,
)

HOST_CANDIDATE_FORMAT_VERSION = "odylith.greenfield.host-candidate-format.v2"
HOST_EVENT_CITATION_FIELD = "source_citation"


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
    canonical_facts = deepcopy(dict(facts))
    canonical_facts["first_path"] = path_citations
    canonical_result = deepcopy(dict(result))
    canonical_result["facts"] = canonical_facts
    canonical_result["events"] = canonical_events
    candidate["result"] = canonical_result
    return candidate


__all__ = [
    "HOST_CANDIDATE_FORMAT_VERSION",
    "HOST_EVENT_CITATION_FIELD",
    "canonical_greenfield_host_candidate",
    "greenfield_host_candidate_schema",
]
