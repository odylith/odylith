from __future__ import annotations

from odylith.runtime.intervention_engine import voice
from odylith.runtime.intervention_engine.contract import CaptureAction
from odylith.runtime.intervention_engine.contract import GovernanceFact


_BANNED_MECHANICAL_PHRASES = (
    "Odylith can already",
    "One more corroborating signal",
    "There is a clean way",
    "one clean governed bundle",
    "whole bundle can move",
    "Let the owned boundary",
    "Casebook already has related memory in the frame",
    "governed truth",
    "safe apply lane",
    "living component dossier",
    "affected surfaces",
    "supported actions can move through one confirmation",
    "hook",
    "payload",
    "ledger",
    "broker",
    "systemMessage",
    "additionalContext",
)


def _assert_not_mechanical(text: str) -> None:
    for phrase in _BANNED_MECHANICAL_PHRASES:
        assert phrase not in text


def test_observation_voice_uses_fact_detail_and_action_rationale() -> None:
    fact = GovernanceFact(
        kind="governance_truth",
        headline="B-096 is the live Radar lane for visible intervention hardening.",
        detail="The next proof belongs on that lane while this turn is still touching it.",
    )
    action = CaptureAction(
        surface="radar",
        action="update",
        target_kind="workstream",
        target_id="B-096",
        title="Visible Intervention Hardening",
        rationale="Local Radar candidate: B-096. Update it only if it still owns this work.",
    )

    _headline, markdown_text, plain_text, teaser_text = voice.render_observation(
        facts=[fact],
        proposal_actions=[action],
        moment={"kind": "continuation", "primary_fact": fact.as_dict()},
        seed="stable",
    )

    assert markdown_text.startswith("**Odylith Observation:** B-096 is the live Radar lane")
    assert "Update it only if it still owns this work" in markdown_text
    assert plain_text.startswith("Odylith Observation: B-096 is the live Radar lane")
    assert teaser_text.startswith("Odylith Observation:")
    assert "Odylith is tracking this signal" not in teaser_text
    assert "The next proof belongs on that lane" in teaser_text
    _assert_not_mechanical(markdown_text)
    _assert_not_mechanical(teaser_text)


def test_ambient_voice_uses_supported_fact_content_instead_of_kind_template() -> None:
    fact = GovernanceFact(
        kind="history",
        headline="Casebook has a matching visibility failure.",
        detail="A prior recurrence counted Odylith as active before users could see it.",
        refs=[{"kind": "bug", "id": "CB-122", "label": "CB-122", "path": ""}],
        priority=90,
    )

    label_kind, markdown_text = voice.render_ambient_signal(
        moment={
            "kind": "recovery",
            "ambient_label_kind": "history",
            "primary_fact": fact.as_dict(),
        },
        facts=[fact],
        markdown=True,
        seed="history",
    )

    assert label_kind == "history"
    assert markdown_text.startswith("**Odylith History:** Casebook has a matching visibility failure.")
    assert "before users could see it" in markdown_text
    _assert_not_mechanical(markdown_text)


def test_proposal_voice_keeps_shell_fixed_but_derives_body_from_fact_and_actions() -> None:
    fact = GovernanceFact(
        kind="topology",
        headline="Atlas already carries D-038 for the observation/proposal flow.",
        detail="That diagram is the owned place to show the evidence-to-renderer path.",
    )
    actions = [
        CaptureAction(
            surface="atlas",
            action="review_refresh",
            target_kind="diagram",
            target_id="D-038",
            title="Conversation Observation Flow",
            rationale="Atlas already has D-038, so refresh that diagram instead of creating another one.",
        ),
        CaptureAction(
            surface="registry",
            action="update",
            target_kind="component",
            target_id="governance-intervention-engine",
            title="Governance Intervention Engine",
            rationale="Local Registry candidate: `governance-intervention-engine`. Update it only if it owns this boundary.",
        ),
    ]

    markdown_text, plain_text, confirmation = voice.render_proposal(
        actions=actions,
        moment={"kind": "boundary", "primary_fact": fact.as_dict()},
        seed="proposal",
    )

    assert markdown_text.startswith("-----\nOdylith Proposal: Atlas already carries D-038")
    assert "This would touch Atlas and Registry." in markdown_text
    assert "- Atlas: review D-038." in markdown_text
    assert "refresh that diagram instead of creating another one." in markdown_text
    assert "- Registry: update governance-intervention-engine." in markdown_text
    assert "Some actions still need manual review because Odylith cannot apply them safely yet." in markdown_text
    assert confirmation == "apply this proposal"
    assert plain_text == markdown_text
    assert markdown_text.rstrip().endswith("-----")
    _assert_not_mechanical(markdown_text)
