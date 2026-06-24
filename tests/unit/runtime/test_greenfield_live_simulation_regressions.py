from __future__ import annotations

import json
from pathlib import Path
import re

from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_issues
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_proposals import build_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues


def _intent_from_prompt(prompt: str) -> dict[str, object]:
    return parse_confirmed_intent_text(
        f"""
Product Intent Confirmation needed

Original user intent
{prompt}
""",
        prompt=prompt,
    )


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
