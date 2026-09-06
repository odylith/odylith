"""Observed release proof for installed Greenfield model profiles."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from greenfield_model_profiles import MODEL_PROFILES
from greenfield_model_profiles import UNAVAILABLE_PROVIDER_PROFILE
from greenfield_model_profiles import model_stage_observation_issues
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
    greenfield_model_profile_observation_issues,
)


MODEL_PROFILE_PROOF_VERSION = "odylith.greenfield.installed-model-profile-proof.v2"
UNAVAILABLE_PROVIDER_FAILURE_TEXT = "model authoring is unavailable"
TRANSACTION_COMMITTED_EXPECTATION = "transaction_committed"
CLARIFICATION_REQUIRED_EXPECTATION = "clarification_required"
CLARIFICATION_NO_WRITE_SCORE_BASIS = "clarification_required_no_write_contract"


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
    validation_issues: list[str] = []
    coverage_issues: list[str] = []
    for result in results:
        evidence = _mapping(getattr(result, "evidence", None))
        profile_evidence = _mapping(evidence.get("model_profile"))
        profile_id = str(profile_evidence.get("profile_id") or "").strip()
        if profile_id not in rows:
            validation_issues.append(
                f"matrix result `{getattr(result, 'name', '')}` lacks a supported observed model profile"
            )
            continue
        rows[profile_id].append(result)
        if str(profile_evidence.get("status") or "") != "passed":
            validation_issues.append(f"model profile `{profile_id}` lacks sealed request parity")
        if str(getattr(result, "status", "") or "").strip() != "passed":
            validation_issues.append(f"model profile `{profile_id}` lacks a passed terminal matrix result")
        validation_issues.extend(
            f"model profile `{profile_id}` {issue}"
            for issue in _profile_observation_issues(
                profile_evidence, profile_id, expectation=_result_expectation(result)
            )
        )
        if not bool(getattr(getattr(result, "quality", None), "passed", False)):
            validation_issues.append(f"model profile `{profile_id}` has a semantic or product-quality failure")
        elapsed = _float_value(getattr(result, "proposal_seconds", 0.0))
        budget = get_greenfield_model_profile(profile_id).consumer_budget_seconds
        if not 0.0 < elapsed < budget:
            validation_issues.append(
                f"model profile `{profile_id}` is missing strict under-{budget:g}s installed latency proof"
            )
        expectation = _result_expectation(result)
        if expectation not in {TRANSACTION_COMMITTED_EXPECTATION, CLARIFICATION_REQUIRED_EXPECTATION}:
            validation_issues.append(
                f"model profile `{profile_id}` lacks a declared supported case expectation"
            )
        elif expectation == CLARIFICATION_REQUIRED_EXPECTATION and not _result_proves_clarification_no_write(
            result,
            profile_id,
        ):
            validation_issues.append(
                f"model profile `{profile_id}` clarification row lacks source-bound no-write proof"
            )
    if require_complete:
        for profile_id, profile_results in rows.items():
            if not profile_results:
                coverage_issues.append(f"release proof is missing model profile `{profile_id}`")
            elif not any(_result_proves_committed_case(result, profile_id) for result in profile_results):
                coverage_issues.append(
                    f"release proof is missing a committed positive case for model profile `{profile_id}`"
                )

    lower_profile_ids = tuple(
        profile_id
        for profile_id in MODEL_PROFILES
        if get_greenfield_model_profile(profile_id).lower_capability
    )
    if not lower_profile_ids:
        validation_issues.append("supported model profiles do not declare a lower-capability semantic member")
    for profile_id in lower_profile_ids:
        profile_results = rows[profile_id]
        if not any(_result_proves_committed_case(result, profile_id) for result in profile_results):
            coverage_issues.append(
                f"lower-capability model profile `{profile_id}` lacks an observed committed positive case"
            )
        if not any(_result_proves_clarification_no_write(result, profile_id) for result in profile_results):
            coverage_issues.append(
                f"lower-capability model profile `{profile_id}` lacks an observed "
                "source-bound clarification/no-write control"
            )

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
            "source_review_model": contract.source_review_model,
            "source_review_reasoning_effort": contract.source_review_reasoning_effort,
            "consumer_budget_seconds": contract.consumer_budget_seconds,
            "lower_capability": contract.lower_capability,
            "lower_capability_role": "initial_authoring" if contract.lower_capability else "not_applicable",
            "case_count": len(profile_results),
            "committed_positive_case_count": sum(
                _result_proves_committed_case(result, profile_id)
                for result in profile_results
            ),
            "clarification_no_write_control_count": sum(
                _result_proves_clarification_no_write(result, profile_id)
                for result in profile_results
            ),
            "worst_proposal_seconds": max(elapsed_values, default=0.0),
            "status": (
                "passed"
                if profile_results
                and all(_result_proves_valid_case(result, profile_id) for result in profile_results)
                else "missing"
                if not profile_results
                else "failed"
            ),
        }
    lower_capability_scope = _lower_capability_scope(rows, lower_profile_ids)
    cleaned_validation_issues = tuple(dict.fromkeys(validation_issues))
    cleaned_coverage_issues = tuple(dict.fromkeys(coverage_issues))
    cleaned_issues = (*cleaned_validation_issues, *cleaned_coverage_issues)
    status = (
        "failed"
        if cleaned_validation_issues or (require_complete and cleaned_coverage_issues)
        else "passed"
    )
    return {
        "version": MODEL_PROFILE_PROOF_VERSION,
        "status": status,
        "coverage_status": "passed" if not cleaned_coverage_issues else "incomplete",
        "required_complete_coverage": bool(require_complete),
        "profiles": profile_summaries,
        "lower_capability_scope": lower_capability_scope,
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

    del subprocess_attempts
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
        and not _profile_observation_issues(
            profile_evidence, profile_id, expectation=_result_expectation(result)
        )
        and 0.0
        < _float_value(getattr(result, "proposal_seconds", 0.0))
        < contract.consumer_budget_seconds
    )


def _result_proves_committed_case(result: Any, profile_id: str) -> bool:
    return (
        _result_expectation(result) == TRANSACTION_COMMITTED_EXPECTATION
        and _result_proves_profile(result, profile_id)
    )


def _result_proves_clarification_no_write(result: Any, profile_id: str) -> bool:
    """Verify the retained source binding and fail-safe clarification contract."""

    if not _result_proves_profile(result, profile_id):
        return False
    evidence = _mapping(getattr(result, "evidence", None))
    case = _mapping(evidence.get("case"))
    clarification = _mapping(evidence.get("clarification"))
    no_write = _mapping(evidence.get("no_write"))
    expected = _mapping(case.get("expected_clarification"))
    expected_field = str(expected.get("field") or "").strip()
    expected_question = str(expected.get("question") or "").strip()
    question = str(clarification.get("question") or "").strip()
    required_fields = clarification.get("required_fields")
    quality = getattr(result, "quality", None)
    return (
        _result_expectation(result) == CLARIFICATION_REQUIRED_EXPECTATION
        and _is_sha256(case.get("prompt_sha256"))
        and bool(expected_field)
        and isinstance(required_fields, Sequence)
        and not isinstance(required_fields, (str, bytes))
        and tuple(str(value or "").strip() for value in required_fields) == (expected_field,)
        and str(clarification.get("mode") or "").strip() == CLARIFICATION_REQUIRED_EXPECTATION
        and clarification.get("returncode") == 0
        and bool(question)
        and (not expected_question or question == expected_question)
        and str(getattr(quality, "score_basis", "") or "").strip()
        == CLARIFICATION_NO_WRITE_SCORE_BASIS
        and tuple(getattr(quality, "issues", ()) or ()) == ()
        and no_write.get("write_audit_active") is True
        and not str(no_write.get("write_audit_error") or "").strip()
        and _empty_sequence(no_write.get("write_attempts"))
        and _empty_sequence(no_write.get("changed_records"))
        and no_write.get("staged_transaction_present") is False
        and isinstance(no_write.get("before_record_count"), int)
        and isinstance(no_write.get("after_record_count"), int)
        and no_write.get("before_record_count") == no_write.get("after_record_count")
    )


def _result_proves_valid_case(result: Any, profile_id: str) -> bool:
    expectation = _result_expectation(result)
    if expectation == TRANSACTION_COMMITTED_EXPECTATION:
        return _result_proves_committed_case(result, profile_id)
    if expectation == CLARIFICATION_REQUIRED_EXPECTATION:
        return _result_proves_clarification_no_write(result, profile_id)
    return False


def _result_expectation(result: Any) -> str:
    evidence = _mapping(getattr(result, "evidence", None))
    case = _mapping(evidence.get("case"))
    return str(case.get("expectation") or "").strip().casefold()


def _lower_capability_scope(
    rows: Mapping[str, Sequence[Any]],
    lower_profile_ids: Sequence[str],
) -> dict[str, Any]:
    """Report only profile identity actually observed in valid installed rows."""

    observed_profiles: list[dict[str, Any]] = []
    complete = bool(lower_profile_ids)
    for profile_id in lower_profile_ids:
        profile_results = rows.get(profile_id, ())
        valid_results = [
            result for result in profile_results if _result_proves_profile(result, profile_id)
        ]
        positive_count = sum(
            _result_proves_committed_case(result, profile_id) for result in profile_results
        )
        clarification_count = sum(
            _result_proves_clarification_no_write(result, profile_id)
            for result in profile_results
        )
        if not valid_results:
            complete = False
            continue
        evidence = _mapping(getattr(valid_results[0], "evidence", None))
        observed = _mapping(_mapping(evidence.get("model_profile")).get("observed"))
        observed_profiles.append(
            {
                key: observed.get(key)
                for key in (
                    "profile_id",
                    "provider",
                    "model",
                    "reasoning_effort",
                    "effective_timeout_seconds",
                    "authoring_tier",
                )
            }
            | {
                "committed_positive_case_count": positive_count,
                "clarification_no_write_control_count": clarification_count,
            }
        )
        complete = complete and positive_count > 0 and clarification_count > 0
    return {
        "status": "passed" if complete else "unproven",
        "observed_profiles": observed_profiles,
        "role": "initial_authoring",
        "requirement": "installed_committed_positive_and_source_bound_clarification_no_write",
    }


def _profile_observation_issues(
    profile_evidence: Mapping[str, Any],
    profile_id: str,
    *,
    expectation: str,
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
    stages = _mapping(profile_evidence.get("stage_observation"))
    issues.extend(model_stage_observation_issues(
        profile_id, observed=observed, stage_observation=stages,
    ))
    expected_status = (
        "authored" if expectation == TRANSACTION_COMMITTED_EXPECTATION
        else "clarification_required"
    )
    if _nested_mapping(stages, "response", "result").get("status") != expected_status:
        issues.append("retained model response does not match the declared case outcome")
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


def _is_sha256(value: Any) -> bool:
    normalized = str(value or "").strip().casefold()
    return len(normalized) == 64 and all(character in "0123456789abcdef" for character in normalized)


def _empty_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 0


__all__ = [
    "MODEL_PROFILE_PROOF_VERSION",
    "model_profile_release_proof",
    "sealed_model_profile_observation",
    "unavailable_provider_proof_issues",
]
