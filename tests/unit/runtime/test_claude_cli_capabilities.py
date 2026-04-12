from __future__ import annotations

import json
import subprocess
from pathlib import Path

from odylith.runtime.common import claude_cli_capabilities


def _seed_repo(repo_root: Path, *, with_settings: bool = True) -> None:
    (repo_root / "CLAUDE.md").write_text("# Repo memory\n", encoding="utf-8")
    (repo_root / "AGENTS.md").write_text("# Repo guidance\n", encoding="utf-8")
    launcher_dir = repo_root / ".odylith" / "bin"
    launcher_dir.mkdir(parents=True, exist_ok=True)
    (launcher_dir / "odylith").write_text("#!/bin/sh\n", encoding="utf-8")

    claude_root = repo_root / ".claude"
    (claude_root / "commands").mkdir(parents=True, exist_ok=True)
    (claude_root / "commands" / "odylith-start.md").write_text("---\n", encoding="utf-8")
    (claude_root / "agents").mkdir(parents=True, exist_ok=True)
    (claude_root / "agents" / "odylith-workstream.md").write_text("---\n", encoding="utf-8")
    skill_dir = claude_root / "skills" / "casebook-bug-capture"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    if with_settings:
        (claude_root / "settings.json").write_text(
            json.dumps(
                {
                    "$schema": "https://json.schemastore.org/claude-code-settings.json",
                    "permissions": {"allow": ["Bash(./.odylith/bin/odylith start:*)"]},
                    "statusLine": {
                        "type": "command",
                        "command": '"$CLAUDE_PROJECT_DIR"/.claude/statusline.sh',
                    },
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Bash",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": '"$CLAUDE_PROJECT_DIR"/.odylith/bin/odylith claude bash-guard --repo-root "$CLAUDE_PROJECT_DIR"',
                                    }
                                ],
                            }
                        ],
                        "PostToolUse": [
                            {
                                "matcher": "Write|Edit|MultiEdit",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": '"$CLAUDE_PROJECT_DIR"/.odylith/bin/odylith claude post-edit-checkpoint --repo-root "$CLAUDE_PROJECT_DIR"',
                                    }
                                ],
                            }
                        ],
                        "PreCompact": [
                            {
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": '"$CLAUDE_PROJECT_DIR"/.odylith/bin/odylith claude pre-compact-snapshot --repo-root "$CLAUDE_PROJECT_DIR" --quiet',
                                    }
                                ]
                            }
                        ],
                        "SubagentStart": [
                            {
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": '"$CLAUDE_PROJECT_DIR"/.odylith/bin/odylith claude subagent-start --repo-root "$CLAUDE_PROJECT_DIR"',
                                    }
                                ]
                            }
                        ],
                        "SubagentStop": [
                            {
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": '"$CLAUDE_PROJECT_DIR"/.odylith/bin/odylith claude subagent-stop --repo-root "$CLAUDE_PROJECT_DIR"',
                                    }
                                ]
                            }
                        ],
                    },
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )


def test_parse_claude_version_handles_release_and_prerelease_tokens() -> None:
    assert claude_cli_capabilities.parse_claude_version("claude 1.0.30") == "1.0.30"
    assert claude_cli_capabilities.parse_claude_version("claude 1.2.0-beta.4") == "1.2.0-beta.4"
    assert claude_cli_capabilities.parse_claude_version("") == ""


def test_inspect_claude_cli_capabilities_marks_baseline_safe_live_proven(monkeypatch, tmp_path: Path) -> None:
    _seed_repo(tmp_path, with_settings=True)

    def _fake_run(*, repo_root: Path, claude_bin: str, args: list[str], timeout: int = 10):
        del repo_root, claude_bin, timeout
        if args == ["--version"]:
            return subprocess.CompletedProcess(args, 0, stdout="claude 1.0.30\n", stderr="")
        raise AssertionError(args)

    monkeypatch.setattr(claude_cli_capabilities, "_run_claude_command", _fake_run)
    claude_cli_capabilities.clear_claude_cli_capability_cache()

    snapshot = claude_cli_capabilities.inspect_claude_cli_capabilities(
        repo_root=tmp_path,
        probe_version=True,
    )

    assert snapshot.claude_available is True
    assert snapshot.claude_version == "1.0.30"
    assert snapshot.baseline_ready is True
    assert snapshot.project_settings_present is True
    assert snapshot.supports_project_hooks is True
    assert snapshot.supports_subagent_hooks is True
    assert snapshot.supports_pre_compact_hook is True
    assert snapshot.supports_statusline_command is True
    assert snapshot.supports_post_tool_matchers is True
    assert snapshot.supports_slash_commands is True
    assert snapshot.trusted_project_required is False
    assert snapshot.project_assets_mode == "first_class_project_surface"
    assert snapshot.overall_posture == "baseline_safe_live_proven"


def test_inspect_claude_cli_capabilities_stays_baseline_safe_when_claude_is_missing(monkeypatch, tmp_path: Path) -> None:
    _seed_repo(tmp_path, with_settings=False)

    monkeypatch.setattr(claude_cli_capabilities, "_run_claude_command", lambda **_: None)
    claude_cli_capabilities.clear_claude_cli_capability_cache()

    snapshot = claude_cli_capabilities.inspect_claude_cli_capabilities(
        repo_root=tmp_path,
        probe_version=True,
    )

    assert snapshot.claude_available is False
    assert snapshot.baseline_ready is True
    assert snapshot.project_settings_present is False
    assert snapshot.supports_project_hooks is False
    assert snapshot.supports_pre_compact_hook is False
    assert snapshot.overall_posture == "baseline_safe"


def test_render_effective_claude_project_settings_is_byte_stable_and_idempotent(tmp_path: Path) -> None:
    _seed_repo(tmp_path, with_settings=False)
    claude_cli_capabilities.clear_claude_cli_capability_cache()

    first = claude_cli_capabilities.render_effective_claude_project_settings(repo_root=tmp_path)
    second = claude_cli_capabilities.render_effective_claude_project_settings(repo_root=tmp_path)

    assert first == second
    payload = json.loads(first)
    assert payload["$schema"] == "https://json.schemastore.org/claude-code-settings.json"
    assert payload["statusLine"]["type"] == "command"
    assert payload["hooks"]["PreToolUse"][0]["matcher"] == "Bash"
    assert payload["hooks"]["PostToolUse"][0]["matcher"] == "Write|Edit|MultiEdit"
    assert payload["hooks"]["PreCompact"][0]["hooks"][0]["command"].endswith(
        "claude pre-compact-snapshot --repo-root \"$CLAUDE_PROJECT_DIR\" --quiet"
    )
    allow = payload["permissions"]["allow"]
    assert "Bash(./.odylith/bin/odylith claude:*)" in allow
    assert "Bash(./.odylith/bin/odylith codex:*)" in allow
    assert len(allow) == 15


def test_write_effective_claude_project_settings_writes_then_round_trips(tmp_path: Path) -> None:
    _seed_repo(tmp_path, with_settings=False)
    claude_cli_capabilities.clear_claude_cli_capability_cache()

    target = claude_cli_capabilities.write_effective_claude_project_settings(repo_root=tmp_path)
    rendered = claude_cli_capabilities.render_effective_claude_project_settings(repo_root=tmp_path)

    assert target.is_file()
    assert target.read_text(encoding="utf-8") == rendered

    target.write_text("{}\n", encoding="utf-8")
    claude_cli_capabilities.write_effective_claude_project_settings(repo_root=tmp_path)
    assert target.read_text(encoding="utf-8") == rendered
