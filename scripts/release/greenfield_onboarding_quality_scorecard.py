"""Aggregate the versioned Greenfield onboarding-quality rubric from release proof."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


ONBOARDING_QUALITY_RUBRIC_VERSION = "greenfield-onboarding-quality-v1"
ONBOARDING_QUALITY_DIMENSIONS = (
    "consumer_utility_and_comprehension",
    "intent_fidelity_and_evidence_custody",
    "actor_action_state_object_extraction",
    "first_path_completeness_and_coherence",
    "clarification_quality_and_assumption_discipline",
    "cross_artifact_consistency",
    "absence_of_generic_or_ai_shaped_output",
    "preconfirm_tribunal_accuracy",
    "confirm_time_atomicity_readback_retry_and_recovery",
    "confirmation_and_post_success_ux_clarity",
)


def build_onboarding_quality_scorecard(
    *,
    results: Sequence[Any],
    browser_proof: Mapping[str, Any],
    platform_leakage_proof: Mapping[str, Any],
    metamorphic_output: Mapping[str, Any],
    rescue_proof: Any | None,
    natural_rescue_proof: Any | None,
    commit_recovery_proof: Any | None,
) -> dict[str, Any]:
    """Return a strict ten-dimension scorecard for the installed onboarding corpus.

    A dimension is intentionally binary. A release-quality 10 means the
    selected, versioned corpus proved every obligation for that dimension; a
    missing proof is a zero rather than a generous partial score.
    """

    transaction_results = tuple(result for result in results if _expectation(result) != "clarification_required")
    clarification_results = tuple(result for result in results if _expectation(result) == "clarification_required")
    all_transaction_scores = lambda *names: _all_scores(transaction_results, *names)
    browser_passed = _mapping_status(browser_proof) == "passed"
    custody_passed = _mapping_status(platform_leakage_proof) == "passed" and bool(metamorphic_output.get("passed"))
    rescue_passed = _proof_passed(rescue_proof)
    natural_rescue_passed = _proof_passed(natural_rescue_proof)
    recovery_passed = _proof_passed(commit_recovery_proof)

    dimensions = {
        "consumer_utility_and_comprehension": _dimension(
            passed=bool(transaction_results) and all_transaction_scores("operator_usefulness", "implementation_prompts") and browser_passed,
            evidence=(
                f"{len(transaction_results)} committed cases expose project prompts and completed governance surfaces",
                "headless project/workspace browser proof passed" if browser_passed else "headless project/workspace browser proof did not pass",
            ),
            missing=_missing_transaction_scores(transaction_results, "operator_usefulness", "implementation_prompts"),
        ),
        "intent_fidelity_and_evidence_custody": _dimension(
            passed=bool(transaction_results) and all_transaction_scores("semantic_manifest") and custody_passed,
            evidence=(
                "every committed case has a valid typed semantic manifest",
                "generated-artifact platform leakage and metamorphic output proof passed" if custody_passed else "custody proof did not pass",
            ),
            missing=_missing_transaction_scores(transaction_results, "semantic_manifest"),
        ),
        "actor_action_state_object_extraction": _dimension(
            passed=bool(transaction_results) and all_transaction_scores("copy_semantic_clarity", "product_manager", "domain_expert"),
            evidence=("copy, product, and domain quality lenses passed for every committed first path",),
            missing=_missing_transaction_scores(transaction_results, "copy_semantic_clarity", "product_manager", "domain_expert"),
        ),
        "first_path_completeness_and_coherence": _dimension(
            passed=bool(transaction_results) and all_transaction_scores("completion", "copy_semantic_clarity", "product_manager"),
            evidence=("every committed case passed completion, copy-semantic, and product-manager gates",),
            missing=_missing_transaction_scores(transaction_results, "completion", "copy_semantic_clarity", "product_manager"),
        ),
        "clarification_quality_and_assumption_discipline": _dimension(
            passed=bool(clarification_results) and all(_quality_passed(result) for result in clarification_results),
            evidence=(
                f"{len(clarification_results)} material-ambiguity case(s) returned one focused no-write clarification",
                f"{len(transaction_results)} non-clarification case(s) compiled a usable transaction",
            ),
            missing=() if clarification_results else ("corpus has no material-ambiguity clarification case",),
        ),
        "cross_artifact_consistency": _dimension(
            passed=bool(transaction_results) and all_transaction_scores("traceability", "architect"),
            evidence=("every committed package passed traceability and architecture consistency gates",),
            missing=_missing_transaction_scores(transaction_results, "traceability", "architect"),
        ),
        "absence_of_generic_or_ai_shaped_output": _dimension(
            passed=bool(transaction_results) and all_transaction_scores("copy_semantic_clarity", "domain_expert"),
            evidence=("rendered-copy and domain-expert gates found no scored generic or semantically thin output",),
            missing=_missing_transaction_scores(transaction_results, "copy_semantic_clarity", "domain_expert"),
        ),
        "preconfirm_tribunal_accuracy": _dimension(
            passed=bool(transaction_results) and all_transaction_scores("semantic_manifest") and rescue_passed and natural_rescue_passed,
            evidence=(
                "all committed cases passed the typed manifest gate",
                "synthetic rescue and real structured rescue proof passed" if rescue_passed and natural_rescue_passed else "one or more pre-confirm rescue proofs did not pass",
            ),
            missing=_missing_transaction_scores(transaction_results, "semantic_manifest"),
        ),
        "confirm_time_atomicity_readback_retry_and_recovery": _dimension(
            passed=bool(transaction_results) and all_transaction_scores("completion", "engineer") and recovery_passed,
            evidence=(
                "every committed case passed commit-only completion and engineering custody gates",
                "installed crash, retry, rollback, and readback recovery proof passed" if recovery_passed else "installed recovery proof did not pass",
            ),
            missing=_missing_transaction_scores(transaction_results, "completion", "engineer"),
        ),
        "confirmation_and_post_success_ux_clarity": _dimension(
            passed=bool(transaction_results) and all_transaction_scores("confirmation_ux") and browser_passed,
            evidence=(
                "every committed case exposed a hash-bound CONFIRM / EDIT / REJECT rail and five stable success routes",
                "headless browser proof passed for the generated workspace" if browser_passed else "headless browser proof did not pass",
            ),
            missing=_missing_transaction_scores(transaction_results, "confirmation_ux"),
        ),
    }
    score = min(int(dimension["score"]) for dimension in dimensions.values()) if dimensions else 0
    return {
        "version": ONBOARDING_QUALITY_RUBRIC_VERSION,
        "status": "passed" if score == 10 else "failed",
        "score": score,
        "score_scope": "versioned installed Greenfield corpus and explicit transaction contract only",
        "dimensions": dimensions,
    }


def _dimension(*, passed: bool, evidence: Sequence[str], missing: Sequence[str]) -> dict[str, Any]:
    issues = tuple(dict.fromkeys(str(issue).strip() for issue in missing if str(issue).strip()))
    return {
        "score": 10 if passed and not issues else 0,
        "status": "passed" if passed and not issues else "failed",
        "evidence": [str(item) for item in evidence if str(item).strip()],
        "issues": list(issues),
    }


def _all_scores(results: Sequence[Any], *names: str) -> bool:
    return bool(results) and not _missing_transaction_scores(results, *names)


def _missing_transaction_scores(results: Sequence[Any], *names: str) -> tuple[str, ...]:
    issues: list[str] = []
    for result in results:
        scores = getattr(getattr(result, "quality", None), "scores", {})
        score_map = scores if isinstance(scores, Mapping) else {}
        for name in names:
            if int(score_map.get(name, 0)) != 10:
                issues.append(f"{getattr(result, 'name', 'unnamed case')}: {name} is not 10")
    return tuple(issues)


def _expectation(result: Any) -> str:
    evidence = getattr(result, "evidence", {})
    case = evidence.get("case") if isinstance(evidence, Mapping) else {}
    return str(case.get("expectation") or "transaction_committed").strip() if isinstance(case, Mapping) else "transaction_committed"


def _quality_passed(result: Any) -> bool:
    return bool(getattr(getattr(result, "quality", None), "passed", False))


def _mapping_status(value: Mapping[str, Any]) -> str:
    return str(value.get("status") or "").strip()


def _proof_passed(value: Any | None) -> bool:
    if value is None:
        return False
    if isinstance(value, Mapping):
        return str(value.get("status") or "").strip() == "passed"
    return bool(getattr(value, "passed", False))


__all__ = [
    "ONBOARDING_QUALITY_DIMENSIONS",
    "ONBOARDING_QUALITY_RUBRIC_VERSION",
    "build_onboarding_quality_scorecard",
]
