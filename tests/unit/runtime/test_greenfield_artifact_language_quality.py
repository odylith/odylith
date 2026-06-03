from __future__ import annotations

import json

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import _program_problem
from odylith.runtime.domain_intelligence.greenfield_proposals import build_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.governance.component_authoring import _public_what_it_is
from odylith.runtime.governance.component_spec_narrative import build_narrative_component_spec
from odylith.runtime.project_intelligence.product_story_cards import build_greenfield_story_cards


def test_greenfield_story_cards_keep_action_grammar_and_visible_outcome() -> None:
    first_path = (
        "The owner opens the web app, adds one asset, and manually logs a few usage entries. "
        "The owner sees a current health readout with one grounded suggestion. "
        "The owner clicks Accept or Dismiss on that suggestion and the dashboard visibly updates the suggestion state."
    )

    cards = {
        row["label"]: row["body"]
        for row in build_greenfield_story_cards(
            title="Asset Care Companion",
            intent={
                "product_story": "An owner needs one clear place to understand whether a personally managed asset needs attention.",
                "proof_boundary": "Release succeeds when one owner can register an asset, log usage, and receive a grounded health readout.",
                "non_goals": [
                    "Multi-asset automation remains outside the first release.",
                    "Live telemetry import is a later release.",
                ],
            },
            project={},
            objective="",
            outcome="",
            first_path=first_path,
            actors=(("primary", "Owner", "Records asset data and acts on suggestions."),),
            validation=(),
        )
    }

    rendered = json.dumps(cards)
    assert "visible-result event" not in rendered
    assert "rendered dashboard" not in rendered
    assert ", and manually logs" not in rendered
    assert "adds one asset and manually logs a few usage entries" in cards["First Path"]
    assert "current health readout with one grounded suggestion" in cards["First Path"]
    assert "multi-asset automation" in cards["Product Boundary"].casefold()


def test_state_store_specs_do_not_render_as_configuration_policy() -> None:
    contract = {
        "owned_state": "asset history, asset profile, usage entry, blocker state, and next-step context",
        "accepted_inputs": "accepted input context, authorized actor, prior state, and required asset profile command",
        "produced_outputs": "validated asset profile state, correction marker, and replayable change evidence",
        "states_or_transitions": "open, logged, stored, validated, blocked, revised, and ready-for-next-step",
        "outside_boundary": "adjacent component state and recovery context owned elsewhere, mutation of original input facts, and metric state",
        "local_proof": (
            "Asset History Store proves the happy path for asset profile with a visible result and persisted explanation.",
            "Asset History Store blocks missing or malformed asset profile and keeps correction guidance visible.",
        ),
        "upstream_truth": "Accepted input context",
        "downstream_consumers": "Metrics Engine",
        "unique_failure": "Asset History Store can mislead users if the asset profile is missing, stale, or shown without explanation.",
    }

    spec = build_narrative_component_spec(
        component_id="asset-history-store",
        label="Asset History Store",
        path="src/example/asset_history_store",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-002",),
        diagrams=("D-002",),
        responsibility="holds the asset profile, usage entries, and maintenance log",
        component_contract=contract,
    )
    summary = _public_what_it_is(
        label="Asset History Store",
        kind="service",
        responsibility="holds the asset profile, usage entries, and maintenance log",
    )

    assert "product rules can change" not in spec
    assert "administrative policy" not in spec
    assert "keeps the product record together" in spec
    assert "boundary for holds" not in summary
    assert "boundary for the asset profile" in summary


def test_component_spec_preserves_relative_clauses_in_accepted_intent() -> None:
    spec = build_narrative_component_spec(
        component_id="revision-tracker",
        label="Revision Tracker",
        path="src/example/revision_tracker",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-004",),
        diagrams=("D-002",),
        responsibility="links applicant revisions to the documents and checks they are meant to address",
        component_contract={
            "owned_state": "applicant revisions to the documents and checks they are meant to address",
            "accepted_inputs": "zoning check evidence and revision uploads",
            "produced_outputs": "linked revision state and review evidence",
            "states_or_transitions": "submitted, linked, validated, blocked, revised",
            "outside_boundary": "decision package state and final approval state",
            "local_proof": (
                "Revision Tracker links applicant revisions to the documents and checks they are meant to address.",
            ),
            "upstream_truth": "Zoning Check Ledger",
            "downstream_consumers": "Decision Package Review",
            "unique_failure": "Revision Tracker can mislead reviewers if revisions are disconnected from the checks they address.",
        },
    )

    assert "checks they are meant to address" in spec
    assert "checks are meant to address" not in spec


def test_confirmed_greenfield_artifacts_reject_mechanical_dashboard_and_radar_language(tmp_path) -> None:
    intent = parse_confirmed_intent_text(
        """Personal Asset Care — Product Intent Confirmation

Product story
An owner needs one understandable place to record how an important personal asset is performing and receive plain-language guidance about what to do next.

State object that changes through the first journey
An Asset Care Record contains the asset identity, usage entries, health indicators, suggestion state, and explanation history.

First complete path Odylith should prove before broader scope
The owner opens the web app, adds one asset, manually logs several usage entries, sees a current health readout with one grounded suggestion, and accepts or dismisses that suggestion. This rendered dashboard view is the visible-result event that completes the first path.

Human actors
- Owner — records asset data, reads the health readout, and acts on suggestions.

External systems
- Manual entry is the only source for release 0.0.1.
- Live import is deferred.

Internal product systems
- Asset History Store — holds the asset profile, usage entries, and suggestion state.
- Health Metrics Engine — calculates current indicators from accepted entries.
- Suggestion Engine — creates one grounded next action with an explanation.
- Owner Interface — shows the health readout, suggestion, and accept or dismiss control.

Critical assumptions
- One owner and one asset are enough for the first release.

Ambiguities that would change the first path
- Whether automated imports are required before release.

Proof boundary
Release 0.0.1 succeeds when one owner can add the asset, log usage, receive a grounded health readout, and accept or dismiss the suggestion without losing the input facts or explanation.
""",
        prompt="Draft a product-first greenfield proposal for personal asset care",
    )

    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a product-first greenfield proposal for personal asset care",
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal)
    generated = json.dumps(
        {
            "backlog": proposal["backlog"],
            "components": proposal["components"],
            "diagrams": proposal["diagrams"],
            "release_plan": proposal["release_plan"],
        }
    )

    forbidden = (
        "visible-result event",
        "visible result event",
        "rendered dashboard",
        "is useful when",
        "product rules can change",
        "administrative policy",
        "boundary for holds",
        "holds the asset profile",
    )
    for phrase in forbidden:
        assert phrase not in rendered
    assert "maintains the asset profile" in rendered
    assert ", and manually logs" not in generated
    assert "Manually logs" not in generated
    assert "Accepts or dismisses" not in generated
    assert "Manually log several usage" in generated
    assert "Accept or dismisses" not in generated
    assert "Accept or dismiss" in generated

    first_row = proposal["backlog"][0]
    child_row = proposal["backlog"][1]
    assert "record how an important personal asset is performing" in first_row["problem"]
    assert "need Personal Asset Care" not in first_row["problem"]
    assert " to turn " not in first_row["problem"]
    assert "first release can collect activity" not in first_row["problem"]
    assert "is not trustworthy when" not in first_row["problem"]
    assert "source evidence, visible blockers" not in first_row["problem"]
    assert "systems that own the handoff" not in first_row["problem"]
    assert "A representative user can" not in " ".join(first_row["success_metrics"])
    assert "proves the first path" in first_row["success_metrics"][0]
    child_slice_text = " ".join(str(child_row.get(key, "")) for key in ("product_view", "recommended_first_slice")).casefold()
    assert "accepts or dismisses" not in child_slice_text


def test_greenfield_program_problem_fallback_reads_like_a_product_problem() -> None:
    problem = _program_problem(
        label="Example Product",
        actors="Primary User, Supporting Reviewer",
        story="Example Product organizes a first release.",
        capability="add one item and review a result",
        outcome="a clear recommendation",
        fallback="",
    )

    assert problem == (
        "The primary user needs a clear way to add one item and review a result and understand what to do next. "
        "If Example Product only captures activity, the product leaves that user with data but no trustworthy way to use a clear recommendation."
    )
    assert "need Example Product" not in problem
    assert " to turn " not in problem
    assert "first release can collect activity" not in problem
    assert "is not trustworthy when" not in problem


def test_need_to_turn_slop_gate_allows_human_problem_language_but_rejects_product_name_scaffold() -> None:
    human_story = {
        "product_story": (
            "Residents need a calmer way to turn small home repair problems into confirmed appointments "
            "without repeated calls or unclear availability."
        )
    }
    generated_scaffold = {
        "problem": (
            "Residents need RepairDesk Booking Platform to turn source evidence, visible blockers, "
            "and release proof into implementation confidence."
        )
    }

    assert generated_semantic_slop_issues(human_story) == []
    assert generated_semantic_slop_issues(generated_scaffold) == [
        "mechanical need-to-turn problem scaffold leaked at artifact.problem",
    ]
