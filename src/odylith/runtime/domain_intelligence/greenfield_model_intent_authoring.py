"""Source-cited model authoring for pre-confirm Greenfield Product Intent.

The authoring model may propose meaning, but it cannot create authority. This
module accepts only a closed typed response, verifies every cited byte range
against the untrusted evidence supplied to the model, and returns canonical
facts for the deterministic custody, Tribunal, projection, and transaction
pipeline. It never writes files or invokes a fallback parser.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_assumptions import (
    ASSUMPTION_SCHEMA,
    assumption_rows,
    provisional_proof_assumption,
    require_decision_assumptions,
    require_provisional_proof_decision,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    GreenfieldAuthoredSemanticsError,
    authored_component_relation_facts,
)
from odylith.runtime.domain_intelligence.greenfield_authored_relation_validation import MAX_SOURCE_EVENT_RELATIONS
from odylith.runtime.domain_intelligence.greenfield_semantic_invariants import (
    HUMAN_ACTOR_ROLE_DEFINITION,
    INTERNAL_SYSTEM_ROLE_DEFINITION,
    OPERATIONAL_CONSTRAINT_ROLE_DEFINITION,
    PRODUCT_STORY_ROLE_DEFINITION,
    PROOF_BOUNDARY_ROLE_DEFINITION,
    STATE_OBJECT_ROLE_DEFINITION,
    TITLE_ROLE_DEFINITION,
)
from odylith.runtime.domain_intelligence.greenfield_event_ordering import (
    SOURCE_PRECEDENCE_SCHEMA,
    validate_source_precedence,
)
from odylith.runtime.domain_intelligence.greenfield_material_clarification import (
    MATERIAL_DIMENSIONS,
)
from odylith.runtime.domain_intelligence.greenfield_model_atomic_projection import (
    derive_model_atomic_claims,
)
from odylith.runtime.domain_intelligence.greenfield_model_direct_evidence_graph import (
    MODEL_COMPONENT_SCHEMA,
    MODEL_EVENT_SCHEMA,
    MODEL_TERMINAL_SCHEMA,
    derive_model_relations,
    model_component_responsibility_rows,
)
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelAuthoringError,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
)
from odylith.runtime.domain_intelligence.greenfield_model_source_citations import (
    canonical_citation_from_host_selection,
    exact_occurrence_start,
    exact_quote,
    resolve_source_citation,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    MAX_AUTHORED_CITATIONS,
    MAX_AUTHORED_FIELD_VALUE_CHARS,
    MAX_AUTHORED_LIST_ITEMS,
)
from odylith.runtime.domain_intelligence.greenfield_provisional_design import (
    PROVISIONAL_DESIGN_SCHEMA,
    validate_provisional_design,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    verify_greenfield_source_duty_ledger_receipt,
    resolve_greenfield_action_actor_identity,
)

GREENFIELD_INTENT_AUTHORING_VERSION = "odylith.greenfield.intent-authoring.v80"
MATERIALITY_DECISION_CONTRACT = (
    "Ask only when a missing or conflicting choice materially changes the target "
    "user, usable path, visible outcome, product/dependency boundary, source constraint, "
    "safety or proof obligation and cannot safely remain an explicit proposed assumption. "
    "Admission requires a source-supported participant, beneficiary, or explicit "
    "product/system task owner; a usable task; and a visible result. A product title "
    "cannot act as a fabricated user, but a source-supported product or internal system "
    "may own its bound task. Assumptions or provisional design cannot fill any of those "
    "three accepted-source gaps. Use first_path when any part is absent or when competing "
    "task interpretations cannot safely remain proposed. Missing implementation detail "
    "alone does not require clarification. Use product_boundary for a "
    "competing or unclear product responsibility or scope limit; otherwise select "
    "the matching material dimension. Explicit source results, dependencies, "
    "constraints and safety obligations cannot be overridden by assumptions."
)

_TEXT_FIELDS = (
    "title",
    "product_story",
    "state_object",
    "first_path",
    "proof_boundary",
    "problem",
    "customer",
    "opportunity",
    "product_view",
)
_LIST_FIELDS = (
    "supporting_events",
    "success_metrics",
    "evidence_requirements",
    "operational_constraints",
    "component_responsibilities",
    "human_actors",
    "external_systems",
    "internal_systems",
    "assumptions",
    "ambiguities",
    "non_goals",
)
_INTENT_FIELDS = (*_TEXT_FIELDS, *_LIST_FIELDS)
_SINGULAR_SOURCE_FIELDS = tuple(
    field for field in _TEXT_FIELDS if field != "first_path"
)
_REPEATED_SOURCE_FIELDS = (
    "first_path",
    *(
        field
        for field in _LIST_FIELDS
        if field not in {"assumptions", "ambiguities", "component_responsibilities"}
    ),
)
_SOURCE_FACT_FIELDS = tuple(
    field
    for field in _INTENT_FIELDS
    if field not in {"assumptions", "ambiguities", "component_responsibilities"}
)
_OPTIONAL_SOURCE_FACT_FIELDS = frozenset({"supporting_events"})
_SOURCE_REQUIRED_FIELDS = frozenset(
    (*_SOURCE_FACT_FIELDS, "component_responsibilities")
)
_CONSISTENCY_STATUSES = (
    "consistent",
    "non_material_ambiguity",
    "material_ambiguity",
    "material_contradiction",
)


@dataclass(frozen=True)
class GreenfieldAuthoringClarification:
    """One model-identified material dimension rendered by caller policy."""

    required_fields: tuple[str, ...]
    elapsed_seconds: float
    tier: str
    provider: dict[str, str]
    profile_id: str
    effective_timeout_seconds: float
    consistency_status: str
    consistency_source_spans: tuple[dict[str, Any], ...]
    clarification_basis: str = ""
    effective_model_window_seconds: float = 0.0
    semantic_model_call_count: int = 0


@dataclass(frozen=True)
class GreenfieldModelAuthoredIntent:
    """Verified pre-confirm facts and the source spans that justify them."""

    intent: dict[str, Any]
    source_event_relations: tuple[dict[str, Any], ...]
    first_path_context_relations: tuple[dict[str, Any], ...]
    component_responsibility_relations: tuple[dict[str, Any], ...]
    atomic_claims: tuple[dict[str, Any], ...]
    source_spans: tuple[dict[str, Any], ...]
    source_sha256: str
    provisional_design: dict[str, Any]
    source_precedence: tuple[dict[str, int], ...]
    elapsed_seconds: float
    tier: str
    provider: dict[str, str]
    profile_id: str
    effective_timeout_seconds: float
    consistency_status: str
    effective_model_window_seconds: float = 0.0
    semantic_model_call_count: int = 0

    first_path_event_orders: tuple[int, ...] = ()

    @property
    def first_path_relations(self) -> tuple[dict[str, Any], ...]:
        if not self.first_path_event_orders:
            return self.source_event_relations
        by_order = {row["order"]: row for row in self.source_event_relations}
        return tuple(by_order[order] for order in self.first_path_event_orders)


def authoring_tier(profile_id: str) -> str:
    """Return the immutable tier selected before the provider call."""

    return get_greenfield_model_profile(profile_id).repair_tier


def validate_greenfield_authoring_response(
    response: Mapping[str, Any],
    *,
    evidence_text: str,
    elapsed_seconds: float,
    provider: Mapping[str, str],
    profile_id: str,
    effective_timeout_seconds: float,
    semantic_model_call_count: int,
    allow_zero_semantic_calls: bool = False,
    event_citations_are_event_owned: bool = False,
    allow_exact_dual_role_constraints: bool = False,
    first_path_event_orders: Sequence[int] | None = None,
    accepted_source_duties: Mapping[str, Any] | None = None,
    accepted_source_duty_binding: Mapping[str, Any] | None = None,
) -> GreenfieldModelAuthoredIntent | GreenfieldAuthoringClarification:
    minimum_call_count = 0 if allow_zero_semantic_calls else 1
    if type(semantic_model_call_count) is not int or semantic_model_call_count < minimum_call_count:
        raise GreenfieldModelAuthoringError(
            "Greenfield authoring received an invalid semantic call count; no records were created."
        )
    if set(response) != {"version", "result"}:
        raise GreenfieldModelAuthoringError("Greenfield authoring returned an unsupported response contract; no records were created.")
    if str(response.get("version") or "") != GREENFIELD_INTENT_AUTHORING_VERSION:
        raise GreenfieldModelAuthoringError("Greenfield authoring returned an unsupported response contract; no records were created.")
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise GreenfieldModelAuthoringError("Greenfield authoring returned an unsupported response contract; no records were created.")
    consistency_status, consistency_spans = _validated_consistency_assessment(
        result.get("consistency"),
        evidence_text=evidence_text,
    )
    status = str(result.get("status") or "")
    if status == "clarification_required":
        if set(result) != {"status", "consistency", "clarification"}:
            raise GreenfieldModelAuthoringError("Greenfield authoring returned an unsupported clarification contract; no records were created.")
        if consistency_status not in {"material_ambiguity", "material_contradiction"}:
            raise GreenfieldModelAuthoringError(
                "Greenfield authoring returned an invalid evidence consistency decision; no records were created."
            )
        required_fields = _validated_clarification(result)
        return GreenfieldAuthoringClarification(
            required_fields=required_fields,
            elapsed_seconds=elapsed_seconds,
            tier=authoring_tier(profile_id),
            provider={str(key): str(value) for key, value in provider.items()},
            profile_id=profile_id,
            effective_timeout_seconds=effective_timeout_seconds,
            consistency_status=consistency_status,
            consistency_source_spans=consistency_spans,
            semantic_model_call_count=semantic_model_call_count,
        )
    if status != "authored":
        raise GreenfieldModelAuthoringError(
            "A verified source-cited Greenfield package could not be produced from this evidence; no records were created."
        )
    if set(result) != {
        "status",
        "facts",
        "events",
        "terminal",
        "components",
        "assumptions",
        "ambiguities",
        "consistency",
        "provisional_design",
        "source_precedence",
    }:
        raise GreenfieldModelAuthoringError("Greenfield authoring returned an unsupported authored contract; no records were created.")
    if consistency_status in {"material_ambiguity", "material_contradiction"}:
        raise GreenfieldModelAuthoringError(
            "Greenfield authoring attempted to package materially unresolved evidence; no records were created."
        )
    if consistency_status == "non_material_ambiguity" and not _advisory_rows(result.get("ambiguities")):
        raise GreenfieldModelAuthoringError(
            "Greenfield authoring omitted the ambiguity raised by conflicting evidence; no records were created."
        )
    try:
        normalized_actions = _accepted_source_actions(
            accepted_source_duties,
            accepted_source_duty_binding,
            evidence_text=evidence_text, events=result.get("events"),
        )
        if accepted_source_duties is not None:
            if result.get("components") != []:
                raise GreenfieldModelAuthoringError("Verified duties own component responsibility authority")
            component_rows = []
            for (field, _), duty in normalized_actions.items():
                if field == "component_responsibilities":
                    citation = canonical_citation_from_host_selection(
                        evidence_text.encode("utf-8"), duty["event_ref"],
                    )
                    component_rows.append({
                        "responsibility_quote": citation["quote"],
                        "responsibility_occurrence": citation["occurrence"],
                    })
        else:
            component_rows = model_component_responsibility_rows(result.get("components"))
        intent, source_spans, selected_facts = _intent_from_typed_source_spans(
            result.get("facts"),
            component_rows=component_rows,
            evidence_text=evidence_text,
            assumptions=result.get("assumptions"),
            ambiguities=result.get("ambiguities"),
            normalized_actions=normalized_actions,
        )
        terminal = result.get("terminal")
        has_provisional_proof = bool(
            provisional_proof_assumption(intent.get("assumptions", []))
        )
        if (terminal is None) != has_provisional_proof:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring mixed source terminal and provisional proof authority"
            )
        derived_relations = derive_model_relations(
            events=result.get("events"),
            terminal=terminal,
            components=result.get("components"),
            selected_facts=selected_facts,
            first_path=str(intent.get("first_path") or ""),
            evidence_text=evidence_text,
            event_citations_are_event_owned=event_citations_are_event_owned,
            allow_exact_dual_role_constraints=allow_exact_dual_role_constraints,
            first_path_event_orders=first_path_event_orders,
            source_owned_actor_facts=(accepted_source_duties is not None
                and accepted_source_duties["ledger"]["version"] in {"odylith.greenfield.source-duty-ledger.v7", "odylith.greenfield.source-duty-ledger.v8"}),
            source_event_graph=(accepted_source_duties is not None
                and accepted_source_duties["ledger"]["version"] == "odylith.greenfield.source-duty-ledger.v8"),
        )
        authored_component_relation_facts(
            title=str(intent.get("title") or ""),
            internal_systems=tuple(str(row) for row in intent.get("internal_systems", ())),
            relations=derived_relations.source_event_relations,
            component_responsibility_relations=(
                derived_relations.component_responsibility_relations
            ),
        )
    except GreenfieldAuthoredSemanticsError as exc:
        raise GreenfieldModelAuthoringError(f"{exc}; no records were created.") from exc
    try:
        atomic_claims = derive_model_atomic_claims(
            intent=intent,
            selected_facts=selected_facts,
            first_path_relations=derived_relations.source_event_relations,
            terminal_result_fact=derived_relations.terminal_result_fact,
        )
    except GreenfieldAuthoredSemanticsError as exc:
        raise GreenfieldModelAuthoringError(f"{exc}; no records were created.") from exc
    tier = authoring_tier(profile_id)
    try:
        event_orders = [row["order"] for row in derived_relations.source_event_relations]
        source_precedence = validate_source_precedence(
            result.get("source_precedence"), event_orders=event_orders,
            operational_constraints=intent["operational_constraints"],
        )
        provisional_design = validate_provisional_design(
            result.get("provisional_design"),
            event_orders=event_orders, source_precedence=source_precedence,
            result_event_order=next(
                (
                    row["order"]
                    for row in derived_relations.source_event_relations
                    if row["visible_result_quote"]
                ),
                None,
            ),
        )
    except ValueError as exc:
        raise GreenfieldModelAuthoringError(f"{exc}; no records were created.") from exc
    return GreenfieldModelAuthoredIntent(
        intent=intent,
        source_event_relations=derived_relations.source_event_relations,
        first_path_event_orders=tuple(first_path_event_orders or ()),
        first_path_context_relations=(
            derived_relations.first_path_context_relations
        ),
        component_responsibility_relations=(
            derived_relations.component_responsibility_relations
        ),
        atomic_claims=atomic_claims,
        source_spans=(*source_spans, *consistency_spans),
        source_sha256=hashlib.sha256(evidence_text.encode("utf-8")).hexdigest(),
        provisional_design=provisional_design,
        source_precedence=source_precedence,
        elapsed_seconds=elapsed_seconds,
        tier=tier,
        provider={str(key): str(value) for key, value in provider.items()},
        profile_id=profile_id,
        effective_timeout_seconds=effective_timeout_seconds,
        consistency_status=consistency_status,
        semantic_model_call_count=semantic_model_call_count,
    )


def _validated_clarification(response: Mapping[str, Any]) -> tuple[str, ...]:
    clarification = response.get("clarification")
    if not isinstance(clarification, Mapping):
        raise GreenfieldModelAuthoringError("Greenfield authoring returned an invalid clarification; no records were created.")
    if set(clarification) != {"material_dimension"}:
        raise GreenfieldModelAuthoringError("Greenfield authoring returned an invalid clarification; no records were created.")
    dimension = str(clarification.get("material_dimension") or "")
    if dimension not in MATERIAL_DIMENSIONS:
        raise GreenfieldModelAuthoringError("Greenfield authoring did not identify one material clarification; no records were created.")
    return (dimension,)


def _validated_consistency_assessment(
    value: Any,
    *,
    evidence_text: str,
) -> tuple[str, tuple[dict[str, Any], ...]]:
    """Bind missingness to all evidence and contradictions to their exact sides."""

    if not isinstance(value, Mapping) or set(value) != {"status", "evidence_quotes"}:
        raise GreenfieldModelAuthoringError(
            "Greenfield authoring returned an invalid evidence consistency assessment; no records were created."
        )
    status = str(value.get("status") or "")
    quotes = value.get("evidence_quotes")
    if status not in _CONSISTENCY_STATUSES or not isinstance(quotes, Sequence) or isinstance(
        quotes, (str, bytes, bytearray)
    ):
        raise GreenfieldModelAuthoringError(
            "Greenfield authoring returned an invalid evidence consistency assessment; no records were created."
        )
    if status == "consistent":
        if quotes:
            raise GreenfieldModelAuthoringError(
                "Greenfield authoring attached evidence citations to a consistent assessment; no records were created."
            )
        return status, ()
    evidence_bytes = evidence_text.encode("utf-8")
    if status == "material_ambiguity":
        if quotes:
            raise GreenfieldModelAuthoringError(
                "Greenfield authoring attached copied evidence to a missing-information ambiguity; no records were created."
            )
        return status, (
            {
                "span_id": "authoring:consistency:1",
                "section_key": "ambiguities",
                "row_index": 1,
                "classification": "supporting_evidence",
                "text": evidence_text,
                "source_start_byte": 0,
                "source_end_byte": len(evidence_bytes),
                "quote_sha256": hashlib.sha256(evidence_bytes).hexdigest(),
            },
        )
    if not 2 <= len(quotes) <= 4:
        raise GreenfieldModelAuthoringError(
            "Greenfield authoring did not source-bind its unresolved evidence assessment; no records were created."
        )

    spans: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for index, raw in enumerate(quotes, start=1):
        if not isinstance(raw, str):
            raise GreenfieldModelAuthoringError(
                "Greenfield authoring returned an invalid evidence consistency citation; no records were created."
            )
        quote = exact_quote(raw)
        quote_bytes = quote.encode("utf-8")
        start = exact_occurrence_start(evidence_bytes, quote_bytes, 1)
        end = start + len(quote_bytes)
        if not quote or (start, end) in seen:
            raise GreenfieldModelAuthoringError(
                "Greenfield authoring duplicated an evidence consistency citation; no records were created."
            )
        seen.add((start, end))
        spans.append(
            {
                "span_id": f"authoring:consistency:{index}",
                "section_key": "ambiguities",
                "row_index": index,
                "classification": "supporting_evidence",
                "text": quote,
                "source_start_byte": start,
                "source_end_byte": end,
                "quote_sha256": hashlib.sha256(quote_bytes).hexdigest(),
            }
        )
    return status, tuple(spans)


def _accepted_source_actions(
    receipt: Mapping[str, Any] | None,
    binding: Mapping[str, Any] | None,
    *,
    evidence_text: str,
    events: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, int], dict[str, Any]]:
    """Project each verified duty independently, preserving exact actor ownership."""
    if receipt is None and binding is None:
        return {}
    if receipt is None or binding is None:
        raise GreenfieldModelAuthoringError(
            "Greenfield verified source actions require their event binding"
        )
    verified = verify_greenfield_source_duty_ledger_receipt(
        receipt, evidence_text=evidence_text
    )
    ledger = verified["ledger"]
    by_order: dict[int, dict[str, Any]] = {}
    path_orders: set[int] = set()
    if ledger["version"] in {"odylith.greenfield.source-duty-ledger.v6", "odylith.greenfield.source-duty-ledger.v7", "odylith.greenfield.source-duty-ledger.v8"}:
        from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import (
            project_greenfield_source_event_catalog,
        )
        catalog = project_greenfield_source_event_catalog(verified, evidence_text=evidence_text,
                    _passive=ledger["version"] != "odylith.greenfield.source-duty-ledger.v8")
        if any(binding.get(section) != rows for section, rows in catalog["action_bindings"].items()):
            raise GreenfieldModelAuthoringError("Greenfield source action binding differs from its frozen catalog")
        if ledger["version"] in {"odylith.greenfield.source-duty-ledger.v7", "odylith.greenfield.source-duty-ledger.v8"} and (
            [event.get("actor_fact") for event in events]
            != [event["actor_fact"] for event in catalog["events"]]
        ):
            raise GreenfieldModelAuthoringError("Greenfield canonical event actor differs from its verified source action")
        by_order = catalog["actions"]
        path_orders = {order for order, duty in by_order.items()
                       if duty["binding_role"] == "first_path_actions"}
    else:
        for section in ("first_path_actions", "supporting_human_actions", "system_duties"):
            source_rows = ledger[section]
            binding_rows = binding.get(section)
            if not isinstance(binding_rows, list) or len(binding_rows) != len(source_rows):
                raise GreenfieldModelAuthoringError("Greenfield source action binding is malformed")
            for duty, bound in zip(source_rows, binding_rows, strict=True):
                if not isinstance(bound, Mapping) or bound.get("duty_id") != duty["id"]:
                    raise GreenfieldModelAuthoringError("Greenfield source action binding is malformed")
                order = bound.get("event_order")
                if type(order) is not int or order < 1 or order in by_order:
                    raise GreenfieldModelAuthoringError("Greenfield source action binding is malformed")
                by_order[order] = dict(duty)
                if section == "first_path_actions":
                    path_orders.add(order)
    if not by_order or set(by_order) != set(range(1, len(by_order) + 1)):
        raise GreenfieldModelAuthoringError("Greenfield source action binding is incomplete")
    result: dict[tuple[str, int], dict[str, Any]] = {}
    path_row = supporting_row = 0
    component_row = 0
    for order in sorted(by_order):
        if order in path_orders:
            path_row += 1
            key = ("first_path", path_row)
        else:
            supporting_row += 1
            key = ("supporting_events", supporting_row)
        result[key] = {
            **by_order[order],
            "decision_set_sha256": verified["decision_set_sha256"],
            "event_order": order,
        }
        actor_field = (by_order[order]["actor_fact"]["field"] if "actor_fact" in by_order[order]
                       else events[order - 1]["actor_fact"]["field"])
        if actor_field in {"title", "internal_systems"}:
            duty = result[key]
            resolve_greenfield_action_actor_identity(duty, path=key[0])
            component_row += 1
            result[("component_responsibilities", component_row)] = duty
    return result


def _intent_from_typed_source_spans(
    value: Any,
    *,
    component_rows: Sequence[Mapping[str, Any]],
    evidence_text: str,
    assumptions: Any,
    ambiguities: Any,
    normalized_actions: Mapping[tuple[str, int], Mapping[str, Any]],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    """Compile canonical facts from exact quotes and their source occurrences.

    The model selects the source address; deterministic resolution supplies exact
    coordinates and hashes. State objects use a split anchor without changing
    the projected semantic quote or borrowing the prefix's meaning.
    """

    if not isinstance(value, Mapping) or (
        set(value) - _OPTIONAL_SOURCE_FACT_FIELDS
    ) != (set(_SOURCE_FACT_FIELDS) - _OPTIONAL_SOURCE_FACT_FIELDS):
        raise GreenfieldModelAuthoringError("Greenfield authoring returned invalid source citations; no records were created.")
    typed_citations: list[tuple[str, int, Mapping[str, Any]]] = []
    for source_field in _SOURCE_FACT_FIELDS:
        raw_value = value.get(source_field)
        if source_field in _SINGULAR_SOURCE_FIELDS:
            rows: Sequence[Any] = () if raw_value is None else (raw_value,)
        elif (
            isinstance(raw_value, Sequence)
            and not isinstance(raw_value, (str, bytes, bytearray))
            and len(raw_value) <= MAX_AUTHORED_LIST_ITEMS
        ):
            rows = raw_value
        else:
            raise GreenfieldModelAuthoringError("Greenfield authoring returned invalid source citations; no records were created.")
        for source_field_row, raw in enumerate(rows, start=1):
            if not isinstance(raw, Mapping):
                raise GreenfieldModelAuthoringError("Greenfield authoring returned invalid source citations; no records were created.")
            typed_citations.append((source_field, source_field_row, raw))
    typed_citations.extend(
        (
            "component_responsibilities",
            source_field_row,
            {
                "quote": row["responsibility_quote"],
                "occurrence": row["responsibility_occurrence"],
            },
        )
        for source_field_row, row in enumerate(component_rows, start=1)
        if row["responsibility_quote"]
    )
    if len(typed_citations) > MAX_AUTHORED_CITATIONS:
        raise GreenfieldModelAuthoringError("Greenfield authoring returned invalid source citations; no records were created.")
    evidence = evidence_text.encode("utf-8")
    spans: list[dict[str, Any]] = []
    seen: dict[tuple[str, int, int], dict[str, Any]] = {}
    intent: dict[str, Any] = {field: "" for field in _TEXT_FIELDS}
    if normalized_actions:
        intent["prompt"] = evidence_text
    intent.update({field: [] for field in _LIST_FIELDS})
    try:
        intent["assumptions"] = assumption_rows(assumptions)
    except ValueError as exc:
        raise GreenfieldModelAuthoringError(str(exc)) from exc
    intent["ambiguities"] = _advisory_rows(ambiguities)
    selected_facts: list[dict[str, Any]] = []
    for citation_index, (source_field, source_field_row, raw) in enumerate(typed_citations, start=1):
        if source_field not in _SOURCE_REQUIRED_FIELDS:
            raise GreenfieldModelAuthoringError("Greenfield authoring returned invalid source citations; no records were created.")
        quote, start = resolve_source_citation(
            evidence, raw, state_object=source_field == "state_object"
        )
        quoted_bytes = quote.encode("utf-8")
        end = start + len(quoted_bytes)
        action = normalized_actions.get((source_field, source_field_row))
        display_quote = quote
        if action is not None:
            event_quote, event_start = resolve_source_citation(
                evidence,
                canonical_citation_from_host_selection(evidence, action["event_ref"]),
            )
            if quote != event_quote or start != event_start:
                raise GreenfieldModelAuthoringError(
                    "Greenfield verified action differs from its selected source citation"
                )
            display_quote = str(action["statement"])
            if not display_quote or len(display_quote) > MAX_AUTHORED_FIELD_VALUE_CHARS:
                raise GreenfieldModelAuthoringError(
                    "Greenfield verified action statement is invalid"
                )
        key = (source_field, start, end)
        if action is None and key in seen and source_field != "operational_constraints":
            # Duplicate collapse must not renumber model-authored references.
            seen[key]["source_field_rows"].append(source_field_row)
            continue
        projection_start = 0
        if source_field == "first_path":
            existing_path = str(intent[source_field])
            row_index = sum(1 for span in spans if span["section_key"] == source_field) + 1
            if row_index > MAX_AUTHORED_LIST_ITEMS:
                raise GreenfieldModelAuthoringError(
                    "Greenfield authoring exceeded the declared intent size; no records were created."
                )
            projection_start = len(existing_path.encode("utf-8")) + (1 if existing_path else 0)
            composed = f"{existing_path}\n{display_quote}" if existing_path else display_quote
            if len(composed) > MAX_AUTHORED_FIELD_VALUE_CHARS:
                raise GreenfieldModelAuthoringError(
                    "Greenfield authoring exceeded the declared intent size; no records were created."
                )
            intent[source_field] = composed
        elif source_field in _TEXT_FIELDS:
            intent[source_field] = display_quote
            row_index = sum(1 for span in spans if span["section_key"] == source_field) + 1
        else:
            rows = intent[source_field]
            assert isinstance(rows, list)
            if len(rows) >= MAX_AUTHORED_LIST_ITEMS:
                raise GreenfieldModelAuthoringError("Greenfield authoring exceeded the declared intent size; no records were created.")
            rows.append(display_quote)
            row_index = len(rows)
        projection_path = (
            f"/{source_field}" if source_field in _TEXT_FIELDS else f"/{source_field}/{row_index - 1}"
        )
        selected_facts.append(
            {
                "fact_index": citation_index,
                "field": source_field,
                "source_field_rows": [source_field_row],
                "quote": display_quote,
                **({"source_quote": quote} if action is not None else {}),
                "source_start_byte": start,
                "source_end_byte": end,
                "projection_path": projection_path,
                "projection_start_byte": projection_start,
                "projection_end_byte": projection_start + len(display_quote.encode("utf-8")),
                **({
                    "entailment_relationship": "verified_source_action",
                    "source_duty_id": action["id"],
                    "decision_set_sha256": action["decision_set_sha256"],
                    "verified_action": action["action"],
                    "verified_target": action["target"],
                    "source_event_order": action["event_order"],
                    "verified_actor": action["actor_ref"]["quote"],
                    "performer_role": action.get("performer_role"),
                } if action is not None else {}),
            }
        )
        seen[key] = selected_facts[-1]
        spans.append(
            {
                "span_id": f"authoring:{source_field}:{row_index}:{citation_index}",
                "section_key": source_field,
                "row_index": row_index,
                "classification": "product_claim",
                "text": quote,
                "source_start_byte": start,
                "source_end_byte": end,
                "projection_path": projection_path,
                "projection_start_byte": projection_start,
                "projection_end_byte": projection_start + len(display_quote.encode("utf-8")),
                "quote_sha256": hashlib.sha256(quoted_bytes).hexdigest(),
                **({
                    "entailment_relationship": "verified_source_action",
                    "source_duty_id": action["id"],
                    "decision_set_sha256": action["decision_set_sha256"],
                    "projection_text": display_quote,
                    "verified_action": action["action"],
                    "verified_target": action["target"],
                } if action is not None else {}),
            }
        )
    if not intent["title"] or not intent["first_path"]:
        raise GreenfieldModelAuthoringError(
            "Greenfield authoring could not establish the product and first complete path; no records were created."
        )
    try:
        require_decision_assumptions(intent)
        require_provisional_proof_decision(intent)
    except ValueError as exc:
        raise GreenfieldModelAuthoringError(str(exc)) from exc
    return intent, tuple(spans), tuple(selected_facts)


def _advisory_rows(value: Any) -> list[str]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or len(value) > MAX_AUTHORED_LIST_ITEMS
    ):
        raise GreenfieldModelAuthoringError("Greenfield authoring returned an invalid advisory list; no records were created.")
    return [_text(item) for item in value if _text(item)]


def greenfield_authoring_payload(evidence_text: str) -> dict[str, Any]:
    return {
        "version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "evidence": evidence_text,
    }


def bounded_greenfield_model_timeout(
    value: float | None, *, maximum_seconds: float
) -> float:
    if value is None:
        return maximum_seconds
    try:
        timeout = float(value)
    except (TypeError, ValueError) as exc:
        raise GreenfieldModelAuthoringError(
            "Greenfield model authoring received an invalid profile-bound timeout; no records were created."
        ) from exc
    if isinstance(value, bool) or not math.isfinite(timeout) or timeout <= 0:
        raise GreenfieldModelAuthoringError("Greenfield model authoring received an invalid timeout; no records were created.")
    return min(maximum_seconds, timeout)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) > MAX_AUTHORED_FIELD_VALUE_CHARS:
        raise GreenfieldModelAuthoringError("Greenfield authoring exceeded the declared intent size; no records were created.")
    return text


_CITATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["quote", "occurrence"],
    "properties": {
        "quote": {"type": "string", "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS},
        "occurrence": {"type": "integer", "minimum": 1},
    },
}

_STATE_CITATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["prefix", "quote", "anchor_occurrence"],
    "properties": {
        "quote": _CITATION_SCHEMA["properties"]["quote"],
        "prefix": _CITATION_SCHEMA["properties"]["quote"],
        "anchor_occurrence": _CITATION_SCHEMA["properties"]["occurrence"],
    },
}

_TYPED_FACTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [field for field in _SOURCE_FACT_FIELDS if field not in _OPTIONAL_SOURCE_FACT_FIELDS],
    "properties": {
        **{
            field: {"anyOf": [_CITATION_SCHEMA, {"type": "null"}]}
            for field in _SINGULAR_SOURCE_FIELDS
        },
        **{
            field: {
                "type": "array",
                "maxItems": MAX_AUTHORED_LIST_ITEMS,
                "items": _CITATION_SCHEMA,
            }
            for field in _REPEATED_SOURCE_FIELDS
        },
    },
}

_AUTHORED_FACTS_SCHEMA: dict[str, Any] = {
    **_TYPED_FACTS_SCHEMA,
    "properties": {
        **_TYPED_FACTS_SCHEMA["properties"],
        "title": {
            **_CITATION_SCHEMA,
            "description": TITLE_ROLE_DEFINITION,
        },
        "product_story": {
            **_CITATION_SCHEMA,
            "description": PRODUCT_STORY_ROLE_DEFINITION,
        },
        "state_object": {
            **_STATE_CITATION_SCHEMA,
            "description": STATE_OBJECT_ROLE_DEFINITION,
        },
        "proof_boundary": {
            "anyOf": [_CITATION_SCHEMA, {"type": "null"}],
            "description": PROOF_BOUNDARY_ROLE_DEFINITION,
        },
        "problem": {
            **_TYPED_FACTS_SCHEMA["properties"]["problem"],
            "description": (
                "A complete source statement of the user's unmet need or current "
                "difficulty, not the product name or a proposed capability. If the "
                "source does not state that need, use null and a problem assumption."
            ),
        },
        "opportunity": {
            **_TYPED_FACTS_SCHEMA["properties"]["opportunity"],
            "description": (
                "A complete source statement of the improvement or benefit worth "
                "pursuing, not an isolated workflow action. If that benefit is not "
                "stated, use null and an opportunity assumption."
            ),
        },
        "product_view": {
            **_TYPED_FACTS_SCHEMA["properties"]["product_view"],
            "description": (
                "A distinct complete source statement of the envisioned user "
                "experience: what a user can do or understand through the product. "
                "A title or product-category label is not an experience. If absent, "
                "use null and a product_view assumption."
            ),
        },
        "first_path": {
            **_TYPED_FACTS_SCHEMA["properties"]["first_path"],
            "minItems": 1,
        },
        "human_actors": {
            **_TYPED_FACTS_SCHEMA["properties"]["human_actors"],
            "description": HUMAN_ACTOR_ROLE_DEFINITION,
        },
        "internal_systems": {
            **_TYPED_FACTS_SCHEMA["properties"]["internal_systems"],
            "description": INTERNAL_SYSTEM_ROLE_DEFINITION,
        },
        "operational_constraints": {
            **_TYPED_FACTS_SCHEMA["properties"]["operational_constraints"],
            "description": OPERATIONAL_CONSTRAINT_ROLE_DEFINITION,
        },
        "external_systems": {
            **_TYPED_FACTS_SCHEMA["properties"]["external_systems"],
            "description": (
                "Only an explicitly source-stated operational exchange or dependency between this "
                "product and a named external system, service, authority, organization, or data "
                "source. Merely naming task data, an output recipient, or a reviewer does not "
                "establish that connection."
            ),
        },
        "customer": {
            **_TYPED_FACTS_SCHEMA["properties"]["customer"],
            "description": (
                "The source-stated direct user or primary beneficiary. If no such "
                "participant is named, use null and one customer assumption; do "
                "not turn an activity or output purpose into a person."
            ),
        },
    },
}

_ADVISORY_SCHEMA: dict[str, Any] = {
    "type": "array",
    "maxItems": MAX_AUTHORED_LIST_ITEMS,
    "items": {"type": "string", "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS},
}


def _consistency_schema(*, statuses: Sequence[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "evidence_quotes"],
        "properties": {
            "status": {"type": "string", "enum": list(statuses)},
            "evidence_quotes": {
                "type": "array",
                "maxItems": 4,
                "description": (
                    "Use an empty array for consistent or material_ambiguity; the compiler "
                    "binds missingness to the complete evidence. For non_material_ambiguity "
                    "or material_contradiction, return two to four exact source excerpts."
                ),
                "items": {
                    "type": "string",
                    "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS,
                },
            },
        },
    }


_AUTHORED_RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "status",
        "facts",
        "events",
        "terminal",
        "components",
        "assumptions",
        "ambiguities",
        "consistency",
        "provisional_design",
        "source_precedence",
    ],
    "properties": {
        "status": {"type": "string", "enum": ["authored"]},
        "facts": _AUTHORED_FACTS_SCHEMA,
        "events": MODEL_EVENT_SCHEMA,
        "terminal": MODEL_TERMINAL_SCHEMA,
        "components": MODEL_COMPONENT_SCHEMA,
        "assumptions": ASSUMPTION_SCHEMA,
        "ambiguities": _ADVISORY_SCHEMA,
        "provisional_design": PROVISIONAL_DESIGN_SCHEMA,
        "source_precedence": SOURCE_PRECEDENCE_SCHEMA,
        "consistency": _consistency_schema(
            statuses=("consistent", "non_material_ambiguity")
        ),
    },
}

_CLARIFICATION_RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["status", "consistency", "clarification"],
    "properties": {
        "status": {"type": "string", "enum": ["clarification_required"]},
        "consistency": _consistency_schema(
            statuses=("material_ambiguity", "material_contradiction")
        ),
        "clarification": {
            "type": "object",
            "additionalProperties": False,
            "required": ["material_dimension"],
            "properties": {
                "material_dimension": {
                    "type": "string",
                    "enum": sorted(MATERIAL_DIMENSIONS),
                    "description": MATERIALITY_DECISION_CONTRACT,
                },
            },
        },
    },
}

_AUTHORING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["version", "result"],
    "properties": {
        "version": {"type": "string", "enum": [GREENFIELD_INTENT_AUTHORING_VERSION]},
        "result": {
            "anyOf": [_AUTHORED_RESULT_SCHEMA, _CLARIFICATION_RESULT_SCHEMA]
        },
    },
}


def greenfield_authoring_schema(*, source_event_graph: bool = False) -> dict[str, Any]:
    """Return an isolated copy of the complete canonical response schema."""

    schema = deepcopy(_AUTHORING_SCHEMA)
    if source_event_graph:
        events = schema["properties"]["result"]["anyOf"][0]["properties"]["events"]
        events["maxItems"] = MAX_SOURCE_EVENT_RELATIONS
        events["items"]["properties"]["actor_fact"]["properties"]["field"]["enum"] = [
            "human_actors", "internal_systems", "external_systems", "product_identity",
        ]
    return schema


__all__ = [
    "GREENFIELD_INTENT_AUTHORING_VERSION",
    "GreenfieldAuthoringClarification",
    "GreenfieldModelAuthoredIntent",
    "GreenfieldModelAuthoringError",
    "authoring_tier",
    "bounded_greenfield_model_timeout",
    "greenfield_authoring_payload",
    "greenfield_authoring_schema",
    "validate_greenfield_authoring_response",
]
