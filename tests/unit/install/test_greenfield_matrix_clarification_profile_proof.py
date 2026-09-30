from __future__ import annotations

from copy import deepcopy
import hashlib
from types import SimpleNamespace

import pytest

from greenfield_matrix_host_candidate import HOST_NATIVE_ARGV_ARGUMENT_COUNT
from greenfield_matrix_host_candidate import HOST_NATIVE_ARGV_SHAPE_SHA256
from greenfield_matrix_host_candidate import HOST_NATIVE_MATRIX_OBSERVATION_VERSION
from greenfield_model_profile_proof import model_profile_release_proof
from greenfield_model_profiles import DEEP_PROFILE_ID
from greenfield_model_profiles import RESCUE_PROFILE_ID
from greenfield_model_profiles import STANDARD_PROFILE_ID
from greenfield_model_profiles import model_profile_environment
from greenfield_model_profiles import model_profile_evidence
from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    admit_greenfield_host_candidate,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import (
    HOST_CANDIDATE_FORMAT_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
)


SOURCE = "The first complete task remains materially ambiguous."
MISSING = object()


def _profile_evidence(profile_id: str = STANDARD_PROFILE_ID) -> dict[str, object]:
    raw_candidate = {
        "version": HOST_CANDIDATE_FORMAT_VERSION,
        "result": {
            "status": "clarification_required",
            "consistency": {
                "status": "material_ambiguity",
                "evidence_quotes": [],
            },
            "clarification": {"material_dimension": "first_path"},
        },
    }
    _candidate, receipt = admit_greenfield_host_candidate(
        raw_candidate,
        evidence_text=SOURCE,
        clock=lambda: 1.0,
    )
    contract = get_greenfield_model_profile(profile_id)
    observed = {
        "origin": "host_native",
        "host_candidate": receipt,
        "runtime_semantic_model_call_count": 0,
    }
    stage = {
        "version": HOST_NATIVE_MATRIX_OBSERVATION_VERSION,
        "status": "passed",
        "host_invocations": 1,
        "contract_command_invocations": 1,
        "proposal_command_invocations": 1,
        "runtime_semantic_model_call_count": 0,
        "post_receipt_provider_invocations": 0,
        "model_profile_id": profile_id,
        "host_request": {
            "version": "odylith.greenfield.host-argv-receipt.v1",
            "executable_sha256": "1" * 64,
            "argument_count": HOST_NATIVE_ARGV_ARGUMENT_COUNT,
            "model": contract.model,
            "reasoning_effort": contract.reasoning_effort,
            "output_schema_present": True,
            "argv_shape_sha256": HOST_NATIVE_ARGV_SHAPE_SHA256,
        },
        "candidate_temp_cleaned": True,
        "host_workspace_cleaned": True,
        "stage": "propose",
        "contract_returncode": 0,
        "contract_sha256": "2" * 64,
        "source_sha256": hashlib.sha256(SOURCE.encode()).hexdigest(),
        "candidate_schema_sha256": "3" * 64,
        "host_returncode": 0,
        "host_stdout_bytes": 500,
        "host_stderr_bytes": 0,
        "response_kind": "clarification_required",
        "raw_candidate_sha256": receipt["raw_candidate_sha256"],
        "host_output_sha256": "4" * 64,
        "host_output_bytes": 500,
        "candidate_temp_outside_repo": True,
        "proposal_returncode": 0,
        "proposal_stdout_sha256": "5" * 64,
        "proposal_stderr_sha256": "6" * 64,
        "proposal_mode": "clarification_required",
        "elapsed_seconds": 18.02,
    }
    return model_profile_evidence(
        profile_id,
        model_profile_environment(profile_id, {}),
        observed=observed,
        stage_observation=stage,
        raw_candidate=raw_candidate,
        expected_source=SOURCE,
    )


def _result(
    *,
    profile_evidence: dict[str, object],
    expectation: str,
) -> SimpleNamespace:
    profile_evidence = deepcopy(profile_evidence)
    if expectation == "transaction_committed":
        profile_evidence["stage_observation"]["response_kind"] = "authored"
        profile_evidence["stage_observation"][
            "proposal_mode"
        ] = "product_create_transaction"
    evidence: dict[str, object] = {
        "case": {
            "expectation": expectation,
            "prompt_sha256": hashlib.sha256(b"prompt").hexdigest(),
        },
        "model_profile": profile_evidence,
    }
    score_basis = "release_quality_score"
    if expectation == "clarification_required":
        evidence.update(
            {
                "clarification": {
                    "mode": "clarification_required",
                    "question": "What complete task should the first user finish?",
                    "required_fields": ["first_path"],
                    "returncode": 0,
                },
                "no_write": {
                    "write_audit_active": True,
                    "write_audit_error": "",
                    "write_attempts": [],
                    "changed_records": [],
                    "staged_transaction_present": False,
                },
            }
        )
        score_basis = "clarification_required_no_write_contract"
    return SimpleNamespace(
        name=f"{expectation}:{profile_evidence['profile_id']}",
        status="passed",
        proposal_seconds=18.02,
        quality=SimpleNamespace(passed=True, score_basis=score_basis),
        evidence=evidence,
    )


def _mutate_path(
    value: dict[str, object], path: tuple[str, ...], replacement: object
) -> None:
    target = value
    for key in path[:-1]:
        target = target[key]
    if replacement is MISSING:
        target.pop(path[-1])
    else:
        target[path[-1]] = replacement


def test_host_clarification_passes_aggregate_profile_proof() -> None:
    evidence = _profile_evidence()
    proof = model_profile_release_proof(
        (_result(profile_evidence=evidence, expectation="clarification_required"),),
        require_complete=False,
    )
    assert proof["status"] == "passed", proof["issues"]
    profile = proof["profiles"][STANDARD_PROFILE_ID]
    assert profile["host_semantic_model_calls"] == 1
    assert profile["runtime_semantic_model_calls_after_candidate_receipt"] == 0
    assert profile["post_receipt_provider_invocations"] == 0


def test_complete_release_profile_requires_standard_success_and_rescue_no_write_control() -> None:
    standard = _result(
        profile_evidence=_profile_evidence(STANDARD_PROFILE_ID),
        expectation="transaction_committed",
    )
    rescue = _result(
        profile_evidence=_profile_evidence(RESCUE_PROFILE_ID),
        expectation="clarification_required",
    )
    proof = model_profile_release_proof((standard, rescue), require_complete=True)
    assert proof["status"] == "passed", proof["issues"]
    assert proof["lower_capability_scope"]["status"] == "passed"
    assert proof["lower_capability_scope"]["role"] == "host_candidate"


def test_complete_release_profile_fails_without_rescue_control() -> None:
    standard = _result(
        profile_evidence=_profile_evidence(STANDARD_PROFILE_ID),
        expectation="transaction_committed",
    )
    proof = model_profile_release_proof((standard,), require_complete=True)
    assert proof["status"] == "failed"
    assert any("clarification/no-write case" in issue for issue in proof["issues"])


def test_lower_capability_positive_result_cannot_qualify_release_success() -> None:
    rescue = _result(
        profile_evidence=_profile_evidence(RESCUE_PROFILE_ID),
        expectation="transaction_committed",
    )
    proof = model_profile_release_proof((rescue,), require_complete=False)
    assert proof["status"] == "failed"
    assert any("must clarify without writing" in issue for issue in proof["issues"])


def test_deep_profile_cannot_qualify_release_success() -> None:
    deep = _result(
        profile_evidence=_profile_evidence(DEEP_PROFILE_ID),
        expectation="transaction_committed",
    )
    proof = model_profile_release_proof((deep,), require_complete=False)
    assert proof["status"] == "failed"
    assert any("unsupported diagnostic" in issue for issue in proof["issues"])


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("configured", "model"), "gpt-5.6-sol"),
        (("stage_observation", "model_profile_id"), RESCUE_PROFILE_ID),
        (("stage_observation", "host_request", "argument_count"), 15),
        (("stage_observation", "host_request", "output_schema_present"), False),
        (("stage_observation", "host_request", "model"), "gpt-5.6-sol"),
        (("stage_observation", "post_receipt_provider_invocations"), 1),
        (("observed", "runtime_semantic_model_call_count"), 1),
    ),
)
def test_release_profile_rechecks_single_authority_bindings(
    path: tuple[str, ...],
    value: object,
) -> None:
    evidence = deepcopy(_profile_evidence())
    target = evidence
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    proof = model_profile_release_proof(
        (_result(profile_evidence=evidence, expectation="transaction_committed"),),
        require_complete=False,
    )
    assert proof["status"] == "failed"


@pytest.mark.parametrize(
    "path",
    (
        ("host_semantic_model_calls",),
        ("runtime_semantic_model_calls_after_candidate_receipt",),
        ("post_receipt_provider_invocations",),
        ("stage_observation_summary", "host_semantic_model_calls"),
        (
            "stage_observation_summary",
            "runtime_semantic_model_calls_after_candidate_receipt",
        ),
        ("stage_observation_summary", "post_receipt_provider_invocations"),
        ("observed", "runtime_semantic_model_call_count"),
        ("stage_observation", "host_invocations"),
        ("stage_observation", "contract_command_invocations"),
        ("stage_observation", "proposal_command_invocations"),
        ("stage_observation", "runtime_semantic_model_call_count"),
        ("stage_observation", "post_receipt_provider_invocations"),
    ),
)
@pytest.mark.parametrize("invalid", (False, True, 0.0, MISSING))
def test_aggregate_profile_rejects_non_integer_call_counts(
    path: tuple[str, ...],
    invalid: object,
) -> None:
    evidence = _profile_evidence()
    _mutate_path(evidence, path, invalid)

    proof = model_profile_release_proof(
        (_result(profile_evidence=evidence, expectation="clarification_required"),),
        require_complete=False,
    )

    assert proof["status"] == "failed"


@pytest.mark.parametrize(
    "elapsed",
    (180.0, 180.001, None, True, "18.0", 0.0, -1.0, float("nan"), float("inf")),
)
def test_aggregate_profile_rejects_expired_or_invalid_elapsed(elapsed: object) -> None:
    evidence = _profile_evidence()
    evidence["stage_observation"]["elapsed_seconds"] = elapsed
    proof = model_profile_release_proof(
        (_result(profile_evidence=evidence, expectation="clarification_required"),),
        require_complete=False,
    )
    assert proof["status"] == "failed"
