"""Aggregate the versioned Greenfield onboarding-quality rubric from release proof."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    lower_capability_control_greenfield_model_profile_ids,
    release_success_greenfield_model_profile_ids,
)


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
    model_profile_proof: Mapping[str, Any],
    unavailable_provider_proof: Mapping[str, Any],
    commit_recovery_proof: Any | None,
    validated_independent_reviews: Mapping[str, Mapping[str, str]] | None = None,
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
    profile_issues = _profile_evidence_issues(
        transaction_results=transaction_results,
        clarification_results=clarification_results,
        model_profile_proof=model_profile_proof,
    )
    unavailable_provider_passed = _mapping_status(unavailable_provider_proof) == "passed"
    recovery_passed = _proof_passed(commit_recovery_proof)
    independent_reviews = (
        validated_independent_reviews
        if isinstance(validated_independent_reviews, Mapping)
        else {}
    )

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
        "actor_action_state_object_extraction": _review_dimension(
            automated_passed=bool(transaction_results) and all_transaction_scores("copy_semantic_clarity"),
            evidence=("copy-semantic validation passed; product and domain judgment is supplied by independent review",),
            automated_missing=_missing_transaction_scores(transaction_results, "copy_semantic_clarity"),
            review_scores=_independent_review_scores(
                transaction_results,
                independent_reviews,
                "product_manager",
                "domain_expert",
            ),
        ),
        "first_path_completeness_and_coherence": _review_dimension(
            automated_passed=bool(transaction_results) and all_transaction_scores("completion", "copy_semantic_clarity"),
            evidence=("completion and copy-semantic validation passed; product utility is supplied by independent review",),
            automated_missing=_missing_transaction_scores(transaction_results, "completion", "copy_semantic_clarity"),
            review_scores=_independent_review_scores(
                transaction_results,
                independent_reviews,
                "product_manager",
            ),
        ),
        "clarification_quality_and_assumption_discipline": _dimension(
            passed=bool(clarification_results) and all(_quality_passed(result) for result in clarification_results),
            evidence=(
                f"{len(clarification_results)} material-ambiguity case(s) returned one focused no-write clarification",
                f"{len(transaction_results)} non-clarification case(s) compiled a usable transaction",
            ),
            missing=() if clarification_results else ("corpus has no material-ambiguity clarification case",),
        ),
        "cross_artifact_consistency": _review_dimension(
            automated_passed=bool(transaction_results) and all_transaction_scores("traceability"),
            evidence=("traceability validation passed; architecture consistency is supplied by independent review",),
            automated_missing=_missing_transaction_scores(transaction_results, "traceability"),
            review_scores=_independent_review_scores(
                transaction_results,
                independent_reviews,
                "architect",
            ),
        ),
        "absence_of_generic_or_ai_shaped_output": _review_dimension(
            automated_passed=bool(transaction_results) and all_transaction_scores("copy_semantic_clarity"),
            evidence=("rendered-copy validation passed; domain-specific quality is supplied by independent review",),
            automated_missing=_missing_transaction_scores(transaction_results, "copy_semantic_clarity"),
            review_scores=_independent_review_scores(
                transaction_results,
                independent_reviews,
                "domain_expert",
            ),
        ),
        "preconfirm_tribunal_accuracy": _dimension(
            passed=(
                bool(transaction_results)
                and all_transaction_scores("semantic_manifest")
                and not profile_issues
                and unavailable_provider_passed
            ),
            evidence=(
                "Astra passed the committed semantic-manifest floor"
                if not profile_issues
                else "one or more installed profile obligations did not pass",
                "the lower-capability profile returned a passed no-write clarification"
                if not profile_issues
                else "lower-capability safe clarification was not proven",
                "the unavailable-provider case failed quickly without writes or staging"
                if unavailable_provider_passed
                else "unavailable-provider fast no-write behavior was not proven",
            ),
            missing=(
                *_missing_transaction_scores(transaction_results, "semantic_manifest"),
                *profile_issues,
                *(() if unavailable_provider_passed else ("unavailable-provider fast no-write proof did not pass",)),
            ),
        ),
        "confirm_time_atomicity_readback_retry_and_recovery": _review_dimension(
            automated_passed=bool(transaction_results) and all_transaction_scores("completion") and recovery_passed,
            evidence=(
                "every committed case passed commit-only completion; engineering judgment is supplied by independent review",
                "installed crash, retry, rollback, and readback recovery proof passed" if recovery_passed else "installed recovery proof did not pass",
            ),
            automated_missing=(
                *_missing_transaction_scores(transaction_results, "completion"),
                *(() if recovery_passed else ("installed recovery proof did not pass",)),
            ),
            review_scores=_independent_review_scores(
                transaction_results,
                independent_reviews,
                "engineer",
            ),
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
    failed = any(dimension["status"] == "failed" for dimension in dimensions.values())
    unproven = any(dimension["status"] == "unproven" for dimension in dimensions.values())
    score: int | None = 0 if failed else None if unproven else 10
    return {
        "version": ONBOARDING_QUALITY_RUBRIC_VERSION,
        "status": (
            "failed"
            if failed
            else "awaiting-independent-review"
            if unproven
            else "passed"
        ),
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


def _review_dimension(
    *,
    automated_passed: bool,
    evidence: Sequence[str],
    automated_missing: Sequence[str],
    review_scores: Sequence[tuple[str, int]],
) -> dict[str, Any]:
    automated_issues = tuple(
        dict.fromkeys(str(issue).strip() for issue in automated_missing if str(issue).strip())
    )
    failed_reviews = tuple(label for label, score in review_scores if score == 0)
    unproven_reviews = tuple(label for label, score in review_scores if score < 0)
    if not automated_passed or automated_issues or failed_reviews:
        issues = (*automated_issues, *(f"{label} independent review failed" for label in failed_reviews))
        return {
            "score": 0,
            "status": "failed",
            "evidence": [str(item) for item in evidence if str(item).strip()],
            "issues": list(dict.fromkeys(issues)),
        }
    if unproven_reviews:
        return {
            "score": None,
            "status": "unproven",
            "evidence": [str(item) for item in evidence if str(item).strip()],
            "issues": [
                f"{label} independent review is unproven"
                for label in unproven_reviews
            ],
        }
    return {
        "score": 10,
        "status": "passed",
        "evidence": [str(item) for item in evidence if str(item).strip()],
        "issues": [],
    }


def _independent_review_scores(
    results: Sequence[Any],
    validated_reviews: Mapping[str, Mapping[str, str]],
    *lenses: str,
) -> tuple[tuple[str, int], ...]:
    scores: list[tuple[str, int]] = []
    for result in results:
        case_id = _case_id(result)
        result_name = str(_field(result, "name", "unnamed case"))
        overrides = validated_reviews.get(case_id)
        override_map = overrides if isinstance(overrides, Mapping) else {}
        result_scores = _field(_field(result, "quality", {}), "scores", {})
        score_map = result_scores if isinstance(result_scores, Mapping) else {}
        for lens in lenses:
            status = str(override_map.get(lens) or "").strip().casefold()
            embedded = score_map.get(lens, -1)
            if embedded == 0 and not isinstance(embedded, bool):
                score = 0
            elif status:
                score = 10 if status == "passed" else 0 if status == "failed" else -1
            else:
                score = -1
            scores.append((f"{result_name}: {lens}", score))
    return tuple(scores)


def _case_id(result: Any) -> str:
    evidence = _field(result, "evidence", {})
    case = evidence.get("case") if isinstance(evidence, Mapping) else {}
    return str(case.get("id") or "").strip() if isinstance(case, Mapping) else ""


def _all_scores(results: Sequence[Any], *names: str) -> bool:
    return bool(results) and not _missing_transaction_scores(results, *names)


def _missing_transaction_scores(results: Sequence[Any], *names: str) -> tuple[str, ...]:
    issues: list[str] = []
    for result in results:
        scores = _field(_field(result, "quality", {}), "scores", {})
        score_map = scores if isinstance(scores, Mapping) else {}
        for name in names:
            if int(score_map.get(name, 0)) != 10:
                issues.append(f"{_field(result, 'name', 'unnamed case')}: {name} is not 10")
    return tuple(issues)


def _expectation(result: Any) -> str:
    evidence = _field(result, "evidence", {})
    case = evidence.get("case") if isinstance(evidence, Mapping) else {}
    return str(case.get("expectation") or "transaction_committed").strip() if isinstance(case, Mapping) else "transaction_committed"


def _quality_passed(result: Any) -> bool:
    return bool(_field(_field(result, "quality", {}), "passed", False))


def _profile_evidence_issues(
    *,
    transaction_results: Sequence[Any],
    clarification_results: Sequence[Any],
    model_profile_proof: Mapping[str, Any],
) -> tuple[str, ...]:
    issues: list[str] = []
    if _mapping_status(model_profile_proof) != "passed":
        issues.append("installed model-profile proof did not pass")
    profile_value = model_profile_proof.get("profiles")
    profiles = profile_value if isinstance(profile_value, Mapping) else {}
    for profile_id in release_success_greenfield_model_profile_ids():
        summary = profiles.get(profile_id)
        if not isinstance(summary, Mapping):
            issues.append(f"installed model-profile proof does not identify success profile `{profile_id}`")
            continue
        if str(summary.get("status") or "").strip() != "passed":
            issues.append(f"installed success profile `{profile_id}` did not pass")
        profile_results = tuple(
            result
            for result in transaction_results
            if _result_profile_id(result) == profile_id
        )
        if not profile_results:
            issues.append(f"installed success profile `{profile_id}` has no committed semantic-floor case")
        else:
            issues.extend(_missing_transaction_scores(profile_results, "semantic_manifest"))
    lower_capability_profile_ids = list(lower_capability_control_greenfield_model_profile_ids())
    safe_clarifications = tuple(
        result
        for result in clarification_results
        if _result_profile_id(result) in lower_capability_profile_ids
        and _quality_passed(result)
    )
    if not safe_clarifications:
        issues.append("lower-capability profile lacks a passed no-write clarification case")
    return tuple(dict.fromkeys(issues))


def _result_profile_id(result: Any) -> str:
    evidence = _field(result, "evidence", {})
    profile = evidence.get("model_profile") if isinstance(evidence, Mapping) else {}
    return str(profile.get("profile_id") or "").strip() if isinstance(profile, Mapping) else ""


def _field(value: Any, key: str, default: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


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
