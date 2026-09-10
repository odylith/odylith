"""Complete-candidate admission: immutable inputs, one call, shared deadlines."""

from copy import deepcopy
import hashlib
import json

import pytest

from odylith.runtime.domain_intelligence import greenfield_candidate_review as review
from odylith.runtime.domain_intelligence import greenfield_model_intent_authoring as author
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import STANDARD_PROFILE_ID
from tests.unit.runtime.greenfield_model_authoring_fixtures import StructuredAuthoringProvider
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
    return review.review_greenfield_candidate(
        evidence_text=_source(), candidate=_response(_source())["result"],
        profile_id=STANDARD_PROFILE_ID, provider_factory=factory or (lambda: provider),
        deadline=deadline, clock=clock,
        observation=observation if observation is not None else {},
    )


def test_partition_preserves_every_value_and_binds_complete_candidate():
    source = _source()
    candidate = _response(source)["result"]
    original = deepcopy(candidate)
    payload = review.candidate_review_payload(source, candidate)
    assert {**payload["candidate"]["accepted_source"], **payload["candidate"]["proposed_decisions"]} == original
    assert payload["source"] == source
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


def test_unknown_authority_is_not_silently_dropped():
    candidate = _response(_source())["result"]
    candidate["unclassified_authority"] = {}
    with pytest.raises(ValueError, match="authority"):
        review.candidate_review_payload(_source(), candidate)


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


@pytest.mark.parametrize("scope", ["source", "accepted_source", "proposed_decisions"])
def test_review_cannot_mutate_evidence_or_either_authority(scope):
    def mutate(payload):
        if scope == "source":
            payload["source"] += "New authority"
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
    assert receipt["elapsed_seconds"] == 7.0
    assert clock.value == 52.0


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


@pytest.mark.parametrize("duration", [20.001, 55.0])
def test_late_response_fails_after_one_actual_call(duration):
    clock = Clock()
    provider = Reviewer({"admissible": True, "issues": []}, clock, duration)
    with pytest.raises(RuntimeError, match="time window"):
        run_review(provider, clock)
    assert provider.calls == 1


@pytest.mark.parametrize("started,duration", [(0.0, 20.001), (45.0, 10.001)])
@pytest.mark.parametrize("response", [None, {"admissible": True, "issues": []}])
def test_late_review_retains_provider_evidence_without_admitting_or_retrying(started, duration, response):
    clock = Clock()
    clock.value = started
    provider = Reviewer(response, clock, duration)
    provider.last_failure_code = "timeout" if response is None else ""
    provider.last_failure_detail = "Codex CLI exceeded its request budget." if response is None else ""
    observation = {}
    with pytest.raises(RuntimeError, match="exceeded its time window"):
        run_review(provider, clock, observation=observation)
    assert provider.calls == 1
    assert observation["response"] == response
    assert observation["provider"] == review.odylith_reasoning.provider_failure_metadata(provider)
    assert observation["provider"]["model"] == "gpt-5.6-sol"
    assert observation["provider"]["reasoning_effort"] == "medium"
    assert observation["provider"]["code"] == ("timeout" if response is None else "")
    assert observation["elapsed_seconds"] == pytest.approx(duration)


def test_native_author_requires_admission_and_preserves_source_and_design():
    source = _source()
    response = _response(source)
    clock = Clock()
    provider = StructuredAuthoringProvider(response)
    reviewer = Reviewer({"admissible": True, "issues": []}, clock, 4.0)
    result = author.author_greenfield_intent(
        evidence_text=source, provider=provider, clock=clock, review_provider_factory=lambda: reviewer,
    )
    assert provider.calls == reviewer.calls == 1
    assert result.semantic_model_call_count == 2
    assert result.provisional_design == response["result"]["provisional_design"]
    assert result.source_sha256 == result.candidate_review["source_sha256"]
    assert result.elapsed_seconds == 4.0


def test_no_review_provider_cannot_return_authored_success():
    with pytest.raises(author.GreenfieldModelAuthoringError, match="could not be verified"):
        author.author_greenfield_intent(evidence_text=_source(), provider=StructuredAuthoringProvider(_response(_source())))


def test_structural_validation_cannot_change_the_reviewed_candidate(monkeypatch):
    validate = author._validated_authoring_response
    def mutate(response, **kwargs):
        authored = validate(response, **kwargs)
        response["result"]["assumptions"].append({"applies_to": "general", "statement": "Altered"})
        return authored
    monkeypatch.setattr(author, "_validated_authoring_response", mutate)
    with pytest.raises(author.GreenfieldModelAuthoringError, match="validation changed"):
        author.author_greenfield_intent(evidence_text=_source(), provider=StructuredAuthoringProvider(_response(_source())))


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
        run_review(provider, clock)
    assert provider.calls == 1


def test_review_finalization_cannot_admit_a_late_role():
    ticks = iter((0.0, 0.0, 19.9, 19.9, 19.9, 20.1))
    clock = lambda: next(ticks, 20.1)
    provider = StructuredAuthoringProvider({"admissible": True, "issues": []})
    observation = {}
    with pytest.raises(RuntimeError, match="exceeded its time window"):
        run_review(provider, clock, observation=observation)
    assert provider.calls == 1
    assert observation["elapsed_seconds"] == 20.1


@pytest.mark.parametrize("role", ["author", "reviewer"])
def test_actual_dispatch_count_survives_provider_exception(monkeypatch, role):
    class Unavailable(StructuredAuthoringProvider):
        def generate_structured(self, *, request):
            self.calls += 1
            raise TimeoutError("Provider did not return")
    observations = []
    monkeypatch.setattr(author, "_emit_release_proof_observation", lambda **kwargs: observations.append(kwargs))
    provider = Unavailable(None) if role == "author" else StructuredAuthoringProvider(_response(_source()))
    with pytest.raises(author.GreenfieldModelAuthoringError):
        author.author_greenfield_intent(evidence_text=_source(), provider=provider,
            review_provider_factory=lambda: Unavailable(None))
    assert observations[-1]["call_count"] == (1 if role == "author" else 2)
