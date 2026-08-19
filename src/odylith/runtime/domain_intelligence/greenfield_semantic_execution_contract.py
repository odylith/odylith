"""Typed execution identity and latency laws for Greenfield semantic authority."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    semantic_authority_execution_profiles,
    standard_host_stage_profile,
    standard_host_stage_profiles,
)


SEMANTIC_EXECUTION_CONTRACT_VERSION = (
    "odylith.greenfield.semantic-execution-contract.v1"
)
SEMANTIC_EXECUTION_EVIDENCE_VERSION = (
    "odylith.greenfield.semantic-execution-evidence.v2"
)
ACTIVE_SEMANTIC_MECHANISM_ID = (
    "parallel_materiality_atomic_source_then_typed_graph_completion"
)
STANDARD_COMPLETION_DEADLINE_SECONDS = 60
RESCUE_COMPLETION_DEADLINE_SECONDS = 90
DEEP_COMPLETION_DEADLINE_SECONDS = 120

_SUCCESS_CALL_COUNTS = {"commit": 4, "clarify": 4}
_TIER_CONTRACTS = {
    "standard": {
        "deadline_ms": STANDARD_COMPLETION_DEADLINE_SECONDS * 1000,
        "comparison": "strictly_less_than",
        "entry_reason": "consumer_request",
        "host_profile_contract": "standard_stage_profile",
    },
    "rescue": {
        "deadline_ms": RESCUE_COMPLETION_DEADLINE_SECONDS * 1000,
        "comparison": "less_than_or_equal",
        "entry_reason": "typed_standard_failure",
        "host_profile_contract": "standard_stage_profile",
    },
    "explicit_deep": {
        "deadline_ms": DEEP_COMPLETION_DEADLINE_SECONDS * 1000,
        "comparison": "less_than_or_equal",
        "entry_reason": "explicit_operator_or_ci",
        "host_profile_contract": "deep_authority_profile",
    },
}


def semantic_execution_contract() -> dict[str, Any]:
    """Return the one active mechanism and its non-negotiable execution laws."""

    return {
        "version": SEMANTIC_EXECUTION_CONTRACT_VERSION,
        "mechanism_id": ACTIVE_SEMANTIC_MECHANISM_ID,
        "topology": {
            "first_wave": [
                "materiality_critic",
                "source_path",
                "source_boundary",
            ],
            "first_wave_concurrency": "parallel",
            "terminal_author": {
                "commit": "typed_graph_completion_after_settled_materiality_and_source",
                "clarify": "independent_clarification_challenge_after_materiality",
            },
            "semantic_retries": 0,
            "post_confirm_semantic_calls": 0,
        },
        "successful_model_call_counts": dict(_SUCCESS_CALL_COUNTS),
        "tiers": {name: dict(row) for name, row in _TIER_CONTRACTS.items()},
        "automatic_deep_tier": False,
        "standard_and_rescue_host_profiles": standard_host_stage_profiles(),
        "explicit_deep_host_profiles": semantic_authority_execution_profiles(),
    }


def semantic_execution_contract_sha256() -> str:
    return _canonical_sha256(semantic_execution_contract())


def semantic_execution_evidence(
    *,
    host_profile: str,
    tier: str,
    status: str,
    outcome: str,
    wall_ms: int,
    model_call_count: int,
    restart_count: int,
    implementation_fingerprint_sha256: str,
    prior_standard_failure_sha256: str = "",
) -> dict[str, Any]:
    """Build and validate one terminal mechanism-execution receipt."""

    tier_contract = _tier_contract(tier)
    host_contract = (
        standard_host_stage_profile(host_profile)
        if tier_contract["host_profile_contract"] == "standard_stage_profile"
        else _deep_host_profile(host_profile)
    )
    row = {
        "version": SEMANTIC_EXECUTION_EVIDENCE_VERSION,
        "mechanism_id": ACTIVE_SEMANTIC_MECHANISM_ID,
        "mechanism_contract_sha256": semantic_execution_contract_sha256(),
        "implementation_fingerprint_sha256": implementation_fingerprint_sha256,
        "host_profile": host_profile,
        "host_contract": host_contract,
        "tier": tier,
        "entry_reason": tier_contract["entry_reason"],
        "status": status,
        "outcome": outcome,
        "wall_ms": wall_ms,
        "model_call_count": model_call_count,
        "restart_count": restart_count,
        "automatic_deep_tier": False,
        "prior_standard_failure_sha256": prior_standard_failure_sha256,
    }
    return require_semantic_execution_evidence(row)


def require_semantic_execution_evidence(value: Any) -> dict[str, Any]:
    """Validate exact mechanism identity, tier entry, calls, and deadlines."""

    row = _mapping(value, "semantic execution evidence")
    expected_keys = {
        "version",
        "mechanism_id",
        "mechanism_contract_sha256",
        "implementation_fingerprint_sha256",
        "host_profile",
        "host_contract",
        "tier",
        "entry_reason",
        "status",
        "outcome",
        "wall_ms",
        "model_call_count",
        "restart_count",
        "automatic_deep_tier",
        "prior_standard_failure_sha256",
    }
    if set(row) != expected_keys:
        raise ValueError("semantic execution evidence fields do not match its contract")
    if row.get("version") != SEMANTIC_EXECUTION_EVIDENCE_VERSION:
        raise ValueError("semantic execution evidence version is unsupported")
    if row.get("mechanism_id") != ACTIVE_SEMANTIC_MECHANISM_ID:
        raise ValueError("semantic execution evidence names a non-active mechanism")
    if row.get("mechanism_contract_sha256") != semantic_execution_contract_sha256():
        raise ValueError("semantic execution evidence changes its mechanism contract")
    _require_sha256(
        str(row.get("implementation_fingerprint_sha256") or ""),
        "execution implementation fingerprint",
    )
    tier = _text(row.get("tier"), "execution tier")
    tier_contract = _tier_contract(tier)
    if row.get("entry_reason") != tier_contract["entry_reason"]:
        raise ValueError("semantic execution evidence uses the wrong tier entry reason")
    host_profile = _text(row.get("host_profile"), "execution host profile")
    expected_host = (
        standard_host_stage_profile(host_profile)
        if tier_contract["host_profile_contract"] == "standard_stage_profile"
        else _deep_host_profile(host_profile)
    )
    if row.get("host_contract") != expected_host:
        raise ValueError("semantic execution evidence changes its host contract")
    wall_ms = _nonnegative_integer(row.get("wall_ms"), "execution wall_ms")
    calls = _nonnegative_integer(
        row.get("model_call_count"), "execution model_call_count"
    )
    restarts = _nonnegative_integer(row.get("restart_count"), "execution restart_count")
    if restarts != 0:
        raise ValueError("semantic execution evidence contains a retry or restart")
    if row.get("automatic_deep_tier") is not False:
        raise ValueError("semantic execution evidence enables automatic deep execution")
    predecessor = str(row.get("prior_standard_failure_sha256") or "")
    if tier == "rescue":
        _require_sha256(predecessor, "rescue prior standard failure")
    elif predecessor:
        raise ValueError("only rescue evidence may bind a prior standard failure")
    status = _text(row.get("status"), "execution status")
    outcome = _text(row.get("outcome"), "execution outcome")
    if status == "completed":
        expected_calls = _SUCCESS_CALL_COUNTS.get(outcome)
        if expected_calls is None:
            raise ValueError("completed semantic execution has no useful terminal outcome")
        if calls != expected_calls:
            raise ValueError("completed semantic execution has the wrong model-call count")
        if not completion_within_tier(tier=tier, wall_ms=wall_ms):
            raise ValueError("completed semantic execution exceeds its execution tier")
    return dict(row)


def require_typed_standard_failure(value: Any, *, case_id: str) -> str:
    """Return the canonical hash of the only receipt allowed to enter rescue."""

    row = _mapping(value, "standard failure receipt")
    if row.get("case_id") != case_id:
        raise ValueError("rescue predecessor belongs to another Greenfield case")
    evidence = require_semantic_execution_evidence(row.get("mechanism_execution"))
    if (
        evidence["tier"] != "standard"
        or evidence["status"] != "rescue_required"
        or evidence["outcome"] != "typed_standard_failure"
    ):
        raise ValueError("rescue requires one typed standard-path failure")
    return _canonical_sha256(row)


def completion_within_tier(*, tier: str, wall_ms: int) -> bool:
    contract = _tier_contract(tier)
    observed = _nonnegative_integer(wall_ms, "execution wall_ms")
    deadline = int(contract["deadline_ms"])
    return observed < deadline if contract["comparison"] == "strictly_less_than" else observed <= deadline


def _tier_contract(tier: str) -> dict[str, Any]:
    name = str(tier or "").strip()
    if name not in _TIER_CONTRACTS:
        raise ValueError("semantic execution tier is unsupported")
    return dict(_TIER_CONTRACTS[name])


def _deep_host_profile(host_profile: str) -> dict[str, str]:
    matches = [
        row
        for row in semantic_authority_execution_profiles()
        if row["host_profile"] == host_profile
    ]
    if len(matches) != 1:
        raise RuntimeError("unsupported Greenfield semantic host profile")
    return dict(matches[0])


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return dict(value)


def _text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} must be non-empty")
    return text


def _nonnegative_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _require_sha256(value: str, label: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{label} must be a lowercase SHA-256")


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "ACTIVE_SEMANTIC_MECHANISM_ID",
    "DEEP_COMPLETION_DEADLINE_SECONDS",
    "RESCUE_COMPLETION_DEADLINE_SECONDS",
    "SEMANTIC_EXECUTION_CONTRACT_VERSION",
    "SEMANTIC_EXECUTION_EVIDENCE_VERSION",
    "STANDARD_COMPLETION_DEADLINE_SECONDS",
    "completion_within_tier",
    "require_semantic_execution_evidence",
    "require_typed_standard_failure",
    "semantic_execution_contract",
    "semantic_execution_contract_sha256",
    "semantic_execution_evidence",
]
