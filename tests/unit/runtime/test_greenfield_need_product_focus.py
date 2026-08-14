from __future__ import annotations

import json

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source
from odylith.runtime.domain_intelligence.greenfield_need_product_focus import command_product_title
from odylith.runtime.domain_intelligence.greenfield_need_product_focus import is_requester_product_framing
from odylith.runtime.domain_intelligence.greenfield_need_product_focus import need_product_actor_action
from odylith.runtime.domain_intelligence.greenfield_need_product_focus import product_focus_after_command_sentence
from odylith.runtime.domain_intelligence.greenfield_need_product_focus import product_focus_after_need_sentence
from odylith.runtime.domain_intelligence.greenfield_need_product_focus import workflow_object_title
from odylith.runtime.domain_intelligence.greenfield_proposals import build_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_mapping_with_authority


_ACTION_OBJECT_PROMPT = (
    "Our developer-experience group needs a product for extension publishers to assemble release notes "
    "from approved changelog fragments, breaking-change notices, and compatibility windows. Support "
    "engineers and publisher maintainers need the same review view before a release is announced. The "
    "first release boundary is one workspace per extension, a review queue, and an exportable release "
    "brief; marketplace publishing, telemetry, and code scanning are outside this release."
)


def test_need_product_request_uses_action_object_not_requester_framing() -> None:
    source = prompt_intent_source(_ACTION_OBJECT_PROMPT)

    assert product_focus_after_need_sentence(_ACTION_OBJECT_PROMPT) == "release notes"
    assert source.title == "release notes"
    assert "needs a product" not in source.title.casefold()
    assert source.first_path.startswith("extension publishers can assemble release notes")
    assert "first release boundary" not in source.first_path.casefold()
    assert "marketplace publishing" not in source.first_path.casefold()


def test_actor_led_transfer_uses_the_workflow_object_as_product_focus() -> None:
    prompt = (
        "A proteomics team is transferring a DIA mass spectrometry method between two laboratories. "
        "The product must capture peptide library version, retention-time alignment, and iRT standards."
    )

    assert workflow_object_title(prompt) == "DIA mass spectrometry method"
    assert prompt_intent_source(prompt).title == "DIA mass spectrometry method"


def test_command_request_uses_action_object_not_generic_container_and_actor_title() -> None:
    prompt = (
        "Create a tool for extension publishers to assemble release notes from approved changelog fragments, "
        "breaking-change notices, and compatibility windows."
    )

    assert product_focus_after_command_sentence(prompt) == "release notes"
    assert prompt_intent_source(prompt).title == "release notes"


def test_command_container_focus_does_not_overwrite_an_explicit_product_title() -> None:
    prompt = "Create a volunteer scheduling tool for a neighborhood library where staff can assign shifts."

    assert product_focus_after_command_sentence(prompt) == ""
    assert prompt_intent_source(prompt).title == "volunteer scheduling tool"


def test_command_container_focus_does_not_overwrite_a_named_product() -> None:
    prompt = "Create an Extension Publisher Console for extension publishers to manage submissions."

    assert product_focus_after_command_sentence(prompt) == ""
    assert prompt_intent_source(prompt).title == "Extension Publisher Console"


def test_command_title_preserves_a_bounded_domain_object_or_audience() -> None:
    prompts = {
        "Create a compact register for safety captains to certify flame-effect props.": "flame-effect props register",
        "Create a provenance notebook for wetland-restoration nurseries.": (
            "wetland-restoration nurseries provenance notebook"
        ),
        "Create a handoff register for school meal allergen coordinators.": (
            "school meal allergen coordinators handoff register"
        ),
        "Make a stage-lift inspection log for venue rigging teams.": "stage-lift inspection log",
        "Create an ACME Console for operators to manage submissions.": "ACME Console",
    }

    for prompt, expected in prompts.items():
        assert command_product_title(prompt) == expected
        assert prompt_intent_source(prompt).title == expected


def test_command_container_recovers_a_use_for_title_without_completing_the_path() -> None:
    prompt = "Create a tool for extension publishers to use for release notes."

    assert product_focus_after_command_sentence(prompt) == "release notes"
    assert prompt_intent_source(prompt).title == "release notes"


def test_command_container_stops_product_focus_at_the_first_action_boundary() -> None:
    prompt = (
        "Create a greenfield product for municipal permit clerks to intake permit applications, "
        "validate zoning attachments, route reviewer decisions, and show applicants an approval packet."
    )

    assert product_focus_after_command_sentence(prompt) == "permit applications"
    assert prompt_intent_source(prompt).title == "permit applications"


def test_need_product_request_keeps_named_product_focus() -> None:
    prompt = "A research coordinator needs a product for assay review workspace."

    assert product_focus_after_need_sentence(prompt) == "assay review workspace"


def test_need_request_supports_all_container_wrappers() -> None:
    prompts = {
        "A support team needs an app for incident timelines.": "incident timelines",
        "Ops leads need a tool for runbook approvals.": "runbook approvals",
        "Our support team needs a service for incident timelines.": "incident timelines",
        "A support team needs a system for incident timelines.": "incident timelines",
    }

    for prompt, expected_title in prompts.items():
        assert product_focus_after_need_sentence(prompt) == expected_title
        assert prompt_intent_source(prompt).title == expected_title


def test_need_request_uses_a_single_word_action_object() -> None:
    prompt = "A research coordinator needs a product for reviewers to approve assays."

    assert product_focus_after_need_sentence(prompt) == "assays"
    assert prompt_intent_source(prompt).title == "assays"


def test_need_product_request_recovers_actor_infinitive_first_path() -> None:
    prompt = "A support team needs a product for analysts to review exceptions before handoff."

    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(prompt, prompt=prompt)

    assert need_product_actor_action(prompt) == ("analysts", "review exceptions before handoff")
    assert source.title == "exceptions"
    assert source.actor == "analysts"
    assert source.first_path == "analysts can review exceptions before handoff"
    assert "needs a product" not in source.first_path
    assert intent["first_path"].startswith("Analysts can review exceptions before handoff")


def test_direct_need_request_separates_actor_product_object_and_actions() -> None:
    prompt = (
        "A museum registrar needs a register to document inbound loan conditions, compare humidity readings, "
        "request conservator review, obtain lender approval, and create a return readiness summary."
    )

    source = prompt_intent_source(prompt)

    assert need_product_actor_action(prompt) == (
        "museum registrar",
        "document inbound loan conditions, compare humidity readings, request conservator review, "
        "obtain lender approval, and create a return readiness summary",
    )
    assert source.actor == "museum registrar"
    assert source.first_path.startswith("museum registrar can document inbound loan conditions")
    assert "needs a register" not in source.first_path

    bounded = prompt_intent_source(f"{prompt.rstrip('.')} ; it must not transfer ownership.")
    assert "transfer ownership" not in bounded.first_path


def test_path_grant_context_does_not_merge_product_framing_into_actor_or_workflow() -> None:
    prompt = (
        "BarnSignal gives Noor, the veterinary field officer, an outbreak path. "
        "A farmer submits a fever report through the HerdWatch portal."
    )

    source = prompt_intent_source(prompt)

    assert source.actor.rstrip(" ,") == "Noor, the veterinary field officer"
    assert source.first_path == "A farmer submits a fever report through the HerdWatch portal"
    assert "outbreak a farmer" not in source.first_path.casefold()


def test_need_product_request_framing_is_not_a_product_title() -> None:
    assert is_requester_product_framing("Our developer-experience group needs a product")
    assert is_requester_product_framing("A support team needs an app")
    assert not is_requester_product_framing("extension release notes workspace")


def test_need_product_request_compiles_without_requester_framing(tmp_path) -> None:
    envelope = f"""Product Intent Confirmation needed

Original user intent
{_ACTION_OBJECT_PROMPT}

Next step
- Confirm: compile the ProductCreateTransaction.
"""

    intent = parse_confirmed_intent_text(envelope, prompt=_ACTION_OBJECT_PROMPT)
    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=_ACTION_OBJECT_PROMPT,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Release Notes Workspace"
    assert proposal["intent"]["title"] == "Release Notes Workspace"
    assert "review queue" in intent["proof_boundary"].casefold()
    assert "marketplace publishing" not in intent["proof_boundary"].casefold()
    assert "review queue" in proposal["semantic_model"]["domain_ontology"]["proof_boundary"].casefold()
    boundary = next(
        row
        for row in proposal["project_brief"]["blueprint_sections"]
        if row["section"] == "First-release boundary"
    )
    assert "Our Developer-experience Group Needs" not in rendered
    assert "review queue" in rendered.casefold()
    assert boundary["must_capture"] == (
        "The first release includes one workspace per extension, a review queue, and an exportable release brief."
    )
    assert greenfield_quality_issues(proposal) == []
