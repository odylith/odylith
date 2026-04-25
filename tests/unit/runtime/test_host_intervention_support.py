from __future__ import annotations

from pathlib import Path

from odylith.runtime.surfaces import host_intervention_support


def test_join_sections_dedupes_normalized_blocks() -> None:
    assert host_intervention_support.join_sections(" first ", "\nfirst\n", "second") == "first\n\nsecond"


def test_merge_replay_with_closeout_keeps_existing_assist() -> None:
    replay = "---\n\n**Odylith Observation:** already visible.\n\n**Odylith Assist:** already visible.\n\n---"
    closeout = "**Odylith Assist:** keep this grounded."

    rendered = host_intervention_support.merge_replay_with_closeout(replay=replay, closeout_text=closeout)

    assert rendered == "---\n\n**Odylith Observation:** already visible.\n\n---\n\n**Odylith Assist:** already visible."


def test_merge_replay_with_closeout_folds_live_blocks_and_keeps_assist_last() -> None:
    replay = (
        "---\n\n**Odylith Observation:** first visible beat.\n\n---\n\n"
        "---\n\nOdylith is tracking this signal.\n\n---"
    )
    closeout = (
        "**Odylith Assist:** keep the closeout grounded.\n"
        "**Odylith Insight:** the supplemental line should not trail Assist."
    )

    rendered = host_intervention_support.merge_replay_with_closeout(
        replay=replay,
        closeout_text=closeout,
    )

    assert rendered.count("---") == 2
    assert rendered.startswith(
        "---\n\n**Odylith Observation:** first visible beat.\n\nOdylith is tracking this signal.\n\n---"
    )
    assert rendered.rsplit("\n", maxsplit=1)[-1] == "**Odylith Assist:** keep the closeout grounded."
    assert rendered.index("**Odylith Insight:**") < rendered.index("**Odylith Assist:**")


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


def test_render_prompt_system_message_appends_assist_for_visibility_feedback(tmp_path: Path) -> None:
    rendered = host_intervention_support.render_prompt_system_message(
        repo_root=tmp_path,
        host_family="codex",
        prompt="I still do not see any Odylith interventions or Assist in chat.",
        session_id="visibility-feedback",
    )

    assert rendered.startswith("---\n\n**Odylith Observation:** This is a visibility failure")
    assert rendered.count("---") == 2
    assert rendered.rsplit("\n", maxsplit=1)[-1].startswith("**Odylith Assist:**")
    assert "keeping Odylith visibility honest by naming the chat-visible complaint" in rendered


def test_render_prompt_system_message_keeps_assist_hidden_for_generic_failure(tmp_path: Path) -> None:
    rendered = host_intervention_support.render_prompt_system_message(
        repo_root=tmp_path,
        host_family="codex",
        prompt="I do not think it is working",
        session_id="generic-failure",
    )

    assert rendered.startswith("---\n\n**Odylith Observation:** This is a visibility failure")
    assert "**Odylith Assist:**" not in rendered


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
