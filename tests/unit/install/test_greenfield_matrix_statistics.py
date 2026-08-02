from __future__ import annotations

from dataclasses import replace
import sys

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_statistics import outcome_statistics
from greenfield_matrix_statistics import wilson_interval
from greenfield_matrix_types import GreenfieldArtifactCounts
from greenfield_matrix_types import GreenfieldMatrixResult
from greenfield_matrix_types import GreenfieldQualityVerdict
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase


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
