"""Complete one-pass host hypothesis shape for deterministic admission."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    greenfield_authoring_schema,
)
from odylith.runtime.domain_intelligence.greenfield_model_source_citations import (
    canonical_citation_from_host_selection,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    MAX_AUTHORED_FIELD_VALUE_CHARS,
)

HOST_CANDIDATE_FORMAT_VERSION = "odylith.greenfield.host-candidate-format.v18"
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
                    "Always supply locator context. When quote occurs more than once, context "
                    "must be an exact contiguous source excerpt that occurs once and contains "
                    "the selected quote once. When quote occurs once, repeat quote as context. "
                    "Context locates quote but contributes no additional meaning."
                ),
            },
        },
    }
    if description:
        schema["description"] = description
    return schema


def greenfield_host_candidate_schema() -> dict[str, Any]:
    """Return the complete host shape with contextual fact and event citations."""

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
    facts["properties"]["operational_constraints"]["items"] = (
        _context_citation_schema()
    )
    facts["properties"]["operational_constraints"]["description"] = (
        "Every exact source-stated operational, safety, ordering, or actor restriction. "
        "Keep each constraint global and preserve exact dual-role custody when the same "
        "source bytes also carry one component responsibility."
    )
    facts["required"] = [
        field for field in facts["required"] if field != "first_path"
    ]
    facts["properties"].pop("first_path")
    event = authored["properties"]["events"]["items"]
    event["required"] = [
        *event["required"],
        HOST_EVENT_CITATION_FIELD,
    ]
    event["properties"][HOST_EVENT_CITATION_FIELD] = {
        **_context_citation_schema(),
        "description": (
            "The exact source citation for this event. Each event owns exactly one "
            "citation; do not return a separate facts.first_path list."
        ),
    }
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
    authored_schema = greenfield_host_candidate_schema()["properties"]["result"][
        "anyOf"
    ][0]
    if set(result) != set(authored_schema["required"]):
        raise ValueError("Greenfield host candidate result has an invalid shape")
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
        if field != "operational_constraints"
    }
    raw_constraints = facts.get("operational_constraints")
    if not isinstance(raw_constraints, Sequence) or isinstance(
        raw_constraints, (str, bytes, bytearray)
    ):
        raise TypeError("Greenfield host candidate operational constraints must be an array")
    canonical_constraints: list[dict[str, Any]] = []
    constraint_fields = {"quote", "context"}
    for raw_constraint in raw_constraints:
        if not isinstance(raw_constraint, Mapping) or set(raw_constraint) != constraint_fields:
            raise ValueError("Greenfield host candidate operational constraint has invalid fields")
        canonical_constraints.append(
            canonical_citation_from_host_selection(evidence, raw_constraint)
        )
    canonical_facts["operational_constraints"] = canonical_constraints
    canonical_events: list[dict[str, Any]] = []
    path_citations: list[Any] = []
    seen_source_citations: set[tuple[tuple[str, Any], ...]] = set()
    event_fields = frozenset(
        authored_schema["properties"]["events"]["items"]["required"]
    )
    for raw_event in events:
        if not isinstance(raw_event, Mapping) or set(raw_event) != event_fields:
            raise ValueError("Greenfield host candidate event has invalid fields")
        event = deepcopy(dict(raw_event))
        if HOST_EVENT_CITATION_FIELD not in event:
            raise ValueError("Greenfield host candidate event has no source citation")
        citation = canonical_citation_from_host_selection(
            evidence,
            event.pop(HOST_EVENT_CITATION_FIELD),
        )
        path_citations.append(citation)
        citation_identity = tuple(sorted(citation.items()))
        if citation_identity in seen_source_citations:
            raise ValueError(
                "Greenfield events must use distinct non-overlapping source citations"
            )
        seen_source_citations.add(citation_identity)
        canonical_events.append(event)
    canonical_facts["first_path"] = path_citations
    canonical_result = deepcopy(dict(result))
    canonical_result["facts"] = canonical_facts
    canonical_result["events"] = canonical_events
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
            canonical_citation_from_host_selection(evidence, citation)
            for citation in value
        ]
    return canonical_citation_from_host_selection(
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
