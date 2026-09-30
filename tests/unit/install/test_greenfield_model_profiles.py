from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from greenfield_matrix_host_candidate import HOST_NATIVE_ARGV_ARGUMENT_COUNT
from greenfield_matrix_host_candidate import HOST_NATIVE_ARGV_SHAPE_SHA256
from greenfield_matrix_host_candidate import HOST_NATIVE_MATRIX_OBSERVATION_VERSION
from greenfield_model_profile_proof import authored_model_result_binding_issues
from greenfield_model_profile_proof import model_profile_release_proof
from greenfield_model_profiles import STANDARD_PROFILE_ID
from greenfield_model_profiles import (
    host_native_clarification_stage_observation_issues,
)
from greenfield_model_profiles import model_profile_environment
from greenfield_model_profiles import model_profile_evidence
from greenfield_retained_candidate_proof import (
    retained_canonical_candidate_hash_issues,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    admit_greenfield_host_candidate,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import (
    HOST_CANDIDATE_FORMAT_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
)


SOURCE = "Build a useful product."
MISSING = object()


def _raw_and_receipt() -> tuple[dict[str, object], dict[str, object]]:
    raw = {
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
    _authored, receipt = admit_greenfield_host_candidate(
        raw,
        evidence_text=SOURCE,
        clock=lambda: 1.0,
    )
    return raw, receipt


def _observed(receipt: dict[str, object]) -> dict[str, object]:
    return {
        "origin": "host_native",
        "host_candidate": deepcopy(receipt),
        "runtime_semantic_model_call_count": 0,
    }


def _stage(receipt: dict[str, object]) -> dict[str, object]:
    profile = get_greenfield_model_profile(STANDARD_PROFILE_ID)
    return {
        "version": HOST_NATIVE_MATRIX_OBSERVATION_VERSION,
        "status": "passed",
        "host_invocations": 2,
        "authority_gate_host_invocations": 1,
        "candidate_host_invocations": 1,
        "contract_command_invocations": 1,
        "authority_check_command_invocations": 1,
        "proposal_command_invocations": 1,
        "runtime_semantic_model_call_count": 0,
        "post_receipt_provider_invocations": 0,
        "model_profile_id": STANDARD_PROFILE_ID,
        "model_window_seconds": profile.model_timeout_seconds,
        "operational_timeout_seconds": profile.operational_timeout_seconds,
        "host_request": {
            "version": "odylith.greenfield.host-argv-receipt.v1",
            "executable_sha256": "1" * 64,
            "argument_count": HOST_NATIVE_ARGV_ARGUMENT_COUNT,
            "model": "gpt-6-astra",
            "reasoning_effort": "medium",
            "output_schema_present": True,
            "argv_shape_sha256": HOST_NATIVE_ARGV_SHAPE_SHA256,
        },
        "authority_gate_request": {
            "version": "odylith.greenfield.host-argv-receipt.v1",
            "executable_sha256": "1" * 64,
            "argument_count": HOST_NATIVE_ARGV_ARGUMENT_COUNT,
            "model": "gpt-6-astra",
            "reasoning_effort": "medium",
            "output_schema_present": True,
            "argv_shape_sha256": HOST_NATIVE_ARGV_SHAPE_SHA256,
        },
        "candidate_temp_cleaned": True,
        "authority_gate_temp_cleaned": True,
        "host_workspace_cleaned": True,
        "stage": "propose",
        "contract_returncode": 0,
        "contract_sha256": "2" * 64,
        "source_sha256": hashlib.sha256(SOURCE.encode()).hexdigest(),
        "authority_gate_schema_sha256": "a" * 64,
        "authority_gate_returncode": 0,
        "authority_gate_output_sha256": "b" * 64,
        "authority_gate_output_bytes": 200,
        "authority_gate_decision": "admit",
        "authority_gate_temp_outside_repo": True,
        "authority_check_returncode": 0,
        "authority_check_stdout_sha256": "c" * 64,
        "authority_check_stderr_sha256": "d" * 64,
        "candidate_schema_sha256": "3" * 64,
        "host_returncode": 0,
        "host_stdout_bytes": 500,
        "host_stderr_bytes": 0,
        "response_kind": "authored",
        "raw_candidate_sha256": receipt["raw_candidate_sha256"],
        "host_output_sha256": "4" * 64,
        "host_output_bytes": 500,
        "candidate_temp_outside_repo": True,
        "proposal_returncode": 0,
        "proposal_stdout_sha256": "5" * 64,
        "proposal_stderr_sha256": "6" * 64,
        "proposal_mode": "product_create_transaction",
        "elapsed_seconds": 12.0,
    }


def _create_payload(receipt: dict[str, object]) -> dict[str, object]:
    return {
        "commit_manifest": {
            "model_authoring": {
                "authoring_origin": "host_native",
                "authoring_version": "odylith.greenfield.intent-authoring.v77",
                "runtime_semantic_model_call_count": 0,
                "tier": "standard",
                "elapsed_seconds": 1.0,
                "effective_model_window_seconds": 165.0,
                "host_candidate": receipt,
                "canonical_authority": {
                    "canonical_candidate_sha256": receipt[
                        "canonical_candidate_sha256"
                    ],
                    "source_sha256": hashlib.sha256(SOURCE.encode()).hexdigest(),
                    "product_facts_sha256": "7" * 64,
                    "authored_relation_set_sha256": "8" * 64,
                },
            },
            "semantic_compiler": {
                "version": "odylith.greenfield.authored-semantic-validation.v5",
                "status": "passed",
                "semantic_owner": "host_canonical_candidate",
                "post_candidate_receipt_semantic_calls": 0,
            },
        }
    }


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


def _profile_evidence() -> dict[str, object]:
    raw, receipt = _raw_and_receipt()
    return model_profile_evidence(
        STANDARD_PROFILE_ID,
        model_profile_environment(STANDARD_PROFILE_ID, {}),
        observed=_observed(receipt),
        stage_observation=_stage(receipt),
        raw_candidate=raw,
        expected_source=SOURCE,
    )


def _clarification_profile_evidence() -> dict[str, object]:
    _raw, _receipt = _raw_and_receipt()
    stage = _stage(_receipt)
    stage["host_invocations"] = 1
    stage["candidate_host_invocations"] = 0
    stage["proposal_command_invocations"] = 0
    stage["authority_gate_decision"] = "clarify"
    stage["stage"] = "authority-check"
    stage["response_kind"] = "clarification_required"
    stage["proposal_mode"] = "clarification_required"
    for field in (
        "host_request", "candidate_schema_sha256", "host_returncode",
        "host_stdout_bytes", "host_stderr_bytes", "raw_candidate_sha256",
        "host_output_sha256", "host_output_bytes", "candidate_temp_outside_repo",
        "proposal_returncode", "proposal_stdout_sha256", "proposal_stderr_sha256",
    ):
        stage.pop(field)
    return model_profile_evidence(
        STANDARD_PROFILE_ID,
        model_profile_environment(STANDARD_PROFILE_ID, {}),
        observed={},
        stage_observation=stage,
        raw_candidate={},
        expected_source=SOURCE,
    )


def test_retained_candidate_binds_raw_and_canonical_hashes() -> None:
    raw, receipt = _raw_and_receipt()

    assert retained_canonical_candidate_hash_issues(
        raw_candidate=raw,
        receipt=receipt,
        evidence_text=SOURCE,
    ) == ()

    tampered = deepcopy(raw)
    tampered["result"]["clarification"]["material_dimension"] = "product_view"
    issues = retained_canonical_candidate_hash_issues(
        raw_candidate=tampered,
        receipt=receipt,
        evidence_text=SOURCE,
    )
    assert "sealed raw candidate hash does not match retained host output" in issues
    assert (
        "sealed canonical candidate hash does not match deterministic projection"
        in issues
    )


def test_profile_evidence_proves_one_host_and_zero_post_receipt_calls() -> None:
    evidence = _profile_evidence()

    assert evidence["status"] == "passed", evidence["issues"]
    assert evidence["semantic_authority"] == "active_host_single_authority"
    assert evidence["sealed_request_roles"] == ["authority_gate", "host_candidate"]
    assert evidence["host_semantic_model_calls"] == 2
    assert evidence["runtime_semantic_model_calls_after_candidate_receipt"] == 0
    assert evidence["post_receipt_provider_invocations"] == 0
    summary = evidence["stage_observation_summary"]
    assert summary["retained_candidate_hash_summary"]["canonical_projection_verified"] is True
    assert "candidate_" + "review" not in json.dumps(evidence, sort_keys=True)


@pytest.mark.parametrize("clarification", (False, True))
@pytest.mark.parametrize(
    "field", ("model_window_seconds", "operational_timeout_seconds")
)
@pytest.mark.parametrize("invalid", (MISSING, True, "165", 164.0, 180.001))
def test_profile_evidence_rejects_unbound_host_window(
    clarification: bool, field: str, invalid: object,
) -> None:
    raw, receipt = _raw_and_receipt()
    if clarification:
        stage = deepcopy(_clarification_profile_evidence()["stage_observation"])
        observed = {}
        raw = {}
    else:
        stage = _stage(receipt)
        observed = _observed(receipt)
    _mutate_path(stage, (field,), invalid)

    evidence = model_profile_evidence(
        STANDARD_PROFILE_ID,
        model_profile_environment(STANDARD_PROFILE_ID, {}),
        observed=observed,
        stage_observation=stage,
        raw_candidate=raw,
        expected_source=SOURCE,
    )

    assert evidence["status"] == "failed"
    assert (
        f"retained host stage {field} does not match the assigned profile"
        in evidence["issues"]
    )
    if clarification:
        assert host_native_clarification_stage_observation_issues(
            STANDARD_PROFILE_ID,
            stage_observation=stage,
            expected_source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),
        )


def test_profile_evidence_rejects_post_receipt_provider_or_reviewer_fields() -> None:
    raw, receipt = _raw_and_receipt()
    stage = _stage(receipt)
    stage["post_receipt_provider_invocations"] = 1
    observed = _observed(receipt)
    observed["candidate_" + "review"] = {"status": "admitted"}

    evidence = model_profile_evidence(
        STANDARD_PROFILE_ID,
        model_profile_environment(STANDARD_PROFILE_ID, {}),
        observed=observed,
        stage_observation=stage,
        raw_candidate=raw,
        expected_source=SOURCE,
    )

    assert evidence["status"] == "failed"
    assert any("post_receipt_provider_invocations" in issue for issue in evidence["issues"])
    assert "sealed model observation has missing or unsupported fields" in evidence["issues"]


@pytest.mark.parametrize(
    ("location", "field"),
    (
        ("stage", "host_invocations"),
        ("stage", "contract_command_invocations"),
        ("stage", "proposal_command_invocations"),
        ("stage", "runtime_semantic_model_call_count"),
        ("stage", "post_receipt_provider_invocations"),
        ("observed", "runtime_semantic_model_call_count"),
    ),
)
@pytest.mark.parametrize("invalid", (False, True, 0.0, MISSING))
def test_profile_evidence_rejects_non_integer_call_counts(
    location: str,
    field: str,
    invalid: object,
) -> None:
    raw, receipt = _raw_and_receipt()
    stage = _stage(receipt)
    observed = _observed(receipt)
    target = stage if location == "stage" else observed
    if invalid is MISSING:
        target.pop(field)
    else:
        target[field] = invalid

    evidence = model_profile_evidence(
        STANDARD_PROFILE_ID,
        model_profile_environment(STANDARD_PROFILE_ID, {}),
        observed=observed,
        stage_observation=stage,
        raw_candidate=raw,
        expected_source=SOURCE,
    )

    assert evidence["status"] == "failed"


@pytest.mark.parametrize(
    "field",
    (
        "host_invocations",
        "runtime_semantic_model_call_count",
        "post_receipt_provider_invocations",
    ),
)
@pytest.mark.parametrize("invalid", (False, True, 0.0, MISSING))
def test_clarification_stage_rejects_non_integer_call_counts(
    field: str,
    invalid: object,
) -> None:
    _raw, receipt = _raw_and_receipt()
    stage = _stage(receipt)
    stage["response_kind"] = "clarification_required"
    stage["proposal_mode"] = "clarification_required"
    if invalid is MISSING:
        stage.pop(field)
    else:
        stage[field] = invalid

    issues = host_native_clarification_stage_observation_issues(
        STANDARD_PROFILE_ID,
        stage_observation=stage,
        expected_source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),
    )

    assert issues


def test_committed_result_binding_uses_canonical_authority_only() -> None:
    raw, receipt = _raw_and_receipt()
    create_payload = _create_payload(receipt)

    assert authored_model_result_binding_issues(
        stage_observation=_stage(receipt),
        raw_candidate=raw,
        create_payload=create_payload,
        expected_source=SOURCE,
    ) == ()

    create_payload["commit_manifest"]["semantic_compiler"][
        "post_candidate_receipt_semantic_calls"
    ] = 1
    assert "semantic compiler does not prove zero post-receipt semantic calls" in (
        authored_model_result_binding_issues(
            stage_observation=_stage(receipt),
            raw_candidate=raw,
            create_payload=create_payload,
            expected_source=SOURCE,
        )
    )


@pytest.mark.parametrize(
    "path",
    (
        ("commit_manifest", "model_authoring", "runtime_semantic_model_call_count"),
        (
            "commit_manifest",
            "semantic_compiler",
            "post_candidate_receipt_semantic_calls",
        ),
    ),
)
@pytest.mark.parametrize("invalid", (False, True, 0.0, MISSING))
def test_committed_result_binding_rejects_non_integer_call_counts(
    path: tuple[str, ...],
    invalid: object,
) -> None:
    raw, receipt = _raw_and_receipt()
    create_payload = _create_payload(receipt)
    _mutate_path(create_payload, path, invalid)

    issues = authored_model_result_binding_issues(
        stage_observation=_stage(receipt),
        raw_candidate=raw,
        create_payload=create_payload,
        expected_source=SOURCE,
    )

    assert issues


@pytest.mark.parametrize(
    "field",
    ("runtime_semantic_model_call_count", "post_receipt_provider_invocations"),
)
@pytest.mark.parametrize("invalid", (False, True, 0.0, MISSING))
def test_committed_result_binding_rejects_non_integer_stage_call_counts(
    field: str,
    invalid: object,
) -> None:
    raw, receipt = _raw_and_receipt()
    stage = _stage(receipt)
    if invalid is MISSING:
        stage.pop(field)
    else:
        stage[field] = invalid

    issues = authored_model_result_binding_issues(
        stage_observation=stage,
        raw_candidate=raw,
        create_payload=_create_payload(receipt),
        expected_source=SOURCE,
    )

    assert issues


def test_release_profile_summary_has_no_runtime_reviewer_profile() -> None:
    result = SimpleNamespace(
        name="clarification",
        status="passed",
        quality=SimpleNamespace(
            passed=True,
            score_basis="clarification_required_no_write_contract",
        ),
        proposal_seconds=12.0,
        evidence={
            "case": {
                "expectation": "clarification_required",
                "prompt_sha256": "9" * 64,
            },
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
            "model_profile": _clarification_profile_evidence(),
        },
    )

    proof = model_profile_release_proof((result,), require_complete=False)

    assert proof["status"] == "passed", proof["issues"]
    serialized = json.dumps(proof, sort_keys=True)
    assert "candidate_" + "review" not in serialized
    assert "reviewer" not in serialized
    profile = proof["profiles"][STANDARD_PROFILE_ID]
    assert profile["host_model"] == "gpt-6-astra"
    assert profile["runtime_semantic_model_calls_after_candidate_receipt"] == 0
