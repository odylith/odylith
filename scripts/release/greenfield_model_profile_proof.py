"""Observed release proof for installed Greenfield model profiles."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from greenfield_model_profiles import MODEL_PROFILES
from greenfield_model_profiles import UNAVAILABLE_PROVIDER_PROFILE
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
    greenfield_model_profile_observation_issues,
)


MODEL_PROFILE_PROOF_VERSION = "odylith.greenfield.installed-model-profile-proof.v1"
UNAVAILABLE_PROVIDER_FAILURE_TEXT = "model authoring is unavailable"


def sealed_model_profile_observation(
    *,
    proposal: Mapping[str, Any] | None = None,
    create_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Read the actual request observation from its sealed authority owner."""

    proposal_row = _mapping(proposal)
    payload = _mapping(create_payload)
    candidates = (
        _nested_mapping(
            proposal_row,
            "product_intent_authority",
            "operating_envelope",
            "model_contract",
            "observed",
        ),
        _nested_mapping(
            _mapping(proposal_row.get("intent")),
            "product_intent_authority",
            "operating_envelope",
            "model_contract",
            "observed",
        ),
        _nested_mapping(
            payload,
            "product_create_transaction",
            "semantic_snapshot",
            "operating_envelope",
            "model_contract",
            "observed",
        ),
        _nested_mapping(payload, "clarification", "model_profile"),
        _mapping(payload.get("model_profile")),
    )
    for candidate in candidates:
        if candidate:
            return {
                key: candidate.get(key)
                for key in (
                    "profile_id",
                    "provider",
                    "model",
                    "reasoning_effort",
                    "effective_timeout_seconds",
                    "authoring_tier",
                )
            }
    return {}


def model_profile_release_proof(
    results: Sequence[Any],
    *,
    require_complete: bool,
) -> dict[str, Any]:
    """Require installed semantic success and strict latency for each profile."""

    rows: dict[str, list[Any]] = {profile_id: [] for profile_id in MODEL_PROFILES}
    issues: list[str] = []
    for result in results:
        evidence = _mapping(getattr(result, "evidence", None))
        profile_evidence = _mapping(evidence.get("model_profile"))
        profile_id = str(profile_evidence.get("profile_id") or "").strip()
        if profile_id not in rows:
            issues.append(f"matrix result `{getattr(result, 'name', '')}` lacks a supported observed model profile")
            continue
        rows[profile_id].append(result)
        if str(profile_evidence.get("status") or "") != "passed":
            issues.append(f"model profile `{profile_id}` lacks sealed request parity")
        if str(getattr(result, "status", "") or "").strip() != "passed":
            issues.append(f"model profile `{profile_id}` lacks a passed terminal matrix result")
        issues.extend(
            f"model profile `{profile_id}` {issue}"
            for issue in _profile_observation_issues(profile_evidence, profile_id)
        )
        if not bool(getattr(getattr(result, "quality", None), "passed", False)):
            issues.append(f"model profile `{profile_id}` has a semantic or product-quality failure")
        elapsed = _float_value(getattr(result, "proposal_seconds", 0.0))
        budget = get_greenfield_model_profile(profile_id).consumer_budget_seconds
        if not 0.0 < elapsed < budget:
            issues.append(f"model profile `{profile_id}` is missing strict under-{budget:g}s installed latency proof")
    if require_complete:
        for profile_id, profile_results in rows.items():
            if not profile_results:
                issues.append(f"release proof is missing model profile `{profile_id}`")
    profile_summaries = {}
    for profile_id, profile_results in rows.items():
        contract = get_greenfield_model_profile(profile_id)
        elapsed_values = [
            _float_value(getattr(result, "proposal_seconds", 0.0))
            for result in profile_results
        ]
        profile_summaries[profile_id] = {
            "repair_tier": contract.repair_tier,
            "provider": contract.provider,
            "model": contract.model,
            "reasoning_effort": contract.reasoning_effort,
            "consumer_budget_seconds": contract.consumer_budget_seconds,
            "lower_capability": contract.lower_capability,
            "case_count": len(profile_results),
            "worst_proposal_seconds": max(elapsed_values, default=0.0),
            "status": (
                "passed"
                if profile_results
                and all(_result_proves_profile(result, profile_id) for result in profile_results)
                else "missing"
                if not profile_results
                else "failed"
            ),
        }
    cleaned_issues = tuple(dict.fromkeys(issues))
    return {
        "version": MODEL_PROFILE_PROOF_VERSION,
        "status": "passed" if not cleaned_issues else "failed",
        "required_complete_coverage": bool(require_complete),
        "profiles": profile_summaries,
        "issues": list(cleaned_issues),
    }


def unavailable_provider_proof_issues(
    *,
    returncode: int,
    proposal_seconds: float,
    detail: str,
    write_audit_active: bool,
    write_audit_error: str,
    write_attempts: Sequence[str],
    subprocess_attempts: Sequence[str],
    changed_records: Sequence[str],
    staged_transaction_present: bool,
) -> tuple[str, ...]:
    """Require the negative profile to fail quickly before any repository write."""

    contract = get_greenfield_model_profile(UNAVAILABLE_PROVIDER_PROFILE)
    issues: list[str] = []
    if returncode == 0:
        issues.append("unavailable-provider proposal unexpectedly succeeded")
    if not 0.0 < _float_value(proposal_seconds) < contract.consumer_budget_seconds:
        issues.append("unavailable-provider failure did not finish inside the rescue budget")
    if UNAVAILABLE_PROVIDER_FAILURE_TEXT not in str(detail or "").casefold():
        issues.append("unavailable-provider proposal did not report model authoring unavailability")
    if not write_audit_active:
        issues.append("unavailable-provider proposal did not activate the installed write audit")
    if write_audit_error:
        issues.append("unavailable-provider write audit failed")
    if write_attempts:
        issues.append("unavailable-provider proposal attempted repository writes")
    if subprocess_attempts:
        issues.append("unavailable-provider proposal attempted a child process")
    if changed_records:
        issues.append("unavailable-provider proposal changed governed or staged records")
    if staged_transaction_present:
        issues.append("unavailable-provider proposal staged a transaction")
    return tuple(issues)


def _result_proves_profile(result: Any, profile_id: str) -> bool:
    evidence = _mapping(getattr(result, "evidence", None))
    profile_evidence = _mapping(evidence.get("model_profile"))
    contract = get_greenfield_model_profile(profile_id)
    return (
        str(getattr(result, "status", "") or "").strip() == "passed"
        and bool(getattr(getattr(result, "quality", None), "passed", False))
        and str(profile_evidence.get("status") or "") == "passed"
        and not _profile_observation_issues(profile_evidence, profile_id)
        and 0.0
        < _float_value(getattr(result, "proposal_seconds", 0.0))
        < contract.consumer_budget_seconds
    )


def _profile_observation_issues(
    profile_evidence: Mapping[str, Any],
    profile_id: str,
) -> tuple[str, ...]:
    observed = _mapping(profile_evidence.get("observed"))
    if set(observed) != {
        "profile_id",
        "provider",
        "model",
        "reasoning_effort",
        "effective_timeout_seconds",
        "authoring_tier",
    }:
        return ("lacks the stable six-field request observation",)
    if str(observed.get("profile_id") or "").strip() != profile_id:
        return ("observation identifies a different profile",)
    issues = list(
        greenfield_model_profile_observation_issues(
            profile_id=profile_id,
            provider=str(observed.get("provider") or ""),
            model=str(observed.get("model") or ""),
            reasoning_effort=str(observed.get("reasoning_effort") or ""),
            effective_timeout_seconds=observed.get("effective_timeout_seconds"),
            authoring_tier=str(observed.get("authoring_tier") or ""),
        )
    )
    return tuple(issues)


def _nested_mapping(value: Mapping[str, Any], *path: str) -> Mapping[str, Any]:
    current: Mapping[str, Any] = value
    for key in path:
        current = _mapping(current.get(key))
        if not current:
            return {}
    return current


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _float_value(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


__all__ = [
    "MODEL_PROFILE_PROOF_VERSION",
    "model_profile_release_proof",
    "sealed_model_profile_observation",
    "unavailable_provider_proof_issues",
]
