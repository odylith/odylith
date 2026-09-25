from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
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
from greenfield_model_profile_proof import authored_model_result_binding_issues
from greenfield_model_profile_proof import model_profile_release_proof
from greenfield_model_profile_proof import sealed_model_profile_observation
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
    assert standard.model == "gpt-6-astra"
    assert standard.reasoning_effort == "medium"
    assert standard.participant_model == "gpt-6-astra"
    assert standard.participant_reasoning_effort == "medium"
    assert standard.lower_capability is False
    rescue = get_greenfield_model_profile(RESCUE_PROFILE_ID)
    assert rescue.model == "gpt-5.6-luna"
    assert rescue.reasoning_effort == "medium"
    assert rescue.lower_capability is True
    deep = get_greenfield_model_profile(DEEP_PROFILE_ID)
    assert deep.model == "gpt-5.6-sol"
    assert deep.reasoning_effort == "high"
    assert [
        (profile.model_timeout_seconds, profile.performance_target_seconds, profile.operational_timeout_seconds)
        for profile in (standard, rescue, deep)
    ] == [
        (165.0, 90.0, 180.0), (165.0, 120.0, 180.0), (165.0, 150.0, 180.0),
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
    assert standard["ODYLITH_REASONING_MODEL"] == "gpt-6-astra"
    assert standard["ODYLITH_REASONING_CODEX_REASONING_EFFORT"] == "medium"
    assert standard["ODYLITH_REASONING_TIMEOUT_SECONDS"] == "165"
    assert rescue["ODYLITH_REASONING_MODEL"] == "gpt-5.6-luna"
    assert rescue["ODYLITH_REASONING_CODEX_REASONING_EFFORT"] == "medium"
    assert rescue["ODYLITH_REASONING_TIMEOUT_SECONDS"] == "165"
    assert deep["ODYLITH_REASONING_MODEL"] == "gpt-5.6-sol"
    assert deep["ODYLITH_REASONING_CODEX_REASONING_EFFORT"] == "high"
    assert deep["ODYLITH_REASONING_TIMEOUT_SECONDS"] == "165"
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
    assert evidence["sealed_request_roles"] == [
        "participant_selection", "remaining_candidate_authoring",
    ]
    assert evidence["lower_capability_scope"] == "not_applicable"
    assert "expected_source_review" not in evidence
    assert evidence["stage_observation"] == stage_observation
    assert evidence["stage_observation_summary"]["response_kind"] == "authored"
    assert evidence["maximum_semantic_model_calls"] == 5
    assert evidence["stage_observation_summary"]["semantic_model_call_count"] == 3
    assert set(evidence["stage_observation_summary"]["request_roles"]) == {
        "participant_selection", "remaining_candidate_authoring", "candidate_review",
    }
    for role, role_observation in observed.items():
        require_greenfield_model_profile_observation(
            **role_observation, request_role=role,
        )

    mismatched = model_profile_evidence(
        STANDARD_PROFILE_ID,
        env,
        observed={
            **observed,
            "remaining_candidate_authoring": {
                **observed["remaining_candidate_authoring"], "model": "gpt-5.4",
            },
        },
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


def test_sealed_observation_reads_both_exact_envelope_roles_without_flat_migration() -> None:
    observed = _sealed_observation(STANDARD_PROFILE_ID)
    proposal = {
        "product_intent_authority": {
            "operating_envelope": {"model_contract": {"observed": observed}}
        }
    }

    assert sealed_model_profile_observation(proposal=proposal) == observed

    flat = observed["remaining_candidate_authoring"]
    extracted = sealed_model_profile_observation(
        proposal={
            "product_intent_authority": {
                "operating_envelope": {"model_contract": {"observed": flat}}
            }
        }
    )
    assert extracted != observed
    assert model_profile_evidence(
        STANDARD_PROFILE_ID,
        model_profile_environment(STANDARD_PROFILE_ID, {}),
        observed=extracted,
        stage_observation=_stage_observation(STANDARD_PROFILE_ID),
    )["status"] == "failed"


def test_sealed_observation_preserves_unsupported_fields_for_closed_evidence_check() -> None:
    observed = _sealed_observation(STANDARD_PROFILE_ID)
    forged = deepcopy(observed)
    forged["participant_selection"]["extra"] = "must not be normalized away"
    forged["legacy_role"] = deepcopy(forged["remaining_candidate_authoring"])
    proposal = {
        "product_intent_authority": {
            "operating_envelope": {"model_contract": {"observed": forged}}
        }
    }

    extracted = sealed_model_profile_observation(proposal=proposal)
    evidence = model_profile_evidence(
        STANDARD_PROFILE_ID,
        model_profile_environment(STANDARD_PROFILE_ID, {}),
        observed=extracted,
        stage_observation=_stage_observation(STANDARD_PROFILE_ID),
    )

    assert extracted == forged
    assert evidence["status"] == "failed"
    assert "sealed model observations have missing or unsupported roles" in evidence["issues"]
    assert (
        "sealed participant_selection observation has missing or unsupported fields"
        in evidence["issues"]
    )


def test_authored_private_result_binds_to_actual_admitted_consumer_receipt() -> None:
    stage = _stage_observation(STANDARD_PROFILE_ID)
    source = stage["request"]["evidence"]
    create_payload = _create_payload_for_stage(stage, source=source)

    assert authored_model_result_binding_issues(
        stage_observation=stage,
        create_payload=create_payload,
        expected_source=source,
    ) == ()


@pytest.mark.parametrize(
    ("mutation", "expected_issue"),
    (
        ("expected_source", "retained private author request does not match the expected source"),
        ("private_candidate", "retained private reviewed candidate does not match the sealed receipt"),
        ("missing_private_review", "retained private candidate review is missing"),
        ("missing_receipt", "sealed candidate-review receipt is missing"),
        ("denied_receipt", "sealed candidate-review receipt is not admitted"),
        ("source_hash", "sealed candidate-review source hash does not match the expected source"),
        ("candidate_hash", "sealed candidate-review candidate hash is invalid"),
    ),
)
def test_authored_private_result_binding_fails_closed(mutation, expected_issue) -> None:
    stage = _stage_observation(STANDARD_PROFILE_ID)
    source = stage["request"]["evidence"]
    create_payload = _create_payload_for_stage(stage, source=source)
    expected_source = source
    receipt = create_payload["commit_manifest"]["model_authoring"]["candidate_review"]
    if mutation == "expected_source":
        expected_source = source + " changed"
    elif mutation == "private_candidate":
        stage["candidate_review"]["request"]["candidate"]["extra"] = "split proof"
    elif mutation == "missing_private_review":
        stage.pop("candidate_review")
    elif mutation == "missing_receipt":
        create_payload["commit_manifest"]["model_authoring"].pop("candidate_review")
    elif mutation == "denied_receipt":
        receipt["status"] = "denied"
    elif mutation == "source_hash":
        receipt["source_sha256"] = "0" * 64
    elif mutation == "candidate_hash":
        receipt["candidate_sha256"] = "missing"
    else:
        raise AssertionError(f"unknown mutation: {mutation}")

    issues = authored_model_result_binding_issues(
        stage_observation=stage,
        create_payload=create_payload,
        expected_source=expected_source,
    )

    assert expected_issue in issues


def test_profile_evidence_accepts_two_call_clarification_without_review() -> None:
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
    assert evidence["stage_observation_summary"]["semantic_model_call_count"] == 2
    assert set(evidence["stage_observation_summary"]["request_roles"]) == {
        "participant_selection", "remaining_candidate_authoring",
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
    assert "retained model authoring observation version is invalid" in evidence["issues"]
    assert "participant-first response must not record a legacy author path" in evidence["issues"]


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
        ("two_calls", "authored response must record exactly three or five semantic calls"),
        ("forged_participant_role", "retained participant_selection request role is invalid"),
        ("forged_participant_model", "observed model does not match pinned Greenfield model profile"),
        ("participant_failure", "retained participant_selection provider metadata records a failure"),
        ("participant_cap", "retained participant_selection timeout does not match its sealed observation"),
        ("participant_elapsed", "retained remaining_candidate_authoring timeout exceeds the remaining model window"),
        ("missing_participant", "retained participant_selection observation has missing or unsupported fields"),
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
    assert "participant-first response must not record a legacy author path" in issues


@pytest.mark.parametrize(("response_kind", "count"), [
    ("authored", 0), ("authored", 1), ("authored", 2), ("authored", 4),
    ("authored", True), ("authored", 3.0),
    ("clarification_required", 0), ("clarification_required", 1),
    ("clarification_required", 3), ("clarification_required", True),
    ("clarification_required", 2.0),
])
def test_outcomes_require_their_exact_role_count(response_kind, count):
    stage = _stage_observation(RESCUE_PROFILE_ID, response_kind=response_kind)
    stage["semantic_model_call_count"] = count
    issues = model_stage_observation_issues(
        RESCUE_PROFILE_ID, observed=_sealed_observation(RESCUE_PROFILE_ID), stage_observation=stage,
    )
    expected = ("authored response must record exactly three or five semantic calls"
                if response_kind == "authored"
                else "clarification response must record exactly two semantic calls")
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


@pytest.mark.parametrize("profile_id", MODEL_PROFILES)
def test_one_review_guided_revision_qualifies_as_a_five_call_observation(profile_id):
    stage = _stage_observation(profile_id, revised=True)

    assert stage["semantic_model_call_count"] == 5
    assert model_stage_observation_issues(
        profile_id,
        observed=_sealed_observation(profile_id),
        stage_observation=stage,
    ) == ()
    evidence = model_profile_evidence(
        profile_id,
        model_profile_environment(profile_id, {}),
        observed=_sealed_observation(profile_id),
        stage_observation=stage,
    )
    assert evidence["status"] == "passed", evidence["issues"]
    assert set(evidence["stage_observation_summary"]["request_roles"]) == {
        "participant_selection",
        "remaining_candidate_authoring",
        "rejected_candidate_review",
        "candidate_revision",
        "candidate_review",
    }


def test_revision_observation_rejects_a_witness_not_bound_to_the_revision_request():
    stage = _stage_observation(STANDARD_PROFILE_ID, revised=True)
    stage["candidate_revision"]["request"]["review_issue"]["reason"] = "Different issue."

    assert (
        "retained candidate revision fails source-bound replacement validation"
        in model_stage_observation_issues(
            STANDARD_PROFILE_ID,
            observed=_sealed_observation(STANDARD_PROFILE_ID),
            stage_observation=stage,
        )
    )


@pytest.mark.parametrize(("path", "value"), [
    (("candidate_review",), None),
    (("candidate_review", "dispatched"), False),
    (("candidate_review", "dispatched"), 1),
    (("candidate_review", "request_role"), "remaining_candidate_authoring"),
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
    (("participant_selection", "provider", "detail"), "unreported failure"),
    (("participant_selection", "provider", "model"), "gpt-5.6-sol"),
    (("participant_selection", "request", "source"), "Different source"),
    (("participant_selection", "response", "human_actors", 0, "quote"), "Invented actor"),
    (("participant_selection", "resolved", 0, "source_start_byte"), 999),
    (("remaining_candidate_authoring", "request", "frozen_human_actors"), []),
    (("remaining_candidate_authoring", "response", "result", "facts", "human_actors"), []),
    (("candidate_review", "response"), None),
    (("candidate_review", "response"), {"admissible": 1, "issues": []}),
    (("candidate_review", "response"), {"admissible": False, "issues": [{"path": "facts", "reason": "unsupported"}]}),
    (("candidate_review", "response"), {"admissible": True, "issues": [{}]}),
    (("candidate_review", "response"), {"admissible": True, "issues": [], "repair": {}}),
    (("candidate_review", "request", "source"), "Different source"),
    (("candidate_review", "request", "candidate", "accepted_source", "events"), []),
    (("candidate_review", "request", "candidate", "proposed_decisions", "provisional_design"), {}),
    (("candidate_review", "request", "role_definitions"), {}),
    (("candidate_review", "request", "resolved_source_custody"), []),
    (("candidate_review", "request", "resolved_source_custody", 0, "source_start_byte"), 999),
    (("candidate_review", "request", "resolved_source_custody", 0, "context_after"), "Forged context"),
    (("candidate_review", "protocol"), "odylith.greenfield.exact-row-review.experimental.v1"),
    (("candidate_review", "final_candidate"), {}),
    (("participant_selection", "unexpected_role"), {}),
    (("third_role",), {}),
    (("failure",), {}),
    (("request", "version"), "old"),
    (("request", "evidence"), "Different source"),
    (("request", "evidence"), None),
    (("joined_candidate", "result", "facts", "title", "quote"), "Unsupported title"),
    (("joined_candidate", "result", "provisional_design"), {}),
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


@pytest.mark.parametrize(
    "role", ["participant_selection", "remaining_candidate_authoring", "candidate_review"]
)
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
def test_review_cannot_exceed_the_remaining_sealed_window(profile_id, field):
    profile = get_greenfield_model_profile(profile_id)
    for remaining in (2.0, 30.0):
        stage = _stage_observation(profile_id)
        stage["participant_selection"]["elapsed_seconds"] = (
            profile.model_timeout_seconds - remaining - 10.0
        )
        stage["remaining_candidate_authoring"]["elapsed_seconds"] = 10.0
        stage["candidate_review"]["timeout_seconds"] = remaining
        stage["candidate_review"][field] = remaining + 0.001
        assert model_stage_observation_issues(
            profile_id, observed=_sealed_observation(profile_id), stage_observation=stage,
        )


def test_review_elapsed_includes_setup_and_must_fit_request_timeout():
    stage = _stage_observation(STANDARD_PROFILE_ID)
    stage["candidate_review"].update(timeout_seconds=18.0, elapsed_seconds=19.0)
    assert "retained candidate review elapsed time exceeds its timeout" in model_stage_observation_issues(
        STANDARD_PROFILE_ID, observed=_sealed_observation(STANDARD_PROFILE_ID), stage_observation=stage,
    )


@pytest.mark.parametrize(("role", "field", "value"), [
    ("participant_selection", "profile_id", STANDARD_PROFILE_ID),
    ("participant_selection", "provider", "claude-cli"),
    ("participant_selection", "model", "gpt-5.6-sol"),
    ("participant_selection", "reasoning_effort", "low"),
    ("remaining_candidate_authoring", "authoring_tier", "standard"),
    ("remaining_candidate_authoring", "effective_timeout_seconds", 165.001),
    ("remaining_candidate_authoring", "effective_timeout_seconds", None),
    ("remaining_candidate_authoring", "effective_timeout_seconds", True),
])
def test_stage_checker_independently_rejects_false_sealed_profile(role, field, value):
    observed = _sealed_observation(RESCUE_PROFILE_ID)
    observed[role][field] = value
    assert model_stage_observation_issues(
        RESCUE_PROFILE_ID, observed=observed, stage_observation=_stage_observation(RESCUE_PROFILE_ID),
    )


@pytest.mark.parametrize("field", ["timeout_seconds", "elapsed_seconds"])
def test_review_budget_does_not_tolerate_sub_microsecond_overrun(field):
    stage = _stage_observation(STANDARD_PROFILE_ID)
    stage["candidate_review"][field] = (
        get_greenfield_model_profile(STANDARD_PROFILE_ID).model_timeout_seconds
        - stage["participant_selection"]["elapsed_seconds"]
        - stage["remaining_candidate_authoring"]["elapsed_seconds"]
        + 0.0000001
    )
    assert model_stage_observation_issues(
        STANDARD_PROFILE_ID, observed=_sealed_observation(STANDARD_PROFILE_ID), stage_observation=stage,
    )


def test_review_above_old_stage_cap_is_valid_inside_remaining_shared_budget():
    stage = _stage_observation(STANDARD_PROFILE_ID)
    stage["candidate_review"].update(timeout_seconds=30.0, elapsed_seconds=23.0)
    assert model_stage_observation_issues(
        STANDARD_PROFILE_ID, observed=_sealed_observation(STANDARD_PROFILE_ID), stage_observation=stage,
    ) == ()


@pytest.mark.parametrize("profile_id", MODEL_PROFILES)
@pytest.mark.parametrize("elapsed", [None, True, "1.0", 0.0, -1.0, float("nan"), float("inf"), "at_cap"])
def test_profile_aggregate_rejects_non_numeric_missing_or_expired_consumer_time(profile_id, elapsed):
    stage = _stage_observation(profile_id)
    profile = get_greenfield_model_profile(profile_id)
    result = SimpleNamespace(
        name="timing control", status="passed", quality=SimpleNamespace(passed=True),
        proposal_seconds=profile.operational_timeout_seconds if elapsed == "at_cap" else elapsed,
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
    assert any("operational-timeout proof" in issue for issue in proof["issues"])
    assert proof["profiles"][profile_id]["committed_positive_case_count"] == 0
    assert proof["profiles"][profile_id]["maximum_semantic_model_calls"] == 5


@pytest.mark.parametrize("profile_id", MODEL_PROFILES)
def test_profile_aggregate_accepts_exact_participant_first_observations(profile_id):
    stage = _stage_observation(profile_id)
    result = SimpleNamespace(
        name="participant-first control", status="passed",
        quality=SimpleNamespace(passed=True), proposal_seconds=80.0,
        evidence={
            "case": {"expectation": "transaction_committed"},
            "model_profile": model_profile_evidence(
                profile_id, model_profile_environment(profile_id, {}),
                observed=_sealed_observation(profile_id), stage_observation=stage,
            ),
        },
    )

    proof = model_profile_release_proof((result,), require_complete=False)

    assert proof["status"] == "passed", proof["issues"]
    assert proof["profiles"][profile_id]["status"] == "passed"
    assert proof["profiles"][profile_id]["committed_positive_case_count"] == 1


@pytest.mark.parametrize("mutation", ["review", "unsupported_dimension", "unsupported_quote", "empty_source"])
def test_clarification_remains_source_bound_and_has_no_review(mutation):
    stage = _stage_observation(RESCUE_PROFILE_ID, response_kind="clarification_required")
    if mutation == "review":
        stage["candidate_review"] = _stage_observation(RESCUE_PROFILE_ID)["candidate_review"]
    elif mutation == "unsupported_dimension":
        stage["remaining_candidate_authoring"]["response"]["result"]["clarification"][
            "material_dimension"
        ] = "writing_style"
    elif mutation == "unsupported_quote":
        stage["remaining_candidate_authoring"]["response"]["result"]["consistency"] = {
            "status": "material_contradiction", "evidence_quotes": ["Invented one", "Invented two"],
        }
    else:
        stage["request"]["evidence"] = ""
    assert model_stage_observation_issues(
        RESCUE_PROFILE_ID, observed=_sealed_observation(RESCUE_PROFILE_ID), stage_observation=stage,
    )


def _mutated_stage_observation(mutation: str) -> dict[str, object]:
    stage = deepcopy(_stage_observation(RESCUE_PROFILE_ID))
    participant = stage["participant_selection"]
    assert isinstance(participant, dict)
    if mutation in {"version", "authoring_version"}:
        stage[mutation] = "old"
    elif mutation == "response_version":
        stage["remaining_candidate_authoring"]["response"]["version"] = "old"
    elif mutation == "response_kind":
        stage["remaining_candidate_authoring"]["response"]["result"]["status"] = "invented"
    elif mutation == "bool_count":
        stage["semantic_model_call_count"] = True
    elif mutation == "two_calls":
        stage["semantic_model_call_count"] = 2
    elif mutation == "forged_participant_role":
        participant["request_role"] = "source_review"
    elif mutation == "forged_participant_model":
        participant["model"] = "gpt-5.6-sol"
        participant["provider"]["model"] = "gpt-5.6-sol"
    elif mutation == "participant_failure":
        participant["provider"]["code"] = "provider_timeout"
    elif mutation == "participant_cap":
        participant["timeout_seconds"] = 60.0
    elif mutation == "participant_elapsed":
        participant["elapsed_seconds"] = 165.001
    elif mutation == "missing_participant":
        stage.pop("participant_selection")
    else:
        raise AssertionError(f"unknown mutation: {mutation}")
    return stage


def _create_payload_for_stage(stage: dict[str, object], *, source: str) -> dict[str, object]:
    review = stage["candidate_review"]
    assert isinstance(review, dict)
    request = review["request"]
    assert isinstance(request, dict)
    candidate = request["candidate"]
    encoded = json.dumps(
        candidate,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return {
        "commit_manifest": {
            "model_authoring": {
                "candidate_review": {
                    "version": "odylith.greenfield.candidate-review.v3",
                    "status": "admitted",
                    "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                    "candidate_sha256": hashlib.sha256(encoded).hexdigest(),
                    "product_facts_sha256": "2" * 64,
                    "elapsed_seconds": 1.0,
                    "model_profile": {},
                }
            }
        }
    }


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
