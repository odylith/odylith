from __future__ import annotations

import json
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
LIVE_CLAUDE_ROOT = REPO_ROOT / ".claude"
LIVE_CODEX_ROOT = REPO_ROOT / ".codex"
LIVE_SKILLS_ROOT = REPO_ROOT / ".agents" / "skills"
PROJECT_ROOT_BUNDLE = REPO_ROOT / "src" / "odylith" / "bundle" / "assets" / "project-root"
INSTALL_AND_CONTRACT_MODULES = (
    REPO_ROOT / "src" / "odylith" / "install" / "__init__.py",
    REPO_ROOT / "src" / "odylith" / "install" / "agents.py",
    REPO_ROOT / "src" / "odylith" / "install" / "archive_safety.py",
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
    assert payload["SessionStart"][0]["hooks"][0]["command"] == "./.odylith/bin/odylith codex session-start-ground --repo-root ."
    assert payload["UserPromptSubmit"][0]["hooks"][0]["command"] == "./.odylith/bin/odylith codex prompt-context --repo-root ."
    assert payload["PreToolUse"][0]["hooks"][0]["command"] == "./.odylith/bin/odylith codex bash-guard --repo-root ."
    assert payload["PostToolUse"][0]["hooks"][0]["command"] == "./.odylith/bin/odylith codex post-bash-checkpoint --repo-root ."
    assert payload["Stop"][0]["hooks"][0]["command"] == "./.odylith/bin/odylith codex stop-summary --repo-root ."

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
