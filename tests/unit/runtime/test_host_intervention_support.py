from __future__ import annotations

from pathlib import Path

from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.surfaces import host_intervention_support


_CLI_HELP_OUTPUT = """usage: odylith [-h] {start,context,query,sync,codex} ...

Odylith install, grounding, sync, runtime, and repair tooling.

positional arguments:
  {start,context,query,sync,codex}
    start               Choose the safest first Odylith turn-start path.

options:
  -h, --help            show this help message and exit
"""


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
        "---\n\nOdylith Observation: second visible beat.\n\n---"
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
        "---\n\n**Odylith Observation:** first visible beat.\n\nOdylith Observation: second visible beat.\n\n---"
    )
    assert rendered.rsplit("\n", maxsplit=1)[-1] == "**Odylith Assist:** keep the closeout grounded."
    assert rendered.index("**Odylith Insight:**") < rendered.index("**Odylith Assist:**")


def test_looks_like_teaser_live_text_distinguishes_full_live_beats() -> None:
    assert host_intervention_support.looks_like_teaser_live_text("Odylith Observation: a real signal is forming.") is True
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
        lambda *_args, **_kwargs: "Odylith Observation: a real signal is forming.",
    )

    rendered = host_intervention_support.render_prompt_bundle_text(
        bundle={"intervention_bundle": {}},
        anchor_summary="Odylith anchor B-123: primary target src/odylith/runtime/surfaces/host_intervention_support.py.",
        markdown=False,
    )

    assert rendered == (
        "Odylith anchor B-123: primary target src/odylith/runtime/surfaces/host_intervention_support.py.\n\n"
        "Odylith Observation: a real signal is forming."
    )


def test_render_prompt_system_message_appends_assist_for_visibility_feedback(tmp_path: Path) -> None:
    rendered = host_intervention_support.render_prompt_system_message(
        repo_root=tmp_path,
        host_family="codex",
        prompt="I still do not see any Odylith interventions or Assist in chat.",
        session_id="visibility-feedback",
    )

    assert rendered.startswith(
        "---\n\n**Odylith Observation:** Codex has Odylith activity, but no Odylith note has reached this chat yet."
    )
    assert rendered.count("---") == 2
    assert rendered.rsplit("\n", maxsplit=1)[-1].startswith("**Odylith Assist:**")
    assert "visibility feedback noted; this line is deliberately shown in chat" in rendered
    assert "Odylith is tracking this signal" not in rendered
    assert "**Odylith Insight:**" not in rendered
    assert "**Odylith Risks:**" not in rendered
    assert "**Odylith History:**" not in rendered
    assert "B-096" not in rendered
    assert "CB-122" not in rendered
    assert "D-038" not in rendered
    assert "Casebook already remembers" not in rendered


def test_prompt_bundle_preserves_engine_alignment_proof_for_visible_assist(tmp_path: Path) -> None:
    bundle = host_intervention_support.build_prompt_conversation_bundle(
        repo_root=tmp_path,
        host_family="codex",
        prompt="I still do not see any Odylith interventions or Assist in chat.",
        session_id="prompt-proof",
    )
    proof = dict(bundle["observation"]["alignment_proof"])
    lanes = {
        row["lane_id"]: row
        for row in proof["lanes"]
        if isinstance(row, dict)
    }

    assert proof["proof_kind"] == "visibility_recovery"
    assert proof["status"] == "ready"
    assert proof["missing_required_lanes"] == []
    assert lanes["context_engine"]["status"] == "covered"
    assert lanes["execution_engine"]["status"] == "covered"
    assert lanes["intervention_engine"]["status"] == "covered"
    assert lanes["tribunal"]["status"] == "covered"
    assert lanes["delivery"]["status"] == "covered"
    assert lanes["memory_substrate"]["status"] == "covered"
    assert lanes["subagent_orchestration"]["status"] == "policy_deferred"


def test_render_prompt_system_message_keeps_generic_failure_free_of_fake_assist(tmp_path: Path) -> None:
    rendered = host_intervention_support.render_prompt_system_message(
        repo_root=tmp_path,
        host_family="codex",
        prompt="I do not think it is working",
        session_id="generic-failure",
    )

    assert rendered.startswith(
        "---\n\n**Odylith Observation:** Codex has Odylith activity, but no Odylith note has reached this chat yet."
    )
    assert "**Odylith Assist:**" not in rendered


def test_render_prompt_system_message_suppresses_help_fast_path_and_replay(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending replay that should not leak into CLI help.",
        session_id="help-fast-path",
        host_family="codex",
        intervention_key="help-fast-path-replay",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** stale replay",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    rendered = host_intervention_support.render_prompt_system_message(
        repo_root=tmp_path,
        host_family="codex",
        prompt="Odylith, help.",
        session_id="help-fast-path",
    )

    assert rendered == ""


def test_suppress_prompt_live_narration_detects_cli_help_stdout() -> None:
    assert host_intervention_support.suppress_prompt_live_narration(
        prompt="What commands does Odylith support?",
        assistant_summary=_CLI_HELP_OUTPUT,
    )


def test_build_stop_conversation_bundle_suppresses_cli_help_stdout(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending stop replay that should not leak into CLI help.",
        session_id="stop-help-fast-path",
        host_family="codex",
        intervention_key="stop-help-fast-path-replay",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** stale stop replay",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    bundle = host_intervention_support.build_stop_conversation_bundle(
        repo_root=tmp_path,
        host_family="codex",
        session_id="stop-help-fast-path",
        assistant_summary=_CLI_HELP_OUTPUT,
        prompt_excerpt="",
        changed_paths=[],
        workstreams=[],
        components=[],
    )

    assert bundle == {}


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
