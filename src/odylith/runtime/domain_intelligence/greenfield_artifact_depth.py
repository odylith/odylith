"""Choose Greenfield artifact depth from typed structural evidence."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class GreenfieldArtifactDepthPlan:
    """Candidate Radar roles and Atlas views justified by accepted structure."""

    complexity_band: str
    workstream_roles: tuple[str, ...]
    diagram_roles: tuple[str, ...]


def plan_greenfield_artifact_depth(
    *,
    actor_count: int,
    internal_system_count: int,
    external_system_count: int,
    ambiguity_count: int,
    non_goal_count: int,
    evidence_requirement_count: int,
    operational_constraint_count: int,
) -> GreenfieldArtifactDepthPlan:
    """Retain only artifacts with a distinct workflow, boundary, or proof job."""

    separate_workflow = actor_count > 1
    separate_boundary = (
        internal_system_count > 1
        or external_system_count > 0
        or ambiguity_count > 0
        or non_goal_count > 0
    )
    separate_proof = evidence_requirement_count > 1 or operational_constraint_count > 1

    workstream_roles = ["project"]
    if separate_workflow:
        workstream_roles.append("workflow")
    if separate_boundary:
        workstream_roles.append("boundary")
    if separate_proof:
        workstream_roles.append("proof")

    return GreenfieldArtifactDepthPlan(
        complexity_band="simple" if workstream_roles == ["project"] else "structured",
        workstream_roles=tuple(workstream_roles),
        diagram_roles=diagram_roles_for_workstream_roles(workstream_roles),
    )


def diagram_roles_for_workstream_roles(workstream_roles: Sequence[str]) -> tuple[str, ...]:
    """Return existing Atlas views justified by typed artifact-depth evidence."""

    roles = set(workstream_roles)
    diagrams = ["context", "sequence", "state_evidence"]
    if "boundary" in roles:
        diagrams.append("component_boundaries")
    return tuple(diagrams)


__all__ = [
    "GreenfieldArtifactDepthPlan",
    "diagram_roles_for_workstream_roles",
    "plan_greenfield_artifact_depth",
]
