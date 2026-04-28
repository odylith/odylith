from __future__ import annotations

from pathlib import Path

from odylith.runtime.governance import legacy_backlog_normalization
from odylith.runtime.governance import sync_workstream_artifacts


def test_backlog_summary_counts_duplicates_and_suppresses_long_tail() -> None:
    summary = legacy_backlog_normalization.summarize_backlog_contract_errors(
        (
            "odylith/radar/source/INDEX.md: reorder rationale for `B-001` missing `- why now:`",
            "odylith/radar/source/INDEX.md: reorder rationale for `B-001` missing `- why now:`",
            "odylith/radar/source/INDEX.md: reorder rationale for `B-002` missing `- tradeoff:`",
            "odylith/radar/source/ideas/b-003.md: `ordering_score` is invalid",
            "odylith/radar/source/ideas/b-004.md: status must be one of queued, implementation, parked, finished",
            "odylith/radar/source/ideas/b-005.md: missing active plan row",
        ),
        limit=3,
    )

    assert summary == (
        "2x odylith/radar/source/INDEX.md: reorder rationale for `B-001` missing `- why now:`",
        "odylith/radar/source/INDEX.md: reorder rationale for `B-002` missing `- tradeoff:`",
        "odylith/radar/source/ideas/b-003.md: `ordering_score` is invalid",
        "2 more unique backlog-contract error(s) suppressed in the compact summary.",
    )


def test_backlog_next_actions_route_by_failure_class() -> None:
    metadata_action = legacy_backlog_normalization.backlog_next_action(
        errors=("odylith/radar/source/ideas/b-003.md: `ordering_score` is invalid",)
    )
    rationale_action = legacy_backlog_normalization.backlog_next_action(
        errors=("odylith/radar/source/INDEX.md: reorder rationale for `B-001` missing `- why now:`",)
    )
    table_action = legacy_backlog_normalization.backlog_next_action(
        errors=("odylith/radar/source/INDEX.md: B-001 missing from index",)
    )
    fallback_action = legacy_backlog_normalization.backlog_next_action(
        errors=("odylith/radar/source/INDEX.md: unexpected cross-record invariant failed",)
    )

    assert "metadata, status, and plan bindings" in metadata_action
    assert "--check-only" in metadata_action
    assert "normalized rationale blocks" in rationale_action
    assert "--force" in rationale_action
    assert "ranked backlog tables" in table_action
    assert "--force" in table_action
    assert "reported backlog contract fixes" in fallback_action
    assert "--check-only" in fallback_action


def test_execute_plan_failure_uses_step_specific_next_command(tmp_path: Path, capsys) -> None:
    plan = sync_workstream_artifacts.ExecutionPlan(
        headline="runtime repair required",
        steps=(
            sync_workstream_artifacts.ExecutionStep(
                label="Repair runtime state before sync.",
                action=lambda: 2,
                next_command_on_failure="odylith doctor --repo-root . --repair",
            ),
        ),
        dirty_overlap=(),
    )

    rc = sync_workstream_artifacts._execute_plan(  # noqa: SLF001
        repo_root=tmp_path,
        plan_name="workstream sync",
        plan=plan,
        run_impl=lambda **_: 0,
        runtime_fallback_used=False,
    )
    output = capsys.readouterr().out

    assert rc == 2
    assert "workstream sync failed" in output
    assert "- next: odylith doctor --repo-root . --repair" in output
    assert "odylith sync --repo-root . --force" not in output
