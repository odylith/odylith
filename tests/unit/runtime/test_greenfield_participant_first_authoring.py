"""Focused contracts for participant-first Greenfield model ownership."""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_model_intent_authoring
from odylith.runtime.domain_intelligence import greenfield_model_intent_materialization
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    GreenfieldAuthoringClarification,
    GreenfieldModelAuthoredIntent,
)
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelAuthoringError,
    GreenfieldModelRuntimeError,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    GreenfieldClarificationRequired,
    materialize_model_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
)
from odylith.runtime.domain_intelligence.greenfield_participant_first_authoring import (
    GREENFIELD_MODEL_PROOF_FD_ENV,
    GREENFIELD_MODEL_PROOF_OBSERVATION_VERSION,
    MAX_GREENFIELD_SEMANTIC_CALLS,
    author_greenfield_intent,
    join_frozen_greenfield_participants,
    resolve_greenfield_participant_selection,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    AdmittingReviewProvider,
    ParticipantSelectionProvider,
    RemainingCandidateProvider,
    StructuredAuthoringProvider,
    authored_response,
    clarification_response,
)


_INTENT = {
    "title": "Harbor Desk",
    "product_story": "Harbor Desk makes berth occupancy reviewable",
    "state_object": "berth occupancy",
    "first_path": "Dock attendant Ivo records berth occupancy",
    "proof_boundary": "A berth board shows recorded occupancy",
    "problem": "Berth placement is difficult to track",
    "customer": "Dock attendant Ivo",
    "opportunity": "One reviewable berth record",
    "product_view": "Dock attendants can review current berth occupancy",
    "success_metrics": ["Recorded occupancy appears on the berth board"],
    "evidence_requirements": ["Preserve the recorded occupancy evidence"],
    "operational_constraints": ["Council review remains read-only"],
    "component_responsibilities": [],
    "human_actors": ["Dock attendant Ivo", "Council"],
    "external_systems": [],
    "internal_systems": [],
    "assumptions": [],
    "ambiguities": [],
    "non_goals": ["Do not schedule vessels"],
}


def _source() -> str:
    return ". ".join(
        str(row)
        for value in _INTENT.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    ) + "."


def _complete_response() -> dict[str, Any]:
    return authored_response(
        _INTENT,
        evidence_text=_source(),
        first_path_relations=[
            {
                "actor_kind": "human",
                "actor_fact_quote": "Dock attendant Ivo",
                "event_quote": "Dock attendant Ivo records berth occupancy",
                "action_verb_quote": "records",
                "target_quote": "berth occupancy",
                "visible_result_quote": "A berth board shows recorded occupancy",
            }
        ],
    )


def _remaining_response() -> dict[str, Any]:
    response = _complete_response()
    del response["result"]["facts"]["human_actors"]
    return response


class _Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


class _TimedProvider(StructuredAuthoringProvider):
    def __init__(self, response: dict[str, Any], *, clock: _Clock, duration: float) -> None:
        super().__init__(response)
        self.clock = clock
        self.duration = duration

    def generate_structured(self, *, request: object) -> dict[str, Any] | None:
        response = super().generate_structured(request=request)
        self.clock.value += self.duration
        return response


class _InvalidResponseProvider:
    provider_name = "codex-cli"
    last_failure_code = ""
    last_failure_detail = ""
    last_request_model = ""
    last_request_reasoning_effort = ""

    def generate_structured(self, *, request: object) -> object:
        self.last_request_model = str(getattr(request, "model", ""))
        self.last_request_reasoning_effort = str(
            getattr(request, "reasoning_effort", "")
        )
        return ["untrusted raw output"]


class _SequenceProvider(StructuredAuthoringProvider):
    def __init__(self, responses: list[dict[str, Any]], *, clock=None, durations=None) -> None:
        super().__init__(responses[0])
        self.responses = deepcopy(responses)
        self.clock = clock
        self.durations = list(durations or [0.0] * len(responses))

    def generate_structured(self, *, request: object) -> dict[str, Any] | None:
        index = self.calls
        self.response = self.responses[index]
        response = super().generate_structured(request=request)
        if self.clock is not None:
            self.clock.value += self.durations[index]
        return response


class _RevisionAuthorProvider(_SequenceProvider):
    def generate_structured(self, *, request: object) -> dict[str, Any] | None:
        assert getattr(request, "schema_name", "") in {
            "greenfield_remaining_candidate_authoring",
            "greenfield_candidate_revision",
        }
        response = super().generate_structured(request=request)
        if isinstance(response, dict):
            result = response.get("result")
            if isinstance(result, dict) and isinstance(result.get("facts"), dict):
                result["facts"].pop("human_actors", None)
        return response


class _SequenceReviewProvider(_SequenceProvider):
    def generate_structured(self, *, request: object) -> dict[str, Any] | None:
        assert getattr(request, "schema_name", "") == "greenfield_candidate_review"
        return super().generate_structured(request=request)


@pytest.mark.parametrize(
    ("source", "response", "expected_citation", "expected_span"),
    [
        (
            "roles then roles",
            {"human_actors": [{"prefix": "then ", "quote": "roles", "anchor_occurrence": 1}]},
            {"quote": "roles", "occurrence": 2},
            {"quote": "roles", "source_start_byte": 11, "source_end_byte": 16},
        ),
        (
            "équipe then équipe",
            {"human_actors": [{"prefix": "then ", "quote": "équipe", "anchor_occurrence": 1}]},
            {"quote": "équipe", "occurrence": 2},
            {"quote": "équipe", "source_start_byte": 13, "source_end_byte": 20},
        ),
        (
            "aaa",
            {"human_actors": [{"prefix": "a", "quote": "a", "anchor_occurrence": 2}]},
            {"quote": "a", "occurrence": 3},
            {"quote": "a", "source_start_byte": 2, "source_end_byte": 3},
        ),
        ("No people.", {"human_actors": []}, None, None),
    ],
)
def test_selector_resolves_repeated_unicode_overlapping_and_empty_locations(
    source, response, expected_citation, expected_span,
):
    citations, resolved = resolve_greenfield_participant_selection(source, response)
    assert citations == ([] if expected_citation is None else [expected_citation])
    assert resolved == ([] if expected_span is None else [expected_span])


@pytest.mark.parametrize(
    "response",
    [
        {"human_actors": [{"prefix": "", "quote": "", "anchor_occurrence": 1}]},
        {"human_actors": [{"prefix": "", "quote": "roles", "anchor_occurrence": True}]},
        {"human_actors": [{"prefix": "absent ", "quote": "roles", "anchor_occurrence": 1}]},
        {"human_actors": [{"prefix": "", "quote": "roles", "anchor_occurrence": 2}]},
        {"human_actors": [{"prefix": "", "quote": "roles", "anchor_occurrence": 1, "extra": 1}]},
        {"human_actors": [
            {"prefix": "", "quote": "roles", "anchor_occurrence": 1},
            {"prefix": "", "quote": "roles", "anchor_occurrence": 1},
        ]},
    ],
)
def test_selector_rejects_invalid_or_duplicate_locations(response):
    with pytest.raises(GreenfieldModelAuthoringError):
        resolve_greenfield_participant_selection("roles", response)


def test_join_is_exact_and_rejects_author_participant_injection():
    remaining = _remaining_response()
    frozen_remaining = deepcopy(remaining)
    participants = [
        {"quote": "Dock attendant Ivo", "occurrence": 1},
        {"quote": "Council", "occurrence": 1},
    ]
    frozen_participants = deepcopy(participants)
    joined = join_frozen_greenfield_participants(remaining, participants)
    assert joined["result"]["facts"]["human_actors"] == participants
    assert remaining == frozen_remaining
    assert participants == frozen_participants

    injected = deepcopy(remaining)
    injected["result"]["facts"]["human_actors"] = []
    with pytest.raises(GreenfieldModelAuthoringError, match="replace frozen participants"):
        join_frozen_greenfield_participants(injected, participants)


def test_join_rejects_non_mapping_result_as_canonical_authoring_error():
    with pytest.raises(GreenfieldModelAuthoringError, match="cannot be joined"):
        join_frozen_greenfield_participants(
            {"version": GREENFIELD_INTENT_AUTHORING_VERSION, "result": []},
            [],
        )


def test_success_uses_three_roles_and_emits_recomputable_v4_proof(monkeypatch, tmp_path):
    complete = _complete_response()
    selector = ParticipantSelectionProvider(complete)
    remaining = RemainingCandidateProvider(complete)
    reviewer = AdmittingReviewProvider()
    proof_path = tmp_path / "proof.json"
    with proof_path.open("w+b") as proof:
        monkeypatch.setenv(GREENFIELD_MODEL_PROOF_FD_ENV, str(proof.fileno()))
        result = author_greenfield_intent(
            evidence_text=_source(),
            provider=remaining,
            participant_provider_factory=lambda: selector,
            review_provider_factory=lambda: reviewer,
            clock=lambda: 0.0,
        )
        proof.flush()
        proof.seek(0)
        retained = json.loads(proof.read())

    assert isinstance(result, GreenfieldModelAuthoredIntent)
    assert result.semantic_model_call_count == 3
    assert MAX_GREENFIELD_SEMANTIC_CALLS == 5
    assert selector.calls == remaining.calls == reviewer.calls == 1
    assert selector.requests[0].schema_name == "greenfield_participant_selection"
    assert remaining.requests[0].schema_name == "greenfield_remaining_candidate_authoring"
    assert reviewer.requests[0].schema_name == "greenfield_candidate_review"
    facts_schema = remaining.requests[0].output_schema["properties"]["result"]["anyOf"][0]["properties"]["facts"]
    assert "human_actors" not in facts_schema["properties"]
    assert "human_actors" not in facts_schema["required"]
    assert "frozen_human_actors list is the only participant selection" in remaining.requests[0].system_prompt
    assert "actor_fact` field `human_actors` and one-based" in remaining.requests[0].system_prompt
    assert "Bind performing human events to its exact quote values" not in remaining.requests[0].system_prompt
    assert "select proof_boundary only under the source-proof rule above" in remaining.requests[0].system_prompt
    assert "set both facts.proof_boundary and terminal to null" in remaining.requests[0].system_prompt
    assert "proof_boundary, human_actors and first_path" not in remaining.requests[0].system_prompt
    assert remaining.requests[0].prompt_payload["frozen_human_actors"] == complete["result"]["facts"]["human_actors"]
    assert result.intent["human_actors"] == _INTENT["human_actors"]
    assert set(retained) == {
        "version", "authoring_version", "request", "semantic_model_call_count",
        "participant_selection", "remaining_candidate_authoring", "joined_candidate",
        "candidate_review",
    }
    assert retained["version"] == GREENFIELD_MODEL_PROOF_OBSERVATION_VERSION
    assert retained["semantic_model_call_count"] == 3
    assert retained["participant_selection"]["response"] == selector.response
    assert retained["remaining_candidate_authoring"]["response"] == _remaining_response()
    assert retained["joined_candidate"] == complete
    citations, resolved = resolve_greenfield_participant_selection(
        _source(), retained["participant_selection"]["response"]
    )
    assert retained["participant_selection"]["resolved"] == resolved
    assert join_frozen_greenfield_participants(
        retained["remaining_candidate_authoring"]["response"], citations
    ) == retained["joined_candidate"]


@pytest.mark.parametrize("material_dimension", ["human_actors", "proof_boundary"])
def test_clarification_stops_after_two_calls_without_review(monkeypatch, tmp_path, material_dimension):
    complete = _complete_response()
    selector = ParticipantSelectionProvider(complete)
    remaining = StructuredAuthoringProvider(
        clarification_response(
            question="unused",
            material_dimension=material_dimension,
            evidence_quotes=[],
        )
    )
    reviewer = AdmittingReviewProvider()
    proof_path = tmp_path / "proof.json"
    with proof_path.open("w+b") as proof:
        monkeypatch.setenv(GREENFIELD_MODEL_PROOF_FD_ENV, str(proof.fileno()))
        result = author_greenfield_intent(
            evidence_text=_source(),
            provider=remaining,
            participant_provider_factory=lambda: selector,
            review_provider_factory=lambda: reviewer,
            clock=lambda: 0.0,
        )
        proof.flush()
        proof.seek(0)
        retained = json.loads(proof.read())

    assert isinstance(result, GreenfieldAuthoringClarification)
    assert result.required_fields == (material_dimension,)
    assert result.consistency_status == "material_ambiguity"
    assert result.semantic_model_call_count == 2
    assert selector.calls == remaining.calls == 1
    assert reviewer.calls == 0
    assert set(retained) == {
        "version", "authoring_version", "request", "semantic_model_call_count",
        "participant_selection", "remaining_candidate_authoring",
    }
    assert retained["semantic_model_call_count"] == 2


def test_invalid_selector_stops_after_one_call_and_retains_failure(monkeypatch, tmp_path):
    selector = StructuredAuthoringProvider(
        {"human_actors": [{"prefix": "absent ", "quote": "person", "anchor_occurrence": 1}]}
    )
    remaining = RemainingCandidateProvider(_complete_response())
    reviewer = AdmittingReviewProvider()
    proof_path = tmp_path / "proof.json"
    with proof_path.open("w+b") as proof:
        monkeypatch.setenv(GREENFIELD_MODEL_PROOF_FD_ENV, str(proof.fileno()))
        with pytest.raises(GreenfieldModelAuthoringError):
            author_greenfield_intent(
                evidence_text=_source(),
                provider=remaining,
                participant_provider_factory=lambda: selector,
                review_provider_factory=lambda: reviewer,
                clock=lambda: 0.0,
            )
        proof.flush()
        proof.seek(0)
        retained = json.loads(proof.read())

    assert selector.calls == 1
    assert remaining.calls == reviewer.calls == 0
    assert set(retained) == {
        "version", "authoring_version", "request", "semantic_model_call_count",
        "participant_selection", "failure",
    }
    assert retained["semantic_model_call_count"] == 1
    assert retained["failure"]["stage"] == "participant_selection"


def test_non_mapping_selector_response_is_not_retained_in_failure_proof(
    monkeypatch, tmp_path
):
    remaining = RemainingCandidateProvider(_complete_response())
    proof_path = tmp_path / "proof.json"
    with proof_path.open("w+b") as proof:
        monkeypatch.setenv(GREENFIELD_MODEL_PROOF_FD_ENV, str(proof.fileno()))
        with pytest.raises(GreenfieldModelAuthoringError, match="invalid response"):
            author_greenfield_intent(
                evidence_text=_source(),
                provider=remaining,
                participant_provider_factory=_InvalidResponseProvider,
                review_provider_factory=AdmittingReviewProvider,
                clock=lambda: 0.0,
            )
        proof.flush()
        proof.seek(0)
        retained = json.loads(proof.read())

    stage = retained["participant_selection"]
    assert stage["response_shape"] == "list"
    assert "response" not in stage
    assert "untrusted raw output" not in proof_path.read_text()
    assert remaining.calls == 0


def test_non_mapping_remaining_response_stops_after_two_calls(monkeypatch, tmp_path):
    selector = ParticipantSelectionProvider(_complete_response())
    reviewer = AdmittingReviewProvider()
    proof_path = tmp_path / "proof.json"
    with proof_path.open("w+b") as proof:
        monkeypatch.setenv(GREENFIELD_MODEL_PROOF_FD_ENV, str(proof.fileno()))
        with pytest.raises(GreenfieldModelAuthoringError, match="invalid response"):
            author_greenfield_intent(
                evidence_text=_source(),
                provider=_InvalidResponseProvider(),
                participant_provider_factory=lambda: selector,
                review_provider_factory=lambda: reviewer,
                clock=lambda: 0.0,
            )
        proof.flush()
        proof.seek(0)
        retained = json.loads(proof.read())

    assert retained["semantic_model_call_count"] == 2
    assert retained["remaining_candidate_authoring"]["response_shape"] == "list"
    assert "response" not in retained["remaining_candidate_authoring"]
    assert "joined_candidate" not in retained
    assert "candidate_review" not in retained
    assert reviewer.calls == 0


def test_three_calls_receive_only_the_shared_deadlines_remaining_time():
    clock = _Clock()
    complete = _complete_response()
    selector = _TimedProvider(
        ParticipantSelectionProvider(complete).response,
        clock=clock,
        duration=2.0,
    )
    remaining = _TimedProvider(
        _remaining_response(),
        clock=clock,
        duration=3.0,
    )
    reviewer = _TimedProvider(
        {"outcome": "admitted", "issue": None, "clarification": None},
        clock=clock,
        duration=1.0,
    )
    result = author_greenfield_intent(
        evidence_text=_source(),
        provider=remaining,
        participant_provider_factory=lambda: selector,
        review_provider_factory=lambda: reviewer,
        timeout_seconds=10.0,
        clock=clock,
    )
    assert isinstance(result, GreenfieldModelAuthoredIntent)
    assert [
        selector.requests[0].timeout_seconds,
        remaining.requests[0].timeout_seconds,
        reviewer.requests[0].timeout_seconds,
    ] == [10.0, 8.0, 5.0]
    assert result.elapsed_seconds == 6.0
    assert result.effective_model_window_seconds == 10.0


def test_reviewer_clarification_stops_participant_authoring_before_staging(
    tmp_path, monkeypatch,
):
    complete = _complete_response()
    selector = ParticipantSelectionProvider(complete)
    author = _RevisionAuthorProvider([complete])
    reviewer = _SequenceReviewProvider([{
        "outcome": "clarification_required",
        "issue": None,
        "clarification": {"material_dimension": "first_path"},
    }])

    def forbidden_stage(**_kwargs: object) -> object:
        raise AssertionError("reviewer clarification must not stage a package")

    monkeypatch.setattr(
        greenfield_model_intent_materialization,
        "stage_validated_authored_intent",
        forbidden_stage,
    )
    receipt: dict[str, Any] = {}
    with pytest.raises(GreenfieldClarificationRequired) as raised:
        materialize_model_authored_intent(
            prompt=_source(),
            repo_root=tmp_path,
            authoring_provider=author,
            participant_provider_factory=lambda: selector,
            review_provider_factory=lambda: reviewer,
            authoring_receipt=receipt,
            clock=lambda: 0.0,
        )

    assert raised.value.required_fields == ("first_path",)
    assert receipt["candidate_review"]["status"] == "clarification_required"
    assert receipt["consistency_assessment"] == {
        "status": "material_ambiguity",
        "source_spans": [],
        "basis": "complete_source_missingness",
    }
    assert reviewer.calls == 1


def test_denial_gets_one_revision_and_fresh_review_within_shared_deadline(
    monkeypatch, tmp_path
):
    clock = _Clock()
    complete = _complete_response()
    revised = _complete_response()
    revised["result"]["facts"]["opportunity"] = None
    revised["result"]["assumptions"].append(
        {
            "applies_to": "opportunity",
            "statement": "One reviewable berth record can improve berth coordination.",
        }
    )
    selector = _TimedProvider(
        ParticipantSelectionProvider(complete).response, clock=clock, duration=1.0
    )
    author = _RevisionAuthorProvider(
        [complete, revised], clock=clock, durations=[2.0, 4.0]
    )
    reviewer = _SequenceReviewProvider(
        [
            {
                "outcome": "denied",
                "issue": {
                    "path": "candidate.accepted_source.facts.opportunity",
                    "reason": "The selected action is not a complete improvement.",
                },
                "clarification": None,
            },
            {"outcome": "admitted", "issue": None, "clarification": None},
        ],
        clock=clock,
        durations=[3.0, 5.0],
    )
    proof_path = tmp_path / "proof.json"
    with proof_path.open("w+b") as proof:
        monkeypatch.setenv(GREENFIELD_MODEL_PROOF_FD_ENV, str(proof.fileno()))
        result = author_greenfield_intent(
            evidence_text=_source(),
            provider=author,
            participant_provider_factory=lambda: selector,
            review_provider_factory=lambda: reviewer,
            timeout_seconds=30.0,
            clock=clock,
        )
        proof.flush()
        proof.seek(0)
        retained = json.loads(proof.read())

    assert isinstance(result, GreenfieldModelAuthoredIntent)
    assert result.semantic_model_call_count == 5
    assert result.intent["opportunity"] == ""
    assert result.rejected_candidate_review["status"] == "denied"
    assert result.candidate_revision["elapsed_seconds"] == 4.0
    assert result.candidate_review["status"] == "admitted"
    assert selector.calls == 1
    assert author.calls == reviewer.calls == 2
    assert [request.timeout_seconds for request in author.requests] == [29.0, 24.0]
    assert [request.timeout_seconds for request in reviewer.requests] == [27.0, 20.0]
    revision_request = author.requests[1]
    assert revision_request.prompt_payload["review_issue"]["path"].endswith(
        ".opportunity"
    )
    assert revision_request.prompt_payload["rejected_candidate"]["result"]["facts"][
        "opportunity"
    ] is not None
    assert "only revision attempt" in revision_request.system_prompt
    assert set(retained) == {
        "version", "authoring_version", "request", "semantic_model_call_count",
        "participant_selection", "remaining_candidate_authoring",
        "rejected_candidate", "rejected_candidate_review", "candidate_revision",
        "joined_candidate", "candidate_review",
    }
    assert retained["semantic_model_call_count"] == 5
    assert retained["rejected_candidate_review"]["response"]["outcome"] == "denied"
    assert retained["candidate_review"]["response"] == {
        "outcome": "admitted", "issue": None, "clarification": None,
    }


def test_revision_receipts_reach_the_staged_candidate_without_expanding_sealed_roles(
    tmp_path,
):
    complete = _complete_response()
    selector = ParticipantSelectionProvider(complete)
    author = _RevisionAuthorProvider([complete, complete])
    reviewer = _SequenceReviewProvider([
        {
            "outcome": "denied",
            "issue": {
                "path": "candidate.accepted_source.facts.opportunity",
                "reason": "The selected action is not a complete improvement.",
            },
            "clarification": None,
        },
        {"outcome": "admitted", "issue": None, "clarification": None},
    ])
    receipt: dict[str, Any] = {}

    candidate = materialize_model_authored_intent(
        prompt=_source(),
        repo_root=tmp_path,
        authoring_provider=author,
        participant_provider_factory=lambda: selector,
        review_provider_factory=lambda: reviewer,
        authoring_receipt=receipt,
        clock=lambda: 0.0,
    )

    assert receipt["semantic_model_call_count"] == 5
    assert receipt["rejected_candidate_review"]["status"] == "denied"
    assert receipt["candidate_revision"]["model_profile"]["model"] == "gpt-6-astra"
    assert receipt["candidate_review"]["status"] == "admitted"
    observed = candidate["product_intent_authority"]["operating_envelope"][
        "model_contract"
    ]["observed"]
    assert set(observed) == {"participant_selection", "remaining_candidate_authoring"}


def test_repeated_review_denial_fails_closed_without_a_second_revision():
    complete = _complete_response()
    selector = ParticipantSelectionProvider(complete)
    author = _RevisionAuthorProvider([complete, complete])
    reviewer = _SequenceReviewProvider(
        [
            {
                "outcome": "denied",
                "issue": {"path": "candidate.accepted_source.facts.opportunity", "reason": "Invalid."},
                "clarification": None,
            },
            {
                "outcome": "denied",
                "issue": {"path": "candidate.accepted_source.source_precedence", "reason": "Still invalid."},
                "clarification": None,
            },
        ]
    )
    with pytest.raises(GreenfieldModelAuthoringError, match="could not be verified"):
        author_greenfield_intent(
            evidence_text=_source(),
            provider=author,
            participant_provider_factory=lambda: selector,
            review_provider_factory=lambda: reviewer,
            clock=lambda: 0.0,
        )
    assert selector.calls == 1
    assert author.calls == reviewer.calls == 2


def test_request_mutation_fails_closed_without_later_calls():
    complete = _complete_response()

    class MutatingProvider(ParticipantSelectionProvider):
        def generate_structured(self, *, request: object) -> dict[str, Any] | None:
            response = super().generate_structured(request=request)
            request.prompt_payload["source"] = "changed"
            return response

    selector = MutatingProvider(complete)
    remaining = RemainingCandidateProvider(complete)
    reviewer = AdmittingReviewProvider()
    with pytest.raises(GreenfieldModelAuthoringError, match="changed its request"):
        author_greenfield_intent(
            evidence_text=_source(),
            provider=remaining,
            participant_provider_factory=lambda: selector,
            review_provider_factory=lambda: reviewer,
            clock=lambda: 0.0,
        )
    assert selector.calls == 1
    assert remaining.calls == reviewer.calls == 0


def test_missing_selector_provider_fails_before_any_model_call():
    remaining = RemainingCandidateProvider(_complete_response())
    reviewer = AdmittingReviewProvider()
    with pytest.raises(GreenfieldModelRuntimeError, match="unavailable"):
        author_greenfield_intent(
            evidence_text=_source(),
            provider=remaining,
            participant_provider_factory=None,
            review_provider_factory=lambda: reviewer,
            clock=lambda: 0.0,
        )
    assert remaining.calls == reviewer.calls == 0


def test_missing_remaining_provider_fails_before_participant_selection(
    monkeypatch, tmp_path
):
    selector = ParticipantSelectionProvider(_complete_response())
    reviewer = AdmittingReviewProvider()
    proof_path = tmp_path / "proof.json"
    with proof_path.open("w+b") as proof:
        monkeypatch.setenv(GREENFIELD_MODEL_PROOF_FD_ENV, str(proof.fileno()))
        with pytest.raises(GreenfieldModelRuntimeError, match="unavailable"):
            author_greenfield_intent(
                evidence_text=_source(),
                provider=None,
                participant_provider_factory=lambda: selector,
                review_provider_factory=lambda: reviewer,
                clock=lambda: 0.0,
            )
        proof.flush()
        proof.seek(0)
        retained = json.loads(proof.read())
    assert selector.calls == reviewer.calls == 0
    assert retained["semantic_model_call_count"] == 0
    assert retained["failure"] == {
        "stage": "provider_discovery",
        "code": "unavailable",
    }


def test_old_two_call_orchestration_is_not_exported():
    assert not hasattr(greenfield_model_intent_authoring, "author_greenfield_intent")
    assert not hasattr(greenfield_model_intent_authoring, "GREENFIELD_MODEL_PROOF_FD_ENV")
    assert MAX_GREENFIELD_SEMANTIC_CALLS == 5
    assert GREENFIELD_INTENT_AUTHORING_VERSION.endswith(".v68")
