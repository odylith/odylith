from __future__ import annotations

import json

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery import (
    confirmation_from_operator_intent,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_project_brief import confirmed_project_brief
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import (
    build_confirmed_greenfield_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_experience import build_next_steps
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import (
    generated_semantic_slop_issues,
)


def test_sparse_title_recovery_does_not_promote_action_fragments_to_actors() -> None:
    confirmation = confirmation_from_operator_intent("model lab notebook", prefer_product_title=True)
    intent = parse_confirmed_intent_text(confirmation)
    actor_labels = [row.split(":", 1)[0] for row in intent["human_actors"]]

    assert actor_labels == ["Representative User"]
    assert "Records" not in actor_labels
    assert "Sees" not in actor_labels

    proposal = build_confirmed_greenfield_proposal(
        prompt="model lab notebook",
        title="Model Lab Notebook",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert "Records: need the product" not in rendered
    assert "Sees: need the product" not in rendered
    assert generated_semantic_slop_issues(proposal) == []


def test_thin_malformed_confirmation_recovers_from_rich_prompt() -> None:
    prompt = (
        "Create a greenfield product for municipal permit clerks to intake permit applications, "
        "validate zoning attachments, route reviewer decisions, and show applicants a clear approval packet "
        "without issuing permits or promising legal approval."
    )
    confirmation = """# Product Intent Confirmation

## Product story
Make this readable as one product story before implementation begins.

## State object
Permit review state.

## First complete path
Start with the first workflow.

## Proof boundary
Fixture-backed inputs prove the release claim.
"""

    intent = parse_confirmed_intent_text(confirmation, prompt=prompt)
    rendered = json.dumps(intent, sort_keys=True)

    assert "permit clerks" in rendered.casefold()
    assert "zoning attachments" in rendered.casefold()
    assert "approval packet" in rendered.casefold()
    assert "first workflow" not in rendered.casefold()
    assert "before implementation begins" not in rendered.casefold()


def test_project_brief_actor_choice_does_not_repeat_generic_team_label() -> None:
    brief = confirmed_project_brief(
        label="Model Lab Notebook",
        prompt="model lab notebook",
        release="0.0.1",
        state_object="A model lab notebook result record tracks review state and proof evidence.",
        evidence_record="Model lab notebook proof evidence",
        product_story="Teams need a shared notebook for reviewable model lab decisions.",
        first_path="Teams review the notebook, record the status, and publish a reviewable result.",
        proof_boundary="Release 0.0.1 succeeds when teams can review the notebook result with evidence.",
        human_actors=["Teams: coordinate model lab notebook review."],
        internal_systems=["Notebook intake register", "Review workspace", "Proof ledger"],
    )
    rendered = json.dumps(brief, sort_keys=True)

    assert "people and teams: Teams" not in rendered
    assert "who participates in the first path: Teams" in rendered
    assert generated_public_copy_issues("project brief preview", brief) == ()

    next_steps = build_next_steps(
        proposal={
            "intent": {"title": "Model Lab Notebook"},
            "backlog": [
                {"title": "Model Lab Notebook Program"},
                {
                    "title": "Teams Review First Slice",
                    "recommended_first_slice": (
                        "Teams review the notebook, record the status, and publish a reviewable result."
                    ),
                },
            ],
            "project_brief": brief,
        },
        backlog_result={
            "created": [
                {"idea_id": "B-001", "title": "Model Lab Notebook Program"},
                {"idea_id": "B-002", "title": "Teams Review First Slice"},
            ]
        },
        first_release_workstreams=["B-001", "B-002"],
        program_result={"umbrella_id": "B-001", "waves": [{"status": "active", "primary_workstreams": ["B-002"]}]},
        release_selector="0.0.1",
    )
    rendered_next_steps = json.dumps(next_steps, sort_keys=True)

    assert "people and teams: Teams" not in rendered_next_steps
    assert "who participates in the first path: Teams" in rendered_next_steps
    assert generated_public_copy_issues("operator next-steps preview", next_steps) == ()
