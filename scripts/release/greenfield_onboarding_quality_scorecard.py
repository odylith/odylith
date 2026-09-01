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
    model_profile_proof: Mapping[str, Any],
    unavailable_provider_proof: Mapping[str, Any],
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
    profile_issues = _profile_evidence_issues(
        transaction_results=transaction_results,
        clarification_results=clarification_results,
        model_profile_proof=model_profile_proof,
    )
    unavailable_provider_passed = _mapping_status(unavailable_provider_proof) == "passed"
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
            passed=(
                bool(transaction_results)
                and all_transaction_scores("semantic_manifest")
                and not profile_issues
                and unavailable_provider_passed
            ),
            evidence=(
                "standard, rescue, and deep profiles passed one committed semantic-manifest floor"
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
    lower_capability_profile_ids: list[str] = []
    for tier in ("standard", "rescue", "deep"):
        matching_profiles = tuple(
            (str(profile_id), summary)
            for profile_id, summary in profiles.items()
            if isinstance(summary, Mapping) and str(summary.get("repair_tier") or "").strip() == tier
        )
        if len(matching_profiles) != 1:
            issues.append(f"installed model-profile proof does not identify one {tier} profile")
            continue
        profile_id, summary = matching_profiles[0]
        if str(summary.get("status") or "").strip() != "passed":
            issues.append(f"installed {tier} model profile did not pass")
        profile_results = tuple(
            result
            for result in transaction_results
            if _result_profile_id(result) == profile_id
        )
        if not profile_results:
            issues.append(f"installed {tier} model profile has no committed semantic-floor case")
        else:
            issues.extend(_missing_transaction_scores(profile_results, "semantic_manifest"))
        if bool(summary.get("lower_capability")):
            lower_capability_profile_ids.append(profile_id)
    safe_clarifications = tuple(
        result
        for result in clarification_results
        if _result_profile_id(result) in lower_capability_profile_ids
        and _quality_passed(result)
    )
    if not lower_capability_profile_ids:
        issues.append("installed model-profile proof does not identify a lower-capability profile")
    elif not safe_clarifications:
        issues.append("lower-capability profile lacks a passed no-write clarification case")
    return tuple(dict.fromkeys(issues))


def _result_profile_id(result: Any) -> str:
    evidence = getattr(result, "evidence", {})
    profile = evidence.get("model_profile") if isinstance(evidence, Mapping) else {}
    return str(profile.get("profile_id") or "").strip() if isinstance(profile, Mapping) else ""


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
