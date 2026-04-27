from __future__ import annotations

from odylith.runtime.governance import workstream_progress


def test_derive_workstream_progress_keeps_implementation_zero_checklist_out_of_fake_percent() -> None:
    progress = workstream_progress.derive_workstream_progress(
        status="implementation",
        plan={"total_tasks": 15, "done_tasks": 0, "progress_ratio": 0.0},
    )

    assert progress["classification"] == "active_untracked"
    assert progress["display_progress_ratio"] is None
    assert progress["display_progress_label"] == "Checklist 0/15"
    assert progress["has_execution_underway"] is True
    assert progress["has_tracked_checklist_progress"] is False


def test_derive_workstream_progress_keeps_planning_zero_checklist_at_zero_percent() -> None:
    progress = workstream_progress.derive_workstream_progress(
        status="planning",
        plan={"total_tasks": 4, "done_tasks": 0, "progress_ratio": 0.0},
    )

    assert progress["classification"] == "not_started"
    assert progress["display_progress_ratio"] == 0.0
    assert progress["display_progress_label"] == "0% progress"


def test_derive_workstream_progress_prefers_closed_status_over_stale_plan_ratio() -> None:
    progress = workstream_progress.derive_workstream_progress(
        status="finished",
        plan={"total_tasks": 4, "done_tasks": 0, "progress_ratio": 0.0},
    )

    assert progress["classification"] == "closed"
    assert progress["display_progress_ratio"] == 1.0
    assert progress["display_progress_label"] == "100% progress"


def test_derive_workstream_progress_shows_partial_execution_percent_for_tracked_implementation() -> None:
    progress = workstream_progress.derive_workstream_progress(
        status="implementation",
        plan={"total_tasks": 14, "done_tasks": 11, "progress_ratio": 0.7857},
    )

    assert progress["classification"] == "tracked"
    assert progress["display_progress_ratio"] == 0.7857
    assert progress["display_progress_label"] == "79% progress"
    assert progress["checklist_label"] == "Checklist 11/14"


def test_summarize_active_progress_counts_untracked_implementation_separately() -> None:
    summary = workstream_progress.summarize_active_progress(
        [
            {"status": "implementation", "plan": {"total_tasks": 10, "done_tasks": 0, "progress_ratio": 0.0}},
            {"status": "implementation", "plan": {"total_tasks": 10, "done_tasks": 3, "progress_ratio": 0.3}},
            {"status": "planning", "plan": {"total_tasks": 5, "done_tasks": 0, "progress_ratio": 0.0}},
        ]
    )

    assert summary == {
        "closed": 0,
        "tracked": 1,
        "active_untracked": 1,
        "not_started": 1,
        "checklist_only": 0,
        "no_checklist": 0,
    }
