from __future__ import annotations

from pathlib import Path

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


def test_render_prompt_bundle_text_joins_anchor_and_live_text(monkeypatch) -> None:
    monkeypatch.setattr(
        host_intervention_support.conversation_surface,
        "render_live_text",
        lambda *_args, **_kwargs: "Odylith is tracking a real signal.",
    )

    rendered = host_intervention_support.render_prompt_bundle_text(
        bundle={"intervention_bundle": {}},
        anchor_summary="Odylith anchor B-123: primary target src/odylith/runtime/surfaces/host_intervention_support.py.",
        markdown=False,
    )

    assert rendered == (
        "Odylith anchor B-123: primary target src/odylith/runtime/surfaces/host_intervention_support.py.\n\n"
        "Odylith is tracking a real signal."
    )


def test_render_stop_bundle_text_reuses_replayed_live_beat_when_live_text_is_teaser(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        host_intervention_support.conversation_surface,
        "render_live_text",
        lambda *_args, **_kwargs: "Odylith is tracking a real signal.",
    )
    monkeypatch.setattr(
        host_intervention_support.visibility_replay,
        "replayable_chat_markdown",
        lambda **_kwargs: "---\n\n**Odylith Observation:** replayed live beat.\n\n---",
    )
    monkeypatch.setattr(
        host_intervention_support.conversation_surface,
        "render_closeout_text",
        lambda *_args, **_kwargs: "**Odylith Assist:** keep the closeout grounded.",
    )

    rendered = host_intervention_support.render_stop_bundle_text(
        repo_root=tmp_path,
        host_family="codex",
        session_id="sess-1",
        bundle={"intervention_bundle": {}},
    )

    assert rendered == (
        "---\n\n**Odylith Observation:** replayed live beat.\n\n---\n\n"
        "**Odylith Assist:** keep the closeout grounded."
    )
