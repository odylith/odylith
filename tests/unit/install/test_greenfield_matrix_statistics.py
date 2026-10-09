from __future__ import annotations

from dataclasses import replace
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT
from tests.greenfield_model_profile_test_support import production_stage_observation


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_statistics import outcome_statistics
from greenfield_matrix_statistics import release_slice_minimum_sample_contract
from greenfield_matrix_statistics import release_slice_minimum_sample_contract_issues
from greenfield_matrix_statistics import release_statistical_confidence_contract
from greenfield_matrix_statistics import release_statistical_confidence_contract_issues
from greenfield_matrix_statistics import wilson_interval
import greenfield_matrix_statistics as statistics
from greenfield_matrix_clarification import clarification_quality_verdict
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
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_CONTRACT_VERSION,
    HOST_CANDIDATE_RECEIPT_VERSION,
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

    assert report["status"] == "failed"
    assert report["acceptance_passed"] is True
    assert report["confidence_passed"] is True
    assert report["release_evidence_issues"] == []
    assert report["release_coverage_issues"] == [
        "release evidence lacks evidence_format coverage: operator_prompt_with_edit_evidence"
    ]
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
        ("model_profile", STANDARD_PROFILE_ID),
    }
    assert not any(
        row["value"] in {"spoofed-band", "spoofed-profile"}
        for row in report["slices"]
    )
    assert not any(
        row["dimension"] == "evidence_format" and row["value"] == "operator_prompt_with_edit_evidence"
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
    assert set(report["release_coverage_issues"]) == {
        f"release evidence lacks {dimension} coverage: {missing_value}",
        "release evidence lacks evidence_format coverage: operator_prompt_with_edit_evidence",
    }


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
    assert set(report["release_coverage_issues"]) == {
        "release evidence has 3 sample(s) for complexity_band `high`; requires at least 4",
        "release evidence lacks evidence_format coverage: operator_prompt_with_edit_evidence",
    }


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


def test_release_statistics_marks_a_failed_slice_alongside_missing_edit_coverage() -> None:
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
    assert report["release_coverage_issues"] == [
        "release evidence lacks evidence_format coverage: operator_prompt_with_edit_evidence"
    ]
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
        prompt=case.initial_prompt,
        edit_evidence="",
    )
    stage = production_stage_observation(
        STANDARD_PROFILE_ID, response_kind="clarification_required",
    )
    stage["source_sha256"] = hashlib.sha256(source.encode("utf-8")).hexdigest()
    stage["elapsed_seconds"] = 18.02
    stage["proposal_phase_elapsed_seconds"] = 18.02
    stage["whole_journey_seconds"] = 18.02
    profile_evidence = model_profile_evidence(
        STANDARD_PROFILE_ID,
        model_profile_environment(STANDARD_PROFILE_ID, {}),
        observed={},
        stage_observation=stage,
        raw_candidate={},
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
        return "operator_prompt"
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
        prompt=case.initial_prompt,
        edit_evidence="",
    )
    envelope = greenfield_operating_envelope_receipt(
        facts=facts,
        source_format="operator_prompt",
        source_size_bytes=len(evidence_source.encode("utf-8")),
        source_document_count=1,
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
            "source_duty_ledger_sha256": "d" * 64,
            "source_duty_verifier_task_sha256": "0" * 64,
            "source_duty_decision_set_sha256": "f" * 64,
            "source_duty_binding_sha256": "e" * 64,
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


def test_edit_dimensions_use_explicit_lifecycle_correction_and_native_nested_frame() -> None:
    initial = _release_case("literal-edit-heading", edit=True)
    edited = replace(initial, lifecycle_correction="Keep the original record and display its review status.")
    assert statistics.expected_case_evidence_format(initial) == "operator_prompt"
    assert statistics.expected_case_source_complexity(initial)["documents"] == 1
    assert statistics.expected_case_evidence_format(edited) == "operator_prompt_with_edit_evidence"
    assert statistics.expected_case_source_complexity(edited) == {
        "documents": 2, "evidence_bytes": len(edited.model_evidence.evidence_source.encode("utf-8")),
    }
    assert edited.model_evidence.prompt == initial.model_evidence.evidence_source


@pytest.mark.parametrize("damage", [None, "no_manifest", "foreign_case", "changed_result", "changed_artifact", "changed_manifest", "symlink"])
def test_edit_authentication_binds_exact_retained_case_after_consumer_cleanup(tmp_path: Path, damage) -> None:
    from greenfield_matrix_release_artifacts import (
        begin_retained_case_evidence, finalize_retained_case_evidence,
        prepare_retained_evidence_output_dir, record_retained_case_bytes,
        write_retained_evidence_manifest,
    )
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    case = replace(_case("retained-edit", stressor="custody"), lifecycle_correction="Preserve review history.")
    result = replace(_result(case, passed=True), evidence={"case": case_evidence(case)})
    root = prepare_retained_evidence_output_dir(output_dir=tmp_path / "retained", temp_parent=consumer)
    retained = begin_retained_case_evidence(evidence_root=root, case_id=case.case_id)
    record_retained_case_bytes(retained, "commands/lifecycle.initial-request", case.initial_prompt.encode())
    record_retained_case_bytes(retained, "semantic/proposal-payload.v1.json", b"{}")
    case_manifest = finalize_retained_case_evidence(case=retained, repo_root=consumer, result_payload=result.to_dict())
    manifest = write_retained_evidence_manifest(root=root, expected_case_ids=(case.case_id,))
    shutil.rmtree(consumer)
    if damage == "foreign_case":
        case = replace(case, case_id="another-edit")
    elif damage == "changed_result":
        result = replace(result, create_seconds=2.0)
    elif damage in {"changed_artifact", "symlink"}:
        artifact = case_manifest.parent / "commands/lifecycle.initial-request"
        if damage == "changed_artifact":
            artifact.write_bytes(b"Changed source.")
        else:
            foreign = tmp_path / "foreign"
            foreign.write_bytes(artifact.read_bytes())
            artifact.unlink()
            artifact.symlink_to(foreign)
    elif damage == "changed_manifest":
        case_manifest.write_bytes(case_manifest.read_bytes() + b" ")
    if damage:
        with pytest.raises(ValueError):
            statistics._retained_edit_root(case=case, result=result, manifest=None if damage == "no_manifest" else manifest)
    else:
        assert statistics._retained_edit_root(case=case, result=result, manifest=manifest) == case_manifest.parent
        # An authenticated result is necessary, but supplies no journey credit alone.
        assert statistics._receipt_bound_edit_issues(case=case, result=result, manifest=manifest)


@pytest.mark.parametrize("damage", [None, "no_manifest", "tampered_manifest"])
def test_semantic_profiles_authenticate_same_retained_edit_manifest(tmp_path: Path, monkeypatch, damage) -> None:
    """Prove caller custody with real manifests; semantic/compiler fixtures stay isolated."""
    import greenfield_semantic_release_score as score
    from greenfield_matrix_release_artifacts import (
        begin_retained_case_evidence, finalize_retained_case_evidence,
        prepare_retained_evidence_output_dir, record_retained_case_bytes,
        write_retained_evidence_manifest,
    )
    from tests.unit.install.test_greenfield_retained_evidence import _published_case
    from tests.unit.install.test_greenfield_semantic_release_score import FLOORS

    authenticate = statistics._retained_edit_root
    case, result, fixture_root, _transactions = _statistics_edit_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(statistics, "_retained_edit_root", authenticate)
    consumer = tmp_path / "consumer"
    receipt = _published_case(repo=consumer, staged_root=tmp_path / "stage", transaction_hash="b" * 64)
    result.evidence["preconfirm_dry_run"].update(receipt)
    confirmation = result.evidence["confirmation_contract"]
    journal = confirmation["terminal_journal"]
    journal["repository_write_set_hash"] = receipt["repository_write_set_hash"]
    journal_bytes = json.dumps(journal).encode()
    (fixture_root / "commands/terminal-journal.v1.json").write_bytes(journal_bytes)
    journal_hash = hashlib.sha256(journal_bytes).hexdigest()
    confirmation["terminal_journal_sha256"] = journal_hash
    confirmation["terminal_pre_retry_snapshot"]["journal_sha256"] = journal_hash
    evidence_root = prepare_retained_evidence_output_dir(output_dir=tmp_path / "authenticated", temp_parent=consumer)
    retained = begin_retained_case_evidence(evidence_root=evidence_root, case_id=case.case_id)
    for path in sorted(fixture_root.rglob("*")):
        if path.is_file():
            record_retained_case_bytes(retained, path.relative_to(fixture_root).as_posix(), path.read_bytes())
    record_retained_case_bytes(retained, "browser/project.png", b"unit browser artifact")
    finalize_retained_case_evidence(case=retained, repo_root=consumer, result_payload=result.to_dict())
    manifest = write_retained_evidence_manifest(root=evidence_root, expected_case_ids=(case.case_id,))
    shutil.rmtree(consumer)
    assert authenticate(case=case, result=result, manifest=manifest) == retained.final_root
    if damage == "no_manifest":
        manifest = None
    elif damage == "tampered_manifest":
        (retained.final_root / "commands/lifecycle.correction").write_bytes(b"Changed correction")

    # Semantic fidelity has its own tests; this regression targets recursive release scoring.
    def isolated_semantics(**kwargs):
        kwargs["metric_counts"]["atomic_semantic_fidelity"][:] = [1, 1]
        kwargs["metric_counts"]["relation_fidelity"][:] = [1, 1]
        return {**score.empty_relation_counts(), "matched": 1, "sample_count": 1}, [], "unit"

    monkeypatch.setattr(score, "score_native_commit", isolated_semantics)
    dimensions = result.evidence["preconfirm_dry_run"]["semantic_snapshot"]["operating_envelope"]["complexity"]["dimensions"]
    report = score.evaluate_semantic_release(
        cases=(case,), results=(result,), floors=FLOORS,
        annotations={case.case_id: {"expected_outcome": "commit", "complexity": dimensions}},
        retained_evidence_manifest=manifest, _allow_not_applicable_metrics=True,
    )
    assert report["case_outcomes"][0]["passed"] is (damage is None), report["case_outcomes"]
    assert report["model_profiles"][0]["passed"] is (damage is None), report["model_profiles"][0]["issues"]
    assert report["passed"] is (damage is None), report["issues"]


def _statistics_edit_fixture(tmp_path: Path, monkeypatch):
    """Unit enforcement fixture: compiler/profile bindings are isolated, never release evidence."""
    from tests.unit.runtime.test_greenfield_edit_lifecycle_preservation import _edit_case
    from tests.unit.runtime.test_greenfield_source_duty_ledger import _yes_decisions
    from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import (
        greenfield_edit_preservation_context, source_duty_entailment_task,
    )
    from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
        preflight_greenfield_source_duty_ledger, validate_greenfield_source_duty_ledger,
    )
    old_source, ledger, old_context, _task, old_decisions = _edit_case()
    request = old_source.split("\n\n# Operator edit evidence\n\n", 1)[0]
    case = replace(_case("genuine-edit", stressor="custody"), prompt=request,
        lifecycle_correction=old_context["correction"], tags=("edited_confirmation",))
    source = case.model_evidence.evidence_source
    initial_source = statistics.prepare_model_authoring_evidence(prompt=case.initial_prompt).evidence_source
    context = greenfield_edit_preservation_context(transaction_hash="a" * 64,
        prior_lifecycle=old_context["prior_lifecycle"], correction=case.model_evidence.edit_evidence, evidence_text=source)
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    task = source_duty_entailment_task(preflight, evidence_text=source, edit_preservation=context)
    decisions = _yes_decisions(preflight, evidence_text=source)
    decisions.update(version=old_decisions["version"], verifier_task_sha256=task["verifier_task_sha256"],
        edit_preservation=deepcopy(old_decisions["edit_preservation"]))
    duty = validate_greenfield_source_duty_ledger(ledger, evidence_text=source, decision_set=decisions, edit_preservation=context)
    root = tmp_path / "retained-case"
    root.mkdir()
    transactions = {}
    phases = {}

    def write(relative, payload):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload if isinstance(payload, bytes) else json.dumps(payload).encode())
        path.chmod(0o600)
        return path

    for label, digest, framed in (("initial", "a" * 64, initial_source), ("edited", "b" * 64, source)):
        observation = production_stage_observation(STANDARD_PROFILE_ID)
        source_hash = hashlib.sha256(framed.encode()).hexdigest()
        observation["source_sha256"] = source_hash
        nonce = ("c" if label == "initial" else "d") * 64
        journey_id = ("e" if label == "initial" else "f") * 64
        completion_digest = hashlib.sha256(nonce.encode()).hexdigest()
        payloads = {
            "product-create-transaction.v1.json": {"phase": label},
            "product-create-transaction.v1.json.compiler-receipt.v1.json": {"phase": label},
            ".bounded-journey.v1.json": {"version": "odylith.greenfield.journey-supervision.v1", "journey_id": journey_id, "completion_digest": completion_digest},
            ".bounded-completion.v1.json": {"version": "odylith.greenfield.journey-completion.v2", "status": "completion_attempt", "journey_id": journey_id, "transaction_hash": digest, "completion_digest": completion_digest, "record_started_at": 1.0, "deadline": 2.0},
            "completion-receipt.json": {"version": "odylith.greenfield.completion-receipt.v1", "journey_id": journey_id, "transaction_hash": digest, "nonce": nonce},
        }
        artifacts = {}
        for name, payload in payloads.items():
            relative = f"semantic/lifecycle-{label}/{name}"
            path = write(relative, payload)
            original = (f"/deleted-consumer/.odylith/runtime/greenfield/completion-receipts/{digest}/{journey_id}.json"
                if name == "completion-receipt.json" else f"/deleted-consumer/.odylith/runtime/greenfield/pending/{digest}/{name}")
            artifacts[original] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mode": 0o600,
                "retained_mode": 0o600, "retained_path": relative,
                "kind": "completion_receipt" if name == "completion-receipt.json" else "pending"}
        phase = {"transaction_hash": digest, "source_sha256": source_hash, "artifacts": artifacts,
            "transaction_file": f"/deleted-consumer/.odylith/runtime/greenfield/pending/{digest}/product-create-transaction.v1.json",
            "completion_receipt_path": f"/deleted-consumer/.odylith/runtime/greenfield/completion-receipts/{digest}/{journey_id}.json", "observation": observation}
        profile = {"profile_id": STANDARD_PROFILE_ID, "status": "passed", "issues": [],
            "expected_source_sha256": source_hash, "stage_observation": observation}
        if label == "initial":
            phase.update(model_profile=profile, model_binding_issues=[])
        else:
            phase["source_duty_receipt"] = duty
        phases[label] = phase
        transactions[label] = SimpleNamespace(transaction_hash=digest, quality_manifest={},
            proposal={"intent": {"prompt": framed, "authored_semantics": {"source_duty": {"ledger_receipt": duty}}},
                "semantic_model": {"source_lifecycle": context["prior_lifecycle"]}})
        write("diagnostics-initial/candidate.stdout" if label == "initial" else "semantic/host-candidate.raw.v1.json", {})
        write("diagnostics-initial/source-ledger-check.stdout" if label == "initial" else "semantic/host-source-ledger-check.raw.v1.json", {"receipt": {} if label == "initial" else duty})
    envelope = greenfield_operating_envelope_receipt(facts=_facts_for_band(case, band="bounded"),
        source_format=case.model_evidence.source_format, source_size_bytes=len(source.encode()), source_document_count=2,
        model_authoring=_model_authoring_observations(STANDARD_PROFILE_ID))
    transactions["edited"].intent_authority = {"operating_envelope": envelope}
    preview = {"mode": "applied", "backlog": [], "components": [], "diagrams": [],
        "dashboard_refresh": {"status": "passed"}, "validation_gate": {"status": "passed"}}
    transactions["edited"].prewrite_package = SimpleNamespace(commit_result_preview=preview)
    journal = {"state": "closed", "lifecycle_state": "CLOSED", "transaction_hash": "b" * 64,
        "repository_write_set_hash": "0" * 64, "commit_result": preview}
    journal_path = write("commands/terminal-journal.v1.json", journal)
    journal_hash = hashlib.sha256(journal_path.read_bytes()).hexdigest()
    write("semantic/create-payload.v1.json", preview)
    for label in ("decide", "retry-decide"):
        write(f"commands/{label}.stdout", {"version": statistics._TERMINAL_CONFIRMATION_VERSION,
            "status": "CLOSED", "command": "CONFIRM", "transaction_hash": "b" * 64,
            "visible_markdown": "Published the reviewed package.", "developer_context": "Reviewed package committed."})
    write("commands/lifecycle.initial-request", case.initial_prompt.encode())
    write("commands/lifecycle.correction", case.lifecycle_correction.encode())
    evidence = {"case": case_evidence(case), "browser_surface_proof": {"required": True, "attempted": True, "issues": []}, "lifecycle_edit": {
        "version": "odylith.greenfield.matrix.receipt-bound-edit.v1", "status": "edited_seal_confirmed",
        "initial_request_sha256": hashlib.sha256(case.initial_prompt.encode()).hexdigest(),
        "correction_sha256": hashlib.sha256(case.lifecycle_correction.encode()).hexdigest(), **phases,
        "initial_artifacts_after_confirm": {token: {key: row[key] for key in ("sha256", "mode")} for token, row in phases["initial"]["artifacts"].items()},
    }, "model_profile": {"profile_id": STANDARD_PROFILE_ID, "status": "passed", "issues": [],
        "expected_source_sha256": phases["edited"]["source_sha256"], "stage_observation": phases["edited"]["observation"]},
        "preconfirm_dry_run": {"status": "compiled", "transaction_hash": "b" * 64, "repository_write_set_hash": "0" * 64,
            "semantic_snapshot": {"operating_envelope": envelope}},
        "confirmation_contract": {"status": "passed", "scope": "explicit_terminal_decision", "commit_payload_source": "closed_journal",
            "decision_rail_issues": [], "terminal_handoff_issues": [], "terminal_proof_issues": [], "terminal_journal": journal,
            "terminal_journal_sha256": journal_hash, "terminal_pre_retry_snapshot": {"journal_sha256": journal_hash},
            "terminal_commands": [{"attempt": "confirm", "returncode": 0}, {"attempt": "same_hash_retry", "returncode": 0}]}}
    result = replace(_result(case, passed=True), evidence=evidence, browser_surface_proof_attempted=True)
    monkeypatch.setattr(statistics, "_retained_edit_root", lambda **kwargs: root)
    monkeypatch.setattr(statistics, "load_compiled_product_create_transaction_file", lambda path: transactions["initial" if "lifecycle-initial" in str(path) else "edited"])
    monkeypatch.setattr(statistics, "authored_model_result_binding_issues", lambda **kwargs: ())
    monkeypatch.setattr(statistics, "model_profile_release_proof", lambda *args, **kwargs: {"status": "passed"})
    return case, result, root, transactions


@pytest.mark.parametrize("damage", [
    None, "version", "prepare_only", "tag_only", "retained_failure", "retained_custody_issues", "prior_hash", "same_hash",
    "missing_receipt", "foreign_receipt", "foreign_rebound_receipt", "foreign_edit_consumer",
    "stale_receipt", "receipt_bytes", "seal_bytes", "private_mode", "retained_path", "membership",
    "initial_source", "edited_source", "flat_source", "correction", "request",
    "prior_readback_missing", "prior_readback_changed", "prior_duty", "missing_duty", "changed_duty",
    "checker_receipt", "documents", "envelope", "uncommitted", "failed_quality", "failed_create",
    "skipped_browser", "failed_browser", "browser_record", "wrong_case", "model_source",
    "model_observation", "initial_model", "journal", "journal_hash", "retry", "retry_response", "commit_result",
])
def test_edit_slice_requires_receipts_preservation_commit_and_browser_custody(tmp_path: Path, monkeypatch, damage) -> None:
    case, result, root, transactions = _statistics_edit_fixture(tmp_path, monkeypatch)
    lifecycle = result.evidence["lifecycle_edit"]
    initial, edited = lifecycle["initial"], lifecycle["edited"]
    if damage == "version": lifecycle["version"] = "invented"
    elif damage == "prepare_only": lifecycle["status"] = "edited_seal_prepared"
    elif damage == "tag_only": result.evidence.pop("lifecycle_edit")
    elif damage == "retained_failure":
        lifecycle["failure"] = {"phase": "confirmation", "type": "RuntimeError", "message": "Confirmation failed after publication."}
    elif damage == "retained_custody_issues":
        lifecycle["custody_issues"] = ["Initial pending artifact changed after confirmation."]
    elif damage == "prior_hash": initial["transaction_hash"] = "9" * 64
    elif damage == "same_hash": transactions["edited"].transaction_hash = initial["transaction_hash"]
    elif damage == "missing_receipt": initial["artifacts"].pop(initial["completion_receipt_path"])
    elif damage == "foreign_receipt": initial["completion_receipt_path"] = "/foreign/receipt"
    elif damage == "foreign_rebound_receipt":
        original = initial["completion_receipt_path"]
        initial["completion_receipt_path"] = original.replace("/deleted-consumer/", "/foreign-consumer/")
        initial["artifacts"][initial["completion_receipt_path"]] = initial["artifacts"].pop(original)
    elif damage == "foreign_edit_consumer":
        edited["artifacts"] = {token.replace("/deleted-consumer/", "/foreign-consumer/"): row for token, row in edited["artifacts"].items()}
        for key in ("transaction_file", "completion_receipt_path"):
            edited[key] = edited[key].replace("/deleted-consumer/", "/foreign-consumer/")
    elif damage in {"stale_receipt", "receipt_bytes", "seal_bytes"}:
        filename = "product-create-transaction.v1.json" if damage == "seal_bytes" else "completion-receipt.json"
        path = root / "semantic/lifecycle-initial" / filename
        payload = json.loads(path.read_bytes())
        payload["journey_id" if damage == "stale_receipt" else "changed"] = "9" * 64
        path.write_text(json.dumps(payload))
        if damage == "stale_receipt": initial["artifacts"][initial["completion_receipt_path"]]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    elif damage == "private_mode": (root / "semantic/lifecycle-initial/completion-receipt.json").chmod(0o644)
    elif damage == "retained_path": initial["artifacts"][initial["transaction_file"]]["retained_path"] = "/foreign/transaction"
    elif damage == "membership": (root / "semantic/lifecycle-initial/extra").write_bytes(b"unexpected")
    elif damage == "initial_source": initial["source_sha256"] = "9" * 64
    elif damage == "edited_source": transactions["edited"].proposal["intent"]["prompt"] += "changed"
    elif damage == "flat_source": transactions["edited"].proposal["intent"]["prompt"] = combined_prompt_evidence_source(prompt=case.initial_prompt, edit_evidence=case.lifecycle_correction)
    elif damage == "correction": lifecycle["correction_sha256"] = "9" * 64
    elif damage == "request": (root / "commands/lifecycle.initial-request").write_bytes(b"wrong")
    elif damage == "prior_readback_missing": lifecycle.pop("initial_artifacts_after_confirm")
    elif damage == "prior_readback_changed": next(iter(lifecycle["initial_artifacts_after_confirm"].values()))["mode"] = 0o644
    elif damage == "prior_duty": transactions["initial"].proposal["semantic_model"]["source_lifecycle"]["conditional_guards"][0]["rule"] = "Drop protection."
    elif damage in {"missing_duty", "changed_duty"}:
        table = edited["source_duty_receipt"]["decision_set"]["edit_preservation"]
        if damage == "missing_duty": table.pop(next(iter(table)))
        else: next(iter(table.values()))["verdict"] = "changed"
    elif damage == "checker_receipt": edited["source_duty_receipt"] = {}
    elif damage in {"documents", "envelope"}:
        envelope = deepcopy(result.evidence["preconfirm_dry_run"]["semantic_snapshot"]["operating_envelope"])
        if damage == "documents": envelope["complexity"]["dimensions"]["documents"] = 1
        else: envelope["evidence_format"] = "operator_prompt"
        result.evidence["preconfirm_dry_run"]["semantic_snapshot"]["operating_envelope"] = envelope
    elif damage == "uncommitted": result.evidence["preconfirm_dry_run"]["status"] = "prepared"
    elif damage == "failed_quality": result = replace(result, quality=replace(result.quality, passed=False))
    elif damage == "failed_create": result = replace(result, create_returncode=2)
    elif damage == "skipped_browser": result = replace(result, browser_surface_proof_attempted=False)
    elif damage == "failed_browser": result = replace(result, browser_surface_issues=("meaning lost",))
    elif damage == "browser_record": result.evidence["browser_surface_proof"]["required"] = False
    elif damage == "wrong_case": result.evidence["case"]["id"] = "another-case"
    elif damage == "model_source": result.evidence["model_profile"]["expected_source_sha256"] = initial["source_sha256"]
    elif damage == "model_observation": result.evidence["model_profile"]["stage_observation"] = initial["observation"]
    elif damage == "initial_model": initial["model_profile"]["status"] = "failed"
    elif damage == "journal": result.evidence["confirmation_contract"]["terminal_journal"] = {"state": "prepared"}
    elif damage == "journal_hash": result.evidence["confirmation_contract"]["terminal_journal_sha256"] = "9" * 64
    elif damage == "retry": result.evidence["confirmation_contract"]["terminal_commands"].pop()
    elif damage == "retry_response": (root / "commands/retry-decide.stdout").write_text(json.dumps({"status": "CLOSED", "transaction_hash": "b" * 64}))
    elif damage == "commit_result": (root / "semantic/create-payload.v1.json").write_text(json.dumps({"mode": "uncommitted"}))
    slices, issues = statistics.release_slice_evidence(case=case, result=result)
    assert bool(issues) == bool(damage), issues
    assert slices["evidence_format"] == ("" if damage else "operator_prompt_with_edit_evidence")
    report = outcome_statistics(cases=(case,), results=(result,), release=True)
    assert report["passed_count"] == (0 if damage else 1)
    assert not any(row["dimension"] == "evidence_format"
        and row["value"] == "operator_prompt_with_edit_evidence" for row in report["slices"]) == bool(damage)


@pytest.mark.parametrize("damage", [None, "wrong_hash", "body_with_rebound_receipt", "receipt_with_rebound_inventory"])
def test_retained_edit_phase_invokes_real_compiler_seal_validation(tmp_path: Path, monkeypatch, damage) -> None:
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
        load_compiled_product_create_transaction_file, write_compiled_product_create_transaction_file,
    )
    from tests.unit.runtime.test_greenfield_create_transaction import _transaction
    case, result, root, _transactions = _statistics_edit_fixture(tmp_path, monkeypatch)
    phase = result.evidence["lifecycle_edit"]["initial"]
    transaction = _transaction(tmp_path / "compiler-fixture")
    path = root / "semantic/lifecycle-initial/product-create-transaction.v1.json"
    write_compiled_product_create_transaction_file(path, transaction)
    compiler = path.with_name(path.name + ".compiler-receipt.v1.json")
    source = transaction.proposal["intent"]["prompt"]
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    phase.update(transaction_hash=transaction.transaction_hash, source_sha256=source_hash)
    old_hash = "a" * 64
    phase["artifacts"] = {token.replace(old_hash, transaction.transaction_hash): row for token, row in phase["artifacts"].items()}
    for key in ("transaction_file", "completion_receipt_path"):
        phase[key] = phase[key].replace(old_hash, transaction.transaction_hash)
    phase["observation"]["source_sha256"] = source_hash
    phase["model_profile"]["expected_source_sha256"] = source_hash
    for name in (".bounded-completion.v1.json", "completion-receipt.json"):
        target = path.parent / name
        payload = json.loads(target.read_bytes())
        payload["transaction_hash"] = transaction.transaction_hash
        target.write_text(json.dumps(payload))
    if damage == "wrong_hash":
        phase["transaction_hash"] = "9" * 64
    elif damage == "body_with_rebound_receipt":
        body = json.loads(path.read_bytes())
        body["proposal"]["intent"]["first_path"] = "A different actor owns publication."
        path.write_text(json.dumps(body))
        receipt = json.loads(compiler.read_bytes())
        receipt["transaction_file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        compiler.write_text(json.dumps(receipt))
    elif damage == "receipt_with_rebound_inventory":
        receipt = json.loads(compiler.read_bytes())
        receipt["transaction_hash"] = "9" * 64
        compiler.write_text(json.dumps(receipt))
    for row in phase["artifacts"].values():
        artifact = root / row["retained_path"]
        artifact.chmod(0o600)
        row["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    monkeypatch.setattr(statistics, "load_compiled_product_create_transaction_file", load_compiled_product_create_transaction_file)
    if damage:
        with pytest.raises(ValueError):
            statistics._retained_edit_phase(root=root, label="initial", phase=phase, source=source)
    else:
        loaded = statistics._retained_edit_phase(root=root, label="initial", phase=phase, source=source)
        assert loaded.verified and loaded.transaction_hash == transaction.transaction_hash
