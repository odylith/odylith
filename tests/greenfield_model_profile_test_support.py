"""Production-emitted model observations for provider-free profile proof tests."""

import json
import tempfile

import pytest

from odylith.runtime.domain_intelligence import greenfield_participant_first_authoring as author
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import get_greenfield_model_profile
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    AdmittingReviewProvider,
    ParticipantSelectionProvider,
    RemainingCandidateProvider,
    StructuredAuthoringProvider,
    admitted_review_response,
    authored_response,
    clarification_response,
)


def sealed_profile_observation(profile_id, *, shared_timeout=None):
    profile = get_greenfield_model_profile(profile_id)
    timeout = profile.model_timeout_seconds if shared_timeout is None else shared_timeout
    return {
        "participant_selection": {
            "profile_id": profile_id, "provider": profile.provider,
            "model": profile.participant_model,
            "reasoning_effort": profile.participant_reasoning_effort,
            "authoring_tier": profile.repair_tier,
            "effective_timeout_seconds": timeout,
        },
        "remaining_candidate_authoring": {
            "profile_id": profile_id, "provider": profile.provider, "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
            "authoring_tier": profile.repair_tier,
            "effective_timeout_seconds": timeout - 5.0,
        },
    }


def production_stage_observation(
    profile_id, *, response_kind="authored", shared_timeout=None, reviewed=False,
    evidence_text=None, revised=False,
):
    """Capture the real author/review proof FD; historical negatives stay explicit."""
    if reviewed:
        return _historical_review_observation(profile_id, response_kind)
    intent = {
        "title": "Receipt Desk",
        "product_story": "The product displays the receipt",
        "state_object": "receipt",
        "first_path": "The product displays the receipt",
        "proof_boundary": "The product displays the receipt",
        "problem": "Operators cannot find their receipt",
        "customer": "Operators",
        "opportunity": "A receipt is available for review",
        "product_view": "Operators can see their receipt",
        "human_actors": ["Operators"],
        "internal_systems": ["Receipt view"],
        "component_responsibilities": ["Display the receipt"],
    }
    source = ". ".join(row for value in intent.values()
                       for row in (value if isinstance(value, list) else [value])) + "."
    if evidence_text is not None:
        source = evidence_text
    response = (authored_response(intent, evidence_text=source,
                                  component_responsibility_owners=["Receipt view"], first_path_relations=[{
        "order": 1, "actor_kind": "product",
        "owner_system_quote": "Receipt view",
        "event_quote": intent["first_path"], "action_verb_quote": "displays",
        "target_quote": "the receipt", "visible_result_quote": intent["proof_boundary"],
    }]) if response_kind == "authored" else clarification_response(
        question="", material_dimension="first_path", evidence_quotes=[],
    ))
    now = [0.0]

    class TimedRemainingProvider(RemainingCandidateProvider):
        def generate_structured(self, *, request):
            now[0] += 10.0
            if not revised:
                return super().generate_structured(request=request)
            assert getattr(request, "schema_name", "") in {
                "greenfield_remaining_candidate_authoring",
                "greenfield_candidate_revision",
            }
            value = StructuredAuthoringProvider.generate_structured(
                self, request=request,
            )
            if isinstance(value, dict):
                result = value.get("result")
                if isinstance(result, dict) and isinstance(result.get("facts"), dict):
                    result["facts"].pop("human_actors", None)
            return value

    class TimedParticipantProvider(ParticipantSelectionProvider):
        def generate_structured(self, *, request):
            now[0] += 5.0
            return super().generate_structured(request=request)

    class TimedReviewProvider(AdmittingReviewProvider):
        responses = (
            {
                "outcome": "denied",
                "issue": {
                    "path": "candidate.accepted_source.facts.opportunity",
                    "reason": "The selected action is not a complete improvement.",
                },
                "clarification": None,
                "admission_witness": None,
            },
            admitted_review_response(result_event_order=1),
        )

        def __init__(self):
            StructuredAuthoringProvider.__init__(
                self,
                admitted_review_response(result_event_order=1),
            )

        def generate_structured(self, *, request):
            now[0] += 1.0
            if not revised:
                return super().generate_structured(request=request)
            self.response = self.responses[self.calls]
            return super().generate_structured(request=request)

    provider = TimedRemainingProvider(response)
    participant = TimedParticipantProvider(response)
    reviewer = TimedReviewProvider()
    with tempfile.TemporaryFile() as output, pytest.MonkeyPatch.context() as patch:
        patch.setenv(author.GREENFIELD_MODEL_PROOF_FD_ENV, str(output.fileno()))
        result = author.author_greenfield_intent(
            evidence_text=source, provider=provider, model_profile_id=profile_id,
            timeout_seconds=shared_timeout, clock=lambda: now[0],
            participant_provider_factory=lambda: participant,
            review_provider_factory=lambda: reviewer,
        )
        output.seek(0)
        stage = json.load(output)
    assert provider.calls == (2 if revised else 1)
    assert participant.calls == 1
    assert reviewer.calls == (2 if revised else 1 if response_kind == "authored" else 0)
    assert stage["semantic_model_call_count"] == result.semantic_model_call_count
    return stage


def _historical_review_observation(profile_id, response_kind):
    """Retain the old matrix's demoted-clarification fixture solely for refusal."""
    profile = get_greenfield_model_profile(profile_id)
    version = GREENFIELD_INTENT_AUTHORING_VERSION
    result = (clarification_response(
        question="", material_dimension="first_path", evidence_quotes=[],
    )["result"] if response_kind == "clarification_required" else {"status": "authored"})
    return {
        "version": "odylith.greenfield.model-proof-observation.v2",
        "authoring_version": version, "semantic_model_call_count": 2,
        "response": {"version": version, "result": result},
        "initial_authoring": {
            "profile_id": profile_id, "request_role": "initial_authoring",
            "model": profile.model, "reasoning_effort": profile.reasoning_effort,
            "timeout_seconds": profile.model_timeout_seconds, "elapsed_seconds": 5.0,
            "provider": {"provider": profile.provider, "model": profile.model,
                         "reasoning_effort": profile.reasoning_effort},
        },
        "initial_response": {"version": version, "result": {"status": "authored"}},
        "source_review": {
            "profile_id": profile_id, "request_role": "source_review",
            "model": "gpt-5.6-sol", "reasoning_effort": "medium",
            "timeout_seconds": profile.model_timeout_seconds - 5.0, "elapsed_seconds": 5.0,
            "provider": {"provider": profile.provider, "model": "gpt-5.6-sol",
                         "reasoning_effort": "medium"},
            "response": {"result": result if response_kind == "clarification_required" else {"corrections": []}},
        },
    }
