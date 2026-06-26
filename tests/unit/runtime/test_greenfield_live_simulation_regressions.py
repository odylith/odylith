from __future__ import annotations

import json
from pathlib import Path
import re

from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_issues
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import build_greenfield_package_report
from odylith.runtime.domain_intelligence.greenfield_proposals import build_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.project_intelligence.intent_confirmation import build_product_intent_confirmation
from odylith.runtime.project_intelligence.intent_confirmation import format_product_intent_confirmation_text


def _intent_from_prompt(prompt: str) -> dict[str, object]:
    return parse_confirmed_intent_text(
        f"""
Product Intent Confirmation needed

Original user intent
{prompt}
""",
        prompt=prompt,
    )


def _visible_confirmation_intent(prompt: str) -> dict[str, object]:
    confirmation = build_product_intent_confirmation(
        prompt=prompt,
        title="greenfield simulation",
        repo_name="greenfield-simulation",
        observed_source={},
    )
    return parse_confirmed_intent_text(format_product_intent_confirmation_text(confirmation), prompt=prompt)


def _proposal_and_prewrite(tmp_path: Path, prompt: str):
    tmp_path.mkdir(parents=True, exist_ok=True)
    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=_visible_confirmation_intent(prompt),
        require_completion_ready=False,
    )
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")
    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_write.release_assignment_note(selector="0.0.1"),
    )
    return proposal, prewrite


def test_confirmed_actor_labels_drop_dangling_action_fragments(tmp_path: Path) -> None:
    prompt = (
        "Create a greenfield product for a decision coach that lets a user describe a difficult choice, "
        "compare options against stated values, record tradeoffs, and choose one next action with review evidence."
    )

    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=_intent_from_prompt(prompt),
    )
    encoded = json.dumps(proposal, sort_keys=True)
    actor_text = json.dumps(
        [row.get("customer") for row in proposal.get("backlog", []) if isinstance(row, dict)],
        sort_keys=True,
    )

    assert generated_semantic_slop_issues(proposal, root="proposal") == []
    assert "Choose One Next Action with" not in encoded
    assert not re.search(r"\b(?:and|for|from|the|to|when|while|with)\.?(?:\"|$)", actor_text)


def test_repaired_interfaces_do_not_repeat_generic_next_step_copy(tmp_path: Path) -> None:
    prompt = (
        "Create a greenfield product for public agency response teams to collect resident reports, triage urgency, "
        "coordinate owner follow-up, and publish a clear status explanation with proof of action."
    )

    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=_intent_from_prompt(prompt),
        require_completion_ready=False,
    )
    interfaces = [
        item
        for row in proposal.get("backlog", [])
        if isinstance(row, dict)
        for item in row.get("interfaces", [])
        if isinstance(item, str)
    ]
    package = GreenfieldCompletionPackage(
        proposal=proposal,
        accepted_project_preview={"proposal": proposal},
    )
    handoffs = [item for item in interfaces if " hands off " in item]

    assert "The next product step receives" not in json.dumps(proposal, sort_keys=True)
    assert handoffs
    assert len(handoffs) == len(set(handoffs))
    assert not any("repeats a noncanonical sentence" in issue for issue in greenfield_rendered_package_quality_issues(package))


def test_distributed_agent_confirmation_preserves_actor_and_component_boundaries(tmp_path: Path) -> None:
    prompt = (
        "Create a greenfield product for platform operators who submit distributed agent jobs, "
        "track assigned worker progress, collect execution evidence, surface blockers, and publish "
        "a final run record with reviewer approval."
    )

    proposal, prewrite = _proposal_and_prewrite(tmp_path, prompt)
    encoded = json.dumps(proposal, sort_keys=True)
    component_labels = [
        str(row.get("label", "")).strip()
        for row in proposal.get("components", [])
        if isinstance(row, dict) and str(row.get("label", "")).strip()
    ]
    report = build_greenfield_package_report(prewrite.package)

    assert "Publish a Final" not in encoded
    assert "can run record with reviewer approval" not in encoded.casefold()
    assert "reviewer run record with reviewer approval" not in encoded.casefold()
    assert any("Platform Operators" in row for row in proposal["intent"]["human_actors"])
    assert len(component_labels) >= 3
    assert len(component_labels) == len(set(component_labels))
    assert len(prewrite.package.rendered_component_specs or {}) == len(component_labels)
    assert report.issues == ()


def test_relative_actor_confirmation_does_not_promote_outcome_terms_to_people(tmp_path: Path) -> None:
    prompt = (
        "Create a greenfield product for community sports organizers who schedule FIFA-style neighborhood "
        "tournaments, register teams, assign referees, publish fixtures, record match results, and show "
        "standings with dispute review."
    )

    proposal, prewrite = _proposal_and_prewrite(tmp_path, prompt)
    public_payload = json.dumps(
        {
            "intent": proposal.get("intent"),
            "backlog": proposal.get("backlog"),
            "next_steps": prewrite.package.next_steps_preview,
        },
        sort_keys=True,
    )
    actors = [str(row) for row in proposal["intent"]["human_actors"]]
    actor_labels = [row.split(":", 1)[0] for row in actors]
    report = build_greenfield_package_report(prewrite.package)

    assert any(label == "Community Sports Organizers" for label in actor_labels)
    assert "Dispute" not in actor_labels
    assert "can who" not in public_payload.casefold()
    assert "to who" not in public_payload.casefold()
    assert report.issues == ()
    assert greenfield_rendered_package_quality_issues(prewrite.package) == ()


def test_health_followup_recovery_keeps_adjectival_result_terms_out_of_actors(tmp_path: Path) -> None:
    prompt = (
        "Create a greenfield product for digestive health patients who log meals, symptoms, medications, "
        "and bowel patterns, then prepare a clinician-ready follow-up summary with safety escalation notes."
    )

    intent = _visible_confirmation_intent(prompt)
    proposal, prewrite = _proposal_and_prewrite(tmp_path, prompt)
    actor_labels = [str(row).split(":", 1)[0] for row in proposal["intent"]["human_actors"]]
    system_rows = [str(row) for row in intent["internal_systems"]]

    assert intent["title"] == "Clinician Ready Follow Up Summary Workspace"
    assert actor_labels == ["Digestive Health Patients"]
    assert len(system_rows) >= 3
    assert not any("Recovered Product" in row or "— keeps Safety" in row for row in system_rows)
    rendered_package = json.dumps(
        {
            "backlog": prewrite.package.backlog_result.get("idea_files"),
            "next_steps": prewrite.package.next_steps_preview,
        },
        sort_keys=True,
    )
    assert "provide what the product needs, leaves enough context" not in rendered_package
    assert "provides what the product needs" not in rendered_package
    assert "the product keeps enough context for follow-up" not in rendered_package
    assert "the product preserves the saved context" in rendered_package
    assert build_greenfield_package_report(prewrite.package).issues == ()


def test_scientific_lab_state_predicate_does_not_poison_post_confirm_artifacts(tmp_path: Path) -> None:
    intent = parse_confirmed_intent_text(
        """
# Quantum Tunneling Lab

## Product story
A virtual physics lab helps learners run and understand one-dimensional quantum tunneling experiments without physical equipment.

## State object
A lab session contains the selected experiment, particle properties, barrier shape, energy settings, solver settings, visualization state, measured outputs, notes, and saved results.

## First complete path
A physics learner opens a preset electron tunneling experiment, adjusts barrier height and width, runs the simulation, watches the wave packet interact with the barrier, and saves a short lab result with the chosen parameters and observations.

## Human actors
- Physics learner exploring tunneling behavior.
- Instructor assigning or reviewing lab scenarios.

## Internal product systems
- Experiment workspace.
- Units and parameter validation.
- Quantum solver for one-dimensional tunneling.
- Visualization layer for wave function, potential barrier, and probability outputs.
- Results and notes store.
- Benchmark fixtures for known analytic cases.

## External systems
- Browser runtime for the first version.
- Export target for saved lab reports.

## Critical assumptions
- This is a digital simulation lab, not control software for physical lab equipment.
- The first version focuses on one-dimensional tunneling through rectangular barriers.
- Outputs must be reproducible and checked against known formulas or trusted fixtures.

## Ambiguities
- Whether the target audience is high school, undergraduate physics, or research-oriented users.
- Whether the first version should be web-only or also support local/offline use.

## Proof boundary
The first proof is a working one-dimensional quantum tunneling lab for a rectangular barrier. It should run deterministic sample experiments, show transmission and reflection behavior, preserve units clearly, and match expected analytic or benchmark results within stated tolerances.
""",
        prompt="Draft a greenfield proposal for a quantum tunneling lab.",
    )

    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a greenfield proposal for a quantum tunneling lab.",
        release_selector="0.0.1",
        confirmed_intent=intent,
        require_completion_ready=False,
    )
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")
    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_write.release_assignment_note(selector="0.0.1"),
    )
    report = build_greenfield_package_report(prewrite.package)
    rendered = json.dumps(
        {
            "proposal": proposal,
            "project_brief": prewrite.package.project_brief_preview,
            "next_steps": prewrite.package.next_steps_preview,
            "registry": prewrite.package.rendered_component_specs,
            "radar": prewrite.package.backlog_result,
        },
        default=str,
        sort_keys=True,
    )
    registry_rendered = json.dumps(prewrite.package.rendered_component_specs, default=str, sort_keys=True)
    actor_labels = [str(row).split(":", 1)[0] for row in proposal["intent"]["human_actors"]]

    assert report.issues == ()
    assert proposal["semantic_model"]["domain_ontology"]["state_object"] == "Lab Session"
    assert "Lab Session Contains" not in rendered
    assert "openning" not in rendered
    assert "open a preset electron tunneling experiment, adjusts" not in rendered
    assert "done when Done when" not in rendered
    assert "related proof context" not in rendered
    assert "related scope context" not in rendered
    assert not re.search(r"\band\s+or\b", rendered)
    assert not re.search(r"\band\s+and\b", rendered)
    assert "sent, received, declined, and scheduled" not in rendered
    assert "understand one-dimensional quantum tunneling" not in registry_rendered
    assert "Run the simulation" not in actor_labels
    assert "Watch the wave packet interact with the barrier" not in actor_labels
    first_metrics = proposal["backlog"][0]["success_metrics"]
    assert first_metrics[0] == (
        "The first release proves the first path: open a preset electron tunneling experiment, "
        "adjust barrier height and width, run the simulation, watch the wave packet interact with the barrier, "
        "and review a short lab result with the chosen parameters and observations"
    )
    assert not any(metric == "adjust barrier height and width" for metric in first_metrics)
    assert ";" not in first_metrics[0]
    actor_section = proposal["project_brief"]["blueprint_sections"][4]["must_capture"]
    first_user_option = proposal["project_brief"]["customization_options"][0]["recommended"]
    assert actor_section.startswith("Actors include Physics Learner and Instructor.")
    assert first_user_option == "Confirm the first people and teams: Physics Learner and Instructor."


def test_review_and_adjustment_prompts_avoid_generic_handoff_and_recommendation_drift(tmp_path: Path) -> None:
    tenant_prompt = (
        "Create a greenfield product for tenant aid coordinators who intake housing requests, verify "
        "eligibility documents, match residents to assistance programs, track case blockers, and prepare "
        "approval packets for supervisor review."
    )
    warehouse_prompt = (
        "Create a greenfield product for warehouse shift leads who reconcile inventory exceptions, compare "
        "scanner counts against expected stock, assign cycle-count follow-up, and publish an auditable "
        "adjustment decision."
    )

    tenant_proposal, tenant_prewrite = _proposal_and_prewrite(tmp_path / "tenant", tenant_prompt)
    warehouse_proposal, warehouse_prewrite = _proposal_and_prewrite(tmp_path / "warehouse", warehouse_prompt)
    tenant_payload = json.dumps(
        {"proposal": tenant_proposal, "next_steps": tenant_prewrite.package.next_steps_preview},
        sort_keys=True,
    ).casefold()
    warehouse_payload = json.dumps(
        {"proposal": warehouse_proposal, "next_steps": warehouse_prewrite.package.next_steps_preview},
        sort_keys=True,
    ).casefold()
    tenant_actor_labels = [str(row).split(":", 1)[0] for row in tenant_proposal["intent"]["human_actors"]]

    assert "downstream actor" not in tenant_payload
    assert "Packets for Supervisor" not in tenant_actor_labels
    assert "recommendation" not in warehouse_payload
    assert build_greenfield_package_report(tenant_prewrite.package).issues == ()
    assert build_greenfield_package_report(warehouse_prewrite.package).issues == ()
