from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from odylith.runtime.surfaces import claude_host_precompact_snapshot as precompact
from odylith.runtime.surfaces import claude_host_shared


def _write_runtime_snapshot(repo_root: Path, payload: dict) -> Path:
    runtime_dir = repo_root / "odylith" / "compass" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    path = runtime_dir / "current.v1.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _clear_host_env(monkeypatch):
    for var in ("ODYLITH_HOST_FAMILY", "CLAUDE_PROJECT_DIR", "CODEX_HOME", "CODEX_HOST_RUNTIME"):
        monkeypatch.delenv(var, raising=False)


def test_snapshot_writes_markdown_under_memory_dir_override(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_runtime_snapshot(
        repo_root,
        {
            "generated_utc": "2026-04-11T12:00:00Z",
            "execution_focus": {
                "global": {
                    "headline": "B-085 Claude host Python bake",
                    "workstreams": ["B-085", "B-084"],
                }
            },
            "next_actions": [
                {"idea_id": "B-085", "action": "Wire claude subcommand dispatcher in cli.py"},
            ],
        },
    )
    memory_dir = tmp_path / "memory"
    written = precompact.write_claude_host_precompact_snapshot(
        repo_root=repo_root,
        memory_dir_override=memory_dir,
    )
    assert written is not None
    assert written == memory_dir / precompact.PRECOMPACT_SNAPSHOT_FILENAME
    body = written.read_text(encoding="utf-8")
    assert "# Odylith PreCompact Snapshot" in body
    assert "Headline: B-085 Claude host Python bake" in body
    assert "- B-085" in body
    assert "Wire claude subcommand dispatcher" in body
    assert "## Restart Hint" in body


def test_snapshot_degrades_on_missing_runtime(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    memory_dir = tmp_path / "memory"
    written = precompact.write_claude_host_precompact_snapshot(
        repo_root=repo_root,
        memory_dir_override=memory_dir,
    )
    assert written is not None
    body = written.read_text(encoding="utf-8")
    assert "Headline: (not present in Compass runtime snapshot)" in body
    assert "Active workstreams: (not present in Compass runtime snapshot)" in body
    assert "Brief freshness: no snapshot" in body


def test_snapshot_degrades_on_malformed_runtime(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    runtime_dir = repo_root / "odylith" / "compass" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "current.v1.json").write_text("{not json", encoding="utf-8")
    memory_dir = tmp_path / "memory"
    written = precompact.write_claude_host_precompact_snapshot(
        repo_root=repo_root,
        memory_dir_override=memory_dir,
    )
    assert written is not None
    body = written.read_text(encoding="utf-8")
    assert "Active workstreams: (not present in Compass runtime snapshot)" in body


def test_snapshot_is_idempotent(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_runtime_snapshot(
        repo_root,
        {
            "generated_utc": "2026-04-11T12:00:00Z",
            "execution_focus": {"global": {"headline": "h", "workstreams": ["B-001"]}},
        },
    )
    memory_dir = tmp_path / "memory"
    first = precompact.write_claude_host_precompact_snapshot(
        repo_root=repo_root,
        memory_dir_override=memory_dir,
        payload_override={
            "generated_utc": "2026-04-11T12:00:00Z",
            "execution_focus": {"global": {"headline": "h", "workstreams": ["B-001"]}},
            "next_actions": [],
        },
    )
    second = precompact.write_claude_host_precompact_snapshot(
        repo_root=repo_root,
        memory_dir_override=memory_dir,
        payload_override={
            "generated_utc": "2026-04-11T12:00:00Z",
            "execution_focus": {"global": {"headline": "h", "workstreams": ["B-001"]}},
            "next_actions": [],
        },
    )
    assert first is not None and second is not None
    assert first == second
    # Two calls with the same payload override must produce identical bodies except for the capture
    # timestamp line, which is inherently time-sensitive. Strip that line before comparing.
    def _strip_capture(text: str) -> str:
        return "\n".join(line for line in text.splitlines() if not line.startswith("- Snapshot captured:"))
    assert _strip_capture(first.read_text(encoding="utf-8")) == _strip_capture(second.read_text(encoding="utf-8"))


def test_snapshot_returns_none_when_memory_dir_cannot_be_created(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_runtime_snapshot(
        repo_root,
        {
            "generated_utc": "2026-04-11T12:00:00Z",
            "execution_focus": {"global": {"headline": "h", "workstreams": ["B-001"]}},
        },
    )
    bad_parent = tmp_path / "not-a-dir"
    bad_parent.write_text("file-where-dir-should-be", encoding="utf-8")
    written = precompact.write_claude_host_precompact_snapshot(
        repo_root=repo_root,
        memory_dir_override=bad_parent / "memory",
    )
    assert written is None


def test_build_snapshot_contains_expected_sections():
    payload = {
        "generated_utc": "2026-04-11T12:00:00Z",
        "execution_focus": {
            "global": {
                "headline": "Claude host bake",
                "workstreams": ["B-085", "B-084", "B-083"],
            }
        },
        "next_actions": [
            {"idea_id": "B-085", "action": "land statusline"},
            {"idea_id": "", "action": "log slice to Compass"},
        ],
    }
    body = precompact.build_precompact_snapshot(repo_root=".", payload_override=payload)
    assert "## Live Focus" in body
    assert "## Next Actions" in body
    assert "## Restart Hint" in body
    assert "- B-085" in body
    assert "- B-084" in body
    assert "land statusline" in body
    assert "log slice to Compass" in body


def test_main_writes_confirmation_when_not_quiet(tmp_path, capsys, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_runtime_snapshot(
        repo_root,
        {
            "generated_utc": "2026-04-11T12:00:00Z",
            "execution_focus": {"global": {"headline": "h", "workstreams": ["B-001"]}},
        },
    )
    config_dir = tmp_path / "claude-config"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config_dir))
    exit_code = precompact.main(["--repo-root", str(repo_root)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Odylith PreCompact snapshot written:" in captured.out


def test_main_quiet_suppresses_confirmation(tmp_path, capsys, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_runtime_snapshot(
        repo_root,
        {
            "generated_utc": "2026-04-11T12:00:00Z",
            "execution_focus": {"global": {"headline": "h", "workstreams": ["B-001"]}},
        },
    )
    config_dir = tmp_path / "claude-config"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config_dir))
    exit_code = precompact.main(["--repo-root", str(repo_root), "--quiet"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == ""


def test_project_slug_is_stable(tmp_path):
    slug_one = claude_host_shared.project_slug(tmp_path)
    slug_two = claude_host_shared.project_slug(tmp_path)
    assert slug_one == slug_two
    assert slug_one.startswith("-")


def test_project_memory_dir_uses_override_env(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude-config"))
    memory_dir = claude_host_shared.project_memory_dir(tmp_path)
    assert str(memory_dir).startswith(str(tmp_path / "claude-config"))
    assert memory_dir.name == "memory"
    assert memory_dir.parent.parent.name == "projects"
