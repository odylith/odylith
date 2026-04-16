from __future__ import annotations

from odylith.runtime.common import codex_cli_capabilities
from odylith.runtime.common import claude_cli_capabilities
from odylith.runtime.common import host_runtime


def test_resolve_host_capabilities_for_codex() -> None:
    capabilities = host_runtime.resolve_host_capabilities("codex_cli")

    assert capabilities["host_runtime"] == "codex_cli"
    assert capabilities["host_family"] == "codex"
    assert capabilities["model_family"] == ""
    assert capabilities["delegation_style"] == "routed_spawn"
    assert capabilities["supports_native_spawn"] is True
    assert capabilities["supports_interrupt"] is True
    assert capabilities["supports_artifact_paths"] is True
    assert capabilities["supports_local_structured_reasoning"] is True
    assert capabilities["supports_explicit_model_selection"] is True
    assert capabilities["project_assets_mode"] == "best_effort_enhancements"
    assert capabilities["baseline_contract"] == "AGENTS.md + ./.odylith/bin/odylith"
    assert capabilities["trusted_project_required"] is True
    assert capabilities["supports_assistant_visible_intervention_fallback"] is True
    assert capabilities["supports_chat_visible_hook_delivery"] is False


def test_resolve_host_capabilities_for_claude() -> None:
    capabilities = host_runtime.resolve_host_capabilities("claude_cli")

    assert capabilities["host_family"] == "claude"
    assert capabilities["model_family"] == ""
    assert capabilities["delegation_style"] == "task_tool_subagents"
    assert capabilities["supports_native_spawn"] is True
    assert capabilities["supports_local_structured_reasoning"] is True
    # B-084/CB-103: Claude Code is a first-class delegation host; the
    # execution profile ladder must resolve to a real model, so the host
    # capability contract must declare explicit model selection available.
    assert capabilities["supports_explicit_model_selection"] is True


def test_resolve_host_capabilities_for_unknown_host() -> None:
    capabilities = host_runtime.resolve_host_capabilities("unsupported")

    assert capabilities["host_family"] == "unknown"
    assert capabilities["model_family"] == ""
    assert capabilities["delegation_style"] == "none"
    assert capabilities["supports_native_spawn"] is False
    assert capabilities["supports_local_structured_reasoning"] is False


def test_resolve_host_capabilities_for_codex_can_use_local_probe(monkeypatch) -> None:
    monkeypatch.setattr(
        host_runtime.codex_cli_capabilities,
        "inspect_codex_cli_capabilities",
        lambda **_: codex_cli_capabilities.CodexCliCapabilitySnapshot(
            repo_root="/tmp/repo",
            codex_bin="codex",
            codex_available=True,
            codex_version_raw="codex-cli 0.119.0-alpha.28",
            codex_version="0.119.0-alpha.28",
            baseline_contract="AGENTS.md + ./.odylith/bin/odylith",
            baseline_ready=True,
            launcher_present=True,
            repo_agents_present=True,
            codex_project_assets_present=True,
            codex_skill_shims_present=True,
            project_assets_mode="best_effort_enhancements",
            trusted_project_required=True,
            hooks_feature_known=True,
            hooks_feature_enabled=True,
            supports_user_prompt_submit_hook=True,
            supports_post_bash_checkpoint_hook=True,
            supports_stop_summary_hook=True,
            prompt_input_probe_supported=False,
            prompt_input_probe_passed=False,
            repo_guidance_detected=False,
            future_version_policy="capability_based_no_max_pin",
            overall_posture="baseline_safe_with_best_effort_project_assets",
        ),
    )

    capabilities = host_runtime.resolve_host_capabilities("codex_cli", repo_root="/tmp/repo")

    assert capabilities["codex_cli_available"] is True
    assert capabilities["codex_cli_version"] == "0.119.0-alpha.28"
    assert capabilities["supports_project_hooks"] is True
    assert capabilities["supports_prompt_context_hook"] is True
    assert capabilities["supports_post_bash_checkpoint_hook"] is True
    assert capabilities["supports_stop_summary_hook"] is True
    assert capabilities["supports_assistant_visible_intervention_fallback"] is True
    assert capabilities["supports_chat_visible_hook_delivery"] is False
    assert capabilities["compatibility_posture"] == "baseline_safe_with_best_effort_project_assets"


def test_resolve_host_capabilities_for_claude_requires_visible_intervention_hooks(monkeypatch) -> None:
    monkeypatch.setattr(
        host_runtime.claude_cli_capabilities,
        "inspect_claude_cli_capabilities",
        lambda **_: claude_cli_capabilities.ClaudeCliCapabilitySnapshot(
            repo_root="/tmp/repo",
            claude_bin="claude",
            claude_available=True,
            claude_version_raw="claude 1.0.30",
            claude_version="1.0.30",
            baseline_contract="CLAUDE.md + ./.odylith/bin/odylith",
            baseline_ready=True,
            launcher_present=True,
            repo_claude_md_present=True,
            repo_agents_md_present=True,
            project_settings_present=True,
            project_commands_present=True,
            project_agents_present=True,
            project_skills_present=True,
            project_assets_mode="first_class_project_surface",
            trusted_project_required=False,
            supports_project_hooks=True,
            supports_subagent_hooks=True,
            supports_pre_compact_hook=True,
            supports_statusline_command=True,
            supports_prompt_context_hook=True,
            supports_prompt_teaser_hook=True,
            supports_post_edit_checkpoint_hook=True,
            supports_post_bash_checkpoint_hook=True,
            supports_stop_summary_hook=True,
            supports_post_tool_matchers=True,
            supports_slash_commands=True,
            future_version_policy="capability_based_no_max_pin",
            overall_posture="baseline_safe_assistant_visible_ready",
        ),
    )

    capabilities = host_runtime.resolve_host_capabilities("claude_cli", repo_root="/tmp/repo")

    assert capabilities["supports_project_hooks"] is True
    assert capabilities["supports_prompt_context_hook"] is True
    assert capabilities["supports_prompt_teaser_hook"] is True
    assert capabilities["supports_post_edit_checkpoint_hook"] is True
    assert capabilities["supports_post_bash_checkpoint_hook"] is True
    assert capabilities["supports_stop_summary_hook"] is True
