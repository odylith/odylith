from __future__ import annotations

from odylith.runtime.surfaces import compass_narrative_runtime
from odylith.runtime.surfaces import compass_standup_fact_packets


def test_action_clause_for_narrative_keeps_leading_action_verb() -> None:
    clause = compass_narrative_runtime.action_clause_for_narrative(
        "harden release lane checks",
        normalize_action_task=lambda text: text,
    )

    assert clause == "harden release lane checks"


def test_action_clause_for_narrative_keeps_greenfield_action_verbs() -> None:
    for action in ("give the operator a review path", "let users retry", "prove the first path", "show release proof"):
        clause = compass_narrative_runtime.action_clause_for_narrative(
            action,
            normalize_action_task=lambda text: text,
        )

        assert clause == action


def test_action_clause_for_narrative_prefixes_land_when_needed() -> None:
    clause = compass_narrative_runtime.action_clause_for_narrative(
        "release lane checks",
        normalize_action_task=lambda text: text,
    )

    assert clause == "land release lane checks"


def test_direction_fact_falls_back_for_long_greenfield_direction_text() -> None:
    fact_text = compass_standup_fact_packets._direction_fact_text(
        label="Prove One Complete Cooking Robot Controller Path (B-001)",
        status_phrase="queued for execution",
        direction_text=(
            "prove the first release path: pick a recipe, validate that ingredients are staged "
            "and sensors are live, run the step sequence with closed-loop heat and timing control, "
            "and see a finished safe-to-serve state with emergency stop available throughout"
        ),
    )

    assert fact_text == "Prove One Complete Cooking Robot Controller Path (B-001) is queued for execution."


def test_direction_fact_keeps_short_greenfield_action_text() -> None:
    fact_text = compass_standup_fact_packets._direction_fact_text(
        label="Let Home Cook Pick a Recipe (B-002)",
        status_phrase="queued for execution",
        direction_text="turn the first actor-owned action into a complete, reviewable outcome",
    )

    assert fact_text.startswith("Turn the first actor-owned action")
    assert "Land turn" not in fact_text


def test_timeline_clause_explains_heuristic_planning_risk() -> None:
    clause = compass_narrative_runtime.timeline_clause(
        eta_days=6,
        eta_source="heuristic",
        status="planning",
        has_execution_signal=False,
    )

    assert clause == "provisional at roughly 6 days while planning details stabilize"
