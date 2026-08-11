from __future__ import annotations

import json

from odylith.runtime.domain_intelligence import greenfield_experience
from odylith.runtime.domain_intelligence import proposal_memory
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)


def test_accepted_memory_and_handoff_strip_editorial_first_path_framing() -> None:
    raw_first_path = (
        "A person records one entry and sees a trend. That loop - log, repeat, see the pattern - is the smallest "
        "version of the whole product working end to end."
    )
    proposal = {
        "apply_semantic_input": {"first_path": raw_first_path},
        "intent": {"first_path": raw_first_path},
        "semantic_model": {},
    }

    accepted = proposal_memory._accepted_memory_proposal(proposal, repo_root=None)

    assert "smallest version of the whole product" not in accepted["intent"]["first_path"]
    assert "smallest version of the whole product" not in greenfield_experience._first_path_summary(proposal)


def test_accepted_memory_excludes_private_product_intent_authority_without_mutating_proposal() -> None:
    raw_prompt = "Build a customer recovery desk from this private operator evidence."
    authority = {
        "version": "odylith.product_intent_authority.v1",
        "source_spans": [{"span_id": "operator:1", "evidence_text": raw_prompt}],
    }
    proposal = {
        "intent": {"title": "Customer Recovery Desk", "first_path": "Support leads triage one delayed order."},
        "semantic_model": {},
        PRODUCT_INTENT_AUTHORITY_KEY: authority,
    }

    accepted = proposal_memory._accepted_memory_proposal(proposal, repo_root=None)

    assert PRODUCT_INTENT_AUTHORITY_KEY not in accepted
    assert raw_prompt not in json.dumps(accepted, sort_keys=True)
    assert proposal[PRODUCT_INTENT_AUTHORITY_KEY] == authority
