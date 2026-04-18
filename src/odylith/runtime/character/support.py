from __future__ import annotations

from typing import Any


HOST_LANE_SUPPORT_CONTRACT = "odylith_agent_operating_character_host_lane_support.v1"

SUPPORTED_HOST_FAMILIES: tuple[str, ...] = ("codex", "claude")
SUPPORTED_LANES: tuple[str, ...] = ("dev", "dogfood", "consumer")

_HOST_ALIASES: dict[str, str] = {
    "codex": "codex",
    "codex_cli": "codex",
    "codex-cli": "codex",
    "openai_codex": "codex",
    "gpt_5_codex": "codex",
    "gpt-5-codex": "codex",
    "gpt_5_2_codex": "codex",
    "gpt-5.2-codex": "codex",
    "gpt_5_3_codex": "codex",
    "gpt-5.3-codex": "codex",
    "gpt_5_4": "codex",
    "gpt-5.4": "codex",
    "claude": "claude",
    "claude_code": "claude",
    "claude-code": "claude",
    "anthropic_claude": "claude",
    "claude_haiku": "claude",
    "claude-haiku": "claude",
    "claude_sonnet": "claude",
    "claude-sonnet": "claude",
    "claude_opus": "claude",
    "claude-opus": "claude",
}

_LANE_ALIASES: dict[str, str] = {
    "dev": "dev",
    "source_local": "dev",
    "source-local": "dev",
    "maintainer": "dev",
    "maintainer_dev": "dev",
    "maintainer-dev": "dev",
    "dogfood": "dogfood",
    "pinned": "dogfood",
    "pinned_dogfood": "dogfood",
    "pinned-dogfood": "dogfood",
    "pinned_release": "dogfood",
    "consumer": "consumer",
    "consumer_lane": "consumer",
    "consumer-lane": "consumer",
    "installed": "consumer",
}


def normalize_host_family(value: str) -> str:
    token = str(value or "").strip().lower().replace(" ", "_")
    if token in _HOST_ALIASES:
        return _HOST_ALIASES[token]
    compact = token.replace("_", "-")
    if "claude" in compact or "anthropic" in compact:
        return "claude"
    if "codex" in compact or compact.startswith(("gpt-", "gpt", "o1", "o3", "o4")):
        return "codex"
    return token or "unknown"


def normalize_lane(value: str) -> str:
    token = str(value or "").strip().lower().replace(" ", "_")
    return _LANE_ALIASES.get(token, token or "unknown")


def host_capabilities(host_family: str) -> dict[str, Any]:
    host = normalize_host_family(host_family)
    common = {
        "semantic_character_contract": True,
        "local_character_check": True,
        "hot_path_provider_calls": 0,
        "hot_path_host_model_calls": 0,
        "credit_safe_by_default": True,
        "host_model_scope": "adapter_family_model_agnostic",
        "host_model_credit_policy": "character_checks_never_call_host_models",
    }
    if host == "codex":
        return {
            **common,
            "host_family": "codex",
            "known_host": True,
            "delegation_surface": "routed_spawn",
            "skill_surfaces": [".agents/skills/odylith-agent-operating-character/SKILL.md"],
            "visible_intervention_status_command": "odylith codex intervention-status --repo-root .",
        }
    if host == "claude":
        return {
            **common,
            "host_family": "claude",
            "known_host": True,
            "delegation_surface": "task_tool_subagents",
            "skill_surfaces": [
                ".claude/skills/odylith-agent-operating-character/SKILL.md",
                ".claude/commands/odylith-agent-operating-character.md",
            ],
            "visible_intervention_status_command": "odylith claude intervention-status --repo-root .",
        }
    return {
        **common,
        "semantic_character_contract": False,
        "host_family": host,
        "known_host": False,
        "delegation_surface": "none",
        "skill_surfaces": [],
        "visible_intervention_status_command": "",
    }


def lane_capabilities(lane: str) -> dict[str, Any]:
    normalized = normalize_lane(lane)
    if normalized == "dev":
        return {
            "lane": "dev",
            "known_lane": True,
            "runtime_posture": "source_local",
            "product_mutation_default": "allowed_when_grounded",
            "release_claim_allowed": False,
        }
    if normalized == "dogfood":
        return {
            "lane": "dogfood",
            "known_lane": True,
            "runtime_posture": "pinned_dogfood",
            "product_mutation_default": "allowed_when_pinned_runtime_healthy",
            "release_claim_allowed": False,
        }
    if normalized == "consumer":
        return {
            "lane": "consumer",
            "known_lane": True,
            "runtime_posture": "installed_managed_runtime",
            "product_mutation_default": "diagnose_and_handoff",
            "release_claim_allowed": False,
        }
    return {
        "lane": normalized,
        "known_lane": False,
        "runtime_posture": "unknown",
        "product_mutation_default": "diagnose_and_handoff",
        "release_claim_allowed": False,
    }


def host_lane_support(*, host_family: str, lane: str) -> dict[str, Any]:
    host = host_capabilities(host_family)
    lane_profile = lane_capabilities(lane)
    return {
        "contract": HOST_LANE_SUPPORT_CONTRACT,
        "host_family": host["host_family"],
        "lane": lane_profile["lane"],
        "supported_host_families": list(SUPPORTED_HOST_FAMILIES),
        "supported_lanes": list(SUPPORTED_LANES),
        "known_host": bool(host["known_host"]),
        "known_lane": bool(lane_profile["known_lane"]),
        "semantic_contract_supported": bool(host["known_host"] and host["semantic_character_contract"] and lane_profile["known_lane"]),
        "local_character_check": bool(host["local_character_check"]),
        "credit_safe_hot_path": bool(host["credit_safe_by_default"]),
        "host_model_scope": str(host["host_model_scope"]),
        "host_model_credit_policy": str(host["host_model_credit_policy"]),
        "host_model_calls_allowed_by_default": False,
        "provider_calls_allowed_by_default": False,
        "delegation_surface": str(host["delegation_surface"]),
        "runtime_posture": str(lane_profile["runtime_posture"]),
        "product_mutation_default": str(lane_profile["product_mutation_default"]),
        "visible_intervention_status_command": str(host["visible_intervention_status_command"]),
        "skill_surfaces": list(host["skill_surfaces"]),
    }


def host_lane_matrix() -> list[dict[str, Any]]:
    return [
        host_lane_support(host_family=host, lane=lane)
        for host in SUPPORTED_HOST_FAMILIES
        for lane in SUPPORTED_LANES
    ]


__all__ = [
    "HOST_LANE_SUPPORT_CONTRACT",
    "SUPPORTED_HOST_FAMILIES",
    "SUPPORTED_LANES",
    "host_capabilities",
    "host_lane_matrix",
    "host_lane_support",
    "lane_capabilities",
    "normalize_host_family",
    "normalize_lane",
]
