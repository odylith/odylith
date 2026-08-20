"""Atomic critic evidence and author binding for Greenfield semantic custody."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_schema import (
    semantic_source_claims_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    require_semantic_source_refs,
    semantic_source_ref_schema,
    semantic_source_refs_overlap,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_claims import (
    SEMANTIC_SOURCE_CLAIMS_VERSION,
    require_semantic_source_claims,
)


ATOMIC_SOURCE_CANDIDATES_VERSION = (
    "odylith.greenfield.semantic-atomic-source-candidates.v2"
)
ATOMIC_SOURCE_ADJUDICATION_VERSION = (
    "odylith.greenfield.semantic-atomic-source-adjudication.v1"
)
_DECISIONS = frozenset({"retain", "reject_overcapture", "reject_noise"})
_FACT_FIELDS = {
    "identity": "identity",
    "actor": "role",
    "workflow_step": "first_path",
    "state_object": "state_object",
    "visible_output": "visible_result",
    "external_system": "dependency",
    "internal_system": "component_boundary",
    "component_responsibility": "component_boundary",
    "operational_constraint": "constraint",
    "non_goal": "non_goal",
}
_RELATION_FIELDS = {
    "owned_by": ("role", "first_path"),
    "produces": ("first_path", "visible_result"),
    "changes": ("first_path", "state_object"),
    "depends_on": ("dependency",),
    "implements": ("component_boundary", "first_path"),
    "constrained_by": ("constraint",),
    "excludes": ("non_goal",),
}


def atomic_source_custody_contract() -> dict[str, Any]:
    """Return the sole critic-to-author custody boundary."""

    return {
        "critic_authority": "exact_evidence_spans_only",
        "critic_forbidden_authority": [
            "semantic_kind",
            "canonical_field",
            "ownership",
            "relation",
            "product_identity",
        ],
        "graph_author_authority": "candidate_semantic_hypothesis_only",
        "accepted_truth_boundary": "deterministic_source_claim_validation",
        "required_candidate_coverage": "every_candidate_decided_exactly_once",
        "required_graph_coverage": "every_source_fact_and_relation_bound_to_a_retained_candidate",
        "citation_match": "exact_source_ref",
        "rejected_candidate_binding_allowed": False,
        "regex_fuzzy_or_token_semantic_authority_allowed": False,
    }


def atomic_source_candidates_schema(
    *, source_ref_schema: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Return the critic schema for exact atomic evidence candidates."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["version", "candidates"],
        "properties": {
            "version": {
                "type": "string",
                "enum": [ATOMIC_SOURCE_CANDIDATES_VERSION],
            },
            "candidates": {
                "type": "array",
                "minItems": 1,
                "maxItems": 128,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["candidate_id", "source_ref"],
                    "properties": {
                        "candidate_id": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 100,
                        },
                        "source_ref": dict(
                            source_ref_schema or semantic_source_ref_schema()
                        ),
                    },
                },
            },
        },
    }


def atomic_source_candidates_from_catalog(
    catalog: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind every provider-locked evidence block without assigning semantic meaning."""

    if not catalog:
        raise ValueError("atomic source candidate catalog is empty")
    return {
        "version": ATOMIC_SOURCE_CANDIDATES_VERSION,
        "candidates": [
            {"candidate_id": f"candidate.{index}", "source_ref": dict(source_ref)}
            for index, source_ref in enumerate(catalog.values())
        ],
    }


def atomic_source_candidates_without_discarded(
    value: Any,
    *,
    discarded_source_refs: Sequence[Mapping[str, Any]],
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Remove candidates overlapping exact discarded evidence spans."""

    candidates = require_atomic_source_candidates(
        value, evidence_sources=evidence_sources
    )
    discarded = require_semantic_source_refs(
        discarded_source_refs,
        evidence_sources=evidence_sources,
        allow_empty=True,
        maximum=128,
    )
    retained = [
        row for row in candidates["candidates"]
        if not any(
            semantic_source_refs_overlap(
                row["source_ref"], discarded_ref,
                evidence_sources=evidence_sources,
            )
            for discarded_ref in discarded
        )
    ]
    if not retained:
        raise ValueError("discarded evidence removes every atomic source candidate")
    return {"version": ATOMIC_SOURCE_CANDIDATES_VERSION, "candidates": retained}


def atomic_source_adjudication_schema() -> dict[str, Any]:
    """Return the author-to-verifier binding schema."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["version", "candidate_decisions", "source_claims"],
        "properties": {
            "version": {
                "type": "string",
                "enum": [ATOMIC_SOURCE_ADJUDICATION_VERSION],
            },
            "candidate_decisions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 128,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "candidate_id",
                        "decision",
                        "fact_ids",
                        "relation_ids",
                    ],
                    "properties": {
                        "candidate_id": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 100,
                        },
                        "decision": {
                            "type": "string",
                            "enum": sorted(_DECISIONS),
                        },
                        "fact_ids": _id_array(),
                        "relation_ids": _id_array(),
                    },
                },
            },
            "source_claims": semantic_source_claims_schema(),
        },
    }


def require_atomic_source_candidates(
    value: Any,
    *,
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Validate exact candidate identity and source citations."""

    row = _mapping(value, "atomic source candidates")
    _exact_keys(row, {"version", "candidates"}, "atomic source candidates")
    if row.get("version") != ATOMIC_SOURCE_CANDIDATES_VERSION:
        raise ValueError("atomic source candidates use an unsupported version")
    normalized: list[dict[str, Any]] = []
    ids: set[str] = set()
    source_refs: set[tuple[str, str, int]] = set()
    for raw in _sequence(row.get("candidates"), 128, "atomic source candidates"):
        candidate = _mapping(raw, "atomic source candidate")
        _exact_keys(candidate, {"candidate_id", "source_ref"}, "atomic source candidate")
        candidate_id = _identifier(candidate.get("candidate_id"), "candidate id")
        if candidate_id in ids:
            raise ValueError("atomic source candidate ids are not unique")
        ids.add(candidate_id)
        source_ref = require_semantic_source_refs(
            [candidate.get("source_ref")],
            evidence_sources=evidence_sources,
            allow_empty=False,
        )[0]
        source_ref_key = (
            str(source_ref["source_id"]),
            str(source_ref["quote"]),
            int(source_ref["occurrence"]),
        )
        if source_ref_key in source_refs:
            continue
        source_refs.add(source_ref_key)
        normalized.append({
            "candidate_id": candidate_id,
            "source_ref": source_ref,
        })
    if not normalized:
        raise ValueError("atomic source candidates are empty")
    return {"version": ATOMIC_SOURCE_CANDIDATES_VERSION, "candidates": normalized}


def select_atomic_source_claims(
    candidates_value: Any,
    adjudication_value: Any,
    *,
    evidence_sources: Mapping[str, str],
    settled_fields: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify every candidate decision and return the selected source graph."""

    candidates = require_atomic_source_candidates(
        candidates_value,
        evidence_sources=evidence_sources,
    )
    candidate_index = {
        row["candidate_id"]: row for row in candidates["candidates"]
    }
    adjudication = _mapping(adjudication_value, "atomic source adjudication")
    _exact_keys(
        adjudication,
        {"version", "candidate_decisions", "source_claims"},
        "atomic source adjudication",
    )
    if adjudication.get("version") != ATOMIC_SOURCE_ADJUDICATION_VERSION:
        raise ValueError("atomic source adjudication uses an unsupported version")
    source_claims = require_semantic_source_claims(
        adjudication.get("source_claims"),
        evidence_sources=evidence_sources,
        settled_fields=settled_fields,
    )
    fact_index = {
        str(row["fact"]["fact_id"]): row["fact"]
        for row in source_claims["facts"]
    }
    relation_index = {
        str(row["relation"]["relation_id"]): row["relation"]
        for row in source_claims["relations"]
    }
    decisions: list[dict[str, Any]] = []
    decided: set[str] = set()
    bound_fact_ids: set[str] = set()
    bound_relation_ids: set[str] = set()
    for raw in _sequence(
        adjudication.get("candidate_decisions"),
        128,
        "atomic source candidate decisions",
    ):
        decision = _mapping(raw, "atomic source candidate decision")
        _exact_keys(
            decision,
            {"candidate_id", "decision", "fact_ids", "relation_ids"},
            "atomic source candidate decision",
        )
        candidate_id = _identifier(decision.get("candidate_id"), "candidate decision id")
        if candidate_id not in candidate_index or candidate_id in decided:
            raise ValueError("atomic source candidate decisions are incomplete or duplicated")
        decided.add(candidate_id)
        kind = _enum(decision.get("decision"), _DECISIONS, "candidate decision")
        fact_ids = _unique_ids(decision.get("fact_ids"), "candidate fact ids")
        relation_ids = _unique_ids(decision.get("relation_ids"), "candidate relation ids")
        candidate = candidate_index[candidate_id]
        if kind == "retain":
            if not fact_ids and not relation_ids:
                raise ValueError("retained atomic candidate has no typed binding")
            if any(fact_id not in fact_index for fact_id in fact_ids):
                raise ValueError("atomic candidate references an unknown source fact")
            if any(relation_id not in relation_index for relation_id in relation_ids):
                raise ValueError("atomic candidate references an unknown source relation")
            for row in (
                *(fact_index[fact_id] for fact_id in fact_ids),
                *(relation_index[relation_id] for relation_id in relation_ids),
            ):
                if candidate["source_ref"] not in row["source_refs"]:
                    raise ValueError("atomic candidate binding changes its exact source citation")
            bound_fact_ids.update(fact_ids)
            bound_relation_ids.update(relation_ids)
        elif fact_ids or relation_ids:
            raise ValueError("rejected atomic candidate still binds product truth")
        decisions.append({
            "candidate_id": candidate_id,
            "decision": kind,
            "fact_ids": fact_ids,
            "relation_ids": relation_ids,
        })
    if decided != set(candidate_index):
        raise ValueError("atomic source candidate decisions do not cover every candidate")
    if bound_fact_ids != set(fact_index) or bound_relation_ids != set(relation_index):
        raise ValueError("selected source graph contains an unbound fact or relation")
    return (
        {
            "version": ATOMIC_SOURCE_ADJUDICATION_VERSION,
            "candidate_decisions": decisions,
            "source_claims": source_claims,
        },
        source_claims,
    )


def build_atomic_source_adjudication(
    candidates_value: Any,
    *,
    facts: Sequence[tuple[Mapping[str, Any], Sequence[str]]],
    relations: Sequence[tuple[Mapping[str, Any], Sequence[str]]],
    evidence_sources: Mapping[str, str],
    settled_fields: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the sole source-candidate decision set from source-owned typed rows."""

    candidates = require_atomic_source_candidates(
        candidates_value,
        evidence_sources=evidence_sources,
    )
    candidate_ids = {
        str(row["candidate_id"]) for row in candidates["candidates"]
    }
    bound_fact_ids: dict[str, list[str]] = {
        candidate_id: [] for candidate_id in candidate_ids
    }
    bound_relation_ids: dict[str, list[str]] = {
        candidate_id: [] for candidate_id in candidate_ids
    }
    source_facts: list[dict[str, Any]] = []
    source_relations: list[dict[str, Any]] = []
    for raw, raw_candidate_ids in facts:
        fact = dict(raw)
        kind = str(fact.get("kind") or "")
        field = _FACT_FIELDS.get(kind)
        if field is None:
            raise ValueError("source fact kind has no canonical materiality field")
        fact_id = _identifier(fact.get("fact_id"), "source fact id")
        ids = _bound_candidate_ids(raw_candidate_ids, candidate_ids)
        for candidate_id in ids:
            bound_fact_ids[candidate_id].append(fact_id)
        source_facts.append({"field": field, "fact": fact})
    settled = set(settled_fields)
    for raw, raw_candidate_ids in relations:
        relation = dict(raw)
        kind = str(relation.get("kind") or "")
        candidate_fields = _RELATION_FIELDS.get(kind)
        if candidate_fields is None:
            raise ValueError("source relation kind has no canonical materiality field")
        fields = [field for field in candidate_fields if field in settled]
        if not fields:
            raise ValueError("source relation has no settled materiality field")
        relation_id = _identifier(
            relation.get("relation_id"), "source relation id"
        )
        ids = _bound_candidate_ids(raw_candidate_ids, candidate_ids)
        for candidate_id in ids:
            bound_relation_ids[candidate_id].append(relation_id)
        source_relations.append({"fields": fields, "relation": relation})
    adjudication = {
        "version": ATOMIC_SOURCE_ADJUDICATION_VERSION,
        "candidate_decisions": [
            {
                "candidate_id": candidate_id,
                "decision": (
                    "retain"
                    if bound_fact_ids[candidate_id]
                    or bound_relation_ids[candidate_id]
                    else "reject_noise"
                ),
                "fact_ids": bound_fact_ids[candidate_id],
                "relation_ids": bound_relation_ids[candidate_id],
            }
            for candidate_id in (
                str(row["candidate_id"]) for row in candidates["candidates"]
            )
        ],
        "source_claims": {
            "version": SEMANTIC_SOURCE_CLAIMS_VERSION,
            "facts": source_facts,
            "relations": source_relations,
        },
    }
    return select_atomic_source_claims(
        candidates,
        adjudication,
        evidence_sources=evidence_sources,
        settled_fields=settled_fields,
    )


def validated_atomic_source_claims(
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Recover already sealed source claims without interpreting source prose."""

    assessment = _mapping(
        authority.get("semantic_materiality_assessment"),
        "semantic materiality assessment",
    )
    evidence_sources = _mapping(authority.get("evidence_sources"), "evidence sources")
    fields = _sequence(assessment.get("fields"), 32, "materiality fields")
    settled_fields = {
        str(_mapping(row, "materiality field").get("field")): _mapping(
            row, "materiality field"
        )
        for row in fields
    }
    _, source_claims = select_atomic_source_claims(
        assessment.get("source_candidates"),
        authority.get("semantic_source_candidate_adjudication"),
        evidence_sources={key: str(value) for key, value in evidence_sources.items()},
        settled_fields=settled_fields,
    )
    return source_claims


def _id_array() -> dict[str, Any]:
    return {
        "type": "array",
        "maxItems": 128,
        "items": {"type": "string", "minLength": 1, "maxLength": 100},
    }


def _bound_candidate_ids(
    value: Sequence[str], allowed: set[str]
) -> list[str]:
    rows = [_identifier(item, "source candidate id") for item in value]
    if not rows or len(rows) != len(set(rows)) or any(row not in allowed for row in rows):
        raise ValueError("source candidate bindings are invalid")
    return rows


def _unique_ids(value: Any, label: str) -> list[str]:
    rows = [_identifier(item, label) for item in _sequence(value, 128, label)]
    if len(rows) != len(set(rows)):
        raise ValueError(f"{label} are not unique")
    return rows


def _identifier(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 100:
        raise ValueError(f"{label} is invalid")
    return text


def _enum(value: Any, allowed: set[str] | frozenset[str], label: str) -> str:
    text = str(value or "")
    if text not in allowed:
        raise ValueError(f"{label} is unsupported")
    return text


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return dict(value)


def _sequence(value: Any, maximum: int, label: str) -> list[Any]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or len(value) > maximum
    ):
        raise ValueError(f"{label} must be a bounded JSON array")
    return list(value)


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} fields do not match the versioned contract")


__all__ = [
    "ATOMIC_SOURCE_ADJUDICATION_VERSION",
    "ATOMIC_SOURCE_CANDIDATES_VERSION",
    "atomic_source_custody_contract",
    "atomic_source_adjudication_schema",
    "atomic_source_candidates_from_catalog",
    "atomic_source_candidates_without_discarded",
    "atomic_source_candidates_schema",
    "require_atomic_source_candidates",
    "select_atomic_source_claims",
    "validated_atomic_source_claims",
]
