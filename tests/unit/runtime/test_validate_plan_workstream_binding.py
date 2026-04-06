from __future__ import annotations

from pathlib import Path

from odylith.runtime.governance import validate_plan_workstream_binding as validator


_SECTIONS = (
    "Problem",
    "Customer",
    "Opportunity",
    "Proposed Solution",
    "Scope",
    "Non-Goals",
    "Risks",
    "Dependencies",
    "Success Metrics",
    "Validation",
    "Rollout",
    "Why Now",
    "Product View",
    "Impacted Components",
    "Interface Changes",
    "Migration/Compatibility",
    "Test Strategy",
    "Open Questions",
)


def _idea_text(*, idea_id: str, status: str, promoted_to_plan: str) -> str:
    sections = "\n\n".join(f"## {section}\nDetails." for section in _SECTIONS)
    return (
        f"status: {status}\n\n"
        f"idea_id: {idea_id}\n\n"
        "title: Test Idea\n\n"
        "date: 2026-03-03\n\n"
        "priority: P1\n\n"
        "commercial_value: 4\n\n"
        "product_impact: 4\n\n"
        "market_value: 4\n\n"
        "impacted_lanes: both\n\n"
        "impacted_parts: governance\n\n"
        "sizing: M\n\n"
        "complexity: Medium\n\n"
        "ordering_score: 100\n\n"
        "ordering_rationale: deterministic governance\n\n"
        "confidence: high\n\n"
        "founder_override: no\n\n"
        f"promoted_to_plan: {promoted_to_plan}\n\n"
        "workstream_reopens:\n\n"
        "workstream_reopened_by:\n\n"
        "workstream_split_from:\n\n"
        "workstream_split_into:\n\n"
        "workstream_merged_into:\n\n"
        "workstream_merged_from:\n\n"
        "supersedes:\n\n"
        "superseded_by:\n\n"
        f"{sections}\n"
    )


def _write_plan_index(root: Path, *, backlog_id: str) -> Path:
    plan_index = root / "odylith" / "technical-plans" / "INDEX.md"
    plan_index.parent.mkdir(parents=True, exist_ok=True)
    plan_index.write_text(
        (
            "# Plan Index\n\n"
            "## Active Plans\n\n"
            "| Plan | Status | Created | Updated | Backlog |\n"
            "| --- | --- | --- | --- | --- |\n"
            f"| `odylith/technical-plans/in-progress/2026-03-03-test-plan.md` | In progress | 2026-03-03 | 2026-03-03 | `{backlog_id}` |\n"
        ),
        encoding="utf-8",
    )
    plan_path = root / "odylith" / "technical-plans" / "in-progress" / "2026-03-03-test-plan.md"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("Status: In progress\n", encoding="utf-8")
    return plan_index


def _write_idea(root: Path, *, idea_id: str, status: str, promoted_to_plan: str) -> Path:
    idea_path = root / "odylith" / "radar" / "source" / "ideas" / "2026-03" / "2026-03-03-test-idea.md"
    idea_path.parent.mkdir(parents=True, exist_ok=True)
    idea_path.write_text(
        _idea_text(idea_id=idea_id, status=status, promoted_to_plan=promoted_to_plan),
        encoding="utf-8",
    )
    return idea_path


def test_validator_fails_for_touched_active_plan_with_unbound_backlog(tmp_path: Path) -> None:
    plan_index = _write_plan_index(tmp_path, backlog_id="-")
    (tmp_path / "odylith" / "radar" / "source" / "ideas").mkdir(parents=True, exist_ok=True)

    errors = validator.validate_plan_workstream_binding(
        repo_root=tmp_path,
        plan_index_path=plan_index,
        ideas_root=tmp_path / "odylith" / "radar" / "source" / "ideas",
        changed_paths=("odylith/technical-plans/in-progress/2026-03-03-test-plan.md",),
    )
    assert any("must set Backlog to a workstream id" in row for row in errors)


def test_validator_fails_when_bound_workstream_not_execution_ready(tmp_path: Path) -> None:
    plan_index = _write_plan_index(tmp_path, backlog_id="B-201")
    _write_idea(
        tmp_path,
        idea_id="B-201",
        status="queued",
        promoted_to_plan="",
    )

    errors = validator.validate_plan_workstream_binding(
        repo_root=tmp_path,
        plan_index_path=plan_index,
        ideas_root=tmp_path / "odylith" / "radar" / "source" / "ideas",
        changed_paths=("odylith/technical-plans/in-progress/2026-03-03-test-plan.md",),
    )
    assert any("must be in" in row and "queued" in row for row in errors)


def test_validator_passes_for_touched_execution_bound_plan(tmp_path: Path) -> None:
    plan_index = _write_plan_index(tmp_path, backlog_id="B-201")
    _write_idea(
        tmp_path,
        idea_id="B-201",
        status="planning",
        promoted_to_plan="odylith/technical-plans/in-progress/2026-03-03-test-plan.md",
    )

    errors = validator.validate_plan_workstream_binding(
        repo_root=tmp_path,
        plan_index_path=plan_index,
        ideas_root=tmp_path / "odylith" / "radar" / "source" / "ideas",
        changed_paths=("odylith/technical-plans/in-progress/2026-03-03-test-plan.md",),
    )
    assert errors == []


def test_validator_ignores_closed_plan_move_when_in_progress_file_missing(tmp_path: Path) -> None:
    plan_index = tmp_path / "odylith" / "technical-plans" / "INDEX.md"
    plan_index.parent.mkdir(parents=True, exist_ok=True)
    plan_index.write_text(
        (
            "# Plan Index\n\n"
            "## Active Plans\n\n"
            "| Plan | Status | Created | Updated | Backlog |\n"
            "| --- | --- | --- | --- | --- |\n"
        ),
        encoding="utf-8",
    )
    (tmp_path / "odylith" / "radar" / "source" / "ideas").mkdir(parents=True, exist_ok=True)
    # Simulate closeout move: old in-progress plan path is now gone.
    (tmp_path / "odylith" / "technical-plans" / "in-progress").mkdir(parents=True, exist_ok=True)

    errors = validator.validate_plan_workstream_binding(
        repo_root=tmp_path,
        plan_index_path=plan_index,
        ideas_root=tmp_path / "odylith" / "radar" / "source" / "ideas",
        changed_paths=("odylith/technical-plans/in-progress/2026-03-03-test-plan.md",),
    )
    assert errors == []
