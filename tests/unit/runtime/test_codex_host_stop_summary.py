from __future__ import annotations

import io
import json
from pathlib import Path

from odylith.runtime.surfaces import codex_host_stop_summary


def test_log_codex_stop_summary_logs_meaningful_updates(monkeypatch) -> None:
    seen: list[tuple[str, str, list[str] | None]] = []

    def _fake_run_compass_log(*, project_dir: str, summary: str, workstreams: list[str] | None = None) -> bool:
        seen.append((project_dir, summary, workstreams))
        return True

    monkeypatch.setattr(codex_host_stop_summary.codex_host_shared, "run_compass_log", _fake_run_compass_log)

    logged = codex_host_stop_summary.log_codex_stop_summary(
        ".",
        message="Implemented the Codex host dispatcher and validated the focused B-088 runtime tests.",
    )

    assert logged is True
    assert seen
    assert seen[0][0] == "."
    assert "B-088" in seen[0][1]
    assert seen[0][2] == ["B-088"]


def test_log_codex_stop_summary_ignores_non_meaningful_messages(monkeypatch) -> None:
    monkeypatch.setattr(
        codex_host_stop_summary.codex_host_shared,
        "run_compass_log",
        lambda **_: (_ for _ in ()).throw(AssertionError("should not log")),
    )

    assert codex_host_stop_summary.log_codex_stop_summary(".", message="Would you like a follow-up?") is False


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

    def _fake_compose_conversation_bundle(**kwargs):  # noqa: ANN001
        request = kwargs["request"]
        seen["repo_root"] = kwargs["repo_root"]
        seen["prompt"] = request.prompt
        seen["candidate_paths"] = list(request.candidate_paths)
        seen["session_id"] = request.session_id
        return {
            "intervention_bundle": {"ok": True},
            "closeout_bundle": {"markdown_text": "**Odylith Assist:** kept this grounded."},
        }

    monkeypatch.setattr(
        codex_host_stop_summary.conversation_runtime,
        "compose_conversation_bundle",
        _fake_compose_conversation_bundle,
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

    def _fake_compose_conversation_bundle(**kwargs):  # noqa: ANN001
        request = kwargs["request"]
        seen["candidate_paths"] = list(request.candidate_paths)
        return {"intervention_bundle": {"ok": True}, "closeout_bundle": {}}

    monkeypatch.setattr(
        codex_host_stop_summary.conversation_runtime,
        "compose_conversation_bundle",
        _fake_compose_conversation_bundle,
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
        display_plain="Odylith can already see governed truth taking shape here.",
    )
    seen: dict[str, object] = {}

    def _fake_compose_conversation_bundle(**kwargs):  # noqa: ANN001
        request = kwargs["request"]
        seen["prompt"] = request.prompt
        seen["assistant_summary"] = kwargs["assistant_summary"]
        return {
            "intervention_bundle": {},
            "closeout_bundle": {
                "markdown_text": "**Odylith Assist:** kept the UX signal visible.",
                "plain_text": "Odylith Assist: kept the UX signal visible.",
            },
        }

    monkeypatch.setattr(
        codex_host_stop_summary.conversation_runtime,
        "compose_conversation_bundle",
        _fake_compose_conversation_bundle,
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
                "markdown_text": "**Odylith Assist:** kept this grounded.",
                "plain_text": "Odylith Assist: kept this grounded.",
            },
        },
    )

    assert rendered == (
        "**Odylith Observation:** The signal is real.\n\n"
        "**Odylith Assist:** kept this grounded."
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
                "markdown_text": "**Odylith Assist:** kept this grounded.",
                "plain_text": "Odylith Assist: kept this grounded.",
            },
        },
    )

    assert rendered == (
        "**Odylith Observation:** This beat was computed earlier but still needs a visible lane.\n\n"
        "**Odylith Assist:** kept this grounded."
    )


def test_main_emits_system_message_for_visible_stop_surface(
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
        lambda *args, **kwargs: "**Odylith Assist:** kept this grounded.",
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
    payload = json.loads(buffer.getvalue())
    assert payload["systemMessage"] == "**Odylith Assist:** kept this grounded."
    assert payload["decision"] == "block"
    assert "**Odylith Assist:** kept this grounded." in payload["reason"]


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
                "**Odylith Assist:** kept this grounded."
            ),
            "session_id": "stop-main-visible",
        },
    )
    monkeypatch.setattr(
        codex_host_stop_summary,
        "render_codex_stop_summary",
        lambda *args, **kwargs: "**Odylith Assist:** kept this grounded.",
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
    payload = json.loads(buffer.getvalue())
    assert payload["systemMessage"] == "**Odylith Assist:** kept this grounded."
    assert "decision" not in payload
