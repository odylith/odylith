from __future__ import annotations

from copy import deepcopy
import hashlib
import json
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
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    authored_response,
    host_candidate_response,
    synthetic_source_duty_receipt,
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
    contract = get_greenfield_model_profile(profile_id)
    observed = {}
    stage = {
        "version": HOST_NATIVE_MATRIX_OBSERVATION_VERSION,
        "status": "passed",
        "host_invocations": 1,
        "authority_gate_host_invocations": 1,
        "source_ledger_host_invocations": 0,
        "source_duty_verifier_host_invocations": 0,
        "candidate_host_invocations": 0,
        "contract_command_invocations": 1,
        "authority_check_command_invocations": 1,
        "source_ledger_check_command_invocations": 0,
        "proposal_command_invocations": 0,
        "runtime_semantic_model_call_count": 0,
        "post_receipt_provider_invocations": 0,
        "model_profile_id": profile_id,
        "model_window_seconds": contract.model_timeout_seconds,
        "operational_timeout_seconds": contract.operational_timeout_seconds,
        "source_ledger_diagnostic_cap_seconds": 300.0,
        "source_duty_verifier_diagnostic_cap_seconds": 120.0,
        "whole_journey_diagnostic_cap_seconds": 660.0,
        "candidate_completion_reserve_seconds": 15.0,
        "whole_journey_bound_status": "diagnostic_unqualified",
        "whole_journey_elapsed_scope": "through_observer_return_before_final_snapshot_serialization",
        "whole_journey_deadline_status": "within",
        "authority_gate_request": {
            "version": "odylith.greenfield.host-argv-receipt.v1",
            "executable_sha256": "1" * 64,
            "argument_count": HOST_NATIVE_ARGV_ARGUMENT_COUNT,
            "model": contract.model,
            "reasoning_effort": contract.reasoning_effort,
            "output_schema_present": True,
            "argv_shape_sha256": HOST_NATIVE_ARGV_SHAPE_SHA256,
        },
        "candidate_temp_cleaned": True,
        "authority_gate_temp_cleaned": True,
        "source_ledger_temp_cleaned": True,
        "source_duty_decision_temp_cleaned": True,
        "host_workspace_cleaned": True,
        "stage": "authority-check",
        "contract_returncode": 0,
        "contract_sha256": "2" * 64,
        "source_sha256": hashlib.sha256(SOURCE.encode()).hexdigest(),
        "authority_gate_schema_sha256": "3" * 64,
        "authority_gate_returncode": 0,
        "authority_gate_output_sha256": "4" * 64,
        "authority_gate_output_bytes": 200,
        "authority_gate_decision": "clarify",
        "authority_gate_temp_outside_repo": True,
        "authority_check_returncode": 0,
        "authority_check_stdout_sha256": "5" * 64,
        "authority_check_stderr_sha256": "6" * 64,
        "response_kind": "clarification_required",
        "proposal_mode": "clarification_required",
        "elapsed_seconds": 18.02,
        "proposal_phase_elapsed_seconds": 18.02,
        "whole_journey_seconds": 18.02,
    }
    return model_profile_evidence(
        profile_id,
        model_profile_environment(profile_id, {}),
        observed=observed,
        stage_observation=stage,
        raw_candidate={},
        expected_source=SOURCE,
    )


def _authored_profile_evidence(profile_id: str = STANDARD_PROFILE_ID) -> dict[str, object]:
    event = "Mara stores one draft"
    intent = {
        "title": "Draft Desk",
        "product_story": "Draft Desk supports draft review",
        "state_object": "one draft",
        "first_path": event,
        "proof_boundary": "one draft",
        "problem": "Scattered drafts delay reviews",
        "customer": "Mara",
        "opportunity": "A shared draft reduces rework",
        "product_view": "Draft Desk keeps a review trail",
        "human_actors": ["Mara"],
        "external_systems": [],
        "internal_systems": [],
        "component_responsibilities": [],
        "assumptions": [],
        "ambiguities": [],
        "success_metrics": [],
        "evidence_requirements": [],
        "operational_constraints": [],
        "non_goals": [],
    }
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if row
    )
    response = authored_response(
        intent,
        evidence_text=source,
        first_path_relations=[{
            "actor_kind": "human",
            "actor_fact_quote": "Mara",
            "owner_system_quote": "",
            "event_quote": event,
            "action_verb_quote": "stores",
            "target_quote": "one draft",
            "visible_result_quote": "one draft",
        }],
    )
    raw_candidate = host_candidate_response(response, evidence_text=source)
    source_duty_receipt = synthetic_source_duty_receipt(
        raw_candidate, evidence_text=source
    )
    _candidate, receipt = admit_greenfield_host_candidate(
        raw_candidate, evidence_text=source,
        source_duty_receipt=source_duty_receipt, clock=lambda: 1.0
    )
    evidence = _profile_evidence(profile_id)
    stage = evidence["stage_observation"]
    stage["host_invocations"] = 4
    stage["source_ledger_host_invocations"] = 1
    stage["source_duty_verifier_host_invocations"] = 1
    stage["source_ledger_check_command_invocations"] = 2
    stage["candidate_host_invocations"] = 1
    stage["proposal_command_invocations"] = 1
    stage["authority_gate_decision"] = "admit"
    stage["stage"] = "propose"
    stage["host_request"] = deepcopy(stage["authority_gate_request"])
    stage["source_ledger_request"] = deepcopy(stage["authority_gate_request"])
    stage["source_duty_verifier_request"] = deepcopy(stage["authority_gate_request"])
    stage["source_ledger_schema_sha256"] = "b" * 64
    stage["source_ledger_returncode"] = 0
    stage["source_ledger_output_sha256"] = "c" * 64
    stage["source_ledger_output_bytes"] = 300
    stage["source_ledger_temp_outside_repo"] = True
    stage["source_ledger_preflight_returncode"] = 0
    stage["source_ledger_preflight_stdout_sha256"] = "b" * 64
    stage["source_ledger_preflight_mode"] = "source_duty_preflight"
    stage["source_duty_decision_schema_sha256"] = "c" * 64
    stage["source_duty_verifier_returncode"] = 0
    stage["source_duty_decision_output_sha256"] = "d" * 64
    stage["source_duty_decision_output_bytes"] = 300
    stage["source_completeness_verdict"] = "yes"
    stage["source_completeness_omission_count"] = 0
    stage["source_duty_decision_temp_outside_repo"] = True
    stage["source_ledger_check_returncode"] = 0
    stage["source_ledger_check_stdout_sha256"] = "d" * 64
    stage["source_ledger_check_mode"] = "source_duty_admitted"
    stage["source_ledger_elapsed_seconds"] = 20.0
    stage["source_duty_verifier_elapsed_seconds"] = 10.0
    stage["source_ledger_sha256"] = receipt["source_duty_ledger_sha256"]
    stage["source_duty_decision_set_sha256"] = receipt["source_duty_decision_set_sha256"]
    stage["source_duty_verifier_task_sha256"] = receipt["source_duty_verifier_task_sha256"]
    stage["whole_journey_seconds"] = 48.02
    stage["candidate_schema_sha256"] = "7" * 64
    stage["host_returncode"] = 0
    stage["host_stdout_bytes"] = 500
    stage["host_stderr_bytes"] = 0
    stage["host_output_sha256"] = "8" * 64
    stage["host_output_bytes"] = 500
    stage["candidate_temp_outside_repo"] = True
    stage["proposal_returncode"] = 0
    stage["proposal_stdout_sha256"] = "9" * 64
    stage["proposal_stderr_sha256"] = "a" * 64
    stage["response_kind"] = "authored"
    stage["proposal_mode"] = "product_create_transaction"
    stage["source_sha256"] = hashlib.sha256(source.encode("utf-8")).hexdigest()
    stage["raw_candidate_sha256"] = receipt["raw_candidate_sha256"]
    return model_profile_evidence(
        profile_id,
        model_profile_environment(profile_id, {}),
        observed={
            "origin": "host_native",
            "host_candidate": receipt,
            "runtime_semantic_model_call_count": 0,
        },
        stage_observation=stage,
        raw_candidate=raw_candidate,
        source_duty_receipt=source_duty_receipt,
        expected_source=source,
    )


def _result(
    *,
    profile_evidence: dict[str, object],
    expectation: str,
) -> SimpleNamespace:
    profile_evidence = deepcopy(profile_evidence)
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


def test_complete_release_profile_requires_public_whole_journey_bound() -> None:
    standard = _result(
        profile_evidence=_authored_profile_evidence(STANDARD_PROFILE_ID),
        expectation="transaction_committed",
    )
    rescue = _result(
        profile_evidence=_profile_evidence(RESCUE_PROFILE_ID),
        expectation="clarification_required",
    )
    proof = model_profile_release_proof((standard, rescue), require_complete=True)
    assert proof["status"] == "failed"
    assert any("whole-journey bound" in issue for issue in proof["issues"])
    assert proof["lower_capability_scope"]["status"] == "passed"
    assert proof["lower_capability_scope"]["role"] == "authority_gate"


def test_complete_release_profile_fails_without_rescue_control() -> None:
    standard = _result(
        profile_evidence=_authored_profile_evidence(STANDARD_PROFILE_ID),
        expectation="transaction_committed",
    )
    proof = model_profile_release_proof((standard,), require_complete=True)
    assert proof["status"] == "failed"
    assert any("clarification/no-write case" in issue for issue in proof["issues"])


def test_lower_capability_positive_result_cannot_qualify_release_success() -> None:
    rescue = _result(
        profile_evidence=_authored_profile_evidence(RESCUE_PROFILE_ID),
        expectation="transaction_committed",
    )
    proof = model_profile_release_proof((rescue,), require_complete=False)
    assert proof["status"] == "failed"
    assert any("must clarify without writing" in issue for issue in proof["issues"])


def test_deep_profile_cannot_qualify_release_success() -> None:
    deep = _result(
        profile_evidence=_authored_profile_evidence(DEEP_PROFILE_ID),
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
    evidence = deepcopy(_authored_profile_evidence())
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


def test_clarification_rejects_fabricated_sealed_candidate_receipt() -> None:
    evidence = _profile_evidence()
    evidence["observed"] = _authored_profile_evidence()["observed"]
    proof = model_profile_release_proof(
        (_result(profile_evidence=evidence, expectation="clarification_required"),),
        require_complete=False,
    )
    assert proof["status"] == "failed"


def test_clarification_rejects_retained_candidate_hash_mismatch() -> None:
    evidence = _profile_evidence()
    evidence["stage_observation"]["raw_candidate_sha256"] = "0" * 64
    proof = model_profile_release_proof(
        (_result(profile_evidence=evidence, expectation="clarification_required"),),
        require_complete=False,
    )
    assert proof["status"] == "failed"


@pytest.mark.parametrize(
    "elapsed",
    (315.0, 315.001, None, True, "18.0", 0.0, -1.0, float("nan"), float("inf")),
)
def test_aggregate_profile_rejects_expired_or_invalid_elapsed(elapsed: object) -> None:
    evidence = _profile_evidence()
    evidence["stage_observation"]["elapsed_seconds"] = elapsed
    proof = model_profile_release_proof(
        (_result(profile_evidence=evidence, expectation="clarification_required"),),
        require_complete=False,
    )
    assert proof["status"] == "failed"
