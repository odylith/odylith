from __future__ import annotations

from pathlib import Path

from odylith.runtime.governance import validate_guidance_portability


def test_guidance_portability_fails_on_maintained_active_guidance(tmp_path: Path) -> None:
    root_doc = tmp_path / "README.md"
    root_doc.write_text("Run `PYTHONPATH=src .venv/bin/pytest -q tests/unit/test_cli.py`.\n", encoding="utf-8")

    errors = validate_guidance_portability.find_portability_errors(repo_root=tmp_path)

    assert len(errors) == 1
    assert str(root_doc.resolve()) in errors[0]


def test_guidance_portability_ignores_historical_done_records(tmp_path: Path) -> None:
    done_plan = tmp_path / "odylith" / "technical-plans" / "done" / "2026-03" / "historical.md"
    done_plan.parent.mkdir(parents=True, exist_ok=True)
    done_plan.write_text("`PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime`\n", encoding="utf-8")

    in_progress = tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-03" / "active.md"
    in_progress.parent.mkdir(parents=True, exist_ok=True)
    in_progress.write_text("Use `python -m pytest -q tests/unit/runtime`.\n", encoding="utf-8")

    errors = validate_guidance_portability.find_portability_errors(repo_root=tmp_path)

    assert errors == []


def test_guidance_portability_ignores_claude_worktree_copies(tmp_path: Path) -> None:
    tracked_claude = tmp_path / ".claude" / "CLAUDE.md"
    tracked_claude.parent.mkdir(parents=True, exist_ok=True)
    tracked_claude.write_text("Use `python -m pytest -q tests/unit/runtime`.\n", encoding="utf-8")

    worktree_copy = tmp_path / ".claude" / "worktrees" / "scratch" / "CLAUDE.md"
    worktree_copy.parent.mkdir(parents=True, exist_ok=True)
    worktree_copy.write_text("Use `.venv/bin/pytest -q tests/unit/runtime`.\n", encoding="utf-8")

    maintained_paths = validate_guidance_portability.maintained_guidance_paths(repo_root=tmp_path)
    errors = validate_guidance_portability.find_portability_errors(repo_root=tmp_path)

    assert tracked_claude.resolve() in maintained_paths
    assert worktree_copy.resolve() not in maintained_paths
    assert errors == []
