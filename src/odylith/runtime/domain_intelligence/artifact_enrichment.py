"""Artifact-native projections from the domain intelligence graph.

Domain intelligence is source substrate. It should shape Radar, Registry,
Atlas, Casebook, Compass, Project, and Tribunal records in each artifact's
native language instead of being pasted into every artifact as a generic
``Domain Intelligence`` section.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from odylith.runtime.common.value_coercion import dedupe_by_key
from odylith.runtime.domain_intelligence import artifact_tribunal_actors
from odylith.runtime.domain_intelligence.artifact_graph import DomainIntelligenceGraph
from odylith.runtime.domain_intelligence.artifact_graph import domain_graph_from_workstream
from odylith.runtime.domain_intelligence.artifact_graph import graph_layer as _layer
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


@dataclass(frozen=True)
class ArtifactEnrichment:
    radar_sections: dict[str, str]
    registry_contract: dict[str, tuple[str, ...]]
    atlas_contract: dict[str, tuple[str, ...]]
    plan_contract: dict[str, tuple[str, ...]]
    casebook_contract: dict[str, tuple[str, ...]]
    compass_contract: dict[str, tuple[str, ...]]
    project_contract: dict[str, tuple[str, ...]]
    tribunal_actors: tuple[dict[str, str], ...]


def build_artifact_enrichment(
    *,
    row: Mapping[str, Any],
    proposal: Mapping[str, Any] | None = None,
) -> ArtifactEnrichment:
    """Project one workstream's domain graph into artifact-native payloads."""

    graph = domain_graph_from_workstream(row.get("domain_intelligence"), row=row, proposal=proposal or {})
    return ArtifactEnrichment(
        radar_sections=radar_enrichment_sections(row=row, graph=graph),
        registry_contract=registry_projection(graph),
        atlas_contract=atlas_projection(graph),
        plan_contract=technical_plan_projection(graph),
        casebook_contract=casebook_projection(graph),
        compass_contract=compass_projection(graph),
        project_contract=project_projection(graph),
        tribunal_actors=artifact_tribunal_actors.tribunal_actor_projection(proposal or {"backlog": [row]}),
    )


def radar_enrichment_sections(
    *,
    row: Mapping[str, Any],
    graph: DomainIntelligenceGraph,
) -> dict[str, str]:
    """Return Radar-native sections shaped by domain intelligence."""

    first_slice = clean_text(row.get("recommended_first_slice")) or _first(graph.validation_obligations)
    sections: dict[str, str] = {}

    first_path = _bullets(
        [
            _sentence("First path", first_slice),
            _sentence("State object", _first(graph.state_objects)),
            _sentence("Boundary", _first(_layer(row, "scope")) or _first(graph.maturity_and_origin)),
        ]
    )
    if first_path:
        sections["First Path And Boundary"] = first_path

    proof = _bullets(
        [
            *_labelled_rows("Proof", graph.proof_standards[:4]),
            *_labelled_rows("Gate", graph.validation_obligations[:5]),
        ]
    )
    if proof:
        sections["Proof And Acceptance Gates"] = proof

    ownership = _bullets(
        [
            *_labelled_rows("Owner", graph.actors[:3]),
            *_labelled_rows("Risk", graph.risk_owners[:3]),
            *_labelled_rows("Control", graph.exception_paths[:3]),
        ]
    )
    if ownership:
        sections["Ownership And Risk"] = ownership

    return sections


def registry_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return component-spec shaping hints from the domain graph."""

    return {
        "boundaries": _tuple_limit([*graph.state_objects, *graph.invariants], 6),
        "interfaces": _tuple_limit(graph.operators, 5),
        "failure_modes": _tuple_limit(graph.exception_paths, 6),
        "proof_obligations": _tuple_limit(graph.proof_standards, 6),
    }


def atlas_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return diagram-shaping hints from the domain graph."""

    return {
        "actors": _tuple_limit(graph.actors, 6),
        "state_objects": _tuple_limit(graph.state_objects, 6),
        "flows": _tuple_limit(graph.workflows, 8),
        "controls": _tuple_limit([*graph.approvers, *graph.exception_paths], 8),
        "evidence": _tuple_limit(graph.evidence_types, 6),
    }


def technical_plan_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return implementation-plan shaping hints from the domain graph."""

    return {
        "sequence": _tuple_limit(graph.workflows, 6),
        "validation": _tuple_limit(graph.validation_obligations, 6),
        "rollback_or_recovery": _tuple_limit(graph.exception_paths, 5),
        "release_gates": _tuple_limit([*graph.proof_standards, *graph.invariants], 6),
    }


def casebook_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return bug-record shaping hints from the domain graph."""

    return {
        "impact_model": _tuple_limit(graph.risk_owners, 6),
        "affected_actor": _tuple_limit(graph.actors, 4),
        "repro_evidence": _tuple_limit(graph.evidence_types, 6),
        "prevention_rules": _tuple_limit([*graph.invariants, *graph.exception_paths], 6),
    }


def compass_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return current-work narration hints from the domain graph."""

    return {
        "work_language": _tuple_limit(graph.workflows, 5),
        "decision_language": _tuple_limit([*graph.approvers, *graph.operators], 5),
        "proof_boundary": _tuple_limit(graph.proof_standards, 5),
        "open_risk": _tuple_limit(graph.exception_paths, 5),
    }


def project_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return Project-tab shaping hints from the domain graph."""

    return {
        "lens": (graph.primary_lens,),
        "participants": _tuple_limit(graph.actors, 8),
        "state_objects": _tuple_limit(graph.state_objects, 6),
        "first_path": _tuple_limit(graph.workflows, 6),
        "proof": _tuple_limit(graph.proof_standards, 6),
        "unknowns": _tuple_limit(graph.exception_paths, 6),
    }


def _first(values: Sequence[str]) -> str:
    return clean_text(values[0]) if values else ""


def _sentence(label: str, value: str) -> str:
    text = _without_existing_label(label=label, value=clean_text(value))
    return f"{label}: {text}" if text else ""


def _without_existing_label(*, label: str, value: str) -> str:
    text = clean_text(value)
    if not text:
        return ""
    label_text = clean_text(label).casefold()
    lowered = text.casefold()
    prefix = f"{label_text}:"
    if lowered.startswith(prefix):
        return clean_text(text[len(prefix) :])
    return text


def _labelled_rows(label: str, values: Sequence[str]) -> list[str]:
    return [_sentence(label, value) for value in values if clean_text(value)]


def _bullets(values: Sequence[str]) -> str:
    rows = dedupe_by_key(
        (text for value in values if (text := clean_text(value))),
        _bullet_dedupe_key,
    )
    return "\n".join(f"- {row}" for row in rows)


def _bullet_dedupe_key(value: str) -> str:
    text = clean_text(value).casefold()
    text = re.sub(r"^(?:proof|gate|risk|control|owner|boundary|first path|state object):\s*", "", text)
    text = re.sub(r"\b(?:proof|gate|risk|control|owner|boundary)\b", "", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _tuple_limit(values: Sequence[str], limit: int) -> tuple[str, ...]:
    return tuple(unique_text(clean_text(value) for value in values if clean_text(value))[:limit])


__all__ = [
    "ArtifactEnrichment",
    "atlas_projection",
    "build_artifact_enrichment",
    "casebook_projection",
    "compass_projection",
    "project_projection",
    "radar_enrichment_sections",
    "registry_projection",
    "technical_plan_projection",
]
