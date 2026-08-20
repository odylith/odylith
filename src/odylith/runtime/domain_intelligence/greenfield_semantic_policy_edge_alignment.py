"""Rebind provisional completion policy edges to settled materiality kinds."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    semantic_source_refs_overlap,
)


_POLICY_EDGE_KIND = {
    "operational_constraint": "constrained_by",
    "non_goal": "excludes",
}


def align_completion_policy_edges(
    completion_value: Any,
    *,
    provisional_source: Mapping[str, Any],
    settled_source: Mapping[str, Any],
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Move completion edges by exact citations after policy-kind settlement."""

    if not isinstance(completion_value, Mapping):
        raise ValueError("Semantic completion policy alignment is malformed")
    completion = deepcopy(dict(completion_value))
    provisional = _fact_index(provisional_source)
    settled = [
        row for row in _fact_index(settled_source).values()
        if row.get("kind") in _POLICY_EDGE_KIND
    ]
    systems = completion.get("internal_systems")
    if not isinstance(systems, list) or any(
        not isinstance(row, Mapping) for row in systems
    ):
        raise ValueError("Semantic completion policy alignment is malformed")
    if systems and all(
        "constrained_by" not in system and "excludes" not in system
        for system in systems
    ):
        return completion
    aligned_systems: list[dict[str, Any]] = []
    for raw_system in systems:
        system = deepcopy(dict(raw_system))
        rebound = {"constrained_by": [], "excludes": []}
        for old_kind in rebound:
            edges = system.get(old_kind)
            if not isinstance(edges, list) or any(
                not isinstance(edge, Mapping) for edge in edges
            ):
                raise ValueError("Semantic completion policy edges are malformed")
            for raw_edge in edges:
                edge = deepcopy(dict(raw_edge))
                old_fact = provisional.get(str(edge.get("object_id") or ""))
                if (
                    old_fact is None
                    or _POLICY_EDGE_KIND.get(str(old_fact.get("kind") or "")) != old_kind
                ):
                    raise ValueError("Semantic completion policy edge has an invalid object")
                matches = [
                    fact for fact in settled
                    if _refs_overlap(
                        edge.get("source_refs"), fact.get("source_refs"),
                        evidence_sources=evidence_sources,
                    )
                ]
                if len(matches) != 1:
                    raise ValueError("Semantic completion policy edge lacks one settled object")
                fact = matches[0]
                new_kind = _POLICY_EDGE_KIND[str(fact["kind"])]
                edge["object_id"] = str(fact["fact_id"])
                rebound[new_kind].append(edge)
        system.update(rebound)
        aligned_systems.append(system)
    completion["internal_systems"] = aligned_systems
    return completion


def _fact_index(source: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    facts = source.get("facts")
    if not isinstance(facts, list) or any(not isinstance(row, Mapping) for row in facts):
        raise ValueError("Semantic completion policy source facts are malformed")
    result = {str(row.get("fact_id") or ""): dict(row) for row in facts}
    if "" in result or len(result) != len(facts):
        raise ValueError("Semantic completion policy source fact IDs are malformed")
    return result


def _refs_overlap(
    left: Any, right: Any, *, evidence_sources: Mapping[str, str]
) -> bool:
    if (
        not isinstance(left, list) or not left
        or not isinstance(right, list) or not right
        or any(not isinstance(row, Mapping) for row in [*left, *right])
    ):
        raise ValueError("Semantic completion policy edge citations are malformed")
    return any(
        semantic_source_refs_overlap(
            left_ref, right_ref, evidence_sources=evidence_sources
        )
        for left_ref in left
        for right_ref in right
    )


__all__ = ["align_completion_policy_edges"]
