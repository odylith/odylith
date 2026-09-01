"""Canonical Greenfield projection graph for artifact-native views.

The graph is a small read-only view over accepted typed intent and its
workstream row. It deliberately does not synthesize a second generic
``domain_intelligence`` narrative that downstream surfaces could reinterpret.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


@dataclass(frozen=True)
class DomainIntelligenceGraph:
    """Typed canonical facts grouped for artifact-specific projections."""

    family: str
    primary_lens: str
    state_objects: tuple[str, ...]
    actors: tuple[str, ...]
    operators: tuple[str, ...]
    approvers: tuple[str, ...]
    risk_owners: tuple[str, ...]
    proof_standards: tuple[str, ...]
    invariants: tuple[str, ...]
    workflows: tuple[str, ...]
    exception_paths: tuple[str, ...]
    evidence_types: tuple[str, ...]
    validation_obligations: tuple[str, ...]
    glossary: tuple[str, ...]
    maturity_and_origin: tuple[str, ...]


def canonical_graph_from_workstream(
    *,
    row: Mapping[str, Any] | None = None,
    proposal: Mapping[str, Any] | None = None,
) -> DomainIntelligenceGraph:
    """Project accepted intent and one workstream without inventing a new schema."""

    workstream = row or {}
    intent = _intent(proposal)
    title = clean_text(workstream.get("title")) or clean_text(intent.get("title"))
    state_object = clean_text(intent.get("state_object"))
    evidence_record = clean_text(intent.get("evidence_record"))
    first_path = clean_text(intent.get("first_path"))
    first_slice = clean_text(workstream.get("recommended_first_slice"))
    proof_boundary = clean_text(intent.get("proof_boundary"))
    human_actors = _intent_rows(intent, "human_actors")
    internal_systems = _intent_rows(intent, "internal_systems")
    external_systems = _intent_rows(intent, "external_systems")
    constraints = _intent_rows(intent, "operational_constraints")
    assumptions = _intent_rows(intent, "assumptions")
    ambiguities = _intent_rows(intent, "ambiguities")
    non_goals = _intent_rows(intent, "non_goals")
    validation = _row_rows(workstream, "validation")
    interfaces = _row_rows(workstream, "interfaces")
    dependencies = _row_rows(workstream, "dependencies")
    source_requirements = _intent_rows(intent, "source_requirements")

    state_objects = _rows(state_object)
    evidence = _rows(evidence_record, *source_requirements)
    proof = _rows(proof_boundary, evidence_record, *validation)
    workflows = _rows(first_path, first_slice)
    invariants = _rows(*constraints)
    exceptions = _rows(*ambiguities, *non_goals)
    origin = _rows(*assumptions, *external_systems, *dependencies)
    glossary = _rows(state_object, evidence_record, *internal_systems)

    return DomainIntelligenceGraph(
        family=slugify(title).replace("-", "_") or "greenfield_project",
        primary_lens=title or "Project",
        state_objects=tuple(state_objects),
        actors=tuple(human_actors),
        operators=tuple(interfaces),
        approvers=(),
        risk_owners=(),
        proof_standards=tuple(proof),
        invariants=tuple(invariants),
        workflows=tuple(workflows),
        exception_paths=tuple(exceptions),
        evidence_types=tuple(evidence),
        validation_obligations=tuple(validation),
        glossary=tuple(glossary),
        maturity_and_origin=tuple(origin),
    )


def _intent(proposal: Mapping[str, Any] | None) -> Mapping[str, Any]:
    value = (proposal or {}).get("intent") if isinstance(proposal, Mapping) else None
    return value if isinstance(value, Mapping) else {}


def _intent_rows(intent: Mapping[str, Any], key: str) -> list[str]:
    return _rows(*text_values(intent.get(key)))


def _row_rows(row: Mapping[str, Any], key: str) -> list[str]:
    return _rows(*text_values(row.get(key)))


def _rows(*values: str) -> list[str]:
    return unique_text(clean_text(value) for value in values if clean_text(value))


__all__ = ["DomainIntelligenceGraph", "canonical_graph_from_workstream"]
