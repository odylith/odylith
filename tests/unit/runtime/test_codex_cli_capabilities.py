from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.common import codex_cli_capabilities


def _seed_repo(repo_root: Path) -> None:
    (repo_root / "AGENTS.md").write_text("# Repo guidance\n", encoding="utf-8")
    launcher_dir = repo_root / ".odylith" / "bin"
    launcher_dir.mkdir(parents=True, exist_ok=True)
    (launcher_dir / "odylith").write_text("#!/bin/sh\n", encoding="utf-8")
    (repo_root / ".codex").mkdir(parents=True, exist_ok=True)


def test_codex_cli_capability_repo_root_accepts_empty_token() -> None:
    assert codex_cli_capabilities._resolve_repo_root("").is_dir()  # noqa: SLF001


def test_write_effective_codex_hooks_merges_existing_hooks(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    codex_cli_capabilities.clear_codex_cli_capability_cache()
    hooks_path = tmp_path / ".codex" / "hooks.json"
    original_payload = {
        "UserPromptSubmit": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 custom_codex_prompt.py",
                        "timeout": 4,
                    }
                ]
            }
        ],
        "Stop": "user-owned-non-list-shape",
    }
    hooks_path.write_text(json.dumps(original_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    codex_cli_capabilities.write_effective_codex_hooks(repo_root=tmp_path)

    payload = json.loads(hooks_path.read_text(encoding="utf-8"))
    prompt_commands = [
        hook["command"]
        for group in payload["UserPromptSubmit"]
        for hook in group.get("hooks", [])
    ]
    assert "python3 custom_codex_prompt.py" in prompt_commands
    assert any("codex prompt-context" in command for command in prompt_commands)
    assert payload["Stop"] == "user-owned-non-list-shape"
    backup_path = hooks_path.with_name("hooks.json.odylith-preimage.bak")
    assert json.loads(backup_path.read_text(encoding="utf-8")) == original_payload


def test_write_effective_codex_hooks_refuses_invalid_json_and_symlinks(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    codex_cli_capabilities.clear_codex_cli_capability_cache()
    invalid_path = tmp_path / ".codex" / "hooks.json"
    invalid_path.write_text("{not json\n", encoding="utf-8")

    codex_cli_capabilities.write_effective_codex_hooks(repo_root=tmp_path)

    assert invalid_path.read_text(encoding="utf-8") == "{not json\n"
    assert not invalid_path.with_name("hooks.json.odylith-preimage.bak").exists()

    invalid_path.unlink()
    external_hooks = tmp_path / "external-codex-hooks.json"
    external_hooks.write_text('{"UserPromptSubmit":[]}\n', encoding="utf-8")
    invalid_path.symlink_to(external_hooks)

    codex_cli_capabilities.write_effective_codex_hooks(repo_root=tmp_path)

    assert external_hooks.read_text(encoding="utf-8") == '{"UserPromptSubmit":[]}\n'
    assert not invalid_path.with_name("hooks.json.odylith-preimage.bak").exists()


def test_write_effective_codex_project_config_preserves_user_config(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    codex_cli_capabilities.clear_codex_cli_capability_cache()
    config_path = tmp_path / ".codex" / "config.toml"
    original = '[model]\nprovider = "bedrock"\n'
    config_path.write_text(original, encoding="utf-8")

    codex_cli_capabilities.write_effective_codex_project_config(repo_root=tmp_path)

    assert config_path.read_text(encoding="utf-8") == original
    assert not config_path.with_name("config.toml.odylith-preimage.bak").exists()


def test_write_effective_codex_project_config_creates_missing_config(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    codex_cli_capabilities.clear_codex_cli_capability_cache()
    config_path = tmp_path / ".codex" / "config.toml"

    codex_cli_capabilities.write_effective_codex_project_config(repo_root=tmp_path)

    assert config_path.read_text(encoding="utf-8") == codex_cli_capabilities.render_effective_codex_project_config(
        repo_root=tmp_path
    )
