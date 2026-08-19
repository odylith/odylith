"""Disjoint implementation and narrative completion contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_schema import (
    object_schema as _object,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_layered_authoring import (
    semantic_completion_graph_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    semantic_intent_authoring_contract,
)


def semantic_graph_completion_schema(
    *, source_citation_ids: Sequence[str],
    edge_object_ids: Mapping[str, Sequence[str]],
    topology_mode: str,
) -> dict[str, Any]:
    """Return the one-call completion schema over an immutable source graph."""

    citation_ids = list(source_citation_ids)
    if not citation_ids or len(set(citation_ids)) != len(citation_ids):
        raise ValueError("Semantic completion citation IDs are missing or duplicated")
    schema = semantic_completion_graph_schema(
        source_ref_schema={"type": "object"},
        complete_only=True,
    )
    citation_definition = {
        "type": "array",
        "items": {"type": "string", "enum": citation_ids},
        "minItems": 1,
        "maxItems": 8,
    }
    schema["$defs"] = {"source_citation_ids": citation_definition}
    citation_schema = {"$ref": "#/$defs/source_citation_ids"}
    _replace_source_refs_with_citation_ids(schema, citation_schema=citation_schema)
    _compact_self_challenge_schema(schema)
    system = schema["properties"]["internal_systems"]["items"]
    for edge_kind, raw_ids in edge_object_ids.items():
        values = list(raw_ids)
        edge = system["properties"][edge_kind]
        if values:
            edge["items"]["properties"]["object_id"] = {
                "type": "string",
                "enum": values,
            }
        else:
            edge["maxItems"] = 0
    system["required"].remove("implements")
    system["properties"].pop("implements")
    system["required"].remove("release_scope")
    system["properties"].pop("release_scope")
    supporting_system = deepcopy(system)
    for edge_kind in ("depends_on", "constrained_by", "excludes"):
        supporting_system["required"].remove(edge_kind)
        supporting_system["properties"].pop(edge_kind)
    boundary_kinds = [
        kind
        for kind in ("depends_on", "constrained_by", "excludes")
        if edge_object_ids.get(kind)
    ]
    boundary_ids = list(
        dict.fromkeys(
            object_id
            for kind in boundary_kinds
            for object_id in edge_object_ids[kind]
        )
    )
    supporting_system["required"].extend(
        ["boundary_links", "supporting_consumers"]
    )
    supporting_system["properties"]["boundary_links"] = {
        "type": "array",
        "items": _object(
            ["kind", "object_id", "source_citation_ids"],
            {
                "kind": {
                    "type": "string",
                    "enum": boundary_kinds or ["unavailable"],
                },
                "object_id": {
                    "type": "string",
                    "enum": boundary_ids or ["unavailable"],
                },
                "source_citation_ids": deepcopy(citation_schema),
            },
        ),
        "minItems": 1,
        "maxItems": 128,
    }
    supporting_system["properties"]["supporting_consumers"] = _object(
        ["system_indices", "source_citation_ids"],
        {
            "system_indices": {
                "type": "array",
                "items": {"type": "integer", "minimum": 0, "maximum": 127},
                "minItems": 1,
                "maxItems": 128,
            },
            "source_citation_ids": deepcopy(citation_schema),
        },
    )
    schema["required"].append("supporting_systems")
    schema["properties"]["supporting_systems"] = {
        "type": "array",
        "items": supporting_system,
        "maxItems": 128 if boundary_kinds else 0,
    }
    targets = list(edge_object_ids.get("implements", ()))
    schema["required"].append("implementation_assignments")
    schema["properties"]["implementation_assignments"] = _object(
        targets,
        {
            target: _object(
                ["system_indices", "source_citation_ids"],
                {
                    "system_indices": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 0, "maximum": 127},
                        "minItems": 1,
                        "maxItems": 128,
                    },
                    "source_citation_ids": deepcopy(citation_schema),
                },
            )
            for target in targets
        },
    )
    if topology_mode == "single_system":
        schema["properties"]["internal_systems"]["minItems"] = 1
        schema["properties"]["internal_systems"]["maxItems"] = 1
        schema["properties"]["supporting_systems"]["maxItems"] = 0
    elif topology_mode != "adaptive":
        raise ValueError("Semantic completion topology mode is unsupported")
    return schema


def apply_semantic_implementation_assignments(
    value: Any, *, edge_object_ids: Mapping[str, Sequence[str]],
    citation_registry: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Project exact required source-fact assignments into system edges."""

    completion = _hydrate_completion_citations(
        _mapping(value, "Semantic graph completion"),
        citation_registry=citation_registry,
    )
    _project_self_challenge(completion)
    assignments = _mapping(
        completion.pop("implementation_assignments", None),
        "Semantic implementation assignments",
    )
    targets = list(edge_object_ids.get("implements", ()))
    _exact_keys(assignments, set(targets), "Semantic implementation assignments")
    result_systems = completion.get("internal_systems")
    supporting_systems = completion.pop("supporting_systems", None)
    if not isinstance(result_systems, list) or any(
        not isinstance(system, Mapping) for system in result_systems
    ):
        raise ValueError("Semantic completion systems are malformed")
    if not isinstance(supporting_systems, list) or any(
        not isinstance(system, Mapping) for system in supporting_systems
    ):
        raise ValueError("Semantic supporting systems are malformed")
    if len(result_systems) + len(supporting_systems) > 128:
        raise ValueError("Semantic completion has too many systems")
    projected = [dict(system) for system in result_systems]
    for system in projected:
        if "implements" in system:
            raise ValueError("Semantic completion bypasses typed implementation assignments")
        system["implements"] = []
    for target in targets:
        assignment = _mapping(
            assignments[target], f"Semantic implementation assignment {target}"
        )
        _exact_keys(
            assignment,
            {"system_indices", "source_refs"},
            f"Semantic implementation assignment {target}",
        )
        indices = assignment["system_indices"]
        if (
            not isinstance(indices, list)
            or not indices
            or any(not isinstance(index, int) or isinstance(index, bool) for index in indices)
            or len(set(indices)) != len(indices)
            or any(index < 0 or index >= len(projected) for index in indices)
        ):
            raise ValueError("Semantic implementation assignment has an invalid system index")
        for index in indices:
            projected[index]["implements"].append(
                {
                    "object_id": target,
                    "source_refs": deepcopy(assignment["source_refs"]),
                }
            )
    if any(not system["implements"] for system in projected):
        raise ValueError("Semantic result system lacks an implementation assignment")
    for system in projected:
        system["release_scope"] = "first_path_required"
    result_count = len(projected)
    for support_offset, raw_system in enumerate(supporting_systems):
        system = dict(raw_system)
        if any(
            key in system
            for key in (
                "implements", "release_scope", "depends_on", "constrained_by", "excludes"
            )
        ):
            raise ValueError("Semantic supporting system bypasses typed projection")
        boundary_links = system.pop("boundary_links", None)
        consumers = _mapping(
            system.pop("supporting_consumers", None),
            "Semantic supporting consumers",
        )
        _exact_keys(
            consumers,
            {"system_indices", "source_refs"},
            "Semantic supporting consumers",
        )
        raw_consumer_indices = consumers["system_indices"]
        if (
            not isinstance(raw_consumer_indices, list)
            or not raw_consumer_indices
            or any(
                not isinstance(index, int) or isinstance(index, bool)
                for index in raw_consumer_indices
            )
        ):
            raise ValueError("resultless Semantic Intent system lacks typed supporting topology")
        consumer_indices = list(dict.fromkeys(raw_consumer_indices))
        if not isinstance(boundary_links, list) or not boundary_links:
            raise ValueError("resultless Semantic Intent system lacks a typed boundary")
        for kind in ("depends_on", "constrained_by", "excludes"):
            system[kind] = []
        for raw_link in boundary_links:
            link = _mapping(raw_link, "Semantic supporting boundary")
            _exact_keys(
                link,
                {"kind", "object_id", "source_refs"},
                "Semantic supporting boundary",
            )
            kind = link["kind"]
            object_id = link["object_id"]
            if (
                kind not in {"depends_on", "constrained_by", "excludes"}
                or object_id not in edge_object_ids.get(kind, ())
            ):
                raise ValueError("Semantic supporting boundary has an invalid typed target")
            system[kind].append(
                {
                    "object_id": object_id,
                    "source_refs": deepcopy(link["source_refs"]),
                }
            )
        system["implements"] = []
        system["release_scope"] = "first_path_required"
        support_index = result_count + support_offset
        projected.append(system)
        for consumer_index in consumer_indices:
            if (
                consumer_index < 0
                or consumer_index >= result_count
            ):
                raise ValueError(
                    "Semantic supporting topology has an invalid consumer "
                    f"(support_index={support_index}, consumer_index={consumer_index!r}, "
                    f"system_count={len(projected)})"
                )
            projected[consumer_index]["depends_on"].append(
                {
                    "object_id": f"system.{support_index}",
                    "source_refs": deepcopy(consumers["source_refs"]),
                }
            )
    completion["internal_systems"] = projected
    return completion


def semantic_completion_citation_registry(
    source: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return atomic exact citations and the typed source facts they support."""

    facts = source.get("facts")
    if not isinstance(facts, list) or any(not isinstance(row, Mapping) for row in facts):
        raise ValueError("Semantic completion source facts are malformed")
    citations: dict[tuple[str, str, int], dict[str, Any]] = {}
    seen_fact_ids: set[str] = set()
    for raw in facts:
        fact_id = str(raw.get("fact_id") or "")
        refs = raw.get("source_refs")
        if (
            not fact_id
            or fact_id in seen_fact_ids
            or not isinstance(refs, list)
            or not refs
            or any(not isinstance(ref, Mapping) for ref in refs)
        ):
            raise ValueError("Semantic completion source fact citation is malformed")
        seen_fact_ids.add(fact_id)
        for raw_ref in refs:
            ref = dict(raw_ref)
            key = (
                str(ref.get("source_id") or ""),
                str(ref.get("quote") or ""),
                int(ref.get("occurrence") or 0),
            )
            if not all(key):
                raise ValueError("Semantic completion source fact citation is malformed")
            row = citations.setdefault(
                key,
                {"source_ref": deepcopy(ref), "fact_ids": []},
            )
            row["fact_ids"].append(fact_id)
    if not citations:
        raise ValueError("Semantic completion source lacks citable facts")
    return {
        f"citation.{index}": {
            "source_ref": row["source_ref"],
            "fact_ids": tuple(dict.fromkeys(row["fact_ids"])),
        }
        for index, row in enumerate(citations.values())
    }


def semantic_architecture_edge_object_ids(
    source: Mapping[str, Any],
) -> dict[str, tuple[str, ...]]:
    """Return exact typed targets available to implementation architecture."""

    facts = source.get("facts")
    if not isinstance(facts, list) or any(not isinstance(row, Mapping) for row in facts):
        raise ValueError("Semantic completion source facts are malformed")
    contracts = semantic_intent_authoring_contract()["relation_contracts"]
    result: dict[str, tuple[str, ...]] = {}
    for edge_kind in ("depends_on", "implements", "constrained_by", "excludes"):
        object_kinds = set(contracts[edge_kind]["object_kinds"])
        values = [
            str(row["fact_id"])
            for row in facts
            if row.get("kind") in object_kinds and row.get("fact_id")
        ]
        result[edge_kind] = tuple(values)
    return result


def _replace_source_refs_with_citation_ids(
    value: Any, *, citation_schema: Mapping[str, Any]
) -> None:
    if isinstance(value, list):
        for item in value:
            _replace_source_refs_with_citation_ids(
                item, citation_schema=citation_schema
            )
        return
    if not isinstance(value, dict):
        return
    properties = value.get("properties")
    required = value.get("required")
    if isinstance(properties, dict) and "source_refs" in properties:
        if not isinstance(required, list) or "source_refs" not in required:
            raise RuntimeError("Semantic completion citation schema is inconsistent")
        properties.pop("source_refs")
        properties["source_citation_ids"] = deepcopy(dict(citation_schema))
        required[required.index("source_refs")] = "source_citation_ids"
    for item in value.values():
        _replace_source_refs_with_citation_ids(
            item, citation_schema=citation_schema
        )


def _compact_self_challenge_schema(schema: dict[str, Any]) -> None:
    challenge = schema["properties"].get("self_challenge")
    if not isinstance(challenge, Mapping):
        raise RuntimeError("Semantic completion self-challenge schema is missing")
    item = challenge.get("items")
    properties = item.get("properties") if isinstance(item, Mapping) else None
    names = (
        properties.get("challenge", {}).get("enum")
        if isinstance(properties, Mapping) else None
    )
    statuses = (
        properties.get("status", {}).get("enum")
        if isinstance(properties, Mapping) else None
    )
    if not isinstance(names, list) or not isinstance(statuses, list):
        raise RuntimeError("Semantic completion self-challenge schema is malformed")
    schema["properties"]["self_challenge"] = _object(
        list(names),
        {
            name: {"type": "string", "enum": list(statuses)}
            for name in names
        },
    )


def _project_self_challenge(completion: dict[str, Any]) -> None:
    value = completion.get("self_challenge")
    if value is None:
        return
    challenge = _mapping(value, "Semantic completion self challenge")
    schema = semantic_completion_graph_schema(
        source_ref_schema={"type": "object"}, complete_only=True
    )["properties"]["self_challenge"]
    names = list(schema["items"]["properties"]["challenge"]["enum"])
    _exact_keys(challenge, set(names), "Semantic completion self challenge")
    if any(challenge[name] not in {"passed", "failed"} for name in names):
        raise ValueError("Semantic completion self challenge has an invalid status")
    completion["self_challenge"] = [
        {"challenge": name, "status": challenge[name]} for name in names
    ]


def _hydrate_completion_citations(
    value: Any,
    *,
    citation_registry: Mapping[str, Mapping[str, Any]],
) -> Any:
    if isinstance(value, list):
        return [
            _hydrate_completion_citations(
                item, citation_registry=citation_registry
            )
            for item in value
        ]
    if not isinstance(value, Mapping):
        return deepcopy(value)
    if "source_refs" in value:
        raise ValueError("Semantic completion bypasses typed atomic citations")
    result: dict[str, Any] = {}
    for key, item in value.items():
        if key == "source_citation_ids":
            result["source_refs"] = _source_refs_for_citation_ids(
                item, citation_registry=citation_registry
            )
        else:
            result[key] = _hydrate_completion_citations(
                item, citation_registry=citation_registry
            )
    return result


def _source_refs_for_citation_ids(
    value: Any,
    *,
    citation_registry: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if (
        not isinstance(value, list)
        or not value
        or len(value) > 8
        or any(
            not isinstance(citation_id, str)
            or citation_id not in citation_registry
            for citation_id in value
        )
        or len(set(value)) != len(value)
    ):
        raise ValueError("Semantic completion cites an invalid source citation")
    return [
        deepcopy(
            _mapping(
                citation_registry[citation_id].get("source_ref"),
                "Semantic completion source citation",
            )
        )
        for citation_id in value
    ]


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} is malformed")
    return dict(value)


def _exact_keys(value: Mapping[str, Any], keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise ValueError(f"{label} has unsupported or missing fields")


__all__ = [
    "apply_semantic_implementation_assignments",
    "semantic_architecture_edge_object_ids",
    "semantic_completion_citation_registry",
    "semantic_graph_completion_schema",
]
