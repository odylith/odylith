"""Published pinned model profiles eligible for Greenfield semantic authority."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


HOST_EXECUTION_PROFILE_VERSION = "odylith.greenfield.host-execution-profile.v1"
SEMANTIC_REASONING_CAPABILITY_PROFILE = "frontier_semantic_reasoning"
STANDARD_HOST_STAGE_PROFILE_VERSION = (
    "odylith.greenfield.standard-host-stage-profile.v47"
)

_EXECUTION_PROFILES = {
    "codex": {
        "version": HOST_EXECUTION_PROFILE_VERSION,
        "host_profile": "codex",
        "provider": "openai",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "high",
        "runner_family": "codex_exec",
        "structured_output_mode": "provider_json_schema",
        "tool_event_policy": "reject",
        "session_persistence": "disabled",
    },
    "claude": {
        "version": HOST_EXECUTION_PROFILE_VERSION,
        "host_profile": "claude",
        "provider": "anthropic",
        "model": "claude-opus-4-6",
        "reasoning_effort": "high",
        "runner_family": "claude_print",
        "structured_output_mode": "provider_json_schema",
        "tool_event_policy": "reject",
        "session_persistence": "disabled",
    },
}

_STANDARD_STAGE_PROFILES = {
    "codex": {
        "version": STANDARD_HOST_STAGE_PROFILE_VERSION,
        "host_profile": "codex",
        "authors": [
            {
                "role": "author",
                "model": "gpt-5.6-sol",
                "reasoning_effort": "low",
            },
        ],
    },
    "claude": {
        "version": STANDARD_HOST_STAGE_PROFILE_VERSION,
        "host_profile": "claude",
        "authors": [
            {
                "role": "author",
                "model": "claude-opus-4-6",
                "reasoning_effort": "high",
            },
        ],
    },
}


def supported_host_profiles() -> tuple[str, ...]:
    return tuple(_EXECUTION_PROFILES)


def host_execution_profile(host_profile: str) -> dict[str, str]:
    """Return one exact semantic-authority execution profile."""

    host = str(host_profile or "").strip()
    if host not in _EXECUTION_PROFILES:
        raise RuntimeError("unsupported Greenfield semantic host profile")
    return dict(_EXECUTION_PROFILES[host])


def require_host_profiles(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise RuntimeError("required host profiles must be a JSON string array")
    hosts = [str(row or "").strip() for row in value]
    if (
        not hosts
        or any(not host or host not in _EXECUTION_PROFILES for host in hosts)
        or len(set(hosts)) != len(hosts)
    ):
        raise RuntimeError("required host profiles must be supported, non-empty, and unique")
    return hosts


def require_host_execution_profile(value: Any, *, host_profile: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise RuntimeError("host execution profile must be a JSON object")
    expected = host_execution_profile(host_profile)
    if dict(value) != expected:
        raise RuntimeError("host execution profile does not match its pinned contract")
    return expected


def semantic_authority_execution_profiles() -> list[dict[str, str]]:
    """Publish every exact model profile admitted by the operating envelope."""

    return [host_execution_profile(host) for host in supported_host_profiles()]


def standard_host_stage_profile(host_profile: str) -> dict[str, Any]:
    """Return the exact no-retry stage profile for the 60-second path."""

    host = str(host_profile or "").strip()
    if host not in _STANDARD_STAGE_PROFILES:
        raise RuntimeError("unsupported Greenfield semantic host profile")
    profile = _STANDARD_STAGE_PROFILES[host]
    return {
        "version": profile["version"],
        "host_profile": profile["host_profile"],
        "authors": [dict(row) for row in profile["authors"]],
    }


def standard_author_profile(host_profile: str, run_index: int) -> dict[str, str]:
    """Return the exact profile for the sole standard-path author."""

    if isinstance(run_index, bool) or run_index != 0:
        raise RuntimeError("standard Greenfield author run index is unsupported")
    return dict(standard_host_stage_profile(host_profile)["authors"][run_index])


def standard_host_stage_profiles() -> list[dict[str, Any]]:
    """Publish standard-path profiles separately from deep-tier profiles."""

    return [standard_host_stage_profile(host) for host in supported_host_profiles()]


__all__ = [
    "HOST_EXECUTION_PROFILE_VERSION",
    "SEMANTIC_REASONING_CAPABILITY_PROFILE",
    "STANDARD_HOST_STAGE_PROFILE_VERSION",
    "host_execution_profile",
    "require_host_execution_profile",
    "require_host_profiles",
    "semantic_authority_execution_profiles",
    "standard_author_profile",
    "standard_host_stage_profile",
    "standard_host_stage_profiles",
    "supported_host_profiles",
]
