from __future__ import annotations

import json
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
LIVE_CLAUDE_ROOT = REPO_ROOT / ".claude"
LIVE_CODEX_ROOT = REPO_ROOT / ".codex"
LIVE_SKILLS_ROOT = REPO_ROOT / ".agents" / "skills"
PROJECT_ROOT_BUNDLE = REPO_ROOT / "src" / "odylith" / "bundle" / "assets" / "project-root"
CODEX_COMMAND_SKILLS = {
    "odylith-start/SKILL.md",
    "odylith-context/SKILL.md",
    "odylith-query/SKILL.md",
    "odylith-session-brief/SKILL.md",
    "odylith-sync/SKILL.md",
    "odylith-version/SKILL.md",
    "odylith-doctor/SKILL.md",
    "odylith-compass-log/SKILL.md",
    "odylith-compass-refresh/SKILL.md",
    "odylith-atlas-render/SKILL.md",
    "odylith-atlas-auto-update/SKILL.md",
    "odylith-backlog-create/SKILL.md",
    "odylith-backlog-validate/SKILL.md",
    "odylith-registry-validate/SKILL.md",
    "odylith-registry-sync-specs/SKILL.md",
}


def _managed_files(base: Path) -> set[str]:
    return {
        path.relative_to(base).as_posix()
        for path in base.rglob("*")
        if path.is_file()
        and path.name != ".DS_Store"
        and "__pycache__" not in path.parts
        and not path.name.endswith(".pyc")
    }


def test_live_claude_project_assets_match_bundle_mirror_inventory() -> None:
    live = _managed_files(LIVE_CLAUDE_ROOT)
    bundled = _managed_files(PROJECT_ROOT_BUNDLE / ".claude")

    assert live == bundled


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


def test_codex_skill_shims_mirror_the_claude_skill_inventory() -> None:
    claude_skill_files = {
        path.relative_to(LIVE_CLAUDE_ROOT / "skills").as_posix()
        for path in (LIVE_CLAUDE_ROOT / "skills").rglob("SKILL.md")
    }
    codex_skill_files = {
        path.relative_to(LIVE_SKILLS_ROOT).as_posix()
        for path in LIVE_SKILLS_ROOT.rglob("SKILL.md")
    }
    bundled_codex_skill_files = {
        path.relative_to(PROJECT_ROOT_BUNDLE / ".agents" / "skills").as_posix()
        for path in (PROJECT_ROOT_BUNDLE / ".agents" / "skills").rglob("SKILL.md")
    }

    assert codex_skill_files == claude_skill_files | CODEX_COMMAND_SKILLS
    assert bundled_codex_skill_files == claude_skill_files | CODEX_COMMAND_SKILLS


def test_codex_command_skill_sources_exist_for_curated_cli_surface() -> None:
    for relative_path in CODEX_COMMAND_SKILLS:
        skill_name = Path(relative_path).parts[0]
        assert (REPO_ROOT / "odylith" / "skills" / skill_name / "SKILL.md").is_file()
