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
from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import (
    greenfield_source_duty_binding_schema,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    verify_greenfield_source_duty_ledger_receipt,
)

HOST_CANDIDATE_FORMAT_VERSION = "odylith.greenfield.host-candidate-format.v21"
HOST_SOURCE_DUTY_BINDING_FIELD = "source_duty_binding"


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
    authored["required"].append(HOST_SOURCE_DUTY_BINDING_FIELD)
    authored["properties"][HOST_SOURCE_DUTY_BINDING_FIELD] = (
        greenfield_source_duty_binding_schema()
    )
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
        field for field in facts["required"] if field not in {"first_path", "supporting_events"}
    ]
    facts["properties"].pop("first_path")
    facts["properties"].pop("supporting_events")
    event = authored["properties"]["events"]["items"]
    event["required"] = ["actor_fact"]
    event["properties"] = {"actor_fact": event["properties"]["actor_fact"]}
    event["description"] = (
        "Select only the actor fact. The accepted source ledger owns each event citation, "
        "action quote, and target quote through source_duty_binding."
    )
    return schema


def canonical_greenfield_host_candidate(
    response: Mapping[str, Any],
    *,
    evidence_text: str,
    source_duty_receipt: Mapping[str, Any],
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
    if not isinstance(facts, Mapping) or {"first_path", "supporting_events"} & set(facts):
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
    ledger = verify_greenfield_source_duty_ledger_receipt(
        source_duty_receipt, evidence_text=evidence_text
    )["ledger"]
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
    supporting_citations: list[Any] = []
    binding = result[HOST_SOURCE_DUTY_BINDING_FIELD]
    first_path_orders = {
        row["event_order"] for row in binding["first_path_actions"]
    }
    duty_by_id = {
        row["id"]: row
        for section in ("first_path_actions", "supporting_human_actions", "system_duties")
        for row in ledger[section]
    }
    duty_by_order = {
        row["event_order"]: duty_by_id[row["duty_id"]]
        for section in ("first_path_actions", "supporting_human_actions", "system_duties")
        for row in binding[section]
    }
    if set(duty_by_order) != set(range(1, len(events) + 1)):
        raise ValueError("Greenfield host events must bind one source action atom each")
    event_fields = frozenset(
        authored_schema["properties"]["events"]["items"]["required"]
    )
    for event_order, raw_event in enumerate(events, start=1):
        if not isinstance(raw_event, Mapping) or set(raw_event) != event_fields:
            raise ValueError("Greenfield host candidate event has invalid fields")
        duty = duty_by_order[event_order]
        citation = canonical_citation_from_host_selection(
            evidence,
            duty["event_ref"],
        )
        event = {
            "actor_fact": deepcopy(raw_event["actor_fact"]),
            "action_quote": duty["action"],
            "target_quote": duty["target"],
        }
        if event_order in first_path_orders:
            path_citations.append(citation)
        else:
            supporting_citations.append(citation)
        canonical_events.append(event)
    canonical_facts["first_path"] = path_citations
    canonical_facts["supporting_events"] = supporting_citations
    canonical_result = deepcopy(dict(result))
    canonical_result.pop(HOST_SOURCE_DUTY_BINDING_FIELD)
    canonical_result["facts"] = canonical_facts
    canonical_result["events"] = canonical_events
    terminal = canonical_result.get("terminal")
    if isinstance(terminal, dict) and isinstance(terminal.get("result_fact"), dict):
        result_fact = terminal["result_fact"]
        if result_fact.get("field") == "first_path":
            source_row = result_fact.get("row")
            if type(source_row) is not int or source_row not in first_path_orders:
                raise ValueError("Greenfield terminal must cite a selected first-path fact")
            result_fact["row"] = sum(order <= source_row for order in first_path_orders)
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
    "HOST_SOURCE_DUTY_BINDING_FIELD",
    "canonical_greenfield_host_candidate",
    "greenfield_host_candidate_schema",
]
