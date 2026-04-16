from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import surface_runtime


def test_recent_session_helpers_do_not_bleed_without_session_id(tmp_path: Path) -> None:
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_teaser",
        summary="Observation forming.",
        session_id="known-session",
        host_family="codex",
        intervention_key="iv-known",
        turn_phase="prompt_submit",
        prompt_excerpt="Keep the prompt memory specific.",
        artifacts=["src/example.py"],
        workstreams=["B-096"],
        components=["governance-intervention-engine"],
    )

    assert surface_runtime.recent_session_prompt_excerpt(repo_root=tmp_path, session_id="") == ""
    assert surface_runtime.recent_session_changed_paths(repo_root=tmp_path, session_id="") == []
    assert surface_runtime.recent_session_ids(repo_root=tmp_path, session_id="", field="workstreams") == []


def test_recent_session_live_markdown_recovers_unseen_live_beats_only(tmp_path: Path) -> None:
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Already shown.",
        session_id="known-session",
        host_family="codex",
        intervention_key="iv-visible",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** Already shown.",
        delivery_channel="manual_visible_command",
        delivery_status="manual_visible",
    )
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="capture_proposed",
        summary="Proposal ready.",
        session_id="known-session",
        host_family="codex",
        intervention_key="iv-unseen",
        turn_phase="post_bash_checkpoint",
        display_markdown="-----\nOdylith Proposal: keep this visible.\n-----",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    assert surface_runtime.recent_session_live_markdown(
        repo_root=tmp_path,
        session_id="known-session",
    ) == "-----\nOdylith Proposal: keep this visible.\n-----"


def test_compose_host_conversation_bundle_recovers_recent_checkpoint_context(tmp_path: Path) -> None:
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Observation rendered.",
        session_id="checkpoint-1",
        host_family="codex",
        intervention_key="iv-checkpoint-1",
        turn_phase="post_bash_checkpoint",
        prompt_excerpt="Keep interventions visible before the final answer.",
        artifacts=["src/odylith/runtime/intervention_engine/voice.py"],
        workstreams=["B-096"],
        components=["governance-intervention-engine"],
        display_markdown="**Odylith Observation:** The signal is real.",
    )

    bundle = host_surface_runtime.compose_host_conversation_bundle(
        repo_root=tmp_path,
        host_family="codex",
        turn_phase="post_bash_checkpoint",
        session_id="checkpoint-1",
    )

    assist = dict(bundle["closeout_bundle"]["assist"])
    assert bundle["intervention_bundle"]
    assert assist["eligible"] is True
    assert "1 candidate path" in assist["markdown_text"]
    assert "[B-096](?tab=radar&workstream=B-096)" in assist["markdown_text"]
    assert "[governance-intervention-engine](?tab=registry&component=governance-intervention-engine)" in assist["markdown_text"]
    assert [row["id"] for row in assist["affected_contracts"]] == ["B-096", "governance-intervention-engine"]


def test_codex_post_tool_payload_uses_additional_context_and_system_message() -> None:
    payload = host_surface_runtime.codex_post_tool_payload(
        developer_context="**Odylith Observation:** The signal is real.\n\n**Odylith Assist:** kept this grounded.",
        system_message="Odylith governance refresh completed.",
    )

    assert payload["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "Odylith visible delivery fallback:" in payload["hookSpecificOutput"]["additionalContext"]
    assert "<odylith-visible-markdown>" in payload["hookSpecificOutput"]["additionalContext"]
    assert "Odylith developer continuity:" in payload["hookSpecificOutput"]["additionalContext"]
    assert "**Odylith Observation:** The signal is real." in payload["hookSpecificOutput"]["additionalContext"]
    assert "**Odylith Assist:** kept this grounded." in payload["hookSpecificOutput"]["additionalContext"]
    assert payload["systemMessage"] == "Odylith governance refresh completed."


def test_codex_prompt_payload_uses_prompt_context_and_visible_teaser() -> None:
    payload = host_surface_runtime.codex_prompt_payload(
        additional_context="Odylith anchor B-096: primary target src/main.py.\n\nOdylith can already see governed truth taking shape here.",
        system_message="Odylith can already see governed truth taking shape here.",
    )

    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "Odylith visible delivery fallback:" in payload["hookSpecificOutput"]["additionalContext"]
    assert "Odylith anchor B-096" in payload["hookSpecificOutput"]["additionalContext"]
    assert payload["systemMessage"] == "Odylith can already see governed truth taking shape here."


def test_claude_post_tool_payload_uses_additional_context_and_system_message() -> None:
    payload = host_surface_runtime.claude_post_tool_payload(
        developer_context="**Odylith Observation:** The signal is real.",
        system_message="Odylith governance refresh completed.",
    )

    assert "Odylith visible delivery fallback:" in payload["additionalContext"]
    assert "Odylith developer continuity:" in payload["additionalContext"]
    assert "**Odylith Observation:** The signal is real." in payload["additionalContext"]
    assert payload["systemMessage"] == "Odylith governance refresh completed."


def test_claude_prompt_payload_keeps_prompt_context_discreet() -> None:
    payload = host_surface_runtime.claude_prompt_payload(
        additional_context="Odylith anchor B-096: primary target src/main.py.\n\nOdylith can already see governed truth taking shape here.",
        system_message="Odylith can already see governed truth taking shape here.",
    )

    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "Odylith visible delivery fallback:" in payload["hookSpecificOutput"]["additionalContext"]
    assert "Odylith anchor B-096" in payload["hookSpecificOutput"]["additionalContext"]
    assert "systemMessage" not in payload


def test_stop_payload_is_empty_without_message() -> None:
    assert host_surface_runtime.stop_payload(system_message="") == {}


def test_stop_payload_can_force_one_visible_delivery_continuation() -> None:
    payload = host_surface_runtime.stop_payload(
        system_message="**Odylith Assist:** kept this grounded.",
        block_for_visible_delivery=True,
    )

    assert payload["systemMessage"] == "**Odylith Assist:** kept this grounded."
    assert payload["decision"] == "block"
    assert "**Odylith Assist:** kept this grounded." in payload["reason"]
    assert "code fence" in payload["reason"]


def test_visible_delivery_already_present_suppresses_stop_block() -> None:
    assert host_surface_runtime.visible_delivery_already_present(
        last_assistant_message="Implemented the fix.\n\n**Odylith Assist:** kept this grounded.",
        visible_text="**Odylith Assist:** kept this grounded.",
    )


def test_visible_delivery_already_present_requires_the_same_visible_labels() -> None:
    assert not host_surface_runtime.visible_delivery_already_present(
        last_assistant_message="Implemented the fix.\n\n**Odylith Observation:** The signal is real.",
        visible_text="**Odylith Assist:** kept this grounded.",
    )
    assert not host_surface_runtime.visible_delivery_already_present(
        last_assistant_message="Implemented the fix.\n\n**Odylith Observation:** The signal is real.",
        visible_text=(
            "**Odylith Observation:** The signal is real.\n\n"
            "**Odylith Assist:** kept this grounded."
        ),
    )
    assert host_surface_runtime.visible_delivery_already_present(
        last_assistant_message=(
            "Implemented the fix.\n\n"
            "**Odylith Observation:** The signal is real.\n\n"
            "**Odylith Assist:** kept this grounded."
        ),
        visible_text=(
            "**Odylith Observation:** The signal is real.\n\n"
            "**Odylith Assist:** kept this grounded."
        ),
    )


def test_normalized_session_id_falls_back_when_host_payload_is_missing() -> None:
    token = host_surface_runtime.normalized_session_id("", host_family="codex")
    assert token
    assert isinstance(token, str)
    json.dumps({"session_id": token})


def test_render_visible_live_intervention_excludes_closeout_text() -> None:
    rendered = host_surface_runtime.render_visible_live_intervention(
        {
            "intervention_bundle": {
                "candidate": {
                    "stage": "card",
                    "markdown_text": "**Odylith Observation:** The signal is real.",
                    "plain_text": "Odylith Observation: The signal is real.",
                },
                "proposal": {
                    "eligible": True,
                    "markdown_text": '-----\nOdylith Proposal: Keep this grounded.\n\nTo apply, say "apply this proposal".\n-----',
                    "plain_text": 'Odylith Proposal: Keep this grounded. To apply, say "apply this proposal".',
                },
            },
            "closeout_bundle": {
                "markdown_text": "**Odylith Assist:** kept this grounded.",
                "plain_text": "Odylith Assist: kept this grounded.",
            },
        },
        markdown=True,
        include_proposal=True,
    )

    assert "**Odylith Observation:** The signal is real." in rendered
    assert "Odylith Proposal:" in rendered
    assert "Odylith Assist:" not in rendered


def test_codex_prompt_visible_text_comes_from_system_message_not_hidden_context() -> None:
    payload = host_surface_runtime.codex_prompt_payload(
        additional_context="Odylith anchor B-096: primary target src/main.py.\n\nOdylith can already see governed truth taking shape here.",
        system_message="Odylith can already see governed truth taking shape here.",
    )

    visible = host_surface_runtime.chat_visible_text(
        payload,
        host_family="codex",
        turn_phase="prompt_submit",
    )

    assert visible == "Odylith can already see governed truth taking shape here."
    assert "Odylith anchor B-096" not in visible


def test_claude_prompt_visible_text_comes_from_teaser_stdout_not_hidden_context() -> None:
    payload = host_surface_runtime.claude_prompt_payload(
        additional_context="Odylith anchor B-096: primary target src/main.py.\n\nOdylith can already see governed truth taking shape here.",
        system_message="Odylith can already see governed truth taking shape here.",
    )

    visible = host_surface_runtime.chat_visible_text(
        payload,
        host_family="claude",
        turn_phase="prompt_submit",
        plain_stdout="Odylith can already see governed truth taking shape here.",
    )

    assert visible == "Odylith can already see governed truth taking shape here."
    assert "systemMessage" not in payload
    assert "Odylith anchor B-096" not in visible


def test_checkpoint_visible_text_includes_observation_and_proposal_but_keeps_assist_hidden() -> None:
    developer_context = (
        "**Odylith Observation:** The signal is real.\n\n"
        "-----\nOdylith Proposal: Keep this grounded.\n-----\n\n"
        "**Odylith Assist:** kept this grounded."
    )
    system_message = "**Odylith Observation:** The signal is real.\n\n-----\nOdylith Proposal: Keep this grounded.\n-----"
    codex_payload = host_surface_runtime.codex_post_tool_payload(
        developer_context=developer_context,
        system_message=system_message,
    )
    claude_payload = host_surface_runtime.claude_post_tool_payload(
        developer_context=developer_context,
        system_message=system_message,
    )

    codex_visible = host_surface_runtime.chat_visible_text(
        codex_payload,
        host_family="codex",
        turn_phase="post_bash_checkpoint",
    )
    claude_visible = host_surface_runtime.chat_visible_text(
        claude_payload,
        host_family="claude",
        turn_phase="post_edit_checkpoint",
    )

    assert codex_visible == claude_visible
    assert "**Odylith Observation:** The signal is real." in codex_visible
    assert "Odylith Proposal:" in codex_visible
    assert "Odylith Assist:" not in codex_visible
    assert "Odylith visible delivery fallback:" in codex_payload["hookSpecificOutput"]["additionalContext"]
    assert "Odylith Assist:" in codex_payload["hookSpecificOutput"]["additionalContext"]
    assert "Odylith Assist:" in claude_payload["additionalContext"]


def test_stop_visible_text_can_include_assist_closeout() -> None:
    payload = host_surface_runtime.stop_payload(
        system_message=(
            "**Odylith Observation:** The signal is real.\n\n"
            "**Odylith Assist:** kept this grounded."
        )
    )

    visible = host_surface_runtime.chat_visible_text(
        payload,
        host_family="codex",
        turn_phase="stop_summary",
    )

    assert "**Odylith Observation:** The signal is real." in visible
    assert "**Odylith Assist:** kept this grounded." in visible


def test_ambient_signal_is_visible_when_it_wins_the_live_slot() -> None:
    payload = host_surface_runtime.codex_post_tool_payload(
        developer_context="**Odylith Insight:** this stayed smaller than it first looked.",
        system_message="**Odylith Insight:** this stayed smaller than it first looked.",
    )

    visible = host_surface_runtime.chat_visible_text(
        payload,
        host_family="codex",
        turn_phase="post_bash_checkpoint",
    )

    assert visible == "**Odylith Insight:** this stayed smaller than it first looked."


def test_compose_checkpoint_system_message_prefers_live_intervention_over_success_status() -> None:
    message = host_surface_runtime.compose_checkpoint_system_message(
        live_intervention="**Odylith Observation:** The signal is real.",
        governance_status="Odylith governance refresh completed.",
    )

    assert message == "**Odylith Observation:** The signal is real."


def test_compose_checkpoint_system_message_keeps_failure_status_with_live_intervention() -> None:
    message = host_surface_runtime.compose_checkpoint_system_message(
        live_intervention="**Odylith Observation:** The signal is real.",
        governance_status="Odylith governance refresh failed after editing foo.md: exit code 2",
    )

    assert message.startswith("**Odylith Observation:** The signal is real.")
    assert "failed after editing foo.md" in message
