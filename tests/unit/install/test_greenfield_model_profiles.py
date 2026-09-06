from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import sys

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_model_profiles import MODEL_PROFILES
from greenfield_model_profiles import DEEP_PROFILE_ID
from greenfield_model_profiles import RESCUE_PROFILE_ID
from greenfield_model_profiles import STANDARD_PROFILE_ID
from greenfield_model_profiles import UNAVAILABLE_PROVIDER_PROFILE
from greenfield_model_profiles import assign_model_profiles
from greenfield_model_profiles import case_model_profile
from greenfield_model_profiles import model_profile_environment
from greenfield_model_profiles import model_profile_evidence
from greenfield_model_profiles import model_stage_observation_issues
from greenfield_model_profiles import profile_coverage
from greenfield_model_profiles import profile_counts
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
    model_profile_id_for_repair_tier,
    normalize_greenfield_model_repair_tier,
    require_greenfield_model_profile_observation,
    supported_greenfield_model_profile_ids,
    supported_greenfield_model_repair_tiers,
)


def test_assignment_is_balanced_by_outcome_and_does_not_consult_prompt_text() -> None:
    cases = tuple(
        _case(f"commit-{index}", expectation="transaction_committed")
        for index in range(6)
    ) + tuple(
        _case(f"clarify-{index}", expectation="clarification_required")
        for index in range(3)
    )

    assigned = assign_model_profiles(cases)
    changed_prompts = assign_model_profiles(
        tuple(replace(case, prompt=f"Completely different evidence {index}") for index, case in enumerate(cases))
    )

    assert profile_counts(assigned) == {profile: 3 for profile in MODEL_PROFILES}
    assert [case_model_profile(case) for case in assigned] == [
        case_model_profile(case) for case in changed_prompts
    ]
    for profile in MODEL_PROFILES:
        profile_cases = [case for case in assigned if case_model_profile(case) == profile]
        assert sum(case.expectation == "transaction_committed" for case in profile_cases) == 2
        assert sum(case.expectation == "clarification_required" for case in profile_cases) == 1


def test_assignment_balances_repeated_input_styles_across_profiles() -> None:
    cases = tuple(
        replace(_case(f"direct-{index}"), input_style="direct_request")
        for index in range(3)
    ) + tuple(
        replace(_case(f"brief-{index}"), input_style="pasted_brief")
        for index in range(3)
    )

    coverage = profile_coverage(assign_model_profiles(cases))

    assert coverage["input_style"]["direct_request"] == {
        profile: 1 for profile in MODEL_PROFILES
    }
    assert coverage["input_style"]["pasted_brief"] == {
        profile: 1 for profile in MODEL_PROFILES
    }


def test_assignment_preserves_one_valid_explicit_profile_and_rejects_bad_tags() -> None:
    explicit = replace(_case("explicit"), tags=(f"model-profile:{MODEL_PROFILES[0]}",))

    assert case_model_profile(assign_model_profiles((explicit,))[0]) == MODEL_PROFILES[0]

    with pytest.raises(ValueError, match="invalid model profile"):
        assign_model_profiles((replace(_case("bad"), tags=("model-profile:unknown",)),))
    with pytest.raises(ValueError, match="invalid model profile"):
        assign_model_profiles(
            (
                replace(
                    _case("duplicate"),
                    tags=(
                        f"model-profile:{MODEL_PROFILES[0]}",
                        f"model-profile:{MODEL_PROFILES[0]}",
                    ),
                ),
            )
        )


def test_profile_registry_pins_preselected_standard_rescue_and_deep_requests() -> None:
    assert supported_greenfield_model_profile_ids() == (
        STANDARD_PROFILE_ID,
        RESCUE_PROFILE_ID,
        DEEP_PROFILE_ID,
    )
    assert supported_greenfield_model_repair_tiers() == ("standard", "rescue", "deep")
    assert model_profile_id_for_repair_tier("standard") == STANDARD_PROFILE_ID
    assert model_profile_id_for_repair_tier("auto") == STANDARD_PROFILE_ID
    assert model_profile_id_for_repair_tier("") == STANDARD_PROFILE_ID
    assert model_profile_id_for_repair_tier("default") == STANDARD_PROFILE_ID
    assert model_profile_id_for_repair_tier("rescue") == RESCUE_PROFILE_ID
    assert model_profile_id_for_repair_tier("deep") == DEEP_PROFILE_ID
    assert normalize_greenfield_model_repair_tier("default") == "auto"
    assert normalize_greenfield_model_repair_tier("rescue") == "rescue"
    with pytest.raises(ValueError, match="unsupported Greenfield repair tier"):
        normalize_greenfield_model_repair_tier("adaptive")
    standard = get_greenfield_model_profile(STANDARD_PROFILE_ID)
    assert standard.model == "gpt-5.6-terra"
    assert standard.reasoning_effort == "low"
    assert standard.source_review_model == "gpt-5.6-sol"
    assert standard.source_review_reasoning_effort == "medium"
    assert standard.lower_capability is True
    rescue = get_greenfield_model_profile(RESCUE_PROFILE_ID)
    assert rescue.model == "gpt-5.6-terra"
    assert rescue.reasoning_effort == "medium"
    assert rescue.source_review_model == "gpt-5.6-sol"
    assert rescue.source_review_reasoning_effort == "high"
    assert rescue.lower_capability is True
    assert rescue.source_review_reserve_seconds == 20.0
    assert standard.source_review_reserve_seconds == 25.0
    deep = get_greenfield_model_profile(DEEP_PROFILE_ID)
    assert deep.source_review_reserve_seconds == 20.0
    assert deep.model == "gpt-5.6-sol"
    assert deep.source_review_model == "gpt-5.6-sol"
    assert deep.source_review_reasoning_effort == "high"
    assert get_greenfield_model_profile(UNAVAILABLE_PROVIDER_PROFILE).lower_capability is False
    assert UNAVAILABLE_PROVIDER_PROFILE not in supported_greenfield_model_profile_ids()


def test_profile_environments_pin_provider_model_effort_and_shared_tier_windows() -> None:
    inherited = {
        "PATH": "/usr/bin:/bin",
        "ODYLITH_REASONING_PROVIDER": "stale-provider",
        "ODYLITH_REASONING_API_KEY": "secret",
        "ODYLITH_REASONING_CLAUDE_BIN": "stale-claude",
    }

    standard = model_profile_environment(STANDARD_PROFILE_ID, inherited)
    rescue = model_profile_environment(RESCUE_PROFILE_ID, inherited)
    deep = model_profile_environment(DEEP_PROFILE_ID, inherited)
    unavailable = model_profile_environment(
        UNAVAILABLE_PROVIDER_PROFILE,
        inherited,
        unavailable_provider_bin="/nonexistent/greenfield-provider-test",
    )

    assert "ODYLITH_REASONING_API_KEY" not in standard
    assert standard["ODYLITH_REASONING_PROVIDER"] == "codex-cli"
    assert standard["ODYLITH_REASONING_MODEL"] == "gpt-5.6-terra"
    assert standard["ODYLITH_REASONING_CODEX_REASONING_EFFORT"] == "low"
    assert standard["ODYLITH_REASONING_TIMEOUT_SECONDS"] == "55"
    assert rescue["ODYLITH_REASONING_MODEL"] == "gpt-5.6-terra"
    assert rescue["ODYLITH_REASONING_CODEX_REASONING_EFFORT"] == "medium"
    assert rescue["ODYLITH_REASONING_TIMEOUT_SECONDS"] == "80"
    assert deep["ODYLITH_REASONING_MODEL"] == "gpt-5.6-sol"
    assert deep["ODYLITH_REASONING_CODEX_REASONING_EFFORT"] == "high"
    assert deep["ODYLITH_REASONING_TIMEOUT_SECONDS"] == "105"
    assert unavailable["ODYLITH_REASONING_CODEX_BIN"] == "/nonexistent/greenfield-provider-test"
    assert unavailable["ODYLITH_REASONING_CODEX_BIN"] != "/usr/bin/false"
    assert unavailable["ODYLITH_REASONING_TIMEOUT_SECONDS"] == "1"
    evidence = model_profile_evidence(UNAVAILABLE_PROVIDER_PROFILE, unavailable)
    assert evidence["provider_unavailability_configured"] is True
    assert evidence["status"] == "unobserved"


def test_profile_evidence_requires_sealed_observation_parity() -> None:
    env = model_profile_environment(STANDARD_PROFILE_ID, {})
    observed = _sealed_observation(STANDARD_PROFILE_ID, shared_timeout=54.5)
    stage_observation = _stage_observation(
        STANDARD_PROFILE_ID,
        shared_timeout=54.5,
    )

    evidence = model_profile_evidence(
        STANDARD_PROFILE_ID,
        env,
        observed=observed,
        stage_observation=stage_observation,
    )

    assert evidence["status"] == "passed"
    assert evidence["profile_id"] == STANDARD_PROFILE_ID
    assert evidence["observed"] == observed
    assert evidence["sealed_request_role"] == "initial_authoring"
    assert evidence["lower_capability_scope"] == "initial_authoring"
    assert evidence["expected_source_review"] == {
        "provider": "codex-cli",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "medium",
    }
    assert evidence["stage_observation"] == stage_observation
    assert evidence["stage_observation_summary"]["response_kind"] == "authored"
    assert evidence["stage_observation_summary"]["semantic_model_call_count"] == 2
    assert set(evidence["stage_observation_summary"]["request_roles"]) == {
        "initial_authoring",
        "source_review",
    }
    require_greenfield_model_profile_observation(**observed)

    mismatched = model_profile_evidence(
        STANDARD_PROFILE_ID,
        env,
        observed={**observed, "model": "gpt-5.4"},
        stage_observation=stage_observation,
    )
    assert mismatched["status"] == "failed"
    assert mismatched["issues"] == ["observed model does not match pinned Greenfield model profile"]

    misconfigured = model_profile_evidence(
        STANDARD_PROFILE_ID,
        {**env, "ODYLITH_REASONING_MODEL": "gpt-5.4"},
        observed=observed,
        stage_observation=stage_observation,
    )
    assert misconfigured["status"] == "failed"
    assert misconfigured["issues"] == [
        "configured model does not match the assigned release profile"
    ]


def test_profile_evidence_accepts_one_call_clarification_without_review() -> None:
    env = model_profile_environment(RESCUE_PROFILE_ID, {})
    observed = _sealed_observation(RESCUE_PROFILE_ID)
    stage = _stage_observation(RESCUE_PROFILE_ID, response_kind="clarification_required")

    evidence = model_profile_evidence(
        RESCUE_PROFILE_ID,
        env,
        observed=observed,
        stage_observation=stage,
    )

    assert evidence["status"] == "passed"
    assert evidence["stage_observation_summary"]["semantic_model_call_count"] == 1
    assert set(evidence["stage_observation_summary"]["request_roles"]) == {
        "initial_authoring"
    }


def test_profile_evidence_accepts_two_call_review_demoted_clarification() -> None:
    env = model_profile_environment(RESCUE_PROFILE_ID, {})
    observed = _sealed_observation(RESCUE_PROFILE_ID)
    stage = _stage_observation(
        RESCUE_PROFILE_ID,
        response_kind="clarification_required",
        reviewed=True,
    )

    evidence = model_profile_evidence(
        RESCUE_PROFILE_ID,
        env,
        observed=observed,
        stage_observation=stage,
    )

    assert evidence["status"] == "passed"
    assert evidence["stage_observation_summary"]["semantic_model_call_count"] == 2
    assert set(evidence["stage_observation_summary"]["request_roles"]) == {
        "initial_authoring",
        "source_review",
    }


def test_profile_evidence_fails_closed_without_retained_stage_observation() -> None:
    env = model_profile_environment(STANDARD_PROFILE_ID, {})

    evidence = model_profile_evidence(
        STANDARD_PROFILE_ID,
        env,
        observed=_sealed_observation(STANDARD_PROFILE_ID),
    )

    assert evidence["status"] == "failed"
    assert "retained model authoring observation is missing" in evidence["issues"]


@pytest.mark.parametrize(
    ("mutation", "expected_issue"),
    (
        ("version", "retained model authoring observation version is invalid"),
        ("authoring_version", "retained model authoring version is invalid"),
        ("bool_count", "retained semantic model call count is invalid"),
        ("one_authored_call", "authored model response must record exactly two semantic calls"),
        ("forged_initial_role", "retained initial_authoring request role is invalid"),
        ("forged_initial_model", "observed model does not match pinned Greenfield model profile"),
        ("initial_failure", "retained initial_authoring provider metadata records a failure"),
        ("initial_cap", "retained initial authoring timeout does not preserve the review reserve"),
        ("initial_elapsed", "retained initial authoring elapsed time exceeds its timeout"),
        ("missing_review", "reviewed model response is missing its source review"),
        ("invalid_initial_candidate", "retained initial candidate is not an authored response"),
        ("legacy_review_decision", "retained source review decision is invalid"),
        ("forged_review_role", "retained source_review request role is invalid"),
        ("forged_review_model", "observed model does not match pinned Greenfield model profile"),
        ("review_remaining", "retained source review timeout exceeds the remaining shared window"),
        ("review_elapsed", "retained source review elapsed time exceeds its timeout"),
        ("total_elapsed", "retained semantic calls exceed the sealed shared model window"),
    ),
)
def test_stage_observation_rejects_malformed_forged_roles_and_timing(
    mutation: str,
    expected_issue: str,
) -> None:
    observed = _sealed_observation(RESCUE_PROFILE_ID)
    stage = _mutated_stage_observation(mutation)

    issues = model_stage_observation_issues(
        RESCUE_PROFILE_ID,
        observed=observed,
        stage_observation=stage,
    )

    assert expected_issue in issues


@pytest.mark.parametrize(
    ("mutation", "expected_issue"),
    (
        ("three_calls", "clarification model response must record one or two semantic calls"),
        ("missing_candidate", "reviewed model response is missing its initial candidate"),
        ("missing_review", "reviewed model response is missing its source review"),
        ("forged_review_role", "retained source_review request role is invalid"),
        ("forged_review_cap", "retained source review timeout exceeds the remaining shared window"),
        ("legacy_review_decision", "retained source review decision is invalid"),
        (
            "mismatched_review_decision",
            "clarification source review decision does not match the final response",
        ),
    ),
)
def test_review_demoted_clarification_rejects_missing_or_forged_proof(
    mutation: str,
    expected_issue: str,
) -> None:
    stage = _stage_observation(
        RESCUE_PROFILE_ID,
        response_kind="clarification_required",
        reviewed=True,
    )
    if mutation == "three_calls":
        stage["semantic_model_call_count"] = 3
    elif mutation == "missing_candidate":
        stage.pop("initial_response")
    elif mutation == "missing_review":
        stage.pop("source_review")
    else:
        review = stage["source_review"]
        assert isinstance(review, dict)
        if mutation == "forged_review_role":
            review["request_role"] = "initial_authoring"
        elif mutation == "forged_review_cap":
            review["timeout_seconds"] = 76.0
        elif mutation == "legacy_review_decision":
            review["response"] = {"corrections": []}
        elif mutation == "mismatched_review_decision":
            review["response"] = {"result": {"corrections": []}}

    issues = model_stage_observation_issues(
        RESCUE_PROFILE_ID,
        observed=_sealed_observation(RESCUE_PROFILE_ID),
        stage_observation=stage,
    )

    assert expected_issue in issues


def _sealed_observation(
    profile_id: str,
    *,
    shared_timeout: float | None = None,
) -> dict[str, object]:
    profile = get_greenfield_model_profile(profile_id)
    return {
        "profile_id": profile_id,
        "provider": profile.provider,
        "model": profile.model,
        "reasoning_effort": profile.reasoning_effort,
        "effective_timeout_seconds": (
            profile.model_timeout_seconds if shared_timeout is None else shared_timeout
        ),
        "authoring_tier": profile.repair_tier,
    }


def _role_observation(
    profile_id: str,
    *,
    request_role: str,
    timeout_seconds: float,
    elapsed_seconds: float,
) -> dict[str, object]:
    profile = get_greenfield_model_profile(profile_id)
    model = profile.model if request_role == "initial_authoring" else profile.source_review_model
    effort = (
        profile.reasoning_effort
        if request_role == "initial_authoring"
        else profile.source_review_reasoning_effort
    )
    return {
        "profile_id": profile_id,
        "request_role": request_role,
        "timeout_seconds": timeout_seconds,
        "elapsed_seconds": elapsed_seconds,
        "model": model,
        "reasoning_effort": effort,
        "provider": {
            "provider": profile.provider,
            "model": model,
            "reasoning_effort": effort,
        },
    }


def _clarification_result() -> dict[str, object]:
    return {
        "status": "clarification_required",
        "consistency": {
            "status": "material_ambiguity",
            "evidence_quotes": [],
        },
        "clarification": {"material_dimension": "first_path"},
    }


def _review_observation(
    profile_id: str,
    *,
    response_kind: str = "authored",
) -> dict[str, object]:
    observation = _role_observation(
        profile_id,
        request_role="source_review",
        timeout_seconds=10.0,
        elapsed_seconds=5.0,
    )
    observation["response"] = {
        "result": (
            {"corrections": []}
            if response_kind == "authored"
            else _clarification_result()
        )
    }
    return observation


def _stage_observation(
    profile_id: str,
    *,
    response_kind: str = "authored",
    shared_timeout: float | None = None,
    reviewed: bool = False,
) -> dict[str, object]:
    profile = get_greenfield_model_profile(profile_id)
    shared = profile.model_timeout_seconds if shared_timeout is None else shared_timeout
    response_result = (
        {"status": "authored"}
        if response_kind == "authored"
        else _clarification_result()
    )
    has_review = response_kind == "authored" or reviewed
    stage: dict[str, object] = {
        "version": "odylith.greenfield.model-proof-observation.v2",
        "authoring_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "semantic_model_call_count": 2 if has_review else 1,
        "response": {
            "version": GREENFIELD_INTENT_AUTHORING_VERSION,
            "result": response_result,
        },
        "initial_authoring": _role_observation(
            profile_id,
            request_role="initial_authoring",
            timeout_seconds=shared - profile.source_review_reserve_seconds,
            elapsed_seconds=10.0,
        ),
    }
    if has_review:
        stage["initial_response"] = {
            "version": GREENFIELD_INTENT_AUTHORING_VERSION,
            "result": {"status": "authored"},
        }
        stage["source_review"] = _review_observation(
            profile_id,
            response_kind=response_kind,
        )
    return stage


def _mutated_stage_observation(mutation: str) -> dict[str, object]:
    stage = deepcopy(_stage_observation(RESCUE_PROFILE_ID))
    initial = stage["initial_authoring"]
    review = stage["source_review"]
    assert isinstance(initial, dict) and isinstance(review, dict)
    if mutation == "version":
        stage["version"] = "old"
    elif mutation == "authoring_version":
        stage["authoring_version"] = "old"
    elif mutation == "bool_count":
        stage["semantic_model_call_count"] = True
    elif mutation == "one_authored_call":
        stage["semantic_model_call_count"] = 1
    elif mutation == "forged_initial_role":
        initial["request_role"] = "source_review"
    elif mutation == "forged_initial_model":
        initial["model"] = "gpt-5.6-sol"
        provider = initial["provider"]
        assert isinstance(provider, dict)
        provider["model"] = "gpt-5.6-sol"
    elif mutation == "initial_failure":
        provider = initial["provider"]
        assert isinstance(provider, dict)
        provider["code"] = "provider_timeout"
    elif mutation == "initial_cap":
        initial["timeout_seconds"] = 80.0
    elif mutation == "initial_elapsed":
        initial["elapsed_seconds"] = 61.0
    elif mutation == "missing_review":
        stage.pop("source_review")
    elif mutation == "invalid_initial_candidate":
        initial_response = stage["initial_response"]
        assert isinstance(initial_response, dict)
        initial_response["result"] = _clarification_result()
    elif mutation == "legacy_review_decision":
        review["response"] = {"corrections": []}
    elif mutation == "forged_review_role":
        review["request_role"] = "initial_authoring"
    elif mutation == "forged_review_model":
        review["model"] = "gpt-5.6-terra"
        provider = review["provider"]
        assert isinstance(provider, dict)
        provider["model"] = "gpt-5.6-terra"
    elif mutation == "review_remaining":
        initial["elapsed_seconds"] = 75.0
        review["timeout_seconds"] = 10.0
    elif mutation == "review_elapsed":
        review["elapsed_seconds"] = 11.0
    elif mutation == "total_elapsed":
        initial["elapsed_seconds"] = 60.0
        review["timeout_seconds"] = 20.0
        review["elapsed_seconds"] = 21.0
    else:
        raise AssertionError(f"unknown mutation: {mutation}")
    return stage


def _case(
    case_id: str,
    *,
    expectation: str = "transaction_committed",
) -> GreenfieldMatrixCase:
    return GreenfieldMatrixCase(
        case_id=case_id,
        name=case_id,
        prompt=f"Operator completes {case_id} and reviews one receipt.",
        required_terms=("receipt",),
        expectation=expectation,
    )
