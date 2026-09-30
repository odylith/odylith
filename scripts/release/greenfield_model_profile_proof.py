"""Observed release proof for one host semantic authority and zero runtime calls."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import hashlib
import math
from typing import Any

from greenfield_matrix_host_candidate import HOST_NATIVE_ARGV_ARGUMENT_COUNT
from greenfield_matrix_host_candidate import HOST_NATIVE_ARGV_RECEIPT_VERSION
from greenfield_matrix_host_candidate import HOST_NATIVE_ARGV_SHAPE_SHA256
from greenfield_model_profiles import DEEP_PROFILE_ID
from greenfield_model_profiles import LOWER_CAPABILITY_CONTROL_PROFILES
from greenfield_model_profiles import MODEL_PROFILES
from greenfield_model_profiles import UNAVAILABLE_PROVIDER_PROFILE
from greenfield_retained_candidate_proof import (
    retained_canonical_candidate_hash_issues,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
)


MODEL_PROFILE_PROOF_VERSION = (
    "odylith.greenfield.installed-single-authority-profile-proof.v7"
)
TRANSACTION_COMMITTED_EXPECTATION = "transaction_committed"
CLARIFICATION_REQUIRED_EXPECTATION = "clarification_required"
CLARIFICATION_NO_WRITE_SCORE_BASIS = "clarification_required_no_write_contract"


def _is_exact_int(value: Any, expected: int) -> bool:
    return type(value) is int and value == expected


def authored_model_result_binding_issues(
    *,
    stage_observation: Mapping[str, Any],
    raw_candidate: Mapping[str, Any],
    create_payload: Mapping[str, Any],
    expected_source: str,
) -> tuple[str, ...]:
    """Bind retained host output to the committed single-authority receipts."""

    stage = _mapping(stage_observation)
    manifest = _nested_mapping(_mapping(create_payload), "commit_manifest")
    model_authoring = _mapping(manifest.get("model_authoring"))
    semantic_compiler = _mapping(manifest.get("semantic_compiler"))
    canonical_authority = _mapping(model_authoring.get("canonical_authority"))
    receipt = _mapping(model_authoring.get("host_candidate"))
    issues: list[str] = []

    expected_model_authoring_fields = {
        "authoring_origin",
        "authoring_version",
        "runtime_semantic_model_call_count",
        "tier",
        "elapsed_seconds",
        "effective_model_window_seconds",
        "host_candidate",
        "canonical_authority",
    }
    if set(model_authoring) != expected_model_authoring_fields:
        issues.append("sealed model-authoring receipt has missing or unsupported fields")
    if model_authoring.get("authoring_origin") != "host_native":
        issues.append("sealed model-authoring receipt does not identify host authority")
    if model_authoring.get("authoring_version") != GREENFIELD_INTENT_AUTHORING_VERSION:
        issues.append("sealed model-authoring version is invalid")
    if not _is_exact_int(
        model_authoring.get("runtime_semantic_model_call_count"), 0
    ):
        issues.append("sealed runtime semantic model call count is not zero")

    expected_compiler = {
        "version": "odylith.greenfield.authored-semantic-validation.v5",
        "status": "passed",
        "semantic_owner": "host_canonical_candidate",
        "post_candidate_receipt_semantic_calls": 0,
    }
    if semantic_compiler != expected_compiler:
        issues.append("semantic compiler does not prove zero post-receipt semantic calls")
    elif not _is_exact_int(
        semantic_compiler.get("post_candidate_receipt_semantic_calls"), 0
    ):
        issues.append("semantic compiler does not prove zero post-receipt semantic calls")

    expected_source_sha256 = hashlib.sha256(expected_source.encode("utf-8")).hexdigest()
    expected_authority_fields = {
        "canonical_candidate_sha256",
        "source_sha256",
        "product_facts_sha256",
        "authored_relation_set_sha256",
    }
    if set(canonical_authority) != expected_authority_fields:
        issues.append("canonical authority has missing or unsupported fields")
    for field in expected_authority_fields:
        if not _is_sha256(canonical_authority.get(field)):
            issues.append(f"canonical authority {field} is invalid")
    if canonical_authority.get("source_sha256") != expected_source_sha256:
        issues.append("canonical authority source hash does not match retained evidence")
    if canonical_authority.get("canonical_candidate_sha256") != receipt.get(
        "canonical_candidate_sha256"
    ):
        issues.append("canonical authority does not match the sealed host candidate")

    issues.extend(
        retained_canonical_candidate_hash_issues(
            raw_candidate=raw_candidate,
            receipt=receipt,
            evidence_text=expected_source,
        )
    )
    if stage.get("raw_candidate_sha256") != receipt.get("raw_candidate_sha256"):
        issues.append("retained host stage does not match the sealed raw candidate")
    if not _is_exact_int(stage.get("runtime_semantic_model_call_count"), 0):
        issues.append("retained host stage reports a runtime semantic model call")
    if not _is_exact_int(stage.get("post_receipt_provider_invocations"), 0):
        issues.append("retained host stage reports a post-receipt provider invocation")
    return tuple(dict.fromkeys(issues))


def sealed_model_profile_observation(
    *,
    proposal: Mapping[str, Any] | None = None,
    create_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Read the request observation from its sealed product-intent authority."""

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
            return deepcopy(dict(candidate))
    return {}


def model_profile_release_proof(
    results: Sequence[Any],
    *,
    require_complete: bool,
) -> dict[str, Any]:
    """Require host/profile parity and zero post-receipt calls for every row."""

    qualified = (*MODEL_PROFILES, *LOWER_CAPABILITY_CONTROL_PROFILES)
    rows: dict[str, list[Any]] = {profile_id: [] for profile_id in qualified}
    validation_issues: list[str] = []
    coverage_issues: list[str] = []
    for result in results:
        evidence = _mapping(getattr(result, "evidence", None))
        profile_evidence = _mapping(evidence.get("model_profile"))
        profile_id = str(profile_evidence.get("profile_id") or "").strip()
        if profile_id == DEEP_PROFILE_ID:
            validation_issues.append(
                "Sol-high is an unsupported diagnostic and cannot count toward release success"
            )
            continue
        if profile_id not in rows:
            validation_issues.append(
                f"matrix result `{getattr(result, 'name', '')}` lacks a supported observed model profile"
            )
            continue
        rows[profile_id].append(result)
        if not _result_proves_profile(result, profile_id):
            validation_issues.append(
                f"model profile `{profile_id}` lacks one-host/zero-runtime-call proof"
            )
        expectation = _result_expectation(result)
        if expectation not in {
            TRANSACTION_COMMITTED_EXPECTATION,
            CLARIFICATION_REQUIRED_EXPECTATION,
        }:
            validation_issues.append(
                f"model profile `{profile_id}` lacks a declared supported case expectation"
            )
        if (
            profile_id in LOWER_CAPABILITY_CONTROL_PROFILES
            and expectation != CLARIFICATION_REQUIRED_EXPECTATION
        ):
            validation_issues.append(
                f"lower-capability control `{profile_id}` must clarify without writing"
            )
        if (
            expectation == CLARIFICATION_REQUIRED_EXPECTATION
            and not _result_proves_clarification_no_write(result, profile_id)
        ):
            validation_issues.append(
                f"model profile `{profile_id}` clarification row lacks source-bound no-write proof"
            )

    for profile_id in MODEL_PROFILES:
        profile_results = rows[profile_id]
        if not any(
            _result_proves_committed_case(result, profile_id)
            for result in profile_results
        ):
            coverage_issues.append(
                f"release proof is missing a committed positive case for model profile `{profile_id}`"
            )
    for profile_id in LOWER_CAPABILITY_CONTROL_PROFILES:
        profile_results = rows[profile_id]
        if not any(
            _result_proves_clarification_no_write(result, profile_id)
            for result in profile_results
        ):
            coverage_issues.append(
                f"lower-capability control `{profile_id}` lacks a clarification/no-write case"
            )

    profiles: dict[str, Any] = {}
    for profile_id, profile_results in rows.items():
        contract = get_greenfield_model_profile(profile_id)
        elapsed = [
            _float_value(getattr(result, "proposal_seconds", 0.0))
            for result in profile_results
        ]
        profiles[profile_id] = {
            "repair_tier": contract.repair_tier,
            "provider": contract.provider,
            "host_model": contract.model,
            "host_reasoning_effort": contract.reasoning_effort,
            "semantic_authority": "active_host_single_authority",
            "host_semantic_model_calls": 1,
            "runtime_semantic_model_calls_after_candidate_receipt": 0,
            "post_receipt_provider_invocations": 0,
            "performance_target_seconds": contract.performance_target_seconds,
            "operational_timeout_seconds": contract.operational_timeout_seconds,
            "performance_target_met": bool(elapsed)
            and max(elapsed) <= contract.performance_target_seconds,
            "lower_capability": contract.lower_capability,
            "lower_capability_role": (
                "host_candidate" if contract.lower_capability else "not_applicable"
            ),
            "case_count": len(profile_results),
            "committed_positive_case_count": sum(
                _result_proves_committed_case(result, profile_id)
                for result in profile_results
            ),
            "clarification_no_write_control_count": sum(
                _result_proves_clarification_no_write(result, profile_id)
                for result in profile_results
            ),
            "worst_proposal_seconds": max(elapsed, default=0.0),
            "status": (
                "passed"
                if profile_results
                and all(
                    _result_proves_valid_case(result, profile_id)
                    for result in profile_results
                )
                else "missing"
                if not profile_results
                else "failed"
            ),
        }

    validation_issues = list(dict.fromkeys(validation_issues))
    coverage_issues = list(dict.fromkeys(coverage_issues))
    valid_lower_profiles = [
        profile_id
        for profile_id in LOWER_CAPABILITY_CONTROL_PROFILES
        if any(
            _result_proves_clarification_no_write(result, profile_id)
            for result in rows.get(profile_id, ())
        )
    ]
    status = (
        "failed"
        if validation_issues or (require_complete and coverage_issues)
        else "passed"
    )
    return {
        "version": MODEL_PROFILE_PROOF_VERSION,
        "status": status,
        "coverage_status": "passed" if not coverage_issues else "incomplete",
        "required_complete_coverage": bool(require_complete),
        "profiles": profiles,
        "lower_capability_scope": {
            "status": (
                "passed" if len(valid_lower_profiles) == len(LOWER_CAPABILITY_CONTROL_PROFILES)
                else "unproven"
            ),
            "role": "host_candidate",
            "requirement": "source_bound_clarification_no_write_only",
            "observed_profiles": [
                {
                    "profile_id": profile_id,
                    "model": get_greenfield_model_profile(profile_id).model,
                    "committed_positive_case_count": profiles[profile_id][
                        "committed_positive_case_count"
                    ],
                    "clarification_no_write_control_count": profiles[profile_id][
                        "clarification_no_write_control_count"
                    ],
                }
                for profile_id in valid_lower_profiles
            ],
        },
        "issues": [*validation_issues, *coverage_issues],
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
    """Require deterministic admission to ignore disabled runtime providers."""

    del detail, subprocess_attempts
    contract = get_greenfield_model_profile(UNAVAILABLE_PROVIDER_PROFILE)
    issues: list[str] = []
    if returncode != 0:
        issues.append("post-receipt provider isolation proposal did not succeed")
    if not 0.0 < _float_value(proposal_seconds) < contract.operational_timeout_seconds:
        issues.append("post-receipt provider isolation exceeded its operational timeout")
    if not write_audit_active:
        issues.append("post-receipt provider isolation did not activate the write audit")
    if write_audit_error:
        issues.append("post-receipt provider isolation write audit failed")
    if write_attempts:
        issues.append("post-receipt provider isolation attempted repository writes")
    unexpected_changes = tuple(
        path
        for path in changed_records
        if not str(path).startswith(".odylith/runtime/greenfield/pending/")
    )
    if unexpected_changes:
        issues.append("post-receipt provider isolation changed governed records")
    if not staged_transaction_present:
        issues.append("post-receipt provider isolation did not stage a transaction")
    return tuple(issues)


def _result_proves_profile(result: Any, profile_id: str) -> bool:
    evidence = _mapping(getattr(result, "evidence", None))
    profile = _mapping(evidence.get("model_profile"))
    contract = get_greenfield_model_profile(profile_id)
    summary = _mapping(profile.get("stage_observation_summary"))
    stage = _mapping(profile.get("stage_observation"))
    observed = _mapping(profile.get("observed"))
    receipt = _mapping(observed.get("host_candidate"))
    host_request = _mapping(stage.get("host_request"))
    stage_elapsed = _float_value(stage.get("elapsed_seconds"))
    expected_response = (
        "clarification_required"
        if _result_expectation(result) == CLARIFICATION_REQUIRED_EXPECTATION
        else "authored"
    )
    exact_observed = {
        "origin",
        "host_candidate",
        "runtime_semantic_model_call_count",
    }
    exact_receipt = {
        "version",
        "contract_version",
        "canonical_version",
        "source_sha256",
        "raw_candidate_sha256",
        "canonical_candidate_sha256",
    }
    configured = _mapping(profile.get("configured"))
    configured_matches = not configured or (
        configured.get("provider") == contract.provider
        and configured.get("model") == contract.model
        and configured.get("reasoning_effort") == contract.reasoning_effort
        and configured.get("maximum_model_timeout_seconds")
        == contract.model_timeout_seconds
    )
    summary_matches = not summary or (
        summary.get("status") == "passed"
        and _is_exact_int(summary.get("host_semantic_model_calls"), 1)
        and _is_exact_int(
            summary.get("runtime_semantic_model_calls_after_candidate_receipt"), 0
        )
        and _is_exact_int(summary.get("post_receipt_provider_invocations"), 0)
    )
    return (
        str(getattr(result, "status", "") or "") == "passed"
        and bool(getattr(getattr(result, "quality", None), "passed", False))
        and profile.get("status") == "passed"
        and profile.get("issues") == []
        and profile.get("profile_id") == profile_id
        and profile.get("semantic_authority") == "active_host_single_authority"
        and profile.get("sealed_request_roles") == ["host_candidate"]
        and _is_exact_int(profile.get("host_semantic_model_calls"), 1)
        and _is_exact_int(
            profile.get("runtime_semantic_model_calls_after_candidate_receipt"), 0
        )
        and _is_exact_int(profile.get("post_receipt_provider_invocations"), 0)
        and configured_matches
        and set(observed) == exact_observed
        and observed.get("origin") == "host_native"
        and _is_exact_int(observed.get("runtime_semantic_model_call_count"), 0)
        and set(receipt) == exact_receipt
        and all(
            _is_sha256(receipt.get(field))
            for field in (
                "source_sha256",
                "raw_candidate_sha256",
                "canonical_candidate_sha256",
            )
        )
        and stage.get("status") == "passed"
        and stage.get("model_profile_id") == profile_id
        and _is_exact_int(stage.get("host_invocations"), 1)
        and _is_exact_int(stage.get("contract_command_invocations"), 1)
        and _is_exact_int(stage.get("proposal_command_invocations"), 1)
        and _is_exact_int(stage.get("runtime_semantic_model_call_count"), 0)
        and _is_exact_int(stage.get("post_receipt_provider_invocations"), 0)
        and stage.get("raw_candidate_sha256") == receipt.get("raw_candidate_sha256")
        and stage.get("source_sha256") == receipt.get("source_sha256")
        and stage.get("response_kind") == expected_response
        and stage.get("proposal_mode")
        == (
            CLARIFICATION_REQUIRED_EXPECTATION
            if expected_response == CLARIFICATION_REQUIRED_EXPECTATION
            else "product_create_transaction"
        )
        and host_request.get("model") == contract.model
        and host_request.get("reasoning_effort") == contract.reasoning_effort
        and host_request.get("version") == HOST_NATIVE_ARGV_RECEIPT_VERSION
        and host_request.get("argument_count") == HOST_NATIVE_ARGV_ARGUMENT_COUNT
        and host_request.get("argv_shape_sha256") == HOST_NATIVE_ARGV_SHAPE_SHA256
        and host_request.get("output_schema_present") is True
        and type(stage_elapsed) is float
        and math.isfinite(stage_elapsed)
        and 0.0 < stage_elapsed < contract.operational_timeout_seconds
        and summary_matches
        and 0.0
        < _float_value(getattr(result, "proposal_seconds", 0.0))
        < contract.operational_timeout_seconds
    )


def _result_proves_committed_case(result: Any, profile_id: str) -> bool:
    return (
        _result_expectation(result) == TRANSACTION_COMMITTED_EXPECTATION
        and _result_proves_profile(result, profile_id)
    )


def _result_proves_clarification_no_write(result: Any, profile_id: str) -> bool:
    if not _result_proves_profile(result, profile_id):
        return False
    evidence = _mapping(getattr(result, "evidence", None))
    case = _mapping(evidence.get("case"))
    clarification = _mapping(evidence.get("clarification"))
    no_write = _mapping(evidence.get("no_write"))
    required_fields = clarification.get("required_fields")
    quality = getattr(result, "quality", None)
    return (
        _result_expectation(result) == CLARIFICATION_REQUIRED_EXPECTATION
        and _is_sha256(case.get("prompt_sha256"))
        and isinstance(required_fields, Sequence)
        and not isinstance(required_fields, (str, bytes))
        and len(required_fields) == 1
        and clarification.get("mode") == CLARIFICATION_REQUIRED_EXPECTATION
        and clarification.get("returncode") == 0
        and bool(str(clarification.get("question") or "").strip())
        and str(getattr(quality, "score_basis", "") or "")
        == CLARIFICATION_NO_WRITE_SCORE_BASIS
        and no_write.get("write_audit_active") is True
        and not str(no_write.get("write_audit_error") or "").strip()
        and _empty_sequence(no_write.get("write_attempts"))
        and _empty_sequence(no_write.get("changed_records"))
        and no_write.get("staged_transaction_present") is False
    )


def _result_proves_valid_case(result: Any, profile_id: str) -> bool:
    if _result_expectation(result) == TRANSACTION_COMMITTED_EXPECTATION:
        return _result_proves_committed_case(result, profile_id)
    if _result_expectation(result) == CLARIFICATION_REQUIRED_EXPECTATION:
        return _result_proves_clarification_no_write(result, profile_id)
    return False


def _result_expectation(result: Any) -> str:
    evidence = _mapping(getattr(result, "evidence", None))
    return str(_mapping(evidence.get("case")).get("expectation") or "").casefold()


def _nested_mapping(value: Mapping[str, Any], *path: str) -> dict[str, Any]:
    current = _mapping(value)
    for key in path:
        current = _mapping(current.get(key))
        if not current:
            return {}
    return current


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _float_value(value: Any) -> float:
    if type(value) not in (int, float):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0


def _is_sha256(value: Any) -> bool:
    normalized = str(value or "").strip().casefold()
    return len(normalized) == 64 and all(
        character in "0123456789abcdef" for character in normalized
    )


def _empty_sequence(value: Any) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and len(value) == 0
    )


__all__ = [
    "MODEL_PROFILE_PROOF_VERSION",
    "authored_model_result_binding_issues",
    "model_profile_release_proof",
    "sealed_model_profile_observation",
    "unavailable_provider_proof_issues",
]
