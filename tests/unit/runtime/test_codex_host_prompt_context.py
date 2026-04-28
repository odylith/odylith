from __future__ import annotations

import io
import json
from pathlib import Path

from odylith.runtime.intervention_engine import delivery_ledger
from odylith.runtime.intervention_engine import surface_runtime
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.surfaces import codex_host_prompt_context


def test_render_codex_prompt_context_uses_first_explicit_anchor(monkeypatch) -> None:
    seen: list[str] = []

    def _fake_context_summary(*, project_dir: str, ref: str, payload_override=None) -> str:
        del project_dir, payload_override
        seen.append(ref)
        return f"Odylith anchor {ref}: primary target src/example.py."

    monkeypatch.setattr(codex_host_prompt_context.codex_host_shared, "context_summary", _fake_context_summary)

    rendered = codex_host_prompt_context.render_codex_prompt_context(
        prompt="Check B-088 against CB-102 before touching D-030.",
        conversation_bundle_override={},
    )

    assert rendered == "Odylith anchor B-088: primary target src/example.py."
    assert seen == ["B-088"]


def test_render_codex_prompt_context_returns_empty_without_anchor() -> None:
    assert codex_host_prompt_context.render_codex_prompt_context(prompt="Explain the change.") == ""


def test_render_codex_prompt_context_returns_empty_for_show_me_fast_path() -> None:
    assert codex_host_prompt_context.render_codex_prompt_context(
        prompt="odylith, show me what you can do"
    ) == ""


def test_render_codex_prompt_context_can_surface_a_teaser_without_anchor() -> None:
    rendered = codex_host_prompt_context.render_codex_prompt_context(
        prompt="Design a conversation observation engine with governed proposal flow.",
        intervention_bundle_override={
            "candidate": {
                "stage": "teaser",
                "teaser_text": "Odylith sees enough signal here to capture it.",
            }
        },
    )

    assert rendered == surface_runtime.wrap_live_text("Odylith sees enough signal here to capture it.")


def test_codex_prompt_system_message_hard_fails_visible_for_zero_signals(tmp_path: Path) -> None:
    prompt = "ZERO signals in my chat. Odylith interventions NEED to be visible."

    rendered = codex_host_prompt_context.render_codex_prompt_system_message(
        repo_root=str(tmp_path),
        prompt=prompt,
        session_id="codex-zero-signals",
    )
    bundle = codex_host_prompt_context._prompt_conversation_bundle(
        repo_root=str(tmp_path),
        prompt=prompt,
        session_id="codex-zero-signals",
    )
    observation = dict(bundle["observation"])

    assert rendered.startswith("---\n\n**Odylith Observation:** This chat still has no visible Odylith moment")
    assert observation["context_packet_summary"]["packet_state"] == "visibility_recovery"
    assert observation["execution_engine_summary"]["execution_engine_next_move"] == "recover.current_blocker"
    assert observation["memory_summary"]["visibility_complaint"] is True
    assert observation["tribunal_summary"]["source"] == "intervention_alignment_context"


def test_codex_prompt_system_message_replays_pending_chat_block(tmp_path: Path) -> None:
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending prompt replay.",
        session_id="codex-prompt-replay",
        host_family="codex",
        intervention_key="codex-prompt-replay-key",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** Prompt must carry this pending block.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    rendered = codex_host_prompt_context.render_codex_prompt_system_message(
        repo_root=str(tmp_path),
        prompt="Do we still have a visible block pending?",
        session_id="codex-prompt-replay",
    )

    assert rendered == (
        "---\n\n**Odylith Observation:** Prompt must carry this pending block.\n\n---\n\n"
        "**Odylith Assist:** kept Odylith visible in this chat so the brand promise is something the user can see."
    )


def test_codex_prompt_system_message_suppresses_help_fast_path_replay(tmp_path: Path) -> None:
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending prompt replay.",
        session_id="codex-help-fast-path",
        host_family="codex",
        intervention_key="codex-help-fast-path-replay",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** Prompt must not carry this into help.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    rendered = codex_host_prompt_context.render_codex_prompt_system_message(
        repo_root=str(tmp_path),
        prompt="Odylith, help.",
        session_id="codex-help-fast-path",
    )

    assert rendered == ""


def test_codex_prompt_system_message_prefers_pending_ambient_risk_over_observation(tmp_path: Path) -> None:
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending observation replay.",
        session_id="codex-prompt-ambient",
        host_family="codex",
        intervention_key="codex-prompt-observation",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** Prompt should not hide the stronger ambient beat.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="ambient_signal",
        summary="Pending prompt risk replay.",
        session_id="codex-prompt-ambient",
        host_family="codex",
        intervention_key="codex-prompt-risk",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Risks:** Prompt should surface this branded ambient beat first.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    rendered = codex_host_prompt_context.render_codex_prompt_system_message(
        repo_root=str(tmp_path),
        prompt="Do we still have a visible block pending?",
        session_id="codex-prompt-ambient",
    )

    assert rendered == (
        "---\n\n"
        "**Odylith Risks:** Prompt should surface this branded ambient beat first.\n"
        "\n"
        "**Odylith Observation:** Prompt should not hide the stronger ambient beat.\n"
        "\n---\n\n"
        "**Odylith Assist:** kept Odylith visible in this chat so the brand promise is something the user can see."
    )


def test_main_writes_user_prompt_hook_json(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"prompt": "Please inspect B-088 next."})),
    )
    monkeypatch.setattr(
        codex_host_prompt_context.codex_host_shared,
        "context_summary",
        lambda **_: "Odylith anchor B-088: primary target src/odylith/cli.py.",
    )
    monkeypatch.setattr(
        codex_host_prompt_context.conversation_surface,
        "build_conversation_bundle",
        lambda **_: {},
    )

    exit_code = codex_host_prompt_context.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "src/odylith/cli.py" in payload["hookSpecificOutput"]["additionalContext"]
    assert payload["systemMessage"] == (
        "**Odylith Assist:** kept Odylith visible in this chat so the brand promise is something the user can see."
    )


def test_main_emits_show_me_route_lock_without_running_prompt_observation(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    def _unexpected_bundle(**_: object) -> dict[str, object]:
        raise AssertionError("show-me route lock should bypass prompt observation")

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "prompt": "odylith, show me what you can do",
                    "session_id": "codex-show-main",
                }
            )
        ),
    )
    monkeypatch.setattr(
        codex_host_prompt_context.conversation_surface,
        "build_conversation_bundle",
        _unexpected_bundle,
    )

    exit_code = codex_host_prompt_context.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    additional_context = payload["hookSpecificOutput"]["additionalContext"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "Odylith Codex show-me first-match route lock" in additional_context
    assert "must not write a hand-authored demonstration summary" in additional_context
    assert "install posture" in additional_context
    assert "dirty paths" in additional_context
    assert "impact packets" in additional_context
    assert "module counts" in additional_context
    assert "tmp clone noise" in additional_context
    assert "spawn policy" in additional_context
    assert "`./.odylith/bin/odylith show --repo-root .`" in additional_context
    assert "`odylith show --repo-root .`" in additional_context
    assert "Return that stdout directly" in additional_context
    assert "systemMessage" not in payload


def test_main_emits_help_route_lock_without_pending_replay(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending prompt replay.",
        session_id="codex-help-main",
        host_family="codex",
        intervention_key="codex-help-main-replay",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** stale replay",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"prompt": "Odylith, help.", "session_id": "codex-help-main"})),
    )

    exit_code = codex_host_prompt_context.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    additional_context = payload["hookSpecificOutput"]["additionalContext"]
    assert "Odylith Codex help first-match route lock" in additional_context
    assert "host capability summary" in additional_context
    assert "`./.odylith/bin/odylith --help`" in additional_context
    assert "`odylith --help`" in additional_context
    assert "stale replay" not in additional_context
    assert "systemMessage" not in payload


def test_main_surfaces_visible_teaser_in_system_message(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"prompt": "Design a conversation observation engine with governed proposal flow."})),
    )
    monkeypatch.setattr(
        codex_host_prompt_context.conversation_surface,
        "build_conversation_bundle",
        lambda **_: {
            "intervention_bundle": {
                "candidate": {
                    "stage": "teaser",
                    "teaser_text": (
                        "Odylith Observation: This turn is already framing a governed proposal. "
                        "Why it matters: Capture the exact governed change while the request is still current."
                    ),
                }
            }
        },
    )

    exit_code = codex_host_prompt_context.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert payload["hookSpecificOutput"]["additionalContext"].startswith("Odylith visible delivery fallback:")
    assert "Odylith Observation:" in payload["hookSpecificOutput"]["additionalContext"]
    assert payload["systemMessage"].startswith(f"{surface_runtime.LIVE_BOUNDARY}\n\nOdylith Observation:")
    assert "\n---\n\n**Odylith Assist:** kept Odylith visible in this chat" in payload["systemMessage"]
    assert payload["systemMessage"].rsplit("\n", maxsplit=1)[-1].startswith("**Odylith Assist:**")


def test_main_records_prompt_events_on_stable_thread_id_not_turn_id(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setenv("CODEX_THREAD_ID", "codex-thread-123")
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "prompt": "Design a conversation observation engine with governed proposal flow.",
                    "turn_id": "turn-9",
                }
            )
        ),
    )
    monkeypatch.setattr(
        codex_host_prompt_context.conversation_surface,
        "build_conversation_bundle",
        lambda **_: {
            "intervention_bundle": {
                "candidate": {
                    "stage": "teaser",
                    "teaser_text": "Odylith Observation: Keep the visible Odylith moment on the stable chat id.",
                }
            }
        },
    )

    exit_code = codex_host_prompt_context.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    json.loads(capsys.readouterr().out)
    thread_events = stream_state.load_recent_intervention_events(
        repo_root=tmp_path,
        session_id="codex-thread-123",
    )
    turn_events = stream_state.load_recent_intervention_events(
        repo_root=tmp_path,
        session_id="turn-9",
    )

    assert thread_events
    assert {row["session_id"] for row in thread_events} == {"codex-thread-123"}
    assert turn_events == []


def test_main_confirms_visible_prompt_replay_from_last_assistant_message(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending prompt replay awaiting transcript proof.",
        session_id="codex-confirm-prompt",
        host_family="codex",
        intervention_key="codex-confirm-prompt-key",
        turn_phase="post_bash_checkpoint",
        display_markdown="---\n**Odylith Observation:** Codex prompt already rendered this block.\n---",
        delivery_channel="assistant_visible_fallback",
        delivery_status="assistant_render_required",
        render_surface="codex_post_tool_use",
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "prompt": "Continue with the next slice.",
                    "session_id": "codex-confirm-prompt",
                    "last_assistant_message": (
                        "Done.\n\n---\n**Odylith Observation:** Codex prompt already rendered this block.\n---"
                    ),
                }
            )
        ),
    )
    monkeypatch.setattr(
        codex_host_prompt_context.conversation_surface,
        "build_conversation_bundle",
        lambda **_: {},
    )

    exit_code = codex_host_prompt_context.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["systemMessage"] == (
        "**Odylith Assist:** kept Odylith visible in this chat so the brand promise is something the user can see."
    )
    snapshot = delivery_ledger.delivery_snapshot(
        repo_root=tmp_path,
        host_family="codex",
        session_id="codex-confirm-prompt",
    )
    assert snapshot["chat_confirmed_event_count"] == 1
    assert snapshot["unconfirmed_event_count"] == 0
