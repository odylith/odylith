from __future__ import annotations

from types import SimpleNamespace

from odylith import cli
from odylith.runtime.common.dirty_overlap import summarize_dirty_overlap


def test_lifecycle_plan_condenses_dirty_overlap_for_install_reinstall_and_upgrade(capsys) -> None:
    for command in ("install", "reinstall", "upgrade"):
        plan = SimpleNamespace(
            command=command,
            headline="preview",
            steps=(),
            dirty_overlap=("M one", "M two", "M three", "M four", "M five"),
            notes=(),
        )

        cli._print_lifecycle_plan(plan, dry_run=True, verbose=False)  # noqa: SLF001

    output = capsys.readouterr().out

    assert output.count("5 local worktree entries overlap this mutation plan.") == 3
    assert output.count("... 1 more overlap entries hidden; rerun with --verbose to show the full set.") == 3
    assert "install dry-run" in output
    assert "reinstall dry-run" in output
    assert "upgrade dry-run" in output
    assert "M five" not in output


def test_lifecycle_plan_verbose_prints_full_overlap_for_all_lifecycle_commands(capsys) -> None:
    for command in ("install", "reinstall", "upgrade"):
        plan = SimpleNamespace(
            command=command,
            headline="preview",
            steps=(),
            dirty_overlap=("M one", "M two", "M three", "M four", "M five"),
            notes=(),
        )

        cli._print_lifecycle_plan(plan, dry_run=True, verbose=True)  # noqa: SLF001

    output = capsys.readouterr().out

    assert output.count("M five") == 3
    assert "hidden; rerun with --verbose" not in output


def test_lifecycle_plan_write_mode_hides_internal_step_graph_without_verbose(capsys) -> None:
    plan = SimpleNamespace(
        command="install",
        headline="Preview the Odylith install lifecycle.",
        steps=(
            SimpleNamespace(
                label="Materialize managed guidance.",
                mutation_classes=("managed_guidance",),
                paths=("AGENTS.md", "CLAUDE.md"),
                detail="Internal install detail.",
            ),
            SimpleNamespace(
                label="Stage managed runtime.",
                mutation_classes=("runtime_state",),
                paths=(".odylith/install.json",),
                detail="Internal runtime detail.",
            ),
        ),
        dirty_overlap=(),
        notes=("Dry-run detail.",),
    )

    cli._print_lifecycle_plan(plan, dry_run=False, verbose=False)  # noqa: SLF001
    output = capsys.readouterr().out

    assert "install plan" in output
    assert "- steps: 2 planned; progress follows." in output
    assert "Materialize managed guidance" not in output
    assert "mutation_classes:" not in output
    assert "Dry-run detail." not in output


def test_dirty_overlap_summary_groups_runtime_truth_guidance_generated_and_other_paths() -> None:
    summary = summarize_dirty_overlap(
        (
            "M .odylith/install.json",
            "M odylith/radar/radar.html",
            "M odylith/radar/source/INDEX.md",
            "M AGENTS.md",
            "M app/main.py",
        ),
        verbose=False,
        sample_size=2,
    )

    assert summary[0] == "5 local worktree entries overlap this mutation plan."
    assert "generated_surfaces=1" in summary[1]
    assert "managed_guidance=1" in summary[1]
    assert "other=1" in summary[1]
    assert "repo_truth=1" in summary[1]
    assert "runtime_state=1" in summary[1]
    assert "M .odylith/install.json" in summary
    assert "M odylith/radar/radar.html" in summary
    assert "M odylith/radar/source/INDEX.md" not in summary
    assert summary[-1] == "... 3 more overlap entries hidden; rerun with --verbose to show the full set."
