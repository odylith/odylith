from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

from odylith.runtime.intervention_engine import delivery_ledger
from odylith.runtime.intervention_engine import surface_runtime
from odylith.runtime.surfaces import claude_host_prompt_context
from odylith.runtime.surfaces import claude_host_prompt_teaser


def test_render_prompt_context_resolves_first_anchor_via_override() -> None:
    payload = {
        "target_resolution": {
            "candidate_targets": [
                {"path": "odylith/radar/source/queued/B-083.md"},
            ]
        }
    }
    rendered = claude_host_prompt_context.render_prompt_context(
        prompt="Continue work on B-083 and CB-104",
        context_output_override="Anchor resolved.\n" + json.dumps(payload),
        conversation_bundle_override={},
    )

    assert "Odylith anchor B-083" in rendered
    assert "primary target odylith/radar/source/queued/B-083.md" in rendered


def test_render_prompt_context_returns_empty_when_no_anchor_present() -> None:
    rendered = claude_host_prompt_context.render_prompt_context(
        prompt="No anchor in this prompt.",
        context_output_override="anything",
    )
    assert rendered == ""


def test_render_prompt_context_can_surface_a_teaser_without_anchor() -> None:
    rendered = claude_host_prompt_context.render_prompt_context(
        prompt="Design a conversation observation engine with governed proposal flow.",
        intervention_bundle_override={
            "candidate": {
                "stage": "teaser",
                "teaser_text": "Odylith sees enough signal here to capture it.",
            }
        },
    )

    assert rendered == surface_runtime.wrap_live_text("Odylith sees enough signal here to capture it.")


def test_claude_prompt_system_message_hard_fails_visible_for_zero_signals(tmp_path: Path) -> None:
    prompt = "ZERO signals in my chat. Odylith interventions NEED to be visible."

    rendered = claude_host_prompt_context.render_prompt_system_message(
        repo_root=tmp_path,
        prompt=prompt,
        session_id="claude-zero-signals",
    )
    bundle = claude_host_prompt_context._prompt_conversation_bundle(
        repo_root=tmp_path,
        prompt=prompt,
        session_id="claude-zero-signals",
    )
    observation = dict(bundle["observation"])

    assert rendered.startswith(
        "---\n\n**Odylith Observation:** Claude has Odylith activity, but no Odylith note has reached this chat yet."
    )
    assert observation["context_packet_summary"]["packet_state"] == "visibility_recovery"
    assert observation["execution_engine_summary"]["execution_engine_next_move"] == "recover.current_blocker"
    assert observation["memory_summary"]["visibility_complaint"] is True
    assert observation["tribunal_summary"]["source"] == "intervention_alignment_context"


def test_claude_prompt_system_message_replays_pending_chat_block(tmp_path: Path) -> None:
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending prompt replay.",
        session_id="claude-prompt-replay",
        host_family="claude",
        intervention_key="claude-prompt-replay-key",
        turn_phase="post_edit_checkpoint",
        display_markdown="**Odylith Observation:** Claude prompt must carry this pending block.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    rendered = claude_host_prompt_context.render_prompt_system_message(
        repo_root=tmp_path,
        prompt="Do we still have a visible block pending?",
        session_id="claude-prompt-replay",
    )

    assert rendered == (
        "---\n\n**Odylith Observation:** Claude prompt must carry this pending block.\n\n---"
    )


def test_claude_prompt_system_message_suppresses_help_fast_path_replay(tmp_path: Path) -> None:
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending prompt replay.",
        session_id="claude-help-fast-path",
        host_family="claude",
        intervention_key="claude-help-fast-path-replay",
        turn_phase="post_edit_checkpoint",
        display_markdown="**Odylith Observation:** Claude prompt must not carry this into help.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    rendered = claude_host_prompt_context.render_prompt_system_message(
        repo_root=tmp_path,
        prompt="Odylith, help.",
        session_id="claude-help-fast-path",
    )

    assert rendered == ""


def test_claude_prompt_system_message_prefers_pending_ambient_history_over_observation(tmp_path: Path) -> None:
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending Claude observation replay.",
        session_id="claude-prompt-ambient",
        host_family="claude",
        intervention_key="claude-prompt-observation",
        turn_phase="post_edit_checkpoint",
        display_markdown="**Odylith Observation:** Claude prompt should not hide the stronger ambient beat.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="ambient_signal",
        summary="Pending Claude history replay.",
        session_id="claude-prompt-ambient",
        host_family="claude",
        intervention_key="claude-prompt-history",
        turn_phase="post_edit_checkpoint",
        display_markdown="**Odylith History:** Claude prompt should surface this branded ambient beat first.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    rendered = claude_host_prompt_context.render_prompt_system_message(
        repo_root=tmp_path,
        prompt="Do we still have a visible block pending?",
        session_id="claude-prompt-ambient",
    )

    assert rendered == (
        "---\n\n"
        "**Odylith History:** Claude prompt should surface this branded ambient beat first.\n"
        "\n"
        "**Odylith Observation:** Claude prompt should not hide the stronger ambient beat.\n"
        "\n---"
    )


def test_render_prompt_context_falls_back_to_relevant_docs_when_no_targets() -> None:
    payload = {"relevant_docs": ["odylith/CLAUDE.md"]}
    rendered = claude_host_prompt_context.render_prompt_context(
        prompt="Resolve CB-104",
        context_output_override=json.dumps(payload),
        conversation_bundle_override={},
    )
    assert "Odylith anchor CB-104" in rendered
    assert "relevant doc odylith/CLAUDE.md" in rendered


def test_main_runs_context_command_for_first_anchor(monkeypatch, tmp_path: Path, capsys) -> None:
    project = tmp_path / "repo"
    launcher = project / ".odylith" / "bin"
    launcher.mkdir(parents=True)
    (launcher / "odylith").write_text("#!/bin/sh\n", encoding="utf-8")

    captured: list[list[str]] = []

    def _fake_run_odylith(*, project_dir, args, timeout=20):
        captured.append(list(args))
        payload = {"target_resolution": {"candidate_targets": [{"path": "src/foo.py"}]}}
        return subprocess.CompletedProcess(
            args,
            0,
            stdout="Context resolved.\n" + json.dumps(payload),
            stderr="",
        )

    monkeypatch.setattr(
        claude_host_prompt_context.claude_host_shared,
        "run_odylith",
        _fake_run_odylith,
    )
    monkeypatch.setattr(
        claude_host_prompt_context.conversation_surface,
        "build_conversation_bundle",
        lambda **_: {},
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"prompt": "Continue work on B-088"})),
    )

    exit_code = claude_host_prompt_context.main(["--repo-root", str(project)])

    assert exit_code == 0
    assert captured == [["context", "--repo-root", ".", "B-088"]]
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "Odylith anchor B-088: primary target src/foo.py." in payload["hookSpecificOutput"]["additionalContext"]
    assert "systemMessage" not in payload


def test_main_prints_nothing_for_help_fast_path_even_with_pending_replay(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending prompt replay.",
        session_id="claude-help-main",
        host_family="claude",
        intervention_key="claude-help-main-replay",
        turn_phase="post_edit_checkpoint",
        display_markdown="**Odylith Observation:** stale replay",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"prompt": "Odylith, help.", "session_id": "claude-help-main"})),
    )

    exit_code = claude_host_prompt_context.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert capsys.readouterr().out == ""


def test_main_keeps_teaser_in_discreet_prompt_context_when_signal_is_real(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    project = tmp_path / "repo"
    project.mkdir()

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"prompt": "Continue work on B-088"})),
    )
    monkeypatch.setattr(
        claude_host_prompt_context.conversation_surface,
        "build_conversation_bundle",
        lambda **_: {
            "intervention_bundle": {
                "candidate": {
                    "stage": "teaser",
                    "teaser_text": (
                        "Odylith Observation: Casebook needs real failure evidence before it writes. "
            "Why it matters: The prompt still contains a placeholder; ask for the actual command output or frame the item as Radar debt."
                    ),
                }
            }
        },
    )

    exit_code = claude_host_prompt_context.main(["--repo-root", str(project)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert payload["hookSpecificOutput"]["additionalContext"].startswith("Odylith visible delivery recovery:")
    assert "Odylith Observation:" in payload["hookSpecificOutput"]["additionalContext"]
    assert "systemMessage" not in payload


def test_prompt_teaser_main_prints_plain_best_effort_teaser_text(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    project = tmp_path / "repo"
    project.mkdir()

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"prompt": "Continue work on B-088"})),
    )
    monkeypatch.setattr(
        claude_host_prompt_context.conversation_surface,
        "build_conversation_bundle",
        lambda **_: {
            "intervention_bundle": {
                "candidate": {
                    "stage": "teaser",
                    "teaser_text": (
                        "Odylith Observation: Casebook needs real failure evidence before it writes. "
            "Why it matters: The prompt still contains a placeholder; ask for the actual command output or frame the item as Radar debt."
                    ),
                }
            }
        },
    )

    exit_code = claude_host_prompt_teaser.main(["--repo-root", str(project)])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert output.startswith(f"{surface_runtime.LIVE_BOUNDARY}\n\nOdylith Observation:")
    assert "**Odylith Assist:**" not in output
    assert not output.lstrip().startswith("{")


def test_main_confirms_visible_prompt_replay_from_last_assistant_message(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending Claude prompt replay awaiting transcript proof.",
        session_id="claude-confirm-prompt",
        host_family="claude",
        intervention_key="claude-confirm-prompt-key",
        turn_phase="post_edit_checkpoint",
        display_markdown="---\n**Odylith Observation:** Claude prompt already rendered this block.\n---",
        delivery_channel="assistant_visible_fallback",
        delivery_status="assistant_render_required",
        render_surface="claude_post_tool_use",
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "prompt": "Continue with the next slice.",
                    "session_id": "claude-confirm-prompt",
                    "last_assistant_message": (
                        "Done.\n\n---\n**Odylith Observation:** Claude prompt already rendered this block.\n---"
                    ),
                }
            )
        ),
    )
    monkeypatch.setattr(
        claude_host_prompt_context.conversation_surface,
        "build_conversation_bundle",
        lambda **_: {},
    )

    exit_code = claude_host_prompt_context.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert capsys.readouterr().out == ""
    snapshot = delivery_ledger.delivery_snapshot(
        repo_root=tmp_path,
        host_family="claude",
        session_id="claude-confirm-prompt",
    )
    assert snapshot["chat_confirmed_event_count"] == 1
    assert snapshot["unconfirmed_event_count"] == 0
