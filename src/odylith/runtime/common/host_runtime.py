"""Host runtime detection and host-capability guards."""

from __future__ import annotations

import os
from typing import Any, Mapping


_CODEX_HOST_RUNTIME = "codex_cli"
_CLAUDE_HOST_RUNTIME = "claude_cli"
_UNSUPPORTED_HOST_RUNTIME = "unsupported"
_UNKNOWN_HOST_RUNTIME = "unknown"
_CODEX_HOST_FAMILY = "codex"
_CLAUDE_HOST_FAMILY = "claude"
_UNKNOWN_HOST_FAMILY = "unknown"
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
    return " ".join(str(value or "").split()).strip().lower().replace("-", "_").replace(" ", "_")


def _is_truthy_env(value: Any) -> bool:
    token = str(value or "").strip().lower()
    return token not in {"", "0", "false", "no", "off"}


def normalize_host_runtime(value: Any) -> str:
    token = _normalize_token(value)
    if token in _CODEX_TOKENS:
        return _CODEX_HOST_RUNTIME
    if token in _CLAUDE_TOKENS:
        return _CLAUDE_HOST_RUNTIME
    if token in _UNSUPPORTED_TOKENS:
        return _UNSUPPORTED_HOST_RUNTIME
    return ""


def detect_host_runtime(*, environ: Mapping[str, str] | None = None) -> str:
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
    for value in candidates:
        normalized = normalize_host_runtime(value)
        if normalized:
            return normalized
    return detect_host_runtime(environ=environ)


def host_capabilities(host_runtime: Any, *, default_when_unknown: bool = False) -> dict[str, Any]:
    normalized = normalize_host_runtime(host_runtime)
    if normalized == _CODEX_HOST_RUNTIME:
        return {
            "host_runtime": normalized,
            "host_family": _CODEX_HOST_FAMILY,
            "model_family": _CODEX_HOST_FAMILY,
            "supports_native_spawn": True,
            "supports_interrupt": True,
            "supports_artifact_paths": True,
            "supports_local_structured_reasoning": True,
            "supports_explicit_model_selection": True,
        }
    if normalized == _CLAUDE_HOST_RUNTIME:
        return {
            "host_runtime": normalized,
            "host_family": _CLAUDE_HOST_FAMILY,
            "model_family": _CLAUDE_HOST_FAMILY,
            "supports_native_spawn": False,
            "supports_interrupt": False,
            "supports_artifact_paths": False,
            "supports_local_structured_reasoning": True,
            "supports_explicit_model_selection": False,
        }
    if normalized == _UNSUPPORTED_HOST_RUNTIME:
        return {
            "host_runtime": normalized,
            "host_family": _UNKNOWN_HOST_FAMILY,
            "model_family": _UNKNOWN_HOST_FAMILY,
            "supports_native_spawn": False,
            "supports_interrupt": False,
            "supports_artifact_paths": False,
            "supports_local_structured_reasoning": False,
            "supports_explicit_model_selection": False,
        }
    return {
        "host_runtime": normalized or _UNKNOWN_HOST_RUNTIME,
        "host_family": _UNKNOWN_HOST_FAMILY,
        "model_family": _UNKNOWN_HOST_FAMILY,
        "supports_native_spawn": bool(default_when_unknown),
        "supports_interrupt": False,
        "supports_artifact_paths": False,
        "supports_local_structured_reasoning": False,
        "supports_explicit_model_selection": False,
    }


def resolve_host_capabilities(*candidates: Any, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    return host_capabilities(
        resolve_host_runtime(*candidates, environ=environ),
        default_when_unknown=False,
    )


def native_spawn_supported(host_runtime: Any, *, default_when_unknown: bool = False) -> bool:
    return bool(host_capabilities(host_runtime, default_when_unknown=default_when_unknown).get("supports_native_spawn"))
