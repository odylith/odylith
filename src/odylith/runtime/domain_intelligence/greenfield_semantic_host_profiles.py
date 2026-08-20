"""Published pinned model profiles eligible for Greenfield semantic authority."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


HOST_EXECUTION_PROFILE_VERSION = "odylith.greenfield.host-execution-profile.v1"
STANDARD_HOST_STAGE_PROFILE_VERSION = (
    "odylith.greenfield.standard-host-stage-profile.v13"
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
        "critic_model": "gpt-5.6-sol",
        "critic_reasoning_effort": "low",
        "source_hypothesis_model": "gpt-5.5",
        "source_hypothesis_reasoning_effort": "low",
        "final_adjudicator_model": "gpt-5.6-sol",
        "final_adjudicator_reasoning_effort": "low",
    },
    "claude": {
        "version": STANDARD_HOST_STAGE_PROFILE_VERSION,
        "host_profile": "claude",
        "critic_model": "claude-opus-4-6",
        "critic_reasoning_effort": "medium",
        "source_hypothesis_model": "claude-opus-4-6",
        "source_hypothesis_reasoning_effort": "low",
        "final_adjudicator_model": "claude-opus-4-6",
        "final_adjudicator_reasoning_effort": "low",
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


def standard_host_stage_profile(host_profile: str) -> dict[str, str]:
    """Return the exact no-retry stage profile for the 60-second path."""

    host = str(host_profile or "").strip()
    if host not in _STANDARD_STAGE_PROFILES:
        raise RuntimeError("unsupported Greenfield semantic host profile")
    return dict(_STANDARD_STAGE_PROFILES[host])


def standard_host_stage_profiles() -> list[dict[str, str]]:
    """Publish standard-path profiles separately from deep-tier profiles."""

    return [standard_host_stage_profile(host) for host in supported_host_profiles()]


__all__ = [
    "HOST_EXECUTION_PROFILE_VERSION",
    "STANDARD_HOST_STAGE_PROFILE_VERSION",
    "host_execution_profile",
    "require_host_execution_profile",
    "require_host_profiles",
    "semantic_authority_execution_profiles",
    "standard_host_stage_profile",
    "standard_host_stage_profiles",
    "supported_host_profiles",
]
