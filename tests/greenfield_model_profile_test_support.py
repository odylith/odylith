"""Production-emitted model observations for provider-free profile proof tests."""

import json
import tempfile

import pytest

from odylith.runtime.domain_intelligence import greenfield_model_intent_authoring as author
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import get_greenfield_model_profile
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider, authored_response, clarification_response,
)


def sealed_profile_observation(profile_id, *, shared_timeout=None):
    profile = get_greenfield_model_profile(profile_id)
    return {
        "profile_id": profile_id, "provider": profile.provider, "model": profile.model,
        "reasoning_effort": profile.reasoning_effort, "authoring_tier": profile.repair_tier,
        "effective_timeout_seconds": profile.model_timeout_seconds if shared_timeout is None else shared_timeout,
    }


def production_stage_observation(
    profile_id, *, response_kind="authored", shared_timeout=None, reviewed=False,
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
        "internal_systems": ["Receipt view"],
        "component_responsibilities": ["Display the receipt"],
    }
    source = ". ".join(row for value in intent.values()
                       for row in (value if isinstance(value, list) else [value])) + "."
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

    class TimedProvider(StructuredAuthoringProvider):
        def generate_structured(self, *, request):
            now[0] += 10.0 if request.schema_name == "greenfield_intent_authoring" else 1.0
            return super().generate_structured(request=request)

    provider = TimedProvider(response)
    reviewer = TimedProvider({"admissible": True, "issues": []})
    with tempfile.TemporaryFile() as output, pytest.MonkeyPatch.context() as patch:
        patch.setenv(author.GREENFIELD_MODEL_PROOF_FD_ENV, str(output.fileno()))
        result = author.author_greenfield_intent(
            evidence_text=source, provider=provider, model_profile_id=profile_id,
            timeout_seconds=shared_timeout, clock=lambda: now[0],
            review_provider_factory=lambda: reviewer,
        )
        output.seek(0)
        stage = json.load(output)
    assert provider.calls == 1
    assert reviewer.calls == (1 if response_kind == "authored" else 0)
    assert stage["semantic_model_call_count"] == result.semantic_model_call_count
    return stage


def _historical_review_observation(profile_id, response_kind):
    """Retain the old matrix's demoted-clarification fixture solely for refusal."""
    profile = get_greenfield_model_profile(profile_id)
    version = author.GREENFIELD_INTENT_AUTHORING_VERSION
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
