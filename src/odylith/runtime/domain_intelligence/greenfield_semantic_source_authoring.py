"""Typed source-authoring partitions for Greenfield semantic graphs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_schema import (
    array_schema as _array,
    object_schema as _object,
    string_schema as _string,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    SEMANTIC_CLARIFICATION_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    semantic_source_ref_schema,
)


SEMANTIC_SOURCE_PARTITIONED_GRAPH_VERSION = (
    "odylith.greenfield.semantic-source-partitioned-authoring-graph.v22"
)
SEMANTIC_SOURCE_PATH_GRAPH_VERSION = "odylith.greenfield.semantic-source-path-graph.v8"
SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION = (
    "odylith.greenfield.semantic-source-boundary-graph.v7"
)
SEMANTIC_SOURCE_GRAPH_VERSION = "odylith.greenfield.semantic-source-authoring-graph.v17"
SOURCE_ACCESS_MODES = ("read", "write", "read_write", "invoke")
SOURCE_PATH_COLLECTIONS = {
    "identities": "identity",
    "actors": "actor",
    "workflow_steps": "workflow_step",
    "state_objects": "state_object",
    "visible_outputs": "visible_output",
}
SOURCE_BOUNDARY_COLLECTIONS = {
    "external_systems": "external_system",
    "policies": "policy",
    "assumptions": "assumption",
    "discarded_evidence": "discarded_evidence",
}
SOURCE_PATH_RELATION_KINDS: tuple[str, ...] = ()
SOURCE_BOUNDARY_RELATION_KINDS: tuple[str, ...] = ()
SOURCE_FACT_ID_PREFIXES = {
    "identity": "identity",
    "actor": "actor",
    "workflow_step": "step",
    "state_object": "state",
    "visible_output": "output",
    "external_system": "dependency",
    "internal_system": "system",
    "component_responsibility": "component-responsibility",
    "operational_constraint": "constraint",
    "non_goal": "non-goal",
    "assumption": "assumption",
    "ambiguity": "ambiguity",
}


def semantic_source_partitioned_graph_schema(
    *, source_ref_schema: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Return one response schema with explicit path and boundary ownership."""

    return _object(
        ["version", "path", "boundary"],
        {
            "version": {
                "type": "string", "enum": [SEMANTIC_SOURCE_PARTITIONED_GRAPH_VERSION]
            },
            "path": _partition_schema(
                collections=SOURCE_PATH_COLLECTIONS,
                relation_kinds=SOURCE_PATH_RELATION_KINDS,
                source_ref_schema=source_ref_schema,
            ),
            "boundary": _partition_schema(
                collections=SOURCE_BOUNDARY_COLLECTIONS,
                relation_kinds=SOURCE_BOUNDARY_RELATION_KINDS,
                source_ref_schema=source_ref_schema,
            ),
        },
    )


def semantic_source_path_graph_schema(
    *, source_ref_schema: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Return the sole source-path authoring schema."""

    return _object(
        ["version", "path"],
        {
            "version": {
                "type": "string", "enum": [SEMANTIC_SOURCE_PATH_GRAPH_VERSION]
            },
            "path": _partition_schema(
                collections=SOURCE_PATH_COLLECTIONS,
                relation_kinds=SOURCE_PATH_RELATION_KINDS,
                source_ref_schema=source_ref_schema,
            ),
        },
    )


def semantic_source_boundary_graph_schema(
    *, source_ref_schema: Mapping[str, Any] | None = None,
    assumption_fields: Sequence[str] = SEMANTIC_CLARIFICATION_FIELDS,
) -> dict[str, Any]:
    """Return the sole source-boundary authoring schema."""

    return _object(
        ["version", "boundary"],
        {
            "version": {
                "type": "string", "enum": [SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION]
            },
            "boundary": _partition_schema(
                collections=SOURCE_BOUNDARY_COLLECTIONS,
                relation_kinds=SOURCE_BOUNDARY_RELATION_KINDS,
                source_ref_schema=source_ref_schema,
                assumption_fields=assumption_fields,
            ),
        },
    )


def combine_source_authoring_partitions(
    path_value: Any, boundary_value: Any
) -> dict[str, Any]:
    """Combine disjoint typed authorities without interpreting either partition."""

    if not isinstance(path_value, Mapping) or set(path_value) != {"version", "path"}:
        raise ValueError("Semantic source path graph is malformed")
    if path_value.get("version") != SEMANTIC_SOURCE_PATH_GRAPH_VERSION:
        raise ValueError("Semantic source path graph uses an unsupported version")
    if not isinstance(boundary_value, Mapping) or set(boundary_value) != {
        "version", "boundary",
    }:
        raise ValueError("Semantic source boundary graph is malformed")
    if boundary_value.get("version") != SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION:
        raise ValueError("Semantic source boundary graph uses an unsupported version")
    return {
        "version": SEMANTIC_SOURCE_PARTITIONED_GRAPH_VERSION,
        "path": dict(path_value["path"]),
        "boundary": dict(boundary_value["boundary"]),
    }


def compile_source_partitioned_graph(value: Any) -> dict[str, Any]:
    """Flatten explicit source partitions without reparsing or semantic inference."""

    if not isinstance(value, Mapping) or set(value) != {"version", "path", "boundary"}:
        raise ValueError("Semantic source partitioned graph is malformed")
    if value.get("version") != SEMANTIC_SOURCE_PARTITIONED_GRAPH_VERSION:
        raise ValueError("Semantic source partitioned graph uses an unsupported version")
    path = _partition(
        value.get("path"),
        label="Semantic source path graph",
        collections=SOURCE_PATH_COLLECTIONS,
        relation_kinds=SOURCE_PATH_RELATION_KINDS,
    )
    if sum(row["kind"] == "identity" for row in path["facts"]) != 1:
        raise ValueError("Semantic source graph must contain one product identity")
    boundary = _partition(
        value.get("boundary"),
        label="Semantic source boundary graph",
        collections=SOURCE_BOUNDARY_COLLECTIONS,
        relation_kinds=SOURCE_BOUNDARY_RELATION_KINDS,
        dependency_subjects={
            "identity.0",
            *(row["fact_id"] for row in path["facts"] if row["kind"] == "workflow_step"),
        },
    )
    return {
        "version": SEMANTIC_SOURCE_GRAPH_VERSION,
        "facts": [*path["facts"], *boundary["facts"]],
        "relations": [*path["relations"], *boundary["relations"]],
    }


def _partition_schema(
    *,
    collections: Mapping[str, str],
    relation_kinds: Sequence[str],
    source_ref_schema: Mapping[str, Any] | None,
    assumption_fields: Sequence[str] = SEMANTIC_CLARIFICATION_FIELDS,
) -> dict[str, Any]:
    source_refs = _array(
        source_ref_schema or semantic_source_ref_schema(), minimum=1, maximum=8
    )
    return _object(
        [*collections, "relations"],
        {
            **{
                name: _array(
                    _workflow_group_schema(source_refs=source_refs)
                    if kind == "workflow_step"
                    else _fact_schema(
                        kind, source_refs=source_refs,
                        assumption_fields=assumption_fields,
                    ),
                    minimum=(
                        1 if kind in {"identity", "workflow_step", "visible_output"}
                        else 0
                    ),
                    maximum=(
                        1 if kind == "identity" else
                        0 if kind == "assumption" and not assumption_fields else 128
                    ),
                )
                for name, kind in collections.items()
            },
            "relations": _object(
                relation_kinds,
                {
                    kind: _array(
                        _object(
                            ["subject_id", "object_id", "source_refs"],
                            {
                                "subject_id": _string(100),
                                "object_id": _string(100),
                                "source_refs": source_refs,
                            },
                        ),
                        maximum=128,
                    )
                    for kind in relation_kinds
                },
            ),
        },
    )


def _fact_schema(
    kind: str, *, source_refs: Mapping[str, Any],
    assumption_fields: Sequence[str] = SEMANTIC_CLARIFICATION_FIELDS,
) -> dict[str, Any]:
    required = ["label", "source_refs"]
    properties: dict[str, Any] = {
        "label": _string(300),
        "source_refs": dict(source_refs),
    }
    typed_fields: dict[str, tuple[str, ...]] = {
        "identity": ("source_title",),
        "workflow_step": ("action", "action_phrase"),
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
    if kind == "visible_output":
        required.extend(["condition", "producer"])
        properties["condition"] = {
            "anyOf": [_string(800), {"type": "null"}],
        }
        properties["producer"] = _object(
            ["step_index", "source_refs"],
            {
                "step_index": {"type": "integer", "minimum": 0, "maximum": 127},
                "source_refs": dict(source_refs),
            },
        )
    if kind == "state_object":
        required.append("transition")
        properties["transition"] = {
            "anyOf": [
                _object(
                    ["step_index", "from_state", "to_state", "source_refs"],
                    {
                        "step_index": {
                            "type": "integer", "minimum": 0, "maximum": 127,
                        },
                        "from_state": _string(800),
                        "to_state": _string(800),
                        "source_refs": dict(source_refs),
                    },
                ),
                {"type": "null"},
            ]
        }
    if kind == "external_system":
        required.extend(["access_mode", "consumer"])
        properties["access_mode"] = {
            "anyOf": [
                {"type": "string", "enum": list(SOURCE_ACCESS_MODES)},
                {"type": "null"},
            ]
        }
        properties["consumer"] = {
            "anyOf": [
                _object(
                    ["kind"], {"kind": {"type": "string", "enum": ["identity"]}}
                ),
                _object(
                    ["kind", "step_index"],
                    {
                        "kind": {"type": "string", "enum": ["workflow_step"]},
                        "step_index": {"type": "integer", "minimum": 0, "maximum": 127},
                    },
                ),
                {"type": "null"},
            ]
        }
    if kind == "policy":
        required.append("policy_kind")
        properties["policy_kind"] = {
            "type": "string",
            "enum": ["operating_invariant", "excluded_capability"],
        }
    if kind == "assumption":
        required.append("materiality_field")
        properties["materiality_field"] = {
            "type": "string",
            "enum": list(assumption_fields or SEMANTIC_CLARIFICATION_FIELDS),
        }
    return _object(required, properties)


def _workflow_group_schema(*, source_refs: Mapping[str, Any]) -> dict[str, Any]:
    owner = {
        "anyOf": [
            _object(
                ["kind", "actor_id"],
                {
                    "kind": {"type": "string", "enum": ["actor"]},
                    "actor_id": _string(100),
                },
            ),
            *(
                _object(
                    ["kind"],
                    {"kind": {"type": "string", "enum": [kind]}},
                )
                for kind in ("product", "system")
            ),
        ]
    }
    step = _fact_schema("workflow_step", source_refs=source_refs)
    return _object(
        ["owner", "steps"],
        {
            "owner": owner,
            "steps": _array(
                step,
                minimum=1,
                maximum=128,
            ),
        },
    )


def _partition(
    value: Any,
    *,
    label: str,
    collections: Mapping[str, str],
    relation_kinds: Sequence[str],
    dependency_subjects: set[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {*collections, "relations"}:
        raise ValueError(f"{label} is malformed")
    facts: list[dict[str, Any]] = []
    derived_relations: list[dict[str, Any]] = []
    for name, kind in collections.items():
        rows = _rows(value.get(name), 128, f"{label} {name}")
        if kind == "discarded_evidence":
            continue
        if kind == "workflow_step":
            expanded = []
            for group in rows:
                owner = group.get("owner")
                if not isinstance(owner, Mapping) or owner.get("kind") not in {
                    "actor", "product", "system"
                }:
                    raise ValueError("Semantic source workflow owner is malformed")
                owner_kind = str(owner["kind"])
                if owner_kind == "actor" and set(owner) != {"kind", "actor_id"}:
                    raise ValueError("Semantic source actor workflow owner is malformed")
                if owner_kind != "actor" and set(owner) != {"kind"}:
                    raise ValueError("Semantic source workflow owner is malformed")
                for fact in _rows(group.get("steps"), 128, "Semantic workflow steps"):
                    expanded.append((dict(fact), owner_kind, owner.get("actor_id")))
        else:
            expanded = [(dict(row), "none", None) for row in rows]
        for fact, owner_kind, actor_id in expanded:
            compiled_kind = kind
            dependency_subject = ""
            if kind == "state_object" and "transition" not in fact:
                raise ValueError("Semantic source state transition is missing")
            transition = fact.pop("transition", None) if kind == "state_object" else None
            producer = fact.pop("producer", None) if kind == "visible_output" else None
            if kind == "visible_output":
                if "condition" not in fact:
                    raise ValueError("Semantic source visible output condition is missing")
                if fact["condition"] is None:
                    fact.pop("condition")
            if kind == "external_system" and fact.get("access_mode") is None:
                fact.pop("access_mode")
            if kind == "external_system":
                consumer = fact.pop("consumer", None)
                if consumer is not None and not isinstance(consumer, Mapping):
                    raise ValueError("Semantic source dependency consumer is malformed")
                if isinstance(consumer, Mapping) and set(consumer) == {
                    "kind"
                } and consumer.get("kind") == "identity":
                    dependency_subject = "identity.0"
                elif isinstance(consumer, Mapping) and (
                    set(consumer) == {"kind", "step_index"}
                    and consumer.get("kind") == "workflow_step"
                    and isinstance(consumer.get("step_index"), int)
                    and not isinstance(consumer.get("step_index"), bool)
                ):
                    dependency_subject = f"step.{consumer['step_index']}"
                if consumer is not None and dependency_subject not in (
                    dependency_subjects or set()
                ):
                    raise ValueError("Semantic source dependency consumer is invalid")
            if kind == "policy":
                compiled_kind = {
                    "operating_invariant": "operational_constraint",
                    "excluded_capability": "non_goal",
                }.get(str(fact.pop("policy_kind", "")), "")
                if not compiled_kind:
                    raise ValueError("Semantic source policy kind is invalid")
            fact_id = (
                f"{SOURCE_FACT_ID_PREFIXES[compiled_kind]}."
                f"{sum(row['kind'] == compiled_kind for row in facts)}"
            )
            if kind == "workflow_step":
                fact["owner_kind"] = owner_kind
                if actor_id:
                    derived_relations.append(
                        {
                            "kind": "owned_by",
                            "subject_id": fact_id,
                            "object_id": str(actor_id),
                            "source_refs": list(fact["source_refs"]),
                        }
                    )
            elif kind == "state_object":
                fact["transition"] = None
                if transition is not None:
                    edge = _axis_assignment(
                        transition,
                        label="Semantic source state transition",
                        fields={"step_index", "from_state", "to_state", "source_refs"},
                        step_count=sum(row["kind"] == "workflow_step" for row in facts),
                    )
                    if edge["from_state"] == edge["to_state"]:
                        raise ValueError("Semantic workflow transition does not change state")
                    fact["transition"] = {
                        "from_state": edge["from_state"],
                        "to_state": edge["to_state"],
                    }
                    derived_relations.append(
                        {
                            "kind": "changes",
                            "subject_id": f"step.{edge['step_index']}",
                            "object_id": fact_id,
                            "source_refs": list(edge["source_refs"]),
                        }
                    )
            elif kind == "visible_output":
                edge = _axis_assignment(
                    producer,
                    label="Semantic source output producer",
                    fields={"step_index", "source_refs"},
                    step_count=sum(row["kind"] == "workflow_step" for row in facts),
                )
                derived_relations.append(
                    {
                        "kind": "produces",
                        "subject_id": f"step.{edge['step_index']}",
                        "object_id": fact_id,
                        "source_refs": list(edge["source_refs"]),
                    }
                )
            elif compiled_kind in {
                "external_system", "operational_constraint", "non_goal"
            } and (compiled_kind != "external_system" or dependency_subject):
                relation_kind = {
                    "external_system": "depends_on",
                    "operational_constraint": "constrained_by",
                    "non_goal": "excludes",
                }[compiled_kind]
                derived_relations.append(
                    {
                        "kind": relation_kind,
                        "subject_id": (
                            dependency_subject if compiled_kind == "external_system"
                            else "identity.0"
                        ),
                        "object_id": fact_id,
                        "source_refs": list(fact["source_refs"]),
                    }
                )
            facts.append({**fact, "fact_id": fact_id, "kind": compiled_kind})
    relation_collections = value.get("relations")
    if not isinstance(relation_collections, Mapping) or set(relation_collections) != set(
        relation_kinds
    ):
        raise ValueError(f"{label} relations are malformed")
    relations = [
        {**row, "kind": kind}
        for kind in relation_kinds
        for row in _rows(
            relation_collections[kind], 128, f"{label} {kind} relations"
        )
    ]
    return {"facts": facts, "relations": [*derived_relations, *relations]}


def _axis_assignment(
    value: Any,
    *,
    label: str,
    fields: set[str],
    step_count: int,
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{label} is malformed")
    assignment = dict(value)
    step_index = assignment.get("step_index")
    if (
        isinstance(step_index, bool)
        or not isinstance(step_index, int)
        or step_index < 0
        or step_index >= step_count
    ):
        raise ValueError(f"{label} has an invalid step")
    if any(
        not isinstance(assignment.get(field), str)
        or not str(assignment[field]).strip()
        for field in fields - {"step_index", "source_refs"}
    ):
        raise ValueError(f"{label} is malformed")
    return assignment


def _rows(value: Any, maximum: int, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{label} is malformed")
    rows = list(value)
    if len(rows) > maximum or any(not isinstance(row, Mapping) for row in rows):
        raise ValueError(f"{label} is malformed")
    return [dict(row) for row in rows]


__all__ = [
    "SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION",
    "SEMANTIC_SOURCE_GRAPH_VERSION",
    "SEMANTIC_SOURCE_PATH_GRAPH_VERSION",
    "SEMANTIC_SOURCE_PARTITIONED_GRAPH_VERSION",
    "SOURCE_BOUNDARY_COLLECTIONS",
    "SOURCE_ACCESS_MODES",
    "SOURCE_FACT_ID_PREFIXES",
    "SOURCE_PATH_COLLECTIONS",
    "combine_source_authoring_partitions",
    "compile_source_partitioned_graph",
    "semantic_source_boundary_graph_schema",
    "semantic_source_partitioned_graph_schema",
    "semantic_source_path_graph_schema",
]
