from __future__ import annotations

from odylith.runtime.artifact_quality.generated_copy_quality import has_inline_role_casing_drift
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_actions import actor_owned_outcome_event


def test_known_actor_outcome_event_preserves_inline_actor_casing() -> None:
    event = actor_owned_outcome_event(
        outcome="vulnerable dependency reports",
        outcome_action="receive vulnerable dependency reports",
        known_actors=(
            "Package Manager: uses the product to receive vulnerable dependency reports; "
            "the outcome stays clear enough to choose the next step",
        ),
    )

    assert event.startswith("the package manager can use the product to receive vulnerable dependency reports")
    assert "package Manager" not in event
    assert not has_inline_role_casing_drift(f"The workspace shows that {event}.")


def test_known_actor_outcome_event_preserves_protected_tokens() -> None:
    api_event = actor_owned_outcome_event(
        outcome="API evidence review",
        outcome_action="review API evidence",
        known_actors=("API Owner: uses the product to review API evidence before publishing proof",),
    )
    compound_event = actor_owned_outcome_event(
        outcome="GLP-1 companion risk notes",
        outcome_action="review GLP-1 companion risk notes",
        known_actors=("GLP-1 Companion Reviewer: uses the product to review GLP-1 companion risk notes",),
    )

    assert api_event.startswith("the API owner can use the product to review API evidence")
    assert compound_event.startswith("the GLP-1 companion reviewer can use the product")
    assert "API owner" in api_event
    assert "api" not in api_event
    assert "glp-1" not in compound_event
