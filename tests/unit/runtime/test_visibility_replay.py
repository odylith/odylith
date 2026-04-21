from __future__ import annotations

from pathlib import Path

from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.intervention_engine import visibility_replay


def test_replay_returns_visible_and_hidden_blocks_until_transcript_confirmation(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="ambient_signal",
        summary="Odylith Risks",
        session_id="replay-session",
        host_family="codex",
        intervention_key="risk",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Risks:** Hidden risk still needs chat proof.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Odylith Observation",
        session_id="replay-session",
        host_family="codex",
        intervention_key="observation",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** Manual visible is still not transcript proof.",
        delivery_channel="manual_visible_command",
        delivery_status="manual_visible",
    )

    replay = visibility_replay.replayable_chat_markdown(
        repo_root=tmp_path,
        host_family="codex",
        session_id="replay-session",
    )

    assert replay == (
        "---\n\n"
        "**Odylith Risks:** Hidden risk still needs chat proof.\n"
        "\n---"
    )

    confirmed = host_surface_runtime.confirm_assistant_chat_delivery(
        repo_root=tmp_path,
        host_family="codex",
        session_id="replay-session",
        last_assistant_message=replay,
        render_surface="codex_intervention_status",
    )

    assert len(confirmed) == 1
    assert visibility_replay.replayable_chat_markdown(
        repo_root=tmp_path,
        host_family="codex",
        session_id="replay-session",
    ) == ""


def test_replay_dedupes_latest_blocks_and_keeps_assist_unwrapped(tmp_path: Path) -> None:
    for index in range(4):
        stream_state.append_intervention_event(
            repo_root=tmp_path,
            kind="ambient_signal",
            summary=f"Odylith Insight {index}",
            session_id="replay-dedupe",
            host_family="claude",
            intervention_key=f"ambient-{index}",
            turn_phase="post_edit_checkpoint",
            display_markdown=f"**Odylith Insight:** ambient {index}.",
            delivery_channel="system_message_and_assistant_fallback",
            delivery_status="assistant_fallback_ready",
        )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="ambient_signal",
        summary="Duplicate ambient.",
        session_id="replay-dedupe",
        host_family="claude",
        intervention_key="ambient-3",
        turn_phase="post_edit_checkpoint",
        display_markdown="**Odylith Insight:** ambient 3.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="assist_closeout",
        summary="Odylith Assist",
        session_id="replay-dedupe",
        host_family="claude",
        intervention_key="assist",
        turn_phase="stop_summary",
        display_markdown="---\n\n**Odylith Assist:** closeout stays outside the live ruler.\n\n---",
        delivery_channel="stop_one_shot_guard",
        delivery_status="stop_continuation_ready",
    )

    replay = visibility_replay.replayable_chat_markdown(
        repo_root=tmp_path,
        host_family="claude",
        session_id="replay-dedupe",
        ambient_cap=3,
        include_assist=True,
    )

    assert "**Odylith Insight:** ambient 0." not in replay
    assert replay.count("**Odylith Insight:**") == 3
    assert replay.count("**Odylith Insight:** ambient 3.") == 1
    assert "**Odylith Assist:** closeout stays outside the live ruler." not in replay


def test_preferred_replay_prioritizes_history_and_risks_ambient_over_intervention_blocks(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Primary observation.",
        session_id="preferred-replay",
        host_family="codex",
        intervention_key="preferred-observation",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** Replay the primary intervention block first.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_render_required",
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="ambient_signal",
        summary="Newer ambient risk.",
        session_id="preferred-replay",
        host_family="codex",
        intervention_key="preferred-risk",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Risks:** A newer ambient note should not outrank the intervention block.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_render_required",
    )

    preferred = visibility_replay.preferred_replayable_chat_markdown(
        repo_root=tmp_path,
        host_family="codex",
        session_id="preferred-replay",
        include_assist=False,
        include_teaser=False,
    )

    assert preferred == (
        "---\n\n"
        "**Odylith Risks:** A newer ambient note should not outrank the intervention block.\n"
        "\n---\n\n"
        "---\n\n"
        "**Odylith Observation:** Replay the primary intervention block first.\n"
        "\n---"
    )


def test_preferred_replay_prioritizes_history_and_risks_over_plain_insight_ambient(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="ambient_signal",
        summary="Ambient history should stay ahead.",
        session_id="preferred-ambient-replay",
        host_family="claude",
        intervention_key="preferred-history",
        turn_phase="post_edit_checkpoint",
        display_markdown="**Odylith History:** Earlier history still matters more than a later generic insight.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_render_required",
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="ambient_signal",
        summary="Newer ambient insight.",
        session_id="preferred-ambient-replay",
        host_family="claude",
        intervention_key="preferred-insight",
        turn_phase="post_edit_checkpoint",
        display_markdown="**Odylith Insight:** A newer generic insight should not outrank history or risks.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_render_required",
    )

    preferred = visibility_replay.preferred_replayable_chat_markdown(
        repo_root=tmp_path,
        host_family="claude",
        session_id="preferred-ambient-replay",
        include_assist=False,
        include_teaser=False,
    )

    assert preferred == (
        "---\n\n"
        "**Odylith History:** Earlier history still matters more than a later generic insight.\n"
        "\n---\n\n"
        "---\n\n"
        "**Odylith Insight:** A newer generic insight should not outrank history or risks.\n"
        "\n---"
    )
