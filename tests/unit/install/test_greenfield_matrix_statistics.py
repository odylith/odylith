from __future__ import annotations

from dataclasses import replace
import hashlib
import sys

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_statistics import outcome_statistics
from greenfield_matrix_statistics import release_slice_minimum_sample_contract
from greenfield_matrix_statistics import release_slice_minimum_sample_contract_issues
from greenfield_matrix_statistics import release_statistical_confidence_contract
from greenfield_matrix_statistics import release_statistical_confidence_contract_issues
from greenfield_matrix_statistics import wilson_interval
from greenfield_matrix_clarification import clarification_quality_verdict
from greenfield_matrix_host_candidate import HOST_NATIVE_ARGV_ARGUMENT_COUNT
from greenfield_matrix_host_candidate import HOST_NATIVE_ARGV_SHAPE_SHA256
from greenfield_matrix_types import GreenfieldArtifactCounts
from greenfield_matrix_types import GreenfieldMatrixResult
from greenfield_matrix_types import GreenfieldQualityVerdict
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from greenfield_preconfirm_matrix_cases import case_evidence
from greenfield_model_profiles import model_profile_environment
from greenfield_model_profiles import model_profile_evidence
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    combined_prompt_evidence_source,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    DEEP_PROFILE_ID,
    RESCUE_PROFILE_ID,
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_CONTRACT_VERSION,
    HOST_CANDIDATE_RECEIPT_VERSION,
    admit_greenfield_host_candidate,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import (
    HOST_CANDIDATE_FORMAT_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    greenfield_operating_envelope_receipt,
)


def _case(case_id: str, *, stressor: str, input_style: str = "direct_request") -> GreenfieldMatrixCase:
    return GreenfieldMatrixCase(
        case_id=case_id,
        name=case_id,
        prompt=f"Build {case_id}.",
        required_terms=(case_id,),
        leakage_terms=(case_id,),
        stressors=(stressor,),
        tags=("complexity:medium", "host-profile:codex"),
        input_style=input_style,
    )


def _result(case: GreenfieldMatrixCase, *, passed: bool) -> GreenfieldMatrixResult:
    verdict = GreenfieldQualityVerdict(
        passed=passed,
        issues=() if passed else ("failed",),
        lenses={},
        scores={},
        score=10 if passed else 0,
        score_explanation=(),
    )
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed" if passed else "failed",
        create_seconds=1.0,
        counts=GreenfieldArtifactCounts(),
        quality=verdict,
        evidence={"case": {"id": case.case_id}},
    )


def test_wilson_interval_is_bounded_and_truthful_for_small_perfect_samples() -> None:
    lower, upper = wilson_interval(10, 10)

    assert 0.72 < lower < 1.0
    assert upper == 1.0
    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_outcome_statistics_reports_sample_interval_and_worst_slice() -> None:
    first = _case("case-one", stressor="dense")
    second = _case("case-two", stressor="dense")
    third = _case("case-three", stressor="sparse", input_style="markdown")

    report = outcome_statistics(
        cases=(first, second, third),
        results=(_result(first, passed=True), _result(second, passed=False), _result(third, passed=True)),
    )

    assert report["status"] == "complete"
    assert report["sample_count"] == 3
    assert report["point_estimate"] == 0.666667
    assert report["confidence_interval_95"]["method"] == "wilson"
    assert report["worst_slice"]["point_estimate"] == 0.5
    assert any(
        row["dimension"] == "stressor" and row["value"] == "dense" and row["point_estimate"] == 0.5
        for row in report["slices"]
    )


def test_outcome_statistics_cannot_hide_a_missing_case() -> None:
    case = _case("case-one", stressor="dense")

    report = outcome_statistics(cases=(case, replace(case, case_id="case-two")), results=(_result(case, passed=True),))

    assert report["status"] == "incomplete"
    assert report["missing_case_ids"] == ["case-two"]


def test_release_statistics_use_sealed_slices_instead_of_spoofable_tags() -> None:
    cases, results = _complete_release_matrix()

    report = outcome_statistics(cases=cases, results=results, release=True)

    assert report["status"] == "passed"
    assert report["acceptance_passed"] is True
    assert report["confidence_passed"] is True
    assert report["release_evidence_issues"] == []
    assert report["release_coverage_issues"] == []
    assert report["release_minimum_samples"] == release_slice_minimum_sample_contract()
    assert {
        (row["dimension"], row["value"])
        for row in report["slices"]
        if row["dimension"] in {"complexity_band", "evidence_format", "model_profile"}
    } >= {
        ("complexity_band", "bounded"),
        ("complexity_band", "moderate"),
        ("complexity_band", "high"),
        ("evidence_format", "operator_prompt"),
        ("evidence_format", "operator_prompt_with_edit_evidence"),
        ("model_profile", STANDARD_PROFILE_ID),
    }
    assert not any(
        row["value"] in {"spoofed-band", "spoofed-profile"}
        for row in report["slices"]
    )


def test_release_statistics_count_a_verified_no_write_clarification_without_a_sealed_package() -> None:
    question = "Which result must the operator see first?"
    case = replace(
        _case("clarification-case", stressor="material-ambiguity"),
        expectation="clarification_required",
        expected_clarification_field="first_path",
        expected_clarification_question=question,
    )
    result = _host_native_clarification_result(case)

    report = outcome_statistics(cases=(case,), results=(result,), release=True)

    assert report["release_evidence_issues"] == []
    assert {
        (row["dimension"], row["value"])
        for row in report["slices"]
    } >= {
        ("complexity_band", "bounded"),
        ("evidence_format", "operator_prompt"),
        ("model_profile", STANDARD_PROFILE_ID),
    }


@pytest.mark.parametrize(
    "mutation",
    (
        "stage_status",
        "stage_model_call_count",
        "frozen_source_hash",
        "frozen_clarification",
    ),
)
def test_release_statistics_reject_a_clarification_with_broken_host_custody(
    mutation: str,
) -> None:
    question = "Which result must the operator see first?"
    case = replace(
        _case("broken-clarification", stressor="material-ambiguity"),
        expectation="clarification_required",
        expected_clarification_field="first_path",
        expected_clarification_question=question,
    )
    result = _host_native_clarification_result(case)
    model_profile = dict(result.evidence["model_profile"])
    if mutation == "frozen_clarification":
        observed_case = dict(result.evidence["case"])
        observed_case["expected_clarification"] = {
            "field": "proof_boundary",
            "question": case.expected_clarification_question,
        }
        result = replace(
            result,
            evidence={**result.evidence, "case": observed_case},
        )
    elif mutation == "stage_status":
        model_profile["stage_observation"] = {
            **model_profile["stage_observation"],
            "status": "failed",
        }
    else:
        if mutation == "stage_model_call_count":
            model_profile["stage_observation"] = {
                **model_profile["stage_observation"],
                "host_invocations": 2,
            }
        else:
            model_profile["expected_source_sha256"] = "9" * 64
    if mutation != "frozen_clarification":
        result = replace(
            result,
            evidence={**result.evidence, "model_profile": model_profile},
        )

    report = outcome_statistics(cases=(case,), results=(result,), release=True)

    assert report["release_evidence_issues"]
    assert report["status"] == "failed"


@pytest.mark.parametrize(
    ("dimension", "missing_value"),
    (
        ("complexity_band", "high"),
        ("evidence_format", "operator_prompt_with_edit_evidence"),
    ),
)
def test_each_published_release_axis_fails_independently_when_coverage_is_missing(
    dimension: str,
    missing_value: str,
) -> None:
    cases, results = _complete_release_matrix()
    selected_pairs = tuple(
        (case, result)
        for case, result in zip(cases, results, strict=True)
        if _release_slice_value(case, result, dimension) != missing_value
    )

    report = outcome_statistics(
        cases=tuple(case for case, _result_row in selected_pairs),
        results=tuple(result for _case_row, result in selected_pairs),
        release=True,
    )

    assert report["status"] == "failed"
    assert report["release_contract_issues"] == []
    assert report["release_evidence_issues"] == []
    assert report["release_coverage_issues"] == [
        f"release evidence lacks {dimension} coverage: {missing_value}"
    ]


def test_release_statistics_reject_an_observed_slice_below_the_frozen_sample_minimum() -> None:
    cases, results = _complete_release_matrix()
    selected: list[tuple[GreenfieldMatrixCase, GreenfieldMatrixResult]] = []
    retained_high = 0
    for case, result in zip(cases, results, strict=True):
        if _release_slice_value(case, result, "complexity_band") == "high":
            if retained_high >= 3:
                continue
            retained_high += 1
        selected.append((case, result))

    report = outcome_statistics(
        cases=tuple(case for case, _result_row in selected),
        results=tuple(result for _case_row, result in selected),
        release=True,
    )

    assert report["status"] == "failed"
    assert report["release_coverage_issues"] == [
        "release evidence has 3 sample(s) for complexity_band `high`; requires at least 4"
    ]


def test_release_slice_minimum_contract_rejects_narrowed_counts() -> None:
    contract = release_slice_minimum_sample_contract()
    contract["complexity_band"]["high"] -= 1

    assert release_slice_minimum_sample_contract_issues(contract) == [
        "release slice minimum samples must match the published contract"
    ]


@pytest.mark.parametrize(
    ("field", "threshold", "expected_evidence"),
    (
        ("overall_case_success", 0.52, "perfect evidence reaches 0.510109"),
        (
            "unnecessary_question_rate_ceiling",
            0.48,
            "zero failures reach 0.489891",
        ),
    ),
)
def test_confidence_preflight_rejects_thresholds_impossible_at_declared_minima(
    field: str,
    threshold: float,
    expected_evidence: str,
) -> None:
    contract = release_statistical_confidence_contract()
    contract[field] = threshold

    issues = release_statistical_confidence_contract_issues(
        contract,
        minimum_samples=release_slice_minimum_sample_contract(),
    )

    assert any(field in issue and expected_evidence in issue for issue in issues)


def test_release_statistics_reject_unknown_or_narrowed_slice_contracts() -> None:
    cases, results = _complete_release_matrix()
    narrowed = {
        "complexity_band": ("bounded", "moderate"),
        "evidence_format": ("operator_prompt", "operator_prompt_with_edit_evidence"),
        "model_profile": (STANDARD_PROFILE_ID,),
        "invented_dimension": ("invented",),
    }

    report = outcome_statistics(
        cases=cases,
        results=results,
        release=True,
        required_slices=narrowed,
    )

    assert report["status"] == "failed"
    assert report["release_contract_issues"] == [
        "release slice contract must declare only every published slice dimension"
    ]


def test_release_statistics_marks_a_failed_slice_even_when_coverage_is_complete() -> None:
    cases, results = _complete_release_matrix()
    failed = replace(
        results[4],
        status="failed",
        quality=GreenfieldQualityVerdict(
            passed=False,
            issues=("failed",),
            lenses={},
            scores={},
            score=0,
            score_explanation=(),
        ),
    )
    results = (*results[:4], failed, *results[5:])

    report = outcome_statistics(cases=cases, results=results, release=True)

    assert report["status"] == "failed"
    assert report["release_coverage_issues"] == []
    assert any(
        row["dimension"] == "complexity_band"
        and row["value"] == "moderate"
        and row["failed_count"] == 1
        for row in report["failing_release_slices"]
    )


def _complete_release_matrix() -> tuple[
    tuple[GreenfieldMatrixCase, ...],
    tuple[GreenfieldMatrixResult, ...],
]:
    base_specifications = (
        ("bounded-operator", "bounded", False, STANDARD_PROFILE_ID),
        ("bounded-edit", "bounded", True, STANDARD_PROFILE_ID),
        ("bounded-operator-deep", "bounded", False, STANDARD_PROFILE_ID),
        ("bounded-edit-standard", "bounded", True, STANDARD_PROFILE_ID),
        ("moderate-operator", "moderate", False, STANDARD_PROFILE_ID),
        ("moderate-edit", "moderate", True, STANDARD_PROFILE_ID),
        ("moderate-operator-standard", "moderate", False, STANDARD_PROFILE_ID),
        ("moderate-edit-rescue", "moderate", True, STANDARD_PROFILE_ID),
        ("high-operator", "high", False, STANDARD_PROFILE_ID),
        ("high-edit", "high", True, STANDARD_PROFILE_ID),
        ("high-operator-rescue", "high", False, STANDARD_PROFILE_ID),
        ("high-edit-deep", "high", True, STANDARD_PROFILE_ID),
    )
    specifications = tuple(
        (f"{case_id}-{cycle}", band, edit, profile)
        for cycle in ("a", "b")
        for case_id, band, edit, profile in base_specifications
    )
    cases = tuple(
        _release_case(case_id, edit=edit)
        for case_id, _band, edit, _profile in specifications
    )
    results = tuple(
        _release_result(case, band=band, profile_id=profile)
        for case, (_case_id, band, _edit, profile) in zip(cases, specifications, strict=True)
    )
    return cases, results


def _host_native_clarification_result(
    case: GreenfieldMatrixCase,
) -> GreenfieldMatrixResult:
    source = combined_prompt_evidence_source(
        prompt=case.prompt,
        edit_evidence=case.confirmed_intent_markdown,
    )
    profile = get_greenfield_model_profile(STANDARD_PROFILE_ID)
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
        evidence_text=source,
        clock=lambda: 1.0,
    )
    stage = {
        "version": "odylith.greenfield.host-native-matrix-observation.v5",
        "status": "passed",
        "host_invocations": 1,
        "contract_command_invocations": 1,
        "proposal_command_invocations": 1,
        "runtime_semantic_model_call_count": 0,
        "post_receipt_provider_invocations": 0,
        "model_profile_id": STANDARD_PROFILE_ID,
        "host_request": {
            "version": "odylith.greenfield.host-argv-receipt.v1",
            "executable_sha256": "7" * 64,
            "argument_count": HOST_NATIVE_ARGV_ARGUMENT_COUNT,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
            "output_schema_present": True,
            "argv_shape_sha256": HOST_NATIVE_ARGV_SHAPE_SHA256,
        },
        "candidate_temp_cleaned": True,
        "host_workspace_cleaned": True,
        "stage": "propose",
        "contract_returncode": 0,
        "contract_sha256": "1" * 64,
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "candidate_schema_sha256": "2" * 64,
        "host_returncode": 0,
        "host_stdout_bytes": 200,
        "host_stderr_bytes": 0,
        "response_kind": "clarification_required",
        "raw_candidate_sha256": receipt["raw_candidate_sha256"],
        "host_output_sha256": "4" * 64,
        "host_output_bytes": 200,
        "candidate_temp_outside_repo": True,
        "proposal_returncode": 0,
        "proposal_stdout_sha256": "5" * 64,
        "proposal_stderr_sha256": "6" * 64,
        "proposal_mode": "clarification_required",
        "elapsed_seconds": 18.02,
    }
    profile_evidence = model_profile_evidence(
        STANDARD_PROFILE_ID,
        model_profile_environment(STANDARD_PROFILE_ID, {}),
        observed={},
        stage_observation=stage,
        raw_candidate=raw_candidate,
        expected_source=source,
    )
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed",
        create_seconds=18.02,
        proposal_seconds=18.02,
        counts=GreenfieldArtifactCounts(),
        quality=clarification_quality_verdict(()),
        evidence={
            "case": case_evidence(case),
            "clarification": {
                "mode": "clarification_required",
                "question": case.expected_clarification_question,
                "required_fields": ["first_path"],
                "returncode": 0,
            },
            "no_write": {
                "before_record_count": 0,
                "after_record_count": 0,
                "staged_transaction_present": False,
                "changed_records": [],
                "write_audit_active": True,
                "write_attempts": [],
                "write_audit_error": "",
            },
            "model_profile": profile_evidence,
        },
    )


def _release_slice_value(
    case: GreenfieldMatrixCase,
    result: GreenfieldMatrixResult,
    dimension: str,
) -> str:
    if dimension == "evidence_format":
        return (
            "operator_prompt_with_edit_evidence"
            if case.confirmed_intent_markdown
            else "operator_prompt"
        )
    if dimension == "model_profile":
        return str(result.evidence["model_profile"]["profile_id"])
    envelope = result.evidence["preconfirm_dry_run"]["semantic_snapshot"]["operating_envelope"]
    return str(envelope["complexity"]["band"])


def _release_case(case_id: str, *, edit: bool) -> GreenfieldMatrixCase:
    return GreenfieldMatrixCase(
        case_id=case_id,
        name=case_id,
        prompt=f"Operator records one governed result for {case_id}.",
        confirmed_intent_markdown=(
            "Keep the governed result visible for review."
            if edit
            else ""
        ),
        required_terms=(case_id,),
        tags=("complexity:spoofed-band", "model-profile:spoofed-profile"),
        input_style="direct_request",
    )


def _release_result(
    case: GreenfieldMatrixCase,
    *,
    band: str,
    profile_id: str,
) -> GreenfieldMatrixResult:
    facts = _facts_for_band(case, band=band)
    evidence_source = combined_prompt_evidence_source(
        prompt=case.prompt,
        edit_evidence=case.confirmed_intent_markdown,
    )
    envelope = greenfield_operating_envelope_receipt(
        facts=facts,
        source_format=(
            "operator_prompt_with_edit_evidence"
            if case.confirmed_intent_markdown
            else "operator_prompt"
        ),
        source_size_bytes=len(evidence_source.encode("utf-8")),
        source_document_count=2 if case.confirmed_intent_markdown else 1,
        model_authoring=_model_authoring_observations(profile_id),
    )
    assert envelope["status"] == "supported"
    assert envelope["complexity"]["band"] == band
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed",
        create_seconds=1.0,
        counts=GreenfieldArtifactCounts(),
        quality=GreenfieldQualityVerdict(True, (), {}, {}, 10, ()),
        evidence={
            "case": {"id": case.case_id},
            "preconfirm_dry_run": {
                "semantic_snapshot": {"operating_envelope": envelope},
            },
            "model_profile": {
                "profile_id": profile_id,
                "status": "passed",
                "issues": [],
            },
        },
    )


def _model_authoring_observations(profile_id: str) -> dict[str, object]:
    del profile_id
    return {
        "origin": "host_native",
        "host_candidate": {
            "version": HOST_CANDIDATE_RECEIPT_VERSION,
            "contract_version": HOST_CANDIDATE_CONTRACT_VERSION,
            "canonical_version": GREENFIELD_INTENT_AUTHORING_VERSION,
            "source_sha256": "a" * 64,
            "raw_candidate_sha256": "b" * 64,
            "canonical_candidate_sha256": "c" * 64,
        },
        "runtime_semantic_model_call_count": 0,
    }


def _facts_for_band(case: GreenfieldMatrixCase, *, band: str) -> dict[str, object]:
    facts: dict[str, object] = {
        "state_object": "One governed result",
        "first_path": case.prompt,
        "human_actors": ["Operator"],
    }
    if band == "moderate":
        facts["human_actors"] = [f"Actor {index}" for index in range(5)]
        facts["operational_constraints"] = [f"Boundary {index}" for index in range(3)]
    elif band == "high":
        facts["human_actors"] = [f"Actor {index}" for index in range(17)]
        facts["internal_systems"] = [f"System {index}" for index in range(17)]
        facts["ambiguities"] = [f"Ambiguity {index}" for index in range(9)]
        facts["operational_constraints"] = [f"Boundary {index}" for index in range(9)]
    return facts
