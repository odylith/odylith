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
    canonical_citation_from_host_selection,
    resolve_source_citation,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    MAX_AUTHORED_FIELD_VALUE_CHARS,
)

HOST_CANDIDATE_FORMAT_VERSION = "odylith.greenfield.host-candidate-format.v8"
HOST_EVENT_CITATION_FIELD = "source_citation"
HOST_EVENT_RESPONSIBILITY_FIELD = "responsibility_citation"


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
    event["required"] = [
        *event["required"],
        HOST_EVENT_CITATION_FIELD,
        HOST_EVENT_RESPONSIBILITY_FIELD,
    ]
    event["properties"][HOST_EVENT_CITATION_FIELD] = {
        **_context_citation_schema(),
        "description": (
            "The exact source citation for this event. Each event owns exactly one "
            "citation; do not return a separate facts.first_path list."
        ),
    }
    event["properties"][HOST_EVENT_RESPONSIBILITY_FIELD] = {
        "anyOf": [
            _context_citation_schema(),
            {"type": "null"},
        ],
        "description": (
            "For a title- or internal-system-owned event, select the exact contiguous "
            "subspan of source_citation that states only that product responsibility at "
            "the same source location. It may equal source_citation when that citation "
            "contains only this product action. When source_citation contains another "
            "actor or owner, select only this product's clause. Use null for every human "
            "or external event."
        ),
    }
    component = authored["properties"]["components"]["items"]
    responsibility = component["properties"].pop("responsibilities")
    component["required"] = [
        "additional_responsibilities" if field == "responsibilities" else field
        for field in component["required"]
    ]
    component["properties"]["additional_responsibilities"] = {
        **deepcopy(responsibility),
        "minItems": 0,
        "items": _context_citation_schema(),
        "description": (
            "Every exact source-stated responsibility citation for this owner except a "
            "citation identical to one of its typed product-event responsibility citations. Related "
            "wording, a shared target, or the same owner does not make two citations "
            "identical. Product events become accepted component responsibilities "
            "during canonical projection; do not repeat only those exact citations here."
        ),
    }
    authored["properties"]["components"]["description"] = (
        "Additional source-stated product or component responsibilities, grouped by "
        "their selected product owner. Typed product events establish their own "
        "exact accepted component responsibility automatically. Preserve separately "
        "worded source responsibilities even when their meaning overlaps an event. "
        "Return [] only when the source states no additional non-event responsibility."
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
    event_responsibilities: list[tuple[str, dict[str, Any]]] = []
    source_citation_owners: dict[tuple[tuple[str, Any], ...], set[str]] = {}
    authored_schema = greenfield_host_candidate_schema()["properties"]["result"][
        "anyOf"
    ][0]
    event_fields = frozenset(
        authored_schema["properties"]["events"]["items"]["required"]
    )
    component_fields = frozenset(
        authored_schema["properties"]["components"]["items"]["required"]
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
        owner_quote = _product_event_owner_quote(facts, event.get("actor_fact"))
        source_citation_owners.setdefault(
            tuple(sorted(citation.items())), set()
        ).add(_event_owner_identity(facts, event.get("actor_fact")))
        responsibility = event.pop(HOST_EVENT_RESPONSIBILITY_FIELD)
        if owner_quote:
            if not isinstance(responsibility, Mapping):
                raise ValueError(
                    "Greenfield product event requires one responsibility citation"
                )
            canonical_responsibility = canonical_citation_from_host_selection(
                evidence, responsibility
            )
            if not _citation_contains(
                evidence,
                outer=citation,
                inner=canonical_responsibility,
            ):
                raise ValueError(
                    "Greenfield event responsibility must be inside its source citation"
                )
            event_responsibilities.append((owner_quote, canonical_responsibility))
        elif responsibility is not None:
            raise ValueError(
                "Greenfield non-product event cannot own a component responsibility"
            )
        canonical_events.append(event)
    if any(len(owners) > 1 for owners in source_citation_owners.values()):
        raise ValueError(
            "Greenfield shared event citation has mixed or contradictory actor ownership"
        )
    canonical_facts["first_path"] = path_citations
    canonical_components: list[dict[str, Any]] = []
    components_by_owner: dict[str, dict[str, Any]] = {}
    components = result.get("components")
    if not isinstance(components, Sequence) or isinstance(
        components, (str, bytes, bytearray)
    ):
        raise TypeError("Greenfield host candidate components must be an array")
    for raw_component in components:
        if not isinstance(raw_component, Mapping) or set(raw_component) != component_fields:
            raise ValueError("Greenfield host candidate component has invalid fields")
        component = deepcopy(dict(raw_component))
        owner_quote = str(component.get("owner_fact_quote") or "")
        responsibilities = component.pop("additional_responsibilities", None)
        if not isinstance(responsibilities, Sequence) or isinstance(
            responsibilities, (str, bytes, bytearray)
        ):
            raise TypeError(
                "Greenfield host candidate additional responsibilities must be an array"
            )
        component["responsibilities"] = [
            canonical_citation_from_host_selection(evidence, responsibility)
            for responsibility in responsibilities
        ]
        canonical_components.append(component)
        components_by_owner[owner_quote] = component
    for owner_quote, citation in event_responsibilities:
        if any(
            other_owner != owner_quote and citation in other_component["responsibilities"]
            for other_owner, other_component in components_by_owner.items()
        ):
            raise ValueError(
                "Greenfield responsibility citation has contradictory product owners"
            )
        component = components_by_owner.get(owner_quote)
        if component is None:
            component = {
                "owner_fact_quote": owner_quote,
                "responsibilities": [],
            }
            components_by_owner[owner_quote] = component
            canonical_components.append(component)
        if citation not in component["responsibilities"]:
            component["responsibilities"].append(deepcopy(citation))
    canonical_result = deepcopy(dict(result))
    canonical_result["facts"] = canonical_facts
    canonical_result["events"] = canonical_events
    canonical_result["components"] = canonical_components
    candidate["result"] = canonical_result
    return candidate


def _product_event_owner_quote(
    facts: Mapping[str, Any],
    actor_fact: Any,
) -> str:
    """Return the selected product owner for an event, never a human actor."""

    if not isinstance(actor_fact, Mapping):
        return ""
    field = str(actor_fact.get("field") or "")
    row = actor_fact.get("row")
    if field == "title":
        citation = facts.get("title")
    elif field == "internal_systems" and isinstance(row, int) and not isinstance(row, bool):
        systems = facts.get("internal_systems")
        citation = (
            systems[row - 1]
            if isinstance(systems, Sequence)
            and not isinstance(systems, (str, bytes, bytearray))
            and 1 <= row <= len(systems)
            else None
        )
    else:
        return ""
    return str(citation.get("quote") or "") if isinstance(citation, Mapping) else ""


def _event_owner_identity(
    facts: Mapping[str, Any],
    actor_fact: Any,
) -> str:
    """Return one typed actor identity for shared-citation ownership checks."""

    product_owner = _product_event_owner_quote(facts, actor_fact)
    if product_owner:
        return f"product:{product_owner}"
    if not isinstance(actor_fact, Mapping):
        return "invalid:<missing>"
    field = str(actor_fact.get("field") or "")
    row = actor_fact.get("row")
    values = facts.get(field)
    citation = (
        values[row - 1]
        if field in {"human_actors", "external_systems"}
        and isinstance(row, int)
        and not isinstance(row, bool)
        and isinstance(values, Sequence)
        and not isinstance(values, (str, bytes, bytearray))
        and 1 <= row <= len(values)
        else None
    )
    quote = str(citation.get("quote") or "") if isinstance(citation, Mapping) else ""
    return f"{field}:{quote or row}"


def _citation_contains(
    evidence: bytes,
    *,
    outer: Mapping[str, Any],
    inner: Mapping[str, Any],
) -> bool:
    """Return whether one canonical citation is a source-local subspan of another."""

    outer_quote, outer_start = resolve_source_citation(evidence, outer)
    inner_quote, inner_start = resolve_source_citation(evidence, inner)
    return (
        outer_start <= inner_start
        and inner_start + len(inner_quote.encode("utf-8"))
        <= outer_start + len(outer_quote.encode("utf-8"))
    )


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
    "HOST_EVENT_RESPONSIBILITY_FIELD",
    "canonical_greenfield_host_candidate",
    "greenfield_host_candidate_schema",
]
