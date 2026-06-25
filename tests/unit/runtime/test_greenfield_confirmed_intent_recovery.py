from __future__ import annotations

import json

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_project_title_source
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues


def _guidance_envelope(prompt: str) -> str:
    return f"""Product Intent Confirmation needed
No files changed. Source posture: empty_or_no_app_source.

Host reasoning task: Infer the product shape live from the operator prompt and any observed repo source.

Visible format contract
- Render the visible confirmation as sectioned Markdown in this order.

Original user intent
{prompt}
Next step
- Confirm: write this same visible Product Intent Confirmation to .odylith/runtime/greenfield/confirmed-intent.md.
Confirmed CLI after confirmation: odylith greenfield create --repo-root . --prompt '{prompt}' --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1
"""


def test_prompt_title_source_recognizes_generic_product_containers() -> None:
    assert (
        prompt_project_title_source(
            "Draft a greenfield proposal for a cooking robot controller where a home cook chooses a recipe."
        )
        == "cooking robot controller"
    )
    assert (
        prompt_project_title_source("Draft a greenfield proposal for a cooking robot controller")
        == "cooking robot controller"
    )
    assert (
        prompt_project_title_source("Draft a greenfield proposal for a solar energy installation planning hub")
        == "solar energy installation planning hub"
    )
    assert (
        prompt_project_title_source("Draft a greenfield proposal for a clinic follow-up coordination desk")
        == "clinic follow-up coordination desk"
    )
    assert (
        prompt_project_title_source("Draft a greenfield proposal for a warehouse slotting planner")
        == "warehouse slotting planner"
    )
    assert (
        prompt_project_title_source(
            "Draft a greenfield proposal for a contract redline review room where reviewers compare clauses."
        )
        == "contract redline review room"
    )
    assert (
        prompt_project_title_source(
            "Draft a greenfield proposal for a dispatch evidence console where coordinators review handoffs."
        )
        == "dispatch evidence console"
    )
    assert (
        prompt_project_title_source(
            "Draft a greenfield proposal for a classroom lab safety tracker where teachers prepare experiments."
        )
        == "classroom lab safety tracker"
    )
    assert (
        prompt_project_title_source(
            "Draft a greenfield proposal for a digestive health tracking notebook where a person records meals."
        )
        == "digestive health tracking notebook"
    )


def test_prompt_intent_source_splits_direct_product_title_from_first_path() -> None:
    source = prompt_intent_source(
        "factory line changeover readiness board where supervisors verify tooling, materials, safety checks, and restart approval"
    )

    assert source.title == "factory line changeover readiness board"
    assert source.first_path == "supervisors verify tooling, materials, safety checks, and restart approval"
    assert not source.command_led
    assert (
        prompt_project_title_source(
            "collaborative robot safety case builder where engineers map hazards, mitigations, validation tests, and release signoff evidence"
        )
        == "collaborative robot safety case builder"
    )
    assert (
        prompt_project_title_source(
            "customer data retention policy executor where privacy teams classify records, schedule deletions, and prove exceptions are approved"
        )
        == "customer data retention policy executor"
    )


def test_host_guidance_recovery_keeps_direct_where_prompt_title_instead_of_terminal_outcome() -> None:
    prompt = (
        "factory line changeover readiness board where supervisors verify tooling, materials, "
        "safety checks, and restart approval"
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Factory Line Changeover Readiness Board"
    assert "supervisors verify tooling" in intent["first_path"].casefold()
    assert "the and restart approval" not in rendered
    assert "And Restart Approval Workspace" not in rendered
    assert "Factory Line Changeover Readiness Board Intake Register" in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_uses_original_intent_over_visible_format_instructions() -> None:
    prompt = (
        "Draft a greenfield proposal for a digestive health tracking notebook where a person records meals, "
        "symptoms, timing, triggers, and a reviewable pattern summary without making diagnosis claims."
    )
    envelope = f"""Product Intent Confirmation needed
No files changed. Source posture: empty_or_no_app_source.

Host reasoning task: Infer the product shape live from the operator prompt and any observed repo source.

Visible format contract
Product story
State object
First complete path
Human actors
External systems
Internal product systems
Proof boundary

Original user intent
{prompt}
Next step
- Confirm: write this same visible Product Intent Confirmation to .odylith/runtime/greenfield/confirmed-intent.md.
Confirmed CLI after confirmation: odylith greenfield create --repo-root . --prompt "{prompt}" --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1
"""

    intent = parse_confirmed_intent_text(envelope, prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Digestive Health Tracking Notebook"
    assert "records meals, symptoms" in intent["first_path"].casefold()
    assert len(intent["internal_systems"]) == 3
    assert all("visible format" not in row.casefold() for row in intent["internal_systems"])
    assert "post-confirm repair loop" not in rendered.casefold()
    assert "product intent confirmation needed" not in rendered.casefold()
    assert "Visible Format Contract" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_builds_clean_confirmed_proposal_from_controller_prompt() -> None:
    prompt = (
        "Draft a greenfield proposal for a cooking robot controller where a home cook chooses a recipe, "
        "the controller sequences heat and motion, and safety proof must stop the run when sensors disagree."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Cooking Robot Controller"
    assert intent["human_actors"] == [
        "Home Cook: needs the product to choose a recipe and keep the result visible and reviewable"
    ]
    assert "Recovered Product Workspace" not in rendered
    assert "needs a dependable way to understand" not in rendered
    assert "Only accepted actors or systems can move first-path state: A." not in rendered
    assert "the cooking Robot Controller result" not in rendered
    assert "the cooking robot controller result" in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_nominalizes_actor_led_state_outcomes() -> None:
    prompt = (
        "Build a research replication package tracker where a principal investigator registers datasets, "
        "analysts attach reproducibility evidence, reviewers flag missing methods, and the lab publishes "
        "a clean audit trail before submission."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    state = intent["state_object"]

    assert state.startswith(("A missing methods record tracks", "A clean audit trail record tracks"))
    assert "A Reviewers flag" not in state
    assert "A reviewers flag" not in state


def test_host_guidance_recovery_lowercases_generated_state_article_body() -> None:
    prompt = (
        "Build a hospital equipment sterilization handoff board where technicians log tray readiness, "
        "nurses reserve urgent kits, supervisors verify failed-cycle evidence, and operating rooms see "
        "only safe release status."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)

    assert intent["state_object"].startswith("A safe release status record tracks")
    assert "An Only" not in intent["state_object"]


def test_host_guidance_recovery_handles_broad_product_prompt_without_parser_debris() -> None:
    prompt = "Draft a greenfield proposal for a cooking robot controller"

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Cooking Robot Controller"
    assert intent["first_path"] == (
        "A cooking robot controller user starts a cooking robot controller request, "
        "the product records required information, the product shows a reviewable result, "
        "and the product marks the request ready or blocked."
    )
    assert intent["human_actors"] == [
        "Cooking Robot Controller User: needs the product to start a cooking robot controller request and keep the result visible and reviewable"
    ]
    assert intent["state_object"].startswith("A cooking robot controller result record tracks")
    assert "the cooking robot controller result" in rendered
    assert "A a " not in rendered
    assert "A the " not in rendered
    assert "where A " not in rendered
    assert "Provides:" not in rendered
    assert "Reviews:" not in rendered
    assert "First Participant" not in rendered
    assert "Recovered Product Workspace" not in rendered
    assert "Cooking Robot Controller Participant review" not in rendered
    assert "sequence/parser debris" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_rejects_long_title_noun_as_first_path() -> None:
    prompt = "Draft a greenfield proposal for a solar energy installation planning hub"

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Solar Energy Installation Planning Hub"
    assert intent["first_path"].startswith(
        "A solar energy installation planning hub user starts a solar energy installation planning hub request"
    )
    assert "when a solar energy installation planning hub." not in intent["proof_boundary"]
    assert intent["human_actors"] == [
        "Solar Energy Installation Planning Hub User: needs the product to start a solar energy installation planning hub request and keep the result visible and reviewable"
    ]
    assert "sequence/parser debris" not in rendered
    assert "First Participant" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_strips_release_proof_tail_from_first_path() -> None:
    prompt = (
        "Draft a product-first greenfield proposal for a rooftop solar planning workspace where a homeowner "
        "captures roof details, utility constraints, installer options, incentive paperwork, design review, "
        "and installation readiness before release 0.0.1 proves one complete solar project planning path."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Rooftop Solar Planning Workspace"
    assert "roof details" in intent["first_path"].casefold()
    assert "installation readiness" in intent["first_path"].casefold()
    assert "0.0.1 proves" not in intent["first_path"]
    assert "one complete solar project planning path" not in intent["state_object"].casefold()
    assert [row.split(":", 1)[0] for row in intent["human_actors"]] == ["Homeowner"]
    assert "Installation Readiness Before Release" not in rendered
    assert "A 1 proves" not in rendered
    assert "and and" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_does_not_promote_verb_led_path_to_actor() -> None:
    prompt = (
        "Create a solar installation planning product that turns roof, utility, incentive, "
        "and installer constraints into a homeowner-ready installation plan, with review gates "
        "for feasibility, cost, and next actions."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Solar Installation Planning Product"
    assert intent["human_actors"]
    assert all("Installation Plan with" not in row for row in intent["human_actors"])
    assert "helps a with" not in rendered
    assert "With needs" not in rendered
    assert "where turns" not in rendered
    assert "when turns" not in rendered
    assert "the product turns roof" in rendered
    assert "Turn Roof Utility Incentive and Installer Constraints Into a Homeowner Ready Installation Plan with" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_rejects_hyphenated_title_noun_as_first_path() -> None:
    prompt = "Draft a greenfield proposal for a clinic follow-up coordination desk"

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Clinic Follow Up Coordination Desk"
    assert intent["first_path"].startswith(
        "A clinic follow up coordination desk user starts a clinic follow up coordination desk request"
    )
    assert "when a clinic follow-up coordination desk." not in intent["proof_boundary"]
    assert "sequence/parser debris" not in rendered
    assert "First Participant" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_handles_bare_short_product_noun_phrase() -> None:
    prompt = "warehouse slotting planner"

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Warehouse Slotting Planner"
    assert intent["first_path"].startswith(
        "A warehouse slotting planner user starts a warehouse slotting planner request"
    )
    assert len(intent["internal_systems"]) == 3
    assert intent["internal_systems"][0].startswith("Warehouse Slotting Planner Intake Register ")
    assert "records source input" in intent["internal_systems"][0]
    assert intent["internal_systems"][1].startswith("Warehouse Slotting Planner Review Workspace ")
    assert "presents current state" in intent["internal_systems"][1]
    assert intent["internal_systems"][2].startswith("Warehouse Slotting Planner Proof Ledger ")
    assert "replayable evidence" in intent["internal_systems"][2]
    assert "Recovered Product Workspace" not in rendered
    assert "First Participant" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_keeps_audience_suffix_inside_product_title() -> None:
    prompt = "kitchen robot controller for home cooks"

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Kitchen Robot Controller for Home Cooks"
    assert "Kitchen Robot Controller for Home Cooks Workspace" not in rendered
    assert "Recovered Product Workspace" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_handles_plural_actor_clauses_without_generic_workspace() -> None:
    prompt = (
        "Draft a greenfield proposal for a classroom lab safety tracker where teachers prepare experiments, "
        "students acknowledge hazards, and lab coordinators verify cleanup proof."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Classroom Lab Safety Tracker"
    assert intent["human_actors"] == [
        "Teachers: need the product to prepare experiments and keep the result visible and reviewable",
        "Students: need the product to acknowledge hazards and keep the result visible and reviewable",
        "Lab Coordinators: need the product to verify cleanup proof and keep the result visible and reviewable",
    ]
    assert "Recovered Product Workspace" not in rendered
    assert "a Teachers" not in rendered
    assert "Teachers needs" not in rendered
    assert "teachers can prepare experiments" in rendered
    assert greenfield_quality_issues(proposal) == []


def test_confirmed_completion_splits_finite_actor_sentences_before_domain_intelligence(tmp_path) -> None:
    prompt = (
        "specialty clinic referral tracker where coordinators triage referrals, flag missing documents, "
        "and review a ready-or-blocked status"
    )
    intent = parse_confirmed_intent_text(
        """
# Specialty Clinic Referral Tracker

## Product story
Specialty clinics need one shared referral tracker so coordinators can triage incoming referrals, see missing documents, and keep each referral in a ready-or-blocked state before it is reviewed.

## State object
A referral case records the patient-facing request, referral source, specialty destination, required documents, triage status, blocker reason, owner, timestamps, and review evidence.

## First complete path
Coordinators triage one new referral, flag any missing documents, resolve or document the blocker, and review a ready-or-blocked status that can be trusted by the clinic team.

## Actors
- Coordinators manage referral intake and document readiness.
- Clinic reviewers use the ready-or-blocked status to decide the next action.
- Referral sources supply missing documents when a blocker is raised.

## Systems
- Referral intake queue
- Document checklist service
- Status review workspace
- Audit evidence log

## Assumptions
- The first release focuses on one specialty clinic team and one referral source workflow.

## Ambiguities
- Which source system should send the initial referral payload first?

## Proof boundary
Release 0.0.1 is ready when one coordinator can triage a referral, mark missing documents, clear or preserve a blocker, and produce a ready-or-blocked review trail without relying on an external spreadsheet.
""",
        prompt=prompt,
    )

    completed = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(completed, sort_keys=True)

    assert "Clinic Reviewers Use the" not in rendered
    assert "Referral Sources Supply" not in rendered
    assert "Use the." not in rendered
    assert greenfield_quality_issues(completed) == []


def test_confirmed_recovery_uses_actor_subject_for_public_response_prompt(tmp_path) -> None:
    prompt = (
        "public comment response tracker where agency staff cluster comments, draft replies, "
        "and prove publication readiness"
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    completed = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(completed, sort_keys=True)

    assert intent["human_actors"][0].startswith("Agency Staff:")
    assert "Public Comment Response Participant" not in rendered
    assert "First Participant" not in rendered
    assert "participant" not in next(
        row for row in completed["diagrams"] if row["title"] == "First Path Sequence"
    )["mermaid_source"].casefold()
    assert greenfield_quality_issues(completed) == []


def test_confirmed_recovery_fallback_actor_does_not_emit_participant(tmp_path) -> None:
    prompt = "incident intake console where analysts wrangle incoming reports"

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    completed = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(completed, sort_keys=True)

    assert "First Participant" not in rendered
    assert "Participant:" not in rendered
    assert "participant" not in next(
        row for row in completed["diagrams"] if row["title"] == "First Path Sequence"
    )["mermaid_source"].casefold()
    assert greenfield_quality_issues(completed) == []
