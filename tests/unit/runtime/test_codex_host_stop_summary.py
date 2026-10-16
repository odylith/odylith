from __future__ import annotations

import io
import json
from pathlib import Path

from odylith.runtime.intervention_engine import surface_runtime
from odylith.runtime.surfaces import codex_host_stop_summary
from odylith.runtime.surfaces import host_dirty_checkpoint


_CLI_HELP_OUTPUT = """usage: odylith [-h] {start,context,query,sync,codex} ...

Odylith install, grounding, sync, runtime, and repair tooling.

positional arguments:
  {start,context,query,sync,codex}
    start               Choose the safest first Odylith turn-start path.

options:
  -h, --help            show this help message and exit
"""


def test_stop_retains_complete_meaningful_sentence_with_actual_session(monkeypatch, tmp_path: Path) -> None:
    summary = ("Implemented complete source custody and retained every final verification clause "
               "across the governed runtime boundary with explicit durable session identity; "
               "the original authority and recovery evidence remain intact for B-088.")
    assert len(summary) > 180
    session = "codex-actual-native-session"
    confirmations = []
    monkeypatch.setattr(codex_host_stop_summary.codex_host_shared, "load_payload",
                        lambda: {"session_id": session, "last_assistant_message": summary + " More details follow."})
    monkeypatch.setattr(codex_host_stop_summary.host_surface_runtime, "confirm_assistant_chat_delivery",
                        lambda **kwargs: confirmations.append(kwargs))
    monkeypatch.setattr(codex_host_stop_summary.codex_host_shared, "run_odylith",
                        lambda **kwargs: (_ for _ in ()).throw(AssertionError("Stop must not dispatch canonical commands")))

    assert codex_host_stop_summary.main(["--repo-root", str(tmp_path)]) == 0
    rows = host_dirty_checkpoint.read_compass_events(repo_root=tmp_path)
    assert len(rows) == 1
    event = rows[0]["event"]
    assert event["summary"] == summary
    assert event["session_id"] == rows[0]["session_id"] == session
    assert event["host_family"] == "codex"
    assert event["author"] == event["source"] == "assistant"
    assert event["kind"] == "implementation"
    assert event["workstreams"] == ["B-088"]
    assert event["ts_iso"]
    assert event["transaction_id"] == "host-event-" + rows[0]["id"]
    assert host_dirty_checkpoint.read_compass_events(repo_root=tmp_path) == rows
    assert confirmations[0]["defer"] is True and confirmations[0]["session_id"] == session
    assert not (tmp_path / "odylith").exists()


def test_stop_ignores_non_meaningful_messages(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(codex_host_stop_summary.codex_host_shared, "load_payload",
                        lambda: {"session_id": "quiet-session", "last_assistant_message": "Would you like a follow-up?"})
    monkeypatch.setattr(host_dirty_checkpoint, "capture_stop_summary",
                        lambda **_: (_ for _ in ()).throw(AssertionError("should not capture")))
    assert codex_host_stop_summary.main(["--repo-root", str(tmp_path)]) == 0
    assert host_dirty_checkpoint.read_compass_events(repo_root=tmp_path) == []


def test_stop_intervention_bundle_uses_recent_prompt_excerpt_not_intervention_summary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    codex_host_stop_summary.intervention_surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="capture_proposed",
        summary="Odylith Proposal pending.",
        session_id="stop-1",
        host_family="codex",
        intervention_key="iv-stop-1",
        turn_phase="post_edit_checkpoint",
        prompt_excerpt="Design the conversation governance engine for this session.",
        display_markdown="**Odylith Proposal**",
    )
    seen: dict[str, object] = {}

    def _fake_compose_host_bundle(**kwargs):  # noqa: ANN001
        seen["repo_root"] = kwargs["repo_root"]
        seen["prompt"] = kwargs["prompt_excerpt"]
        seen["candidate_paths"] = list(kwargs["changed_paths"])
        seen["session_id"] = kwargs["session_id"]
        return {
            "intervention_bundle": {"ok": True},
            "closeout_bundle": {"markdown_text": "**Odylith Assist:** B-096 stayed tied to the refreshed intervention contract."},
        }

    monkeypatch.setattr(
        codex_host_stop_summary.host_surface_runtime,
        "compose_host_conversation_bundle",
        _fake_compose_host_bundle,
    )

    bundle = codex_host_stop_summary._stop_intervention_bundle(
        repo_root=str(tmp_path),
        message=(
            "Implemented the stop-summary memory regression fix for B-096 and "
            "validated the focused runtime hook tests."
        ),
        session_id="stop-1",
    )

    assert bundle["intervention_bundle"] == {"ok": True}
    assert seen["prompt"] == (
        "Design the conversation governance engine for this session."
    )
    assert seen["session_id"] == "stop-1"


def test_stop_intervention_bundle_recovers_recent_changed_paths(monkeypatch, tmp_path: Path) -> None:
    codex_host_stop_summary.intervention_surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Observation rendered.",
        session_id="stop-2",
        host_family="codex",
        intervention_key="iv-stop-2",
        turn_phase="post_bash_checkpoint",
        prompt_excerpt="Capture the governed truth from this engine session.",
        artifacts=["src/odylith/runtime/intervention_engine/engine.py"],
        display_markdown="**Odylith Observation:**",
    )
    seen: dict[str, object] = {}

    def _fake_compose_host_bundle(**kwargs):  # noqa: ANN001
        seen["candidate_paths"] = list(kwargs["changed_paths"])
        return {"intervention_bundle": {"ok": True}, "closeout_bundle": {}}

    monkeypatch.setattr(
        codex_host_stop_summary.host_surface_runtime,
        "compose_host_conversation_bundle",
        _fake_compose_host_bundle,
    )

    codex_host_stop_summary._stop_intervention_bundle(
        repo_root=str(tmp_path),
        message=(
            "Implemented the stop-summary changed-path recovery fix for B-096 and "
            "validated the focused runtime hook tests."
        ),
        session_id="stop-2",
    )

    assert seen["candidate_paths"] == ["src/odylith/runtime/intervention_engine/engine.py"]


def test_stop_intervention_bundle_can_recover_prompt_when_last_message_is_short(
    monkeypatch,
    tmp_path: Path,
) -> None:
    codex_host_stop_summary.intervention_surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_teaser",
        summary="Observation forming.",
        session_id="stop-short-1",
        host_family="codex",
        intervention_key="iv-stop-short-1",
        turn_phase="prompt_submit",
        prompt_excerpt=(
            "I still do not see any Odylith ambient highlights or interventions "
            "visible in chat."
        ),
        display_plain=(
            "Odylith Observation: Casebook needs real failure evidence before it writes. "
            "Why it matters: The prompt still contains a placeholder; ask for the actual command output or frame the item as Radar debt."
        ),
    )
    seen: dict[str, object] = {}

    def _fake_compose_host_bundle(**kwargs):  # noqa: ANN001
        seen["prompt"] = kwargs["prompt_excerpt"]
        seen["assistant_summary"] = kwargs["assistant_summary"]
        return {
            "intervention_bundle": {},
            "closeout_bundle": {
                "markdown_text": "**Odylith Assist:** kept the UX signal visible.",
                "plain_text": "Odylith Assist: kept the UX signal visible.",
            },
        }

    monkeypatch.setattr(
        codex_host_stop_summary.host_surface_runtime,
        "compose_host_conversation_bundle",
        _fake_compose_host_bundle,
    )

    bundle = codex_host_stop_summary._stop_intervention_bundle(
        repo_root=str(tmp_path),
        message="Understood.",
        session_id="stop-short-1",
    )

    assert bundle["closeout_bundle"]["markdown_text"].startswith("**Odylith Assist:**")
    assert "ambient highlights" in str(seen["prompt"])
    assert seen["assistant_summary"] == ""


def test_render_codex_stop_summary_combines_observation_and_assist() -> None:
    rendered = codex_host_stop_summary.render_codex_stop_summary(
        ".",
        message="Implemented the engine slice.",
        session_id="stop-3",
        conversation_bundle_override={
            "intervention_bundle": {
                "candidate": {
                    "stage": "card",
                    "suppressed_reason": "",
                    "markdown_text": "**Odylith Observation:** The signal is real.",
                    "plain_text": "Odylith Observation: The signal is real.",
                },
                "proposal": {"eligible": False, "suppressed_reason": ""},
            },
            "closeout_bundle": {
                "markdown_text": "**Odylith Assist:** B-096 stayed tied to the refreshed intervention contract.",
                "plain_text": "Odylith Assist: B-096 stayed tied to the refreshed intervention contract.",
            },
        },
    )

    assert rendered == (
        "---\n\n"
        "**Odylith Observation:** The signal is real.\n"
        "\n---\n\n"
        "**Odylith Assist:** B-096 stayed tied to the refreshed intervention contract."
    )


def test_render_codex_stop_summary_replays_unseen_live_beat_through_stop_lane(tmp_path: Path) -> None:
    codex_host_stop_summary.intervention_surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Observation rendered.",
        session_id="stop-replay-1",
        host_family="codex",
        intervention_key="iv-stop-replay-1",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** This beat was computed earlier but still needs a visible lane.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    rendered = codex_host_stop_summary.render_codex_stop_summary(
        str(tmp_path),
        message="Implemented the engine slice.",
        session_id="stop-replay-1",
        conversation_bundle_override={
            "intervention_bundle": {
                "candidate": {
                    "stage": "silent",
                    "suppressed_reason": "",
                },
                "proposal": {"eligible": False, "suppressed_reason": ""},
            },
            "closeout_bundle": {
                "markdown_text": "**Odylith Assist:** B-096 stayed tied to the refreshed intervention contract.",
                "plain_text": "Odylith Assist: B-096 stayed tied to the refreshed intervention contract.",
            },
        },
    )

    assert rendered == (
        "---\n\n"
        "**Odylith Observation:** This beat was computed earlier but still needs a visible lane.\n"
        "\n---\n\n"
        "**Odylith Assist:** B-096 stayed tied to the refreshed intervention contract."
    )


def test_render_codex_stop_summary_replaces_teaser_with_unseen_live_beat(tmp_path: Path) -> None:
    codex_host_stop_summary.intervention_surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Observation rendered.",
        session_id="stop-replay-teaser",
        host_family="codex",
        intervention_key="iv-stop-replay-teaser",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** The earlier card still needs chat visibility.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    rendered = codex_host_stop_summary.render_codex_stop_summary(
        str(tmp_path),
        message="Implemented the engine slice.",
        session_id="stop-replay-teaser",
        conversation_bundle_override={
            "intervention_bundle": {
                "candidate": {
                    "stage": "teaser",
                    "suppressed_reason": "",
                    "teaser_text": "Odylith Observation: the Odylith note still needs to reach chat.",
                },
                "proposal": {"eligible": False, "suppressed_reason": ""},
            },
            "closeout_bundle": {
                "markdown_text": "**Odylith Assist:** B-096 stayed tied to the refreshed intervention contract.",
                "plain_text": "Odylith Assist: B-096 stayed tied to the refreshed intervention contract.",
            },
        },
    )

    assert "**Odylith Observation:** The earlier card still needs chat visibility." in rendered
    assert "Odylith is tracking this signal" not in rendered


def test_main_stays_silent_without_pending_stop_replay(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        codex_host_stop_summary.codex_host_shared,
        "load_payload",
        lambda: {
            "last_assistant_message": (
                "Implemented the stop-summary visible surface fix for B-096 and "
                "validated the focused runtime hook tests."
            ),
            "session_id": "stop-main",
        },
    )
    monkeypatch.setattr(
        codex_host_stop_summary,
        "render_codex_stop_summary",
        lambda *args, **kwargs: "**Odylith Assist:** B-096 stayed tied to the refreshed intervention contract.",
    )
    monkeypatch.setattr(
        codex_host_stop_summary,
        "_stop_intervention_bundle",
        lambda **kwargs: {},
    )
    buffer = io.StringIO()
    monkeypatch.setattr("sys.stdout", buffer)

    exit_code = codex_host_stop_summary.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert buffer.getvalue() == ""


def test_main_retains_dirty_checkpoints_without_synchronous_settlement(monkeypatch, tmp_path: Path, capsys) -> None:
    event_id = host_dirty_checkpoint.record_dirty_event(
        repo_root=tmp_path, host_family="codex", session_id="stop-status", source="test",
        governed_paths=["odylith/casebook/bugs/example.md"],
    )
    monkeypatch.setattr(codex_host_stop_summary.codex_host_shared, "load_payload",
                        lambda: {"last_assistant_message": "Completed the requested change.", "session_id": "stop-status"})
    monkeypatch.setattr(codex_host_stop_summary.codex_host_shared, "run_odylith",
                        lambda **kwargs: (_ for _ in ()).throw(AssertionError("Stop must not dispatch canonical work")))
    assert codex_host_stop_summary.main(["--repo-root", str(tmp_path)]) == 0
    assert [row["id"] for row in host_dirty_checkpoint.read_dirty_events(repo_root=tmp_path)] == [event_id]
    assert capsys.readouterr().out == ""


def test_main_reports_summary_capture_failure_without_claiming_saved_memory(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(codex_host_stop_summary.codex_host_shared, "load_payload", lambda: {
        "last_assistant_message": "Implemented the Stop summary capture failure regression and validated the focused tests.",
        "session_id": "stop-failure",
    })
    monkeypatch.setattr(host_dirty_checkpoint, "capture_stop_summary", lambda **kwargs: (
        _ for _ in ()).throw(host_dirty_checkpoint.HostDirtyCheckpointError("fsync refused")))
    monkeypatch.setattr(codex_host_stop_summary.host_surface_runtime, "confirm_assistant_chat_delivery", lambda **kwargs: [])
    assert codex_host_stop_summary.main(["--repo-root", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"systemMessage": "Odylith could not save this turn's summary."}
    assert host_dirty_checkpoint.read_compass_events(repo_root=tmp_path) == []


def test_main_keeps_pending_chat_blocks_out_of_stop_output(
    monkeypatch,
    tmp_path: Path,
) -> None:
    codex_host_stop_summary.intervention_surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending stop replay.",
        session_id="stop-main-replay",
        host_family="codex",
        intervention_key="stop-main-replay-key",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** Stop must replay this before Assist.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )
    monkeypatch.setattr(
        codex_host_stop_summary.codex_host_shared,
        "load_payload",
        lambda: {
            "last_assistant_message": (
                "Implemented the stop-summary visible surface fix for B-096 and "
                "validated the focused runtime hook tests."
            ),
            "session_id": "stop-main-replay",
        },
    )
    monkeypatch.setattr(
        host_dirty_checkpoint,
        "capture_stop_summary",
        lambda **kwargs: True,
    )
    monkeypatch.setattr(
        codex_host_stop_summary,
        "_stop_intervention_bundle",
        lambda **kwargs: {
            "observation": surface_runtime.observation_envelope(
                host_family="codex",
                turn_phase="stop_summary",
                session_id="stop-main-replay",
                assistant_summary="Implemented the stop-summary visible surface fix.",
            ),
            "intervention_bundle": {
                "candidate": {"stage": "silent", "suppressed_reason": ""},
                "proposal": {"eligible": False, "suppressed_reason": ""},
            },
            "closeout_bundle": {
                "markdown_text": "**Odylith Assist:** B-096 stayed tied to the refreshed intervention contract.",
                "plain_text": "Odylith Assist: B-096 stayed tied to the refreshed intervention contract.",
            },
        },
    )
    buffer = io.StringIO()
    monkeypatch.setattr("sys.stdout", buffer)

    exit_code = codex_host_stop_summary.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert buffer.getvalue() == ""


def test_main_suppresses_cli_help_stop_replay(monkeypatch, tmp_path: Path) -> None:
    codex_host_stop_summary.intervention_surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending stop replay.",
        session_id="codex-stop-help",
        host_family="codex",
        intervention_key="codex-stop-help-replay",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** stale stop replay",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )
    monkeypatch.setattr(
        codex_host_stop_summary.codex_host_shared,
        "load_payload",
        lambda: {"last_assistant_message": _CLI_HELP_OUTPUT, "session_id": "codex-stop-help"},
    )
    buffer = io.StringIO()
    monkeypatch.setattr("sys.stdout", buffer)

    exit_code = codex_host_stop_summary.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert buffer.getvalue() == ""


def test_main_does_not_block_stop_when_odylith_closeout_is_already_visible(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        codex_host_stop_summary.codex_host_shared,
        "load_payload",
        lambda: {
            "last_assistant_message": (
                "Implemented the stop-summary visible surface fix for B-096.\n\n"
                "**Odylith Assist:** B-096 stayed tied to the refreshed intervention contract."
            ),
            "session_id": "stop-main-visible",
        },
    )
    monkeypatch.setattr(
        codex_host_stop_summary,
        "render_codex_stop_summary",
        lambda *args, **kwargs: "**Odylith Assist:** B-096 stayed tied to the refreshed intervention contract.",
    )
    monkeypatch.setattr(
        codex_host_stop_summary,
        "_stop_intervention_bundle",
        lambda **kwargs: {},
    )
    buffer = io.StringIO()
    monkeypatch.setattr("sys.stdout", buffer)

    exit_code = codex_host_stop_summary.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert buffer.getvalue() == ""


def test_confirmation_refusal_preserves_the_saved_summary(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(codex_host_stop_summary.codex_host_shared, "load_payload", lambda: {
        "session_id": "confirmation-refused", "last_assistant_message": 'Implemented the deferred confirmation boundary and validated the durable session retention tests.',
    })
    monkeypatch.setattr(codex_host_stop_summary.host_surface_runtime, "confirm_assistant_chat_delivery", lambda **kwargs: (
        _ for _ in ()).throw(host_dirty_checkpoint.HostDirtyCheckpointError("confirmation journal refused")))
    assert codex_host_stop_summary.main(["--repo-root", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out) == {"systemMessage": "Odylith could not save chat-delivery confirmation."}
    rows = host_dirty_checkpoint.read_compass_events(repo_root=tmp_path)
    assert len(rows) == 1 and rows[0]["event"]["summary"] == 'Implemented the deferred confirmation boundary and validated the durable session retention tests.'
    assert rows[0]["event"]["session_id"] == "confirmation-refused"
