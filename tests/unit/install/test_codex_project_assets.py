from __future__ import annotations

import json
import tomllib
from pathlib import Path

from odylith.install import bootstrap_assets
from odylith.runtime.common import codex_cli_capabilities


REPO_ROOT = Path(__file__).resolve().parents[3]
LIVE_CLAUDE_ROOT = REPO_ROOT / ".claude"
LIVE_CODEX_ROOT = REPO_ROOT / ".codex"
LIVE_AGENTS_ROOT = REPO_ROOT / ".agents"
LIVE_SKILLS_ROOT = REPO_ROOT / ".agents" / "skills"
PROJECT_ROOT_BUNDLE = REPO_ROOT / "src" / "odylith" / "bundle" / "assets" / "project-root"
INSTALL_AND_CONTRACT_MODULES = (
    REPO_ROOT / "src" / "odylith" / "install" / "__init__.py",
    REPO_ROOT / "src" / "odylith" / "install" / "agents.py",
    REPO_ROOT / "src" / "odylith" / "install" / "archive_safety.py",
    REPO_ROOT / "src" / "odylith" / "install" / "destructive_write_scenarios.py",
    REPO_ROOT / "src" / "odylith" / "install" / "manager.py",
    REPO_ROOT / "src" / "odylith" / "install" / "migration_audit.py",
    REPO_ROOT / "src" / "odylith" / "install" / "paths.py",
    REPO_ROOT / "src" / "odylith" / "install" / "python_env.py",
    REPO_ROOT / "src" / "odylith" / "install" / "release_assets.py",
    REPO_ROOT / "src" / "odylith" / "install" / "repair.py",
    REPO_ROOT / "src" / "odylith" / "install" / "runtime.py",
    REPO_ROOT / "src" / "odylith" / "install" / "runtime_integrity.py",
    REPO_ROOT / "src" / "odylith" / "install" / "runtime_status.py",
    REPO_ROOT / "src" / "odylith" / "install" / "runtime_tree_policy.py",
    REPO_ROOT / "src" / "odylith" / "install" / "state.py",
    REPO_ROOT / "src" / "odylith" / "contracts" / "__init__.py",
    REPO_ROOT / "src" / "odylith" / "contracts" / "host_adapter.py",
    REPO_ROOT / "src" / "odylith" / "contracts" / "plan_v1.py",
    REPO_ROOT / "src" / "odylith" / "contracts" / "route_v1.py",
    REPO_ROOT / "src" / "odylith" / "cli.py",
    REPO_ROOT / "src" / "odylith" / "bundle" / "__init__.py",
)
CODEX_COMMAND_SKILLS = {
    "odylith-start/SKILL.md",
    "odylith-context/SKILL.md",
    "odylith-show-me/SKILL.md",
    "odylith-query/SKILL.md",
    "odylith-session-brief/SKILL.md",
    "odylith-sync/SKILL.md",
    "odylith-version/SKILL.md",
    "odylith-doctor/SKILL.md",
    "odylith-compass-log/SKILL.md",
    "odylith-compass-refresh/SKILL.md",
    "odylith-casebook-bug-capture/SKILL.md",
    "odylith-casebook-bug-preflight/SKILL.md",
    "odylith-code-hygiene-guard/SKILL.md",
    "odylith-guidance-behavior/SKILL.md",
    "odylith-discipline/SKILL.md",
}


def _managed_files(base: Path) -> set[str]:
    return {
        path.relative_to(base).as_posix()
        for path in base.rglob("*")
        if path.is_file()
        and path.name != ".DS_Store"
        and "__pycache__" not in path.parts
        and "worktrees" not in path.parts
        and not path.name.endswith(".pyc")
    }


def test_live_claude_project_assets_match_bundle_mirror_inventory() -> None:
    live = _managed_files(LIVE_CLAUDE_ROOT)
    bundled = _managed_files(PROJECT_ROOT_BUNDLE / ".claude")

    assert live == bundled


def test_live_claude_skill_shims_cover_repo_owned_odylith_skills() -> None:
    source_skill_names = {path.parent.name for path in (REPO_ROOT / "odylith" / "skills").glob("*/SKILL.md")}
    live_skill_names = {path.parent.name for path in (LIVE_CLAUDE_ROOT / "skills").glob("*/SKILL.md")}
    bundled_skill_names = {
        path.parent.name for path in (PROJECT_ROOT_BUNDLE / ".claude" / "skills").glob("*/SKILL.md")
    }

    assert live_skill_names == source_skill_names
    assert bundled_skill_names == source_skill_names


def test_live_claude_skill_shims_and_review_assets_match_bundle_content() -> None:
    mirrored_paths = (
        *sorted(path.relative_to(LIVE_CLAUDE_ROOT) for path in (LIVE_CLAUDE_ROOT / "skills").rglob("SKILL.md")),
        Path("CLAUDE.md"),
        Path("agents") / "odylith-reviewer.md",
    )
    for relative_path in mirrored_paths:
        live_path = LIVE_CLAUDE_ROOT / relative_path
        bundle_path = PROJECT_ROOT_BUNDLE / ".claude" / relative_path
        assert live_path.read_text(encoding="utf-8") == bundle_path.read_text(encoding="utf-8")


def test_live_claude_hook_scripts_match_bundle_mirror_content() -> None:
    live_hooks = LIVE_CLAUDE_ROOT / "hooks"
    bundle_hooks = PROJECT_ROOT_BUNDLE / ".claude" / "hooks"

    live_hook_names = {path.name for path in live_hooks.glob("*.py")}
    bundled_hook_names = {path.name for path in bundle_hooks.glob("*.py")}
    assert live_hook_names == bundled_hook_names

    for hook_name in sorted(live_hook_names):
        assert (live_hooks / hook_name).read_text(encoding="utf-8") == (
            bundle_hooks / hook_name
        ).read_text(encoding="utf-8")


def test_live_agents_bin_matches_bundle_mirror_content() -> None:
    live_helper = LIVE_AGENTS_ROOT / "bin" / "odylith-host-launcher.py"
    bundle_helper = PROJECT_ROOT_BUNDLE / ".agents" / "bin" / "odylith-host-launcher.py"

    assert live_helper.is_file()
    assert bundle_helper.is_file()
    assert live_helper.read_text(encoding="utf-8") == bundle_helper.read_text(encoding="utf-8")


def test_install_and_contract_entry_modules_start_with_docstrings() -> None:
    for path in INSTALL_AND_CONTRACT_MODULES:
        text = path.read_text(encoding="utf-8").lstrip()
        assert text.startswith('"""'), f"module docstring missing: {path.relative_to(REPO_ROOT)}"


def test_codex_project_config_uses_verified_contract_keys() -> None:
    payload = tomllib.loads((LIVE_CODEX_ROOT / "config.toml").read_text(encoding="utf-8"))

    assert payload["project_root_markers"] == [".git", "AGENTS.md", "CLAUDE.md", ".claude/CLAUDE.md"]
    assert payload["project_doc_max_bytes"] >= (REPO_ROOT / "AGENTS.md").stat().st_size
    assert payload["project_doc_fallback_filenames"] == ["CLAUDE.md"]
    assert payload["features"]["codex_hooks"] is True
    assert payload["agents"] == {"max_threads": 6, "max_depth": 1}


def test_codex_project_agents_have_expected_schema_and_runtime_fields() -> None:
    expected = {
        "odylith-atlas-diagrammer.toml": ("gpt-5.3-codex", "medium", "workspace-write"),
        "odylith-compass-briefer.toml": ("gpt-5.4-mini", "high", "read-only"),
        "odylith-compass-narrator.toml": ("gpt-5.3-codex-spark", "medium", "read-only"),
        "odylith-context-engine.toml": ("gpt-5.4-mini", "medium", "read-only"),
        "odylith-governance-scribe.toml": ("gpt-5.3-codex", "medium", "workspace-write"),
        "odylith-registry-scribe.toml": ("gpt-5.3-codex", "medium", "workspace-write"),
        "odylith-reviewer.toml": ("gpt-5.4", "high", "read-only"),
        "odylith-validator.toml": ("gpt-5.4-mini", "high", "read-only"),
        "odylith-workstream.toml": ("gpt-5.3-codex", "medium", "workspace-write"),
    }

    agent_dir = LIVE_CODEX_ROOT / "agents"
    assert {path.name for path in agent_dir.glob("*.toml")} == set(expected)

    for filename, (model, reasoning, sandbox_mode) in expected.items():
        payload = tomllib.loads((agent_dir / filename).read_text(encoding="utf-8"))
        assert payload["name"]
        assert payload["description"]
        assert payload["developer_instructions"]
        assert payload["model"] == model
        assert payload["model_reasoning_effort"] == reasoning
        assert payload["sandbox_mode"] == sandbox_mode


def test_codex_hooks_register_supported_events_only() -> None:
    payload = json.loads((LIVE_CODEX_ROOT / "hooks.json").read_text(encoding="utf-8"))

    assert set(payload) == {"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"}
    assert payload["SessionStart"][0]["matcher"] == "startup|resume"
    assert payload["PreToolUse"][0]["matcher"] == "Bash"
    assert payload["PostToolUse"][0]["matcher"] == "Bash"
    assert payload["SessionStart"][0]["hooks"][0]["command"] == (
        "python3 ./.agents/bin/odylith-host-launcher.py codex session-start-ground --repo-root ."
    )
    assert payload["UserPromptSubmit"][0]["hooks"][0]["command"] == (
        "python3 ./.agents/bin/odylith-host-launcher.py codex prompt-context --repo-root ."
    )
    assert payload["PreToolUse"][0]["hooks"][0]["command"] == (
        "python3 ./.agents/bin/odylith-host-launcher.py codex bash-guard --repo-root ."
    )
    assert payload["PostToolUse"][0]["hooks"][0]["command"] == (
        "python3 ./.agents/bin/odylith-host-launcher.py codex post-bash-checkpoint --repo-root ."
    )
    assert payload["Stop"][0]["hooks"][0]["command"] == (
        "python3 ./.agents/bin/odylith-host-launcher.py codex stop-summary --repo-root ."
    )

    live_scripts = {path.name for path in (LIVE_CODEX_ROOT / "hooks").glob("*.py")}
    bundled_scripts = {path.name for path in (PROJECT_ROOT_BUNDLE / ".codex" / "hooks").glob("*.py")}

    assert live_scripts == set()
    assert bundled_scripts == set()


def test_codex_skill_shims_stay_on_the_curated_command_surface() -> None:
    codex_skill_files = {
        path.relative_to(LIVE_SKILLS_ROOT).as_posix()
        for path in LIVE_SKILLS_ROOT.rglob("SKILL.md")
    }
    bundled_codex_skill_files = {
        path.relative_to(PROJECT_ROOT_BUNDLE / ".agents" / "skills").as_posix()
        for path in (PROJECT_ROOT_BUNDLE / ".agents" / "skills").rglob("SKILL.md")
    }

    assert codex_skill_files == CODEX_COMMAND_SKILLS
    assert bundled_codex_skill_files == CODEX_COMMAND_SKILLS


def test_codex_command_skill_sources_exist_for_curated_cli_surface() -> None:
    for relative_path in CODEX_COMMAND_SKILLS:
        skill_name = Path(relative_path).parts[0]
        assert (REPO_ROOT / "odylith" / "skills" / skill_name / "SKILL.md").is_file()


def test_write_effective_codex_project_config_preserves_existing_user_config(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Repo\n", encoding="utf-8")
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    original = '[model]\nprovider = "bedrock"\nname = "claude-sonnet"\n'
    config_path.write_text(original, encoding="utf-8")

    codex_cli_capabilities.write_effective_codex_project_config(repo_root=tmp_path)

    assert config_path.read_text(encoding="utf-8") == original
    assert not config_path.with_name("config.toml.odylith-preimage.bak").exists()


def test_write_effective_codex_hooks_merges_without_destroying_user_hooks(tmp_path: Path) -> None:
    hooks_path = tmp_path / ".codex" / "hooks.json"
    hooks_path.parent.mkdir(parents=True, exist_ok=True)
    original_payload = {
        "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python3 user_prompt.py"}]}],
        "Stop": [{"hooks": [{"type": "command", "command": "python3 user_stop.py"}]}],
    }
    hooks_path.write_text(json.dumps(original_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    codex_cli_capabilities.write_effective_codex_hooks(repo_root=tmp_path)

    payload = json.loads(hooks_path.read_text(encoding="utf-8"))
    prompt_commands = [
        hook["command"]
        for group in payload["UserPromptSubmit"]
        for hook in group.get("hooks", [])
    ]
    stop_commands = [
        hook["command"]
        for group in payload["Stop"]
        for hook in group.get("hooks", [])
    ]
    assert "python3 user_prompt.py" in prompt_commands
    assert any("codex prompt-context" in command for command in prompt_commands)
    assert "python3 user_stop.py" in stop_commands
    assert any("codex stop-summary" in command for command in stop_commands)
    assert json.loads(hooks_path.with_name("hooks.json.odylith-preimage.bak").read_text(encoding="utf-8")) == original_payload


def test_write_effective_codex_hooks_refuses_invalid_json(tmp_path: Path) -> None:
    hooks_path = tmp_path / ".codex" / "hooks.json"
    hooks_path.parent.mkdir(parents=True, exist_ok=True)
    hooks_path.write_text("{not json\n", encoding="utf-8")

    codex_cli_capabilities.write_effective_codex_hooks(repo_root=tmp_path)

    assert hooks_path.read_text(encoding="utf-8") == "{not json\n"
    assert not hooks_path.with_name("hooks.json.odylith-preimage.bak").exists()


def test_write_effective_codex_hooks_refuses_symlink(tmp_path: Path) -> None:
    external_hooks = tmp_path / "external-hooks.json"
    external_hooks.write_text('{"UserPromptSubmit":[]}\n', encoding="utf-8")
    hooks_path = tmp_path / ".codex" / "hooks.json"
    hooks_path.parent.mkdir(parents=True, exist_ok=True)
    hooks_path.symlink_to(external_hooks)

    codex_cli_capabilities.write_effective_codex_hooks(repo_root=tmp_path)

    assert external_hooks.read_text(encoding="utf-8") == '{"UserPromptSubmit":[]}\n'
    assert not hooks_path.with_name("hooks.json.odylith-preimage.bak").exists()


def test_write_effective_codex_assets_refuse_symlinked_codex_directory(tmp_path: Path) -> None:
    external_codex_root = tmp_path / "external-codex"
    external_codex_root.mkdir()
    external_config = external_codex_root / "config.toml"
    external_hooks = external_codex_root / "hooks.json"
    external_config.write_text('[model]\nprovider = "bedrock"\n', encoding="utf-8")
    external_hooks.write_text('{"UserPromptSubmit":[]}\n', encoding="utf-8")
    (tmp_path / ".codex").symlink_to(external_codex_root, target_is_directory=True)

    codex_cli_capabilities.write_effective_codex_project_config(repo_root=tmp_path)
    codex_cli_capabilities.write_effective_codex_hooks(repo_root=tmp_path)

    assert external_config.read_text(encoding="utf-8") == '[model]\nprovider = "bedrock"\n'
    assert external_hooks.read_text(encoding="utf-8") == '{"UserPromptSubmit":[]}\n'
    assert not (external_codex_root / "config.toml.odylith-preimage.bak").exists()
    assert not (external_codex_root / "hooks.json.odylith-preimage.bak").exists()


def test_project_root_skill_prune_preserves_user_custom_skills(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    target_root = tmp_path / "repo"
    (source_root / ".agents" / "skills" / "odylith-start").mkdir(parents=True)
    (source_root / ".agents" / "skills" / "odylith-start" / "SKILL.md").write_text(
        "# odylith-start\n",
        encoding="utf-8",
    )
    custom_skill = target_root / ".agents" / "skills" / "team-custom" / "SKILL.md"
    custom_skill.parent.mkdir(parents=True, exist_ok=True)
    custom_skill.write_text("# team custom\n", encoding="utf-8")
    retired_skill = target_root / ".agents" / "skills" / "odylith-subagent-router" / "SKILL.md"
    retired_skill.parent.mkdir(parents=True, exist_ok=True)
    retired_skill.write_text("# retired\n", encoding="utf-8")

    bootstrap_assets.prune_removed_project_root_skill_shims(source_root=source_root, target_root=target_root)

    assert custom_skill.read_text(encoding="utf-8") == "# team custom\n"
    assert not retired_skill.exists()


def test_sync_managed_project_root_assets_refuses_symlinked_managed_file(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_hook = source_root / ".claude" / "hooks" / "odylith_support.py"
    source_hook.parent.mkdir(parents=True)
    source_hook.write_text("# managed hook\n", encoding="utf-8")
    repo_root = tmp_path / "repo"
    external_hook = tmp_path / "external-hook.py"
    external_hook.write_text("# user hook\n", encoding="utf-8")
    target_hook = repo_root / ".claude" / "hooks" / "odylith_support.py"
    target_hook.parent.mkdir(parents=True)
    target_hook.symlink_to(external_hook)

    bootstrap_assets.sync_managed_project_root_assets(
        repo_root=repo_root,
        source_root=source_root,
        activate_host_settings=False,
    )

    assert target_hook.is_symlink()
    assert external_hook.read_text(encoding="utf-8") == "# user hook\n"


def test_sync_managed_project_root_assets_refuses_symlinked_managed_directory(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    (source_root / ".claude").mkdir(parents=True)
    (source_root / ".claude" / "CLAUDE.md").write_text("# managed claude\n", encoding="utf-8")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    external_claude_root = tmp_path / "external-claude"
    external_claude_root.mkdir()
    (repo_root / ".claude").symlink_to(external_claude_root, target_is_directory=True)

    bootstrap_assets.sync_managed_project_root_assets(
        repo_root=repo_root,
        source_root=source_root,
        activate_host_settings=False,
    )

    assert (repo_root / ".claude").is_symlink()
    assert not (external_claude_root / "CLAUDE.md").exists()


def test_sync_managed_project_root_assets_refuses_symlinked_skill_prune_root(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_skill = source_root / ".agents" / "skills" / "odylith-start" / "SKILL.md"
    source_skill.parent.mkdir(parents=True)
    source_skill.write_text("# odylith-start\n", encoding="utf-8")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    external_skills_root = tmp_path / "external-skills"
    retired_skill = external_skills_root / "odylith-subagent-router" / "SKILL.md"
    retired_skill.parent.mkdir(parents=True)
    retired_skill.write_text("# external retired shim\n", encoding="utf-8")
    (repo_root / ".agents").mkdir()
    (repo_root / ".agents" / "skills").symlink_to(external_skills_root, target_is_directory=True)

    bootstrap_assets.sync_managed_project_root_assets(
        repo_root=repo_root,
        source_root=source_root,
        activate_host_settings=False,
    )

    assert retired_skill.read_text(encoding="utf-8") == "# external retired shim\n"


def test_sync_managed_release_notes_refuses_symlinked_target_root(tmp_path: Path) -> None:
    product_root = tmp_path / "product" / "odylith"
    source_notes = product_root / "runtime" / "source" / "release-notes"
    source_notes.mkdir(parents=True)
    (source_notes / "v1.2.3.md").write_text("# v1.2.3\n", encoding="utf-8")
    repo_root = tmp_path / "repo"
    repo_notes_parent = repo_root / "odylith" / "runtime" / "source"
    repo_notes_parent.mkdir(parents=True)
    external_notes = tmp_path / "external-release-notes"
    external_notes.mkdir()
    keep_file = external_notes / "keep.md"
    keep_file.write_text("# keep\n", encoding="utf-8")
    (repo_notes_parent / "release-notes").symlink_to(external_notes, target_is_directory=True)

    bootstrap_assets.sync_managed_release_notes(
        repo_root=repo_root,
        version="1.2.3",
        product_root=product_root,
    )

    assert keep_file.read_text(encoding="utf-8") == "# keep\n"
    assert not (external_notes / "v1.2.3.md").exists()


def test_sync_managed_agents_guidelines_refuses_symlinked_odylith_root(tmp_path: Path) -> None:
    product_root = tmp_path / "product" / "odylith"
    source_guidelines = product_root / "agents-guidelines"
    source_guidelines.mkdir(parents=True)
    (source_guidelines / "SECURITY.md").write_text("# managed security\n", encoding="utf-8")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    external_odylith_root = tmp_path / "external-odylith"
    external_odylith_root.mkdir()
    (repo_root / "odylith").symlink_to(external_odylith_root, target_is_directory=True)

    bootstrap_assets.sync_managed_agents_guidelines(repo_root=repo_root, product_root=product_root)

    assert not (external_odylith_root / "agents-guidelines" / "SECURITY.md").exists()
