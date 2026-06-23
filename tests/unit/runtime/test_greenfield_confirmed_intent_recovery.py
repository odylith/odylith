from __future__ import annotations

import json

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
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
