from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from greenfield_matrix_clarification import ClarificationExecution
from greenfield_matrix_clarification import clarification_contract_issues
from greenfield_matrix_clarification import run_expected_clarification
from greenfield_matrix_host_candidate import HOST_NATIVE_ARGV_ARGUMENT_COUNT
from greenfield_matrix_host_candidate import HOST_NATIVE_ARGV_SHAPE_SHA256
from greenfield_matrix_host_candidate import HOST_NATIVE_MATRIX_OBSERVATION_VERSION
from greenfield_model_profiles import STANDARD_PROFILE_ID


SOURCE = "Build a useful product."


def _stage() -> dict[str, object]:
    return {
        "version": HOST_NATIVE_MATRIX_OBSERVATION_VERSION,
        "response_kind": "clarification_required",
        "proposal_mode": "clarification_required",
        "source_sha256": hashlib.sha256(SOURCE.encode()).hexdigest(),
        "host_invocations": 1,
        "authority_gate_host_invocations": 1,
        "candidate_host_invocations": 0,
        "proposal_command_invocations": 0,
        "runtime_semantic_model_call_count": 0,
        "post_receipt_provider_invocations": 0,
        "authority_gate_request": {
            "version": "odylith.greenfield.host-argv-receipt.v1",
            "executable_sha256": "1" * 64,
            "argument_count": HOST_NATIVE_ARGV_ARGUMENT_COUNT,
            "model": "gpt-6-astra",
            "reasoning_effort": "medium",
            "output_schema_present": True,
            "argv_shape_sha256": HOST_NATIVE_ARGV_SHAPE_SHA256,
        },
    }


def _execution() -> ClarificationExecution:
    return ClarificationExecution(
        payload={
            "mode": "clarification_required",
            "clarification": {
                "question": (
                    "Who uses this product first, what complete task do they finish, "
                    "and what result do they see?"
                ),
                "required_fields": ["first_path"],
            },
        },
        returncode=0,
        seconds=1.0,
        before_record_count=0,
        after_record_count=0,
        changed_records=(),
        staged_transaction_present=False,
        write_audit_active=True,
    )


def test_clarification_requires_one_host_authority_and_zero_runtime_calls() -> None:
    issues = clarification_contract_issues(
        _execution(),
        expected_fields=("first_path",),
        expected_model_profile_id=STANDARD_PROFILE_ID,
        stage_observation=_stage(),
        expected_source=SOURCE,
    )

    assert issues == ()


def test_gate_only_clarification_accepts_equivalent_question_not_exact_sentence() -> None:
    execution = _execution()
    clarification = dict(execution.payload["clarification"])
    clarification["question"] = (
        "Who is this product for, which task should they complete, "
        "and what observable outcome should it produce?"
    )
    execution = replace(execution, payload={"mode": "clarification_required", "clarification": clarification})

    assert clarification_contract_issues(
        execution,
        expected_fields=("first_path",),
        expected_question=(
            "Who uses this product first, what complete task do they finish, "
            "and what result do they see?"
        ),
        expected_model_profile_id=STANDARD_PROFILE_ID,
        stage_observation=_stage(),
        expected_source=SOURCE,
    ) == ()


def test_gate_only_clarification_rejects_retired_candidate_consistency_shape() -> None:
    execution = _execution()
    clarification = dict(execution.payload["clarification"])
    clarification["consistency_assessment"] = {"status": "material_ambiguity"}
    execution = replace(execution, payload={"mode": "clarification_required", "clarification": clarification})

    issues = clarification_contract_issues(
        execution,
        expected_fields=("first_path",),
        expected_model_profile_id=STANDARD_PROFILE_ID,
        stage_observation=_stage(),
        expected_source=SOURCE,
    )

    assert "host-native clarification payload must contain only question and required_fields" in issues


def test_clarification_rejects_runtime_reviewer_style_outcome() -> None:
    stage = _stage()
    stage["response_kind"] = "authored"

    issues = clarification_contract_issues(
        _execution(),
        expected_fields=("first_path",),
        expected_model_profile_id=STANDARD_PROFILE_ID,
        stage_observation=stage,
        expected_source=SOURCE,
    )

    assert "retained host clarification response kind is invalid" in issues


def test_clarification_rejects_post_receipt_provider_call() -> None:
    stage = _stage()
    stage["post_receipt_provider_invocations"] = 1

    issues = clarification_contract_issues(
        _execution(),
        expected_fields=("first_path",),
        expected_model_profile_id=STANDARD_PROFILE_ID,
        stage_observation=stage,
        expected_source=SOURCE,
    )

    assert "retained host clarification used a post-receipt provider call" in issues


def test_run_expected_clarification_detects_changed_records(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    governed = repo / "odylith/radar/source/changed.md"

    def invoke() -> SimpleNamespace:
        governed.parent.mkdir(parents=True)
        governed.write_text("changed\n", encoding="utf-8")
        return SimpleNamespace(
            returncode=0,
            stdout='{"mode":"clarification_required","clarification":{}}',
            stderr="",
        )

    execution = run_expected_clarification(
        repo_root=repo,
        invoke=invoke,
        parse_payload=lambda _value: {
            "mode": "clarification_required",
            "clarification": {},
        },
    )

    assert execution.changed_records == ("odylith/radar/source/changed.md",)
