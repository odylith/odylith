"""One author and one independent review share a pinned window without repair."""

from copy import deepcopy
import json

import pytest

from odylith.runtime.domain_intelligence import greenfield_model_intent_authoring as author
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import materialize_model_authored_intent
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    DEEP_PROFILE_ID, RESCUE_PROFILE_ID, STANDARD_PROFILE_ID, get_greenfield_model_profile,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    AdmittingReviewProvider, StructuredAuthoringProvider, authored_response,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _LIST_FIELDS, _TEXT_FIELDS, _response, _source


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


class Provider:
    provider_name = "codex-cli"

    def __init__(self, responses, durations, clock):
        self.responses, self.durations, self.clock = responses, durations, clock
        self.requests = []

    def generate_structured(self, *, request):
        index = len(self.requests)
        self.requests.append(request)
        self.clock.value += self.durations[index]
        return deepcopy(self.responses[index])


@pytest.mark.parametrize(
    ("profile_id", "model_budget", "consumer_budget"),
    [(STANDARD_PROFILE_ID, 55.0, 60.0), (RESCUE_PROFILE_ID, 80.0, 90.0), (DEEP_PROFILE_ID, 105.0, 120.0)],
)
def test_one_author_and_review_share_the_full_pinned_window(profile_id, model_budget, consumer_budget):
    response = _response(_source())
    clock = Clock()
    provider = Provider([response], [model_budget - 1.0], clock)
    reviewer = Provider([{"admissible": True, "issues": []}], [1.0], clock)
    result = author.author_greenfield_intent(
        review_provider_factory=lambda: reviewer,
        evidence_text=_source(), provider=provider, clock=clock, model_profile_id=profile_id,
    )
    profile = get_greenfield_model_profile(profile_id)
    assert result.semantic_model_call_count == 2
    assert len(provider.requests) == len(reviewer.requests) == 1
    assert result.elapsed_seconds == result.effective_timeout_seconds == model_budget
    assert result.initial_authoring_elapsed_seconds == model_budget - 1.0
    assert result.candidate_review["elapsed_seconds"] == 1.0
    assert reviewer.requests[0].timeout_seconds == 1.0
    assert reviewer.requests[0].schema_name == "greenfield_candidate_review"
    assert profile.consumer_budget_seconds == consumer_budget
    request = provider.requests[0]
    assert request.timeout_seconds == model_budget
    assert (request.model, request.reasoning_effort) == (profile.model, profile.reasoning_effort)
    assert request.schema_name == "greenfield_intent_authoring"
    assert result.provisional_design == response["result"]["provisional_design"]
    assert result.intent["first_path"] == "\n".join(row["quote"] for row in response["result"]["facts"]["first_path"])


@pytest.mark.parametrize("profile_id", [STANDARD_PROFILE_ID, RESCUE_PROFILE_ID, DEEP_PROFILE_ID])
def test_overrun_fails_after_one_call_without_review_or_retry(profile_id):
    clock = Clock()
    budget = get_greenfield_model_profile(profile_id).model_timeout_seconds
    provider = Provider([_response(_source())], [budget + 0.001], clock)
    reviewer = AdmittingReviewProvider()
    with pytest.raises(author.GreenfieldModelAuthoringError, match="model time window"):
        author.author_greenfield_intent(
            review_provider_factory=lambda: reviewer,
            evidence_text=_source(), provider=provider, clock=clock, model_profile_id=profile_id,
        )
    assert len(provider.requests) == 1
    assert reviewer.calls == 0
    assert provider.requests[0].timeout_seconds == budget


def test_shorter_remaining_window_is_not_reduced_by_a_review_reserve():
    clock = Clock()
    provider = Provider([_response(_source())], [19.0], clock)
    reviewer = AdmittingReviewProvider()
    result = author.author_greenfield_intent(
        review_provider_factory=lambda: reviewer,
        evidence_text=_source(), provider=provider, clock=clock,
        model_profile_id=RESCUE_PROFILE_ID, timeout_seconds=20.0,
    )
    assert result.effective_timeout_seconds == provider.requests[0].timeout_seconds == 20.0
    assert result.semantic_model_call_count == 2
    assert len(provider.requests) == reviewer.calls == 1
    assert reviewer.requests[0].timeout_seconds == 1.0


@pytest.mark.parametrize("call_count", [True, False, 0, 2])
def test_validation_boundary_rejects_non_single_integer_call_claims(call_count):
    with pytest.raises(author.GreenfieldModelAuthoringError, match="exactly one complete authoring call"):
        author._validated_authoring_response(
            _response(_source()), evidence_text=_source(), elapsed_seconds=1.0,
            provider={"provider": "codex-cli", "model": "gpt-5.6-terra", "reasoning_effort": "low"},
            profile_id=STANDARD_PROFILE_ID, effective_timeout_seconds=55.0,
            semantic_model_call_count=call_count,
        )


@pytest.mark.parametrize("failure", ["ownership", "source_quote", "design_source_fact", "design_authority", "empty_owner_group"])
def test_invalid_candidate_never_reaches_a_second_prepared_response_or_writes(tmp_path, failure):
    source = _source()
    invalid = _response(source)
    if failure == "ownership":
        invalid["result"]["components"][0]["responsibilities"] = [
            {"quote": "Dock attendant Ivo enters a vessel tag", "occurrence": 1},
        ]
    elif failure == "source_quote":
        invalid["result"]["facts"]["title"]["quote"] = "Invented title"
    elif failure == "design_source_fact":
        invalid["result"]["facts"]["internal_systems"].append({
            "quote": invalid["result"]["provisional_design"]["components"][0]["name"],
            "occurrence": 1,
        })
    elif failure == "design_authority":
        invalid["result"]["provisional_design"]["authority_kind"] = "accepted_fact"
    else:
        invalid["result"]["components"][0]["responsibilities"] = []
    original = deepcopy(invalid)
    clock = Clock()
    provider = Provider([invalid, _response(source)], [1.0, 1.0], clock)
    with pytest.raises(author.GreenfieldModelAuthoringError):
        materialize_model_authored_intent(review_provider_factory=AdmittingReviewProvider, prompt=source, repo_root=tmp_path, authoring_provider=provider)
    assert len(provider.requests) == 1
    assert invalid == original
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("human_actors", [
    "Dock attendant Ivo",
    [{"quote": "Dock attendant Ivo"}],
    [{"quote": "Dock attendant Ivo", "occurrence": 0}],
    [{"quote": "Invented reviewer", "occurrence": 1}],
    [],
])
def test_source_actor_custody_cannot_be_malformed_or_remove_a_referenced_human(tmp_path, human_actors):
    response = _response(_source())
    response["result"]["facts"]["human_actors"] = human_actors
    provider = StructuredAuthoringProvider(response)
    with pytest.raises(author.GreenfieldModelAuthoringError):
        materialize_model_authored_intent(review_provider_factory=AdmittingReviewProvider, prompt=_source(), repo_root=tmp_path, authoring_provider=provider)
    assert provider.calls == 1
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("failure", ["missing_fact_and_assumption", "both_fact_and_assumption"])
def test_decision_fact_and_targeted_assumption_remain_exclusive(tmp_path, failure):
    response = _response(_source())
    if failure == "missing_fact_and_assumption":
        response["result"]["facts"]["opportunity"] = None
    else:
        response["result"]["assumptions"] = [{
            "applies_to": "opportunity",
            "statement": "A reviewable berth workflow is the worthwhile improvement.",
        }]
    provider = StructuredAuthoringProvider(response)
    with pytest.raises(author.GreenfieldModelAuthoringError):
        materialize_model_authored_intent(review_provider_factory=AdmittingReviewProvider, prompt=_source(), repo_root=tmp_path, authoring_provider=provider)
    assert provider.calls == 1
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("response", [None, {}, {"result": {"corrections": []}}])
def test_unavailable_or_retired_review_response_is_fail_closed(tmp_path, response):
    provider = StructuredAuthoringProvider(response)
    with pytest.raises(author.GreenfieldModelAuthoringError):
        materialize_model_authored_intent(review_provider_factory=AdmittingReviewProvider, prompt=_source(), repo_root=tmp_path, authoring_provider=provider)
    assert provider.calls == 1
    assert list(tmp_path.iterdir()) == []


def test_model_observation_is_checked_before_and_after_the_only_call(monkeypatch):
    observed = []
    require = author.require_greenfield_model_profile_observation

    def record(**values):
        observed.append(values)
        return require(**values)

    monkeypatch.setattr(author, "require_greenfield_model_profile_observation", record)
    provider = StructuredAuthoringProvider(_response(_source()))
    author.author_greenfield_intent(review_provider_factory=AdmittingReviewProvider, evidence_text=_source(), provider=provider, clock=lambda: 0.0)
    assert provider.calls == 1
    assert len(observed) == 2
    assert all(row["model"] == "gpt-5.6-terra" for row in observed)
    assert all(row["reasoning_effort"] == "low" for row in observed)
    assert all(row["effective_timeout_seconds"] == 55.0 for row in observed)


def test_false_post_call_model_identity_fails_without_retry():
    class MismatchedProvider(StructuredAuthoringProvider):
        def generate_structured(self, *, request):
            response = super().generate_structured(request=request)
            self.last_request_model = "gpt-5.6-sol"
            return response

    provider = MismatchedProvider(_response(_source()))
    with pytest.raises(ValueError, match="pinned Greenfield model profile"):
        author.author_greenfield_intent(review_provider_factory=AdmittingReviewProvider, evidence_text=_source(), provider=provider, clock=lambda: 0.0)
    assert provider.calls == 1


@pytest.mark.parametrize("failed", [False, True])
def test_proof_preserves_the_exact_candidate_and_dispatched_review_metadata(tmp_path, monkeypatch, failed):
    response = _response(_source())
    if failed:
        response["result"]["facts"]["title"]["quote"] = "Invented title"
    clock = Clock()
    provider = Provider([response], [36.0], clock)
    path = tmp_path / "observation.json"
    with path.open("wb") as output:
        monkeypatch.setenv(author.GREENFIELD_MODEL_PROOF_FD_ENV, str(output.fileno()))
        if failed:
            with pytest.raises(author.GreenfieldModelAuthoringError):
                author.author_greenfield_intent(
                    review_provider_factory=AdmittingReviewProvider,
                    evidence_text=_source(), provider=provider, clock=clock, model_profile_id=RESCUE_PROFILE_ID,
                )
        else:
            author.author_greenfield_intent(
                review_provider_factory=AdmittingReviewProvider,
                evidence_text=_source(), provider=provider, clock=clock, model_profile_id=RESCUE_PROFILE_ID,
            )
    retained = json.loads(path.read_text())
    assert retained["response"] == response
    assert retained["semantic_model_call_count"] == (1 if failed else 2)
    assert retained["authoring_version"] == author.GREENFIELD_INTENT_AUTHORING_VERSION
    assert retained["initial_authoring"]["timeout_seconds"] == 80.0
    assert retained["initial_authoring"]["elapsed_seconds"] == 36.0
    assert "source_review" not in retained
    if failed:
        assert "candidate_review" not in retained
    else:
        assert retained["candidate_review"]["response"] == {"admissible": True, "issues": []}
        assert retained["candidate_review"]["request"]["source"] == _source()
    assert "initial_response" not in retained


def test_source_binding_preserves_explicit_unicode_occurrences_without_auto_repair():
    source = "🧭 Dock attendant Ivohip. " + _source() + " café"
    response = _response(source)
    response["result"]["facts"]["human_actors"][0]["occurrence"] = 2
    provider = StructuredAuthoringProvider(response)
    result = author.author_greenfield_intent(review_provider_factory=AdmittingReviewProvider, evidence_text=source, provider=provider, clock=lambda: 0.0)
    span = next(row for row in result.source_spans if row["projection_path"] == "/human_actors/0")
    start = source.encode().index(b"Dock attendant Ivo", len("🧭 Dock attendant Ivo".encode()))
    assert span["source_start_byte"] == start
    assert source.encode()[span["source_start_byte"]:span["source_end_byte"]] == b"Dock attendant Ivo"
    assert provider.calls == 1


def test_fixture_terminal_occurrence_is_local_to_its_explicit_raw_fact_row():
    terminal = _response(_source())["result"]["terminal"]
    source = f"Earlier label: {terminal['result_quote']}. {_source()}"
    response = _response(source)
    assert response["result"]["terminal"] == terminal
    assert terminal["result_occurrence"] == 1
    reference = terminal["result_fact"]
    raw = response["result"]["facts"][reference["field"]]
    fact = raw[reference["row"] - 1] if isinstance(raw, list) else raw
    assert terminal["result_quote"] in fact["quote"]
    provider = StructuredAuthoringProvider(response)
    author.author_greenfield_intent(review_provider_factory=AdmittingReviewProvider, evidence_text=source, provider=provider, clock=lambda: 0.0)
    assert provider.calls == 1


def test_source_schema_keeps_human_participants_distinct_from_operational_dependencies():
    provider = StructuredAuthoringProvider(_response(_source()))
    author.author_greenfield_intent(review_provider_factory=AdmittingReviewProvider, evidence_text=_source(), provider=provider, clock=lambda: 0.0)
    properties = provider.requests[0].output_schema["properties"]["result"]["anyOf"][0]["properties"]
    external = properties["facts"]["properties"]["external_systems"]["description"]
    component = properties["components"]["items"]["properties"]
    assert "explicitly source-stated operational exchange or dependency" in external
    assert "an output recipient, or a reviewer does not" in external
    assert "never a human performer or external participant" in component["owner_fact_quote"]["description"]
    assert properties["components"]["minItems"] == 0
    assert component["responsibilities"]["minItems"] == 1


def test_component_relation_order_is_unicode_and_domain_neutral() -> None:
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "component_responsibilities": ["Žurnalo įrašas", "航路記録"],
        "internal_systems": ["Sąsaja", "航路"],
    }
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    )
    response = authored_response(
        intent,
        evidence_text=source,
        component_responsibility_owners=["Sąsaja", "航路"],
    )
    assert [
        (row["owner_fact_quote"], row["responsibilities"][0]["quote"])
        for row in response["result"]["components"]
    ] == [("Sąsaja", "Žurnalo įrašas"), ("航路", "航路記録")]
    result = author.author_greenfield_intent(
        review_provider_factory=AdmittingReviewProvider,
        evidence_text=source,
        provider=StructuredAuthoringProvider(response),
        clock=lambda: 0.0,
    )

    assert [
        row["responsibility_quote"] for row in result.component_responsibility_relations
    ] == ["Žurnalo įrašas", "航路記録"]
    assert [
        row["owner_system_quote"] for row in result.component_responsibility_relations
    ] == ["Sąsaja", "航路"]
