"""Detached release-evidence profile pins; never runtime semantic authority."""

from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence import (
    greenfield_model_profile_contract as profiles,
)


def _observation(profile_id: str) -> dict[str, object]:
    profile = profiles.get_greenfield_model_profile(profile_id)
    return {
        "profile_id": profile_id,
        "provider": profile.provider,
        "model": profile.model,
        "reasoning_effort": profile.reasoning_effort,
        "effective_timeout_seconds": profile.model_timeout_seconds,
        "authoring_tier": profile.repair_tier,
        "request_role": "candidate_authoring",
    }


def test_v25_profiles_are_detached_single_candidate_release_evidence() -> None:
    assert profiles.GREENFIELD_MODEL_PROFILE_CONTRACT_VERSION == (
        "odylith.greenfield.model-profile-contract.v25"
    )
    assert profiles.supported_greenfield_model_profile_ids() == (
        profiles.STANDARD_PROFILE_ID,
    )
    assert profiles.declared_greenfield_model_profile_ids() == (
        profiles.STANDARD_PROFILE_ID,
        profiles.RESCUE_PROFILE_ID,
        profiles.DEEP_PROFILE_ID,
    )
    assert [
        (
            profile.model,
            profile.reasoning_effort,
            profile.performance_target_seconds,
            profile.model_timeout_seconds,
        )
        for profile in map(
            profiles.get_greenfield_model_profile,
            profiles.declared_greenfield_model_profile_ids(),
        )
    ] == [
        ("gpt-6-astra", "medium", 90.0, 300.0),
        ("gpt-5.6-luna", "medium", 120.0, 165.0),
        ("gpt-5.6-sol", "high", 150.0, 165.0),
    ]


def test_only_candidate_authoring_is_a_declared_release_evidence_role() -> None:
    observation = _observation(profiles.STANDARD_PROFILE_ID)
    assert profiles.greenfield_model_profile_observation_issues(**observation) == ()
    assert profiles.require_greenfield_model_profile_observation(**observation).profile_id == (
        profiles.STANDARD_PROFILE_ID
    )

    with pytest.raises(ValueError, match="unsupported Greenfield model request role"):
        profiles.require_greenfield_model_profile_observation(
            **{**observation, "request_role": "second_semantic_authority"}
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("provider", "other-provider"),
        ("model", "other-model"),
        ("reasoning_effort", "other-effort"),
        ("effective_timeout_seconds", 0),
        ("effective_timeout_seconds", 301.0),
        ("authoring_tier", "rescue"),
    ),
)
def test_candidate_authoring_release_observation_fails_closed_on_drift(
    field: str,
    value: object,
) -> None:
    observation = _observation(profiles.STANDARD_PROFILE_ID)
    observation[field] = value
    with pytest.raises(ValueError, match="pinned Greenfield model"):
        profiles.require_greenfield_model_profile_observation(**observation)


@pytest.mark.parametrize("tier", ("rescue", "deep", "premium", "deep-repair", "ci"))
def test_control_and_diagnostic_tiers_are_not_runtime_success_routes(tier: str) -> None:
    with pytest.raises(ValueError, match="not release-qualified"):
        profiles.model_profile_id_for_repair_tier(tier)


@pytest.mark.parametrize(
    "profile_id",
    (
        "greenfield-retired-composition-v0",
        "greenfield-standard-host-candidate-astra-medium-v20",
        "greenfield-legacy-authoring-v0",
    ),
)
def test_retired_composition_profiles_have_no_compatibility_alias(profile_id: str) -> None:
    with pytest.raises(ValueError, match="unsupported Greenfield model profile"):
        profiles.get_greenfield_model_profile(profile_id)


def test_standard_budget_revision_keeps_control_budgets_and_completion_reserve() -> None:
    assert profiles.GREENFIELD_COMPLETION_RESERVE_SECONDS == 15.0
    assert profiles.STANDARD_PROFILE_ID.endswith("-v21")
    assert profiles.get_greenfield_model_profile(profiles.STANDARD_PROFILE_ID).operational_timeout_seconds == 315.0
    assert profiles.get_greenfield_model_profile(profiles.RESCUE_PROFILE_ID).operational_timeout_seconds == 180.0
    assert profiles.get_greenfield_model_profile(profiles.DEEP_PROFILE_ID).operational_timeout_seconds == 180.0
