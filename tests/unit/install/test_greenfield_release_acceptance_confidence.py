"""Acceptance and statistical-confidence gates for Greenfield release proof."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from tests.unit.install import test_greenfield_semantic_release_score as support

from greenfield_matrix_types import GreenfieldQualityVerdict


score_module = support.score_module


@pytest.fixture(autouse=True)
def _isolate_structural_scoring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        score_module,
        "require_atomic_fact_ledger",
        lambda *_args, **_kwargs: None,
    )


def test_point_acceptance_and_wilson_floor_are_gated_separately() -> None:
    case = support._case("small-perfect", expectation="transaction_committed")
    floors = deepcopy(support.FLOORS)
    floors["overall_case_success"] = 0.21
    floors["statistical_confidence"]["overall_case_success"] = 0.21

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: support._commit_annotation()},
        results=(support._commit_result(case),),
        floors=floors,
        _include_model_profiles=False,
        _allow_not_applicable_metrics=True,
    )

    acceptance = _check(report, group="acceptance_checks", name="overall_case_success")
    confidence = _check(report, group="confidence_checks", name="overall_case_success")
    assert report["overall_case_success"]["rate"] == 1.0
    assert (acceptance["observed"], acceptance["status"]) == (1.0, "passed")
    assert (confidence["observed"], confidence["status"]) == (0.206549, "failed")


def test_point_acceptance_and_wilson_ceiling_are_gated_separately() -> None:
    case = support._case("small-zero", expectation="transaction_committed")
    floors = deepcopy(support.FLOORS)
    floors["unnecessary_question_rate_ceiling"] = 0.79
    floors["statistical_confidence"]["unnecessary_question_rate_ceiling"] = 0.79

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: support._commit_annotation()},
        results=(support._commit_result(case),),
        floors=floors,
        _include_model_profiles=False,
        _allow_not_applicable_metrics=True,
    )

    acceptance = _check(
        report,
        group="acceptance_checks",
        name="unnecessary_question_rate",
    )
    confidence = _check(
        report,
        group="confidence_checks",
        name="unnecessary_question_rate",
    )
    assert report["metrics"]["unnecessary_question_rate"]["rate"] == 0.0
    assert (acceptance["observed"], acceptance["status"]) == (0.0, "passed")
    assert (confidence["observed"], confidence["status"]) == (0.793451, "failed")


def test_exact_acceptance_and_confidence_pass_for_four_perfect_samples() -> None:
    cases = tuple(
        support._case(f"perfect-{index}", expectation="transaction_committed")
        for index in range(4)
    )

    report = score_module.evaluate_semantic_release(
        cases=cases,
        annotations={case.case_id: support._commit_annotation() for case in cases},
        results=tuple(support._commit_result(case) for case in cases),
        floors=support.EXACT_RELEASE_FLOORS,
        _allow_not_applicable_metrics=True,
    )

    assert report["passed"] is True
    assert all(
        row["status"] in {"passed", "not_applicable"}
        for row in report["acceptance_checks"]
    )
    assert all(
        row["status"] in {"passed", "not_applicable"}
        for row in report["confidence_checks"]
    )
    assert report["overall_case_success"]["rate"] == 1.0
    assert report["overall_case_success"]["confidence_interval_95"]["lower"] == 0.510109
    assert report["model_profiles"][0]["passed"] is True


def test_one_defect_fails_exact_release_acceptance() -> None:
    cases = tuple(
        support._case(f"one-defect-{index}", expectation="transaction_committed")
        for index in range(4)
    )
    results = tuple(support._commit_result(case) for case in cases)
    defective = replace(
        results[-1],
        status="failed",
        quality=GreenfieldQualityVerdict(False, ("failed",), {}, {}, 0, ()),
    )

    report = score_module.evaluate_semantic_release(
        cases=cases,
        annotations={case.case_id: support._commit_annotation() for case in cases},
        results=(*results[:-1], defective),
        floors=support.EXACT_RELEASE_FLOORS,
        _include_model_profiles=False,
        _allow_not_applicable_metrics=True,
    )

    acceptance = _check(report, group="acceptance_checks", name="overall_case_success")
    assert report["passed"] is False
    assert (acceptance["observed"], acceptance["expected"], acceptance["status"]) == (
        0.75,
        1.0,
        "failed",
    )


def test_perfect_but_weak_sample_fails_confidence_without_relaxing_acceptance() -> None:
    case = support._case("weak-perfect", expectation="transaction_committed")

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: support._commit_annotation()},
        results=(support._commit_result(case),),
        floors=support.EXACT_RELEASE_FLOORS,
        _include_model_profiles=False,
        _allow_not_applicable_metrics=True,
    )

    acceptance = _check(report, group="acceptance_checks", name="overall_case_success")
    confidence = _check(report, group="confidence_checks", name="overall_case_success")
    assert acceptance["status"] == "passed"
    assert (confidence["observed"], confidence["expected"], confidence["status"]) == (
        0.206549,
        0.5,
        "failed",
    )
    assert report["passed"] is False


def _check(
    report: dict[str, object],
    *,
    group: str,
    name: str,
) -> dict[str, object]:
    rows = report[group]
    assert isinstance(rows, list)
    return next(row for row in rows if row["name"] == name)
