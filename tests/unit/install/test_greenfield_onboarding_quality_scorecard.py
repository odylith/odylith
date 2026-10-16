from __future__ import annotations

from types import SimpleNamespace
import sys

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_onboarding_quality_scorecard import ONBOARDING_QUALITY_DIMENSIONS
from greenfield_onboarding_quality_scorecard import build_onboarding_quality_scorecard
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    RESCUE_PROFILE_ID,
    STANDARD_PROFILE_ID,
)


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
_PROFILE_IDS = {
    "standard": STANDARD_PROFILE_ID,
    "rescue": RESCUE_PROFILE_ID,
}
_INDEPENDENT_LENSES = (
    "product_manager",
    "architect",
    "engineer",
    "domain_expert",
)


def test_scorecard_requires_every_explicit_onboarding_dimension() -> None:
    scorecard = build_onboarding_quality_scorecard(
        results=_passing_results(),
        browser_proof={"status": "passed"},
        platform_leakage_proof={"status": "passed"},
        metamorphic_output={"passed": True},
        model_profile_proof=_passing_profile_proof(),
        unavailable_provider_proof={"status": "passed"},
        commit_recovery_proof={"status": "passed"},
        validated_independent_reviews=_validated_reviews(),
    )

    assert scorecard["status"] == "passed"
    assert scorecard["score"] == 10
    assert tuple(scorecard["dimensions"]) == ONBOARDING_QUALITY_DIMENSIONS
    assert all(row["score"] == 10 for row in scorecard["dimensions"].values())


def test_scorecard_accepts_serialized_results_for_post_run_finalization() -> None:
    serialized = tuple(
        {
            "name": result.name,
            "evidence": result.evidence,
            "quality": {
                "passed": result.quality.passed,
                "scores": dict(result.quality.scores),
            },
        }
        for result in _passing_results()
    )

    scorecard = build_onboarding_quality_scorecard(
        results=serialized,
        browser_proof={"status": "passed"},
        platform_leakage_proof={"status": "passed"},
        metamorphic_output={"passed": True},
        model_profile_proof=_passing_profile_proof(),
        unavailable_provider_proof={"status": "passed"},
        commit_recovery_proof={"status": "passed"},
        validated_independent_reviews=_validated_reviews(),
    )

    assert scorecard["status"] == "passed"
    assert scorecard["score"] == 10


def test_failed_preflight_is_not_described_as_a_committed_transaction() -> None:
    result = _result("failed before preflight", profile_id=_PROFILE_IDS["standard"])
    result.status = "case-execution-exception"
    result.create_returncode = 1
    result.quality.passed = False
    result.quality.scores = {name: 0 for name in _COMMITTED_SCORES}

    scorecard = build_onboarding_quality_scorecard(
        results=(result,),
        browser_proof={"status": "skipped"},
        platform_leakage_proof={"status": "passed"},
        metamorphic_output={"passed": True},
        model_profile_proof={"status": "failed", "profiles": {}},
        unavailable_provider_proof={"status": "not_requested"},
        commit_recovery_proof=None,
    )

    evidence = "\n".join(
        item
        for dimension in scorecard["dimensions"].values()
        for item in dimension["evidence"]
    )
    assert scorecard["status"] == "failed"
    assert "Transaction cases passing operator-usefulness and implementation-prompt checks: 0/1" in evidence
    assert "committed case" not in evidence
    assert "compiled a usable transaction" not in evidence


def test_scorecard_fails_when_visible_confirmation_or_navigation_is_not_proven() -> None:
    results = list(_passing_results())
    result = results[0]
    result.quality.scores["confirmation_ux"] = 0

    scorecard = build_onboarding_quality_scorecard(
        results=tuple(results),
        browser_proof={"status": "passed"},
        platform_leakage_proof={"status": "passed"},
        metamorphic_output={"passed": True},
        model_profile_proof=_passing_profile_proof(),
        unavailable_provider_proof={"status": "passed"},
        commit_recovery_proof={"status": "passed"},
        validated_independent_reviews=_validated_reviews(),
    )

    dimension = scorecard["dimensions"]["confirmation_and_post_success_ux_clarity"]
    assert scorecard["status"] == "failed"
    assert scorecard["score"] == 0
    assert dimension["score"] == 0
    assert dimension["issues"] == ["standard package: confirmation_ux is not 10"]


def test_scorecard_requires_one_semantic_floor_for_every_supported_profile() -> None:
    results = list(_passing_results())
    results[0].quality.scores["semantic_manifest"] = 0

    scorecard = build_onboarding_quality_scorecard(
        results=tuple(results),
        browser_proof={"status": "passed"},
        platform_leakage_proof={"status": "passed"},
        metamorphic_output={"passed": True},
        model_profile_proof=_passing_profile_proof(),
        unavailable_provider_proof={"status": "passed"},
        commit_recovery_proof={"status": "passed"},
    )

    dimension = scorecard["dimensions"]["preconfirm_tribunal_accuracy"]
    assert dimension["status"] == "failed"
    assert "standard package: semantic_manifest is not 10" in dimension["issues"]


def test_scorecard_requires_lower_capability_clarification_and_unavailable_provider_proof() -> None:
    results = tuple(
        result
        for result in _passing_results()
        if result.name != "rescue clarification"
    )

    scorecard = build_onboarding_quality_scorecard(
        results=results,
        browser_proof={"status": "passed"},
        platform_leakage_proof={"status": "passed"},
        metamorphic_output={"passed": True},
        model_profile_proof=_passing_profile_proof(),
        unavailable_provider_proof={"status": "failed"},
        commit_recovery_proof={"status": "passed"},
    )

    dimension = scorecard["dimensions"]["preconfirm_tribunal_accuracy"]
    assert dimension["status"] == "failed"
    assert "lower-capability profile lacks a passed no-write clarification case" in dimension["issues"]
    assert "unavailable-provider fast no-write proof did not pass" in dimension["issues"]


def test_scorecard_keeps_absent_independent_reviews_unproven() -> None:
    results = list(_passing_results())

    scorecard = build_onboarding_quality_scorecard(
        results=tuple(results),
        browser_proof={"status": "passed"},
        platform_leakage_proof={"status": "passed"},
        metamorphic_output={"passed": True},
        model_profile_proof=_passing_profile_proof(),
        unavailable_provider_proof={"status": "passed"},
        commit_recovery_proof={"status": "passed"},
    )

    assert scorecard["status"] == "awaiting-independent-review"
    assert scorecard["score"] is None
    assert scorecard["dimensions"]["actor_action_state_object_extraction"]["status"] == "unproven"
    assert scorecard["dimensions"]["cross_artifact_consistency"]["score"] is None


def test_embedded_failed_independent_review_remains_a_blocker() -> None:
    results = list(_passing_results())
    results[0].quality.scores["product_manager"] = 0

    scorecard = build_onboarding_quality_scorecard(
        results=tuple(results),
        browser_proof={"status": "passed"},
        platform_leakage_proof={"status": "passed"},
        metamorphic_output={"passed": True},
        model_profile_proof=_passing_profile_proof(),
        unavailable_provider_proof={"status": "passed"},
        commit_recovery_proof={"status": "passed"},
        validated_independent_reviews=_validated_reviews(),
    )

    dimension = scorecard["dimensions"]["actor_action_state_object_extraction"]
    assert scorecard["status"] == "failed"
    assert dimension["status"] == "failed"
    assert "standard package: product_manager independent review failed" in dimension["issues"]


def test_validated_independent_reviews_finalize_unproven_lenses() -> None:
    results = list(_passing_results())
    for lens in _INDEPENDENT_LENSES:
        results[0].quality.scores[lens] = -1

    scorecard = build_onboarding_quality_scorecard(
        results=tuple(results),
        browser_proof={"status": "passed"},
        platform_leakage_proof={"status": "passed"},
        metamorphic_output={"passed": True},
        model_profile_proof=_passing_profile_proof(),
        unavailable_provider_proof={"status": "passed"},
        commit_recovery_proof={"status": "passed"},
        validated_independent_reviews={
            "standard package": {lens: "passed" for lens in _INDEPENDENT_LENSES}
        },
    )

    assert scorecard["status"] == "passed"
    assert scorecard["score"] == 10


def test_failed_review_or_automated_gate_cannot_be_promoted_by_other_reviews() -> None:
    results = list(_passing_results())
    for lens in _INDEPENDENT_LENSES:
        results[0].quality.scores[lens] = -1
    results[0].quality.scores["copy_semantic_clarity"] = 0

    scorecard = build_onboarding_quality_scorecard(
        results=tuple(results),
        browser_proof={"status": "passed"},
        platform_leakage_proof={"status": "passed"},
        metamorphic_output={"passed": True},
        model_profile_proof=_passing_profile_proof(),
        unavailable_provider_proof={"status": "passed"},
        commit_recovery_proof={"status": "passed"},
        validated_independent_reviews={
            "standard package": {
                **{lens: "passed" for lens in _INDEPENDENT_LENSES},
                "product_manager": "failed",
            }
        },
    )

    assert scorecard["status"] == "failed"
    dimension = scorecard["dimensions"]["actor_action_state_object_extraction"]
    assert dimension["status"] == "failed"
    assert "standard package: copy_semantic_clarity is not 10" in dimension["issues"]
    assert "standard package: product_manager independent review failed" in dimension["issues"]


def _passing_results() -> tuple[SimpleNamespace, ...]:
    return (
        _result("standard package", profile_id=_PROFILE_IDS["standard"]),
        _result(
            "rescue clarification",
            expectation="clarification_required",
            profile_id=_PROFILE_IDS["rescue"],
        ),
    )


def _passing_profile_proof() -> dict[str, object]:
    return {
        "status": "passed",
        "profiles": {
            profile_id: {
                "repair_tier": tier,
                "lower_capability": tier == "rescue",
                "status": "passed",
            }
            for tier, profile_id in _PROFILE_IDS.items()
        },
    }


def _validated_reviews() -> dict[str, dict[str, str]]:
    return {
        "standard package": {
            lens: "passed"
            for lens in _INDEPENDENT_LENSES
        }
    }


def _result(
    name: str,
    *,
    expectation: str = "transaction_committed",
    profile_id: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        evidence={
            "case": {"id": name, "expectation": expectation},
            "model_profile": {"profile_id": profile_id},
        },
        quality=SimpleNamespace(passed=True, scores=dict(_COMMITTED_SCORES)),
    )
