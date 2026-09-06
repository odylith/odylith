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
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    RESCUE_PROFILE_ID,
    STANDARD_PROFILE_ID,
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


def _review_response(*corrections):
    return {"result": {"corrections": deepcopy(list(corrections))}}


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
    return _review_response({"path": "components", "value": result["components"]})


def _provider(monkeypatch, responses, durations):
    clock = Clock()
    monkeypatch.setattr(greenfield_model_source_review, "monotonic", clock)
    return Provider(responses, durations, clock), clock


@pytest.mark.parametrize("durations,review_timeout", [([20.0, 7.0], 35.0), ([29.0, 4.0], 26.0)])
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
    assert first.timeout_seconds == 30.0
    assert review.timeout_seconds == review_timeout
    assert (first.model, first.reasoning_effort) == ("gpt-5.6-terra", "low")
    assert (review.model, review.reasoning_effort) == ("gpt-5.6-sol", "medium")
    assert review.schema_name == "greenfield_semantic_source_review"
    assert review.prompt_payload["candidate"] == original["result"]
    assert review.prompt_payload["validation_error"] == (
        "Greenfield authoring assigned a non-product event as a component responsibility"
    )
    responsibility = next(
        row
        for row in review.prompt_payload["resolved_citations"]
        if row["path"] == "/components/0/responsibilities/0"
    )
    assert responsibility["quote"] == "Dock attendant Ivo enters a vessel tag"
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
    assert review == {"result": {"corrections": []}}
    payload = provider.requests[1].prompt_payload
    assert payload["evidence"] == _source()
    assert payload["candidate"] == initial["result"]
    assert payload["resolved_citations"]
    assert result.intent["title"] == initial["result"]["facts"]["title"]["quote"]
    assert result.intent["first_path"] == "\n".join(
        row["quote"] for row in initial["result"]["facts"]["first_path"]
    )
    assert result.intent["product_story"] == initial["result"]["facts"]["product_story"]["quote"]
    assert result.intent["component_responsibilities"] == ["Record berth occupancy"]


def test_author_and_reviewer_share_every_mutable_fact_and_whole_list_contract(monkeypatch):
    provider, clock = _provider(monkeypatch, [_response(_source()), _review_response()], [10.0, 5.0])
    author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    author_request, reviewer = provider.requests
    authored_schema = author_request.output_schema["properties"]["result"]["anyOf"][0]
    authored_properties = authored_schema["properties"]
    shared_schemas = {
        **{
            f"facts.{field}": schema
            for field, schema in authored_properties["facts"]["properties"].items()
        },
        **{
            field: schema
            for field, schema in authored_properties.items()
            if field not in {"facts", "status"}
        },
    }
    review_outcomes = reviewer.output_schema["properties"]["result"]["anyOf"]
    assert review_outcomes[1] is author_request.output_schema["properties"]["result"]["anyOf"][1]
    branches = review_outcomes[0]["properties"]["corrections"]["items"]["anyOf"]
    branch_by_path = {row["properties"]["path"]["const"]: row for row in branches}
    assert set(branch_by_path) == set(shared_schemas)
    assert {"facts.first_path", "events", "terminal", "assumptions", "components"} <= set(
        branch_by_path
    )
    assert "status" not in branch_by_path
    for path, branch in branch_by_path.items():
        assert branch["properties"]["value"] is shared_schemas[path]
    assert authored_properties["components"]["minItems"] == 1


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
    assert "resolved_citations is the compiler's read-only binding view" in reviewed.system_prompt
    assert "Occurrences count literal substring matches" in reviewed.system_prompt
    assert "Preserve a defensible, role-correct, consumer-usable source-grounded choice" in reviewed.system_prompt
    assert "Correct material meaning, custody and usefulness defects" in reviewed.system_prompt
    assert "A semantically sound usable package should return no corrections." in reviewed.system_prompt


def test_source_review_requires_resolved_citations(monkeypatch):
    provider, _clock = _provider(monkeypatch, [], [])

    with pytest.raises(TypeError, match="resolved_citations"):
        greenfield_model_source_review.review_semantic_source_claims(
            _response(_source()),
            evidence_text=_source(),
            provider=provider,
            profile_id=STANDARD_PROFILE_ID,
            remaining_seconds=25.0,
            observation={},
            authored_schemas={},
            clarification_schema={},
        )

    assert provider.requests == []


def test_resolved_context_exposes_prefix_collision_without_automatic_repair(
    monkeypatch,
):
    source = "Dock attendant Ivohip. " + _source()
    initial = _response(source)
    corrected_actor = {"quote": "Dock attendant Ivo", "occurrence": 2}
    review = _review_response(
        {"path": "facts.human_actors", "value": [corrected_actor]}
    )
    provider, clock = _provider(monkeypatch, [initial, review], [10.0, 5.0])

    result = author_greenfield_intent(
        evidence_text=source, provider=provider, clock=clock
    )

    bound_actor = next(
        row
        for row in provider.requests[1].prompt_payload["resolved_citations"]
        if row["path"] == "/facts/human_actors/0"
    )
    assert bound_actor == {
        "path": "/facts/human_actors/0",
        "quote": "Dock attendant Ivo",
        "occurrence": 1,
        "source_start_byte": 0,
        "source_end_byte": 18,
        "before": "",
        "after": "hip. " + _source()[:59],
    }
    selected_actor = next(
        row
        for row in result.source_spans
        if row["projection_path"] == "/human_actors/0"
    )
    assert selected_actor["source_start_byte"] == source.index(
        "Dock attendant Ivo", 1
    )

    unchanged_provider, unchanged_clock = _provider(
        monkeypatch, [initial, _review_response()], [10.0, 5.0]
    )
    unchanged = author_greenfield_intent(
        evidence_text=source,
        provider=unchanged_provider,
        clock=unchanged_clock,
    )
    unchanged_actor = next(
        row
        for row in unchanged.source_spans
        if row["projection_path"] == "/human_actors/0"
    )
    assert unchanged_actor["source_start_byte"] == 0


def test_resolved_context_is_unicode_safe(monkeypatch):
    source = "🧭" * 70 + " " + _source() + " café"
    initial = _response(source)
    provider, clock = _provider(
        monkeypatch, [initial, _review_response()], [10.0, 5.0]
    )

    author_greenfield_intent(evidence_text=source, provider=provider, clock=clock)

    title = next(
        row
        for row in provider.requests[1].prompt_payload["resolved_citations"]
        if row["path"] == "/facts/title"
    )
    encoded = source.encode("utf-8")
    assert encoded[title["source_start_byte"]:title["source_end_byte"]].decode() == (
        title["quote"]
    )
    assert title["before"] == "🧭" * 63 + " "
    assert len(title["before"]) == 64
    assert len(title["after"]) <= 64


def test_review_keeps_recipient_human_while_removing_cross_field_external_noise(
    monkeypatch,
):
    source, initial = _reviewed_people_response()
    initial_copy = deepcopy(initial)
    performing, recipient, _purpose_fragment = initial["result"]["facts"]["human_actors"]
    external_system = initial["result"]["facts"]["external_systems"][0]
    review = _review_response(
        {"path": "facts.human_actors", "value": [performing, recipient]},
        {"path": "facts.external_systems", "value": [external_system]},
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
        {"path": "facts.human_actors", "value": [recipient]}
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
        {"path": "facts.human_actors", "value": human_actors}
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
        {"path": "facts.opportunity", "value": None},
        {"path": "assumptions", "value": [assumption]},
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
        _review_response({"path": "facts.opportunity", "value": None}),
        _review_response({
            "path": "assumptions",
            "value": [{
                "applies_to": "opportunity",
                "statement": "A reviewable berth workflow is the worthwhile improvement.",
            }],
        }),
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
    invalid_review = _review_response({"path": "components", "value": []})
    provider, clock = _provider(monkeypatch, [_response(_source()), invalid_review], [20.0, 13.0])
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
        monkeypatch, [_conflicting_response(), _component_correction()], [25.0, 31.0]
    )
    with pytest.raises(GreenfieldModelAuthoringError, match="exceeded"):
        author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    assert len(provider.requests) == 2
    assert provider.requests[1].timeout_seconds == 30.0


@pytest.mark.parametrize("review", [
    None,
    {},
    {"corrections": [], "events": []},
    _review_response({
        "path": "components",
        "value": [{
            "owner_fact_quote": "Berth map",
            "responsibilities": [
                {"quote": "This quote is not in the source", "occurrence": 1},
            ],
        }],
    }),
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
        _review_response({"path": "facts.unknown_fact", "value": []}),
        _review_response(
            {
                "path": "facts.title",
                "value": _response(_source())["result"]["facts"]["title"],
            },
            {
                "path": "facts.title",
                "value": _response(_source())["result"]["facts"]["title"],
            },
        ),
        {"result": {"corrections": [{"path": "facts.title"}]}},
        _review_response({"path": "facts.title", "value": None}),
        _review_response({"path": "facts.human_actors", "value": None}),
        {"result": {"corrections": None}},
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
    review = _review_response(
        {"path": "components", "value": invalid["result"]["components"]}
    )
    provider, clock = _provider(monkeypatch, [invalid, review], [20.0, 5.0])
    with pytest.raises(GreenfieldModelAuthoringError):
        author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)
    assert len(provider.requests) == 2


def test_source_review_role_mismatch_fails_without_a_third_call(monkeypatch):
    class MismatchedRoleProvider(Provider):
        def generate_structured(self, *, request):
            response = super().generate_structured(request=request)
            self.last_request_model = request.model
            self.last_request_reasoning_effort = request.reasoning_effort
            if len(self.requests) == 2:
                self.last_request_reasoning_effort = "high"
            return response

    clock = Clock()
    monkeypatch.setattr(greenfield_model_source_review, "monotonic", clock)
    provider = MismatchedRoleProvider(
        [_response(_source()), _review_response()], [20.0, 5.0], clock
    )

    with pytest.raises(ValueError, match="pinned Greenfield model profile"):
        author_greenfield_intent(
            evidence_text=_source(), provider=provider, clock=clock
        )

    assert len(provider.requests) == 2


def test_source_review_observes_pinned_role_before_and_after_call(monkeypatch):
    observed = []
    require_observation = (
        greenfield_model_source_review.require_greenfield_model_profile_observation
    )

    def record_observation(**values):
        observed.append(values)
        return require_observation(**values)

    monkeypatch.setattr(
        greenfield_model_source_review,
        "require_greenfield_model_profile_observation",
        record_observation,
    )
    provider, clock = _provider(
        monkeypatch, [_response(_source()), _review_response()], [20.0, 5.0]
    )

    author_greenfield_intent(evidence_text=_source(), provider=provider, clock=clock)

    assert len(observed) == 2
    assert all(row["request_role"] == "source_review" for row in observed)
    assert all(row["model"] == "gpt-5.6-sol" for row in observed)
    assert all(row["reasoning_effort"] == "medium" for row in observed)
    assert all(row["effective_timeout_seconds"] == 35.0 for row in observed)


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
    expected["result"]["components"] = review["result"]["corrections"][0]["value"]
    assert retained["response"] == expected


def test_source_review_replaces_invocation_claim_without_changing_workflow(monkeypatch):
    source = "Please propose a workspace. " + _source()
    initial = _response(source)
    initial["result"]["facts"]["product_story"] = {
        "quote": "Please propose a workspace.", "occurrence": 1,
    }
    valid_story = _response(_source())["result"]["facts"]["product_story"]
    review = _review_response(
        {"path": "facts.product_story", "value": valid_story}
    )
    provider, clock = _provider(monkeypatch, [initial, review], [20.0, 6.0])

    result = author_greenfield_intent(evidence_text=source, provider=provider, clock=clock)

    assert result.intent["product_story"] == valid_story["quote"]
    assert result.intent["first_path"] == "\n".join(
        row["quote"] for row in initial["result"]["facts"]["first_path"]
    )
    assert result.semantic_model_call_count == 2


def test_source_review_jointly_replaces_first_path_events_and_terminal(monkeypatch):
    complete = _response(_source())
    initial = deepcopy(complete)
    initial["result"]["facts"]["first_path"] = [
        complete["result"]["facts"]["first_path"][1]
    ]
    initial["result"]["events"] = [complete["result"]["events"][1]]
    initial["result"]["terminal"] = {
        "result_quote": "berth occupancy",
        "result_occurrence": 2,
    }
    review = _review_response(
        {"path": "facts.first_path", "value": complete["result"]["facts"]["first_path"]},
        {"path": "events", "value": complete["result"]["events"]},
        {"path": "terminal", "value": complete["result"]["terminal"]},
    )
    provider, clock = _provider(monkeypatch, [initial, review], [20.0, 6.0])

    result = author_greenfield_intent(
        evidence_text=_source(), provider=provider, clock=clock
    )

    assert result.intent["first_path"] == "\n".join(
        row["quote"] for row in complete["result"]["facts"]["first_path"]
    )
    assert [row["action_verb_quote"] for row in result.first_path_relations] == [
        "enters", "records", "shows"
    ]
    assert result.first_path_relations[-1]["visible_result_quote"] == (
        "the berth map shows the placement"
    )
    assert len(provider.requests) == result.semantic_model_call_count == 2


@pytest.mark.parametrize("shared_budget,initial_cap", [(80.0, 60.0), (40.0, 20.0)])
def test_rescue_reserves_review_inside_original_window(monkeypatch, shared_budget, initial_cap):
    provider, clock = _provider(
        monkeypatch, [_response(_source()), _review_response()], [initial_cap - 1.0, 19.0]
    )
    result = author_greenfield_intent(
        evidence_text=_source(), provider=provider, clock=clock,
        model_profile_id=RESCUE_PROFILE_ID, timeout_seconds=shared_budget,
    )
    assert result.effective_timeout_seconds == shared_budget
    assert result.elapsed_seconds == shared_budget - 2.0
    assert result.tier == "rescue"
    assert result.semantic_model_call_count == 2
    assert [request.timeout_seconds for request in provider.requests] == [initial_cap, 21.0]
    assert [request.model for request in provider.requests] == ["gpt-5.6-terra", "gpt-5.6-sol"]
    assert [request.reasoning_effort for request in provider.requests] == ["medium", "high"]


def test_rescue_rejects_initial_overrun_before_review_or_acceptance(monkeypatch):
    provider, clock = _provider(monkeypatch, [_response(_source())], [60.001])
    with pytest.raises(GreenfieldModelAuthoringError, match="declared time window"):
        author_greenfield_intent(
            evidence_text=_source(), provider=provider, clock=clock,
            model_profile_id=RESCUE_PROFILE_ID,
        )
    assert len(provider.requests) == 1
    assert provider.requests[0].timeout_seconds == 60.0


def test_rescue_rejects_insufficient_shared_budget_without_a_provider_call(monkeypatch):
    provider, clock = _provider(monkeypatch, [], [])
    with pytest.raises(GreenfieldModelAuthoringError, match="reserved source review"):
        author_greenfield_intent(
            evidence_text=_source(), provider=provider, clock=clock,
            model_profile_id=RESCUE_PROFILE_ID, timeout_seconds=20.0,
        )
    assert provider.requests == []


def test_rescue_proof_distinguishes_actual_initial_cap_from_shared_window(tmp_path, monkeypatch):
    provider, clock = _provider(monkeypatch, [_response(_source()), _review_response()], [36.0, 7.0])
    observation = tmp_path / "observation.json"
    with observation.open("wb") as output:
        monkeypatch.setenv(GREENFIELD_MODEL_PROOF_FD_ENV, str(output.fileno()))
        result = author_greenfield_intent(
            evidence_text=_source(), provider=provider, clock=clock, model_profile_id=RESCUE_PROFILE_ID,
        )
    retained = json.loads(observation.read_text())
    assert result.effective_timeout_seconds == 80.0
    assert retained["initial_authoring"] == {
        "profile_id": RESCUE_PROFILE_ID, "timeout_seconds": 60.0,
        "elapsed_seconds": 36.0, "model": "gpt-5.6-terra", "reasoning_effort": "medium",
        "request_role": "initial_authoring",
        "provider": {
            "provider": "codex-cli", "code": "", "detail": "",
            "model": "gpt-5.6-terra", "reasoning_effort": "medium",
        },
    }
    assert retained["source_review"]["timeout_seconds"] == 44.0
    assert retained["source_review"]["elapsed_seconds"] == 7.0
    assert retained["source_review"]["profile_id"] == RESCUE_PROFILE_ID
    assert retained["source_review"]["request_role"] == "source_review"
    assert retained["source_review"]["model"] == "gpt-5.6-sol"
    assert retained["source_review"]["reasoning_effort"] == "high"
