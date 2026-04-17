from __future__ import annotations

import io
import json
from pathlib import Path

from odylith.runtime.intervention_engine import surface_runtime
from odylith.runtime.surfaces import claude_host_stop_summary


def test_main_logs_meaningful_stop_summary_to_compass(monkeypatch, tmp_path: Path) -> None:
    captured: list[tuple[str, str, list[str]]] = []

    def _fake_run_compass_log(*, project_dir, summary, workstreams):
        captured.append((str(project_dir), summary, list(workstreams)))

    monkeypatch.setattr(
        claude_host_stop_summary.claude_host_shared,
        "run_compass_log",
        _fake_run_compass_log,
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "last_assistant_message": (
                        "Updated CLAUDE assets and validated focused runtime tests for B-083. "
                        "Validation passed on the install and runtime slices."
                    )
                }
            )
        ),
    )

    exit_code = claude_host_stop_summary.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert len(captured) == 1
    project_dir, summary, workstreams = captured[0]
    assert project_dir == str(tmp_path.resolve())
    assert "Updated CLAUDE assets" in summary
    assert workstreams == ["B-083"]


def test_main_skips_question_shaped_stop_summaries(monkeypatch, tmp_path: Path) -> None:
    called: list[bool] = []
    monkeypatch.setattr(
        claude_host_stop_summary.claude_host_shared,
        "run_compass_log",
        lambda **kwargs: called.append(True),
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"last_assistant_message": "Would you like me to keep going?"})),
    )

    exit_code = claude_host_stop_summary.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert called == []


def test_main_skips_active_stop_hook_payload(monkeypatch, tmp_path: Path) -> None:
    called: list[bool] = []
    monkeypatch.setattr(
        claude_host_stop_summary.claude_host_shared,
        "run_compass_log",
        lambda **kwargs: called.append(True),
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "stop_hook_active": True,
                    "last_assistant_message": (
                        "Updated CLAUDE assets and validated focused runtime tests for B-083."
                    ),
                }
            )
        ),
    )

    exit_code = claude_host_stop_summary.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert called == []


def test_stop_intervention_bundle_uses_recent_prompt_excerpt_not_intervention_summary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    claude_host_stop_summary.intervention_surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="capture_proposed",
        summary="Odylith Proposal pending.",
        session_id="claude-stop-1",
        host_family="claude",
        intervention_key="iv-claude-stop-1",
        turn_phase="post_edit_checkpoint",
        prompt_excerpt="Capture the governed truth from this design conversation.",
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
            "closeout_bundle": {"markdown_text": "**Odylith Assist:** kept this grounded."},
        }

    monkeypatch.setattr(
        claude_host_stop_summary.host_surface_runtime,
        "compose_host_conversation_bundle",
        _fake_compose_host_bundle,
    )

    bundle = claude_host_stop_summary._stop_intervention_bundle(
        repo_root=tmp_path,
        payload={
            "session_id": "claude-stop-1",
            "last_assistant_message": (
                "Implemented the stop-summary memory regression fix for B-096 and "
                "validated the focused runtime hook tests."
            ),
        },
    )

    assert bundle["intervention_bundle"] == {"ok": True}
    assert seen["prompt"] == (
        "Capture the governed truth from this design conversation."
    )
    assert seen["session_id"] == "claude-stop-1"


def test_stop_intervention_bundle_recovers_recent_changed_paths(monkeypatch, tmp_path: Path) -> None:
    claude_host_stop_summary.intervention_surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Observation rendered.",
        session_id="claude-stop-2",
        host_family="claude",
        intervention_key="iv-claude-stop-2",
        turn_phase="post_edit_checkpoint",
        prompt_excerpt="Capture the governed truth from this engine session.",
        artifacts=["src/odylith/runtime/intervention_engine/voice.py"],
        display_markdown="**Odylith Observation:**",
    )
    seen: dict[str, object] = {}

    def _fake_compose_host_bundle(**kwargs):  # noqa: ANN001
        seen["candidate_paths"] = list(kwargs["changed_paths"])
        return {"intervention_bundle": {"ok": True}, "closeout_bundle": {}}

    monkeypatch.setattr(
        claude_host_stop_summary.host_surface_runtime,
        "compose_host_conversation_bundle",
        _fake_compose_host_bundle,
    )

    claude_host_stop_summary._stop_intervention_bundle(
        repo_root=tmp_path,
        payload={
            "session_id": "claude-stop-2",
            "last_assistant_message": (
                "Implemented the stop-summary changed-path recovery fix for B-096 and "
                "validated the focused runtime hook tests."
            ),
        },
    )

    assert seen["candidate_paths"] == ["src/odylith/runtime/intervention_engine/voice.py"]


def test_stop_intervention_bundle_can_recover_prompt_when_last_message_is_short(
    monkeypatch,
    tmp_path: Path,
) -> None:
    claude_host_stop_summary.intervention_surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_teaser",
        summary="Observation forming.",
        session_id="claude-stop-short-1",
        host_family="claude",
        intervention_key="iv-claude-stop-short-1",
        turn_phase="prompt_submit",
        prompt_excerpt=(
            "I still do not see any Odylith ambient highlights or interventions "
            "visible in chat."
        ),
        display_plain="Odylith is tracking this signal: governed truth is taking shape here.",
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
        claude_host_stop_summary.host_surface_runtime,
        "compose_host_conversation_bundle",
        _fake_compose_host_bundle,
    )

    bundle = claude_host_stop_summary._stop_intervention_bundle(
        repo_root=tmp_path,
        payload={
            "session_id": "claude-stop-short-1",
            "last_assistant_message": "Understood.",
        },
    )

    assert bundle["closeout_bundle"]["markdown_text"].startswith("**Odylith Assist:**")
    assert "ambient highlights" in str(seen["prompt"])
    assert seen["assistant_summary"] == ""


def test_render_stop_summary_combines_observation_and_assist(tmp_path: Path) -> None:
    rendered = claude_host_stop_summary.render_stop_summary(
        repo_root=tmp_path,
        payload={"last_assistant_message": "Implemented the engine slice.", "session_id": "claude-stop-3"},
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
                "markdown_text": "**Odylith Assist:** kept this grounded.",
                "plain_text": "Odylith Assist: kept this grounded.",
            },
        },
    )

    assert rendered == (
        "---\n\n"
        "**Odylith Observation:** The signal is real.\n"
        "\n---\n\n"
        "**Odylith Assist:** kept this grounded."
    )


def test_render_stop_summary_replays_unseen_live_beat_through_stop_lane(tmp_path: Path) -> None:
    claude_host_stop_summary.intervention_surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="ambient_signal",
        summary="Ambient signal rendered.",
        session_id="claude-stop-replay-1",
        host_family="claude",
        intervention_key="ambient",
        turn_phase="post_edit_checkpoint",
        display_markdown="**Odylith Insight:** this beat was computed earlier but still needs a visible lane.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    rendered = claude_host_stop_summary.render_stop_summary(
        repo_root=tmp_path,
        payload={
            "last_assistant_message": "Implemented the engine slice.",
            "session_id": "claude-stop-replay-1",
        },
        conversation_bundle_override={
            "intervention_bundle": {
                "candidate": {
                    "stage": "silent",
                    "suppressed_reason": "",
                },
                "proposal": {"eligible": False, "suppressed_reason": ""},
            },
            "closeout_bundle": {
                "markdown_text": "**Odylith Assist:** kept this grounded.",
                "plain_text": "Odylith Assist: kept this grounded.",
            },
        },
    )

    assert rendered == (
        "---\n\n"
        "**Odylith Insight:** this beat was computed earlier but still needs a visible lane.\n"
        "\n---\n\n"
        "**Odylith Assist:** kept this grounded."
    )


def test_render_stop_summary_replaces_teaser_with_unseen_live_beat(tmp_path: Path) -> None:
    claude_host_stop_summary.intervention_surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Observation rendered.",
        session_id="claude-stop-replay-teaser",
        host_family="claude",
        intervention_key="iv-claude-stop-replay-teaser",
        turn_phase="post_edit_checkpoint",
        display_markdown="**Odylith Observation:** The earlier card still needs chat visibility.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    rendered = claude_host_stop_summary.render_stop_summary(
        repo_root=tmp_path,
        payload={
            "last_assistant_message": "Implemented the engine slice.",
            "session_id": "claude-stop-replay-teaser",
        },
        conversation_bundle_override={
            "intervention_bundle": {
                "candidate": {
                    "stage": "teaser",
                    "suppressed_reason": "",
                    "teaser_text": "Odylith is tracking this signal: governed visibility is still unproven.",
                },
                "proposal": {"eligible": False, "suppressed_reason": ""},
            },
            "closeout_bundle": {
                "markdown_text": "**Odylith Assist:** kept this grounded.",
                "plain_text": "Odylith Assist: kept this grounded.",
            },
        },
    )

    assert "**Odylith Observation:** The earlier card still needs chat visibility." in rendered
    assert "Odylith is tracking this signal" not in rendered


def test_main_emits_system_message_for_visible_stop_surface(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        claude_host_stop_summary.claude_host_shared,
        "run_compass_log",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "session_id": "claude-stop-main",
                    "last_assistant_message": (
                        "Implemented the stop-summary visible surface fix for B-096 and "
                        "validated the focused runtime hook tests."
                    ),
                }
            )
        ),
    )
    monkeypatch.setattr(
        claude_host_stop_summary,
        "render_stop_summary",
        lambda **kwargs: "**Odylith Assist:** kept this grounded.",
    )
    monkeypatch.setattr(
        claude_host_stop_summary,
        "_stop_intervention_bundle",
        lambda **kwargs: {},
    )
    buffer = io.StringIO()
    monkeypatch.setattr("sys.stdout", buffer)

    exit_code = claude_host_stop_summary.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    payload = json.loads(buffer.getvalue())
    assert payload["systemMessage"] == "**Odylith Assist:** kept this grounded."
    assert payload["decision"] == "block"
    assert "**Odylith Assist:** kept this grounded." in payload["reason"]


def test_main_replays_pending_chat_blocks_before_stop_assist(monkeypatch, tmp_path: Path) -> None:
    claude_host_stop_summary.intervention_surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending stop replay.",
        session_id="claude-stop-main-replay",
        host_family="claude",
        intervention_key="claude-stop-main-replay-key",
        turn_phase="post_edit_checkpoint",
        display_markdown="**Odylith Observation:** Claude Stop must replay this before Assist.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )
    monkeypatch.setattr(
        claude_host_stop_summary.claude_host_shared,
        "run_compass_log",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "session_id": "claude-stop-main-replay",
                    "last_assistant_message": (
                        "Implemented the stop-summary visible surface fix for B-096 and "
                        "validated the focused runtime hook tests."
                    ),
                }
            )
        ),
    )
    monkeypatch.setattr(
        claude_host_stop_summary,
        "_stop_intervention_bundle",
        lambda **kwargs: {
            "observation": surface_runtime.observation_envelope(
                host_family="claude",
                turn_phase="stop_summary",
                session_id="claude-stop-main-replay",
                assistant_summary="Implemented the stop-summary visible surface fix.",
            ),
            "intervention_bundle": {
                "candidate": {"stage": "silent", "suppressed_reason": ""},
                "proposal": {"eligible": False, "suppressed_reason": ""},
            },
            "closeout_bundle": {
                "markdown_text": "**Odylith Assist:** kept this grounded.",
                "plain_text": "Odylith Assist: kept this grounded.",
            },
        },
    )
    buffer = io.StringIO()
    monkeypatch.setattr("sys.stdout", buffer)

    exit_code = claude_host_stop_summary.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    payload = json.loads(buffer.getvalue())
    assert payload["systemMessage"] == (
        "---\n\n"
        "**Odylith Observation:** Claude Stop must replay this before Assist.\n"
        "\n---\n\n"
        "**Odylith Assist:** kept this grounded."
    )
    assert payload["decision"] == "block"


def test_main_does_not_block_stop_when_odylith_closeout_is_already_visible(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        claude_host_stop_summary.claude_host_shared,
        "run_compass_log",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "session_id": "claude-stop-main-visible",
                    "last_assistant_message": (
                        "Implemented the stop-summary visible surface fix for B-096.\n\n"
                        "**Odylith Assist:** kept this grounded."
                    ),
                }
            )
        ),
    )
    monkeypatch.setattr(
        claude_host_stop_summary,
        "render_stop_summary",
        lambda **kwargs: "**Odylith Assist:** kept this grounded.",
    )
    monkeypatch.setattr(
        claude_host_stop_summary,
        "_stop_intervention_bundle",
        lambda **kwargs: {},
    )
    buffer = io.StringIO()
    monkeypatch.setattr("sys.stdout", buffer)

    exit_code = claude_host_stop_summary.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    payload = json.loads(buffer.getvalue())
    assert payload["systemMessage"] == "**Odylith Assist:** kept this grounded."
    assert "decision" not in payload
