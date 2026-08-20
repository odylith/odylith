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
    "odylith.greenfield.semantic-execution-contract.v22"
)
SEMANTIC_EXECUTION_EVIDENCE_VERSION = (
    "odylith.greenfield.semantic-execution-evidence.v23"
)
ACTIVE_SEMANTIC_MECHANISM_ID = (
    "independent_source_pair_with_bounded_typed_rescue"
)
STANDARD_COMPLETION_DEADLINE_SECONDS = 60
RESCUE_COMPLETION_DEADLINE_SECONDS = 90
DEEP_COMPLETION_DEADLINE_SECONDS = 120

_SUCCESS_CALL_COUNTS = {
    "standard": {"commit": 3, "clarify": 3},
    "rescue": {"commit": 4, "clarify": 4},
    "explicit_deep": {"commit": 4, "clarify": 4},
}
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
        "entry_reason": "reusable_standard_handoff",
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
                "independent_prompt_only_materiality_critic",
                "one_full_graph_and_one_source_only_hypothesis",
            ],
            "first_wave_concurrency": "parallel",
            "candidate_selection": (
                "independent_source_admission_then_whole_existing_hypothesis"
            ),
            "candidate_validation": "paired_source_and_completion_end_to_end_packet",
            "source_authority": (
                "exact_pair_discard_and_ambiguity_settlement_then_independent_"
                "source_admission"
            ),
            "completion_disagreement": (
                "typed_source_handoff_then_one_frontier_existing_candidate_selection"
            ),
            "source_pair_failure": (
                "fail_closed_without_fresh_graph_authorship"
            ),
            "hedge_degradation": (
                "completed_source_authority_remains_reusable_when_full_graph_times_out"
            ),
            "materiality_authority": (
                "one_prompt_only_critic_challenged_by_two_typed_source_hypotheses_"
                "with_two_source_agreement_required_to_settle_and_one_bounded_"
                "frontier_adjudication_on_disagreement"
            ),
            "policy_alignment": (
                "source_and_completion_admitted_before_final_selection"
            ),
            "rescue_graph_authorship": 0,
            "discard_custody": "exact_overlapping_source_spans_removed_before_sealing",
            "citation_custody": "host_authored_atomic_refs_exact_byte_validated",
            "terminal_authority": (
                "single_compiled_author_output_without_downstream_recompilation"
            ),
            "semantic_retries": 0,
            "post_confirm_semantic_calls": 0,
        },
        "successful_model_call_counts": {
            tier: dict(counts) for tier, counts in _SUCCESS_CALL_COUNTS.items()
        },
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
        expected_calls = _SUCCESS_CALL_COUNTS[tier].get(outcome)
        if expected_calls is None:
            raise ValueError("completed semantic execution has no useful terminal outcome")
        if calls != expected_calls:
            raise ValueError("completed semantic execution has the wrong model-call count")
        if not completion_within_tier(tier=tier, wall_ms=wall_ms):
            raise ValueError("completed semantic execution exceeds its execution tier")
    return dict(row)


def require_reusable_standard_handoff(value: Any, *, case_id: str) -> str:
    """Return the canonical hash of one exact, reusable standard-path handoff."""

    row = _mapping(value, "standard failure receipt")
    if row.get("case_id") != case_id:
        raise ValueError("rescue predecessor belongs to another Greenfield case")
    evidence = require_semantic_execution_evidence(row.get("mechanism_execution"))
    if evidence["tier"] != "standard" or evidence["status"] != "rescue_required":
        raise ValueError("rescue requires one reusable standard-path handoff")
    handoff_contract = {
        "standard_deadline_exceeded": (
            "final_graph_adjudication", "passed"
        ),
        "typed_standard_handoff": (
            "graph_completion", {"reusable_source_pair", "reusable_source_handoff"}
        ),
    }
    if evidence["outcome"] not in handoff_contract:
        raise ValueError("rescue requires one reusable standard-path handoff")
    expected_stage, expected_source_status = handoff_contract[evidence["outcome"]]
    accepted_source_statuses = (
        expected_source_status
        if isinstance(expected_source_status, set)
        else {expected_source_status}
    )
    if row.get("failed_stage") != expected_stage:
        raise ValueError("rescue standard handoff stage is not reusable")
    critic = _mapping(row.get("materiality_critic"), "deadline materiality critic")
    source = _mapping(row.get("source_hypothesis"), "deadline source hypothesis")
    if (
        critic.get("validation_status") != "passed"
        or source.get("validation_status") not in accepted_source_statuses
        or source.get("authority_used") is not False
        or evidence["model_call_count"] != 3
    ):
        raise ValueError("rescue deadline handoff lacks reusable typed authority")
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
    "require_reusable_standard_handoff",
    "semantic_execution_contract",
    "semantic_execution_contract_sha256",
    "semantic_execution_evidence",
]
