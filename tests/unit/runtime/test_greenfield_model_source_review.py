"""The source-claim review is narrow, observable, and shares the original clock."""

from copy import deepcopy
import json
import os

import pytest

from odylith.runtime.domain_intelligence import greenfield_model_source_review
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_MODEL_PROOF_FD_ENV,
    GreenfieldModelAuthoringError,
    author_greenfield_intent,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


class Provider:
    provider_name = "codex-cli"

    def __init__(self, responses, durations, clock):
        self.responses = responses
        self.durations = durations
        self.clock = clock
        self.requests = []

    def generate_structured(self, *, request):
        index = len(self.requests)
        self.requests.append(request)
        self.clock.value += self.durations[index]
        return deepcopy(self.responses[index])


def _conflicting_response():
    response = _response(_source())
    response["result"]["components"][0]["responsibilities"] = [
        {"quote": "Dock attendant Ivo enters a vessel tag", "occurrence": 1}
    ]
    return response


def _review_response():
    result = _response(_source())["result"]
    return {
        "product_story": result["facts"]["product_story"],
        "components": result["components"],
    }


def _provider(monkeypatch, responses, durations):
    clock = Clock()
    monkeypatch.setattr(greenfield_model_source_review, "monotonic", clock)
    return Provider(responses, durations, clock), clock


@pytest.mark.parametrize("durations,review_timeout", [([30.0, 7.0], 20.0), ([50.0, 4.0], 5.0)])
def test_one_ownership_correction_preserves_every_other_field_and_original_budget(
    monkeypatch, durations, review_timeout,
):
    original = _conflicting_response()
    provider, clock = _provider(monkeypatch, [original, _review_response()], durations)

    result = author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)

    assert len(provider.requests) == result.semantic_model_call_count == 2
    assert result.elapsed_seconds == sum(durations)
    assert result.effective_timeout_seconds == 55.0
    assert result.tier == "standard"
    first, review = provider.requests
    assert first.timeout_seconds == 55.0
    assert review.timeout_seconds == review_timeout
    assert review.model == first.model
    assert review.reasoning_effort == first.reasoning_effort
    assert review.schema_name == "greenfield_semantic_source_review"
    assert review.prompt_payload["candidate"] == original["result"]
    assert result.intent["component_responsibilities"] == ["Record berth occupancy"]
    assert [row["actor_kind"] for row in result.first_path_relations] == ["human", "product", "product"]
    unchanged_provider, unchanged_clock = _provider(
        monkeypatch, [_response(_source()), _review_response()], [0.0, 0.0]
    )
    control = author_greenfield_intent(evidence_text=_source(), provider=unchanged_provider, clock=unchanged_clock)
    assert result.intent == control.intent
    assert result.first_path_relations == control.first_path_relations
    assert result.atomic_claims == control.atomic_claims
    assert result.source_spans == control.source_spans
    assert original == _conflicting_response()


def test_structurally_valid_authoring_still_gets_one_source_claim_review(monkeypatch):
    provider, clock = _provider(monkeypatch, [_response(_source()), _review_response()], [10.0, 5.0])
    result = author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    assert len(provider.requests) == result.semantic_model_call_count == 2


def test_author_and_reviewer_share_the_nonempty_component_contract(monkeypatch):
    provider, clock = _provider(monkeypatch, [_response(_source()), _review_response()], [10.0, 5.0])
    author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    author, reviewer = provider.requests
    authored_schema = author.output_schema["properties"]["result"]["anyOf"][0]
    components = authored_schema["properties"]["components"]
    assert reviewer.output_schema["properties"]["components"] is components
    assert components["minItems"] == 1


def test_review_cannot_erase_valid_components_or_silently_accept_the_original(monkeypatch):
    invalid_review = {**_review_response(), "components": []}
    provider, clock = _provider(monkeypatch, [_response(_source()), invalid_review], [40.0, 13.0])
    with pytest.raises(GreenfieldModelAuthoringError, match="invalid component ownership"):
        author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    assert len(provider.requests) == 2


def test_no_remaining_budget_does_not_trigger_another_call(monkeypatch):
    provider, clock = _provider(monkeypatch, [_conflicting_response()], [55.0])
    with pytest.raises(GreenfieldModelAuthoringError):
        author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    assert len(provider.requests) == 1


def test_review_cannot_extend_the_remaining_deadline(monkeypatch):
    provider, clock = _provider(monkeypatch, [_conflicting_response(), _review_response()], [45.0, 11.0])
    with pytest.raises(GreenfieldModelAuthoringError, match="exceeded"):
        author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    assert len(provider.requests) == 2
    assert provider.requests[1].timeout_seconds == 10.0


@pytest.mark.parametrize("review", [
    None,
    {},
    {"components": [], "events": []},
    {"components": [{"owner_fact_quote": "Berth map", "responsibilities": [
        {"quote": "This quote is not in the source", "occurrence": 1},
    ]}]},
])
def test_invalid_correction_fails_without_another_call(monkeypatch, review):
    provider, clock = _provider(monkeypatch, [_conflicting_response(), review], [20.0, 5.0])
    with pytest.raises(GreenfieldModelAuthoringError):
        author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    assert len(provider.requests) == 2


def test_repeated_ownership_conflict_does_not_start_a_repair_loop(monkeypatch):
    invalid = _conflicting_response()
    review = {**_review_response(), "components": deepcopy(invalid["result"]["components"])}
    provider, clock = _provider(monkeypatch, [invalid, review], [20.0, 5.0])
    with pytest.raises(GreenfieldModelAuthoringError):
        author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    assert len(provider.requests) == 2


def test_unrelated_custody_error_is_not_an_ownership_retry(monkeypatch):
    invalid = _response(_source())
    invalid["result"]["facts"]["title"]["quote"] = "Invented title"
    provider, clock = _provider(monkeypatch, [invalid], [10.0])
    with pytest.raises(GreenfieldModelAuthoringError, match="not present"):
        author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    assert len(provider.requests) == 1


def test_proof_retains_initial_response_exact_review_and_final_candidate(tmp_path, monkeypatch):
    initial = _conflicting_response()
    review = _review_response()
    provider, clock = _provider(monkeypatch, [initial, review], [25.0, 7.0])
    observation = tmp_path / "observation.json"
    descriptor = os.open(observation, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    monkeypatch.setenv(GREENFIELD_MODEL_PROOF_FD_ENV, str(descriptor))
    try:
        author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    finally:
        os.close(descriptor)
    retained = json.loads(observation.read_text())
    assert retained["semantic_model_call_count"] == 2
    assert retained["initial_response"] == initial
    assert retained["source_review"]["response"] == review
    assert retained["source_review"]["elapsed_seconds"] == 7.0
    expected = deepcopy(initial)
    expected["result"]["components"] = review["components"]
    assert retained["response"] == expected


def test_source_review_replaces_invocation_claim_without_changing_workflow(monkeypatch):
    source = "Please propose a workspace. " + _source()
    initial = _response(source)
    initial["result"]["facts"]["product_story"] = {
        "quote": "Please propose a workspace.", "occurrence": 1,
    }
    review = _review_response()
    provider, clock = _provider(monkeypatch, [initial, review], [20.0, 6.0])

    result = author_greenfield_intent(evidence_text=source, provider=provider, clock=clock)

    assert result.intent["product_story"] == review["product_story"]["quote"]
    assert result.intent["first_path"] == "\n".join(
        row["quote"] for row in initial["result"]["facts"]["first_path"]
    )
    assert result.semantic_model_call_count == 2


def test_source_review_cannot_rewrite_a_protected_field(monkeypatch):
    review = {**_review_response(), "events": []}
    provider, clock = _provider(monkeypatch, [_response(_source()), review], [20.0, 6.0])
    with pytest.raises(GreenfieldModelAuthoringError, match="valid candidate"):
        author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    assert len(provider.requests) == 2
