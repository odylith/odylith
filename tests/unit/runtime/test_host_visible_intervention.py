from __future__ import annotations

from odylith import cli
from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.intervention_engine import surface_runtime
from odylith.runtime.surfaces import host_visible_intervention


_INTERNAL_VISIBLE_WORDS = (
    "hook",
    "payload",
    "ledger",
    "broker",
    "systemMessage",
    "additionalContext",
    "proof",
    "transcript",
    "fallback",
    "delivery",
)


def _assert_user_facing_visible_voice(rendered: str) -> None:
    for word in _INTERNAL_VISIBLE_WORDS:
        assert word not in rendered
    assert "Odylith Observation:" in rendered or "**Odylith Observation:**" in rendered
    assert "Odylith" in rendered


_CLI_HELP_OUTPUT = """usage: odylith [-h] {start,context,query,sync,codex} ...

Odylith install, grounding, sync, runtime, and repair tooling.

positional arguments:
  {start,context,query,sync,codex}
    start               Choose the safest first Odylith turn-start path.

options:
  -h, --help            show this help message and exit
"""


def _bundle() -> dict[str, object]:
    return {
        "intervention_bundle": {
            "candidate": {
                "stage": "card",
                "suppressed_reason": "",
                "markdown_text": "**Odylith Observation:** The Odylith signal is visible here now.",
                "plain_text": "Odylith Observation: The Odylith signal is visible here now.",
            },
            "proposal": {
                "eligible": True,
                "suppressed_reason": "",
                "markdown_text": (
                    "-----\n"
                    "Odylith Proposal: Preserve the chat-visible UX contract.\n\n"
                    "- Registry: update the host visibility contract.\n\n"
                    "To apply, say \"apply this proposal\".\n"
                    "-----"
                ),
                "plain_text": "Odylith Proposal: Preserve the chat-visible UX contract.",
            },
        },
        "closeout_bundle": {
            "markdown_text": "**Odylith Assist:** kept the visible path alive.",
            "plain_text": "Odylith Assist: kept the visible path alive.",
        },
    }


def test_visible_intervention_renders_live_markdown_without_closeout_by_default(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        host_visible_intervention.host_surface_runtime,
        "compose_host_conversation_bundle",
        lambda **kwargs: _bundle(),
    )

    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="post_bash_checkpoint",
        session_id="unit-visible-live",
        changed_paths=["src/example.py"],
    )

    assert "**Odylith Observation:**" in rendered
    assert "Odylith Proposal:" in rendered
    assert "**Odylith Assist:** kept the visible path alive." not in rendered


def test_visible_intervention_renders_stop_assist(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        host_visible_intervention.host_surface_runtime,
        "compose_host_conversation_bundle",
        lambda **kwargs: _bundle(),
    )

    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="claude",
        phase="stop_summary",
        session_id="unit-visible-stop",
        summary="Implemented the visible fallback.",
    )

    assert "**Odylith Observation:**" in rendered
    assert "**Odylith Assist:** kept the visible path alive." in rendered


def test_stop_visible_intervention_recovers_assist_from_summary_validation(tmp_path) -> None:
    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="stop_summary",
        summary="Validation passed with 551 tests after the visible intervention fallback landed.",
        include_closeout=True,
    )

    assert "**Odylith Assist:**" in rendered
    assert "closing with 1 focused check" in rendered


def test_visible_intervention_operator_visibility_failure_is_never_silent(tmp_path) -> None:
    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="prompt_submit",
        prompt="I do not think it is working",
    )

    assert rendered.startswith("---\n\n**Odylith Observation:** This chat still has no visible Odylith moment")
    assert rendered.count("---") == 2
    assert rendered.rsplit("\n", maxsplit=1)[-1].startswith("**Odylith Assist:**")
    assert "user can see what changed and what happens next" in rendered
    assert "Odylith is tracking this signal" not in rendered
    _assert_user_facing_visible_voice(rendered)


def test_visible_intervention_prompt_submit_defaults_to_assist_for_normal_prompt(tmp_path) -> None:
    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="prompt_submit",
        prompt="Make this intervention path less brittle.",
    )

    assert rendered == (
        "**Odylith Assist:** kept Odylith visible in this chat so the brand promise is something the user can see."
    )
    assert host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="prompt_submit",
        prompt="Odylith, help.",
    ) == ""


def test_visible_intervention_prompt_submit_appends_assist_when_visible_markdown_renders(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        host_visible_intervention.host_surface_runtime,
        "compose_host_conversation_bundle",
        lambda **kwargs: _bundle(),
    )

    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="prompt_submit",
        session_id="unit-visible-prompt-assist",
        prompt="Are all Odylith engines active and firing?",
    )

    assert rendered.startswith("---\n\n**Odylith Observation:**")
    assert "Odylith Proposal:" not in rendered
    assert rendered.rsplit("\n", maxsplit=1)[-1] == "**Odylith Assist:** kept the visible path alive."


def test_visible_intervention_visibility_feedback_adds_assist_after_live_block(tmp_path) -> None:
    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="prompt_submit",
        prompt="I still do not see any Odylith ambient highlights, interventions, or Assist in chat.",
    )

    assert rendered.startswith("---\n\n**Odylith Observation:** This chat still has no visible Odylith moment")
    assert rendered.count("---") == 2
    assert rendered.rsplit("\n", maxsplit=1)[-1].startswith("**Odylith Assist:**")
    assert "kept Odylith visible in this chat" in rendered
    assert "Odylith is tracking this signal" not in rendered
    assert "**Odylith Insight:**" not in rendered
    assert "**Odylith Risks:**" not in rendered
    assert "**Odylith History:**" not in rendered
    _assert_user_facing_visible_voice(rendered)


def test_visible_intervention_suppresses_cli_help_passthrough(tmp_path) -> None:
    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="prompt_submit",
        prompt="Odylith, help.",
        summary=_CLI_HELP_OUTPUT,
    )

    assert rendered == ""


def test_visible_intervention_suppresses_cli_help_stop_replay(tmp_path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending stop replay.",
        session_id="visible-stop-help",
        host_family="codex",
        intervention_key="visible-stop-help-replay",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** stale stop replay",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="stop_summary",
        prompt="Odylith, help.",
        summary=_CLI_HELP_OUTPUT,
        session_id="visible-stop-help",
    )

    assert rendered == ""


def test_visible_intervention_replays_pending_chat_block_before_generic_failure(tmp_path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending observation.",
        session_id="visible-replay",
        host_family="codex",
        intervention_key="visible-replay-key",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** Replay this exact earned block in chat.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_render_required",
        render_surface="codex_post_tool_use",
    )

    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="prompt_submit",
        prompt="I cannot see the Odylith block in chat.",
        session_id="visible-replay",
    )

    assert rendered.startswith("---\n\n**Odylith Observation:** Replay this exact earned block in chat.\n\n---")
    assert "\n\n**Odylith Assist:**" in rendered
    assert "kept Odylith visible in this chat" in rendered
    assert "This is a visibility failure" not in rendered
    _assert_user_facing_visible_voice(rendered)


def test_visible_intervention_detects_only_assist_visibility_feedback(tmp_path) -> None:
    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="prompt_submit",
        prompt="Dude, I am still not sure about Odylith interventions being visible; only " + "As" "sit" + " works",
    )

    assert rendered.startswith("---\n\n**Odylith Observation:** This chat still has no visible Odylith moment")
    assert "user can see what changed and what happens next" in rendered
    assert "**Odylith Assist:**" in rendered
    assert "Odylith is tracking this signal" not in rendered
    _assert_user_facing_visible_voice(rendered)


def test_visible_intervention_can_record_manual_visible_fallback(tmp_path) -> None:
    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="prompt_submit",
        prompt="I do not think it is working",
        session_id="visible-session",
        record_delivery=True,
    )

    events = host_visible_intervention.stream_state.load_recent_intervention_events(
        repo_root=tmp_path,
        session_id="visible-session",
    )
    assert rendered.startswith("---\n\n**Odylith Observation:** This chat still has no visible Odylith moment")
    assert rendered.rsplit("\n", maxsplit=1)[-1].startswith("**Odylith Assist:**")
    assert events[-1]["delivery_status"] == "manual_visible"
    assert events[-1]["delivery_channel"] == "manual_visible_command"
    assert events[-1]["host_family"] == "codex"
    assert events[-1]["session_id"] == "visible-session"
    assert any(row.get("metadata", {}).get("manual_visible") is True for row in events)
    _assert_user_facing_visible_voice(rendered)


def test_chat_confirmation_can_promote_manual_visible_fallback_once(tmp_path) -> None:
    visible = "---\n\n**Odylith Observation:** Manual fallback is now in the assistant transcript.\n\n---"
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Manual visible fallback.",
        session_id="manual-confirm",
        host_family="codex",
        intervention_key="manual-visible-key",
        turn_phase="post_bash_checkpoint",
        display_markdown=visible,
        delivery_channel="manual_visible_command",
        delivery_status="manual_visible",
        render_surface="codex_visible_intervention",
    )

    first = host_surface_runtime.confirm_assistant_chat_delivery(
        repo_root=tmp_path,
        host_family="codex",
        session_id="manual-confirm",
        last_assistant_message=f"Done.\n\n{visible}",
        render_surface="codex_intervention_status",
    )
    second = host_surface_runtime.confirm_assistant_chat_delivery(
        repo_root=tmp_path,
        host_family="codex",
        session_id="manual-confirm",
        last_assistant_message=f"Done.\n\n{visible}",
        render_surface="codex_intervention_status",
    )

    assert [row["delivery_status"] for row in first] == ["assistant_chat_confirmed"]
    assert second == []
    events = stream_state.load_recent_intervention_events(repo_root=tmp_path, session_id="manual-confirm")
    assert [row["delivery_status"] for row in events] == ["manual_visible", "assistant_chat_confirmed"]


def test_chat_confirmation_infers_host_family_for_legacy_manual_visible_rows(tmp_path) -> None:
    visible = "---\n\n**Odylith Observation:** Legacy fallback is visible in chat.\n\n---"
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Legacy manual visible fallback.",
        session_id="legacy-manual-confirm",
        intervention_key="legacy-manual-key",
        turn_phase="post_bash_checkpoint",
        display_markdown=visible,
        delivery_channel="manual_visible_command",
        delivery_status="manual_visible",
        render_surface="codex_visible_intervention",
    )

    confirmed = host_surface_runtime.confirm_assistant_chat_delivery(
        repo_root=tmp_path,
        host_family="codex",
        session_id="legacy-manual-confirm",
        last_assistant_message=f"{visible}\n",
        render_surface="codex_intervention_status",
    )

    assert [row["delivery_status"] for row in confirmed] == ["assistant_chat_confirmed"]
    assert confirmed[0]["host_family"] == "codex"


def test_chat_confirmation_preserves_value_decision_metadata(tmp_path) -> None:
    visible = "---\n\n**Odylith Observation:** Preserve exact chat-visible proof.\n\n---"
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending visible proof.",
        session_id="confirm-meta",
        host_family="codex",
        intervention_key="confirm-meta-key",
        turn_phase="stop_summary",
        display_markdown=visible,
        semantic_signature=("visible", "proof"),
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_render_required",
        metadata={
            "value_decision": {
                "selected": [{"candidate_id": "observation:confirm-meta"}],
                "suppressed": [],
            }
        },
    )

    confirmed = host_surface_runtime.confirm_assistant_chat_delivery(
        repo_root=tmp_path,
        host_family="codex",
        session_id="confirm-meta",
        last_assistant_message=visible,
        render_surface="codex_stop_summary",
    )

    assert confirmed[-1]["delivery_status"] == "assistant_chat_confirmed"
    assert confirmed[-1]["metadata"]["value_decision"]["selected"][0]["candidate_id"] == "observation:confirm-meta"


def test_visible_intervention_replaces_generic_teaser_for_visibility_failure(tmp_path) -> None:
    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="claude",
        phase="prompt_submit",
        prompt="Dude, I still do not see any Odylith Observation, Proposal, Ambient, or Assist in chat.",
    )

    assert rendered.startswith("---\n\n**Odylith Observation:** This chat still has no visible Odylith moment")
    assert "user can see what changed and what happens next" in rendered
    assert rendered.count("---") == 2
    assert rendered.rsplit("\n", maxsplit=1)[-1].startswith("**Odylith Assist:**")
    assert "One more corroborating signal" not in rendered
    assert "Odylith is tracking this signal" not in rendered
    assert "**Odylith Insight:**" not in rendered
    _assert_user_facing_visible_voice(rendered)


def test_visible_intervention_status_review_surfaces_current_visibility_truth_not_workstream_scope(tmp_path) -> None:
    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="claude",
        phase="stop_summary",
        prompt="Is that observation accurate and relevant?",
        summary=(
            "Overall posture for this session:\n"
            "- Activation: ready\n"
            "- Chat-visible proof: unproven_this_session\n"
            "- End-to-end gate: not met.\n\n"
            "**Odylith Observation:** Radar already has B-096 for this slice. Extend that workstream instead of "
            "creating a duplicate backlog record."
        ),
    )

    assert rendered.startswith("---\n\n**Odylith Observation:** Odylith is on, but this chat still has no visible Odylith moment.")
    assert "what Odylith is doing" in rendered
    assert "Radar already has B-096" not in rendered
    _assert_user_facing_visible_voice(rendered)


def test_codex_visible_intervention_cli_dispatches_plain_markdown(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(
        host_visible_intervention.host_surface_runtime,
        "compose_host_conversation_bundle",
        lambda **kwargs: _bundle(),
    )

    exit_code = cli.main(
        [
            "codex",
            "visible-intervention",
            "--repo-root",
            str(tmp_path),
            "--phase",
            "post_bash_checkpoint",
            "--changed-path",
            "src/example.py",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert output.startswith(f"{surface_runtime.LIVE_BOUNDARY}\n\n**Odylith Observation:**")
    assert "Odylith Proposal:" in output
    assert not output.lstrip().startswith("{")


def test_claude_visible_intervention_cli_dispatches_plain_markdown(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(
        host_visible_intervention.host_surface_runtime,
        "compose_host_conversation_bundle",
        lambda **kwargs: _bundle(),
    )

    exit_code = cli.main(
        [
            "claude",
            "visible-intervention",
            "--repo-root",
            str(tmp_path),
            "--phase",
            "stop_summary",
            "--summary",
            "Implemented the visible fallback.",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "**Odylith Assist:** kept the visible path alive." in output
    assert not output.lstrip().startswith("{")
