"""Contract tests for typed, adaptive Greenfield artifact depth."""

from odylith.runtime.domain_intelligence.greenfield_artifact_depth import (
    plan_greenfield_artifact_depth,
)


def test_one_actor_and_one_system_without_boundary_evidence_stay_simple() -> None:
    plan = plan_greenfield_artifact_depth(
        actor_count=1,
        internal_system_count=1,
        external_system_count=0,
        ambiguity_count=0,
        non_goal_count=0,
        evidence_requirement_count=1,
        operational_constraint_count=1,
    )

    assert plan.complexity_band == "simple"
    assert plan.workstream_roles == ("project",)
    assert plan.diagram_roles == (
        "context",
        "sequence",
        "state_evidence",
    )


def test_distinct_actors_systems_boundaries_and_proof_earn_deeper_artifacts() -> None:
    plan = plan_greenfield_artifact_depth(
        actor_count=4,
        internal_system_count=4,
        external_system_count=3,
        ambiguity_count=2,
        non_goal_count=1,
        evidence_requirement_count=2,
        operational_constraint_count=2,
    )

    assert plan.complexity_band == "structured"
    assert plan.workstream_roles == ("project", "workflow", "boundary", "proof")
    assert plan.diagram_roles == (
        "context",
        "sequence",
        "state_evidence",
        "component_boundaries",
    )


def test_multiple_non_goals_earn_a_boundary_workstream_without_duplicate_views() -> None:
    plan = plan_greenfield_artifact_depth(
        actor_count=1,
        internal_system_count=1,
        external_system_count=0,
        ambiguity_count=0,
        non_goal_count=2,
        evidence_requirement_count=1,
        operational_constraint_count=1,
    )

    assert plan.workstream_roles == ("project", "boundary")
    assert plan.diagram_roles == (
        "context",
        "sequence",
        "state_evidence",
        "component_boundaries",
    )


def test_ambiguity_without_boundary_evidence_does_not_invent_a_boundary_view() -> None:
    plan = plan_greenfield_artifact_depth(
        actor_count=1,
        internal_system_count=1,
        external_system_count=0,
        ambiguity_count=3,
        non_goal_count=0,
        evidence_requirement_count=1,
        operational_constraint_count=1,
    )

    assert plan.workstream_roles == ("project",)
    assert plan.diagram_roles == ("context", "sequence", "state_evidence")
