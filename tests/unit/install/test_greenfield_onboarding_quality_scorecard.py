from __future__ import annotations

from types import SimpleNamespace
import sys

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_onboarding_quality_scorecard import ONBOARDING_QUALITY_DIMENSIONS
from greenfield_onboarding_quality_scorecard import build_onboarding_quality_scorecard


_COMMITTED_SCORES = {
    "completion": 10,
    "semantic_manifest": 10,
    "copy_semantic_clarity": 10,
    "traceability": 10,
    "operator_usefulness": 10,
    "implementation_prompts": 10,
    "confirmation_ux": 10,
    "product_manager": 10,
    "architect": 10,
    "engineer": 10,
    "domain_expert": 10,
}


def test_scorecard_requires_every_explicit_onboarding_dimension() -> None:
    scorecard = build_onboarding_quality_scorecard(
        results=(_result("committed package"), _result("clarification", expectation="clarification_required")),
        browser_proof={"status": "passed"},
        platform_leakage_proof={"status": "passed"},
        metamorphic_output={"passed": True},
        rescue_proof={"status": "passed"},
        natural_rescue_proof={"status": "passed"},
        commit_recovery_proof={"status": "passed"},
    )

    assert scorecard["status"] == "passed"
    assert scorecard["score"] == 10
    assert tuple(scorecard["dimensions"]) == ONBOARDING_QUALITY_DIMENSIONS
    assert all(row["score"] == 10 for row in scorecard["dimensions"].values())


def test_scorecard_fails_when_visible_confirmation_or_navigation_is_not_proven() -> None:
    result = _result("committed package")
    result.quality.scores["confirmation_ux"] = 0

    scorecard = build_onboarding_quality_scorecard(
        results=(result, _result("clarification", expectation="clarification_required")),
        browser_proof={"status": "passed"},
        platform_leakage_proof={"status": "passed"},
        metamorphic_output={"passed": True},
        rescue_proof={"status": "passed"},
        natural_rescue_proof={"status": "passed"},
        commit_recovery_proof={"status": "passed"},
    )

    dimension = scorecard["dimensions"]["confirmation_and_post_success_ux_clarity"]
    assert scorecard["status"] == "failed"
    assert scorecard["score"] == 0
    assert dimension["score"] == 0
    assert dimension["issues"] == ["committed package: confirmation_ux is not 10"]


def _result(name: str, *, expectation: str = "transaction_committed") -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        evidence={"case": {"expectation": expectation}},
        quality=SimpleNamespace(passed=True, scores=dict(_COMMITTED_SCORES)),
    )
