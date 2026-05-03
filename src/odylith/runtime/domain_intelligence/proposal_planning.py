"""Program, release, and UX planning helpers for greenfield proposals."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.archetypes import Archetype


def build_program_waves(archetype: Archetype, components: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    component_ids = [str(row.get("component_id", "")).strip() for row in components if str(row.get("component_id", "")).strip()]
    rows: list[dict[str, Any]] = []
    for index, wave in enumerate(archetype.waves, start=1):
        rows.append(
            {
                "wave": index,
                "label": wave.label,
                "goal": wave.goal,
                "validation": wave.validation,
                "component_focus": component_ids[: max(1, min(len(component_ids), index + 1))],
                "evidence_tier": "odylith_assumption",
            }
        )
    return rows


def release_id_for_title(intent_title: str) -> str:
    project_slug = slugify(intent_title)
    return slugify(f"release-{project_slug}-first") if project_slug else "release-greenfield-first"


def _correctness_milestone(archetype: Archetype) -> dict[str, str] | None:
    if archetype.archetype_id == "formal_proof":
        return {
            "name": "Proof obligations accepted",
            "exit_criteria": "Definitions, theorem statements, admitted lemmas, and checker command are reviewed before any proof is marked complete.",
        }
    if archetype.archetype_id == "computational_notebook":
        return {
            "name": "Reproducibility oracle accepted",
            "exit_criteria": "Dataset manifests, clean notebook execution order, reference outputs, and statistical assumptions are reviewed.",
        }
    if archetype.archetype_id == "simulation_modeling":
        return {
            "name": "Numerical oracle accepted",
            "exit_criteria": "Units, analytic/reference cases, tolerance bands, and convergence or stability checks are reviewed.",
        }
    if archetype.archetype_id == "scientific_pipeline":
        return {
            "name": "Pipeline provenance accepted",
            "exit_criteria": "Raw inputs, metadata, stage-level quality checks, and reference outputs are reviewed.",
        }
    if archetype.archetype_id == "geospatial_environmental":
        return {
            "name": "Spatial evidence accepted",
            "exit_criteria": "CRS, units, spatial extent, temporal coverage, and reference map fixtures are reviewed.",
        }
    if archetype.archetype_id == "ml_experiment_platform":
        return {
            "name": "Model evaluation oracle accepted",
            "exit_criteria": "Dataset split, baseline metrics, promotion thresholds, and error-slice checks are reviewed.",
        }
    if archetype.archetype_id == "science_math":
        return {
            "name": "Correctness oracle accepted",
            "exit_criteria": "Reference data, derivation notes, tolerance bands, or proof obligations are reviewed before implementation claims correctness.",
        }
    return None


def build_release_plan(intent_title: str, archetype: Archetype, waves: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    milestones = [
        {
            "name": f"{intent_title} proposal accepted",
            "exit_criteria": "Operator confirms assumptions, first slice, component map, and draft topology.",
        },
        {
            "name": "First governed implementation slice",
            "exit_criteria": "One user-visible or correctness-critical workflow has source, Registry ownership, Atlas topology, and tests.",
        },
        {
            "name": "Release candidate",
            "exit_criteria": "Backlog, Registry, Atlas, validation, and risk records are refreshed from observed source evidence.",
        },
    ]
    correctness = _correctness_milestone(archetype)
    if correctness is not None:
        milestones.insert(1, correctness)
    release_stages = [
        {
            "stage": f"wave-{row.get('wave')}",
            "label": str(row.get("label", "")).strip(),
            "release_gate": str(row.get("validation", "")).strip(),
        }
        for row in waves
        if isinstance(row, Mapping)
    ]
    return {
        "selector": "next",
        "label": "First governed release",
        "provisional_release_id": release_id_for_title(intent_title),
        "release_mode": "greenfield_provisional_until_source_backed",
        "strategy": "Create a local release target after proposal acceptance; keep waves as delivery checkpoints, not source-backed claims.",
        "wave_labels": [str(row.get("label", "")).strip() for row in waves if str(row.get("label", "")).strip()],
        "release_stages": release_stages,
        "recommended_first_release_slice": str(waves[0].get("label", "Discovery")).strip() if waves else "Discovery",
        "milestones": milestones,
        "evidence_tier": "odylith_assumption",
    }


def build_greenfield_ux(*, intent_title: str, source_posture: str, complexity: str) -> dict[str, Any]:
    return {
        "mode": "consumer_greenfield_proposal",
        "source_posture": source_posture,
        "complexity": complexity,
        "operator_sequence": [
            "review proposed assumptions and first slice",
            "edit or accept backlog, component, diagram, and release suggestions",
            "run the confirmation-gated apply command only after the proposal matches intent",
            "refresh governance surfaces and start implementation from the accepted first wave",
        ],
        "write_guardrail": "Proposal output is allowed from user intent; governed writes require explicit confirmation and stay user_intent until source evidence exists.",
        "next_best_action": f"Confirm or revise the first wave for {intent_title}; do not ask the operator to pre-fill every governance field.",
        "confirmation_options": [
            "apply as proposed",
            "revise scope/components/diagrams before apply",
            "answer open questions and regenerate",
        ],
        "existing_repo_difference": "Existing repos start from source-backed evidence; greenfield repos start from intent-backed proposal drafts and graduate records only after source or design evidence appears.",
    }
