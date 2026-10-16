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
        'python3 "$CLAUDE_PROJECT_DIR"/.agents/bin/odylith-host-launcher.py claude prompt-bundle --repo-root "$CLAUDE_PROJECT_DIR"',
    ]
    assert prompt_hooks[0]["timeout"] == 30
    assert len(prompt_hooks) == 1
    session_hook = payload["hooks"]["SessionStart"][0]["hooks"][0]
    assert session_hook["command"].endswith('claude session-start --repo-root "$CLAUDE_PROJECT_DIR" --quiet')
    post_edit_hook = payload["hooks"]["PostToolUse"][0]["hooks"][0]
    post_bash_hook = payload["hooks"]["PostToolUse"][1]["hooks"][0]
    subagent_stop_hook = payload["hooks"]["SubagentStop"][0]["hooks"][0]
    assert post_edit_hook["async"] is True
    assert post_bash_hook["async"] is True
    guard_hooks = payload["hooks"]["PreToolUse"][0]["hooks"]
    assert len(guard_hooks) == 1
    assert "if" not in guard_hooks[0]
    assert "claude bash-guard" in guard_hooks[0]["command"]
    assert post_bash_hook["command"] == (
        'python3 "$CLAUDE_PROJECT_DIR"/.agents/bin/odylith-host-launcher.py claude post-bash-checkpoint '
        '--repo-root "$CLAUDE_PROJECT_DIR"'
    )
    assert subagent_stop_hook["async"] is True
    allowlist = payload["permissions"]["allow"]
    for required in (
        "Bash(./.odylith/bin/odylith claude:*)",
        "Bash(./.odylith/bin/odylith codex:*)",
        "Bash(./.odylith/bin/odylith doctor:*)",
        "Bash(./.odylith/bin/odylith show:*)",
        "Bash(./.odylith/bin/odylith capabilities:*)",
        "Bash(./.odylith/bin/odylith --help:*)",
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


def test_write_effective_claude_project_settings_merges_without_destroying_user_settings(tmp_path: Path) -> None:
    _seed_repo(tmp_path, with_claude_root=True)
    settings_path = tmp_path / ".claude" / "settings.json"
    original_payload = {
        "env": {
            "ANTHROPIC_MODEL": "bedrock",
            "AWS_PROFILE": "production",
        },
        "hooks": {
            "UserPromptSubmit": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 custom_prompt_hook.py",
                            "timeout": 3,
                        }
                    ]
                }
            ]
        },
        "permissions": {
            "allow": ["Bash(aws:*)"],
            "deny": ["Bash(rm -rf:*)"],
        },
        "statusLine": {
            "type": "command",
            "command": "python3 custom_statusline.py",
        },
    }
    settings_path.write_text(json.dumps(original_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    install_manager._write_effective_claude_project_settings(repo_root=tmp_path)

    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload["env"] == original_payload["env"]
    assert payload["statusLine"] == original_payload["statusLine"]
    assert payload["permissions"]["deny"] == original_payload["permissions"]["deny"]
    assert "Bash(aws:*)" in payload["permissions"]["allow"]
    assert "Bash(./.odylith/bin/odylith claude:*)" in payload["permissions"]["allow"]
    prompt_commands = [
        hook["command"]
        for group in payload["hooks"]["UserPromptSubmit"]
        for hook in group.get("hooks", [])
    ]
    assert "python3 custom_prompt_hook.py" in prompt_commands
    assert any("claude prompt-bundle" in command for command in prompt_commands)
    backup_path = settings_path.with_name("settings.json.odylith-preimage.bak")
    assert json.loads(backup_path.read_text(encoding="utf-8")) == original_payload


def test_write_effective_claude_project_settings_preserves_nonstandard_user_shapes(tmp_path: Path) -> None:
    _seed_repo(tmp_path, with_claude_root=True)
    settings_path = tmp_path / ".claude" / "settings.json"
    original_payload = {
        "env": {"AWS_PROFILE": "production"},
        "hooks": ["custom-host-shape"],
        "permissions": {
            "allow": "Bash(aws:*)",
            "deny": "Bash(rm -rf:*)",
            "ask": ["Bash(git push:*)"],
        },
        "mcpServers": {"corp": {"command": "corp-mcp"}},
        "model": "bedrock-sonnet",
        "statusLine": "custom statusline shape",
    }
    settings_path.write_text(json.dumps(original_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    install_manager._write_effective_claude_project_settings(repo_root=tmp_path)

    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload["env"] == original_payload["env"]
    assert payload["hooks"] == original_payload["hooks"]
    assert payload["permissions"]["allow"] == original_payload["permissions"]["allow"]
    assert payload["permissions"]["deny"] == original_payload["permissions"]["deny"]
    assert payload["permissions"]["ask"] == original_payload["permissions"]["ask"]
    assert payload["mcpServers"] == original_payload["mcpServers"]
    assert payload["model"] == original_payload["model"]
    assert payload["statusLine"] == original_payload["statusLine"]


def test_write_effective_claude_project_settings_keeps_first_preimage_backup(tmp_path: Path) -> None:
    _seed_repo(tmp_path, with_claude_root=True)
    settings_path = tmp_path / ".claude" / "settings.json"
    original_payload = {
        "env": {"AWS_PROFILE": "production"},
        "hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python3 user.py"}]}]},
    }
    settings_path.write_text(json.dumps(original_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    install_manager._write_effective_claude_project_settings(repo_root=tmp_path)
    first_backup = settings_path.with_name("settings.json.odylith-preimage.bak").read_text(encoding="utf-8")
    mutated_payload = json.loads(settings_path.read_text(encoding="utf-8"))
    mutated_payload["env"] = {"AWS_PROFILE": "staging"}
    settings_path.write_text(json.dumps(mutated_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    install_manager._write_effective_claude_project_settings(repo_root=tmp_path)

    assert settings_path.with_name("settings.json.odylith-preimage.bak").read_text(encoding="utf-8") == first_backup
    assert json.loads(first_backup) == original_payload


def test_write_effective_claude_project_settings_refuses_invalid_json(tmp_path: Path) -> None:
    _seed_repo(tmp_path, with_claude_root=True)
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.write_text("{not json\n", encoding="utf-8")

    install_manager._write_effective_claude_project_settings(repo_root=tmp_path)

    assert settings_path.read_text(encoding="utf-8") == "{not json\n"
    assert not settings_path.with_name("settings.json.odylith-preimage.bak").exists()


def test_write_effective_claude_project_settings_refuses_symlink(tmp_path: Path) -> None:
    _seed_repo(tmp_path, with_claude_root=True)
    external_settings = tmp_path / "external-claude-settings.json"
    external_settings.write_text('{"env":{"AWS_PROFILE":"do-not-touch"}}\n', encoding="utf-8")
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.symlink_to(external_settings)

    install_manager._write_effective_claude_project_settings(repo_root=tmp_path)

    assert external_settings.read_text(encoding="utf-8") == '{"env":{"AWS_PROFILE":"do-not-touch"}}\n'
    assert not settings_path.with_name("settings.json.odylith-preimage.bak").exists()


def test_write_effective_claude_project_settings_refuses_symlinked_claude_directory(tmp_path: Path) -> None:
    _seed_repo(tmp_path, with_claude_root=False)
    external_claude_root = tmp_path / "external-claude"
    external_claude_root.mkdir()
    external_settings = external_claude_root / "settings.json"
    external_settings.write_text('{"env":{"AWS_PROFILE":"external"}}\n', encoding="utf-8")
    (tmp_path / ".claude").symlink_to(external_claude_root, target_is_directory=True)

    claude_cli_capabilities.write_effective_claude_project_settings(repo_root=tmp_path)

    assert external_settings.read_text(encoding="utf-8") == '{"env":{"AWS_PROFILE":"external"}}\n'
    assert not (external_claude_root / "settings.json.odylith-preimage.bak").exists()
