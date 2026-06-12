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
    "odylith-atlas-auto-update/SKILL.md",
    "odylith-atlas-render/SKILL.md",
    "odylith-backlog-create/SKILL.md",
    "odylith-backlog-validate/SKILL.md",
    "odylith-casebook-bug-capture/SKILL.md",
    "odylith-casebook-bug-investigation/SKILL.md",
    "odylith-casebook-bug-preflight/SKILL.md",
    "odylith-code-hygiene-guard/SKILL.md",
    "odylith-compass-executive/SKILL.md",
    "odylith-compass-log/SKILL.md",
    "odylith-compass-refresh/SKILL.md",
    "odylith-compass-timeline-stream/SKILL.md",
    "odylith-component-registry/SKILL.md",
    "odylith-context-engine-operations/SKILL.md",
    "odylith-start/SKILL.md",
    "odylith-context/SKILL.md",
    "odylith-delivery-governance-surface-ops/SKILL.md",
    "odylith-diagram-catalog/SKILL.md",
    "odylith-discipline/SKILL.md",
    "odylith-show-me/SKILL.md",
    "odylith-query/SKILL.md",
    "odylith-registry-spec-sync/SKILL.md",
    "odylith-registry-sync-specs/SKILL.md",
    "odylith-registry-validate/SKILL.md",
    "odylith-release-planning/SKILL.md",
    "odylith-schema-registry-governance/SKILL.md",
    "odylith-security-hardening/SKILL.md",
    "odylith-session-brief/SKILL.md",
    "odylith-session-context/SKILL.md",
    "odylith-subagent-orchestrator/SKILL.md",
    "odylith-subagent-router/SKILL.md",
    "odylith-sync/SKILL.md",
    "odylith-version/SKILL.md",
    "odylith-doctor/SKILL.md",
    "odylith-greenfield-governance/SKILL.md",
    "odylith-guidance-behavior/SKILL.md",
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


def test_claude_project_bridge_and_hooks_stay_low_surface() -> None:
    bridge_paths = (
        LIVE_CLAUDE_ROOT / "CLAUDE.md",
        PROJECT_ROOT_BUNDLE / ".claude" / "CLAUDE.md",
    )
    for path in bridge_paths:
        text = path.read_text(encoding="utf-8")
        assert "@../AGENTS.md" in text
        assert "Treat AI slop as a regression." not in text
        assert "freedom-research" not in text
        assert "Commit messages must use only" not in text
        assert len(text.encode("utf-8")) < 1600

    settings_paths = (
        LIVE_CLAUDE_ROOT / "settings.json",
        PROJECT_ROOT_BUNDLE / ".claude" / "settings.json",
    )
    for path in settings_paths:
        text = path.read_text(encoding="utf-8")
        payload = json.loads(text)
        assert "compatibility marker" not in text
        assert "prompt-context compatibility" not in text
        assert "prompt-teaser compatibility" not in text
        session_command = payload["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        assert session_command.endswith('claude session-start --repo-root "$CLAUDE_PROJECT_DIR" --quiet')


def test_claude_explicit_only_skills_do_not_hide_automatic_context_skills() -> None:
    explicit_only = {
        "odylith-atlas-auto-update",
        "odylith-atlas-render",
        "odylith-backlog-create",
        "odylith-backlog-validate",
        "odylith-casebook-bug-investigation",
        "odylith-compass-log",
        "odylith-compass-refresh",
        "odylith-compass-executive",
        "odylith-compass-timeline-stream",
        "odylith-component-registry",
        "odylith-context-engine-operations",
        "odylith-delivery-governance-surface-ops",
        "odylith-diagram-catalog",
        "odylith-discipline",
        "odylith-doctor",
        "odylith-guidance-behavior",
        "odylith-query",
        "odylith-registry-spec-sync",
        "odylith-registry-sync-specs",
        "odylith-registry-validate",
        "odylith-release-planning",
        "odylith-schema-registry-governance",
        "odylith-security-hardening",
        "odylith-session-brief",
        "odylith-session-context",
        "odylith-subagent-orchestrator",
        "odylith-subagent-router",
        "odylith-version",
    }
    automatic = {
        "odylith-casebook-bug-capture",
        "odylith-casebook-bug-preflight",
        "odylith-code-hygiene-guard",
        "odylith-context",
        "odylith-greenfield-governance",
        "odylith-show-me",
        "odylith-start",
        "odylith-sync",
    }

    for root in (LIVE_CLAUDE_ROOT / "skills", PROJECT_ROOT_BUNDLE / ".claude" / "skills"):
        model_invocable: set[str] = set()
        for skill_path in root.glob("*/SKILL.md"):
            text = skill_path.read_text(encoding="utf-8")
            if "disable-model-invocation: true" not in text:
                model_invocable.add(skill_path.parent.name)
        for skill_name in explicit_only:
            text = (root / skill_name / "SKILL.md").read_text(encoding="utf-8")
            assert "disable-model-invocation: true" in text
        for skill_name in automatic:
            text = (root / skill_name / "SKILL.md").read_text(encoding="utf-8")
            assert "disable-model-invocation: true" not in text
        assert model_invocable == automatic
        assert len(model_invocable) <= 8


def test_claude_backlog_skill_shim_carries_exact_cli_enum_guard() -> None:
    paths = (
        LIVE_CLAUDE_ROOT / "skills" / "odylith-backlog-create" / "SKILL.md",
        PROJECT_ROOT_BUNDLE / ".claude" / "skills" / "odylith-backlog-create" / "SKILL.md",
        LIVE_CLAUDE_ROOT / "commands" / "odylith-workstream-new.md",
        PROJECT_ROOT_BUNDLE / ".claude" / "commands" / "odylith-workstream-new.md",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for token in ("`XS`", "`S`", "`M`", "`L`", "`XL`"):
            assert token in text
        for token in ("`Low`", "`Medium`", "`High`", "`VeryHigh`"):
            assert token in text
        assert "moderate" in text


def test_greenfield_guidance_uses_product_intent_then_cli_owned_create_path() -> None:
    guidance_paths = (
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "odylith" / "AGENTS.md",
        REPO_ROOT / "odylith" / "README.md",
        REPO_ROOT / "odylith" / "skills" / "odylith-greenfield-governance" / "SKILL.md",
        REPO_ROOT / "odylith" / "skills" / "odylith-show-me" / "SKILL.md",
        REPO_ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "AGENTS.md",
        REPO_ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "README.md",
        REPO_ROOT
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "skills"
        / "odylith-greenfield-governance"
        / "SKILL.md",
        REPO_ROOT
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "skills"
        / "odylith-show-me"
        / "SKILL.md",
    )
    source_paths = (
        REPO_ROOT / "src" / "odylith" / "install" / "agents.py",
        REPO_ROOT / "src" / "odylith" / "install" / "bootstrap_assets.py",
    )
    forbidden = (
        "host drafts backlog",
        "host model drafts",
        "greenfield apply --repo-root . --proposal-file <proposal.json>",
        "host-authored proposal JSON is reviewed",
        "host authors an internal proposal payload",
        "active-proposal.v1.json",
    )

    for path in (*guidance_paths, *source_paths):
        text = path.read_text(encoding="utf-8")
        compact_text = " ".join(text.split())
        assert "Product Intent Confirmation" in text, path
        assert "greenfield create" in text, path
        assert "--intent-file" in text, path
        assert ".odylith/runtime/greenfield/confirmed-intent.md" in text, path
        assert ".odylith/runtime/greenfield/confirmed-intent.json" in text, path
        assert "--confirm" in text, path
        assert (
            "Do not inspect Odylith source" in text
            or "do not inspect Odylith source" in text
            or "Do not search `src/odylith`" in text
            or "do not search Odylith source" in text
            or "rather than searching Odylith source" in text
            or "do not search `src/odylith`" in compact_text.casefold()
            or "do not search odylith source" in compact_text.casefold()
        ), path
        assert "normalizes" in compact_text, path
        assert "bounded, provider-free post-confirm repair loop" in compact_text, path
        assert "final manifest passes" in compact_text, path
        assert "same visible" in compact_text, path
        assert (
            "parser/schema retries" in compact_text
            or "intermediate create-shape failures" in compact_text
        ), path
        assert (
            "project-first" in compact_text
            or "product story" in compact_text
            or "coding-readiness gates" in compact_text
            or path.name == "SKILL.md"
        ), path
        assert "greenfield create" in compact_text, path
        assert "hand-author" in compact_text or "hand author" in compact_text or "Do not hand-author" in text, path
        assert (
            "Do not ask the operator to inspect JSON" in text
            or "does not need to inspect proposal JSON" in compact_text
            or "without a second confirmation" in text
            or "Do not ask the operator to inspect proposal JSON" in text
        ), path
        for token in forbidden:
            assert token not in text, f"{path} still carries stale greenfield guidance: {token}"


def test_greenfield_guidance_keeps_post_confirmation_contract_internal() -> None:
    guidance_paths = (
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "odylith" / "AGENTS.md",
        REPO_ROOT / "odylith" / "skills" / "odylith-greenfield-governance" / "SKILL.md",
        REPO_ROOT / "odylith" / "skills" / "odylith-show-me" / "SKILL.md",
        REPO_ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "AGENTS.md",
        REPO_ROOT
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "skills"
        / "odylith-greenfield-governance"
        / "SKILL.md",
        REPO_ROOT
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "skills"
        / "odylith-show-me"
        / "SKILL.md",
        REPO_ROOT / "src" / "odylith" / "install" / "agents.py",
        REPO_ROOT / "src" / "odylith" / "install" / "bootstrap_assets.py",
    )

    for path in guidance_paths:
        text = path.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        assert "Product Intent Confirmation" in normalized, path
        assert "greenfield create" in normalized, path
        assert "--intent-file" in normalized, path
        assert ".odylith/runtime/greenfield/confirmed-intent.md" in normalized, path
        assert ".odylith/runtime/greenfield/confirmed-intent.json" in normalized, path
        assert "--confirm" in normalized, path
        assert "normalizes" in normalized, path
        assert "bounded, provider-free post-confirm repair loop" in normalized, path
        assert "final manifest passes" in normalized, path
        assert "hand-author" in normalized.casefold() or "hand author" in normalized.casefold(), path
        assert (
            "parser/schema retries" in normalized
            or "intermediate create-shape failures" in normalized
        ), path
        assert (
            "surface only" in normalized.casefold()
            or "show either created records" in normalized.casefold()
            or "created-record summary" in normalized.casefold()
        ), path
        assert (
            "second approval step" in normalized
            or "second confirmation" in normalized
            or "confirm a second time" in normalized
        ), path


def test_claude_output_style_keeps_observation_rare_and_assist_concrete() -> None:
    paths = (
        LIVE_CLAUDE_ROOT / "output-styles" / "odylith-grounded.md",
        PROJECT_ROOT_BUNDLE / ".claude" / "output-styles" / "odylith-grounded.md",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "Use `Odylith Assist:` as the post-action lane" in text
        assert "After a successful Odylith governance CLI mutation" in text
        assert "Do not emit `Odylith Observation:` just because the prompt names Radar" in text
        assert "No generic `this turn is already...` language" in text
        assert "surfaced this visibility issue" in text
        assert "Never use canned Assist text" in text


def test_grounding_assets_enforce_serial_start_before_context() -> None:
    paths = (
        REPO_ROOT / "odylith" / "skills" / "odylith-start" / "SKILL.md",
        REPO_ROOT / "odylith" / "skills" / "odylith-context" / "SKILL.md",
        REPO_ROOT / "odylith" / "agents-guidelines" / "GROUNDING_AND_NARROWING.md",
        LIVE_AGENTS_ROOT / "skills" / "odylith-start" / "SKILL.md",
        LIVE_AGENTS_ROOT / "skills" / "odylith-context" / "SKILL.md",
        PROJECT_ROOT_BUNDLE / ".agents" / "skills" / "odylith-start" / "SKILL.md",
        PROJECT_ROOT_BUNDLE / ".agents" / "skills" / "odylith-context" / "SKILL.md",
        PROJECT_ROOT_BUNDLE / ".claude" / "CLAUDE.md",
        PROJECT_ROOT_BUNDLE / ".claude" / "skills" / "odylith-start" / "SKILL.md",
        PROJECT_ROOT_BUNDLE / ".claude" / "skills" / "odylith-context" / "SKILL.md",
        PROJECT_ROOT_BUNDLE / ".claude" / "commands" / "odylith-start.md",
        PROJECT_ROOT_BUNDLE / ".claude" / "commands" / "odylith-context.md",
        LIVE_CLAUDE_ROOT / "CLAUDE.md",
        LIVE_CLAUDE_ROOT / "skills" / "odylith-start" / "SKILL.md",
        LIVE_CLAUDE_ROOT / "skills" / "odylith-context" / "SKILL.md",
        LIVE_CLAUDE_ROOT / "commands" / "odylith-start.md",
        LIVE_CLAUDE_ROOT / "commands" / "odylith-context.md",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "parallel" in text or "fan out" in text
        assert "start" in text
        assert "context" in text

    start_skill_path = REPO_ROOT / "odylith" / "skills" / "odylith-start" / "SKILL.md"
    context_skill_path = REPO_ROOT / "odylith" / "skills" / "odylith-context" / "SKILL.md"
    bundle_start_skill_path = (
        REPO_ROOT
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "skills"
        / "odylith-start"
        / "SKILL.md"
    )
    bundle_grounding_guideline_path = (
        REPO_ROOT
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "agents-guidelines"
        / "GROUNDING_AND_NARROWING.md"
    )
    start_skill = start_skill_path.read_text(encoding="utf-8")
    context_skill = context_skill_path.read_text(encoding="utf-8")
    assert "Do not run `odylith context`, `odylith query`, `git status`, or broad" in start_skill
    assert "Use this only after the current turn has run `odylith start`" in context_skill
    assert "description: Use first, before context/search fan out, when a task needs" in (
        LIVE_AGENTS_ROOT / "skills" / "odylith-start" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "description: Use after startup, never in parallel with startup" in (
        LIVE_AGENTS_ROOT / "skills" / "odylith-context" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert start_skill == bundle_start_skill_path.read_text(encoding="utf-8")
    assert (
        (REPO_ROOT / "odylith" / "agents-guidelines" / "GROUNDING_AND_NARROWING.md").read_text(
            encoding="utf-8"
        )
        == bundle_grounding_guideline_path.read_text(encoding="utf-8")
    )


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


def test_claude_destructive_guard_assets_route_uninstall_to_cli() -> None:
    paths = (
        LIVE_CLAUDE_ROOT / "hooks" / "guard-destructive-bash.py",
        PROJECT_ROOT_BUNDLE / ".claude" / "hooks" / "guard-destructive-bash.py",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "./.odylith/bin/odylith uninstall --repo-root ." in text
        assert "./.odylith/bin/odylith uninstall --repo-root . --dry-run" in text
        assert "raw deletion and hook bypasses are blocked" in text
        assert "removes `.odylith/` runtime state" in text
        assert "detaches Odylith hook entries" in text
        assert "`odylith/` governed source truth" in text
        assert "`.claude/`, `.codex/`, and `.agents/` stay in place" in text
        assert "shutil\\.rmtree" in text


def test_live_agents_bin_matches_bundle_mirror_content() -> None:
    live_helper = LIVE_AGENTS_ROOT / "bin" / "odylith-host-launcher.py"
    bundle_helper = PROJECT_ROOT_BUNDLE / ".agents" / "bin" / "odylith-host-launcher.py"

    assert live_helper.is_file()
    assert bundle_helper.is_file()
    assert live_helper.read_text(encoding="utf-8") == bundle_helper.read_text(encoding="utf-8")


def test_generated_python_project_assets_do_not_pollute_host_ruff_lint() -> None:
    generated_python_assets = (
        PROJECT_ROOT_BUNDLE / ".agents" / "bin" / "odylith-host-launcher.py",
        *(PROJECT_ROOT_BUNDLE / ".claude" / "hooks").glob("*.py"),
        LIVE_AGENTS_ROOT / "bin" / "odylith-host-launcher.py",
        *(LIVE_CLAUDE_ROOT / "hooks").glob("*.py"),
    )

    assert generated_python_assets
    for path in generated_python_assets:
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[:2] == ["#!/usr/bin/env python3", "# ruff: noqa"], (
            f"generated host asset can leak into consumer `ruff check .`: "
            f"{path.relative_to(REPO_ROOT)}"
        )


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
