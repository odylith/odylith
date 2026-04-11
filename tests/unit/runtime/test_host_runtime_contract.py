from __future__ import annotations

from odylith.runtime.common import host_runtime


def test_resolve_host_capabilities_for_codex() -> None:
    capabilities = host_runtime.resolve_host_capabilities("codex_cli")

    assert capabilities == {
        "host_runtime": "codex_cli",
        "host_family": "codex",
        "model_family": "",
        "delegation_style": "routed_spawn",
        "supports_native_spawn": True,
        "supports_interrupt": True,
        "supports_artifact_paths": True,
        "supports_local_structured_reasoning": True,
        "supports_explicit_model_selection": True,
    }


def test_resolve_host_capabilities_for_claude() -> None:
    capabilities = host_runtime.resolve_host_capabilities("claude_cli")

    assert capabilities["host_family"] == "claude"
    assert capabilities["model_family"] == ""
    assert capabilities["delegation_style"] == "task_tool_subagents"
    assert capabilities["supports_native_spawn"] is True
    assert capabilities["supports_local_structured_reasoning"] is True
    assert capabilities["supports_explicit_model_selection"] is False


def test_resolve_host_capabilities_for_unknown_host() -> None:
    capabilities = host_runtime.resolve_host_capabilities("unsupported")

    assert capabilities["host_family"] == "unknown"
    assert capabilities["model_family"] == ""
    assert capabilities["delegation_style"] == "none"
    assert capabilities["supports_native_spawn"] is False
    assert capabilities["supports_local_structured_reasoning"] is False
