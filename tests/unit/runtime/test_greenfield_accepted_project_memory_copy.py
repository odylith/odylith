from __future__ import annotations

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.domain_intelligence.proposal_memory import build_accepted_project_source_payload


def test_accepted_project_memory_normalizes_malformed_terminal_punctuation() -> None:
    payload = build_accepted_project_source_payload(
        proposal={
            "intent": {
                "title": "Disclosure Council",
                "first_path": "A coordinator receives a report and records its review state.",
                "summary": "Release stays bounded to: A coordinator records the review state, .",
                "proof_boundary": "A reviewer verifies the receipt! ,",
                "capability": "A reviewer can verify the receipt? ,",
            },
            "semantic_model": {
                "first_path_contract": {"events": [{"text": "A coordinator receives a report"}]}
            },
        },
        backlog_items=(),
        component_items=(),
        diagram_ids=(),
        release_selector="0.0.1",
        release_id="release-disclosure-0-0-1",
        validation_gate={"status": "passed"},
    )

    intent = payload["proposal"]["intent"]
    assert intent["summary"].endswith("review state.")
    assert intent["proof_boundary"].endswith("receipt!")
    assert intent["capability"].endswith("receipt?")
    assert generated_public_copy_issues("accepted-project memory preview", payload) == ()
