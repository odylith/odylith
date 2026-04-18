from __future__ import annotations

from odylith.runtime.surfaces import host_intervention_support


def test_join_sections_dedupes_normalized_blocks() -> None:
    assert host_intervention_support.join_sections(" first ", "\nfirst\n", "second") == "first\n\nsecond"


def test_merge_replay_with_closeout_keeps_existing_assist() -> None:
    replay = "---\n\n**Odylith Observation:** already visible.\n\n**Odylith Assist:** already visible.\n\n---"
    closeout = "**Odylith Assist:** keep this grounded."

    assert host_intervention_support.merge_replay_with_closeout(replay=replay, closeout_text=closeout) == replay


def test_looks_like_teaser_live_text_distinguishes_full_live_beats() -> None:
    assert host_intervention_support.looks_like_teaser_live_text("Odylith is tracking a real signal.") is True
    assert (
        host_intervention_support.looks_like_teaser_live_text(
            "---\n\n**Odylith Observation:** This is a real visible beat.\n\n---"
        )
        is False
    )
