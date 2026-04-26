from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith import cli
from odylith.runtime.intervention_engine import delivery_ledger
from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.surfaces import host_intervention_status


def _seed_codex_repo(repo_root: Path) -> None:
    (repo_root / "AGENTS.md").write_text("# Repo guidance\n", encoding="utf-8")
    launcher = repo_root / ".odylith" / "bin"
    launcher.mkdir(parents=True, exist_ok=True)
    (launcher / "odylith").write_text("#!/bin/sh\n", encoding="utf-8")
    codex_root = repo_root / ".codex"
    codex_root.mkdir(parents=True, exist_ok=True)
    (codex_root / "config.toml").write_text("[features]\ncodex_hooks = true\n", encoding="utf-8")
    (codex_root / "hooks.json").write_text(
        json.dumps(
            {
                "UserPromptSubmit": [
                    {
                        "hooks": [
                            {
                                "command": "python3 ./.agents/bin/odylith-host-launcher.py codex prompt-context --repo-root ."
                            }
                        ]
                    }
                ],
                "PostToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {
                                "command": "python3 ./.agents/bin/odylith-host-launcher.py codex post-bash-checkpoint --repo-root ."
                            }
                        ],
                    }
                ],
                "Stop": [
                    {
                        "hooks": [
                            {
                                "command": "python3 ./.agents/bin/odylith-host-launcher.py codex stop-summary --repo-root ."
                            }
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _seed_claude_repo(repo_root: Path) -> None:
    (repo_root / "AGENTS.md").write_text("# Repo guidance\n", encoding="utf-8")
    (repo_root / "CLAUDE.md").write_text("# Claude memory\n", encoding="utf-8")
    launcher = repo_root / ".odylith" / "bin"
    launcher.mkdir(parents=True, exist_ok=True)
    (launcher / "odylith").write_text("#!/bin/sh\n", encoding="utf-8")
    hooks = {
        "UserPromptSubmit": [
            {
                "hooks": [
                    {
                        "command": 'python3 "$CLAUDE_PROJECT_DIR"/.agents/bin/odylith-host-launcher.py claude prompt-context --repo-root "$CLAUDE_PROJECT_DIR"'
                    },
                    {
                        "command": 'python3 "$CLAUDE_PROJECT_DIR"/.agents/bin/odylith-host-launcher.py claude prompt-teaser --repo-root "$CLAUDE_PROJECT_DIR"'
                    },
                ]
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Write|Edit|MultiEdit",
                "hooks": [
                    {
                        "command": 'python3 "$CLAUDE_PROJECT_DIR"/.agents/bin/odylith-host-launcher.py claude post-edit-checkpoint --repo-root "$CLAUDE_PROJECT_DIR"'
                    }
                ],
            },
            {
                "matcher": "Bash",
                "hooks": [
                    {
                        "command": 'python3 "$CLAUDE_PROJECT_DIR"/.agents/bin/odylith-host-launcher.py claude post-bash-checkpoint --repo-root "$CLAUDE_PROJECT_DIR"'
                    }
                ],
            },
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "command": 'python3 "$CLAUDE_PROJECT_DIR"/.agents/bin/odylith-host-launcher.py claude stop-summary --repo-root "$CLAUDE_PROJECT_DIR"'
                    }
                ]
            }
        ],
    }
    (repo_root / ".claude").mkdir(parents=True, exist_ok=True)
    (repo_root / ".claude" / "settings.json").write_text(json.dumps({"hooks": hooks}), encoding="utf-8")


def test_delivery_snapshot_reports_proven_visible_events(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Observation rendered.",
        session_id="session-1",
        host_family="codex",
        intervention_key="iv-1",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** The visible path is armed.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
        render_surface="codex_post_tool_use",
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="capture_proposed",
        summary="Proposal rendered.",
        session_id="session-1",
        host_family="codex",
        intervention_key="iv-1",
        turn_phase="post_bash_checkpoint",
        action_surfaces=("radar", "registry"),
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
        render_surface="codex_post_tool_use",
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="assist_closeout",
        summary="Odylith Assist closing with 1 focused check.",
        session_id="session-1",
        host_family="codex",
        intervention_key="assist",
        turn_phase="stop_summary",
        delivery_channel="stop_one_shot_guard",
        delivery_status="stop_continuation_ready",
        render_surface="codex_stop",
    )

    snapshot = delivery_ledger.delivery_snapshot(repo_root=tmp_path, host_family="codex", session_id="session-1")

    assert snapshot["event_count"] == 3
    assert snapshot["visible_event_count"] == 1
    assert snapshot["chat_confirmed_event_count"] == 0
    assert snapshot["unconfirmed_event_count"] == 1
    assert snapshot["counts_by_kind"]["intervention_card"] == 1
    assert snapshot["counts_by_kind"]["capture_proposed"] == 1
    assert snapshot["counts_by_kind"]["assist_closeout"] == 1
    assert snapshot["latest_visible_event"]["delivery_channel"] == "stop_one_shot_guard"
    assert snapshot["latest_unconfirmed_event"]["delivery_status"] == "assistant_fallback_ready"
    assert snapshot["pending_proposal_state"]["pending_count"] == 1


def test_delivery_snapshot_separates_chat_confirmed_from_manual_visible(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Manual fallback rendered.",
        session_id="session-chat-ratio",
        host_family="codex",
        intervention_key="iv-manual",
        display_markdown="**Odylith Observation:** Manual fallback rendered.",
        delivery_channel="manual_visible_command",
        delivery_status="manual_visible",
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Transcript confirmed.",
        session_id="session-chat-ratio",
        host_family="codex",
        intervention_key="iv-chat",
        display_markdown="**Odylith Observation:** Transcript confirmed.",
        delivery_channel="assistant_chat_transcript",
        delivery_status="assistant_chat_confirmed",
    )

    snapshot = delivery_ledger.delivery_snapshot(repo_root=tmp_path, host_family="codex", session_id="session-chat-ratio")

    assert snapshot["event_count"] == 2
    assert snapshot["visible_event_count"] == 2
    assert snapshot["chat_confirmed_event_count"] == 1
    assert snapshot["latest_chat_confirmed_event"]["intervention_key"] == "iv-chat"


def test_delivery_snapshot_infers_host_family_from_render_surface_for_legacy_visible_rows(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Legacy manual fallback rendered.",
        session_id="legacy-visible",
        intervention_key="legacy-visible-key",
        display_markdown="**Odylith Observation:** Legacy fallback rendered.",
        delivery_channel="manual_visible_command",
        delivery_status="manual_visible",
        render_surface="codex_visible_intervention",
    )

    snapshot = delivery_ledger.delivery_snapshot(repo_root=tmp_path, host_family="codex", session_id="legacy-visible")

    assert snapshot["event_count"] == 1
    assert snapshot["visible_event_count"] == 1
    assert snapshot["latest_visible_event"]["host_family"] == "codex"


def test_delivery_snapshot_reports_visibility_ratios_by_family(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="ambient_signal",
        summary="Odylith Risks: risky hidden fallback.",
        session_id="ratio-session",
        host_family="codex",
        intervention_key="ambient-hidden",
        display_markdown="---\n\n**Odylith Risks:** Risk needs chat confirmation.\n\n---",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
        render_surface="codex_post_tool_use",
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="ambient_signal",
        summary="Odylith History: visible prior bug.",
        session_id="ratio-session",
        host_family="codex",
        intervention_key="ambient-visible",
        display_markdown="---\n\n**Odylith History:** Prior bug is visible.\n\n---",
        delivery_channel="manual_visible_command",
        delivery_status="manual_visible",
        render_surface="codex_visible_intervention",
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Odylith Observation",
        session_id="ratio-session",
        host_family="codex",
        intervention_key="observation-confirmed",
        display_markdown="---\n\n**Odylith Observation:** Confirmed in chat.\n\n---",
        delivery_channel="assistant_chat_transcript",
        delivery_status="assistant_chat_confirmed",
        render_surface="codex_intervention_status",
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="assist_closeout",
        summary="**Odylith Assist:** visible closeout.",
        session_id="ratio-session",
        host_family="codex",
        intervention_key="assist",
        display_markdown="**Odylith Assist:** visible closeout.",
        delivery_channel="manual_visible_command",
        delivery_status="manual_visible",
        render_surface="codex_visible_intervention",
    )

    snapshot = delivery_ledger.delivery_snapshot(repo_root=tmp_path, host_family="codex", session_id="ratio-session")
    ratios = snapshot["visibility_ratios"]

    assert ratios["ambient"]["total"] == 2
    assert ratios["ambient"]["ledger_visible"] == 1
    assert ratios["ambient"]["chat_confirmed"] == 0
    assert ratios["ambient"]["pending_confirmation"] == 1
    assert ratios["ambient"]["ledger_visible_ratio"] == 0.5
    assert ratios["ambient"]["chat_confirmed_ratio"] == 0.0
    assert ratios["intervention"]["total"] == 1
    assert ratios["intervention"]["ledger_visible"] == 1
    assert ratios["intervention"]["chat_confirmed"] == 1
    assert ratios["intervention"]["ledger_visible_ratio"] == 1.0
    assert ratios["intervention"]["chat_confirmed_ratio"] == 1.0
    assert ratios["assist"]["total"] == 1
    assert ratios["assist"]["ledger_visible"] == 1
    assert ratios["assist"]["chat_confirmed"] == 0
    assert ratios["assist"]["pending_confirmation"] == 0
    assert ratios["assist"]["ledger_visible_ratio"] == 1.0
    assert ratios["assist"]["chat_confirmed_ratio"] == 0.0


def test_delivery_snapshot_visibility_ratios_collapse_pending_and_confirmed_rows_by_beat_identity(
    tmp_path: Path,
) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Observation needs chat confirmation.",
        session_id="ratio-collapse",
        host_family="codex",
        intervention_key="observation-collapse",
        display_markdown="---\n\n**Odylith Observation:** One real beat should not count twice.\n\n---",
        delivery_channel="assistant_visible_fallback",
        delivery_status="assistant_render_required",
        render_surface="codex_post_tool_use",
    )

    host_surface_runtime.confirm_assistant_chat_delivery(
        repo_root=tmp_path,
        host_family="codex",
        session_id="ratio-collapse",
        last_assistant_message="---\n\n**Odylith Observation:** One real beat should not count twice.\n\n---",
        render_surface="codex_user_prompt_submit",
    )

    snapshot = delivery_ledger.delivery_snapshot(repo_root=tmp_path, host_family="codex", session_id="ratio-collapse")
    ratios = snapshot["visibility_ratios"]

    assert ratios["intervention"]["total"] == 1
    assert ratios["intervention"]["ledger_visible"] == 1
    assert ratios["intervention"]["chat_confirmed"] == 1
    assert ratios["intervention"]["pending_confirmation"] == 0
    assert ratios["intervention"]["ledger_visible_ratio"] == 1.0
    assert ratios["intervention"]["chat_confirmed_ratio"] == 1.0


@pytest.mark.parametrize(
    ("host_family", "seed_repo"),
    [
        ("codex", _seed_codex_repo),
        ("claude", _seed_claude_repo),
    ],
)
def test_later_live_beats_supersede_stale_teaser_confirmation_debt(
    tmp_path: Path,
    host_family: str,
    seed_repo,
) -> None:
    seed_repo(tmp_path)
    session_id = f"{host_family}-stale-teaser"
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_teaser",
        summary="Teaser still waiting.",
        session_id=session_id,
        host_family=host_family,
        intervention_key="teaser",
        turn_phase="prompt_submit",
        display_markdown="---\n\nOdylith is tracking this signal: teaser waiting for proof.\n\n---",
        delivery_channel="assistant_visible_fallback",
        delivery_status="assistant_render_required",
        render_surface=f"{host_family}_user_prompt_submit",
        metadata={"selected_block_set_id": "prompt-1"},
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="ambient_signal",
        summary="Later live beat.",
        session_id=session_id,
        host_family=host_family,
        intervention_key="risk",
        turn_phase="post_bash_checkpoint",
        display_markdown="---\n\n**Odylith Risks:** Later live proof should retire the teaser debt.\n\n---",
        delivery_channel="assistant_visible_fallback",
        delivery_status="assistant_render_required",
        render_surface=f"{host_family}_post_tool_use",
        metadata={"selected_block_set_id": "checkpoint-1"},
    )

    host_surface_runtime.confirm_assistant_chat_delivery(
        repo_root=tmp_path,
        host_family=host_family,
        session_id=session_id,
        last_assistant_message="---\n\n**Odylith Risks:** Later live proof should retire the teaser debt.\n\n---",
        render_surface=f"{host_family}_post_tool_use",
    )

    report = host_intervention_status.inspect_intervention_status(
        repo_root=tmp_path,
        host_family=host_family,
        session_id=session_id,
    )

    assert report["chat_visible_proof"]["status"] == "proven_this_session"
    assert report["delivery_ledger"]["unconfirmed_event_count"] == 0
    assert report["assistant_visible_replay_markdown"] == ""
    assert report["delivery_ledger"]["visibility_ratios"]["teaser"]["total"] == 0


@pytest.mark.parametrize(
    ("host_family", "seed_repo"),
    [
        ("codex", _seed_codex_repo),
        ("claude", _seed_claude_repo),
    ],
)
def test_all_visible_lanes_clear_to_proven_session_for_both_hosts(
    tmp_path: Path,
    host_family: str,
    seed_repo,
) -> None:
    seed_repo(tmp_path)
    session_id = f"{host_family}-all-lanes"

    def _append(*, key: str, kind: str, text: str, phase: str, bundle: str) -> None:
        stream_state.append_intervention_event(
            repo_root=tmp_path,
            kind=kind,
            summary=text,
            session_id=session_id,
            host_family=host_family,
            intervention_key=key,
            turn_phase=phase,
            display_markdown=text,
            delivery_channel="assistant_visible_fallback",
            delivery_status="assistant_render_required",
            render_surface=f"{host_family}_{phase}",
            metadata={"selected_block_set_id": bundle},
        )

    _append(
        key="teaser",
        kind="intervention_teaser",
        text="---\n\nOdylith is tracking this signal: teaser pending.\n\n---",
        phase="prompt_submit",
        bundle="prompt-1",
    )
    _append(
        key="history",
        kind="ambient_signal",
        text="---\n\n**Odylith History:** Earlier bug still matters.\n\n---",
        phase="post_bash_checkpoint",
        bundle="checkpoint-1",
    )
    _append(
        key="risk",
        kind="ambient_signal",
        text="---\n\n**Odylith Risks:** New risk must surface.\n\n---",
        phase="post_bash_checkpoint",
        bundle="checkpoint-1",
    )
    _append(
        key="observation",
        kind="intervention_card",
        text="---\n\n**Odylith Observation:** The repo is ready for capture.\n\n---",
        phase="post_bash_checkpoint",
        bundle="checkpoint-1",
    )
    _append(
        key="proposal",
        kind="capture_proposed",
        text=(
            "---\n\n"
            "**Odylith Proposal:**\n"
            "Update governed truth now.\n\n"
            "- Refresh the component dossier.\n"
            "- Refresh the proof surface.\n\n"
            "Reply with yes to continue.\n\n"
            "---"
        ),
        phase="post_bash_checkpoint",
        bundle="checkpoint-1",
    )

    checkpoint_report = host_intervention_status.inspect_intervention_status(
        repo_root=tmp_path,
        host_family=host_family,
        session_id=session_id,
    )
    host_surface_runtime.confirm_assistant_chat_delivery(
        repo_root=tmp_path,
        host_family=host_family,
        session_id=session_id,
        last_assistant_message=checkpoint_report["assistant_visible_replay_markdown"],
        render_surface=f"{host_family}_post_tool_use",
    )

    _append(
        key="assist",
        kind="assist_closeout",
        text="**Odylith Assist:** closeout is visible.",
        phase="stop_summary",
        bundle="stop-1",
    )

    stop_report = host_intervention_status.inspect_intervention_status(
        repo_root=tmp_path,
        host_family=host_family,
        session_id=session_id,
    )
    host_surface_runtime.confirm_assistant_chat_delivery(
        repo_root=tmp_path,
        host_family=host_family,
        session_id=session_id,
        last_assistant_message=stop_report["assistant_visible_replay_markdown"],
        render_surface=f"{host_family}_stop_summary",
    )

    final_report = host_intervention_status.inspect_intervention_status(
        repo_root=tmp_path,
        host_family=host_family,
        session_id=session_id,
    )
    ratios = final_report["delivery_ledger"]["visibility_ratios"]

    assert checkpoint_report["assistant_visible_replay_markdown"] == (
        "---\n\n"
        "**Odylith History:** Earlier bug still matters.\n"
        "\n"
        "**Odylith Risks:** New risk must surface.\n"
        "\n"
        "**Odylith Observation:** The repo is ready for capture.\n"
        "\n"
        "**Odylith Proposal:**\n"
        "Update governed truth now.\n\n"
        "- Refresh the component dossier.\n"
        "- Refresh the proof surface.\n\n"
        "Reply with yes to continue.\n\n"
        "---"
    )
    assert final_report["chat_visible_proof"]["status"] == "proven_this_session"
    assert final_report["delivery_ledger"]["unconfirmed_event_count"] == 0
    assert final_report["assistant_visible_replay_markdown"] == ""
    assert ratios["ambient"]["chat_confirmed_ratio"] == 1.0
    assert ratios["intervention"]["chat_confirmed_ratio"] == 1.0
    assert ratios["assist"]["chat_confirmed_ratio"] == 1.0
    assert ratios["teaser"]["total"] == 0


def test_codex_intervention_status_is_low_latency_and_human_readable(tmp_path: Path) -> None:
    _seed_codex_repo(tmp_path)
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Observation rendered.",
        session_id="session-2",
        host_family="codex",
        intervention_key="iv-2",
        turn_phase="post_bash_checkpoint",
        delivery_channel="manual_visible_command",
        delivery_status="manual_visible",
        render_surface="codex_visible_intervention",
    )

    report = host_intervention_status.inspect_intervention_status(
        repo_root=tmp_path,
        host_family="codex",
        session_id="session-2",
    )
    rendered = host_intervention_status.render_intervention_status(report)

    assert report["activation"] == "ready"
    assert report["chat_visible_proof"]["status"] == "ledger_visible_unconfirmed"
    assert report["delivery_ledger"]["visible_event_count"] == 1
    assert report["delivery_ledger"]["chat_confirmed_event_count"] == 0
    assert "**Odylith Intervention Status**" in rendered
    assert "Activation: ready" in rendered
    assert "Chat-visible proof: ledger_visible_unconfirmed" in rendered
    assert "1 ledger-visible event(s)" in rendered
    assert "proven-visible event(s)" not in rendered
    assert "- Observation/Proposal: ledger 1/1 (100.0%); chat-confirmed 0/1 (0.0%);" in rendered
    assert "Odylith Observation" in rendered
    assert "Fast smoke:" in rendered
    assert any(row["lane"] == "Ambient Highlight" for row in report["active_lanes"])
    assert any(
        row["lane"] == "Odylith Assist"
        and "prompt-submit visible fallback" in row["phase"]
        for row in report["active_lanes"]
    )
    assert all(row["lane"] != "Teaser / Ambient" for row in report["active_lanes"])


def test_codex_intervention_status_separates_static_ready_from_visible_proof(tmp_path: Path) -> None:
    _seed_codex_repo(tmp_path)

    report = host_intervention_status.inspect_intervention_status(
        repo_root=tmp_path,
        host_family="codex",
        session_id="session-without-visible-proof",
    )
    rendered = host_intervention_status.render_intervention_status(report)

    assert report["activation"] == "ready"
    assert report["delivery_ledger"]["visible_event_count"] == 0
    assert report["chat_visible_proof"]["status"] == "unproven_this_session"
    assert "Chat-visible proof: unproven_this_session" in rendered
    assert "End-to-end claim gate: only `Activation: ready` with `Chat-visible proof: proven_this_session` counts as fully chat-proved" in rendered
    assert "assistant must render the visible-intervention fallback directly" in rendered


def test_codex_intervention_status_does_not_count_hidden_ready_payload_as_visible(tmp_path: Path) -> None:
    _seed_codex_repo(tmp_path)
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Observation computed in hidden hook context.",
        session_id="session-hidden-ready",
        host_family="codex",
        intervention_key="iv-hidden-ready",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** Hidden hook context is not chat-visible proof.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
        render_surface="codex_post_tool_use",
    )

    report = host_intervention_status.inspect_intervention_status(
        repo_root=tmp_path,
        host_family="codex",
        session_id="session-hidden-ready",
    )
    rendered = host_intervention_status.render_intervention_status(report)

    assert report["activation"] == "ready"
    assert report["delivery_ledger"]["event_count"] == 1
    assert report["delivery_ledger"]["visible_event_count"] == 0
    assert report["delivery_ledger"]["chat_confirmed_event_count"] == 0
    assert report["delivery_ledger"]["unconfirmed_event_count"] == 1
    assert report["chat_visible_proof"]["status"] == "pending_confirmation"
    assert report["assistant_visible_replay_count"] == 1
    assert report["assistant_visible_replay_additional_count"] == 0
    assert "Next assistant-visible replay:" in rendered
    assert rendered.count("**Odylith Observation:** Hidden hook context is not chat-visible proof.") == 1
    assert "---\n\n**Odylith Observation:** Hidden hook context is not chat-visible proof.\n\n---" in rendered


def test_intervention_status_keeps_proven_session_honest_when_new_hidden_beat_is_pending(
    tmp_path: Path,
) -> None:
    _seed_codex_repo(tmp_path)
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Earlier Observation rendered.",
        session_id="session-proven-pending",
        host_family="codex",
        intervention_key="iv-visible",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** Earlier visible proof.",
        delivery_channel="manual_visible_command",
        delivery_status="manual_visible",
        render_surface="codex_visible_intervention",
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="New Observation waiting for chat confirmation.",
        session_id="session-proven-pending",
        host_family="codex",
        intervention_key="iv-hidden-later",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** New hidden beat still needs proof.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
        render_surface="codex_post_tool_use",
    )

    report = host_intervention_status.inspect_intervention_status(
        repo_root=tmp_path,
        host_family="codex",
        session_id="session-proven-pending",
    )
    rendered = host_intervention_status.render_intervention_status(report)

    assert report["delivery_ledger"]["visible_event_count"] == 1
    assert report["delivery_ledger"]["unconfirmed_event_count"] == 1
    assert report["chat_visible_proof"]["status"] == "ledger_visible_with_pending_confirmation"
    assert "pending chat-confirmation event(s)" in rendered
    assert "ledger-visible-only and pending-confirmation states are partial." in rendered
    assert report["assistant_visible_replay_count"] == 1
    assert report["assistant_visible_replay_additional_count"] == 0
    assert "Next assistant-visible replay:" in rendered
    assert "Additional pending replay blocks:" not in rendered
    assert report["assistant_visible_replay_markdown"] == (
        "---\n\n"
        "**Odylith Observation:** New hidden beat still needs proof.\n"
        "\n---"
    )


def test_intervention_status_prefers_ambient_risk_for_next_visible_replay(tmp_path: Path) -> None:
    _seed_codex_repo(tmp_path)
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Observation waiting for replay.",
        session_id="session-ambient-replay",
        host_family="codex",
        intervention_key="iv-observation-replay",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** The generic intervention should not hide the ambient brand signal.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
        render_surface="codex_post_tool_use",
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="ambient_signal",
        summary="Odylith Risks: ambient risk replay.",
        session_id="session-ambient-replay",
        host_family="codex",
        intervention_key="ambient-risk-replay",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Risks:** Surface this ambient replay block before the generic intervention.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
        render_surface="codex_post_tool_use",
    )

    report = host_intervention_status.inspect_intervention_status(
        repo_root=tmp_path,
        host_family="codex",
        session_id="session-ambient-replay",
    )
    rendered = host_intervention_status.render_intervention_status(report)

    assert report["assistant_visible_replay_count"] == 2
    assert report["assistant_visible_replay_additional_count"] == 0
    assert report["assistant_visible_replay_markdown"] == (
        "---\n\n"
        "**Odylith Risks:** Surface this ambient replay block before the generic intervention.\n"
        "\n"
        "**Odylith Observation:** The generic intervention should not hide the ambient brand signal.\n"
        "\n---"
    )
    assert "Additional pending replay blocks:" not in rendered
    assert "**Odylith Risks:** Surface this ambient replay block before the generic intervention." in rendered
    assert "**Odylith Observation:** The generic intervention should not hide the ambient brand signal." in rendered


def test_hook_payload_visible_text_without_ledger_proof_stays_unproven(tmp_path: Path) -> None:
    _seed_codex_repo(tmp_path)
    payload = host_surface_runtime.codex_post_tool_payload(
        developer_context=(
            "**Odylith Observation:** Hidden hook context is not chat proof.\n\n"
            "**Odylith Assist:** kept the continuity state."
        ),
        system_message="**Odylith Observation:** Hidden hook context is not chat proof.",
    )

    visible_candidate = host_surface_runtime.chat_visible_text(
        payload,
        host_family="codex",
        turn_phase="post_bash_checkpoint",
    )
    report = host_intervention_status.inspect_intervention_status(
        repo_root=tmp_path,
        host_family="codex",
        session_id="payload-only-session",
    )

    assert visible_candidate == "---\n\n**Odylith Observation:** Hidden hook context is not chat proof.\n\n---"
    assert report["activation"] == "ready"
    assert report["delivery_ledger"]["event_count"] == 0
    assert report["delivery_ledger"]["visible_event_count"] == 0
    assert report["chat_visible_proof"]["status"] == "unproven_this_session"


def test_claude_intervention_status_checks_prompt_teaser_and_edit_hooks(tmp_path: Path) -> None:
    _seed_claude_repo(tmp_path)

    report = host_intervention_status.inspect_intervention_status(
        repo_root=tmp_path,
        host_family="claude",
        session_id="session-3",
    )
    checks = report["static_readiness"]["checks"]

    assert report["activation"] == "ready"
    assert checks["prompt_context_hook"] is True
    assert checks["prompt_teaser_hook"] is True
    assert checks["post_edit_checkpoint_hook"] is True
    assert checks["post_bash_checkpoint_hook"] is True


def test_host_intervention_status_cli_dispatches_for_both_hosts(tmp_path: Path, capsys) -> None:
    _seed_codex_repo(tmp_path)
    assert cli.main(["codex", "intervention-status", "--repo-root", str(tmp_path), "--json"]) == 0
    codex_payload = json.loads(capsys.readouterr().out)
    assert codex_payload["host_family"] == "codex"
    assert codex_payload["activation"] == "ready"
    assert codex_payload["chat_visible_proof"]["status"] == "unproven_this_session"

    _seed_claude_repo(tmp_path)
    assert cli.main(["claude", "intervention-status", "--repo-root", str(tmp_path), "--json"]) == 0
    claude_payload = json.loads(capsys.readouterr().out)
    assert claude_payload["host_family"] == "claude"
    assert claude_payload["activation"] == "ready"
