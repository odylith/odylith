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
from odylith.runtime.domain_intelligence.greenfield_candidate_review import (
    HUMAN_ACTOR_ROLE_DEFINITION,
    INTERNAL_SYSTEM_ROLE_DEFINITION,
    OPERATIONAL_CONSTRAINT_ROLE_DEFINITION,
    PRODUCT_STORY_ROLE_DEFINITION,
    PROOF_BOUNDARY_ROLE_DEFINITION,
    STATE_OBJECT_ROLE_DEFINITION,
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

GREENFIELD_INTENT_AUTHORING_VERSION = "odylith.greenfield.intent-authoring.v71"
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
    participant_selection: dict[str, Any] = field(default_factory=dict)
    remaining_candidate_authoring: dict[str, Any] = field(default_factory=dict)
    candidate_review: dict[str, Any] = field(default_factory=dict)
    semantic_model_call_count: int = 0


@dataclass(frozen=True)
class GreenfieldModelAuthoredIntent:
    """Verified pre-confirm facts and the source spans that justify them."""

    intent: dict[str, Any]
    first_path_relations: tuple[dict[str, Any], ...]
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
    participant_selection: dict[str, Any] = field(default_factory=dict)
    remaining_candidate_authoring: dict[str, Any] = field(default_factory=dict)
    semantic_model_call_count: int = 0
    candidate_review: dict[str, Any] = field(default_factory=dict)
    candidate_revision: dict[str, Any] = field(default_factory=dict)
    rejected_candidate_review: dict[str, Any] = field(default_factory=dict)


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
        component_rows = model_component_responsibility_rows(
            result.get("components")
        )
        intent, source_spans, selected_facts = _intent_from_typed_source_spans(
            result.get("facts"),
            component_rows=component_rows,
            evidence_text=evidence_text,
            assumptions=result.get("assumptions"),
            ambiguities=result.get("ambiguities"),
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
        )
        authored_component_relation_facts(
            title=str(intent.get("title") or ""),
            internal_systems=tuple(str(row) for row in intent.get("internal_systems", ())),
            relations=derived_relations.first_path_relations,
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
            first_path_relations=derived_relations.first_path_relations,
            terminal_result_fact=derived_relations.terminal_result_fact,
        )
    except GreenfieldAuthoredSemanticsError as exc:
        raise GreenfieldModelAuthoringError(f"{exc}; no records were created.") from exc
    tier = authoring_tier(profile_id)
    try:
        event_orders = [row["order"] for row in derived_relations.first_path_relations]
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
                    for row in derived_relations.first_path_relations
                    if row["visible_result_quote"]
                ),
                None,
            ),
        )
    except ValueError as exc:
        raise GreenfieldModelAuthoringError(f"{exc}; no records were created.") from exc
    return GreenfieldModelAuthoredIntent(
        intent=intent,
        first_path_relations=derived_relations.first_path_relations,
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


def _intent_from_typed_source_spans(
    value: Any,
    *,
    component_rows: Sequence[Mapping[str, Any]],
    evidence_text: str,
    assumptions: Any,
    ambiguities: Any,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    """Compile canonical facts from exact quotes and their source occurrences.

    The model selects the source address; deterministic resolution supplies exact
    coordinates and hashes. State objects use a split anchor without changing
    the projected semantic quote or borrowing the prefix's meaning.
    """

    if not isinstance(value, Mapping) or set(value) != set(_SOURCE_FACT_FIELDS):
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
        key = (source_field, start, end)
        if key in seen and source_field != "operational_constraints":
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
            composed = f"{existing_path}\n{quote}" if existing_path else quote
            if len(composed) > MAX_AUTHORED_FIELD_VALUE_CHARS:
                raise GreenfieldModelAuthoringError(
                    "Greenfield authoring exceeded the declared intent size; no records were created."
                )
            intent[source_field] = composed
        elif source_field in _TEXT_FIELDS:
            intent[source_field] = quote
            row_index = sum(1 for span in spans if span["section_key"] == source_field) + 1
        else:
            rows = intent[source_field]
            assert isinstance(rows, list)
            if len(rows) >= MAX_AUTHORED_LIST_ITEMS:
                raise GreenfieldModelAuthoringError("Greenfield authoring exceeded the declared intent size; no records were created.")
            rows.append(quote)
            row_index = len(rows)
        projection_path = (
            f"/{source_field}" if source_field in _TEXT_FIELDS else f"/{source_field}/{row_index - 1}"
        )
        selected_facts.append(
            {
                "fact_index": citation_index,
                "field": source_field,
                "source_field_rows": [source_field_row],
                "quote": quote,
                "source_start_byte": start,
                "source_end_byte": end,
                "projection_path": projection_path,
                "projection_start_byte": projection_start,
                "projection_end_byte": projection_start + len(quoted_bytes),
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
                "projection_end_byte": projection_start + len(quoted_bytes),
                "quote_sha256": hashlib.sha256(quoted_bytes).hexdigest(),
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
    "required": list(_SOURCE_FACT_FIELDS),
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
        "title": _CITATION_SCHEMA,
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


def greenfield_authoring_schema() -> dict[str, Any]:
    """Return an isolated copy of the complete canonical response schema."""

    return deepcopy(_AUTHORING_SCHEMA)


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
