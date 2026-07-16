from __future__ import annotations

import json

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source
from odylith.runtime.domain_intelligence.greenfield_need_product_focus import is_requester_product_framing
from odylith.runtime.domain_intelligence.greenfield_need_product_focus import need_product_actor_action
from odylith.runtime.domain_intelligence.greenfield_need_product_focus import product_focus_after_need_sentence
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
    assert "Our Developer-experience Group Needs" not in rendered
    assert greenfield_quality_issues(proposal) == []
