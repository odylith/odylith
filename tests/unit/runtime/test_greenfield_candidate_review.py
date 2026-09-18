"""Complete-candidate admission: immutable inputs, one call, shared deadlines."""

from copy import deepcopy
import hashlib
import json

import pytest

from odylith.runtime.domain_intelligence import greenfield_candidate_review as review
from odylith.runtime.domain_intelligence import greenfield_model_intent_authoring as author
from odylith.runtime.domain_intelligence import greenfield_participant_first_authoring as participant_authoring
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import STANDARD_PROFILE_ID
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    AdmittingReviewProvider,
    RemainingCandidateProvider,
    StructuredAuthoringProvider,
    authored_response,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _source, _response


class Clock:
    value = 0.0

    def __call__(self):
        return self.value


class Reviewer(StructuredAuthoringProvider):
    def __init__(self, response, clock, duration=0.0, mutation=None):
        super().__init__(response)
        self.clock, self.duration, self.mutation = clock, duration, mutation

    def generate_structured(self, *, request):
        self.clock.value += self.duration
        if self.mutation:
            self.mutation(request.prompt_payload)
        return super().generate_structured(request=request)


def run_review(provider, clock, *, deadline=55.0, observation=None, factory=None):
    source = _source()
    authored = author.validate_greenfield_authoring_response(
        _response(source), evidence_text=source, elapsed_seconds=0.0,
        provider={"provider": "codex-cli", "model": "gpt-5.6-terra", "reasoning_effort": "low"},
        profile_id=STANDARD_PROFILE_ID, effective_timeout_seconds=55.0,
        semantic_model_call_count=2,
    )
    return review.review_greenfield_candidate(
        evidence_text=source, candidate=_response(source)["result"], source_spans=authored.source_spans,
        profile_id=STANDARD_PROFILE_ID, provider_factory=factory or (lambda: provider),
        deadline=deadline, clock=clock,
        observation=observation if observation is not None else {},
    )


def test_partition_preserves_every_value_and_binds_complete_candidate():
    source = _source()
    candidate = _response(source)["result"]
    original = deepcopy(candidate)
    spans = author.validate_greenfield_authoring_response(
        _response(source), evidence_text=source, elapsed_seconds=0.0,
        provider={}, profile_id=STANDARD_PROFILE_ID, effective_timeout_seconds=55.0,
        semantic_model_call_count=2,
    ).source_spans
    payload = review.candidate_review_payload(source, candidate, source_spans=spans)
    assert {**payload["candidate"]["accepted_source"], **payload["candidate"]["proposed_decisions"]} == original
    assert payload["source"] == source
    assert payload["resolved_source_custody"]
    state_object_role = payload["role_definitions"]["state_object"]
    assert state_object_role == review.STATE_OBJECT_ROLE_DEFINITION
    assert state_object_role == author._AUTHORED_FACTS_SCHEMA["properties"][
        "state_object"
    ]["description"]
    assert "performer merely because it performs" in state_object_role
    proof_role = payload["role_definitions"]["proof_boundary"]
    assert proof_role == review.PROOF_BOUNDARY_ROLE_DEFINITION
    assert proof_role == author._AUTHORED_FACTS_SCHEMA["properties"]["proof_boundary"]["description"]
    assert "phrase or complete statement" in proof_role
    assert "do not reject a longer faithful span" in proof_role
    assert "purpose without an identified result is not proof" in proof_role
    internal_role = payload["role_definitions"]["internal_systems"]
    assert internal_role == review.INTERNAL_SYSTEM_ROLE_DEFINITION
    assert internal_role == author._AUTHORED_FACTS_SCHEMA["properties"]["internal_systems"]["description"]
    assert "same owner, not a new component" in internal_role
    assert "Do not infer product ownership from a mere mention" in internal_role
    constraint_role = payload["role_definitions"]["operational_constraints"]
    assert constraint_role == review.OPERATIONAL_CONSTRAINT_ROLE_DEFINITION
    assert constraint_role == author._AUTHORED_FACTS_SCHEMA["properties"][
        "operational_constraints"
    ]["description"]
    assert "Each quote is projected independently" in constraint_role
    assert "governed subject" in constraint_role
    assert "required, prohibited or permitted behavior" in constraint_role
    assert "condition or scope" in constraint_role
    assert "contiguous source context before or after" in constraint_role
    assert "Do not require an explicit subject" in constraint_role
    assert "Do not turn an activity or output purpose into a person." in payload["role_definitions"]["customer"]
    clock = Clock()
    provider = Reviewer({"admissible": True, "issues": []}, clock, 7.0)
    receipt = run_review(provider, clock)
    assert candidate == original
    assert receipt["source_sha256"] == hashlib.sha256(source.encode()).hexdigest()
    encoded = json.dumps(payload["candidate"], sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    assert receipt["candidate_sha256"] == hashlib.sha256(encoded).hexdigest()
    assert receipt["elapsed_seconds"] == 7.0
    assert provider.calls == 1
    assert provider.requests[0].schema_name == "greenfield_candidate_review"


def test_review_request_makes_selected_source_location_authoritative():
    clock = Clock()
    provider = Reviewer({"admissible": True, "issues": []}, clock)
    run_review(provider, clock)

    prompt = provider.requests[0].system_prompt
    assert "resolved_source_custody is the authoritative resolution" in prompt
    assert "Judge its semantic role at those exact byte offsets and surrounding context" in prompt
    assert "support from another occurrence of the same quote does not cure" in prompt


def test_human_subject_state_object_keeps_source_and_performer_custody_separate():
    source = "Harbor intake helps city staff register displaced residents."
    event = "city staff register displaced residents"
    intent = {
        "title": "Harbor intake",
        "product_story": source[:-1],
        "state_object": "displaced residents",
        "first_path": event,
        "proof_boundary": "displaced residents",
        "customer": "city staff",
        "human_actors": ["city staff", "displaced residents"],
        "assumptions": [
            {"applies_to": "problem", "statement": "Registration needs one intake path."},
            {"applies_to": "opportunity", "statement": "One intake path can reduce handoffs."},
            {"applies_to": "product_view", "statement": "Staff use one intake view."},
        ],
    }
    response = authored_response(
        intent,
        evidence_text=source,
        first_path_relations=[{
            "actor_kind": "human",
            "actor_fact_quote": "city staff",
            "event_quote": event,
            "action_verb_quote": "register",
            "target_quote": "displaced residents",
            "visible_result_quote": "displaced residents",
        }],
    )
    authored = author.validate_greenfield_authoring_response(
        response,
        evidence_text=source,
        elapsed_seconds=0.0,
        provider={},
        profile_id=STANDARD_PROFILE_ID,
        effective_timeout_seconds=55.0,
        semantic_model_call_count=2,
    )
    payload = review.candidate_review_payload(
        source,
        response["result"],
        source_spans=authored.source_spans,
    )

    accepted = payload["candidate"]["accepted_source"]
    assert accepted["facts"]["state_object"] == {
        "quote": "displaced residents",
        "prefix": "",
        "anchor_occurrence": 1,
    }
    assert accepted["events"][0] == {
        "actor_fact_quote": "city staff",
        "action_quote": "register",
        "target_quote": "displaced residents",
    }
    assert accepted["events"][0]["actor_fact_quote"] != accepted["facts"]["state_object"]["quote"]
    assert any(
        row["field"] == "state_object" and row["quote"] == "displaced residents"
        for row in payload["resolved_source_custody"]
    )


@pytest.mark.parametrize("constraint", [
    "The oversight team consists of auditors. They have read-only access.",
    "Auditors must never alter requests.",
    "The oversight team has read-only access only during intake.",
    "Never delete published notices.",
])
def test_self_contained_constraints_keep_exact_custody_without_a_new_shape(constraint):
    source = _source() + " " + constraint
    response = _response(_source())
    response["result"]["facts"]["operational_constraints"].append(
        {"quote": constraint, "occurrence": 1}
    )
    original = deepcopy(response)
    authored = author.validate_greenfield_authoring_response(
        response, evidence_text=source, elapsed_seconds=0.0,
        provider={}, profile_id=STANDARD_PROFILE_ID, effective_timeout_seconds=165.0,
        semantic_model_call_count=2,
    )
    assert authored.intent["operational_constraints"][-1] == constraint
    payload = review.candidate_review_payload(
        source, response["result"], source_spans=authored.source_spans,
    )
    constraint_spans = [row for row in payload["resolved_source_custody"]
                        if row["field"] == "operational_constraints"]
    span = constraint_spans[-1]
    assert span["quote"] == constraint
    assert source.encode()[span["source_start_byte"]:span["source_end_byte"]] == constraint.encode()
    schema = deepcopy(author._AUTHORED_FACTS_SCHEMA["properties"]["operational_constraints"])
    schema.pop("description")
    assert schema == author._TYPED_FACTS_SCHEMA["properties"]["operational_constraints"]
    assert response == original


def test_unknown_authority_is_not_silently_dropped():
    candidate = _response(_source())["result"]
    candidate["unclassified_authority"] = {}
    with pytest.raises(ValueError, match="authority"):
        review.candidate_review_payload(_source(), candidate, source_spans=())


def _span(source, quote, *, field="first_path", row=1, start=None):
    encoded, quoted = source.encode(), quote.encode()
    start = encoded.find(quoted) if start is None else start
    return {
        "section_key": field, "row_index": row, "text": quote,
        "source_start_byte": start, "source_end_byte": start + len(quoted),
    }


def test_utf8_context_is_bounded_by_characters_while_coordinates_remain_bytes():
    source = "é" * 70 + " target " + "文" * 70
    payload = review.candidate_review_payload(
        source, _response(_source())["result"], source_spans=(_span(source, "target"),),
    )
    custody = payload["resolved_source_custody"][0]
    assert custody["source_start_byte"] == len(("é" * 70 + " ").encode())
    assert custody["context_before"] == "é" * 63 + " "
    assert custody["context_after"] == " " + "文" * 63


def test_overlapping_source_spans_remain_distinct_context_rows():
    source = "prefix abcde suffix"
    first = _span(source, "abcd", row=1)
    second = _span(source, "cde", row=2, start=first["source_start_byte"] + 2)
    payload = review.candidate_review_payload(
        source, _response(_source())["result"], source_spans=(first, second),
    )
    assert [(row["row"], row["quote"]) for row in payload["resolved_source_custody"]] == [
        (1, "abcd"), (2, "cde"),
    ]


@pytest.mark.parametrize("mutation", [
    {"source_start_byte": -1}, {"source_end_byte": 10_000}, {"text": "other"},
    {"row_index": True}, {"section_key": ""},
])
def test_malformed_or_mutated_source_spans_fail_before_provider_dispatch(mutation):
    source = _source()
    span = _span(source, "training coordinators") | mutation
    provider = Reviewer({"admissible": True, "issues": []}, Clock())
    with pytest.raises(ValueError, match="source span"):
        review.review_greenfield_candidate(
            evidence_text=source, candidate=_response(source)["result"], source_spans=(span,),
            profile_id=STANDARD_PROFILE_ID, provider_factory=lambda: provider,
            deadline=55.0, clock=Clock(), observation={},
        )
    assert provider.calls == 0


@pytest.mark.parametrize("verdict", [
    None, {}, {"admissible": "true", "issues": []}, {"admissible": True, "issues": [], "repair": {}},
    {"admissible": True, "issues": [{"path": "x", "reason": "y"}]},
    {"admissible": False, "issues": []},
    {"admissible": False, "issues": [{"path": "", "reason": "y"}]},
    {"admissible": False, "issues": [{"path": "x", "reason": "y"}] * 2},
    {"admissible": False, "issues": [{"path": "candidate.accepted_source", "reason": "Missing source constraint"}]},
])
def test_denial_or_malformed_verdict_never_repairs_or_retries(verdict):
    clock = Clock()
    provider = Reviewer(verdict, clock)
    observation = {}
    with pytest.raises(RuntimeError):
        run_review(provider, clock, observation=observation)
    assert provider.calls == 1
    assert observation["dispatched"] is True


@pytest.mark.parametrize("scope", ["source", "resolved_source_custody", "accepted_source", "proposed_decisions"])
def test_review_cannot_mutate_evidence_or_either_authority(scope):
    def mutate(payload):
        if scope == "source":
            payload["source"] += "New authority"
        elif scope == "resolved_source_custody":
            payload[scope][0]["quote"] += "New authority"
        else:
            payload["candidate"][scope]["extra"] = "New authority"
    clock = Clock()
    provider = Reviewer({"admissible": True, "issues": []}, clock, mutation=mutate)
    with pytest.raises(RuntimeError, match="changed"):
        run_review(provider, clock)


def test_reviewer_setup_and_dispatch_use_remaining_absolute_deadline():
    clock = Clock()
    clock.value = 45.0
    provider = Reviewer({"admissible": True, "issues": []}, clock, 5.0)
    def factory():
        clock.value += 2.0
        return provider
    receipt = run_review(provider, clock, factory=factory)
    assert provider.requests[0].timeout_seconds == 8.0
    assert receipt["elapsed_seconds"] == 5.0
    assert clock.value == 52.0


def test_reviewer_dispatch_elapsed_excludes_setup_but_keeps_shared_deadline():
    clock = Clock()
    provider = Reviewer({"admissible": True, "issues": []}, clock, 3.0)
    observation = {}

    def factory():
        clock.value += 6.0
        return provider

    receipt = run_review(
        provider, clock, factory=factory, deadline=10.0, observation=observation,
    )
    assert provider.requests[0].timeout_seconds == 4.0
    assert receipt["elapsed_seconds"] == 3.0
    assert observation["elapsed_seconds"] == 3.0
    assert clock.value == 9.0


@pytest.mark.parametrize("setup", [False, True])
def test_no_budget_means_no_review_dispatch(setup):
    clock = Clock()
    clock.value = 54.5 if not setup else 53.0
    provider = Reviewer({"admissible": True, "issues": []}, clock)
    def factory():
        clock.value += 1.5
        return provider
    observation = {}
    with pytest.raises(RuntimeError, match="time"):
        run_review(provider, clock, factory=factory, observation=observation)
    assert provider.calls == 0
    assert "dispatched" not in observation


def test_review_can_use_more_than_twenty_seconds_inside_the_shared_deadline():
    clock = Clock()
    provider = Reviewer({"admissible": True, "issues": []}, clock, 23.0)
    receipt = run_review(provider, clock)
    assert receipt["elapsed_seconds"] == 23.0
    assert provider.requests[0].timeout_seconds == 55.0


@pytest.mark.parametrize("duration", [55.001, 60.0])
def test_late_response_fails_after_one_actual_call(duration):
    clock = Clock()
    provider = Reviewer({"admissible": True, "issues": []}, clock, duration)
    with pytest.raises(RuntimeError, match="time window"):
        run_review(provider, clock)
    assert provider.calls == 1


@pytest.mark.parametrize("started,duration", [(0.0, 55.001), (45.0, 10.001)])
@pytest.mark.parametrize("response", [None, {"admissible": True, "issues": []}])
def test_late_review_retains_provider_evidence_without_admitting_or_retrying(started, duration, response):
    clock = Clock()
    clock.value = started
    provider = Reviewer(response, clock, duration)
    provider.last_failure_code = "timeout" if response is None else ""
    provider.last_failure_detail = "Codex CLI exceeded its request budget." if response is None else ""
    observation = {}
    with pytest.raises(RuntimeError, match="exceeded its model time window"):
        run_review(provider, clock, observation=observation)
    assert provider.calls == 1
    assert observation["response"] == response
    assert observation["provider"] == review.odylith_reasoning.provider_failure_metadata(provider)
    assert observation["provider"]["model"] == "gpt-6-astra"
    assert observation["provider"]["reasoning_effort"] == "medium"
    assert observation["provider"]["code"] == ("timeout" if response is None else "")
    assert observation["elapsed_seconds"] == pytest.approx(duration)


def test_native_author_requires_admission_and_preserves_source_and_design():
    source = _source()
    response = _response(source)
    clock = Clock()
    provider = RemainingCandidateProvider(response)
    participant = provider.participant_provider()
    reviewer = Reviewer({"admissible": True, "issues": []}, clock, 4.0)
    result = participant_authoring.author_greenfield_intent(
        evidence_text=source, provider=provider,
        participant_provider_factory=lambda: participant,
        clock=clock, review_provider_factory=lambda: reviewer,
    )
    assert participant.calls == provider.calls == reviewer.calls == 1
    assert result.semantic_model_call_count == 3
    assert result.provisional_design == response["result"]["provisional_design"]
    assert result.source_sha256 == result.candidate_review["source_sha256"]
    assert result.elapsed_seconds == 4.0


def test_no_review_provider_cannot_return_authored_success():
    with pytest.raises(author.GreenfieldModelAuthoringError, match="unavailable"):
        provider = RemainingCandidateProvider(_response(_source()))
        participant_authoring.author_greenfield_intent(
            evidence_text=_source(), provider=provider,
            participant_provider_factory=provider.participant_provider,
        )


def test_structural_validation_cannot_change_the_reviewed_candidate(monkeypatch):
    validate = author.validate_greenfield_authoring_response
    def mutate(response, **kwargs):
        authored = validate(response, **kwargs)
        response["result"]["assumptions"].append({"applies_to": "general", "statement": "Altered"})
        return authored
    monkeypatch.setattr(participant_authoring, "validate_greenfield_authoring_response", mutate)
    with pytest.raises(author.GreenfieldModelAuthoringError, match="validation changed"):
        provider = RemainingCandidateProvider(_response(_source()))
        participant_authoring.author_greenfield_intent(
            evidence_text=_source(), provider=provider,
            participant_provider_factory=provider.participant_provider,
            review_provider_factory=AdmittingReviewProvider,
        )


def test_review_postvalidation_deadline_is_enforced(monkeypatch):
    clock = Clock()
    provider = Reviewer({"admissible": True, "issues": []}, clock, 19.0)
    validate = review.require_greenfield_model_profile_observation
    def slow_validation(**kwargs):
        result = validate(**kwargs)
        if provider.calls:
            clock.value += 2.0
        return result
    monkeypatch.setattr(review, "require_greenfield_model_profile_observation", slow_validation)
    with pytest.raises(RuntimeError, match="exceeded.*time window"):
        run_review(provider, clock, deadline=20.0)
    assert provider.calls == 1


def test_review_finalization_cannot_admit_a_late_role():
    ticks = iter((0.0, 0.0, 54.9, 54.9, 54.9, 55.1))
    clock = lambda: next(ticks, 55.1)
    provider = StructuredAuthoringProvider({"admissible": True, "issues": []})
    observation = {}
    with pytest.raises(RuntimeError, match="exceeded its model time window"):
        run_review(provider, clock, observation=observation)
    assert provider.calls == 1
    assert observation["elapsed_seconds"] == pytest.approx(0.2)


@pytest.mark.parametrize("role", ["participant", "author", "reviewer"])
def test_actual_dispatch_count_survives_provider_exception(monkeypatch, role):
    class Unavailable(StructuredAuthoringProvider):
        def generate_structured(self, *, request):
            self.calls += 1
            raise TimeoutError("Provider did not return")
    observations = []
    monkeypatch.setattr(
        participant_authoring,
        "_emit_release_proof_observation",
        lambda **kwargs: observations.append(kwargs),
    )
    provider = (
        Unavailable(_response(_source()))
        if role == "author"
        else RemainingCandidateProvider(_response(_source()))
    )
    participant_factory = (
        (lambda: Unavailable(None))
        if role == "participant"
        else provider.participant_provider
    )
    with pytest.raises(author.GreenfieldModelAuthoringError):
        participant_authoring.author_greenfield_intent(
            evidence_text=_source(), provider=provider,
            participant_provider_factory=participant_factory,
            review_provider_factory=(
                (lambda: Unavailable(None)) if role == "reviewer" else AdmittingReviewProvider
            ),
        )
    assert observations[-1]["semantic_model_call_count"] == {
        "participant": 1,
        "author": 2,
        "reviewer": 3,
    }[role]
