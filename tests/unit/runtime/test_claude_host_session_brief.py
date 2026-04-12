from __future__ import annotations

import json
import os
from pathlib import Path

from odylith.runtime.surfaces import claude_host_session_brief


def _write_runtime_snapshot(repo_root: Path) -> None:
    runtime_dir = repo_root / "odylith" / "compass" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "current.v1.json").write_text(
        json.dumps(
            {
                "generated_utc": "2026-04-11T12:00:00Z",
                "execution_focus": {
                    "global": {
                        "headline": "Claude hardening is live for B-083",
                        "workstreams": ["B-083"],
                    }
                },
                "current_workstreams": [
                    {"idea_id": "B-083", "title": "Claude support hardening"},
                ],
                "verified_scoped_workstreams": {"24h": ["B-083"]},
                "next_actions": [
                    {"idea_id": "B-083", "action": "Finish hooks and memory bridge"},
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_render_session_brief_summarizes_start_output() -> None:
    start_output = (
        "Odylith ready for this repo.\n"
        + json.dumps(
            {
                "selection_reason": "focused on B-083",
                "relevant_docs": ["odylith/CLAUDE.md"],
                "recommended_commands": ["./.odylith/bin/odylith context --repo-root . B-083"],
            }
        )
    )

    rendered = claude_host_session_brief.render_session_brief(
        start_output_override=start_output,
    )

    assert "Odylith startup:" in rendered
    assert "selection: focused on B-083" in rendered
    assert "relevant doc: odylith/CLAUDE.md" in rendered
    assert "next command: ./.odylith/bin/odylith context --repo-root . B-083" in rendered


def test_render_session_brief_returns_empty_string_when_start_output_empty() -> None:
    rendered = claude_host_session_brief.render_session_brief(start_output_override="")
    assert rendered == ""


def test_main_writes_project_memory_and_prints_summary(monkeypatch, tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    config_root = tmp_path / "claude-config"
    _write_runtime_snapshot(repo_root)

    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config_root))

    captured: list[tuple[Path, list[str]]] = []

    def _fake_render(*, repo_root: Path | str = ".", **_):
        captured.append((Path(repo_root), []))
        return (
            "Odylith startup: selection: focused on B-083\n"
            "Odylith startup: relevant doc: odylith/CLAUDE.md"
        )

    monkeypatch.setattr(claude_host_session_brief, "render_session_brief", _fake_render)

    exit_code = claude_host_session_brief.main(["--repo-root", str(repo_root)])

    assert exit_code == 0
    captured_out = capsys.readouterr().out
    assert "Odylith startup: selection: focused on B-083" in captured_out

    project_dirs = sorted((config_root / "projects").iterdir())
    assert len(project_dirs) == 1
    memory_dir = project_dirs[0] / "memory"
    governed_note = memory_dir / "odylith-governed-brief.md"
    assert governed_note.is_file()
    note_text = governed_note.read_text(encoding="utf-8")
    assert "Claude hardening is live for B-083" in note_text


def test_main_quiet_flag_suppresses_stdout_summary(monkeypatch, tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude-config"))
    _write_runtime_snapshot(repo_root)

    monkeypatch.setattr(
        claude_host_session_brief,
        "render_session_brief",
        lambda **_: "Odylith startup: selection: focused on B-083",
    )

    exit_code = claude_host_session_brief.main(["--repo-root", str(repo_root), "--quiet"])

    assert exit_code == 0
    assert capsys.readouterr().out == ""
