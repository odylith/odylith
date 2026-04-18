"""Host runtime detection and host-capability guards."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from odylith.runtime.common import claude_cli_capabilities
from odylith.runtime.common import codex_cli_capabilities


_CODEX_HOST_RUNTIME = "codex_cli"
_CLAUDE_HOST_RUNTIME = "claude_cli"
_UNSUPPORTED_HOST_RUNTIME = "unsupported"
_UNKNOWN_HOST_RUNTIME = "unknown"
_CODEX_HOST_FAMILY = "codex"
_CLAUDE_HOST_FAMILY = "claude"
_UNKNOWN_HOST_FAMILY = "unknown"
_UNSPECIFIED_MODEL_FAMILY = ""
_CODEX_DELEGATION_STYLE = "routed_spawn"
_CLAUDE_DELEGATION_STYLE = "task_tool_subagents"
_UNKNOWN_DELEGATION_STYLE = "none"
_CODEX_TOKENS: frozenset[str] = frozenset(
    {
        "codex",
        "codex_cli",
        "codex_desktop",
    }
)
_CLAUDE_TOKENS: frozenset[str] = frozenset(
    {
        "anthropic",
        "claude",
        "claude_cli",
        "claude_code",
    }
)
_UNSUPPORTED_TOKENS: frozenset[str] = frozenset(
    {
        "none",
        "other",
        "unknown",
        "unsupported",
    }
)


def _normalize_token(value: Any) -> str:
    """Normalize host-runtime tokens for comparison against known aliases."""
    return " ".join(str(value or "").split()).strip().lower().replace("-", "_").replace(" ", "_")


def _is_truthy_env(value: Any) -> bool:
    """Interpret common shell truthy values the same way across host probes."""
    token = str(value or "").strip().lower()
    return token not in {"", "0", "false", "no", "off"}


def normalize_host_runtime(value: Any) -> str:
    """Map raw host hints onto the supported runtime identifiers."""
    token = _normalize_token(value)
    if token in _CODEX_TOKENS:
        return _CODEX_HOST_RUNTIME
    if token in _CLAUDE_TOKENS:
        return _CLAUDE_HOST_RUNTIME
    if token in _UNSUPPORTED_TOKENS:
        return _UNSUPPORTED_HOST_RUNTIME
    return ""


def detect_host_runtime(*, environ: Mapping[str, str] | None = None) -> str:
    """Infer the active host runtime from the environment when possible."""
    env = environ or os.environ
    bundle_id = str(env.get("__CFBundleIdentifier", "")).strip().lower()
    if (
        any(key.startswith("CLAUDE_CODE") and _is_truthy_env(env.get(key, "")) for key in env)
        or "claude" in bundle_id
        or "anthropic" in bundle_id
    ):
        return _CLAUDE_HOST_RUNTIME
    if any(str(env.get(key, "")).strip() for key in ("CODEX_THREAD_ID", "CODEX_SHELL")) or "codex" in bundle_id:
        return _CODEX_HOST_RUNTIME
    return ""


def resolve_host_runtime(*candidates: Any, environ: Mapping[str, str] | None = None) -> str:
    """Choose the first explicit host hint that normalizes cleanly, else probe."""
    for value in candidates:
        normalized = normalize_host_runtime(value)
        if normalized:
            return normalized
    return detect_host_runtime(environ=environ)


def _base_capabilities(
    *,
    host_runtime: str,
    host_family: str,
    delegation_style: str,
    supports_native_spawn: bool,
    supports_interrupt: bool,
    supports_artifact_paths: bool,
    supports_local_structured_reasoning: bool,
    supports_explicit_model_selection: bool,
) -> dict[str, Any]:
    """Build the shared capability shape returned by every host probe."""
    return {
        "host_runtime": host_runtime,
        "host_family": host_family,
        "model_family": _UNSPECIFIED_MODEL_FAMILY,
        "delegation_style": delegation_style,
        "supports_native_spawn": supports_native_spawn,
        "supports_interrupt": supports_interrupt,
        "supports_artifact_paths": supports_artifact_paths,
        "supports_local_structured_reasoning": supports_local_structured_reasoning,
        "supports_explicit_model_selection": supports_explicit_model_selection,
    }


def host_capabilities(
    host_runtime: Any,
    *,
    default_when_unknown: bool = False,
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    """Return the capability contract exposed by the requested host runtime."""
    normalized = normalize_host_runtime(host_runtime)
    if normalized == _CODEX_HOST_RUNTIME:
        payload = _base_capabilities(
            host_runtime=normalized,
            host_family=_CODEX_HOST_FAMILY,
            delegation_style=_CODEX_DELEGATION_STYLE,
            supports_native_spawn=True,
            supports_interrupt=True,
            supports_artifact_paths=True,
            supports_local_structured_reasoning=True,
            supports_explicit_model_selection=True,
        )
        snapshot = codex_cli_capabilities.inspect_codex_cli_capabilities(
            repo_root=repo_root or ".",
            probe_prompt_input=False,
        )
        payload.update(
            {
                "codex_cli_available": snapshot.codex_available,
                "codex_cli_version": snapshot.codex_version,
                "supports_project_hooks": bool(
                    snapshot.hooks_feature_enabled
                    and snapshot.supports_user_prompt_submit_hook
                    and snapshot.supports_post_bash_checkpoint_hook
                    and snapshot.supports_stop_summary_hook
                ),
                "supports_prompt_context_hook": snapshot.supports_user_prompt_submit_hook,
                "supports_post_bash_checkpoint_hook": snapshot.supports_post_bash_checkpoint_hook,
                "supports_stop_summary_hook": snapshot.supports_stop_summary_hook,
                "supports_assistant_visible_intervention_fallback": True,
                "supports_chat_visible_hook_delivery": False,
                "trusted_project_required": snapshot.trusted_project_required,
                "project_assets_mode": snapshot.project_assets_mode,
                "compatibility_posture": snapshot.overall_posture,
                "baseline_contract": snapshot.baseline_contract,
            }
        )
        return payload
    if normalized == _CLAUDE_HOST_RUNTIME:
        payload = _base_capabilities(
            host_runtime=normalized,
            host_family=_CLAUDE_HOST_FAMILY,
            delegation_style=_CLAUDE_DELEGATION_STYLE,
            supports_native_spawn=True,
            supports_interrupt=False,
            supports_artifact_paths=False,
            supports_local_structured_reasoning=True,
            supports_explicit_model_selection=True,
        )
        snapshot = claude_cli_capabilities.inspect_claude_cli_capabilities(
            repo_root=repo_root or ".",
            probe_version=False,
        )
        payload.update(
            {
                "claude_cli_available": snapshot.claude_available,
                "claude_cli_version": snapshot.claude_version,
                "supports_project_hooks": bool(
                    snapshot.supports_project_hooks
                    and snapshot.supports_prompt_context_hook
                    and snapshot.supports_prompt_teaser_hook
                    and snapshot.supports_post_edit_checkpoint_hook
                    and snapshot.supports_post_bash_checkpoint_hook
                    and snapshot.supports_stop_summary_hook
                ),
                "supports_prompt_context_hook": snapshot.supports_prompt_context_hook,
                "supports_prompt_teaser_hook": snapshot.supports_prompt_teaser_hook,
                "supports_post_edit_checkpoint_hook": snapshot.supports_post_edit_checkpoint_hook,
                "supports_post_bash_checkpoint_hook": snapshot.supports_post_bash_checkpoint_hook,
                "supports_stop_summary_hook": snapshot.supports_stop_summary_hook,
                "supports_assistant_visible_intervention_fallback": True,
                "supports_chat_visible_hook_delivery": False,
                "supports_subagent_hooks": snapshot.supports_subagent_hooks,
                "supports_pre_compact_hook": snapshot.supports_pre_compact_hook,
                "supports_statusline_command": snapshot.supports_statusline_command,
                "supports_post_tool_matchers": snapshot.supports_post_tool_matchers,
                "supports_slash_commands": snapshot.supports_slash_commands,
                "trusted_project_required": snapshot.trusted_project_required,
                "project_assets_mode": snapshot.project_assets_mode,
                "compatibility_posture": snapshot.overall_posture,
                "baseline_contract": snapshot.baseline_contract,
            }
        )
        return payload
    if normalized == _UNSUPPORTED_HOST_RUNTIME:
        return _base_capabilities(
            host_runtime=normalized,
            host_family=_UNKNOWN_HOST_FAMILY,
            delegation_style=_UNKNOWN_DELEGATION_STYLE,
            supports_native_spawn=False,
            supports_interrupt=False,
            supports_artifact_paths=False,
            supports_local_structured_reasoning=False,
            supports_explicit_model_selection=False,
        )
    return _base_capabilities(
        host_runtime=normalized or _UNKNOWN_HOST_RUNTIME,
        host_family=_UNKNOWN_HOST_FAMILY,
        delegation_style=_UNKNOWN_DELEGATION_STYLE,
        supports_native_spawn=bool(default_when_unknown),
        supports_interrupt=False,
        supports_artifact_paths=False,
        supports_local_structured_reasoning=False,
        supports_explicit_model_selection=False,
    )


def resolve_host_capabilities(
    *candidates: Any,
    environ: Mapping[str, str] | None = None,
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    """Resolve the runtime first, then load the matching host capability contract."""
    return host_capabilities(
        resolve_host_runtime(*candidates, environ=environ),
        default_when_unknown=False,
        repo_root=repo_root,
    )


def native_spawn_supported(host_runtime: Any, *, default_when_unknown: bool = False) -> bool:
    """Return whether the host contract allows native delegated execution."""
    return bool(host_capabilities(host_runtime, default_when_unknown=default_when_unknown).get("supports_native_spawn"))
