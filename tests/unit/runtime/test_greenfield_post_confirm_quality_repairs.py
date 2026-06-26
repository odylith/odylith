from __future__ import annotations

import json

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import action_chain_fragment
from odylith.runtime.domain_intelligence.greenfield_post_confirm_semantic_drift import contrastive_domain_drift_issues
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.domain_intelligence.greenfield_product_risks import build_product_risks
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.domain_intelligence.proposal_memory import build_accepted_project_source_payload
from odylith.runtime.governance.component_spec_narrative import build_narrative_component_spec


def test_plain_title_actor_subjects_lower_coherently_before_finite_actions() -> None:
    assert base_action_clause("Home Cook picks a recipe") == "home cook picks a recipe"
    assert action_chain_fragment("Home Cook picks a recipe") == "home cook picks a recipe"
    assert first_path_capability_phrase("Home Cook picks a recipe").startswith("home cook can pick a recipe")
    assert generated_semantic_slop_issues({"capability": first_path_capability_phrase("Home Cook picks a recipe")}) == []

    assert base_action_clause("Station Lead Review") == "station lead review"
    assert action_chain_fragment("Station Lead Review") == "station lead review"
    assert generated_semantic_slop_issues({"fragment": action_chain_fragment("Station Lead Review")}) == []


def test_robotic_safety_parent_workstream_uses_proof_subject_and_visible_status() -> None:
    intent = parse_confirmed_intent_text(
        """
# Robotic Warehouse Safety Stop Console

## Product story
Warehouse operators need a safety console that makes blocked aisles, impacted robots, inventory moves, stop decisions, overrides, maintenance actions, and recovery evidence visible before automation resumes.

## State object
A robotics exception record tracks aisle blocker, impacted robots, inventory moves, stop or resume decision, safety reviewer approval, override reason, maintenance action, incident evidence, and recovery status.

## First complete path
A floor operator reports a blocked aisle, the console maps impacted robots and moves, a safety reviewer confirms whether to stop or resume automation, maintenance records corrective action, and operations receives recovery status with unsafe states still visible.

## Human actors
- Floor operator who reports blocked aisles and exceptions
- Safety reviewer who approves stop or resume decisions
- Maintenance technician who records corrective action
- Operations lead who accepts recovery status
- Automation supervisor who reviews overrides

## External systems
- Warehouse robot control system
- Inventory movement system
- Safety interlock telemetry
- Maintenance ticketing system

## Internal systems
- Exception intake console
- Robot impact mapper
- Safety stop decision ledger
- Override and interlock tracker
- Maintenance recovery record
- Operations readiness view

## Critical assumptions
- Unsafe states must stop the first path rather than be hidden.
- The product records safety decisions and handoffs but does not bypass physical interlocks.
- Recovery needs evidence before automation resumes.

## Ambiguities
- Whether robot commands are sent directly or exported for the control system.
- Which incident evidence is mandatory for each stop class.

## Proof boundary
Release 0.0.1 succeeds when one blocked aisle incident can stop automation, record impacted robots and inventory moves, capture corrective action, and show reviewed recovery status before resume.
""",
        prompt="Robotic warehouse safety stop console",
    )
    proposal = build_confirmed_greenfield_proposal(
        prompt="Robotic warehouse safety stop console",
        title="Robotic Warehouse Safety Stop Console",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert generated_semantic_slop_issues(proposal) == []
    assert "proves map impacted robots" not in rendered
    assert "maping impacted robots" not in rendered
    assert "letting the safety reviewer state still visible" not in rendered
    assert "proves mapping impacted robots and moves" in rendered
    assert "letting the safety reviewer see the recovery status with unsafe states still visible" in rendered


def test_confirmed_intent_accepts_trustworthy_when_proof_boundary() -> None:
    intent = parse_confirmed_intent_text(
        """
# Sewing Pattern Relief Planner

## Product story
A garment maker needs to understand where a sewing pattern may feel tight before cutting fabric. A fitting coach needs a repeatable adjustment record that explains measurements, garment ease, suggested adjustment, and risk notes.

## State object
A pattern adjustment record tracks garment type, wearer measurements, pattern size, target ease, pressure areas, suggested adjustment, rationale, fitting notes, and approval status.

## First complete path
Garment Maker enters measurements, chooses a garment pattern, reviews pressure areas, accepts a suggested adjustment, and receives an adjustment plan with rationale and fitting notes.

## Human actors
- Garment maker who enters measurements and reviews the adjustment
- Fitting coach who approves adjustment guidance
- Pattern librarian who maintains garment pattern data

## Internal systems
- Measurement intake workflow
- Pattern comparison model
- Adjustment recommendation service
- Fitting-note review workspace

## Proof boundary
Release 0.0.1 is trustworthy when one garment maker can produce an adjustment plan and a fitting coach can inspect the rationale.
""",
        prompt="Draft a greenfield proposal for a sewing pattern relief planner",
    )

    assert intent["proof_boundary"].startswith("Release 0.0.1 is trustworthy when")


def test_accepted_project_memory_avoids_compact_action_splice_after_capability() -> None:
    intent = complete_confirmed_intent(
        parse_confirmed_intent_text(
            """
# Choice Practice Learning App

## Product story
A parent needs a child-safe practice app where a learner can make one guided choice and give the parent a simple recap.

## State object
A practice session record tracks learner profile, scenario, selected choice, consequence, reflection answer, parent recap status, and safety review notes.

## First complete path
Operator creates a learner profile, starts one scenario, lets the learner choose an option, shows the consequence and reflection prompt, and saves a parent recap with safety notes.

## Human actors
- Parent who sets up the learner and reviews the recap
- Learner who makes the guided choice and reflection
- Content reviewer who approves scenarios and safety notes

## Internal systems
- Learner profile and consent setup
- Scenario and choice engine
- Reflection capture workflow
- Parent recap and safety review

## Proof boundary
Release 0.0.1 is trustworthy when one learner can complete a scenario and the parent can review the recap.
""",
            prompt="Draft a greenfield proposal for a child choice-practice learning app",
        )
    )
    proposal = build_confirmed_greenfield_proposal(
        prompt="Draft a greenfield proposal for a child choice-practice learning app",
        title="Choice Practice Learning App",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    payload = build_accepted_project_source_payload(
        proposal=proposal,
        backlog_items=[],
        component_items=[],
        diagram_ids=[],
        release_selector="0.0.1",
        release_id="release-choice-practice-0-0-1",
        validation_gate={"status": "passed"},
    )

    assert generated_public_copy_issues("accepted-project memory preview", payload) == ()


def test_greenfield_quality_gate_ignores_apply_result_operational_metadata() -> None:
    payload = {
        "intent": {"prompt": "Draft a greenfield proposal for a request workspace"},
        "validation_gate": {
            "dimensions": {
                "artifact_substance": "Radar, Registry, Atlas, and Compass surfaces refreshed."
            }
        },
        "post_confirm_quality_manifest": {
            "quality_lenses": {
                "lenses": [
                    {"role": "architect", "checks": [{"evidence": "Atlas diagram count is complete."}]}
                ]
            }
        },
        "next_steps": {
            "verification_commands": [
                "./.odylith/bin/odylith context --repo-root . B-001",
            ]
        },
        "program": {
            "execution_engine": {
                "contract": {
                    "validation_plan": [
                        "odylith validate backlog-contract --repo-root .",
                    ]
                }
            }
        },
    }

    assert greenfield_quality_issues(payload) == []


def test_terminal_result_chain_allows_captured_reflection_before_completion_action() -> None:
    assert generated_public_copy_issues(
        "first path",
        "The learner writes or records a short reflection, completes the session, and the parent opens a recap.",
    ) == ()
    assert generated_public_copy_issues(
        "bad result",
        "The visible result and completes the session.",
    ) == ("bad result leaked terminal action inside result prose",)


def test_contrastive_drift_allows_recommendation_when_intent_says_suggested() -> None:
    proposal = {
        "intent": {
            "title": "Adjustment Planner",
            "product_story": "A maker reviews a suggested adjustment before accepting a change plan.",
            "state_object": "An adjustment plan with suggested adjustment, rationale, and review status.",
            "first_path": "A maker reviews a suggested adjustment and saves the accepted plan.",
            "proof_boundary": "Release succeeds when the suggested adjustment can be reviewed.",
        },
        "components": [
            {
                "label": "Adjustment Review Service",
                "source_system_description": "keeps the suggested adjustment reviewable",
                "component_contract": {
                    "owned_state": (
                        "recommendation result, recommendation rationale, recommendation evidence, "
                        "recommendation status, recommendation blocker, recommendation review, "
                        "recommendation handoff, and recommendation history"
                    )
                },
            }
        ],
    }

    assert contrastive_domain_drift_issues(proposal, {}) == []


def test_product_risks_strip_bare_actor_label_from_weak_input_clause() -> None:
    risks = build_product_risks(
        title="Municipal Permit Review Portal",
        product_story=(
            "A resident needs one clear online path to request a small building permit, provide required project details, "
            "receive corrections when information is missing, and see the review decision."
        ),
        first_path=(
            "Resident Applicant selects the permit type, enters project details, attaches required documents, "
            "pays the fee, and receives an approved or rejected permit decision with reviewer notes."
        ),
        state_object="A permit application record with applicant identity, submitted documents, status, and decision notes.",
        proof_boundary=(
            "Release 0.0.1 is trustworthy when one resident can submit a permit application and inspect the decision evidence."
        ),
        human_actors=[
            "Resident Applicant: submits project details and corrections",
            "Permit Reviewer: checks zoning and document completeness",
        ],
        release="0.0.1",
    )
    rendered = json.dumps(risks, sort_keys=True)

    assert "resident Applicant" not in rendered
    assert "weak inputs are the permit type" in rendered
    assert generated_semantic_slop_issues({"risks": risks}) == []


def test_product_risks_describe_noun_focus_as_information_for_activity() -> None:
    risks = build_product_risks(
        title="Practice Session Workspace",
        product_story="A learner needs one place to complete a practice session and leave usable evidence.",
        first_path="A learner opens the lab session and sees a visible summary.",
        state_object="A lab session with selected scenario, attempt history, visible result, and completion status.",
        proof_boundary="Release 0.0.1 succeeds when one learner can complete a session and see a summary.",
        human_actors=["Learner", "Coach"],
        release="0.0.1",
    )
    raw_rendered = json.dumps(risks, sort_keys=True)
    rendered = raw_rendered.casefold()

    assert "provides lab session" not in rendered
    assert "provides information for lab session" in rendered
    assert "wrong person. the learner" not in raw_rendered
    assert generated_semantic_slop_issues({"risks": risks}) == []


def test_component_specs_strip_coordinated_actions_from_owned_artifact_slots() -> None:
    intent = complete_confirmed_intent(
        parse_confirmed_intent_text(
            """
# Solar Energy Optimization Workspace

## Product story
A building owner needs a daily plan that compares solar production, consumption, and battery state before choosing load timing.

## State object
An energy plan day tracks solar forecast, expected consumption profile, battery state, selected load window, recommendation status, and plan history.

## First complete path
An energy manager imports or enters a solar forecast, adds an expected consumption profile, enters current battery state, chooses one flexible load, reviews the recommended run window, and sees the updated daily plan.

## Human actors
- Energy manager who prepares the daily plan and reviews recommendations

## Internal systems
- Solar forecast intake.
- Consumption profile builder.
- Battery and tariff constraint model.
- Daily energy plan view.

## Proof boundary
Release 0.0.1 succeeds when one energy manager can create a daily plan, receive a recommended load window, and see the reason while missing forecasts or battery constraints block misleading recommendations.
""",
            prompt="An app that optimizes the production and consumption of solar energy",
        )
    )
    proposal = build_confirmed_greenfield_proposal(
        prompt="An app that optimizes the production and consumption of solar energy",
        title="Solar Energy Optimization Workspace",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    component = next(row for row in proposal["components"] if "Consumption Profile" in row["label"])
    spec = build_narrative_component_spec(
        component_id=component["component_id"],
        label=component["label"],
        path="src/example/consumption_profile_builder",
        kind=component.get("kind", "service"),
        status=component.get("status", "planned"),
        sources=("user_intent",),
        workstreams=("B-002",),
        responsibility=component.get("responsibility", ""),
        implementation_handoff={"workstream_id": "B-002", "workstream_title": "Build the consumption profile"},
        component_contract=component["component_contract"],
    )

    assert "and adds expected consumption profile" not in spec
    assert "and expected consumption profile" in spec
