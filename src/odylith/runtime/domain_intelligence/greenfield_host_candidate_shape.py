"""Compact host candidate shape with one owner for each path event citation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    greenfield_authoring_schema,
)
from odylith.runtime.domain_intelligence.greenfield_model_source_citations import (
    canonical_citation_from_unique_context,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    MAX_AUTHORED_FIELD_VALUE_CHARS,
)

HOST_CANDIDATE_FORMAT_VERSION = "odylith.greenfield.host-candidate-format.v3"
HOST_EVENT_CITATION_FIELD = "source_citation"


def _context_citation_schema(*, description: str = "") -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["quote", "context"],
        "properties": {
            "quote": {
                "type": "string",
                "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS,
                "description": "The exact complete source text that carries the selected meaning.",
            },
            "context": {
                "type": "string",
                "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS,
                "description": (
                    "An exact contiguous source excerpt that occurs once and contains quote once. "
                    "It locates quote but contributes no additional meaning."
                ),
            },
        },
    }
    if description:
        schema["description"] = description
    return schema


def greenfield_host_candidate_schema() -> dict[str, Any]:
    """Return the host shape with contextual, event-owned source citations."""

    schema = greenfield_authoring_schema()
    schema["properties"]["version"]["enum"] = [HOST_CANDIDATE_FORMAT_VERSION]
    authored = schema["properties"]["result"]["anyOf"][0]
    facts = authored["properties"]["facts"]
    for field, fact_schema in tuple(facts["properties"].items()):
        description = str(fact_schema.get("description") or "")
        if fact_schema.get("type") == "array":
            replacement = deepcopy(fact_schema)
            replacement["items"] = _context_citation_schema()
        elif "anyOf" in fact_schema:
            replacement = deepcopy(fact_schema)
            replacement["anyOf"] = [
                _context_citation_schema(),
                {"type": "null"},
            ]
        else:
            replacement = _context_citation_schema(description=description)
        facts["properties"][field] = replacement
    facts["required"] = [
        field for field in facts["required"] if field != "first_path"
    ]
    facts["properties"].pop("first_path")
    event = authored["properties"]["events"]["items"]
    event["required"] = [*event["required"], HOST_EVENT_CITATION_FIELD]
    event["properties"][HOST_EVENT_CITATION_FIELD] = {
        **_context_citation_schema(),
        "description": (
            "The exact source citation for this event. Each event owns exactly one "
            "citation; do not return a separate facts.first_path list."
        ),
    }
    component = authored["properties"]["components"]["items"]
    responsibility = component["properties"]["responsibilities"]["items"]
    component["properties"]["responsibilities"]["items"] = _context_citation_schema(
        description=str(responsibility.get("description") or "")
    )
    return schema


def canonical_greenfield_host_candidate(
    response: Mapping[str, Any],
    *,
    evidence_text: str,
) -> dict[str, Any]:
    """Project unique host contexts into the unchanged canonical validator shape."""

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
    evidence = evidence_text.encode("utf-8")
    canonical_facts = {
        field: _canonical_fact_value(
            evidence,
            value,
            state_object=field == "state_object",
        )
        for field, value in facts.items()
    }
    canonical_events: list[dict[str, Any]] = []
    path_citations: list[Any] = []
    for raw_event in events:
        if not isinstance(raw_event, Mapping):
            raise TypeError("Greenfield host candidate event must be an object")
        event = deepcopy(dict(raw_event))
        if HOST_EVENT_CITATION_FIELD not in event:
            raise ValueError("Greenfield host candidate event has no source citation")
        path_citations.append(
            canonical_citation_from_unique_context(
                evidence,
                event.pop(HOST_EVENT_CITATION_FIELD),
            )
        )
        canonical_events.append(event)
    canonical_facts["first_path"] = path_citations
    canonical_components: list[dict[str, Any]] = []
    components = result.get("components")
    if not isinstance(components, Sequence) or isinstance(
        components, (str, bytes, bytearray)
    ):
        raise TypeError("Greenfield host candidate components must be an array")
    for raw_component in components:
        if not isinstance(raw_component, Mapping):
            raise TypeError("Greenfield host candidate component must be an object")
        component = deepcopy(dict(raw_component))
        responsibilities = component.get("responsibilities")
        if not isinstance(responsibilities, Sequence) or isinstance(
            responsibilities, (str, bytes, bytearray)
        ):
            raise TypeError("Greenfield host candidate responsibilities must be an array")
        component["responsibilities"] = [
            canonical_citation_from_unique_context(evidence, responsibility)
            for responsibility in responsibilities
        ]
        canonical_components.append(component)
    canonical_result = deepcopy(dict(result))
    canonical_result["facts"] = canonical_facts
    canonical_result["events"] = canonical_events
    canonical_result["components"] = canonical_components
    candidate["result"] = canonical_result
    return candidate


def _canonical_fact_value(
    evidence: bytes,
    value: Any,
    *,
    state_object: bool,
) -> Any:
    if value is None:
        return None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [
            canonical_citation_from_unique_context(evidence, citation)
            for citation in value
        ]
    return canonical_citation_from_unique_context(
        evidence,
        value,
        state_object=state_object,
    )


__all__ = [
    "HOST_CANDIDATE_FORMAT_VERSION",
    "HOST_EVENT_CITATION_FIELD",
    "canonical_greenfield_host_candidate",
    "greenfield_host_candidate_schema",
]
