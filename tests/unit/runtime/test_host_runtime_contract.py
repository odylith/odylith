from __future__ import annotations

from odylith.runtime.common import codex_cli_capabilities
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
    assert capabilities["compatibility_posture"] == "baseline_safe_with_best_effort_project_assets"
