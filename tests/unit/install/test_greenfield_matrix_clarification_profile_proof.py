from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    DEEP_PROFILE_ID,
    RESCUE_PROFILE_ID,
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
)
from tests.unit.install.test_greenfield_matrix_clarification import (
    _host_native_clarification_execution,
    _host_native_clarification_stage,
    _host_native_reviewer_admission_observation,
    _host_native_reviewer_clarification_observation,
)

from greenfield_matrix_clarification import clarification_quality_verdict
from greenfield_model_profile_proof import model_profile_release_proof
from greenfield_model_profiles import model_profile_environment
from greenfield_model_profiles import model_profile_evidence


def _host_native_clarification_profile_evidence(
    source: str,
    *,
    profile_id: str = STANDARD_PROFILE_ID,
) -> dict[str, object]:
    return model_profile_evidence(
        profile_id,
        model_profile_environment(profile_id, {}),
        observed={},
        stage_observation=_host_native_clarification_stage(
            source,
            profile_id=profile_id,
        ),
        expected_source=source,
    )


def _host_native_authored_profile_evidence(
    source: str,
    *,
    profile_id: str = STANDARD_PROFILE_ID,
) -> dict[str, object]:
    profile = get_greenfield_model_profile(profile_id)
    stage = _host_native_clarification_stage(source, profile_id=profile_id)
    stage["response_kind"] = "authored"
    observed = {
        "origin": "host_native",
        "host_candidate": {
            "version": "odylith.greenfield.host-candidate.v1",
            "contract_version": "odylith.greenfield.intent-authoring.v75",
            "source_sha256": stage["source_sha256"],
            "candidate_sha256": stage["candidate_sha256"],
        },
        "candidate_review": {
            "profile_id": profile_id,
            "provider": profile.provider,
            "model": profile.review_model,
            "reasoning_effort": profile.review_reasoning_effort,
            "effective_timeout_seconds": 120.0,
            "authoring_tier": profile.repair_tier,
        },
    }
    reviewer_candidate_sha256 = "9" * 64
    reviewer = _host_native_reviewer_admission_observation(
        source,
        profile_id=profile_id,
        host_candidate_sha256=str(stage["candidate_sha256"]),
        reviewer_candidate_sha256=reviewer_candidate_sha256,
    )
    return model_profile_evidence(
        profile_id,
        model_profile_environment(profile_id, {}),
        observed=observed,
        stage_observation=stage,
        reviewer_observation=reviewer,
        expected_reviewer_candidate_sha256=reviewer_candidate_sha256,
        expected_source=source,
    )


def _host_native_clarification_aggregate_result(
    source: str,
    *,
    profile_evidence: dict[str, object],
) -> SimpleNamespace:
    execution = _host_native_clarification_execution(source)
    public = execution.payload["clarification"]
    return SimpleNamespace(
        name="host-native clarification",
        status="passed",
        proposal_seconds=18.02,
        quality=clarification_quality_verdict(()),
        evidence={
            "case": {
                "expectation": "clarification_required",
                "prompt_sha256": hashlib.sha256(b"prompt").hexdigest(),
                "expected_clarification": {
                    "field": "first_path",
                    "question": public["question"],
                },
            },
            "clarification": {
                "mode": "clarification_required",
                "question": public["question"],
                "required_fields": ["first_path"],
                "returncode": 0,
            },
            "no_write": {
                "before_record_count": 0,
                "after_record_count": 0,
                "changed_records": [],
                "staged_transaction_present": False,
                "write_audit_active": True,
                "write_attempts": [],
                "write_audit_error": "",
            },
            "model_profile": profile_evidence,
        },
    )


def _host_native_committed_aggregate_result(
    *,
    profile_evidence: dict[str, object],
) -> SimpleNamespace:
    return SimpleNamespace(
        name="host-native committed",
        status="passed",
        proposal_seconds=18.02,
        quality=SimpleNamespace(passed=True),
        evidence={
            "case": {
                "expectation": "transaction_committed",
                "prompt_sha256": hashlib.sha256(b"prompt").hexdigest(),
            },
            "model_profile": profile_evidence,
        },
    )


def test_reviewer_selected_clarification_stays_host_native_without_reclassifying_host_output() -> None:
    source = "The first complete task remains materially ambiguous."
    stage = _host_native_clarification_stage(source)
    stage["response_kind"] = "authored"
    stage["candidate_review_status"] = "clarification_required"
    reviewer = _host_native_reviewer_clarification_observation(source)
    review = reviewer["candidate_review"]
    assert isinstance(review, dict)

    evidence = model_profile_evidence(
        STANDARD_PROFILE_ID,
        model_profile_environment(STANDARD_PROFILE_ID, {}),
        observed={},
        stage_observation=stage,
        reviewer_observation=reviewer,
        expected_reviewer_candidate_sha256=str(review["candidate_sha256"]),
        expected_source=source,
    )

    assert evidence["status"] == "passed", evidence["issues"]
    summary = evidence["stage_observation_summary"]
    assert summary["response_kind"] == "authored"
    assert summary["clarification_origin"] == "reviewer"
    assert evidence["sealed_request_roles"] == ["host_candidate"]
    assert summary["reviewer_receipt_verified"] is True
    assert not any(
        "participant_selection" in issue or "remaining_candidate_authoring" in issue
        for issue in evidence["issues"]
    )

    result = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=evidence,
    )
    proof = model_profile_release_proof((result,), require_complete=False)
    assert proof["status"] == "passed", proof["issues"]


def test_host_native_clarification_passes_aggregate_profile_proof() -> None:
    source = "The first complete task remains materially ambiguous."
    profile_evidence = _host_native_clarification_profile_evidence(source)
    result = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=profile_evidence,
    )

    proof = model_profile_release_proof((result,), require_complete=False)

    assert proof["status"] == "passed", proof["issues"]
    assert proof["profiles"][STANDARD_PROFILE_ID]["maximum_semantic_model_calls"] == 1


def test_release_profile_proof_requires_astra_success_and_luna_no_write_control() -> None:
    source = "The first complete task remains materially ambiguous."
    clarification = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=_host_native_clarification_profile_evidence(
            source,
            profile_id=RESCUE_PROFILE_ID,
        ),
    )
    authored_evidence = _host_native_authored_profile_evidence(
        source,
        profile_id=STANDARD_PROFILE_ID,
    )
    assert authored_evidence["status"] == "passed", authored_evidence["issues"]
    committed = _host_native_committed_aggregate_result(
        profile_evidence=authored_evidence,
    )
    proof = model_profile_release_proof((committed, clarification), require_complete=True)

    assert proof["status"] == "passed", proof["issues"]
    assert proof["lower_capability_scope"]["status"] == "passed"
    assert proof["lower_capability_scope"]["role"] == "host_candidate"
    observed = proof["lower_capability_scope"]["observed_profiles"]
    assert len(observed) == 1
    assert observed[0]["profile_id"] == RESCUE_PROFILE_ID
    assert observed[0]["model"] == get_greenfield_model_profile(
        RESCUE_PROFILE_ID
    ).model
    assert observed[0]["committed_positive_case_count"] == 0
    assert observed[0]["clarification_no_write_control_count"] == 1


def test_complete_release_profile_proof_fails_without_astra_or_luna_control() -> None:
    source = "The first complete task remains materially ambiguous."
    astra = _host_native_committed_aggregate_result(
        profile_evidence=_host_native_authored_profile_evidence(source),
    )
    luna = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=_host_native_clarification_profile_evidence(
            source,
            profile_id=RESCUE_PROFILE_ID,
        ),
    )

    missing_luna = model_profile_release_proof((astra,), require_complete=True)
    missing_astra = model_profile_release_proof((luna,), require_complete=True)

    assert missing_luna["status"] == "failed"
    assert any("clarification/no-write control" in issue for issue in missing_luna["issues"])
    assert missing_astra["status"] == "failed"
    assert any("missing success profile" in issue for issue in missing_astra["issues"])


def test_release_profile_proof_rejects_duplicate_luna_controls() -> None:
    source = "The first complete task remains materially ambiguous."
    committed = _host_native_committed_aggregate_result(
        profile_evidence=_host_native_authored_profile_evidence(source),
    )
    clarification = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=_host_native_clarification_profile_evidence(
            source,
            profile_id=RESCUE_PROFILE_ID,
        ),
    )

    proof = model_profile_release_proof(
        (committed, clarification, clarification),
        require_complete=True,
    )

    assert proof["status"] == "failed"
    assert any("exactly one result" in issue for issue in proof["issues"])


def test_luna_or_sol_positive_result_cannot_qualify_release_success() -> None:
    source = "The first complete task remains materially ambiguous."
    luna_positive = _host_native_committed_aggregate_result(
        profile_evidence=_host_native_authored_profile_evidence(
            source,
            profile_id=RESCUE_PROFILE_ID,
        ),
    )
    sol_evidence = _host_native_authored_profile_evidence(
        source,
        profile_id=DEEP_PROFILE_ID,
    )
    sol_positive = _host_native_committed_aggregate_result(
        profile_evidence=sol_evidence,
    )

    luna_proof = model_profile_release_proof((luna_positive,), require_complete=False)
    sol_proof = model_profile_release_proof((sol_positive,), require_complete=False)

    assert luna_proof["status"] == "failed"
    assert any("must clarify without writing" in issue for issue in luna_proof["issues"])
    assert sol_proof["status"] == "failed"
    assert any("unsupported diagnostic" in issue for issue in sol_proof["issues"])
    assert sol_proof["profiles"][STANDARD_PROFILE_ID]["committed_positive_case_count"] == 0


def test_supported_profile_rejects_a_forged_profile_relabel() -> None:
    source = "The first complete task remains materially ambiguous."
    forged = _host_native_authored_profile_evidence(source)
    forged["profile_id"] = RESCUE_PROFILE_ID

    proof = model_profile_release_proof(
        (_host_native_committed_aggregate_result(profile_evidence=forged),),
        require_complete=False,
    )

    assert proof["status"] == "failed"
    assert any("different model profile" in issue for issue in proof["issues"])


@pytest.mark.parametrize(
    "binding",
    (
        "configured_provider", "configured_model", "configured_effort", "stage",
        "host_executable", "host_shape", "host_argument_count", "host_output_schema",
        "host_model", "host_effort", "review_profile", "review_provider",
        "review_model", "review_effort",
    ),
)
def test_supported_profile_rechecks_each_host_native_profile_binding(binding: str) -> None:
    source = "The first complete task remains materially ambiguous."
    evidence = _host_native_authored_profile_evidence(source)
    if binding == "configured_provider":
        evidence["configured"]["provider"] = "anthropic-cli"
    elif binding == "configured_model":
        evidence["configured"]["model"] = "gpt-5.6-sol"
    elif binding == "configured_effort":
        evidence["configured"]["reasoning_effort"] = "high"
    elif binding == "stage":
        evidence["stage_observation"]["model_profile_id"] = RESCUE_PROFILE_ID
    elif binding == "host_executable":
        evidence["stage_observation"]["host_request"]["executable_sha256"] = "a" * 64
    elif binding == "host_shape":
        evidence["stage_observation"]["host_request"]["argv_shape_sha256"] = "b" * 64
    elif binding == "host_argument_count":
        evidence["stage_observation"]["host_request"]["argument_count"] = 15
    elif binding == "host_output_schema":
        evidence["stage_observation"]["host_request"]["output_schema_present"] = False
    elif binding == "host_model":
        evidence["stage_observation"]["host_request"]["model"] = "gpt-5.6-sol"
    elif binding == "host_effort":
        evidence["stage_observation"]["host_request"]["reasoning_effort"] = "high"
    elif binding == "review_profile":
        evidence["observed"]["candidate_review"]["profile_id"] = RESCUE_PROFILE_ID
    elif binding == "review_provider":
        evidence["observed"]["candidate_review"]["provider"] = "anthropic-cli"
    elif binding == "review_model":
        evidence["observed"]["candidate_review"]["model"] = "gpt-5.6-sol"
    else:
        evidence["observed"]["candidate_review"]["reasoning_effort"] = "high"

    proof = model_profile_release_proof(
        (_host_native_committed_aggregate_result(profile_evidence=evidence),),
        require_complete=False,
    )

    assert proof["status"] == "failed"
    expected_issue = {
        "configured_provider": "host-native configured model",
        "configured_model": "host-native configured model",
        "configured_effort": "host-native configured model",
        "stage": "host-native stage identifies a different model profile",
        "host_executable": "host-native executable identity does not match the sealed observation",
        "host_shape": "retained host-native argv shape fingerprint is invalid",
        "host_argument_count": "retained host-native argument count is invalid",
        "host_output_schema": "retained host-native output schema proof is missing",
        "host_model": "retained host-native argv model does not match",
        "host_effort": "retained host-native argv reasoning effort does not match",
        "review_profile": "host-native candidate review identifies a different model profile",
        "review_provider": "observed provider does not match",
        "review_model": "observed model does not match",
        "review_effort": "observed reasoning_effort does not match",
    }[binding]
    assert any(expected_issue in issue for issue in proof["issues"])


def test_aggregate_clarification_rejects_contradictory_authored_observations() -> None:
    source = "The first complete task remains materially ambiguous."
    profile_evidence = _host_native_clarification_profile_evidence(source)
    profile_evidence["observed"] = {
        "participant_selection": {},
        "remaining_candidate_authoring": {},
    }
    result = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=profile_evidence,
    )

    proof = model_profile_release_proof((result,), require_complete=False)

    assert proof["status"] == "failed"
    assert any("contradictory authored observations" in issue for issue in proof["issues"])


def test_aggregate_authored_evidence_cannot_be_reclassified_by_response_kind() -> None:
    source = "The first complete task remains materially ambiguous."
    profile_evidence = _host_native_authored_profile_evidence(source)
    assert profile_evidence["status"] == "passed", profile_evidence["issues"]
    profile_evidence["stage_observation"]["response_kind"] = "clarification_required"
    result = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=profile_evidence,
    )

    proof = model_profile_release_proof((result,), require_complete=False)

    assert proof["status"] == "failed"
    assert any("reviewed candidate does not match" in issue for issue in proof["issues"])


def test_aggregate_clarification_revalidates_retained_expected_source_hash() -> None:
    source = "The first complete task remains materially ambiguous."
    profile_evidence = _host_native_clarification_profile_evidence(source)
    profile_evidence["stage_observation"]["source_sha256"] = "4" * 64
    result = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=profile_evidence,
    )

    proof = model_profile_release_proof((result,), require_complete=False)

    assert proof["status"] == "failed"
    assert any("source does not match" in issue for issue in proof["issues"])


@pytest.mark.parametrize(
    "elapsed",
    (180.0, 180.001, None, True, "18.0", 0.0, -1.0, float("nan"), float("inf")),
)
def test_aggregate_clarification_rejects_expired_or_invalid_elapsed(elapsed: object) -> None:
    source = "The first complete task remains materially ambiguous."
    profile_evidence = _host_native_clarification_profile_evidence(source)
    profile_evidence["stage_observation"]["elapsed_seconds"] = elapsed
    result = _host_native_clarification_aggregate_result(
        source,
        profile_evidence=profile_evidence,
    )

    proof = model_profile_release_proof((result,), require_complete=False)

    assert proof["status"] == "failed"
    assert any("operational-timeout proof" in issue for issue in proof["issues"])
