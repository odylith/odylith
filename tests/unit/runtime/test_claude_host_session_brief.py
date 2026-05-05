from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

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
    assert "interventions armed for Observation, Proposal, and Assist" in rendered


def test_render_session_brief_returns_empty_string_when_start_output_empty() -> None:
    rendered = claude_host_session_brief.render_session_brief(start_output_override="")
    assert rendered == ""


def test_render_session_brief_sanitizes_start_narrowing_output() -> None:
    start_output = """
odylith start
- lane: fallback
- reason: Need one code path.
{
  "context_packet": {
    "packet_state": "gated_ambiguous"
  }
}
"""

    rendered = claude_host_session_brief.render_session_brief(start_output_override=start_output)

    assert rendered == (
        "Odylith startup: needs a narrower target before implementation. "
        "Name one code path, workstream, component, bug, or file."
    )
    assert "fallback" not in rendered.casefold()
    assert "gated_ambiguous" not in rendered


def test_render_session_brief_eager_start_requests_json_packet(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, list[str], int]] = []

    def _fake_run_odylith(**kwargs: object) -> SimpleNamespace:
        calls.append(
            (
                str(kwargs["project_dir"]),
                list(kwargs["args"]),  # type: ignore[arg-type]
                int(kwargs["timeout"]),
            )
        )
        return SimpleNamespace(
            stdout=(
                "odylith start\n"
                "- lane: bootstrap\n"
                '{"selection_reason":"focused on B-083","recommended_commands":["odylith context --repo-root . B-083"]}'
            )
        )

    monkeypatch.setattr(claude_host_session_brief.claude_host_shared, "run_odylith", _fake_run_odylith)

    rendered = claude_host_session_brief.render_session_brief(repo_root=tmp_path, eager_start=True)

    assert "selection: focused on B-083" in rendered
    assert calls == [(str(tmp_path), ["start", "--repo-root", ".", "--json"], 20)]


def test_render_session_brief_uses_substrate_without_start(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_runtime_snapshot(repo_root)

    def _unexpected_run(**_: object) -> None:
        raise AssertionError("cached SessionStart fast path must not run odylith start")

    monkeypatch.setattr(claude_host_session_brief.claude_host_shared, "run_odylith", _unexpected_run)
    monkeypatch.setattr(
        claude_host_session_brief.host_intervention_support,
        "session_start_substrate_context",
        lambda **_: "Odylith startup substrate: context=host_intervention_context/observing.",
    )

    rendered = claude_host_session_brief.render_session_brief(repo_root=repo_root)

    assert "Odylith startup: snapshot: Claude hardening is live for B-083" in rendered
    assert "Odylith startup: active: B-083: Claude support hardening" in rendered
    assert "Odylith startup substrate: context=host_intervention_context/observing." in rendered
    assert "fast path used cached runtime state" not in rendered


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
