"""Shared structured-provider fixtures for Greenfield model-authoring tests."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_intent_fact_values import (
    TERMINAL_RESULT_FACT_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    _REPEATED_SOURCE_FIELDS,
    _SINGULAR_SOURCE_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import (
    HOST_CANDIDATE_FORMAT_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_source_citations import (
    resolve_source_citation,
)


class StructuredAuthoringProvider:
    """Return a fixed model response without manufacturing custody coordinates."""

    provider_name = "codex-cli"

    def __init__(self, response: Mapping[str, Any] | None) -> None:
        self.response = response
        self.calls = 0
        self.requests: list[object] = []

    def generate_structured(self, *, request: object) -> Mapping[str, Any] | None:
        self.last_request_system_prompt = str(getattr(request, "system_prompt", ""))
        self.last_request_output_schema = copy.deepcopy(
            getattr(request, "output_schema", {})
        )
        self.last_request_model = str(getattr(request, "model", ""))
        self.last_request_reasoning_effort = str(getattr(request, "reasoning_effort", ""))
        self.requests.append(request)
        self.calls += 1
        return copy.deepcopy(dict(self.response)) if self.response is not None else None

    def participant_provider(self) -> ParticipantSelectionProvider:
        """Return a separate selector for participants explicitly declared by this fixture."""

        return ParticipantSelectionProvider(self.response)


class RemainingCandidateProvider(StructuredAuthoringProvider):
    """Project a complete canonical fixture onto the remaining-author response schema."""

    def review_provider(self) -> AdmittingReviewProvider:
        """Return a reviewer double bound to this fixture's declared canonical truth."""

        result = self.response.get("result") if isinstance(self.response, Mapping) else None
        source_precedence = (
            result.get("source_precedence") if isinstance(result, Mapping) else ()
        )
        return AdmittingReviewProvider(
            component_custody=component_custody_for_response(self.response),
            source_precedence_custody=(
                source_precedence if isinstance(source_precedence, list) else ()
            ),
        )

    def generate_structured(self, *, request: object) -> Mapping[str, Any] | None:
        assert getattr(request, "schema_name", "") == "greenfield_remaining_candidate_authoring"
        response = super().generate_structured(request=request)
        if isinstance(response, dict):
            result = response.get("result")
            if isinstance(result, dict) and isinstance(result.get("facts"), dict):
                result["facts"].pop("human_actors", None)
                result.pop("components", None)
                result.pop("source_precedence", None)
        return response


class ParticipantSelectionProvider(StructuredAuthoringProvider):
    """Convert declared fixture citations, never discover roles from the source prose."""

    def __init__(self, candidate: Mapping[str, Any] | None = None) -> None:
        result = candidate.get("result") if isinstance(candidate, Mapping) else None
        facts = result.get("facts") if isinstance(result, Mapping) else None
        citations = facts.get("human_actors", []) if isinstance(facts, Mapping) else []
        if isinstance(citations, list):
            selectors = [
                {
                    "quote": citation["quote"],
                    "prefix": "",
                    "anchor_occurrence": citation["occurrence"],
                }
                if isinstance(citation, Mapping) and set(citation) == {"quote", "occurrence"}
                else copy.deepcopy(citation)
                for citation in citations
            ]
        else:
            selectors = copy.deepcopy(citations)
        super().__init__({"human_actors": selectors})

    def generate_structured(self, *, request: object) -> Mapping[str, Any] | None:
        assert getattr(request, "schema_name", "") == "greenfield_participant_selection"
        return super().generate_structured(request=request)


class AdmittingReviewProvider(StructuredAuthoringProvider):
    """Independent transport double for structurally valid positive wiring cases."""

    def __init__(
        self,
        *,
        component_custody: Mapping[str, Any] | None = None,
        source_precedence_custody: Sequence[Mapping[str, Any]] | None = None,
        constraint_custody: Sequence[Mapping[str, Any]] | None = None,
    ) -> None:
        self.configured_component_custody = copy.deepcopy(component_custody)
        self.configured_source_precedence_custody = copy.deepcopy(
            list(source_precedence_custody or ())
        )
        configured_custody = (
            constraint_custody
            if constraint_custody is not None
            else (
                {
                    "constraint_index": 1,
                    "kind": "participant_only",
                    "actor_fact": {"field": "human_actors", "row": 1},
                },
            )
        )
        super().__init__(
            admitted_review_response(
                component_custody=(
                    component_custody
                    if component_custody is not None
                    else {
                        "event_responsibilities": [],
                        "additional_responsibilities": [],
                    }
                ),
                source_precedence_custody=self.configured_source_precedence_custody,
                constraint_custody=configured_custody,
            )
        )

    def generate_structured(self, *, request: object) -> Mapping[str, Any] | None:
        assert getattr(request, "schema_name", "") == "greenfield_candidate_review"
        assert getattr(request, "model", "") == "gpt-6-astra"
        assert getattr(request, "reasoning_effort", "") == "medium"
        if isinstance(self.response, Mapping) and self.response.get("outcome") == "admitted":
            payload = getattr(request, "prompt_payload", {})
            candidate = payload.get("candidate") if isinstance(payload, Mapping) else None
            facts = candidate.get("accepted_source", {}).get("facts") if isinstance(candidate, Mapping) else None
            terminal = candidate.get("accepted_source", {}).get("terminal") if isinstance(candidate, Mapping) else None
            events = candidate.get("accepted_source", {}).get("events") if isinstance(candidate, Mapping) else None
            design = candidate.get("proposed_decisions", {}).get("provisional_design") if isinstance(candidate, Mapping) else None
            participant_field = "human_actors"
            participant_row = 1
            if isinstance(facts, Mapping):
                if isinstance(facts.get("customer"), Mapping):
                    participant_field = "customer"
                elif not facts.get("human_actors") and facts.get("external_systems"):
                    participant_field = "external_systems"
                elif not facts.get("human_actors"):
                    first_event = events[0] if isinstance(events, list) and events else None
                    actor_fact = (
                        first_event.get("actor_fact")
                        if isinstance(first_event, Mapping)
                        else None
                    )
                    if (
                        isinstance(actor_fact, Mapping)
                        and actor_fact.get("field") in {"title", "internal_systems"}
                    ):
                        participant_field = str(actor_fact["field"])
                        participant_row = int(actor_fact.get("row") or 1)
            result_event_order = (
                terminal.get("event_order") if isinstance(terminal, Mapping) else 1
            )
            constraints = facts.get("operational_constraints") if isinstance(facts, Mapping) else []
            witness = self.response.get("admission_witness")
            configured_custody = (
                witness.get("constraint_custody")
                if isinstance(witness, Mapping)
                else None
            )
            constraint_custody = (
                []
                if isinstance(constraints, Sequence)
                and not isinstance(constraints, (str, bytes, bytearray))
                and not constraints
                else copy.deepcopy(configured_custody)
            )
            component_custody = self.configured_component_custody
            if component_custody is None:
                first_path = facts.get("first_path") if isinstance(facts, Mapping) else None
                distinct_first_path = _distinct_declared_citations(first_path)
                component_custody = {
                    "event_responsibilities": [
                        {
                            "event_order": order,
                            "responsibility_citation": copy.deepcopy(
                                distinct_first_path[order - 1]
                            ),
                        }
                        for order, event in enumerate(events or (), start=1)
                        if isinstance(event, Mapping)
                        and isinstance(event.get("actor_fact"), Mapping)
                        and event["actor_fact"].get("field") in {"title", "internal_systems"}
                        and order <= len(distinct_first_path)
                    ],
                    "additional_responsibilities": [],
                }
            self.response = admitted_review_response(
                participant_field=participant_field,
                participant_row=participant_row,
                result_event_order=result_event_order,
                provisional_design=design,
                component_custody=component_custody,
                source_precedence_custody=(
                    self.configured_source_precedence_custody
                ),
                constraint_custody=constraint_custody,
            )
        return super().generate_structured(request=request)


def admitted_review_response(
    *,
    component_custody: Mapping[str, Any] | None = None,
    constraint_custody: Sequence[Mapping[str, Any]],
    source_precedence_custody: Sequence[Mapping[str, Any]] = (),
    participant_field: str = "human_actors",
    participant_row: int = 1,
    task_event_order: int = 1,
    result_event_order: int = 3,
    provisional_design: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return one structurally grounded admitted-review fixture."""

    design = provisional_design or structural_design_fixture((1, 2, 3))
    risks = design["risk_posture"]["items"]
    return {
        "outcome": "admitted",
        "issue": None,
        "clarification": None,
        "admission_witness": {
            "participant_fact": {
                "field": participant_field,
                "row": participant_row,
            },
            "task_event_order": task_event_order,
            "result_event_order": result_event_order,
            "design_coverage": {
                "component_verification_keys": [row["key"] for row in design["components"]],
                "workstream_verification_keys": [row["key"] for row in design["workstreams"]],
                "risk_keys": [row["key"] for row in risks],
                "risk_posture_status": design["risk_posture"]["status"],
            },
            "component_custody": copy.deepcopy(
                component_custody
                if component_custody is not None
                else {
                    "event_responsibilities": [],
                    "additional_responsibilities": [],
                }
            ),
            "source_precedence_custody": copy.deepcopy(
                list(source_precedence_custody)
            ),
            "constraint_custody": copy.deepcopy(
                list(constraint_custody)
            ),
        },
    }


def host_candidate_response(
    response: Mapping[str, Any],
    *,
    evidence_text: str,
) -> dict[str, Any]:
    """Project a canonical test response into the public host-candidate shape."""

    candidate = copy.deepcopy(dict(response))
    candidate["version"] = HOST_CANDIDATE_FORMAT_VERSION
    result = candidate.get("result")
    if not isinstance(result, dict) or result.get("status") == "clarification_required":
        return candidate
    facts = result.get("facts")
    events = result.get("events")
    if not isinstance(facts, dict) or not isinstance(events, list):
        raise TypeError("canonical fixture cannot be projected to a host candidate")
    result.pop("components", None)
    result.pop("source_precedence", None)
    first_path = facts.pop("first_path")
    if not isinstance(first_path, list) or len(first_path) != len(events):
        raise ValueError("canonical fixture event citations are incomplete")
    for field, value in tuple(facts.items()):
        if isinstance(value, list):
            citations = [
                _unique_context_citation(evidence_text, row)
                for row in value
            ]
            facts[field] = citations
        elif isinstance(value, Mapping):
            facts[field] = _unique_context_citation(
                evidence_text,
                value,
                state_object=field == "state_object",
            )
    for event, citation in zip(events, first_path, strict=True):
        event["source_citation"] = _unique_context_citation(evidence_text, citation)
    return candidate


def component_custody_for_response(
    response: Mapping[str, Any] | None,
) -> dict[str, list[dict[str, Any]]]:
    """Translate declared canonical fixture truth into reviewer-owned custody.

    This helper does not interpret source prose. It only moves exact citations and
    typed owners already declared by a test fixture into the review witness.
    """

    result = response.get("result") if isinstance(response, Mapping) else None
    facts = result.get("facts") if isinstance(result, Mapping) else None
    events = result.get("events") if isinstance(result, Mapping) else None
    components = result.get("components") if isinstance(result, Mapping) else None
    raw_first_path = facts.get("first_path") if isinstance(facts, Mapping) else None
    first_path = _distinct_declared_citations(raw_first_path)
    constraints = (
        facts.get("operational_constraints") if isinstance(facts, Mapping) else None
    )
    if not (
        isinstance(facts, Mapping)
        and isinstance(events, list)
        and isinstance(components, list)
        and isinstance(raw_first_path, list)
        and len(first_path) == len(events)
        and isinstance(constraints, list)
    ):
        raise ValueError("canonical fixture cannot supply component custody")

    owner_facts: dict[str, dict[str, Any]] = {}
    title = facts.get("title")
    if isinstance(title, Mapping) and str(title.get("quote") or ""):
        owner_facts[str(title["quote"])] = {"field": "title", "row": 1}
    internal_systems = facts.get("internal_systems")
    if isinstance(internal_systems, list):
        for row, citation in enumerate(internal_systems, start=1):
            if isinstance(citation, Mapping) and str(citation.get("quote") or ""):
                owner_facts[str(citation["quote"])] = {
                    "field": "internal_systems",
                    "row": row,
                }

    declared: list[tuple[str, dict[str, Any]]] = []
    for component in components:
        if not isinstance(component, Mapping):
            raise ValueError("canonical fixture has invalid component truth")
        owner = str(component.get("owner_fact_quote") or "")
        responsibilities = component.get("responsibilities")
        if owner not in owner_facts or not isinstance(responsibilities, list):
            raise ValueError("canonical fixture has invalid component truth")
        for citation in responsibilities:
            if not isinstance(citation, Mapping):
                raise ValueError("canonical fixture has invalid component truth")
            declared.append((owner, copy.deepcopy(dict(citation))))

    used: set[int] = set()
    event_rows: list[dict[str, Any]] = []
    for event_order, (event, event_citation) in enumerate(
        zip(events, first_path, strict=True), start=1
    ):
        if not isinstance(event, Mapping) or not isinstance(event_citation, Mapping):
            raise ValueError("canonical fixture has invalid event truth")
        actor_fact = event.get("actor_fact")
        if not isinstance(actor_fact, Mapping):
            continue
        field = actor_fact.get("field")
        row = actor_fact.get("row")
        if field == "title" and row == 1:
            owner_citation = title
        elif (
            field == "internal_systems"
            and type(row) is int
            and isinstance(internal_systems, list)
            and 1 <= row <= len(internal_systems)
        ):
            owner_citation = internal_systems[row - 1]
        else:
            continue
        owner = (
            str(owner_citation.get("quote") or "")
            if isinstance(owner_citation, Mapping)
            else ""
        )
        event_quote = str(event_citation.get("quote") or "")
        matches = [
            index
            for index, (declared_owner, citation) in enumerate(declared)
            if index not in used
            and declared_owner == owner
            and str(citation.get("quote") or "") in event_quote
        ]
        if len(matches) > 1:
            raise ValueError("canonical fixture ambiguously binds an event responsibility")
        responsibility = (
            declared[matches[0]][1]
            if matches
            else copy.deepcopy(dict(event_citation))
        )
        if matches:
            used.add(matches[0])
        event_rows.append(
            {
                "event_order": event_order,
                "responsibility_citation": responsibility,
            }
        )

    constraint_values = [dict(row) for row in constraints if isinstance(row, Mapping)]
    additional_rows = [
        {
            "owner_fact": copy.deepcopy(owner_facts[owner]),
            "responsibility_citation": copy.deepcopy(citation),
        }
        for index, (owner, citation) in enumerate(declared)
        if index not in used and citation not in constraint_values
    ]
    return {
        "event_responsibilities": event_rows,
        "additional_responsibilities": additional_rows,
    }


def _distinct_declared_citations(value: Any) -> list[dict[str, Any]]:
    """Collapse exact duplicate fixture selections without interpreting their text."""

    if not isinstance(value, list):
        return []
    distinct: list[dict[str, Any]] = []
    for citation in value:
        if not isinstance(citation, Mapping):
            return []
        row = copy.deepcopy(dict(citation))
        if row not in distinct:
            distinct.append(row)
    return distinct


def write_host_candidate_fixture(
    path: Path,
    response: Mapping[str, Any],
    *,
    evidence_text: str,
) -> Path:
    """Write one public host candidate fixture and return its path."""

    path.write_text(
        json.dumps(
            host_candidate_response(response, evidence_text=evidence_text)
        ),
        encoding="utf-8",
    )
    return path


def _unique_context_citation(
    evidence_text: str,
    citation: Mapping[str, Any],
    *,
    state_object: bool = False,
) -> dict[str, str]:
    evidence = evidence_text.encode("utf-8")
    quote, start = resolve_source_citation(
        evidence,
        citation,
        state_object=state_object,
    )
    start_character = len(evidence[:start].decode("utf-8"))
    end_character = start_character + len(quote)
    for added in range(len(evidence_text) + 1):
        for before in range(added + 1):
            after = added - before
            left = max(0, start_character - before)
            right = min(len(evidence_text), end_character + after)
            context = evidence_text[left:right]
            if evidence_text.count(context) == 1 and context.count(quote) == 1:
                return {"quote": quote, "context": context}
    raise AssertionError("fixture could not derive unique citation context")


def authored_response(
    intent: Mapping[str, Any],
    *,
    evidence_text: str = "",
    first_path_segments: Sequence[str] | None = None,
    first_path_relations: Sequence[Mapping[str, Any]] | None = None,
    component_responsibility_owners: Sequence[str] | None = None,
    provisional_design: Mapping[str, Any] | None = None,
    source_precedence: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build model-shaped citations; fixture states retain their declared quote."""

    source_relations = tuple(
        first_path_relations or _default_first_path_relations(intent)
    )
    path_segments = (
        [str(row).strip() for row in first_path_segments]
        if first_path_segments is not None
        else [str(row.get("event_quote") or "").strip() for row in source_relations]
    )
    facts: dict[str, Any] = {
        **{field: None for field in _SINGULAR_SOURCE_FIELDS},
        **{field: [] for field in _REPEATED_SOURCE_FIELDS},
    }
    selected_facts: list[dict[str, Any]] = []
    fact_indexes: dict[str, int] = {}
    first_path_fact_indexes: list[int] = []
    for field, value in intent.items():
        if field in {"assumptions", "ambiguities", "component_responsibilities"}:
            continue
        rows = (
            path_segments
            if field == "first_path"
            else value if isinstance(value, list) else [value]
        )
        for row_index, row in enumerate(rows):
            quote = str(row).strip()
            if not quote:
                continue
            fact_index = len(selected_facts) + 1
            projection_path = f"/{field}" if not isinstance(value, list) else f"/{field}/{row_index}"
            citation = {"quote": quote, "occurrence": 1}
            if field in _SINGULAR_SOURCE_FIELDS:
                facts[field] = citation
                source_field_row = 1
            else:
                facts[field].append(citation)
                source_field_row = len(facts[field])
            selected_facts.append({"field": field, "row": source_field_row, **citation})
            fact_indexes[projection_path] = fact_index
            if field == "first_path":
                first_path_fact_indexes.append(fact_index)

    state_citation = facts["state_object"]
    if state_citation is not None:
        facts["state_object"] = {
            "quote": state_citation["quote"],
            "prefix": "",
            "anchor_occurrence": state_citation["occurrence"],
        }

    relation_rows = _relation_rows(
        source_relations,
        first_path_segments=(
            path_segments
        ),
        first_path_fact_indexes=first_path_fact_indexes,
        fact_indexes=fact_indexes,
        intent=intent,
    )
    if not relation_rows:
        raise ValueError("authored fixture requires one event")
    terminal = _terminal_row(
        relations=source_relations,
        facts=selected_facts,
        evidence_text=evidence_text,
    )
    components = _component_responsibility_relation_rows(
        intent=intent,
        fact_indexes=fact_indexes,
        owners=component_responsibility_owners,
    )
    return {
        "version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "result": {
            "status": "authored",
            "facts": facts,
            "events": relation_rows,
            "source_precedence": [dict(row) for row in source_precedence],
            "terminal": terminal,
            "components": components,
            "assumptions": list(intent.get("assumptions") or []),
            "ambiguities": list(intent.get("ambiguities") or []),
            "consistency": {"status": "consistent", "evidence_quotes": []},
            "provisional_design": copy.deepcopy(provisional_design) if provisional_design is not None
            else structural_design_fixture(range(1, len(relation_rows) + 1)),
        },
    }


def structural_design_fixture(
    event_orders: Sequence[int], *, first_run_event_orders: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Synthetic design for custody/wiring tests, never product-quality evidence."""

    orders = list(event_orders)
    if not orders:
        raise ValueError("design fixture requires source events")
    components = [
        {
            "key": f"test-boundary-{index}",
            "name": f"Structural test boundary {index}",
            "responsibility": f"Retain the test value at boundary {index}.",
            "supported_event_orders": orders if index == 1 else [orders[(index - 1) % len(orders)]],
            "verification": f"Read back the exact test value assigned to boundary {index}.",
            "verification_event_orders": (
                orders if index == 1 else [orders[(index - 1) % len(orders)]]
            ),
        }
        for index in range(1, 5)
    ]
    return {
        "version": "odylith.greenfield.provisional-design.v6",
        "authority_kind": "provisional_design",
        "first_run": {
            "event_orders": list(first_run_event_orders) if first_run_event_orders is not None else orders,
            "rationale": "The fixture proposes this execution order; citation order does not establish chronology.",
        },
        "components": components,
        "workstreams": [
            {
                "key": f"test-work-{index}",
                "title": f"Implement structural test boundary {index}",
                "problem": f"Users cannot yet rely on the distinct test boundary {index}.",
                "component_keys": [row["key"]],
                "depends_on": [f"test-work-{index - 1}"] if index > 1 else [],
                "deliverable": f"Implement the exact-value boundary {index}.",
                "verification": f"An independent read returns the test value from boundary {index}.",
                "verification_event_orders": list(row["verification_event_orders"]),
            }
            for index, row in enumerate(components, 1)
        ],
        "exchanges": [
            {
                "from_component": components[index - 1]["key"],
                "to_component": components[index]["key"],
                "contract": f"The exact test value from boundary {index}.",
            }
            for index in range(1, 4)
        ],
        "risk_posture": {
            "status": "no_material_risks_identified",
            "rationale": "This structural fixture carries no product-domain risk claim.",
            "items": [],
        },
    }


def clarification_response(
    *,
    question: str,
    material_dimension: str,
    evidence_quotes: Sequence[str],
    consistency_status: str = "material_ambiguity",
) -> dict[str, Any]:
    """Return a clarification response; the question remains test-only metadata."""

    del question
    return {
        "version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "result": {
            "status": "clarification_required",
            "consistency": {
                "status": consistency_status,
                "evidence_quotes": [str(quote) for quote in evidence_quotes],
            },
            "clarification": {"material_dimension": material_dimension},
        },
    }


def model_event_rows(response: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return mutable fixture event rows in their authored order."""

    result = response.get("result")
    events = result.get("events") if isinstance(result, Mapping) else None
    if not isinstance(events, list) or not all(
        isinstance(row, dict) for row in events
    ):
        raise ValueError("authored fixture response has no event graph")
    return events


def _relation_rows(
    relations: Sequence[Mapping[str, Any]],
    *,
    first_path_segments: Sequence[str],
    first_path_fact_indexes: Sequence[int],
    fact_indexes: Mapping[str, int],
    intent: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for relation in relations:
        event_quote = str(relation.get("event_quote") or "")
        # Legacy-looking surface text is accepted only as fixture ergonomics for
        # choosing an already-selected human/external fact; it is never emitted.
        test_surface_actor_quote = str(relation.get("actor_quote") or "")
        target_quote = str(relation.get("target_quote") or "")
        actor_kind = str(relation.get("actor_kind") or "")
        segment_index = relation.get("segment_index")
        if isinstance(segment_index, int) and not isinstance(segment_index, bool):
            selected_segment_index = segment_index
        else:
            matches = [
                index
                for index, segment in enumerate(first_path_segments)
                if _occurrence(segment, event_quote)
            ]
            if len(matches) != 1:
                raise ValueError(
                    "authored fixture relation must identify exactly one first_path segment"
                )
            selected_segment_index = matches[0]
        if selected_segment_index < 0 or selected_segment_index >= len(first_path_fact_indexes):
            raise ValueError("authored fixture relation references an unknown first_path segment")
        actor_fact = _actor_fact(
            relation,
            actor_kind=actor_kind,
            test_surface_actor_quote=test_surface_actor_quote,
            fact_indexes=fact_indexes,
            intent=intent,
        )
        rows.append(
            {
                "actor_fact": actor_fact,
                "action_quote": str(
                    relation.get("action_verb_quote") or event_quote
                ),
                "target_quote": target_quote,
            }
        )
    return rows


def _terminal_row(
    *,
    relations: Sequence[Mapping[str, Any]],
    facts: Sequence[Mapping[str, Any]],
    evidence_text: str,
) -> dict[str, Any]:
    visible_rows = [
        (order, str(relation.get("visible_result_quote") or ""))
        for order, relation in enumerate(relations, start=1)
        if str(relation.get("visible_result_quote") or "")
    ]
    if not visible_rows:
        raise ValueError("authored fixture requires one terminal visible result")
    event_order, result_quote = visible_rows[-1]
    proof_fact = next(
        (
            fact
            for fact in facts
            if fact["field"] in TERMINAL_RESULT_FACT_FIELDS
            and result_quote in str(fact.get("quote") or "")
        ),
        None,
    )
    if proof_fact is None:
        raise ValueError(
            "authored fixture terminal result requires a selected proof fact"
        )
    if evidence_text:
        _nth_start(
            evidence_text.encode("utf-8"),
            str(proof_fact["quote"]).encode("utf-8"),
            int(proof_fact["occurrence"]),
        )
    return {
        "event_order": event_order,
        "result_fact": {"field": proof_fact["field"], "row": proof_fact["row"]},
        "result_quote": result_quote,
        "result_occurrence": 1,
    }


def _actor_fact(
    relation: Mapping[str, Any],
    *,
    actor_kind: str,
    test_surface_actor_quote: str,
    fact_indexes: Mapping[str, int],
    intent: Mapping[str, Any],
) -> dict[str, object]:
    explicit_path = relation.get("actor_fact_path")
    if explicit_path is not None:
        return _actor_fact_reference_for_path(
            explicit_path,
            actor_kind=actor_kind,
            relation=relation,
            test_surface_actor_quote=test_surface_actor_quote,
            fact_indexes=fact_indexes,
            intent=intent,
        )
    if actor_kind == "product":
        return _owner_system_fact_reference(
            relation,
            fact_indexes=fact_indexes,
            intent=intent,
        )
    field = {
        "human": "human_actors",
        "external_system": "external_systems",
    }.get(actor_kind)
    if field is None:
        raise ValueError(f"unknown authored fixture actor_kind: {actor_kind}")
    selected_quote = str(
        relation.get("actor_fact_quote") or test_surface_actor_quote
    )
    rows = [str(row) for row in intent.get(field, [])]
    matches = [index for index, row in enumerate(rows) if row == selected_quote]
    if len(matches) != 1:
        raise ValueError("authored fixture actor must identify one exact selected entity fact")
    if not fact_indexes.get(f"/{field}/{matches[0]}", 0):
        raise ValueError("authored fixture actor fact is not selected")
    return {"field": field, "row": matches[0] + 1}


def _actor_fact_reference_for_path(
    path: object,
    *,
    actor_kind: str,
    relation: Mapping[str, Any],
    test_surface_actor_quote: str,
    fact_indexes: Mapping[str, int],
    intent: Mapping[str, Any],
) -> dict[str, object]:
    if not isinstance(path, str) or not fact_indexes.get(path, 0):
        raise ValueError("authored fixture actor path is not selected")
    field, separator, row_text = path.strip("/").partition("/")
    if not separator or not row_text.isdigit():
        if path == "/title" and actor_kind == "product":
            field, row_text = "title", "0"
        else:
            raise ValueError("authored fixture actor path is invalid")
    row_index = int(row_text)
    expected_fields = {
        "human": {"human_actors"},
        "external_system": {"external_systems"},
        "product": {"title", "internal_systems"},
    }.get(actor_kind)
    if expected_fields is None or field not in expected_fields:
        raise ValueError("authored fixture actor path conflicts with actor_kind")
    values = [str(value) for value in intent.get(field, [])] if field != "title" else [str(intent.get("title") or "")]
    if row_index < 0 or row_index >= len(values) or not values[row_index]:
        raise ValueError("authored fixture actor path is not selected")
    expected_quote = str(
        relation.get("owner_system_quote")
        if actor_kind == "product"
        else relation.get("actor_fact_quote") or test_surface_actor_quote
    )
    if expected_quote and expected_quote != values[row_index]:
        raise ValueError("authored fixture actor path conflicts with actor quote")
    return {"field": field, "row": row_index + 1}


def _owner_system_fact_reference(
    relation: Mapping[str, Any],
    *,
    fact_indexes: Mapping[str, int],
    intent: Mapping[str, Any],
) -> dict[str, object]:
    owner = str(relation.get("owner_system_quote") or "")
    systems = [str(row) for row in intent.get("internal_systems", [])]
    if not owner:
        raise ValueError("authored fixture must explicitly bind every product event to owner_system_quote")
    if owner == str(intent.get("title") or ""):
        if fact_indexes.get("/title", 0):
            return {"field": "title", "row": 1}
    for index, system in enumerate(systems):
        if owner == system and fact_indexes.get(f"/internal_systems/{index}", 0):
            return {"field": "internal_systems", "row": index + 1}
    raise ValueError(f"unknown authored fixture owner_system_quote: {owner}")


def _component_responsibility_relation_rows(
    *,
    intent: Mapping[str, Any],
    fact_indexes: Mapping[str, int],
    owners: Sequence[str] | None,
) -> list[dict[str, Any]]:
    responsibilities = [
        str(row)
        for row in intent.get("component_responsibilities", [])
        if str(row)
    ]
    systems = [str(row) for row in intent.get("internal_systems", []) if str(row)]
    if not responsibilities:
        return []
    if owners is None:
        raise ValueError(
            "authored fixture must explicitly bind component_responsibility_owners"
        )
    owner_values = [str(owner) for owner in owners]
    if len(owner_values) != len(responsibilities):
        raise ValueError("authored fixture must bind every component responsibility exactly once")
    rows: list[dict[str, Any]] = []
    for index, owner in enumerate(owner_values):
        owner_fact_quote = _owner_fact_quote(
            owner=owner,
            intent=intent,
            systems=systems,
            fact_indexes=fact_indexes,
        )
        if not owner_fact_quote:
            raise ValueError("authored fixture component responsibility owner is not a selected fact")
        group = next(
            (
                row
                for row in rows
                if row["owner_fact_quote"] == owner_fact_quote
            ),
            None,
        )
        if group is None:
            group = {
                "owner_fact_quote": owner_fact_quote,
                "responsibilities": [],
            }
            rows.append(group)
        group["responsibilities"].append(
            {"quote": responsibilities[index], "occurrence": 1}
        )
    return rows


def _owner_fact_quote(
    *,
    owner: str,
    intent: Mapping[str, Any],
    systems: Sequence[str],
    fact_indexes: Mapping[str, int],
) -> str:
    if owner == str(intent.get("title") or ""):
        path = "/title"
    else:
        try:
            path = f"/internal_systems/{systems.index(owner)}"
        except ValueError as exc:
            raise ValueError(
                f"unknown authored fixture component responsibility owner: {owner}"
            ) from exc
    fact_index = fact_indexes.get(path, 0)
    if not fact_index:
        raise ValueError("authored fixture component owner is not a selected fact")
    return owner


def _default_first_path_relations(intent: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    first_path = str(intent.get("first_path") or "").strip()
    actors = intent.get("human_actors") or []
    human_actor = str(actors[0]).strip() if actors else ""
    return (
        {
            "actor_kind": "human",
            "actor_fact_quote": human_actor,
            "event_quote": first_path,
            "action_verb_quote": first_path,
            "target_quote": "",
            "visible_result_quote": first_path,
        },
    )


def _occurrence(source: str, quote: str) -> int:
    return 1 if quote and source.encode("utf-8").find(quote.encode("utf-8")) >= 0 else 0


def _nth_start(source: bytes, quote: bytes, occurrence: int) -> int:
    cursor = 0
    found = -1
    for _ in range(occurrence):
        found = source.find(quote, cursor)
        if found < 0:
            raise ValueError("authored fixture quote occurrence is not present")
        cursor = found + 1
    return found
