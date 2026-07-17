from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence.greenfield_actor_terms import is_automated_actor
from odylith.runtime.domain_intelligence.greenfield_actor_terms import omit_actor_from_material_action


@pytest.mark.parametrize(
    "actor",
    ("AI reviewer", "Automated reviewer", "Coordinator bot", "Virtual assistant", "AI-powered agent"),
)
def test_automated_actor_detection_rejects_automation_labels(actor: str) -> None:
    assert is_automated_actor(actor)


@pytest.mark.parametrize(
    "actor",
    (
        "AI/ML engineer",
        "AI product manager",
        "Autonomous engineer",
        "Bot operator",
        "Field agent",
        "Review assistant",
        "Researcher",
    ),
)
def test_automated_actor_detection_preserves_human_role_labels(actor: str) -> None:
    assert not is_automated_actor(actor)


@pytest.mark.parametrize("actor", ("A person", "Someone", "The end user", "AI reviewer"))
def test_abstract_or_automated_actors_do_not_become_material_action_text(actor: str) -> None:
    assert omit_actor_from_material_action(actor)


@pytest.mark.parametrize("actor", ("Extension publishers", "Patient", "AI/ML engineer"))
def test_specific_human_actors_remain_material_action_context(actor: str) -> None:
    assert not omit_actor_from_material_action(actor)
