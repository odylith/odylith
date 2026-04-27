from __future__ import annotations

from pathlib import Path

from odylith.runtime.orchestration import subagent_tuning_surface


def test_tuning_surface_marks_empty_feedback_as_scope_not_failure(tmp_path: Path) -> None:
    payload = subagent_tuning_surface.build_tuning_surface(
        repo_root=tmp_path,
        state_payload={
            "version": "v1",
            "outcome_counts": {"analysis_high": {}},
            "family_outcome_counts": {"analysis_review": {"analysis_high": {}}},
            "applied_outcome_keys": {},
        },
        component_id="subagent-router",
        applied_key="applied_outcome_keys",
    )

    assert payload["component_id"] == "subagent-router"
    assert payload["tuning_scope"] == "adaptive_feedback_only"
    assert payload["tuning_state"] == "no_feedback_recorded"
    assert "not proof that routing" in payload["tuning_note"]
    assert payload["live_orchestration_adoption"]["status"] in {"no_history", "active"}


def test_tuning_surface_detects_recorded_feedback(tmp_path: Path) -> None:
    payload = subagent_tuning_surface.build_tuning_surface(
        repo_root=tmp_path,
        state_payload={
            "version": "v1",
            "outcome_counts": {"single_leaf": {"success": 1}},
            "family_outcome_counts": {},
            "applied_feedback_keys": {},
        },
        component_id="subagent-orchestrator",
        applied_key="applied_feedback_keys",
    )

    assert payload["tuning_state"] == "feedback_recorded"
