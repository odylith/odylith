from __future__ import annotations

import json
from pathlib import Path

from odylith import cli
from odylith.runtime.intervention_engine import delivery_ledger
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
                    {"hooks": [{"command": "./.odylith/bin/odylith codex prompt-context --repo-root ."}]}
                ],
                "PostToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {"command": "./.odylith/bin/odylith codex post-bash-checkpoint --repo-root ."}
                        ],
                    }
                ],
                "Stop": [
                    {"hooks": [{"command": "./.odylith/bin/odylith codex stop-summary --repo-root ."}]}
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
                    {"command": '"$CLAUDE_PROJECT_DIR"/.odylith/bin/odylith claude prompt-context --repo-root "$CLAUDE_PROJECT_DIR"'},
                    {"command": '"$CLAUDE_PROJECT_DIR"/.odylith/bin/odylith claude prompt-teaser --repo-root "$CLAUDE_PROJECT_DIR"'},
                ]
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Write|Edit|MultiEdit",
                "hooks": [
                    {"command": '"$CLAUDE_PROJECT_DIR"/.odylith/bin/odylith claude post-edit-checkpoint --repo-root "$CLAUDE_PROJECT_DIR"'}
                ],
            },
            {
                "matcher": "Bash",
                "hooks": [
                    {"command": '"$CLAUDE_PROJECT_DIR"/.odylith/bin/odylith claude post-bash-checkpoint --repo-root "$CLAUDE_PROJECT_DIR"'}
                ],
            },
        ],
        "Stop": [
            {"hooks": [{"command": '"$CLAUDE_PROJECT_DIR"/.odylith/bin/odylith claude stop-summary --repo-root "$CLAUDE_PROJECT_DIR"'}]}
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
        summary="Odylith Assist kept the proof tight.",
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
    assert snapshot["counts_by_kind"]["intervention_card"] == 1
    assert snapshot["counts_by_kind"]["capture_proposed"] == 1
    assert snapshot["counts_by_kind"]["assist_closeout"] == 1
    assert snapshot["latest_visible_event"]["delivery_channel"] == "stop_one_shot_guard"
    assert snapshot["pending_proposal_state"]["pending_count"] == 1


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
    assert report["chat_visible_proof"]["status"] == "proven_this_session"
    assert report["delivery_ledger"]["visible_event_count"] == 1
    assert "**Odylith Intervention Status**" in rendered
    assert "Activation: ready" in rendered
    assert "Chat-visible proof: proven_this_session" in rendered
    assert "Odylith Observation" in rendered
    assert "Fast smoke:" in rendered
    assert any(row["lane"] == "Ambient Highlight" for row in report["active_lanes"])
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
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
        render_surface="codex_post_tool_use",
    )

    report = host_intervention_status.inspect_intervention_status(
        repo_root=tmp_path,
        host_family="codex",
        session_id="session-hidden-ready",
    )

    assert report["activation"] == "ready"
    assert report["delivery_ledger"]["event_count"] == 1
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
