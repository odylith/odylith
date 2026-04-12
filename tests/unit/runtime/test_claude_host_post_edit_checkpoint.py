from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

from odylith.runtime.surfaces import claude_host_post_edit_checkpoint


def test_should_refresh_returns_true_for_governed_paths() -> None:
    assert claude_host_post_edit_checkpoint.should_refresh("odylith/radar/source/queued/B-999.md") is True
    assert claude_host_post_edit_checkpoint.should_refresh("odylith/technical-plans/in-progress/2026-04/plan.md") is True
    assert claude_host_post_edit_checkpoint.should_refresh("odylith/casebook/bugs/CB-123.md") is True
    assert claude_host_post_edit_checkpoint.should_refresh("odylith/registry/source/components/foo/CURRENT_SPEC.md") is True
    assert claude_host_post_edit_checkpoint.should_refresh("odylith/atlas/source/diagram.mmd") is True


def test_should_refresh_skips_non_governed_paths_and_agents_files() -> None:
    assert claude_host_post_edit_checkpoint.should_refresh("src/odylith/cli.py") is False
    assert claude_host_post_edit_checkpoint.should_refresh("odylith/radar/source/AGENTS.md") is False
    assert claude_host_post_edit_checkpoint.should_refresh("odylith/registry/source/CLAUDE.md") is False
    assert claude_host_post_edit_checkpoint.should_refresh("") is False


def test_edited_path_returns_relative_token(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    (project / "odylith" / "radar" / "source").mkdir(parents=True)
    target = project / "odylith" / "radar" / "source" / "queued.md"
    target.write_text("# stub\n", encoding="utf-8")

    payload = {"tool_input": {"file_path": str(target)}}
    token = claude_host_post_edit_checkpoint.edited_path(payload=payload, project_dir=project)
    assert token == "odylith/radar/source/queued.md"


def test_edited_path_ignores_files_outside_project(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    other = tmp_path / "other-file.md"
    other.write_text("# stub\n", encoding="utf-8")
    payload = {"tool_input": {"file_path": str(other)}}
    assert claude_host_post_edit_checkpoint.edited_path(payload=payload, project_dir=project) == ""


def test_main_refreshes_governance_for_governed_edit(monkeypatch, tmp_path: Path, capsys) -> None:
    project = tmp_path / "repo"
    (project / "odylith" / "radar" / "source").mkdir(parents=True)
    target = project / "odylith" / "radar" / "source" / "queued.md"
    target.write_text("# stub\n", encoding="utf-8")

    captured: list[tuple[str, list[str], int]] = []

    def _fake_run_odylith(*, project_dir, args, timeout=180):
        captured.append((str(project_dir), list(args), timeout))
        return subprocess.CompletedProcess(args, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(
        claude_host_post_edit_checkpoint.claude_host_shared,
        "run_odylith",
        _fake_run_odylith,
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool_input": {"file_path": str(target)}})),
    )

    exit_code = claude_host_post_edit_checkpoint.main(["--repo-root", str(project)])

    assert exit_code == 0
    assert len(captured) == 1
    project_dir, args, timeout = captured[0]
    assert args[0] == "sync"
    assert "--impact-mode" in args and "selective" in args
    assert "odylith/radar/source/queued.md" in args
    assert timeout == 180
    payload = json.loads(capsys.readouterr().out)
    assert "Odylith governance refresh completed" in payload["systemMessage"]


def test_main_skips_non_governed_edits_silently(monkeypatch, tmp_path: Path, capsys) -> None:
    project = tmp_path / "repo"
    (project / "src").mkdir(parents=True)
    target = project / "src" / "main.py"
    target.write_text("# stub\n", encoding="utf-8")

    called: list[bool] = []

    monkeypatch.setattr(
        claude_host_post_edit_checkpoint.claude_host_shared,
        "run_odylith",
        lambda **kwargs: called.append(True),
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool_input": {"file_path": str(target)}})),
    )

    exit_code = claude_host_post_edit_checkpoint.main(["--repo-root", str(project)])

    assert exit_code == 0
    assert called == []
    assert capsys.readouterr().out == ""
