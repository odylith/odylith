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
)


def _assert_not_mechanical(text: str) -> None:
    for phrase in _BANNED_MECHANICAL_PHRASES:
        assert phrase not in text


def test_observation_voice_uses_fact_detail_and_action_rationale() -> None:
    fact = GovernanceFact(
        kind="governance_truth",
        headline="Radar already has B-096 bound to visible intervention hardening.",
        detail="Extending that workstream prevents a duplicate release lane.",
    )
    action = CaptureAction(
        surface="radar",
        action="update",
        target_kind="workstream",
        target_id="B-096",
        title="Visible Intervention Hardening",
        rationale="Radar already tracks B-096, so this should extend that workstream instead of creating a duplicate slice.",
    )

    _headline, markdown_text, plain_text, teaser_text = voice.render_observation(
        facts=[fact],
        proposal_actions=[action],
        moment={"kind": "continuation", "primary_fact": fact.as_dict()},
        seed="stable",
    )

    assert markdown_text.startswith("**Odylith Observation:** Radar already has B-096")
    assert "Radar already tracks B-096" in markdown_text
    assert plain_text.startswith("Odylith Observation: Radar already has B-096")
    assert teaser_text.startswith("Odylith is tracking this signal:")
    assert "Extending that workstream prevents a duplicate release lane." in teaser_text
    _assert_not_mechanical(markdown_text)
    _assert_not_mechanical(teaser_text)


def test_ambient_voice_uses_supported_fact_content_instead_of_kind_template() -> None:
    fact = GovernanceFact(
        kind="history",
        headline="Casebook already remembers CB-122.",
        detail="The prior recurrence was hidden hook payloads being mistaken for chat-visible proof.",
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
    assert markdown_text.startswith("**Odylith History:** Casebook already remembers CB-122.")
    assert "hidden hook payloads" in markdown_text
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
            rationale="Atlas already has D-038, so the next governed move is a review refresh rather than a duplicate map.",
        ),
        CaptureAction(
            surface="registry",
            action="update",
            target_kind="component",
            target_id="governance-intervention-engine",
            title="Governance Intervention Engine",
            rationale="Registry already maps the runtime boundary, so the living dossier should carry the voice contract.",
        ),
    ]

    markdown_text, plain_text, confirmation = voice.render_proposal(
        actions=actions,
        moment={"kind": "boundary", "primary_fact": fact.as_dict()},
        seed="proposal",
    )

    assert markdown_text.startswith("-----\nOdylith Proposal: Atlas already carries D-038")
    assert "The proposed actions touch Atlas and Registry." in markdown_text
    assert "- Atlas: review refresh D-038." in markdown_text
    assert "review refresh rather than a duplicate map." in markdown_text
    assert "- Registry: update governance-intervention-engine." in markdown_text
    assert confirmation == "apply this proposal"
    assert plain_text == markdown_text
    assert markdown_text.rstrip().endswith("-----")
    _assert_not_mechanical(markdown_text)
