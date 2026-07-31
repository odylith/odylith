from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence.greenfield_actor_terms import is_automated_actor
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_action_context
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import omit_actor_from_material_action
from odylith.runtime.domain_intelligence.greenfield_actor_terms import starts_with_automated_actor


@pytest.mark.parametrize(
    "actor",
    ("AI reviewer", "Automated reviewer", "Coordinator bot", "Virtual assistant", "AI-powered agent"),
)
def test_automated_actor_detection_rejects_automation_labels(actor: str) -> None:
    assert is_automated_actor(actor)


@pytest.mark.parametrize(
    ("first_path", "expected"),
    (
        ("An AI assistant assembles approved fragments.", True),
        ("A coordinator bot assembles approved fragments.", True),
        ("An AI research assistant assembles approved fragments.", False),
        ("An operator uses an AI assistant to assemble approved fragments.", False),
    ),
)
def test_leading_automated_actor_classifier_stops_at_the_first_action(first_path: str, expected: bool) -> None:
    assert starts_with_automated_actor(first_path) is expected


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


@pytest.mark.parametrize("actor", ("Permit clerks", "Extension publishers", "Lab operators"))
def test_human_actor_signal_recognizes_domain_role_labels(actor: str) -> None:
    assert has_human_actor_signal(actor)


def test_human_actor_signal_rejects_short_connective_suffixes() -> None:
    assert not has_human_actor_signal("booking workspace for")


@pytest.mark.parametrize(
    "actor_clause",
    (
        "A homeowner enters address details",
        "The patient logs a new activity",
        "A resident can submit a repair request",
        "Experimental physicists who coordinate calibration work",
        "Teachers prepare experiments",
    ),
)
def test_human_actor_signal_uses_explicit_actor_action_context(actor_clause: str) -> None:
    assert has_human_actor_signal(actor_clause)


@pytest.mark.parametrize(
    "label",
    ("homeowner", "patient", "resident", "solar", "solar system records a result"),
)
def test_human_actor_signal_does_not_promote_bare_or_system_nouns(label: str) -> None:
    assert not has_human_actor_signal(label)


@pytest.mark.parametrize(
    ("actor", "action"),
    (
        ("A homeowner", "captures roof details"),
        ("Teachers", "prepare experiments"),
        ("Experimental physicists", "coordinate calibration work"),
    ),
)
def test_human_actor_action_context_respects_the_proposed_split(actor: str, action: str) -> None:
    assert has_human_actor_action_context(actor, action)


def test_human_actor_action_context_rejects_an_action_phrase_as_the_actor() -> None:
    assert not has_human_actor_action_context(
        "Teachers prepare experiments students",
        "acknowledge hazards",
    )


@pytest.mark.parametrize(
    ("actor", "action"),
    (
        ("Entanglement", "links calibration"),
        ("Baseline", "routes operator notes"),
        ("Research nurses verify participant consent", "capture symptom evidence"),
    ),
)
def test_human_actor_action_context_rejects_technical_or_embedded_action_subjects(
    actor: str,
    action: str,
) -> None:
    assert not has_human_actor_action_context(actor, action)


@pytest.mark.parametrize("label", ("message broker", "event router"))
def test_human_actor_signal_rejects_infrastructure_suffix_nouns(label: str) -> None:
    assert not has_human_actor_signal(label)


@pytest.mark.parametrize(
    "label",
    ("Cooking Robot Controller", "Water-rights Hearing Evidence Preparation"),
)
def test_human_actor_signal_rejects_system_and_title_nouns(label: str) -> None:
    assert not has_human_actor_signal(label)
