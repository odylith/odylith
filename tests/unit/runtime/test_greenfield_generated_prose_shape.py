from odylith.runtime.domain_intelligence.greenfield_generated_prose_shape import (
    gerund_actor_role_finite_action_splice,
)


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
