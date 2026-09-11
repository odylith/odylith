from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import sys
from types import SimpleNamespace

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
from greenfield_model_profile_proof import model_profile_release_proof
from tests.greenfield_model_profile_test_support import (
    production_stage_observation as _stage_observation,
    sealed_profile_observation as _sealed_observation,
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
    assert standard.lower_capability is True
    rescue = get_greenfield_model_profile(RESCUE_PROFILE_ID)
    assert rescue.model == "gpt-5.6-terra"
    assert rescue.reasoning_effort == "medium"
    assert rescue.lower_capability is True
    deep = get_greenfield_model_profile(DEEP_PROFILE_ID)
    assert deep.model == "gpt-5.6-sol"
    assert deep.reasoning_effort == "high"
    assert [(profile.model_timeout_seconds, profile.consumer_budget_seconds) for profile in (standard, rescue, deep)] == [
        (55.0, 90.0), (80.0, 120.0), (105.0, 150.0),
    ]
    assert all(not hasattr(profile, "source_review_model") for profile in (standard, rescue, deep))
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
    assert "expected_source_review" not in evidence
    assert evidence["stage_observation"] == stage_observation
    assert evidence["stage_observation_summary"]["response_kind"] == "authored"
    assert evidence["maximum_semantic_model_calls"] == 2
    assert evidence["stage_observation_summary"]["semantic_model_call_count"] == 2
    assert set(evidence["stage_observation_summary"]["request_roles"]) == {
        "initial_authoring", "candidate_review",
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


def test_profile_evidence_rejects_obsolete_two_call_review_demoted_clarification() -> None:
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

    assert evidence["status"] == "failed"
    assert "clarification response must record exactly one semantic call" in evidence["issues"]
    assert "complete-author response must not record an intermediate review path" in evidence["issues"]


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
        ("response_version", "retained model response version is invalid"),
        ("response_kind", "retained model response kind is invalid"),
        ("bool_count", "retained semantic model call count is invalid"),
        ("one_call", "authored response must record exactly two semantic calls"),
        ("forged_initial_role", "retained initial_authoring request role is invalid"),
        ("forged_initial_model", "observed model does not match pinned Greenfield model profile"),
        ("initial_failure", "retained initial_authoring provider metadata records a failure"),
        ("initial_cap", "retained authoring timeout does not match the sealed model window"),
        ("initial_elapsed", "retained initial authoring elapsed time exceeds its timeout"),
        ("missing_initial", "retained initial authoring observation is missing"),
    ),
)
def test_stage_observation_rejects_malformed_forged_roles_and_timing(
    mutation: str, expected_issue: str,
) -> None:
    issues = model_stage_observation_issues(
        RESCUE_PROFILE_ID, observed=_sealed_observation(RESCUE_PROFILE_ID),
        stage_observation=_mutated_stage_observation(mutation),
    )
    assert expected_issue in issues


@pytest.mark.parametrize("response_kind", ["authored", "clarification_required"])
@pytest.mark.parametrize("field", ["source_review", "initial_response"])
def test_obsolete_review_metadata_is_rejected_even_with_a_one_call_claim(response_kind, field):
    stage = _stage_observation(RESCUE_PROFILE_ID, response_kind=response_kind)
    stage[field] = {}
    issues = model_stage_observation_issues(
        RESCUE_PROFILE_ID, observed=_sealed_observation(RESCUE_PROFILE_ID), stage_observation=stage,
    )
    assert "complete-author response must not record an intermediate review path" in issues


@pytest.mark.parametrize(("response_kind", "count"), [
    ("authored", 0), ("authored", 1), ("authored", 3),
    ("clarification_required", 0), ("clarification_required", 2), ("clarification_required", 3),
])
def test_outcomes_require_their_exact_role_count(response_kind, count):
    stage = _stage_observation(RESCUE_PROFILE_ID, response_kind=response_kind)
    stage["semantic_model_call_count"] = count
    issues = model_stage_observation_issues(
        RESCUE_PROFILE_ID, observed=_sealed_observation(RESCUE_PROFILE_ID), stage_observation=stage,
    )
    expected = ("authored response must record exactly two semantic calls"
                if response_kind == "authored"
                else "clarification response must record exactly one semantic call")
    assert expected in issues


@pytest.mark.parametrize("profile_id", MODEL_PROFILES)
@pytest.mark.parametrize("response_kind", ["authored", "clarification_required"])
def test_current_production_observations_qualify_without_mutation(profile_id, response_kind):
    stage = _stage_observation(profile_id, response_kind=response_kind)
    original = deepcopy(stage)
    assert model_stage_observation_issues(
        profile_id, observed=_sealed_observation(profile_id), stage_observation=stage,
    ) == ()
    assert stage == original


@pytest.mark.parametrize(("path", "value"), [
    (("candidate_review",), None),
    (("candidate_review", "dispatched"), False),
    (("candidate_review", "dispatched"), 1),
    (("candidate_review", "request_role"), "initial_authoring"),
    (("candidate_review", "profile_id"), STANDARD_PROFILE_ID),
    (("candidate_review", "model"), "gpt-5.6-terra"),
    (("candidate_review", "reasoning_effort"), "low"),
    (("candidate_review", "provider"), {}),
    (("candidate_review", "provider", "model"), "gpt-5.6-terra"),
    (("candidate_review", "provider", "reasoning_effort"), "low"),
    (("candidate_review", "provider", "provider"), "claude-cli"),
    (("candidate_review", "provider", "code"), "timeout"),
    (("candidate_review", "provider", "detail"), "unreported failure"),
    (("candidate_review", "provider", "code"), None),
    (("initial_authoring", "provider", "detail"), "unreported failure"),
    (("initial_authoring", "provider", "model"), "gpt-5.6-sol"),
    (("candidate_review", "response"), None),
    (("candidate_review", "response"), {"admissible": 1, "issues": []}),
    (("candidate_review", "response"), {"admissible": False, "issues": [{"path": "facts", "reason": "unsupported"}]}),
    (("candidate_review", "response"), {"admissible": True, "issues": [{}]}),
    (("candidate_review", "response"), {"admissible": True, "issues": [], "repair": {}}),
    (("candidate_review", "request", "source"), "Different source"),
    (("candidate_review", "request", "candidate", "accepted_source", "events"), []),
    (("candidate_review", "request", "candidate", "proposed_decisions", "provisional_design"), {}),
    (("candidate_review", "request", "role_definitions"), {}),
    (("candidate_review", "protocol"), "odylith.greenfield.exact-row-review.experimental.v1"),
    (("candidate_review", "final_candidate"), {}),
    (("initial_authoring", "unexpected_role"), {}),
    (("third_role",), {}),
    (("failure",), {}),
    (("request", "version"), "old"),
    (("request", "evidence"), "Different source"),
    (("request", "evidence"), None),
    (("response", "result", "facts", "title", "quote"), "Unsupported title"),
    (("response", "result", "provisional_design"), {}),
])
def test_current_review_rejects_missing_failed_stale_or_unbound_observations(path, value):
    stage = _stage_observation(RESCUE_PROFILE_ID)
    target = stage
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    original = deepcopy(stage)
    assert model_stage_observation_issues(
        RESCUE_PROFILE_ID, observed=_sealed_observation(RESCUE_PROFILE_ID), stage_observation=stage,
    )
    assert stage == original


@pytest.mark.parametrize("role", ["initial_authoring", "candidate_review"])
@pytest.mark.parametrize("field", ["elapsed_seconds", "timeout_seconds"])
@pytest.mark.parametrize("value", [None, True, "1.0", 0.0, -1.0, float("nan"), float("inf")])
def test_every_role_requires_positive_finite_numeric_timing(role, field, value):
    stage = _stage_observation(RESCUE_PROFILE_ID)
    stage[role][field] = value
    assert model_stage_observation_issues(
        RESCUE_PROFILE_ID, observed=_sealed_observation(RESCUE_PROFILE_ID), stage_observation=stage,
    )


@pytest.mark.parametrize("profile_id", MODEL_PROFILES)
@pytest.mark.parametrize("field", ["elapsed_seconds", "timeout_seconds"])
def test_review_cannot_exceed_its_cap_or_the_remaining_sealed_window(profile_id, field):
    profile = get_greenfield_model_profile(profile_id)
    for remaining in (2.0, 30.0):
        stage = _stage_observation(profile_id)
        stage["initial_authoring"]["elapsed_seconds"] = profile.model_timeout_seconds - remaining
        stage["candidate_review"]["timeout_seconds"] = min(remaining, profile.review_timeout_seconds)
        stage["candidate_review"][field] = min(remaining, profile.review_timeout_seconds) + 0.001
        assert model_stage_observation_issues(
            profile_id, observed=_sealed_observation(profile_id), stage_observation=stage,
        )


def test_review_elapsed_includes_setup_so_it_may_exceed_request_timeout():
    stage = _stage_observation(STANDARD_PROFILE_ID)
    stage["candidate_review"].update(timeout_seconds=18.0, elapsed_seconds=19.0)
    assert model_stage_observation_issues(
        STANDARD_PROFILE_ID, observed=_sealed_observation(STANDARD_PROFILE_ID), stage_observation=stage,
    ) == ()


@pytest.mark.parametrize(("field", "value"), [
    ("profile_id", STANDARD_PROFILE_ID), ("provider", "claude-cli"),
    ("model", "gpt-5.6-sol"), ("reasoning_effort", "low"),
    ("authoring_tier", "standard"), ("effective_timeout_seconds", 80.001),
    ("effective_timeout_seconds", None), ("effective_timeout_seconds", True),
])
def test_stage_checker_independently_rejects_false_sealed_profile(field, value):
    observed = _sealed_observation(RESCUE_PROFILE_ID)
    observed[field] = value
    assert model_stage_observation_issues(
        RESCUE_PROFILE_ID, observed=observed, stage_observation=_stage_observation(RESCUE_PROFILE_ID),
    )


@pytest.mark.parametrize("field", ["timeout_seconds", "elapsed_seconds"])
def test_review_budget_does_not_tolerate_sub_microsecond_overrun(field):
    stage = _stage_observation(STANDARD_PROFILE_ID)
    stage["candidate_review"][field] = 20.0000001
    assert model_stage_observation_issues(
        STANDARD_PROFILE_ID, observed=_sealed_observation(STANDARD_PROFILE_ID), stage_observation=stage,
    )


@pytest.mark.parametrize("profile_id", MODEL_PROFILES)
@pytest.mark.parametrize("elapsed", [None, True, "1.0", 0.0, -1.0, float("nan"), float("inf"), "at_cap"])
def test_profile_aggregate_rejects_non_numeric_missing_or_expired_consumer_time(profile_id, elapsed):
    stage = _stage_observation(profile_id)
    profile = get_greenfield_model_profile(profile_id)
    result = SimpleNamespace(
        name="timing control", status="passed", quality=SimpleNamespace(passed=True),
        proposal_seconds=profile.consumer_budget_seconds if elapsed == "at_cap" else elapsed,
        evidence={
            "case": {"expectation": "transaction_committed"},
            "model_profile": model_profile_evidence(
                profile_id, model_profile_environment(profile_id, {}),
                observed=_sealed_observation(profile_id), stage_observation=stage,
            ),
        },
    )
    proof = model_profile_release_proof((result,), require_complete=False)
    assert proof["status"] == "failed"
    assert any("installed latency proof" in issue for issue in proof["issues"])
    assert proof["profiles"][profile_id]["committed_positive_case_count"] == 0
    assert proof["profiles"][profile_id]["maximum_semantic_model_calls"] == 2


@pytest.mark.parametrize("mutation", ["review", "unsupported_dimension", "unsupported_quote", "empty_source"])
def test_clarification_remains_source_bound_and_has_no_review(mutation):
    stage = _stage_observation(RESCUE_PROFILE_ID, response_kind="clarification_required")
    if mutation == "review":
        stage["candidate_review"] = _stage_observation(RESCUE_PROFILE_ID)["candidate_review"]
    elif mutation == "unsupported_dimension":
        stage["response"]["result"]["clarification"]["material_dimension"] = "writing_style"
    elif mutation == "unsupported_quote":
        stage["response"]["result"]["consistency"] = {
            "status": "material_contradiction", "evidence_quotes": ["Invented one", "Invented two"],
        }
    else:
        stage["request"]["evidence"] = ""
    assert model_stage_observation_issues(
        RESCUE_PROFILE_ID, observed=_sealed_observation(RESCUE_PROFILE_ID), stage_observation=stage,
    )


def _mutated_stage_observation(mutation: str) -> dict[str, object]:
    stage = deepcopy(_stage_observation(RESCUE_PROFILE_ID))
    initial = stage["initial_authoring"]
    assert isinstance(initial, dict)
    if mutation in {"version", "authoring_version"}:
        stage[mutation] = "old"
    elif mutation == "response_version":
        stage["response"]["version"] = "old"
    elif mutation == "response_kind":
        stage["response"]["result"]["status"] = "invented"
    elif mutation == "bool_count":
        stage["semantic_model_call_count"] = True
    elif mutation == "one_call":
        stage["semantic_model_call_count"] = 1
    elif mutation == "forged_initial_role":
        initial["request_role"] = "source_review"
    elif mutation == "forged_initial_model":
        initial["model"] = "gpt-5.6-sol"
        initial["provider"]["model"] = "gpt-5.6-sol"
    elif mutation == "initial_failure":
        initial["provider"]["code"] = "provider_timeout"
    elif mutation == "initial_cap":
        initial["timeout_seconds"] = 60.0
    elif mutation == "initial_elapsed":
        initial["elapsed_seconds"] = 80.001
    elif mutation == "missing_initial":
        stage.pop("initial_authoring")
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
