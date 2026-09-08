from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.common import codex_cli_capabilities
from odylith.runtime.surfaces import host_intervention_status


def test_rendered_hooks_use_native_document_wrapper() -> None:
    document = json.loads(codex_cli_capabilities.render_effective_codex_hooks())
    assert set(document) == {"hooks"}
    assert "UserPromptSubmit" in document["hooks"]


def test_mixed_legacy_and_native_hooks_converge_without_duplicate_commands(tmp_path: Path) -> None:
    path = tmp_path / ".codex/hooks.json"
    path.parent.mkdir()
    managed = json.loads(codex_cli_capabilities.render_effective_codex_hooks())["hooks"]
    custom = {"hooks": [{"type": "command", "command": "echo retained"}]}
    path.write_text(json.dumps({"hooks": {"UserPromptSubmit": [custom]}, **managed}))
    codex_cli_capabilities.write_effective_codex_hooks(repo_root=tmp_path)
    document = json.loads(path.read_text())
    assert set(document) == {"hooks"}
    assert document["hooks"]["UserPromptSubmit"] == [custom, *managed["UserPromptSubmit"]]


@pytest.mark.parametrize("invalid", ["user-owned", [], None])
def test_malformed_native_map_is_not_overwritten(tmp_path: Path, invalid: object) -> None:
    path = tmp_path / ".codex/hooks.json"
    path.parent.mkdir()
    original = json.dumps({"description": "Preserve this file", "hooks": invalid}).encode()
    path.write_bytes(original)
    codex_cli_capabilities.write_effective_codex_hooks(repo_root=tmp_path)
    codex_cli_capabilities.deactivate_codex_project_hooks(repo_root=tmp_path)
    assert path.read_bytes() == original
    assert not path.with_name("hooks.json.odylith-preimage.bak").exists()


@pytest.mark.parametrize("wrapped", [False, True])
def test_hook_upgrade_preserves_user_entries_metadata_and_first_backup(tmp_path: Path, wrapped: bool) -> None:
    path = tmp_path / ".codex/hooks.json"
    path.parent.mkdir()
    user_map = {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "echo user-owned"}]}]}
    original = {"description": "User-owned configuration", **({"hooks": user_map} if wrapped else user_map)}
    original_bytes = json.dumps(original).encode()
    path.write_bytes(original_bytes)

    codex_cli_capabilities.write_effective_codex_hooks(repo_root=tmp_path)

    updated = json.loads(path.read_text())
    assert set(updated) == {"description", "hooks"}
    assert updated["description"] == original["description"]
    assert updated["hooks"]["UserPromptSubmit"][0] == user_map["UserPromptSubmit"][0]
    assert len(updated["hooks"]["UserPromptSubmit"]) == 2
    assert path.with_name("hooks.json.odylith-preimage.bak").read_bytes() == original_bytes
    once = path.read_bytes()
    codex_cli_capabilities.write_effective_codex_hooks(repo_root=tmp_path)
    assert path.read_bytes() == once
    codex_cli_capabilities.deactivate_codex_project_hooks(repo_root=tmp_path)
    assert json.loads(path.read_text()) == {"description": original["description"], "hooks": user_map}


@pytest.mark.parametrize("wrapped", [False, True])
def test_static_readiness_matches_native_hook_document_shape(tmp_path: Path, wrapped: bool) -> None:
    path = tmp_path / ".codex/hooks.json"
    path.parent.mkdir()
    events = {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "odylith codex prompt-context"}]}]}
    path.write_text(json.dumps({"hooks": events} if wrapped else events))
    codex_cli_capabilities.clear_codex_cli_capability_cache()
    snapshot = codex_cli_capabilities.inspect_codex_cli_capabilities(tmp_path, codex_bin="/no/native/probe", probe_prompt_input=False)
    assert snapshot.supports_user_prompt_submit_hook is wrapped
    assert host_intervention_status._codex_static_readiness(tmp_path)["checks"]["prompt_context_hook"] is wrapped


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
        for group in payload["hooks"]["UserPromptSubmit"]
        for hook in group.get("hooks", [])
    ]
    assert "python3 custom_codex_prompt.py" in prompt_commands
    assert any("codex prompt-context" in command for command in prompt_commands)
    assert payload["hooks"]["Stop"] == "user-owned-non-list-shape"
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
