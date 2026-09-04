from __future__ import annotations

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
from greenfield_model_profiles import profile_coverage
from greenfield_model_profiles import profile_counts
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
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


def test_profile_registry_pins_proven_standard_rescue_and_deep_requests() -> None:
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
    assert standard.reasoning_effort == "medium"
    assert standard.lower_capability is False
    rescue = get_greenfield_model_profile(RESCUE_PROFILE_ID)
    assert rescue.model == "gpt-5.6-sol"
    assert rescue.reasoning_effort == "high"
    assert rescue.lower_capability is False
    assert get_greenfield_model_profile(DEEP_PROFILE_ID).model == "gpt-5.6-sol"
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
    assert standard["ODYLITH_REASONING_CODEX_REASONING_EFFORT"] == "medium"
    assert standard["ODYLITH_REASONING_TIMEOUT_SECONDS"] == "55"
    assert rescue["ODYLITH_REASONING_MODEL"] == "gpt-5.6-sol"
    assert rescue["ODYLITH_REASONING_CODEX_REASONING_EFFORT"] == "high"
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
    observed = {
        "profile_id": STANDARD_PROFILE_ID,
        "provider": "codex-cli",
        "model": "gpt-5.6-terra",
        "reasoning_effort": "medium",
        "effective_timeout_seconds": 54.5,
        "authoring_tier": "standard",
    }

    evidence = model_profile_evidence(STANDARD_PROFILE_ID, env, observed=observed)

    assert evidence["status"] == "passed"
    assert evidence["profile_id"] == STANDARD_PROFILE_ID
    assert evidence["observed"] == observed
    require_greenfield_model_profile_observation(**observed)

    mismatched = model_profile_evidence(
        STANDARD_PROFILE_ID,
        env,
        observed={**observed, "model": "gpt-5.4"},
    )
    assert mismatched["status"] == "failed"
    assert mismatched["issues"] == ["observed model does not match pinned Greenfield model profile"]

    misconfigured = model_profile_evidence(
        STANDARD_PROFILE_ID,
        {**env, "ODYLITH_REASONING_MODEL": "gpt-5.4"},
        observed=observed,
    )
    assert misconfigured["status"] == "failed"
    assert misconfigured["issues"] == [
        "configured model does not match the assigned release profile"
    ]


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
