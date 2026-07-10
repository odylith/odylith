from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import state_transition_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import program_problem
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import rationale_release_basis
from odylith.runtime.domain_intelligence.greenfield_proposals import build_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.domain_intelligence.greenfield_text import normalize_confirmed_proof_boundary_sentence
from odylith.runtime.domain_intelligence.greenfield_text import normalize_proof_boundary_language
from odylith.runtime.governance.component_authoring import _public_what_it_is
from odylith.runtime.governance.component_spec_narrative import build_narrative_component_spec
from odylith.runtime.project_intelligence.product_story_cards import build_greenfield_story_cards
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_intent_with_authority


ROOT = Path(__file__).resolve().parents[3]
CONFIRMED_BACKLOG_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_backlog.py"
CONFIRMED_BACKLOG_TEXT_MODEL_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_backlog_text_model.py"
)
CONFIRMED_BACKLOG_LANGUAGE_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_backlog_language.py"
)


def test_confirmed_backlog_text_model_stays_in_dedicated_owner() -> None:
    parent_source = CONFIRMED_BACKLOG_PATH.read_text(encoding="utf-8")
    text_model_source = CONFIRMED_BACKLOG_TEXT_MODEL_PATH.read_text(encoding="utf-8")
    language_source = CONFIRMED_BACKLOG_LANGUAGE_PATH.read_text(encoding="utf-8")

    assert len(parent_source.splitlines()) < 800
    assert len(text_model_source.splitlines()) < 800
    assert len(language_source.splitlines()) < 800
    assert "greenfield_confirmed_backlog_text_model as backlog_text" in parent_source
    assert "def _program_problem" not in parent_source
    assert "def _sentence_fragment" not in parent_source
    assert "def _first_action_clause" not in parent_source
    assert "def program_problem" in text_model_source
    assert "def first_action_clause" in text_model_source
    assert "def sentence_fragment" not in text_model_source
    assert "def sentence_fragment" in language_source
    assert "def rationale_lines" in language_source


def test_release_basis_avoids_clipped_release_gate_wrapper() -> None:
    release_basis = rationale_release_basis(
        title="Prove One Complete Published Auditable Funding Path",
        label="Published Auditable Funding",
        first_slice=(
            "One representative path where municipal resilience grant reviewers can intake flood mitigation project "
            "applications, score risk and equity evidence, route missing documentation back to applicants, and see "
            "the published auditable funding recommendation."
        ),
        proof_boundary=(
            "Release 0.0.1 succeeds when this first path is complete: Municipal resilience grant reviewers who intake "
            "flood mitigation project applications. Score risk and equity evidence. Route missing documentation back "
            "to applicants. Publish an auditable funding recommendation."
        ),
    )

    assert "succeeds when this first path is complete" not in release_basis.casefold()
    assert "municipal resilience grant reviewers" in release_basis.casefold()
    assert "before adjacent scope enters the release" in release_basis


def test_component_transition_inflector_renders_handoff_as_handed_off() -> None:
    transition = state_transition_text(
        action_terms=("handoff", "publish"),
        object_phrases=("review handoff",),
    )

    assert "handed-off" in transition
    assert "handoffed" not in transition


def test_proof_boundary_normalizes_first_path_complete_wrapper() -> None:
    raw = (
        "Release 0.0.1 succeeds when this first path is complete: Municipal resilience grant reviewers who intake "
        "flood mitigation project applications. Score risk and equity evidence. Route missing documentation back "
        "to applicants. Publish an auditable funding recommendation."
    )
    proof = normalize_proof_boundary_language(raw)
    confirmed_proof = normalize_confirmed_proof_boundary_sentence(raw)

    assert proof == (
        "municipal resilience grant reviewers can intake flood mitigation project applications, "
        "score risk and equity evidence, route missing documentation back to applicants, and publish an auditable funding recommendation"
    )
    assert "this first path is complete" not in proof
    assert confirmed_proof == f"Release 0.0.1 succeeds when {proof}"


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


def test_greenfield_story_cards_normalize_clause_like_proof_outcomes() -> None:
    cards = {
        row["label"]: row["body"]
        for row in build_greenfield_story_cards(
            title="Learning Lab",
            intent={
                "product_story": "A learner needs a short practice session that leaves visible evidence for review.",
                "state_object": "A lab session record with selected scenario, attempt history, result, and review status.",
                "non_goals": ["Advanced simulations and live instructor grading are outside the first release."],
            },
            project={},
            objective="",
            outcome="The first proof is a working lab session with visible evidence and correction guidance.",
            first_path="A learner opens one session, completes a guided attempt, and sees a visible result.",
            actors=(("primary", "Learner", "Completes the session."), ("reviewer", "Instructor", "Reviews the result.")),
            validation=(),
        )
    }

    boundary = cards["Product Boundary"]
    assert "stops at" not in boundary
    assert "proof is" not in boundary.casefold()
    assert "This release is limited to a working lab session" in boundary
    assert "advanced simulations" in boundary.casefold()


def test_greenfield_story_cards_preserve_object_tail_first_path_without_sentence_fragment() -> None:
    first_path = (
        "A cryogenic microscope control room console user can coordinate vacuum pumps, stage motion, "
        "thermal drift readings, image capture windows, operator overrides, and recovery proof before "
        "a sample run is accepted."
    )
    cards = {
        row["label"]: row["body"]
        for row in build_greenfield_story_cards(
            title="Cryogenic Microscope Control Room Console",
            intent={
                "product_story": (
                    "Cryogenic Microscope Control Room Console helps a cryogenic microscope control room "
                    "console user complete the first accepted control-room path."
                ),
                "proof_boundary": (
                    "Release succeeds when the user can coordinate vacuum pumps, stage motion, thermal drift "
                    "readings, image capture windows, operator overrides, and recovery proof before a sample run "
                    "is accepted."
                ),
            },
            project={},
            objective="",
            outcome="",
            first_path=first_path,
            actors=(
                (
                    "primary",
                    "Cryogenic Microscope Control Room Console User",
                    "Coordinates the control-room path.",
                ),
            ),
            validation=(),
        )
    }

    assert "operator overrides. Recovery proof" not in cards["First Path"]
    assert (
        "operator overrides, and recovery proof before a sample run is accepted"
        in cards["First Path"]
    )


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


def test_component_spec_preserves_finite_action_accepted_intent_sentence() -> None:
    spec = build_narrative_component_spec(
        component_id="parameter-control-surface",
        label="Parameter Control Surface",
        path="src/example/parameter_control_surface",
        kind="surface",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-003",),
        responsibility="captures barrier width and particle energy choices, enforces bounds, and keeps unit conversions visible",
        component_contract={
            "owned_state": "parameter control, particle energy choices, unit conversions, blocker state, and next-step context",
            "accepted_inputs": "particle energy choices, unit conversions, prior state, and validation context",
            "produced_outputs": "particle energy choices, unit conversions, and bounded parameter state",
            "states_or_transitions": "captured, enforced, validated, blocked, revised, and ready-for-next-step",
            "outside_boundary": "adjacent component state, original input facts, and upstream source truth",
            "local_proof": ("Replay evidence for Parameter Control Surface: actor, input facts, status, and explanation.",),
            "upstream_truth": "Scenario Preset Surface ownership",
            "downstream_consumers": "Simulation Runner",
            "unique_failure": "Parameter Control Surface can mislead users if particle energy choices are missing.",
        },
    )

    assert "Accepted intent says Parameter Control Surface captures barrier width" in spec
    assert "unit conversions visible state" not in spec
    assert "centers Parameter Control Surface on barrier width" not in spec


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
    intent = confirmed_intent_with_authority(
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
        repo_root=tmp_path,
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
    assert "Log Several Usage" in generated
    assert "Accept or dismisses" not in generated
    assert "accepting or dismissing" in generated

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
    problem = program_problem(
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
