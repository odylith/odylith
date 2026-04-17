from __future__ import annotations

from odylith import cli
from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.intervention_engine import surface_runtime
from odylith.runtime.surfaces import host_visible_intervention


def _bundle() -> dict[str, object]:
    return {
        "intervention_bundle": {
            "candidate": {
                "stage": "card",
                "suppressed_reason": "",
                "markdown_text": "**Odylith Observation:** The host hid the hook, so the assistant speaks it.",
                "plain_text": "Odylith Observation: The host hid the hook, so the assistant speaks it.",
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


def test_visible_intervention_renders_live_markdown_without_assist(monkeypatch) -> None:
    monkeypatch.setattr(
        host_visible_intervention.host_surface_runtime,
        "compose_host_conversation_bundle",
        lambda **kwargs: _bundle(),
    )

    rendered = host_visible_intervention.render_visible_intervention(
        host_family="codex",
        phase="post_bash_checkpoint",
        changed_paths=["src/example.py"],
    )

    assert "**Odylith Observation:**" in rendered
    assert "Odylith Proposal:" in rendered
    assert "Odylith Assist:" not in rendered


def test_visible_intervention_renders_stop_assist(monkeypatch) -> None:
    monkeypatch.setattr(
        host_visible_intervention.host_surface_runtime,
        "compose_host_conversation_bundle",
        lambda **kwargs: _bundle(),
    )

    rendered = host_visible_intervention.render_visible_intervention(
        host_family="claude",
        phase="stop_summary",
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

    assert "**Odylith Assist:** kept the proof tight" in rendered
    assert "closing with 1 focused check" in rendered


def test_visible_intervention_operator_visibility_failure_is_never_silent(tmp_path) -> None:
    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="prompt_submit",
        prompt="I do not think it is working",
    )

    assert rendered.startswith("---\n\n**Odylith Observation:** This is a visibility failure")
    assert rendered.endswith("\n---")
    assert "show the Odylith Markdown directly" in rendered


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

    assert rendered == "---\n\n**Odylith Observation:** Replay this exact earned block in chat.\n\n---"
    assert "This is a visibility failure" not in rendered


def test_visible_intervention_detects_only_assist_visibility_feedback(tmp_path) -> None:
    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="prompt_submit",
        prompt="Dude, I am still not sure about Odylith interventions being visible; only Assit works",
    )

    assert rendered.startswith("---\n\n**Odylith Observation:** This is a visibility failure")
    assert rendered.endswith("\n---")
    assert "Codex may be computing intervention payloads" in rendered


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
    assert rendered.startswith("---\n\n**Odylith Observation:** This is a visibility failure")
    assert rendered.endswith("\n---")
    assert events[-1]["delivery_status"] == "manual_visible"
    assert events[-1]["delivery_channel"] == "manual_visible_command"
    assert events[-1]["host_family"] == "codex"
    assert events[-1]["session_id"] == "visible-session"
    assert events[-1]["metadata"]["manual_visible"] is True


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

    assert rendered.startswith("---\n\n**Odylith Observation:** This is a visibility failure")
    assert rendered.endswith("\n---")
    assert "Claude may be computing intervention payloads" in rendered
    assert "One more corroborating signal" not in rendered


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
