from __future__ import annotations

from odylith.runtime.surfaces import compass_narrative_runtime


def test_action_clause_for_narrative_keeps_leading_action_verb() -> None:
    clause = compass_narrative_runtime.action_clause_for_narrative(
        "harden release lane checks",
        normalize_action_task=lambda text: text,
    )

    assert clause == "harden release lane checks"


def test_action_clause_for_narrative_prefixes_land_when_needed() -> None:
    clause = compass_narrative_runtime.action_clause_for_narrative(
        "release lane checks",
        normalize_action_task=lambda text: text,
    )

    assert clause == "land release lane checks"


def test_timeline_clause_explains_heuristic_planning_risk() -> None:
    clause = compass_narrative_runtime.timeline_clause(
        eta_days=6,
        eta_source="heuristic",
        status="planning",
        has_execution_signal=False,
    )

    assert clause == "provisional at roughly 6 days while planning details stabilize"
