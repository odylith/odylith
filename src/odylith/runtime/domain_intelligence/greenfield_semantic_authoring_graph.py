"""Provider-compact authoring graph compiled into the full Semantic Intent contract."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import hashlib
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
    ATOMIC_SOURCE_ADJUDICATION_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    SEMANTIC_INTENT_MANDATORY_CHALLENGES,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_schema import (
    array_schema as _array,
    object_schema as _object,
    string_schema as _string,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    FACT_OWNER_KINDS,
    INTERNAL_SYSTEM_COMPONENT_KINDS,
    INTERNAL_SYSTEM_RELEASE_SCOPES,
    SEMANTIC_ATTRIBUTE_NAMES,
    SEMANTIC_CLARIFICATION_FIELDS,
    SEMANTIC_FACT_KINDS,
    SEMANTIC_NARRATIVE_FIELDS,
    SEMANTIC_RELATION_KINDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_extension_contract import (
    SEMANTIC_GRAPH_EXTENSION_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    semantic_materiality_source_ref_catalog,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_claims import (
    SEMANTIC_SOURCE_CLAIMS_VERSION,
)


SEMANTIC_AUTHORING_GRAPH_VERSION = "odylith.greenfield.semantic-authoring-graph.v2"
_CANDIDATE_DECISIONS = ("retain", "reject_overcapture", "reject_noise")
_FACT_FIELD = {
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
_BOUNDARY_EDGES = ("depends_on", "implements", "constrained_by", "excludes")
_FACT_COLLECTIONS = {
    "identities": "identity",
    "actors": "actor",
    "workflow_steps": "workflow_step",
    "state_objects": "state_object",
    "visible_outputs": "visible_output",
    "external_systems": "external_system",
    "internal_systems": "internal_system",
    "component_responsibilities": "component_responsibility",
    "operational_constraints": "operational_constraint",
    "non_goals": "non_goal",
    "assumptions": "assumption",
    "ambiguities": "ambiguity",
}


def semantic_authoring_graph_schema(
    assessment: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a small provider schema with candidate ids instead of repeated citations."""

    candidates = assessment.get("source_candidates")
    rows = candidates.get("candidates") if isinstance(candidates, Mapping) else None
    if not isinstance(rows, Sequence) or not rows:
        raise ValueError("Semantic authoring graph lacks atomic candidates")
    candidate_ids = [str(row["candidate_id"]) for row in rows if isinstance(row, Mapping)]
    if len(candidate_ids) != len(rows) or len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("Semantic authoring graph candidate ids are invalid")
    complete = assessment.get("decision") == "authorize_graph"
    candidate_refs = _id_array(candidate_ids, minimum=1)
    identifier = _string(100)
    common_fact_ref = {"$ref": "#/$defs/commonFact"}
    workflow_fact_ref = {"$ref": "#/$defs/workflowFact"}
    state_fact_ref = {"$ref": "#/$defs/stateFact"}
    relation_ref = {"$ref": "#/$defs/relation"}
    schema = _object(
        [
            "version",
            "status",
            "clarification",
            "candidate_decisions",
            "facts",
            "fact_sequence",
            "relations",
            "relation_sequence",
            "narratives",
            "self_challenge",
        ],
        {
            "version": {"type": "string", "enum": [SEMANTIC_AUTHORING_GRAPH_VERSION]},
            "status": {"type": "string", "enum": [
                "complete", "clarification_required"
            ]},
            "clarification": _object(
                ["question", "fields", "candidate_ids"],
                {
                    "question": {"type": "string", "maxLength": 600},
                    "fields": _array({
                        "type": "string", "enum": list(SEMANTIC_CLARIFICATION_FIELDS)
                    }, maximum=3),
                    "candidate_ids": _id_array(candidate_ids),
                },
            ),
            "candidate_decisions": _array(
                _object(
                    ["candidate_id", "decision"],
                    {
                        "candidate_id": {"type": "string", "enum": candidate_ids},
                        "decision": {"type": "string", "enum": list(_CANDIDATE_DECISIONS)},
                    },
                ),
                minimum=len(candidate_ids),
                maximum=len(candidate_ids),
            ),
            "facts": _object(
                list(_FACT_COLLECTIONS),
                {
                    collection: _array(
                        (
                            workflow_fact_ref
                            if kind == "workflow_step"
                            else state_fact_ref
                            if kind == "state_object"
                            else common_fact_ref
                        ),
                        minimum=(
                            1
                            if complete and kind in {
                                "identity", "workflow_step", "visible_output", "internal_system"
                            }
                            else 0
                        ),
                        maximum=1 if kind == "identity" else 128,
                    )
                    for collection, kind in _FACT_COLLECTIONS.items()
                },
            ),
            "fact_sequence": _array(identifier, maximum=128),
            "relations": _object(
                list(SEMANTIC_RELATION_KINDS),
                {
                    kind: _array(
                        relation_ref,
                        minimum=1 if complete and kind in {"produces", "implements"} else 0,
                        maximum=256,
                    )
                    for kind in SEMANTIC_RELATION_KINDS
                },
            ),
            "relation_sequence": _array(identifier, maximum=256),
            "narratives": _array(
                _object(
                    ["field", "order", "text", "fact_ids", "candidate_ids"],
                    {
                        "field": {"type": "string", "enum": list(SEMANTIC_NARRATIVE_FIELDS)},
                        "order": {"type": "integer", "minimum": 0},
                        "text": _string(1600),
                        "fact_ids": _array(identifier, minimum=1, maximum=32),
                        "candidate_ids": candidate_refs,
                    },
                ),
                maximum=64,
            ),
            "self_challenge": _array(
                _object(
                    ["challenge", "status"],
                    {
                        "challenge": {
                            "type": "string", "enum": list(SEMANTIC_INTENT_MANDATORY_CHALLENGES)
                        },
                        "status": {"type": "string", "enum": ["passed", "failed"]},
                    },
                ),
                minimum=len(SEMANTIC_INTENT_MANDATORY_CHALLENGES),
                maximum=len(SEMANTIC_INTENT_MANDATORY_CHALLENGES),
            ),
        },
    )
    schema["$defs"] = {
        "commonFact": _authoring_fact_schema("identity", candidate_refs=candidate_refs),
        "workflowFact": _authoring_fact_schema(
            "workflow_step", candidate_refs=candidate_refs
        ),
        "stateFact": _authoring_fact_schema("state_object", candidate_refs=candidate_refs),
        "relation": _authoring_relation_schema(candidate_refs=candidate_refs),
    }
    return schema


def _authoring_fact_schema(
    kind: str,
    *,
    candidate_refs: Mapping[str, Any],
) -> dict[str, Any]:
    required = [
        "fact_id", "label", "statement", "order", "custody", "attributes", "candidate_ids"
    ]
    properties: dict[str, Any] = {
        "fact_id": _string(100),
        "label": _string(300),
        "statement": _string(1600),
        "order": {"type": "integer", "minimum": 0},
        "custody": {
            "type": "string", "enum": ["source_fact", "bounded_interpretation"]
        },
        "attributes": _array(
            _object(
                ["name", "value"],
                {
                    "name": {"type": "string", "enum": list(SEMANTIC_ATTRIBUTE_NAMES)},
                    "value": _string(800),
                },
            ),
            maximum=12,
        ),
        "candidate_ids": dict(candidate_refs),
    }
    if kind == "workflow_step":
        required.append("owner_kind")
        properties["owner_kind"] = {
            "type": "string", "enum": list(FACT_OWNER_KINDS[kind])
        }
    if kind == "state_object":
        required.append("transition")
        properties["transition"] = {
            "anyOf": [
                {"type": "null"},
                _object(
                    ["from_state", "to_state"],
                    {"from_state": _string(800), "to_state": _string(800)},
                ),
            ]
        }
    return _object(required, properties)


def _authoring_relation_schema(
    *, candidate_refs: Mapping[str, Any]
) -> dict[str, Any]:
    return _object(
        ["relation_id", "subject_id", "object_id", "order", "custody", "candidate_ids"],
        {
            "relation_id": _string(100),
            "subject_id": _string(100),
            "object_id": _string(100),
            "order": {"type": "integer", "minimum": 0},
            "custody": {
                "type": "string", "enum": ["source_fact", "bounded_interpretation"]
            },
            "candidate_ids": dict(candidate_refs),
        },
    )


def compile_semantic_authoring_graph(
    value: Any,
    *,
    assessment: Mapping[str, Any],
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Compile the small authoring graph into the existing full packet-author output."""

    graph = _mapping(value, "Semantic authoring graph")
    _exact_keys(
        graph,
        {
            "version", "status", "clarification", "candidate_decisions", "facts",
            "fact_sequence", "relations", "relation_sequence", "narratives", "self_challenge",
        },
        "Semantic authoring graph",
    )
    if graph.get("version") != SEMANTIC_AUTHORING_GRAPH_VERSION:
        raise ValueError("Semantic authoring graph uses an unsupported version")
    candidates = assessment["source_candidates"]["candidates"]
    candidate_refs = {
        str(row["candidate_id"]): dict(row["source_ref"])
        for row in candidates
    }
    decisions = _candidate_decisions(graph.get("candidate_decisions"), candidate_refs)
    used_candidates: set[str] = set()
    facts: list[tuple[dict[str, Any], list[str]]] = []
    fact_collections = _mapping(graph.get("facts"), "Semantic authoring fact collections")
    _exact_keys(
        fact_collections,
        set(_FACT_COLLECTIONS),
        "Semantic authoring fact collections",
    )
    for collection, kind in _FACT_COLLECTIONS.items():
        for raw in _rows(
            fact_collections[collection], 128, f"Semantic authoring {collection}"
        ):
            row = _mapping(raw, "Semantic authoring fact")
            candidate_ids = _candidate_ids(row.pop("candidate_ids", None), candidate_refs)
            used_candidates.update(candidate_ids)
            fact = _fact(
                {**row, "kind": kind},
                candidate_ids=candidate_ids,
                candidate_refs=candidate_refs,
            )
            facts.append((fact, candidate_ids))
    relations: list[tuple[dict[str, Any], list[str]]] = []
    relation_collections = _mapping(
        graph.get("relations"), "Semantic authoring relation collections"
    )
    _exact_keys(
        relation_collections,
        set(SEMANTIC_RELATION_KINDS),
        "Semantic authoring relation collections",
    )
    for kind in SEMANTIC_RELATION_KINDS:
        for raw in _rows(
            relation_collections[kind], 256, f"Semantic authoring {kind} relations"
        ):
            row = _mapping(raw, "Semantic authoring relation")
            candidate_ids = _candidate_ids(row.pop("candidate_ids", None), candidate_refs)
            used_candidates.update(candidate_ids)
            relation = _relation(
                {**row, "kind": kind},
                candidate_ids=candidate_ids,
                candidate_refs=candidate_refs,
            )
            relations.append((relation, candidate_ids))
    facts = _ordered_rows(
        facts,
        graph.get("fact_sequence"),
        id_key="fact_id",
        label="Semantic authoring fact sequence",
    )
    relations = _ordered_rows(
        relations,
        graph.get("relation_sequence"),
        id_key="relation_id",
        label="Semantic authoring relation sequence",
    )
    clarification = _clarification(
        graph.get("clarification"),
        candidate_refs=candidate_refs,
        used_candidates=used_candidates,
    )
    narratives = _narratives(
        graph.get("narratives"),
        candidate_refs=candidate_refs,
        used_candidates=used_candidates,
    )
    rejected = {candidate_id for candidate_id, decision in decisions.items() if decision != "retain"}
    if rejected & used_candidates:
        raise ValueError("rejected atomic evidence still binds authored product meaning")
    source_facts = [(row, ids) for row, ids in facts if row["custody"] == "source_fact"]
    source_relations = [
        (row, ids) for row, ids in relations if row["custody"] == "source_fact"
    ]
    source_claims = {
        "version": SEMANTIC_SOURCE_CLAIMS_VERSION,
        "facts": [
            {"field": _fact_field(row), "fact": row}
            for row, _ in source_facts
        ],
        "relations": [
            {
                "fields": _relation_fields(row, assessment=assessment),
                "relation": row,
            }
            for row, _ in source_relations
        ],
    }
    adjudication = {
        "version": ATOMIC_SOURCE_ADJUDICATION_VERSION,
        "candidate_decisions": [
            {
                "candidate_id": candidate_id,
                "decision": decision,
                "fact_ids": [
                    row["fact_id"] for row, ids in source_facts if candidate_id in ids
                ],
                "relation_ids": [
                    row["relation_id"]
                    for row, ids in source_relations
                    if candidate_id in ids
                ],
            }
            for candidate_id, decision in decisions.items()
        ],
        "source_claims": source_claims,
    }
    handles = _candidate_handles(assessment, evidence_sources=evidence_sources)
    extension = _extension(
        status=str(graph.get("status") or ""),
        clarification=clarification,
        facts=[(row, ids) for row, ids in facts if row["custody"] == "bounded_interpretation"],
        relations=[
            (row, ids)
            for row, ids in relations
            if row["custody"] == "bounded_interpretation"
        ],
        narratives=narratives,
        handles=handles,
    )
    return {
        "source_candidate_adjudication": adjudication,
        "semantic_extension": extension,
        "self_challenge": deepcopy(graph["self_challenge"]),
    }


def _fact(
    row: dict[str, Any],
    *,
    candidate_ids: list[str],
    candidate_refs: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    kind = str(row.get("kind") or "")
    expected = {
        "fact_id", "kind", "label", "statement", "order", "custody", "attributes"
    }
    if kind == "workflow_step":
        expected.add("owner_kind")
    if kind == "state_object":
        expected.add("transition")
    _exact_keys(
        row,
        expected,
        "Semantic authoring fact",
    )
    if kind not in SEMANTIC_FACT_KINDS:
        raise ValueError("Semantic authoring fact kind is invalid")
    owner_kind = row.get("owner_kind", "none")
    if owner_kind not in FACT_OWNER_KINDS[kind]:
        raise ValueError("Semantic authoring fact owner kind is invalid")
    transition = row.pop("transition", None)
    result = {
        **row,
        "owner_kind": owner_kind,
        "source_refs": _refs(candidate_ids, candidate_refs),
    }
    if kind == "state_object":
        result["transition"] = transition
    return result


def _relation(
    row: dict[str, Any],
    *,
    candidate_ids: list[str],
    candidate_refs: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    _exact_keys(
        row,
        {"relation_id", "kind", "subject_id", "object_id", "order", "custody"},
        "Semantic authoring relation",
    )
    if row.get("kind") not in SEMANTIC_RELATION_KINDS:
        raise ValueError("Semantic authoring relation kind is invalid")
    return {**row, "source_refs": _refs(candidate_ids, candidate_refs)}


def _extension(
    *,
    status: str,
    clarification: Mapping[str, Any],
    facts: Sequence[tuple[Mapping[str, Any], list[str]]],
    relations: Sequence[tuple[Mapping[str, Any], list[str]]],
    narratives: Sequence[tuple[Mapping[str, Any], list[str]]],
    handles: Mapping[str, str],
) -> dict[str, Any]:
    nodes = [
        {
            "fact": _with_handles(fact, ids, handles),
            "depends_on": [],
            "implements": [],
            "constrained_by": [],
            "excludes": [],
            "incoming_changes": [],
        }
        for fact, ids in facts
    ]
    by_id = {str(node["fact"]["fact_id"]): node for node in nodes}
    for relation, ids in relations:
        kind = str(relation["kind"])
        edge = {
            "relation_id": relation["relation_id"],
            "order": relation["order"],
            "source_refs": _handle_refs(ids, handles),
        }
        if kind == "changes" and relation["object_id"] in by_id:
            by_id[str(relation["object_id"])]["incoming_changes"].append(
                {**edge, "subject_id": relation["subject_id"]}
            )
        elif kind in _BOUNDARY_EDGES and relation["subject_id"] in by_id:
            by_id[str(relation["subject_id"])][kind].append(
                {**edge, "object_id": relation["object_id"]}
            )
        else:
            raise ValueError("bounded authoring relation has no graph-extension owner")
    return {
        "version": SEMANTIC_GRAPH_EXTENSION_VERSION,
        "status": status,
        "clarification": _with_handles(
            clarification[0], clarification[1], handles
        ),
        "nodes": nodes,
        "narratives": [
            _with_handles(row, ids, handles) for row, ids in narratives
        ],
    }


def _clarification(
    value: Any,
    *,
    candidate_refs: Mapping[str, Mapping[str, Any]],
    used_candidates: set[str],
) -> tuple[dict[str, Any], list[str]]:
    row = _mapping(value, "Semantic authoring clarification")
    _exact_keys(row, {"question", "fields", "candidate_ids"}, "Semantic authoring clarification")
    ids = _candidate_ids(row.pop("candidate_ids"), candidate_refs, allow_empty=True)
    used_candidates.update(ids)
    return row, ids


def _narratives(
    value: Any,
    *,
    candidate_refs: Mapping[str, Mapping[str, Any]],
    used_candidates: set[str],
) -> list[tuple[dict[str, Any], list[str]]]:
    result = []
    for raw in _rows(value, 64, "Semantic authoring narratives"):
        row = _mapping(raw, "Semantic authoring narrative")
        _exact_keys(
            row,
            {"field", "order", "text", "fact_ids", "candidate_ids"},
            "Semantic authoring narrative",
        )
        ids = _candidate_ids(row.pop("candidate_ids"), candidate_refs)
        used_candidates.update(ids)
        result.append((row, ids))
    return result


def _candidate_decisions(
    value: Any,
    candidates: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in _rows(value, 128, "Semantic candidate decisions"):
        row = _mapping(raw, "Semantic candidate decision")
        _exact_keys(row, {"candidate_id", "decision"}, "Semantic candidate decision")
        candidate_id = str(row.get("candidate_id") or "")
        decision = str(row.get("decision") or "")
        if candidate_id not in candidates or candidate_id in result:
            raise ValueError("Semantic candidate decisions are incomplete or duplicated")
        if decision not in _CANDIDATE_DECISIONS:
            raise ValueError("Semantic candidate decision is invalid")
        result[candidate_id] = decision
    if set(result) != set(candidates):
        raise ValueError("Semantic candidate decisions do not cover every span")
    return result


def _fact_field(row: Mapping[str, Any]) -> str:
    field = _FACT_FIELD.get(str(row.get("kind") or ""))
    if not field:
        raise ValueError("source fact kind has no canonical materiality field")
    return field


def _relation_fields(
    row: Mapping[str, Any], *, assessment: Mapping[str, Any]
) -> list[str]:
    settled = {str(field["field"]) for field in assessment["fields"]}
    fields = [field for field in _RELATION_FIELDS[str(row["kind"])] if field in settled]
    if not fields:
        raise ValueError("source relation has no settled materiality field")
    return fields


def _candidate_handles(
    assessment: Mapping[str, Any], *, evidence_sources: Mapping[str, str]
) -> dict[str, str]:
    catalog = semantic_materiality_source_ref_catalog(
        assessment,
        evidence_sources=evidence_sources,
    )
    by_ref = {
        (row["source_id"], row["quote"], row["occurrence"]): row["ref_id"]
        for row in catalog
    }
    return {
        str(row["candidate_id"]): by_ref[
            (
                row["source_ref"]["source_id"],
                row["source_ref"]["quote"],
                row["source_ref"]["occurrence"],
            )
        ]
        for row in assessment["source_candidates"]["candidates"]
    }


def _with_handles(
    row: Mapping[str, Any], ids: Sequence[str], handles: Mapping[str, str]
) -> dict[str, Any]:
    return {**deepcopy(dict(row)), "source_refs": _handle_refs(ids, handles)}


def _handle_refs(ids: Sequence[str], handles: Mapping[str, str]) -> list[dict[str, str]]:
    return [{"ref_id": handles[candidate_id]} for candidate_id in ids]


def _refs(
    ids: Sequence[str], candidates: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for candidate_id in ids:
        ref = dict(candidates[candidate_id])
        if ref not in result:
            result.append(ref)
    return result


def _candidate_ids(
    value: Any,
    candidates: Mapping[str, Mapping[str, Any]],
    *,
    allow_empty: bool = False,
) -> list[str]:
    rows = _rows(value, 32, "Semantic candidate ids")
    ids = [str(row) for row in rows]
    if (not ids and not allow_empty) or len(ids) != len(set(ids)):
        raise ValueError("Semantic candidate ids are empty or duplicated")
    if any(candidate_id not in candidates for candidate_id in ids):
        raise ValueError("Semantic candidate id is unknown")
    return ids


def _ordered_rows(
    rows: Sequence[tuple[dict[str, Any], list[str]]],
    order_value: Any,
    *,
    id_key: str,
    label: str,
) -> list[tuple[dict[str, Any], list[str]]]:
    order = [str(value) for value in _rows(order_value, 256, label)]
    index = {str(row[id_key]): (row, ids) for row, ids in rows}
    if len(index) != len(rows) or len(order) != len(set(order)) or set(order) != set(index):
        raise ValueError(f"{label} does not cover every typed row exactly once")
    return [index[row_id] for row_id in order]


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} is malformed")
    return dict(value)


def _rows(value: Any, maximum: int, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{label} is malformed")
    rows = list(value)
    if len(rows) > maximum:
        raise ValueError(f"{label} exceeds its operating limit")
    return rows


def _exact_keys(value: Mapping[str, Any], keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise ValueError(f"{label} has unsupported or missing fields")


def _id_array(ids: Sequence[str], *, minimum: int = 0) -> dict[str, Any]:
    return _array({"type": "string", "enum": list(ids)}, minimum=minimum, maximum=32)


__all__ = [
    "SEMANTIC_AUTHORING_GRAPH_VERSION",
    "compile_semantic_authoring_graph",
    "semantic_authoring_graph_schema",
]
