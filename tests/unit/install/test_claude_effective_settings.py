from __future__ import annotations

import json
from pathlib import Path

from odylith.install import manager as install_manager
from odylith.runtime.common import claude_cli_capabilities


def _seed_repo(repo_root: Path, *, with_claude_root: bool = True) -> None:
    (repo_root / "CLAUDE.md").write_text("# Repo memory\n", encoding="utf-8")
    (repo_root / "AGENTS.md").write_text("# Repo guidance\n", encoding="utf-8")
    launcher_dir = repo_root / ".odylith" / "bin"
    launcher_dir.mkdir(parents=True, exist_ok=True)
    (launcher_dir / "odylith").write_text("#!/bin/sh\n", encoding="utf-8")
    if with_claude_root:
        (repo_root / ".claude").mkdir(parents=True, exist_ok=True)


def test_write_effective_claude_project_settings_writes_byte_stable_json(tmp_path: Path) -> None:
    _seed_repo(tmp_path, with_claude_root=True)
    claude_cli_capabilities.clear_claude_cli_capability_cache()

    install_manager._write_effective_claude_project_settings(repo_root=tmp_path)

    settings_path = tmp_path / ".claude" / "settings.json"
    assert settings_path.is_file()
    rendered = settings_path.read_text(encoding="utf-8")

    expected = claude_cli_capabilities.render_effective_claude_project_settings(repo_root=tmp_path)
    assert rendered == expected

    payload = json.loads(rendered)
    assert payload["$schema"] == "https://json.schemastore.org/claude-code-settings.json"
    assert payload["statusLine"]["type"] == "command"
    assert "PreCompact" in payload["hooks"]
    assert "SubagentStart" in payload["hooks"]
    assert "SubagentStop" in payload["hooks"]
    assert payload["hooks"]["PreToolUse"][0]["matcher"] == "Bash"
    assert payload["hooks"]["PostToolUse"][0]["matcher"] == "Write|Edit|MultiEdit"
    assert payload["hooks"]["PostToolUse"][1]["matcher"] == "Bash"
    prompt_hooks = payload["hooks"]["UserPromptSubmit"][0]["hooks"]
    assert [hook["command"] for hook in prompt_hooks] == [
        '"$CLAUDE_PROJECT_DIR"/.odylith/bin/odylith claude prompt-context --repo-root "$CLAUDE_PROJECT_DIR"',
        '"$CLAUDE_PROJECT_DIR"/.odylith/bin/odylith claude prompt-teaser --repo-root "$CLAUDE_PROJECT_DIR"',
    ]
    post_edit_hook = payload["hooks"]["PostToolUse"][0]["hooks"][0]
    post_bash_hook = payload["hooks"]["PostToolUse"][1]["hooks"][0]
    subagent_stop_hook = payload["hooks"]["SubagentStop"][0]["hooks"][0]
    assert "async" not in post_edit_hook
    assert "async" not in post_bash_hook
    assert post_bash_hook["command"] == (
        '"$CLAUDE_PROJECT_DIR"/.odylith/bin/odylith claude post-bash-checkpoint '
        '--repo-root "$CLAUDE_PROJECT_DIR"'
    )
    assert subagent_stop_hook["async"] is True
    allowlist = payload["permissions"]["allow"]
    for required in (
        "Bash(./.odylith/bin/odylith claude:*)",
        "Bash(./.odylith/bin/odylith codex:*)",
        "Bash(./.odylith/bin/odylith doctor:*)",
        "Bash(./.odylith/bin/odylith atlas:*)",
        "Bash(./.odylith/bin/odylith governance:*)",
    ):
        assert required in allowlist


def test_write_effective_claude_project_settings_is_idempotent(tmp_path: Path) -> None:
    _seed_repo(tmp_path, with_claude_root=True)
    claude_cli_capabilities.clear_claude_cli_capability_cache()

    install_manager._write_effective_claude_project_settings(repo_root=tmp_path)
    settings_path = tmp_path / ".claude" / "settings.json"
    first = settings_path.read_text(encoding="utf-8")

    settings_path.write_text("{}\n", encoding="utf-8")
    install_manager._write_effective_claude_project_settings(repo_root=tmp_path)
    second = settings_path.read_text(encoding="utf-8")

    assert second == first


def test_write_effective_claude_project_settings_no_op_when_claude_root_missing(tmp_path: Path) -> None:
    _seed_repo(tmp_path, with_claude_root=False)
    claude_cli_capabilities.clear_claude_cli_capability_cache()

    install_manager._write_effective_claude_project_settings(repo_root=tmp_path)

    assert not (tmp_path / ".claude" / "settings.json").exists()
