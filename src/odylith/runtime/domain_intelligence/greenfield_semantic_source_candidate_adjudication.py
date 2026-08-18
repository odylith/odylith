"""Adjudicate locked workflow candidates without inventing source semantics."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_source_claims import (
    SEMANTIC_SOURCE_CANDIDATES_VERSION,
    SEMANTIC_SOURCE_CLAIMS_VERSION,
)


SEMANTIC_SOURCE_CANDIDATE_ADJUDICATION_VERSION = (
    "odylith.greenfield.semantic-source-candidate-adjudication.v1"
)
SEMANTIC_MATERIAL_EFFECTS = (
    "accepts_or_selects_input",
    "mutates_domain_object",
    "routes_or_transfers_domain_object",
    "records_or_creates_domain_evidence",
    "evaluates_or_decides",
    "coordinates_or_approves",
    "configures_or_executes",
    "reads_or_inspects_dependency",
    "communicates_or_notifies",
)
_DECISIONS = {
    "retain_material_action",
    "fold_into_visible_result",
    "fold_into_state_object",
}
_MATERIAL_RELATIONS = {
    "changes",
    "produces",
    "depends_on",
    "constrained_by",
    "excludes",
}


def semantic_source_candidate_adjudication_contract() -> dict[str, Any]:
    """Return the narrow authority boundary for source workflow candidates."""

    return {
        "candidate_authority": "critic_locked_source_candidates",
        "decision_owner": "existing_independent_bounded_graph_author",
        "decisions": {
            "retain_material_action": (
                "candidate has an independent typed material effect beyond perceiving a result"
            ),
            "fold_into_visible_result": (
                "candidate only restates consumer perception of one locked visible result"
            ),
            "fold_into_state_object": (
                "candidate only restates one locked state transition"
            ),
        },
        "material_effects": list(SEMANTIC_MATERIAL_EFFECTS),
        "graph_assembly": "deterministic_selection_and_reindexing",
        "forbidden": [
            "new_source_fact",
            "new_source_relation",
            "source_text_rewrite",
            "regex_or_token_role_inference",
            "validator_guided_retry",
            "third_model_call",
        ],
    }


def semantic_source_candidate_adjudication_schema(
    source_candidates: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a provider schema limited to existing workflow candidate ids."""

    facts = _fact_index(source_candidates) if source_candidates is not None else {}
    workflow_ids = sorted(
        fact_id for fact_id, fact in facts.items() if fact.get("kind") == "workflow_step"
    )
    output_ids = sorted(
        fact_id for fact_id, fact in facts.items() if fact.get("kind") == "visible_output"
    )
    state_ids = sorted(
        fact_id for fact_id, fact in facts.items() if fact.get("kind") == "state_object"
    )
    variants: list[dict[str, Any]] = [
        _decision_schema(
            workflow_ids,
            decision="retain_material_action",
            extra_name="material_effect",
            values=list(SEMANTIC_MATERIAL_EFFECTS),
        )
    ]
    if output_ids or source_candidates is None:
        variants.append(
            _decision_schema(
                workflow_ids,
                decision="fold_into_visible_result",
                extra_name="target_fact_id",
                values=output_ids or None,
            )
        )
    if state_ids or source_candidates is None:
        variants.append(
            _decision_schema(
                workflow_ids,
                decision="fold_into_state_object",
                extra_name="target_fact_id",
                values=state_ids or None,
            )
        )
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["version", "workflow_decisions"],
        "properties": {
            "version": {
                "type": "string",
                "enum": [SEMANTIC_SOURCE_CANDIDATE_ADJUDICATION_VERSION],
            },
            "workflow_decisions": {
                "type": "array",
                "minItems": len(workflow_ids) if source_candidates is not None else 0,
                "maxItems": len(workflow_ids) if source_candidates is not None else 128,
                "items": {"anyOf": variants},
            },
        },
    }


def require_semantic_source_candidate_adjudication(
    value: Any,
    *,
    source_candidates: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one exact decision for every locked workflow candidate."""

    row = _mapping(value, "Semantic source candidate adjudication")
    _exact_keys(
        row,
        {"version", "workflow_decisions"},
        "Semantic source candidate adjudication",
    )
    if row.get("version") != SEMANTIC_SOURCE_CANDIDATE_ADJUDICATION_VERSION:
        raise ValueError("Semantic source candidate adjudication uses an unsupported version")
    facts = _fact_index(source_candidates)
    relations = _relation_rows(source_candidates)
    expected_ids = {
        fact_id for fact_id, fact in facts.items() if fact.get("kind") == "workflow_step"
    }
    decisions = _sequence(row.get("workflow_decisions"), 128, "workflow decisions")
    normalized = []
    decided_ids: set[str] = set()
    for raw in decisions:
        decision = _mapping(raw, "Semantic workflow candidate decision")
        kind = _enum(decision.get("decision"), _DECISIONS, "workflow decision")
        expected_keys = {"fact_id", "decision"}
        expected_keys.add("material_effect" if kind == "retain_material_action" else "target_fact_id")
        _exact_keys(decision, expected_keys, "Semantic workflow candidate decision")
        fact_id = _identifier(decision.get("fact_id"), "workflow candidate id")
        if fact_id not in expected_ids or fact_id in decided_ids:
            raise ValueError("Semantic workflow candidate decisions are incomplete or duplicated")
        decided_ids.add(fact_id)
        normalized_row = {"fact_id": fact_id, "decision": kind}
        if kind == "retain_material_action":
            normalized_row["material_effect"] = _enum(
                decision.get("material_effect"),
                set(SEMANTIC_MATERIAL_EFFECTS),
                "workflow material effect",
            )
        else:
            target_id = _identifier(decision.get("target_fact_id"), "fold target fact id")
            expected_kind = (
                "visible_output" if kind == "fold_into_visible_result" else "state_object"
            )
            target = facts.get(target_id)
            if target is None or target.get("kind") != expected_kind:
                raise ValueError("Semantic workflow fold target has the wrong fact kind")
            _require_fold_custody(
                fact_id=fact_id,
                target_id=target_id,
                facts=facts,
                relations=relations,
            )
            normalized_row["target_fact_id"] = target_id
        normalized.append(normalized_row)
    if decided_ids != expected_ids:
        raise ValueError("Semantic workflow candidate decisions do not cover locked candidates")
    normalized.sort(key=lambda item: int(facts[item["fact_id"]].get("order", 0)))
    return {
        "version": SEMANTIC_SOURCE_CANDIDATE_ADJUDICATION_VERSION,
        "workflow_decisions": normalized,
    }


def select_semantic_source_claims(
    source_candidates: Mapping[str, Any],
    adjudication: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate candidate decisions and project the sole final source claims."""

    selected = require_semantic_source_candidate_adjudication(
        adjudication,
        source_candidates=source_candidates,
    )
    return selected, _adjudicated_semantic_source_claims(source_candidates, selected)


def _adjudicated_semantic_source_claims(
    source_candidates: Mapping[str, Any],
    adjudication: Mapping[str, Any],
) -> dict[str, Any]:
    """Project retained source rows after validation; never author or rewrite one."""

    decisions = {
        str(row["fact_id"]): str(row["decision"])
        for row in adjudication.get("workflow_decisions", ())
    }
    removed = {fact_id for fact_id, decision in decisions.items() if decision != "retain_material_action"}
    fact_rows = [
        {"field": row["field"], "fact": dict(row["fact"])}
        for row in source_candidates.get("facts", ())
        if str(row["fact"]["fact_id"]) not in removed
    ]
    relation_rows = [
        {"fields": list(row["fields"]), "relation": dict(row["relation"])}
        for row in source_candidates.get("relations", ())
        if not removed
        & {
            str(row["relation"]["subject_id"]),
            str(row["relation"]["object_id"]),
        }
    ]
    _reindex_rows((row["fact"] for row in fact_rows), id_key="fact_id")
    _reindex_rows((row["relation"] for row in relation_rows), id_key="relation_id")
    return {
        "version": SEMANTIC_SOURCE_CLAIMS_VERSION,
        "facts": fact_rows,
        "relations": relation_rows,
    }


def selected_semantic_source_claims(
    assessment: Mapping[str, Any],
    adjudication: Any,
) -> dict[str, Any]:
    """Resolve the sole final source claims from validated authority inputs."""

    source_candidates = _mapping(
        assessment.get("source_candidates"),
        "Semantic source candidates",
    )
    _, claims = select_semantic_source_claims(
        source_candidates,
        adjudication,
    )
    return claims


def _require_fold_custody(
    *,
    fact_id: str,
    target_id: str,
    facts: Mapping[str, Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
) -> None:
    candidate_refs = facts[fact_id].get("source_refs", ())
    target_refs = facts[target_id].get("source_refs", ())
    if not any(ref in target_refs for ref in candidate_refs):
        raise ValueError("Semantic workflow fold lacks shared exact source custody")
    for relation in relations:
        if relation.get("subject_id") != fact_id or relation.get("kind") not in _MATERIAL_RELATIONS:
            continue
        if relation.get("object_id") != target_id:
            raise ValueError("Semantic workflow fold would discard an independent material relation")


def _fact_index(source_candidates: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if source_candidates.get("version") != SEMANTIC_SOURCE_CANDIDATES_VERSION:
        raise ValueError("Semantic source candidates use an unsupported version")
    rows = _sequence(source_candidates.get("facts"), 128, "source candidate facts")
    result: dict[str, Mapping[str, Any]] = {}
    for raw in rows:
        wrapper = _mapping(raw, "Semantic source candidate fact wrapper")
        fact = _mapping(wrapper.get("fact"), "Semantic source candidate fact")
        fact_id = _identifier(fact.get("fact_id"), "source candidate fact id")
        if fact_id in result:
            raise ValueError("Semantic source candidate fact ids are not unique")
        result[fact_id] = fact
    return result


def _relation_rows(source_candidates: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        _mapping(_mapping(row, "Semantic source relation wrapper").get("relation"), "Semantic source relation")
        for row in _sequence(
            source_candidates.get("relations"),
            256,
            "source candidate relations",
        )
    ]


def _reindex_rows(rows: Sequence[Mapping[str, Any]] | Any, *, id_key: str) -> None:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["kind"]), []).append(row)
    for kind_rows in grouped.values():
        kind_rows.sort(key=lambda row: (int(row.get("order", 0)), str(row[id_key])))
        for order, row in enumerate(kind_rows):
            row["order"] = order


def _decision_schema(
    fact_ids: Sequence[str],
    *,
    decision: str,
    extra_name: str,
    values: Sequence[str] | None,
) -> dict[str, Any]:
    fact_id_schema = (
        {"type": "string", "enum": list(fact_ids)}
        if fact_ids
        else {"type": "string", "minLength": 1, "maxLength": 100}
    )
    extra_schema = (
        {"type": "string", "enum": list(values)}
        if values
        else {"type": "string", "minLength": 1, "maxLength": 100}
    )
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["fact_id", "decision", extra_name],
        "properties": {
            "fact_id": fact_id_schema,
            "decision": {"type": "string", "enum": [decision]},
            extra_name: extra_schema,
        },
    }


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > 100:
        raise ValueError(f"Semantic {label} is malformed")
    return value


def _enum(value: Any, allowed: set[str], label: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"Semantic {label} is invalid")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} is malformed")
    return value


def _sequence(value: Any, maximum: int, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"Semantic {label} is malformed")
    rows = list(value)
    if len(rows) > maximum:
        raise ValueError(f"Semantic {label} exceeds its operating limit")
    return rows


def _exact_keys(value: Mapping[str, Any], keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise ValueError(f"{label} has unsupported or missing fields")


__all__ = [
    "SEMANTIC_MATERIAL_EFFECTS",
    "SEMANTIC_SOURCE_CANDIDATE_ADJUDICATION_VERSION",
    "require_semantic_source_candidate_adjudication",
    "select_semantic_source_claims",
    "selected_semantic_source_claims",
    "semantic_source_candidate_adjudication_contract",
    "semantic_source_candidate_adjudication_schema",
]
