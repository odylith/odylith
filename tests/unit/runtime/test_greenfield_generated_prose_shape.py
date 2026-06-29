from __future__ import annotations

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.domain_intelligence.greenfield_generated_prose_shape import (
    gerund_actor_role_finite_action_splice,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues


def test_gerund_actor_role_detector_accepts_valid_proof_action_lists() -> None:
    value = (
        "Success proof includes capturing incident telemetry, preserving operator statements, "
        "mapping zone controls, and routing maintenance review."
    )

    assert not gerund_actor_role_finite_action_splice(value)


def test_gerund_actor_role_detector_accepts_role_words_inside_objects() -> None:
    value = (
        "capturing incident telemetry, preserving operator statements, mapping zone controls, "
        "and routing maintenance review"
    )

    assert not gerund_actor_role_finite_action_splice(value)


def test_gerund_actor_role_detector_rejects_actor_role_subject_splice() -> None:
    value = (
        "intaking coordinator records one lab batch and precursor lot, checking blocking observations, "
        "and approving or rejecting manufacturing readiness"
    )

    assert gerund_actor_role_finite_action_splice(value)


def test_copy_and_semantic_gates_allow_title_compound_user_roles() -> None:
    title_compound = "Finding Board User receives model behavior reports"

    assert generated_public_copy_issues("proposal.intent.human_actors.1", title_compound) == ()
    assert (
        generated_semantic_slop_issues(
            {"intent": {"human_actors": [title_compound]}},
            root="proposal",
        )
        == []
    )
