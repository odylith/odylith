"""Pinned author/reviewer identities share fixed Greenfield time budgets."""

from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence import greenfield_model_profile_contract as profiles


PROFILE_IDS = profiles.supported_greenfield_model_profile_ids()
ROLES = ("initial_authoring", "candidate_review")


def _observation(profile_id, role):
    profile = profiles.get_greenfield_model_profile(profile_id)
    review = role == "candidate_review"
    return {
        "profile_id": profile_id,
        "provider": profile.provider,
        "model": profile.review_model if review else profile.model,
        "reasoning_effort": profile.review_reasoning_effort if review else profile.reasoning_effort,
        "effective_timeout_seconds": profile.model_timeout_seconds,
        "authoring_tier": profile.repair_tier,
        "request_role": role,
    }


def test_v17_profiles_separate_performance_targets_from_operational_timeouts():
    assert profiles.GREENFIELD_MODEL_PROFILE_CONTRACT_VERSION == "odylith.greenfield.model-profile-contract.v17"
    assert profiles.GREENFIELD_NORMAL_CASE_TARGET_SECONDS == 60.0
    assert profiles.GREENFIELD_OPERATIONAL_TIMEOUT_SECONDS == 180.0
    assert PROFILE_IDS == (
        "greenfield-standard-terra-low-complete-author-review-v17",
        "greenfield-rescue-terra-medium-complete-author-review-v17",
        "greenfield-deep-sol-high-complete-author-review-v17",
    )
    assert profiles.supported_greenfield_model_repair_tiers() == ("standard", "rescue", "deep")
    assert [
        (
            p.model, p.reasoning_effort, p.model_timeout_seconds,
            p.performance_target_seconds, p.operational_timeout_seconds,
        )
        for p in map(profiles.get_greenfield_model_profile, PROFILE_IDS)
    ] == [
        ("gpt-5.6-terra", "low", 165.0, 90.0, 180.0),
        ("gpt-5.6-terra", "medium", 165.0, 120.0, 180.0),
        ("gpt-5.6-sol", "high", 165.0, 150.0, 180.0),
    ]
    for profile_id in PROFILE_IDS:
        profile = profiles.get_greenfield_model_profile(profile_id)
        assert (profile.review_model, profile.review_reasoning_effort) == ("gpt-6-astra", "medium")
        assert profile.supported_success
        assert profile.operational_timeout_seconds - profile.model_timeout_seconds == 15.0
    assert profiles.get_greenfield_model_profile(profiles.STANDARD_PROFILE_ID).lower_capability
    assert profiles.get_greenfield_model_profile(profiles.RESCUE_PROFILE_ID).lower_capability


@pytest.mark.parametrize("tier,expected", [
    ("auto", profiles.STANDARD_PROFILE_ID),
    ("standard", profiles.STANDARD_PROFILE_ID),
    ("rescue", profiles.RESCUE_PROFILE_ID),
    ("deep", profiles.DEEP_PROFILE_ID),
    ("premium", profiles.DEEP_PROFILE_ID),
])
def test_profile_is_selected_before_calls_and_never_from_elapsed_time(tier, expected):
    assert profiles.model_profile_id_for_repair_tier(tier) == expected


@pytest.mark.parametrize("profile_id", PROFILE_IDS)
@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("fraction", [0.001, 0.5, 1.0])
def test_exact_role_metadata_accepts_finite_positive_residual_windows(profile_id, role, fraction):
    observation = _observation(profile_id, role)
    observation["effective_timeout_seconds"] *= fraction
    assert profiles.greenfield_model_profile_observation_issues(**observation) == ()
    assert profiles.require_greenfield_model_profile_observation(**observation).profile_id == profile_id


@pytest.mark.parametrize("profile_id", PROFILE_IDS)
def test_omitted_role_retains_initial_authoring_contract(profile_id):
    observation = _observation(profile_id, "initial_authoring")
    observation.pop("request_role")
    assert profiles.greenfield_model_profile_observation_issues(**observation) == ()


@pytest.mark.parametrize("profile_id", PROFILE_IDS)
@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("field,value", [
    ("provider", "other-provider"),
    ("model", "other-model"),
    ("reasoning_effort", "other-effort"),
    ("provider", ""),
    ("model", ""),
    ("reasoning_effort", ""),
    ("authoring_tier", "other-tier"),
])
def test_role_observation_rejects_unpinned_metadata(profile_id, role, field, value):
    observation = _observation(profile_id, role)
    observation[field] = value
    assert profiles.greenfield_model_profile_observation_issues(**observation)
    with pytest.raises(ValueError, match="pinned Greenfield model profile"):
        profiles.require_greenfield_model_profile_observation(**observation)


@pytest.mark.parametrize("profile_id", PROFILE_IDS)
@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("timeout", [
    None, True, False, "1", "invalid", [], {}, 0, -1,
    float("nan"), float("inf"), float("-inf"), 10 ** 1000,
])
def test_observed_time_must_be_a_finite_positive_number(profile_id, role, timeout):
    observation = _observation(profile_id, role)
    observation["effective_timeout_seconds"] = timeout
    with pytest.raises(ValueError, match="model window"):
        profiles.require_greenfield_model_profile_observation(**observation)


@pytest.mark.parametrize("profile_id", PROFILE_IDS)
@pytest.mark.parametrize("role", ROLES)
def test_observed_time_cannot_exceed_the_role_cap(profile_id, role):
    observation = _observation(profile_id, role)
    observation["effective_timeout_seconds"] += 0.001
    with pytest.raises(ValueError, match="model window"):
        profiles.require_greenfield_model_profile_observation(**observation)


@pytest.mark.parametrize("profile_id", PROFILE_IDS)
def test_review_uses_the_shared_window_with_its_pinned_identity(profile_id):
    observation = _observation(profile_id, "initial_authoring")
    observation["request_role"] = "candidate_review"
    with pytest.raises(ValueError):
        profiles.require_greenfield_model_profile_observation(**observation)


@pytest.mark.parametrize("profile_id", PROFILE_IDS)
def test_review_rejects_previous_reviewer_identity_even_with_matching_effort(profile_id):
    observation = _observation(profile_id, "candidate_review")
    observation["model"] = "gpt-5.6-sol"
    with pytest.raises(ValueError, match="observed model does not match"):
        profiles.require_greenfield_model_profile_observation(**observation)


@pytest.mark.parametrize("role", ["", "source_review", "design", "repair", "Candidate_Review", None])
def test_unknown_roles_are_rejected(role):
    observation = _observation(profiles.STANDARD_PROFILE_ID, "initial_authoring")
    observation["request_role"] = role
    with pytest.raises(ValueError, match="unsupported Greenfield model request role"):
        profiles.require_greenfield_model_profile_observation(**observation)


def test_unavailable_profile_remains_unsupported_and_review_cannot_extend_its_model_bound():
    profile_id = profiles.UNAVAILABLE_PROVIDER_PROFILE_ID
    profile = profiles.get_greenfield_model_profile(profile_id)
    assert profile_id not in PROFILE_IDS
    assert not profile.supported_success
    assert profile.model_timeout_seconds == 1.0
    assert profile.performance_target_seconds == 120.0
    assert profile.operational_timeout_seconds == 180.0
    observation = _observation(profile_id, "candidate_review")
    assert profiles.greenfield_model_profile_observation_issues(**observation) == ()
    observation["effective_timeout_seconds"] = 1.001
    with pytest.raises(ValueError, match="model window"):
        profiles.require_greenfield_model_profile_observation(**observation)


@pytest.mark.parametrize("profile_id", [
    "greenfield-standard-terra-low-complete-author-v11",
    "greenfield-rescue-terra-medium-complete-author-v11",
    "greenfield-deep-sol-high-complete-author-v11",
])
def test_retired_one_call_profiles_are_not_silently_upgraded(profile_id):
    with pytest.raises(ValueError, match="unsupported Greenfield model profile"):
        profiles.get_greenfield_model_profile(profile_id)


@pytest.mark.parametrize("profile_id", [
    "greenfield-standard-terra-low-complete-author-review-v12",
    "greenfield-rescue-terra-medium-complete-author-review-v12",
    "greenfield-deep-sol-high-complete-author-review-v12",
    "greenfield-standard-terra-low-complete-author-review-v13",
    "greenfield-rescue-terra-medium-complete-author-review-v13",
    "greenfield-deep-sol-high-complete-author-review-v13",
    "greenfield-standard-terra-low-complete-author-review-v14",
    "greenfield-rescue-terra-medium-complete-author-review-v14",
    "greenfield-deep-sol-high-complete-author-review-v14",
    "greenfield-standard-terra-low-complete-author-review-v15",
    "greenfield-rescue-terra-medium-complete-author-review-v15",
    "greenfield-deep-sol-high-complete-author-review-v15",
    "greenfield-standard-terra-low-complete-author-review-v16",
    "greenfield-rescue-terra-medium-complete-author-review-v16",
    "greenfield-deep-sol-high-complete-author-review-v16",
    "greenfield-standard-astra-medium-complete-author-review-v17",
])
def test_retired_consumer_budget_profiles_have_no_aliases(profile_id):
    with pytest.raises(ValueError, match="unsupported Greenfield model profile"):
        profiles.get_greenfield_model_profile(profile_id)
