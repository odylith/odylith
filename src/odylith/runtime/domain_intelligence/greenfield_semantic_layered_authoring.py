"""Parallel source authoring plus bounded completion for production Greenfield graphs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
    build_atomic_source_adjudication,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_graph import (
    SEMANTIC_AUTHORING_GRAPH_VERSION,
    compile_semantic_authoring_graph,
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
    INTERNAL_SYSTEM_COMPONENT_KINDS,
    INTERNAL_SYSTEM_RELEASE_SCOPES,
    SEMANTIC_CLARIFICATION_FIELDS,
    SEMANTIC_RELATION_KINDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_implementation_completion import (
    complete_single_release_system,
    single_release_system_targets,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    require_semantic_source_refs,
    semantic_source_ref_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_narrative_projection import (
    project_semantic_narratives,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_authoring import (
    SEMANTIC_SOURCE_GRAPH_VERSION,
    SOURCE_FACT_ID_PREFIXES,
    compile_source_partitioned_graph,
    semantic_source_partitioned_graph_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_partition_custody import (
    require_discarded_evidence_separation,
)


SEMANTIC_COMPLETION_GRAPH_VERSION = "odylith.greenfield.semantic-completion-authoring-graph.v8"
SEMANTIC_PARTITIONED_AUTHOR_VERSION = "odylith.greenfield.semantic-partitioned-authoring-graph.v6"
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
_FACT_COLLECTION_BY_KIND = {kind: name for name, kind in _FACT_COLLECTIONS.items()}
_COMPLETION_FACTS = {"internal_systems"}
_SYSTEM_EDGE_KINDS = {
    "depends_on",
    "implements",
    "constrained_by",
    "excludes",
}
def semantic_completion_graph_schema(
    *,
    source_ref_schema: Mapping[str, Any] | None = None,
    system_count: int | None = None,
    complete_only: bool = False,
) -> dict[str, Any]:
    """Return an atomic-critic-independent bounded completion schema."""

    source_refs = _array(
        source_ref_schema or semantic_source_ref_schema(), minimum=1, maximum=8
    )
    internal_systems = _array(
        _compact_completion_fact_schema(
            "internal_system",
            source_refs=source_refs,
            include_edges=system_count != 1,
        ),
        minimum=system_count or 1,
        maximum=system_count if system_count is not None else 128,
    )
    schema = _object(
        ["version", "status", "clarification", "internal_systems", "self_challenge"],
        {
            "version": {"type": "string", "enum": [SEMANTIC_COMPLETION_GRAPH_VERSION]},
            "status": {"type": "string", "enum": ["complete", "clarification_required"]},
            "clarification": _object(
                ["question", "fields", "source_refs"],
                {
                    "question": {"type": "string", "maxLength": 600},
                    "fields": _array(
                        {"type": "string", "enum": list(SEMANTIC_CLARIFICATION_FIELDS)},
                        maximum=3,
                    ),
                    "source_refs": _array(
                        semantic_source_ref_schema(), maximum=8
                    ),
                },
            ),
            "internal_systems": internal_systems,
            "self_challenge": _array(
                _object(
                    ["challenge", "status"],
                    {
                        "challenge": {
                            "type": "string",
                            "enum": list(SEMANTIC_INTENT_MANDATORY_CHALLENGES),
                        },
                        "status": {"type": "string", "enum": ["passed", "failed"]},
                    },
                ),
                minimum=len(SEMANTIC_INTENT_MANDATORY_CHALLENGES),
                maximum=len(SEMANTIC_INTENT_MANDATORY_CHALLENGES),
            ),
        },
    )
    if complete_only:
        schema["required"].remove("clarification")
        schema["properties"].pop("clarification")
        schema["properties"]["status"] = {"type": "string", "enum": ["complete"]}
    return schema


def semantic_partitioned_author_schema(
    *, source_ref_schema: Mapping[str, Any] | None = None,
    system_count: int | None = None,
) -> dict[str, Any]:
    """Return the single-turn source-plus-completion authoring contract."""

    source_ref = dict(source_ref_schema or semantic_source_ref_schema())
    shared_ref = {"$ref": "#/$defs/source_ref"}
    schema = _object(
        ["version", "source", "completion"],
        {
            "version": {
                "type": "string", "enum": [SEMANTIC_PARTITIONED_AUTHOR_VERSION]
            },
            "source": semantic_source_partitioned_graph_schema(
                source_ref_schema=shared_ref
            ),
            "completion": semantic_completion_graph_schema(
                source_ref_schema=shared_ref,
                system_count=system_count,
            ),
        },
    )
    schema["$defs"] = {"source_ref": source_ref}
    return schema


def compile_partitioned_authoring_graph(
    value: Any,
    *,
    assessment: Mapping[str, Any],
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Compile one partitioned response without introducing a second authority."""

    author = _mapping(value, "Semantic partitioned authoring graph")
    _exact_keys(
        author,
        {"version", "source", "completion"},
        "Semantic partitioned authoring graph",
    )
    if author.get("version") != SEMANTIC_PARTITIONED_AUTHOR_VERSION:
        raise ValueError("Semantic partitioned authoring graph uses an unsupported version")
    partitioned_source = _mapping(author.get("source"), "Semantic partitioned source")
    boundary = _mapping(
        partitioned_source.get("boundary"), "Semantic partitioned source boundary"
    )
    discarded = boundary.get("discarded_evidence")
    product_boundary = {
        key: value for key, value in boundary.items() if key != "discarded_evidence"
    }
    require_discarded_evidence_separation(
        discarded,
        {**partitioned_source, "boundary": product_boundary},
        author.get("completion"),
    )
    source = compile_source_partitioned_graph(author.get("source"))
    return compile_layered_authoring_graph(
        source,
        author.get("completion"),
        assessment=assessment,
        evidence_sources=evidence_sources,
    )


def compile_layered_authoring_graph(
    source_value: Any,
    completion_value: Any,
    *,
    assessment: Mapping[str, Any],
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Bind parallel source truth to atomic spans, then compile bounded completion."""

    source = _mapping(source_value, "Semantic source authoring graph")
    _exact_keys(
        source,
        {"version", "facts", "relations"},
        "Semantic source authoring graph",
    )
    if source.get("version") != SEMANTIC_SOURCE_GRAPH_VERSION:
        raise ValueError("Semantic source authoring graph uses an unsupported version")
    completion = _mapping(completion_value, "Semantic completion authoring graph")
    _exact_keys(
        completion,
        {
            "version", "status", "clarification", "internal_systems",
            "self_challenge",
        },
        "Semantic completion authoring graph",
    )
    if completion.get("version") != SEMANTIC_COMPLETION_GRAPH_VERSION:
        raise ValueError("Semantic completion authoring graph uses an unsupported version")
    candidate_rows = assessment["source_candidates"]["candidates"]
    candidates = {
        str(row["candidate_id"]): dict(row["source_ref"])
        for row in candidate_rows
    }
    source_facts, used = _source_facts(
        source.get("facts"),
        candidates=candidates,
        evidence_sources=evidence_sources,
    )
    source_relations, relation_used = _source_relations(
        source.get("relations"),
        candidates=candidates,
        evidence_sources=evidence_sources,
    )
    used.update(relation_used)
    full_facts = {name: [] for name in _FACT_COLLECTIONS}
    for name, rows in source_facts.items():
        full_facts[name].extend(rows)
    completion_facts, completion_relations, completion_used = _completion_facts(
        {"internal_systems": completion.get("internal_systems")},
        candidates=candidates,
        evidence_sources=evidence_sources,
        offsets={name: len(rows) for name, rows in full_facts.items()},
        system_targets=single_release_system_targets(full_facts),
    )
    used.update(completion_used)
    for name, rows in completion_facts.items():
        full_facts[name].extend(rows)
    full_relations = {name: [] for name in SEMANTIC_RELATION_KINDS}
    for name, rows in source_relations.items():
        full_relations[name].extend(rows)
    for name, rows in completion_relations.items():
        for order, row in enumerate(rows, start=len(full_relations[name])):
            row["relation_id"] = f"relation.{name}.{order}"
            row["order"] = order
        full_relations[name].extend(rows)
    narratives = project_semantic_narratives(full_facts, full_relations)
    clarification, clarification_used = _completion_clarification(
        completion.get("clarification"),
        candidates=candidates,
        evidence_sources=evidence_sources,
    )
    used.update(clarification_used)
    decisions = [
        {
            "candidate_id": candidate_id,
            "decision": "retain" if candidate_id in used else "reject_noise",
        }
        for candidate_id in candidates
    ]
    graph = {
        "version": SEMANTIC_AUTHORING_GRAPH_VERSION,
        "status": completion["status"],
        "clarification": clarification,
        "candidate_decisions": decisions,
        "facts": full_facts,
        "fact_sequence": [
            row["fact_id"] for rows in full_facts.values() for row in rows
        ],
        "relations": full_relations,
        "relation_sequence": [
            row["relation_id"] for rows in full_relations.values() for row in rows
        ],
        "narratives": narratives,
        "self_challenge": deepcopy(completion["self_challenge"]),
    }
    return compile_semantic_authoring_graph(
        graph,
        assessment=assessment,
        evidence_sources=evidence_sources,
    )


def compile_layered_source_authority(
    source_value: Any,
    *,
    assessment: Mapping[str, Any],
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Validate source-only truth and atomic custody without completion authority."""

    source = _mapping(source_value, "Semantic source authoring graph")
    _exact_keys(
        source,
        {"version", "facts", "relations"},
        "Semantic source authoring graph",
    )
    if source.get("version") != SEMANTIC_SOURCE_GRAPH_VERSION:
        raise ValueError("Semantic source authoring graph uses an unsupported version")
    candidates = {
        str(row["candidate_id"]): dict(row["source_ref"])
        for row in assessment["source_candidates"]["candidates"]
    }
    source_facts, _ = _source_facts(
        source.get("facts"),
        candidates=candidates,
        evidence_sources=evidence_sources,
    )
    source_relations, _ = _source_relations(
        source.get("relations"),
        candidates=candidates,
        evidence_sources=evidence_sources,
    )
    atomic_facts: list[tuple[dict[str, Any], list[str]]] = []
    for collection, rows in source_facts.items():
        kind = _FACT_COLLECTIONS[collection]
        for raw in rows:
            if raw["custody"] != "source_fact":
                continue
            row = deepcopy(raw)
            candidate_ids = list(row.pop("candidate_ids"))
            row["kind"] = kind
            row.setdefault("owner_kind", "none")
            row["source_refs"] = [
                deepcopy(candidates[candidate_id])
                for candidate_id in candidate_ids
            ]
            atomic_facts.append((row, candidate_ids))
    atomic_relations: list[tuple[dict[str, Any], list[str]]] = []
    for kind, rows in source_relations.items():
        for raw in rows:
            row = deepcopy(raw)
            candidate_ids = list(row.pop("candidate_ids"))
            row["kind"] = kind
            row["source_refs"] = [
                deepcopy(candidates[candidate_id])
                for candidate_id in candidate_ids
            ]
            atomic_relations.append((row, candidate_ids))
    adjudication, claims = build_atomic_source_adjudication(
        assessment["source_candidates"],
        facts=atomic_facts,
        relations=atomic_relations,
        evidence_sources=evidence_sources,
        settled_fields={
            str(row["field"]): row for row in assessment["fields"]
        },
    )
    return {
        "source": deepcopy(source),
        "source_candidate_adjudication": adjudication,
        "source_claims": claims,
    }


def _source_facts(
    value: Any,
    *,
    candidates: Mapping[str, Mapping[str, Any]],
    evidence_sources: Mapping[str, str],
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
    set[str],
]:
    result = {name: [] for name in _FACT_COLLECTIONS}
    used: set[str] = set()
    for raw in _rows(value, 256, "Semantic source facts"):
        row = _mapping(raw, "Semantic source fact")
        kind = str(row.pop("kind", ""))
        collection = _FACT_COLLECTION_BY_KIND.get(kind)
        if collection is None:
            raise ValueError("Semantic source fact kind is invalid")
        expected_fact_id = f"{SOURCE_FACT_ID_PREFIXES[kind]}.{len(result[collection])}"
        if row.pop("fact_id", None) != expected_fact_id:
            raise ValueError("Semantic source fact identity is invalid")
        refs = require_semantic_source_refs(
            row.pop("source_refs", None),
            evidence_sources=evidence_sources,
        )
        candidate_ids = _matching_candidates(
            refs,
            candidates=candidates,
            evidence_sources=evidence_sources,
        )
        used.update(candidate_ids)
        row["fact_id"] = expected_fact_id
        result[collection].append(
            _expand_compact_source_fact(
                row,
                kind=kind,
                order=len(result[collection]),
                statement=str(refs[0]["quote"]),
                candidate_ids=candidate_ids,
            )
        )
    return result, used


def _completion_facts(
    value: Any,
    *,
    candidates: Mapping[str, Mapping[str, Any]],
    evidence_sources: Mapping[str, str],
    offsets: Mapping[str, int],
    system_targets: Mapping[str, Mapping[str, list[str]]],
) -> tuple[dict[str, list[dict[str, Any]]], set[str]]:
    collections = _mapping(value, "Semantic completion facts")
    _exact_keys(collections, _COMPLETION_FACTS, "Semantic completion facts")
    result = {name: [] for name in _COMPLETION_FACTS}
    relations = {name: [] for name in _SYSTEM_EDGE_KINDS}
    release_system_ids: list[str] = []
    used: set[str] = set()
    for name in sorted(_COMPLETION_FACTS):
        kind = _FACT_COLLECTIONS[name]
        for local_order, raw in enumerate(
            _rows(collections[name], 128, f"Semantic completion {name}")
        ):
            row = _mapping(raw, "Semantic completion fact")
            edges = (
                {kind: row.pop(kind, []) for kind in _SYSTEM_EDGE_KINDS}
                if kind == "internal_system"
                else {}
            )
            refs = require_semantic_source_refs(
                row.pop("source_refs", None),
                evidence_sources=evidence_sources,
            )
            candidate_ids = _matching_candidates(
                refs,
                candidates=candidates,
                evidence_sources=evidence_sources,
            )
            used.update(candidate_ids)
            result[name].append(
                _expand_compact_completion_fact(
                    row,
                    kind=kind,
                    order=offsets[name] + local_order,
                    candidate_ids=candidate_ids,
                )
            )
            if kind == "internal_system":
                subject_id = result[name][-1]["fact_id"]
                if row.get("release_scope") == "first_path_required":
                    release_system_ids.append(subject_id)
                for edge_kind in sorted(_SYSTEM_EDGE_KINDS):
                    for raw_edge in _rows(
                        edges[edge_kind],
                        256,
                        f"Semantic completion internal system {edge_kind}",
                    ):
                        edge = _mapping(raw_edge, "Semantic completion system edge")
                        _exact_keys(
                            edge,
                            {"object_id", "source_refs"},
                            "Semantic completion system edge",
                        )
                        edge_refs = require_semantic_source_refs(
                            edge.pop("source_refs"), evidence_sources=evidence_sources
                        )
                        edge_candidate_ids = _matching_candidates(
                            edge_refs,
                            candidates=candidates,
                            evidence_sources=evidence_sources,
                        )
                        used.update(edge_candidate_ids)
                        relations[edge_kind].append(
                            {
                                "subject_id": subject_id,
                                "object_id": edge["object_id"],
                                "custody": "bounded_interpretation",
                                "candidate_ids": edge_candidate_ids,
                            }
                        )
    complete_single_release_system(
        relations,
        release_system_ids=release_system_ids,
        targets=system_targets,
    )
    return result, relations, used


def _completion_clarification(
    value: Any,
    *,
    candidates: Mapping[str, Mapping[str, Any]],
    evidence_sources: Mapping[str, str],
) -> tuple[dict[str, Any], set[str]]:
    row = _mapping(value, "Semantic completion clarification")
    refs_value = row.pop("source_refs", None)
    if refs_value:
        refs = require_semantic_source_refs(
            refs_value, evidence_sources=evidence_sources
        )
        candidate_ids = _matching_candidates(
            refs, candidates=candidates, evidence_sources=evidence_sources
        )
    else:
        candidate_ids = []
    return {**row, "candidate_ids": candidate_ids}, set(candidate_ids)


def _source_relations(
    value: Any,
    *,
    candidates: Mapping[str, Mapping[str, Any]],
    evidence_sources: Mapping[str, str],
) -> tuple[dict[str, list[dict[str, Any]]], set[str]]:
    result = {name: [] for name in SEMANTIC_RELATION_KINDS}
    used: set[str] = set()
    for raw in _rows(value, 256, "Semantic source relations"):
        row = _mapping(raw, "Semantic source relation")
        kind = str(row.pop("kind", ""))
        if kind not in result:
            raise ValueError("Semantic source relation kind is invalid")
        refs = require_semantic_source_refs(
            row.pop("source_refs", None),
            evidence_sources=evidence_sources,
        )
        candidate_ids = _matching_candidates(
            refs,
            candidates=candidates,
            evidence_sources=evidence_sources,
        )
        used.update(candidate_ids)
        order = len(result[kind])
        result[kind].append({
            "relation_id": f"relation.{kind}.{order}",
            "subject_id": row["subject_id"],
            "object_id": row["object_id"],
            "order": order,
            "custody": "source_fact",
            "candidate_ids": candidate_ids,
        })
    return result, used


def _matching_candidates(
    refs: Sequence[Mapping[str, Any]],
    *,
    candidates: Mapping[str, Mapping[str, Any]],
    evidence_sources: Mapping[str, str],
) -> list[str]:
    result: list[str] = []
    ref_spans = [_span(ref, evidence_sources=evidence_sources) for ref in refs]
    for candidate_id, candidate_ref in candidates.items():
        candidate_span = _span(candidate_ref, evidence_sources=evidence_sources)
        if any(
            source_id == candidate_span[0]
            and (start <= candidate_span[1] and candidate_span[2] <= end
                 or candidate_span[1] <= start and end <= candidate_span[2])
            for source_id, start, end in ref_spans
        ):
            result.append(candidate_id)
    if not result:
        raise ValueError("Semantic source row has no exact atomic-span custody")
    return result


def _span(
    ref: Mapping[str, Any], *, evidence_sources: Mapping[str, str]
) -> tuple[str, int, int]:
    source_id = str(ref["source_id"])
    quote = str(ref["quote"])
    occurrence = int(ref["occurrence"])
    source = str(evidence_sources[source_id])
    start = -1
    cursor = 0
    for _ in range(occurrence):
        start = source.find(quote, cursor)
        if start < 0:
            raise ValueError("Semantic source ref cannot be resolved")
        cursor = start + len(quote)
    return source_id, start, start + len(quote)


def _compact_completion_fact_schema(
    kind: str, *, source_refs: Mapping[str, Any], include_edges: bool = True,
) -> dict[str, Any]:
    required = ["label", "statement", "source_refs"]
    properties: dict[str, Any] = {
        "label": _string(300),
        "statement": _string(1600),
        "source_refs": dict(source_refs),
    }
    typed_fields: dict[str, tuple[str, ...]] = {
        "state_object": ("object",),
        "internal_system": (
            "responsibility", "component_kind", "boundary", "outside_boundary",
            "proof", "risk", "release_scope",
        ),
        "component_responsibility": ("responsibility",),
    }
    for name in typed_fields.get(kind, ()):
        required.append(name)
        properties[name] = _string(800)
    if kind == "internal_system":
        properties["component_kind"] = {
            "type": "string", "enum": list(INTERNAL_SYSTEM_COMPONENT_KINDS)
        }
        properties["release_scope"] = {
            "type": "string", "enum": list(INTERNAL_SYSTEM_RELEASE_SCOPES)
        }
    if kind == "internal_system" and include_edges:
        edge = _object(
            ["object_id", "source_refs"],
            {"object_id": _string(100), "source_refs": dict(source_refs)},
        )
        for edge_kind in sorted(_SYSTEM_EDGE_KINDS):
            required.append(edge_kind)
            properties[edge_kind] = _array(
                deepcopy(edge),
                minimum=1 if edge_kind == "implements" else 0,
                maximum=128,
            )
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


def _expand_compact_source_fact(
    row: Mapping[str, Any],
    *,
    kind: str,
    order: int,
    statement: str,
    candidate_ids: list[str],
) -> dict[str, Any]:
    values = dict(row)
    values.pop("fact_id", None)
    fact_id = f"{SOURCE_FACT_ID_PREFIXES[kind]}.{order}"
    label = values.pop("label")
    owner_kind = values.pop("owner_kind", "none")
    transition = values.pop("transition", None)
    attributes = [
        {"name": name, "value": str(value)}
        for name, value in values.items()
    ]
    result = {
        "fact_id": fact_id,
        "label": label,
        "statement": statement,
        "order": order,
        "custody": (
            "bounded_interpretation" if kind == "assumption" else "source_fact"
        ),
        "attributes": attributes,
        "candidate_ids": candidate_ids,
    }
    if kind == "workflow_step":
        result["owner_kind"] = owner_kind
    if kind == "state_object":
        result["transition"] = transition
    return result


def _expand_compact_completion_fact(
    row: Mapping[str, Any],
    *,
    kind: str,
    order: int,
    candidate_ids: list[str],
) -> dict[str, Any]:
    values = dict(row)
    values.pop("fact_id", None)
    fact_id = f"{SOURCE_FACT_ID_PREFIXES[kind]}.{order}"
    label = values.pop("label")
    statement = values.pop("statement")
    transition = values.pop("transition", None)
    result = {
        "fact_id": fact_id,
        "label": label,
        "statement": statement,
        "order": order,
        "custody": "bounded_interpretation",
        "attributes": [
            {"name": name, "value": str(value)} for name, value in values.items()
        ],
        "candidate_ids": candidate_ids,
    }
    if kind == "state_object":
        result["transition"] = transition
    return result


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


__all__ = [
    "SEMANTIC_COMPLETION_GRAPH_VERSION", "SEMANTIC_PARTITIONED_AUTHOR_VERSION",
    "compile_layered_authoring_graph", "compile_layered_source_authority",
    "compile_partitioned_authoring_graph",
    "semantic_completion_graph_schema", "semantic_partitioned_author_schema",
]
