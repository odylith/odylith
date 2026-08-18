"""Assemble bounded graph-author additions around locked source claims."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_IR_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    bind_semantic_intent_source_ref_selections,
    semantic_intent_output_schema_for_materiality,
)


SEMANTIC_GRAPH_EXTENSION_VERSION = "odylith.greenfield.semantic-graph-extension.v1"
_FIELD_FACT_KIND = {
    "identity": "identity",
    "state_object": "state_object",
    "dependency": "external_system",
    "constraint": "operational_constraint",
    "non_goal": "non_goal",
}
_ARCHITECTURE_FACT_KINDS = {
    "internal_system",
    "component_responsibility",
    "assumption",
    "ambiguity",
}
_ARCHITECTURE_RELATION_KINDS = {
    "depends_on",
    "implements",
    "constrained_by",
    "excludes",
}


def semantic_graph_extension_schema_for_materiality(
    assessment: Mapping[str, Any],
    *,
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Return an author schema that cannot express source-owned graph rows."""

    schema = deepcopy(
        semantic_intent_output_schema_for_materiality(
            assessment,
            evidence_sources=evidence_sources,
        )
    )
    properties = schema["properties"]
    properties["version"] = {
        "type": "string",
        "enum": [SEMANTIC_GRAPH_EXTENSION_VERSION],
    }
    allowed_facts = _allowed_bounded_fact_kinds(assessment)
    variants = properties["facts"]["items"]["anyOf"]
    properties["facts"]["items"]["anyOf"] = [
        _bounded_fact_variant(variant)
        for variant in variants
        if _schema_enum(variant, "kind") in allowed_facts
    ]
    relation = properties["relations"]["items"]
    relation["properties"]["custody"]["enum"] = ["bounded_interpretation"]
    allowed_relations = set(_ARCHITECTURE_RELATION_KINDS)
    if _field_status(assessment, "state_object") == "nonmaterial_assumption":
        allowed_relations.add("changes")
    relation["properties"]["kind"]["enum"] = sorted(allowed_relations)
    return schema


def bind_semantic_graph_extension_source_refs(
    value: Mapping[str, Any],
    *,
    assessment: Mapping[str, Any],
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Decode provider citation handles without treating the extension as authority."""

    return bind_semantic_intent_source_ref_selections(
        value,
        assessment=assessment,
        evidence_sources=evidence_sources,
    )


def assemble_semantic_intent_from_extension(
    extension: Mapping[str, Any],
    *,
    assessment: Mapping[str, Any],
    source_claims: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge immutable source rows with bounded additions exactly once."""

    _exact_keys(
        extension,
        {"version", "status", "clarification", "facts", "relations", "narratives"},
        "Semantic graph extension",
    )
    if extension.get("version") != SEMANTIC_GRAPH_EXTENSION_VERSION:
        raise ValueError("Semantic graph extension uses an unsupported version")
    source_claims = _mapping(source_claims, "Semantic source claims")
    source_facts = [
        dict(_mapping(row.get("fact"), "Semantic source claim fact"))
        for row in _rows(source_claims.get("facts"), "Semantic source claim facts")
    ]
    source_relations = [
        dict(_mapping(row.get("relation"), "Semantic source claim relation"))
        for row in _rows(
            source_claims.get("relations"),
            "Semantic source claim relations",
        )
    ]
    bounded_facts = [
        dict(_mapping(row, "Semantic bounded fact"))
        for row in _rows(extension.get("facts"), "Semantic bounded facts")
    ]
    bounded_relations = [
        dict(_mapping(row, "Semantic bounded relation"))
        for row in _rows(
            extension.get("relations"),
            "Semantic bounded relations",
        )
    ]
    _require_bounded_extension(
        facts=bounded_facts,
        relations=bounded_relations,
        source_facts=source_facts,
        assessment=assessment,
    )
    return {
        "version": SEMANTIC_INTENT_IR_VERSION,
        "status": extension["status"],
        "clarification": deepcopy(extension["clarification"]),
        "facts": _merge_ordered(source_facts, bounded_facts, id_key="fact_id"),
        "relations": _merge_ordered(
            source_relations,
            bounded_relations,
            id_key="relation_id",
        ),
        "narratives": deepcopy(extension["narratives"]),
    }


def _require_bounded_extension(
    *,
    facts: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
    source_facts: Sequence[Mapping[str, Any]],
    assessment: Mapping[str, Any],
) -> None:
    allowed_facts = _allowed_bounded_fact_kinds(assessment)
    if any(
        row.get("custody") != "bounded_interpretation"
        or row.get("kind") not in allowed_facts
        for row in facts
    ):
        raise ValueError("Semantic graph extension carries non-bounded fact authority")
    bounded_by_id = {str(row.get("fact_id")): row for row in facts}
    source_ids = {str(row.get("fact_id")) for row in source_facts}
    if source_ids & set(bounded_by_id):
        raise ValueError("Semantic graph extension shadows a locked source fact")
    allowed_relations = set(_ARCHITECTURE_RELATION_KINDS)
    if _field_status(assessment, "state_object") == "nonmaterial_assumption":
        allowed_relations.add("changes")
    for row in relations:
        if (
            row.get("custody") != "bounded_interpretation"
            or row.get("kind") not in allowed_relations
        ):
            raise ValueError("Semantic graph extension carries non-bounded relation authority")
        kind = str(row.get("kind"))
        subject = bounded_by_id.get(str(row.get("subject_id")))
        object_row = bounded_by_id.get(str(row.get("object_id")))
        if kind == "implements":
            if subject is None or subject.get("kind") not in {
                "internal_system",
                "component_responsibility",
            }:
                raise ValueError("Semantic graph extension implementation lacks a bounded owner")
        elif kind == "changes":
            if object_row is None or object_row.get("kind") != "state_object":
                raise ValueError("Semantic graph extension state relation lacks a bounded state")
        elif subject is None:
            raise ValueError("Semantic graph extension boundary relation lacks a bounded subject")


def _allowed_bounded_fact_kinds(assessment: Mapping[str, Any]) -> set[str]:
    result = set(_ARCHITECTURE_FACT_KINDS)
    for field, kind in _FIELD_FACT_KIND.items():
        if _field_status(assessment, field) == "nonmaterial_assumption":
            result.add(kind)
    return result


def _field_status(assessment: Mapping[str, Any], field: str) -> str:
    return next(
        (
            str(row.get("status"))
            for row in assessment.get("fields", ())
            if isinstance(row, Mapping) and row.get("field") == field
        ),
        "unresolved",
    )


def _bounded_fact_variant(value: Mapping[str, Any]) -> dict[str, Any]:
    variant = deepcopy(value)
    variant["properties"]["custody"]["enum"] = ["bounded_interpretation"]
    return variant


def _schema_enum(value: Mapping[str, Any], name: str) -> str:
    return str(value["properties"][name]["enum"][0])


def _merge_ordered(
    source: Sequence[Mapping[str, Any]],
    bounded: Sequence[Mapping[str, Any]],
    *,
    id_key: str,
) -> list[dict[str, Any]]:
    result = [dict(row) for row in source]
    source_count = {
        kind: sum(1 for row in source if row.get("kind") == kind)
        for kind in {str(row.get("kind")) for row in source}
    }
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in bounded:
        grouped.setdefault(str(row.get("kind")), []).append(row)
    for kind, rows in grouped.items():
        rows.sort(key=lambda row: (int(row.get("order", 0)), str(row.get(id_key))))
        for offset, row in enumerate(rows, start=source_count.get(kind, 0)):
            result.append({**row, "order": offset})
    return result


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} is malformed")
    return value


def _rows(value: Any, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{label} are malformed")
    return list(value)


def _exact_keys(value: Mapping[str, Any], keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise ValueError(f"{label} has unsupported or missing fields")


__all__ = [
    "SEMANTIC_GRAPH_EXTENSION_VERSION",
    "assemble_semantic_intent_from_extension",
    "bind_semantic_graph_extension_source_refs",
    "semantic_graph_extension_schema_for_materiality",
]
