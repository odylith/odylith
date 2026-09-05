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


def _review_response(
    *, fact_corrections=None, assumptions=None, components=None,
):
    return {
        "fact_corrections": deepcopy(fact_corrections or []),
        "assumptions": deepcopy(assumptions),
        "components": deepcopy(components),
    }


def _reviewed_people_response():
    source = _source() + " Review recipient Mara. for review visibility."
    response = _response(source)
    response["result"]["facts"]["human_actors"].extend(
        [
            {"quote": "Review recipient Mara", "occurrence": 1},
            {"quote": "for review visibility", "occurrence": 1},
        ]
    )
    response["result"]["facts"]["external_systems"].extend(
        [
            {"quote": "Review recipient Mara", "occurrence": 1},
            {"quote": "for review visibility", "occurrence": 1},
        ]
    )
    return source, response


def _component_correction(response=None):
    result = (response or _response(_source()))["result"]
    return _review_response(components=result["components"])


def _provider(monkeypatch, responses, durations):
    clock = Clock()
    monkeypatch.setattr(greenfield_model_source_review, "monotonic", clock)
    return Provider(responses, durations, clock), clock


@pytest.mark.parametrize("durations,review_timeout", [([30.0, 7.0], 20.0), ([50.0, 4.0], 5.0)])
def test_one_ownership_correction_preserves_every_other_field_and_original_budget(
    monkeypatch, durations, review_timeout,
):
    original = _conflicting_response()
    provider, clock = _provider(monkeypatch, [original, _component_correction()], durations)

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
    assert review.prompt_payload["validation_error"] == (
        "Greenfield authoring assigned a non-product event as a component responsibility"
    )
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


def test_structurally_valid_authoring_sparse_review_is_explicit_noop(monkeypatch):
    initial = _response(_source())
    review = _review_response()
    provider, clock = _provider(monkeypatch, [initial, review], [10.0, 5.0])
    result = author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    assert len(provider.requests) == result.semantic_model_call_count == 2
    assert review == {
        "fact_corrections": [],
        "assumptions": None,
        "components": None,
    }
    assert provider.requests[1].prompt_payload == {
        "evidence": _source(), "candidate": initial["result"],
    }
    assert result.intent["product_story"] == initial["result"]["facts"]["product_story"]["quote"]
    assert result.intent["component_responsibilities"] == ["Record berth occupancy"]


def test_author_and_reviewer_share_every_mutable_fact_and_whole_list_contract(monkeypatch):
    provider, clock = _provider(monkeypatch, [_response(_source()), _review_response()], [10.0, 5.0])
    author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    author_request, reviewer = provider.requests
    authored_schema = author_request.output_schema["properties"]["result"]["anyOf"][0]
    components = authored_schema["properties"]["components"]
    assumptions = authored_schema["properties"]["assumptions"]
    fact_schemas = authored_schema["properties"]["facts"]["properties"]
    review_properties = reviewer.output_schema["properties"]
    correction_branches = review_properties["fact_corrections"]["items"]["anyOf"]
    branch_by_field = {
        row["properties"]["field"]["const"]: row
        for row in correction_branches
    }
    assert set(branch_by_field) == set(fact_schemas) - {"first_path"}
    for field, branch in branch_by_field.items():
        assert branch["properties"]["value"] is fact_schemas[field]
    assert review_properties["components"]["anyOf"][0] is components
    assert review_properties["assumptions"]["anyOf"][0] is assumptions
    assert components["minItems"] == 1


def test_admission_meaning_lives_on_the_shared_source_schema_properties(monkeypatch):
    provider, clock = _provider(monkeypatch, [_response(_source()), _review_response()], [10.0, 5.0])
    author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    authored, reviewed = provider.requests
    properties = authored.output_schema["properties"]["result"]["anyOf"][0]["properties"]
    external = properties["facts"]["properties"]["external_systems"]["description"]
    component = properties["components"]["items"]["properties"]

    assert "explicitly source-stated operational exchange or dependency" in external
    assert "an output recipient, or a reviewer does not" in external
    assert external in reviewed.system_prompt
    assert "external_systems" not in greenfield_model_source_review._DEFAULT_FACT_DEFINITIONS
    assert "organizations or data" not in authored.system_prompt
    assert "never a human performer or external participant" in component["owner_fact_quote"]["description"]
    assert "enclosing product capability" in component["responsibilities"]["description"]


def test_review_keeps_recipient_human_while_removing_cross_field_external_noise(
    monkeypatch,
):
    source, initial = _reviewed_people_response()
    initial_copy = deepcopy(initial)
    performing, recipient, _purpose_fragment = initial["result"]["facts"]["human_actors"]
    external_system = initial["result"]["facts"]["external_systems"][0]
    review = _review_response(
        fact_corrections=[
            {"field": "human_actors", "value": [performing, recipient]},
            {"field": "external_systems", "value": [external_system]},
        ]
    )
    provider, clock = _provider(monkeypatch, [initial, review], [20.0, 5.0])

    result = author_greenfield_intent(evidence_text=source, provider=provider, clock=clock)

    assert result.intent["human_actors"] == ["Dock attendant Ivo", "Review recipient Mara"]
    assert result.intent["external_systems"] == ["Harbor Ledger"]
    assert result.first_path_relations[0]["actor_fact_quote"] == "Dock attendant Ivo"
    assert result.intent["customer"] == "Dock attendants"
    assert result.intent["product_story"] == (
        initial["result"]["facts"]["product_story"]["quote"]
    )
    assert result.intent["component_responsibilities"] == ["Record berth occupancy"]
    assert [
        (
            row["actor_fact_quote"],
            row["action_verb_quote"],
            row["target_quote"],
        )
        for row in result.first_path_relations
    ] == [
        (
            row["actor_fact_quote"],
            row["action_quote"],
            row["target_quote"],
        )
        for row in initial["result"]["events"]
    ]
    assert result.first_path_relations[-1]["visible_result_quote"] == (
        "the berth map shows the placement"
    )
    assert result.semantic_model_call_count == len(provider.requests) == 2
    assert provider.requests[1].prompt_payload["candidate"] == initial_copy["result"]
    assert initial == initial_copy


def test_review_cannot_remove_a_human_still_used_by_an_event(monkeypatch):
    source, initial = _reviewed_people_response()
    recipient = initial["result"]["facts"]["human_actors"][1]
    review = _review_response(
        fact_corrections=[{"field": "human_actors", "value": [recipient]}]
    )
    provider, clock = _provider(monkeypatch, [initial, review], [20.0, 5.0])

    with pytest.raises(GreenfieldModelAuthoringError):
        author_greenfield_intent(evidence_text=source, provider=provider, clock=clock)

    assert len(provider.requests) == 2


@pytest.mark.parametrize(
    "human_actors",
    [
        "Dock attendant Ivo",
        [{"quote": "Dock attendant Ivo"}],
        [{"quote": "Dock attendant Ivo", "occurrence": 0}],
        [{"quote": "Invented reviewer", "occurrence": 1}],
    ],
)
def test_review_rejects_malformed_or_out_of_source_human_facts(
    monkeypatch, human_actors,
):
    initial = _response(_source())
    review = _review_response(
        fact_corrections=[{"field": "human_actors", "value": human_actors}]
    )
    provider, clock = _provider(monkeypatch, [initial, review], [20.0, 5.0])

    with pytest.raises(GreenfieldModelAuthoringError):
        author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)

    assert len(provider.requests) == 2


def test_review_can_clear_wrong_opportunity_only_with_whole_targeted_assumption(
    monkeypatch,
):
    initial = _response(_source())
    initial["result"]["facts"]["opportunity"] = {
        "quote": "Dock attendant Ivo enters a vessel tag",
        "occurrence": 1,
    }
    assumption = {
        "applies_to": "opportunity",
        "statement": "A reviewable berth workflow is the worthwhile improvement.",
    }
    review = _review_response(
        fact_corrections=[{"field": "opportunity", "value": None}],
        assumptions=[assumption],
    )
    provider, clock = _provider(monkeypatch, [initial, review], [20.0, 5.0])

    result = author_greenfield_intent(
        evidence_text=_source(), provider=provider, clock=clock
    )

    assert result.intent["opportunity"] == ""
    assert result.intent["assumptions"] == [assumption]
    assert result.intent["product_story"] == (
        initial["result"]["facts"]["product_story"]["quote"]
    )
    assert result.semantic_model_call_count == len(provider.requests) == 2
    assert provider.requests[1].prompt_payload["candidate"] == initial["result"]


@pytest.mark.parametrize(
    "review",
    [
        _review_response(
            fact_corrections=[{"field": "opportunity", "value": None}],
        ),
        _review_response(assumptions=[{
            "applies_to": "opportunity",
            "statement": "A reviewable berth workflow is the worthwhile improvement.",
        }]),
    ],
)
def test_review_preserves_decision_fact_assumption_xor(monkeypatch, review):
    provider, clock = _provider(
        monkeypatch, [_response(_source()), review], [20.0, 5.0]
    )

    with pytest.raises(GreenfieldModelAuthoringError):
        author_greenfield_intent(
            evidence_text=_source(), provider=provider, clock=clock
        )

    assert len(provider.requests) == 2


def test_review_cannot_erase_valid_components_or_silently_accept_the_original(monkeypatch):
    invalid_review = _review_response(components=[])
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
    provider, clock = _provider(
        monkeypatch, [_conflicting_response(), _component_correction()], [45.0, 11.0]
    )
    with pytest.raises(GreenfieldModelAuthoringError, match="exceeded"):
        author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    assert len(provider.requests) == 2
    assert provider.requests[1].timeout_seconds == 10.0


@pytest.mark.parametrize("review", [
    None,
    {},
    {
        "fact_corrections": [],
        "assumptions": None,
        "components": None,
        "events": [],
    },
    _review_response(components=[{
        "owner_fact_quote": "Berth map",
        "responsibilities": [
            {"quote": "This quote is not in the source", "occurrence": 1},
        ],
    }]),
])
def test_invalid_correction_fails_without_another_call(monkeypatch, review):
    provider, clock = _provider(monkeypatch, [_conflicting_response(), review], [20.0, 5.0])
    with pytest.raises(GreenfieldModelAuthoringError):
        author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    assert len(provider.requests) == 2


@pytest.mark.parametrize(
    "review",
    [
        {
            "product_story": _response(_source())["result"]["facts"]["product_story"],
            "components": _response(_source())["result"]["components"],
            "human_actors": _response(_source())["result"]["facts"]["human_actors"],
        },
        _review_response(
            fact_corrections=[{"field": "unknown_fact", "value": []}]
        ),
        _review_response(
            fact_corrections=[
                {
                    "field": "title",
                    "value": _response(_source())["result"]["facts"]["title"],
                },
                {
                    "field": "title",
                    "value": _response(_source())["result"]["facts"]["title"],
                },
            ]
        ),
        _review_response(fact_corrections=[{"field": "title"}]),
        _review_response(
            fact_corrections=[{"field": "title", "value": None}]
        ),
        _review_response(
            fact_corrections=[{"field": "human_actors", "value": None}]
        ),
        {
            "fact_corrections": None,
            "assumptions": None,
            "components": None,
        },
    ],
    ids=(
        "legacy-three-field-response",
        "unknown-field",
        "duplicate-field",
        "malformed-row",
        "non-nullable-singular-null",
        "repeated-field-null",
        "null-correction-list",
    ),
)
def test_sparse_review_contract_rejects_legacy_unknown_duplicate_and_null_shapes(
    monkeypatch, review,
):
    provider, clock = _provider(
        monkeypatch, [_response(_source()), review], [20.0, 5.0]
    )

    with pytest.raises(GreenfieldModelAuthoringError):
        author_greenfield_intent(
            evidence_text=_source(), provider=provider, clock=clock
        )

    assert len(provider.requests) == 2


def test_repeated_ownership_conflict_does_not_start_a_repair_loop(monkeypatch):
    invalid = _conflicting_response()
    review = _review_response(components=invalid["result"]["components"])
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
    review = _component_correction()
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
    assert retained["source_review"]["request"]["validation_error"] == (
        provider.requests[1].prompt_payload["validation_error"]
    )
    expected = deepcopy(initial)
    expected["result"]["components"] = review["components"]
    assert retained["response"] == expected


def test_source_review_replaces_invocation_claim_without_changing_workflow(monkeypatch):
    source = "Please propose a workspace. " + _source()
    initial = _response(source)
    initial["result"]["facts"]["product_story"] = {
        "quote": "Please propose a workspace.", "occurrence": 1,
    }
    valid_story = _response(_source())["result"]["facts"]["product_story"]
    review = _review_response(
        fact_corrections=[{"field": "product_story", "value": valid_story}]
    )
    provider, clock = _provider(monkeypatch, [initial, review], [20.0, 6.0])

    result = author_greenfield_intent(evidence_text=source, provider=provider, clock=clock)

    assert result.intent["product_story"] == valid_story["quote"]
    assert result.intent["first_path"] == "\n".join(
        row["quote"] for row in initial["result"]["facts"]["first_path"]
    )
    assert result.semantic_model_call_count == 2


def test_source_review_cannot_rewrite_a_protected_field(monkeypatch):
    review = _review_response(
        fact_corrections=[{
            "field": "first_path",
            "value": _response(_source())["result"]["facts"]["first_path"],
        }]
    )
    provider, clock = _provider(monkeypatch, [_response(_source()), review], [20.0, 6.0])
    with pytest.raises(GreenfieldModelAuthoringError, match="protected"):
        author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    assert len(provider.requests) == 2
