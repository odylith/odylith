"""Assemble bounded graph-author additions around locked source claims."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_IR_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    semantic_intent_output_schema_for_materiality,
    semantic_materiality_source_ref_catalog,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    bind_semantic_source_ref_selections,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    RELATION_ENDPOINT_KINDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_extension_contract import (
    SEMANTIC_GRAPH_EXTENSION_OUTGOING_EDGE_KINDS,
    SEMANTIC_GRAPH_EXTENSION_VERSION,
)


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
_OUTGOING_EDGE_KINDS = SEMANTIC_GRAPH_EXTENSION_OUTGOING_EDGE_KINDS
_NODE_KEYS = {"fact", *_OUTGOING_EDGE_KINDS, "incoming_changes"}


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
    variants = properties.pop("facts")["items"]["anyOf"]
    relation_source_refs = deepcopy(
        properties.pop("relations")["items"]["properties"]["source_refs"]
    )
    properties["nodes"] = {
        "type": "array",
        "maxItems": 128,
        "items": {
            "anyOf": [
                _bounded_node_variant(
                    _bounded_fact_variant(variant),
                    source_refs=relation_source_refs,
                )
                for variant in variants
                if _schema_enum(variant, "kind") in allowed_facts
            ]
        },
    }
    schema["required"] = [
        "version",
        "status",
        "clarification",
        "nodes",
        "narratives",
    ]
    return schema


def bind_semantic_graph_extension_source_refs(
    value: Mapping[str, Any],
    *,
    assessment: Mapping[str, Any],
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Decode citation handles across the exact node-owned extension shape."""

    catalog = {
        row["ref_id"]: {
            "source_id": row["source_id"],
            "quote": row["quote"],
            "occurrence": row["occurrence"],
        }
        for row in semantic_materiality_source_ref_catalog(
            assessment,
            evidence_sources=evidence_sources,
        )
    }
    result = deepcopy(dict(value))
    clarification = dict(
        _mapping(result.get("clarification"), "Semantic graph extension clarification")
    )
    clarification["source_refs"] = bind_semantic_source_ref_selections(
        clarification.get("source_refs"), catalog=catalog
    )
    result["clarification"] = clarification
    bound_nodes: list[dict[str, Any]] = []
    for raw_node in _rows(result.get("nodes"), "Semantic graph extension nodes"):
        node = dict(_mapping(raw_node, "Semantic graph extension node"))
        fact = dict(_mapping(node.get("fact"), "Semantic bounded fact"))
        fact["source_refs"] = bind_semantic_source_ref_selections(
            fact.get("source_refs"), catalog=catalog
        )
        node["fact"] = fact
        for edge_kind in (*_OUTGOING_EDGE_KINDS, "incoming_changes"):
            bound_edges: list[dict[str, Any]] = []
            for raw_edge in _rows(
                node.get(edge_kind), f"Semantic {edge_kind} edges"
            ):
                edge = dict(_mapping(raw_edge, f"Semantic {edge_kind} edge"))
                edge["source_refs"] = bind_semantic_source_ref_selections(
                    edge.get("source_refs"), catalog=catalog
                )
                bound_edges.append(edge)
            node[edge_kind] = bound_edges
        bound_nodes.append(node)
    result["nodes"] = bound_nodes
    bound_narratives: list[dict[str, Any]] = []
    for raw_narrative in _rows(
        result.get("narratives"), "Semantic graph extension narratives"
    ):
        narrative = dict(_mapping(raw_narrative, "Semantic graph extension narrative"))
        narrative["source_refs"] = bind_semantic_source_ref_selections(
            narrative.get("source_refs"), catalog=catalog
        )
        bound_narratives.append(narrative)
    result["narratives"] = bound_narratives
    return result


def assemble_semantic_intent_from_extension(
    extension: Mapping[str, Any],
    *,
    assessment: Mapping[str, Any],
    source_claims: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge immutable source rows with bounded additions exactly once."""

    _exact_keys(
        extension,
        {"version", "status", "clarification", "nodes", "narratives"},
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
    bounded_facts, bounded_relations = _project_bounded_nodes(extension.get("nodes"))
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
    source_by_id = {str(row.get("fact_id")): row for row in source_facts}
    source_ids = set(source_by_id)
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
        endpoints = RELATION_ENDPOINT_KINDS[kind]
        subject_id = str(row.get("subject_id"))
        object_id = str(row.get("object_id"))
        subject = bounded_by_id.get(subject_id) or source_by_id.get(subject_id)
        object_row = bounded_by_id.get(object_id) or source_by_id.get(object_id)
        if subject is None or subject.get("kind") not in endpoints["subject"]:
            raise ValueError("Semantic graph extension relation has an invalid typed subject")
        if object_row is None or object_row.get("kind") not in endpoints["object"]:
            raise ValueError("Semantic graph extension relation has an invalid typed object")
        if kind == "changes":
            if object_id not in bounded_by_id:
                raise ValueError("Semantic graph extension state relation lacks a bounded state")
        elif subject_id not in bounded_by_id:
            raise ValueError("Semantic graph extension boundary relation lacks a bounded subject")


def _project_bounded_nodes(value: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    facts: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    for raw_node in _rows(value, "Semantic graph extension nodes"):
        node = _mapping(raw_node, "Semantic graph extension node")
        _exact_keys(node, _NODE_KEYS, "Semantic graph extension node")
        fact = dict(_mapping(node.get("fact"), "Semantic bounded fact"))
        facts.append(fact)
        subject_id = str(fact.get("fact_id"))
        if fact.get("kind") == "internal_system":
            for relation_kind in _OUTGOING_EDGE_KINDS:
                for raw_edge in _rows(
                    node.get(relation_kind), f"Semantic {relation_kind} edges"
                ):
                    edge = _mapping(raw_edge, f"Semantic {relation_kind} edge")
                    _exact_keys(
                        edge,
                        {"relation_id", "object_id", "order", "source_refs"},
                        f"Semantic {relation_kind} edge",
                    )
                    relations.append(
                        {
                            "relation_id": edge["relation_id"],
                            "kind": relation_kind,
                            "subject_id": subject_id,
                            "object_id": edge["object_id"],
                            "order": edge["order"],
                            "custody": "bounded_interpretation",
                            "source_refs": deepcopy(edge["source_refs"]),
                        }
                    )
        elif any(_rows(node.get(kind), f"Semantic {kind} edges") for kind in _OUTGOING_EDGE_KINDS):
            raise ValueError("Only a bounded internal system may own outgoing architecture edges")
        incoming_changes = _rows(
            node.get("incoming_changes"), "Semantic incoming changes edges"
        )
        if incoming_changes and fact.get("kind") != "state_object":
            raise ValueError("Only a bounded state may own incoming change edges")
        for raw_edge in incoming_changes:
            edge = _mapping(raw_edge, "Semantic incoming changes edge")
            _exact_keys(
                edge,
                {"relation_id", "subject_id", "order", "source_refs"},
                "Semantic incoming changes edge",
            )
            relations.append(
                {
                    "relation_id": edge["relation_id"],
                    "kind": "changes",
                    "subject_id": edge["subject_id"],
                    "object_id": subject_id,
                    "order": edge["order"],
                    "custody": "bounded_interpretation",
                    "source_refs": deepcopy(edge["source_refs"]),
                }
            )
    return facts, relations


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


def _bounded_node_variant(
    fact: Mapping[str, Any], *, source_refs: Mapping[str, Any]
) -> dict[str, Any]:
    kind = _schema_enum(fact, "kind")
    outgoing_limit = 32 if kind == "internal_system" else 0
    incoming_limit = 32 if kind == "state_object" else 0
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["fact", *_OUTGOING_EDGE_KINDS, "incoming_changes"],
        "properties": {
            "fact": deepcopy(dict(fact)),
            **{
                edge_kind: {
                    "type": "array",
                    "maxItems": outgoing_limit,
                    "items": _outgoing_edge_schema(source_refs),
                }
                for edge_kind in _OUTGOING_EDGE_KINDS
            },
            "incoming_changes": {
                "type": "array",
                "maxItems": incoming_limit,
                "items": _incoming_change_schema(source_refs),
            },
        },
    }


def _outgoing_edge_schema(source_refs: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["relation_id", "object_id", "order", "source_refs"],
        "properties": {
            "relation_id": {"type": "string", "minLength": 1, "maxLength": 100},
            "object_id": {"type": "string", "minLength": 1, "maxLength": 100},
            "order": {"type": "integer", "minimum": 0},
            "source_refs": deepcopy(dict(source_refs)),
        },
    }


def _incoming_change_schema(source_refs: Mapping[str, Any]) -> dict[str, Any]:
    schema = _outgoing_edge_schema(source_refs)
    properties = schema["properties"]
    properties["subject_id"] = properties.pop("object_id")
    schema["required"] = ["relation_id", "subject_id", "order", "source_refs"]
    return schema


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
