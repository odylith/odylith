from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.intervention_engine import delivery_ledger
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.intervention_engine import surface_runtime
from odylith.runtime.intervention_engine import visibility_broker
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


def _bundle(
    *,
    host_family: str = "codex",
    session_id: str = "visibility-session",
    prompt: str = "Keep the intervention visible.",
    visible_text: str = "**Odylith Observation:** The visible path is armed.",
) -> dict[str, object]:
    observation = surface_runtime.observation_envelope(
        host_family=host_family,
        turn_phase="post_bash_checkpoint",
        session_id=session_id,
        prompt_excerpt=prompt,
        changed_paths=["src/odylith/runtime/intervention_engine/visibility_broker.py"],
        workstreams=["B-096"],
        components=["governance-intervention-engine"],
        context_packet_summary={"packet_kind": "context_dossier", "route_ready": True},
        execution_engine_summary={
            "execution_engine_present": True,
            "execution_engine_mode": "verify",
            "execution_engine_next_move": "verify.visible_chat_contract",
        },
        memory_summary={"recent_event_count": 0, "semantic_signature": ["visibility", "fallback"]},
        tribunal_summary={"systemic_brief": {"latent_causes": ["hidden hook output"]}},
        visibility_summary={"chat_visible_proof": "unproven_this_session"},
    )
    return {
        "observation": observation,
        "intervention_bundle": {
            "candidate": {
                "stage": "card",
                "suppressed_reason": "",
                "markdown_text": visible_text,
                "plain_text": visible_text.replace("**", ""),
                "moment": {"score": 91},
            },
            "proposal": {"eligible": False, "suppressed_reason": ""},
        },
        "closeout_bundle": {
            "markdown_text": "**Odylith Assist:** kept the visible proof honest.",
            "plain_text": "Odylith Assist: kept the visible proof honest.",
        },
    }


def test_visibility_failure_detector_stays_quiet_for_benign_suppression_language() -> None:
    assert not visibility_broker.reports_visibility_failure(
        prompt="No intervention needed here; keep the chat quiet."
    )
    assert not visibility_broker.reports_visibility_failure(
        prompt="This proposal is not necessary for the current turn."
    )
    assert visibility_broker.reports_visibility_failure(
        prompt="No intervention blocks are visible in my chat."
    )
    assert visibility_broker.reports_visibility_failure(
        prompt="The proposal is not visible inside the chat."
    )


def test_broker_hard_fail_visible_for_zero_visibility_feedback(tmp_path: Path) -> None:
    bundle = _bundle(
        prompt="ZERO ambient highlights, ZERO intervention blocks, and ZERO Assis in this session.",
        visible_text="",
    )

    decision = visibility_broker.build_visible_intervention_decision(
        repo_root=tmp_path,
        bundle=bundle,
        host_family="codex",
        turn_phase="prompt_submit",
        session_id="visibility-session",
        include_proposal=False,
        include_closeout=False,
    )

    assert decision.visible_markdown.startswith("---\n\n**Odylith Observation:** This is a visibility failure")
    assert decision.delivery_status == "assistant_render_required"
    assert decision.delivery_channel == "assistant_visible_fallback"
    assert decision.proof_required is True


def test_broker_hard_fail_visible_for_zero_signals_branding_feedback(tmp_path: Path) -> None:
    bundle = _bundle(
        prompt="ZERO signals in my chat. Odylith interventions NEED to be visible for branding.",
        visible_text="",
    )

    decision = visibility_broker.build_visible_intervention_decision(
        repo_root=tmp_path,
        bundle=bundle,
        host_family="codex",
        turn_phase="prompt_submit",
        session_id="visibility-session",
        include_proposal=False,
        include_closeout=False,
    )

    assert decision.visible_markdown.startswith("---\n\n**Odylith Observation:** This is a visibility failure")
    assert decision.delivery_status == "assistant_render_required"
    assert decision.proof_required is True


def test_hidden_fallback_ready_is_not_chat_visible_until_exact_markdown_confirmed(tmp_path: Path) -> None:
    bundle = _bundle()
    decision = visibility_broker.build_visible_intervention_decision(
        repo_root=tmp_path,
        bundle=bundle,
        host_family="codex",
        turn_phase="post_bash_checkpoint",
        session_id="visibility-session",
        include_proposal=False,
        include_closeout=False,
    )

    visibility_broker.append_decision_events(
        repo_root=tmp_path,
        bundle=bundle,
        decision=decision,
        render_surface="codex_post_tool_use",
    )
    before = delivery_ledger.delivery_snapshot(
        repo_root=tmp_path,
        host_family="codex",
        session_id="visibility-session",
    )

    assert before["event_count"] >= 1
    assert before["visible_event_count"] == 0
    assert before["latest_event"]["delivery_status"] == "assistant_render_required"

    confirmed = visibility_broker.confirm_assistant_chat_delivery(
        repo_root=tmp_path,
        host_family="codex",
        session_id="visibility-session",
        last_assistant_message="Done.\n\n---\n**Odylith Observation:** The visible path is armed.\n---",
        render_surface="codex_status_probe",
    )
    after = delivery_ledger.delivery_snapshot(
        repo_root=tmp_path,
        host_family="codex",
        session_id="visibility-session",
    )

    assert confirmed
    assert after["visible_event_count"] == 1
    assert after["latest_visible_event"]["delivery_status"] == "assistant_chat_confirmed"


def test_assistant_chat_confirmation_tolerates_unruled_text_but_records_ruled_markdown(tmp_path: Path) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Observation waiting for exact chat proof.",
        session_id="exact-session",
        host_family="codex",
        intervention_key="iv-exact",
        turn_phase="post_bash_checkpoint",
        display_markdown="---\n**Odylith Observation:** The exact visible path is armed.\n---",
        display_plain="Odylith Observation: The exact visible path is armed.",
        delivery_channel="assistant_visible_fallback",
        delivery_status="assistant_render_required",
        render_surface="codex_post_tool_use",
    )

    partial = visibility_broker.confirm_assistant_chat_delivery(
        repo_root=tmp_path,
        host_family="codex",
        session_id="exact-session",
        last_assistant_message="The exact visible path is armed.",
        render_surface="codex_status_probe",
    )
    plain_label = visibility_broker.confirm_assistant_chat_delivery(
        repo_root=tmp_path,
        host_family="codex",
        session_id="exact-session",
        last_assistant_message="Odylith Observation: The exact visible path is armed.",
        render_surface="codex_status_probe",
    )
    unruled_markdown = visibility_broker.confirm_assistant_chat_delivery(
        repo_root=tmp_path,
        host_family="codex",
        session_id="exact-session",
        last_assistant_message="Done.\n\n**Odylith Observation:** The exact visible path is armed.",
        render_surface="codex_status_probe",
    )
    assert partial == []
    assert plain_label == []
    assert len(unruled_markdown) == 1
    proven = delivery_ledger.delivery_snapshot(
        repo_root=tmp_path,
        host_family="codex",
        session_id="exact-session",
    )

    assert proven["visible_event_count"] == 1
    assert proven["latest_visible_event"]["delivery_status"] == "assistant_chat_confirmed"
    latest_event = stream_state.load_recent_intervention_events(
        repo_root=tmp_path,
        session_id="exact-session",
        limit=1,
    )[-1]
    assert latest_event["display_markdown"].startswith("---\n\n**Odylith Observation:**")
    assert latest_event["display_markdown"].endswith("\n---")


def test_duplicate_hidden_fallbacks_confirm_once_and_do_not_count_visible_before_chat(
    tmp_path: Path,
) -> None:
    for render_surface in ("codex_prompt_context", "codex_post_tool_use"):
        stream_state.append_intervention_event(
            repo_root=tmp_path,
            kind="intervention_card",
            summary="Duplicate hidden fallback waiting for chat proof.",
            session_id="duplicate-session",
            host_family="codex",
            intervention_key="iv-duplicate",
            turn_phase="post_bash_checkpoint",
            display_markdown="---\n**Odylith Observation:** The duplicate path still needs chat proof.\n---",
            delivery_channel="assistant_visible_fallback",
            delivery_status="assistant_render_required",
            render_surface=render_surface,
        )
    hidden = delivery_ledger.delivery_snapshot(
        repo_root=tmp_path,
        host_family="codex",
        session_id="duplicate-session",
    )

    assert hidden["event_count"] == 2
    assert hidden["visible_event_count"] == 0

    confirmed = visibility_broker.confirm_assistant_chat_delivery(
        repo_root=tmp_path,
        host_family="codex",
        session_id="duplicate-session",
        last_assistant_message=(
            "Visible now.\n\n"
            "---\n**Odylith Observation:** The duplicate path still needs chat proof.\n---"
        ),
        render_surface="codex_status_probe",
    )
    proven = delivery_ledger.delivery_snapshot(
        repo_root=tmp_path,
        host_family="codex",
        session_id="duplicate-session",
    )

    assert len(confirmed) == 1
    assert proven["event_count"] == 3
    assert proven["visible_event_count"] == 1


def test_generated_proposal_is_not_actionable_until_chat_visible(tmp_path: Path) -> None:
    bundle = _bundle(
        visible_text=(
            "**Odylith Observation:** Proposal proof must be visible before confirmation.\n\n"
            "Odylith Proposal: Capture the visible proposal gate.\n\n"
            "- Casebook: capture CB-122 so the recurrence is auditable.\n\n"
            'To apply, say "apply this proposal".'
        )
    )
    proposal_text = (
        "Odylith Proposal: Capture the visible proposal gate.\n\n"
        "- Casebook: capture CB-122 so the recurrence is auditable.\n\n"
        'To apply, say "apply this proposal".'
    )
    intervention = dict(bundle["intervention_bundle"])
    intervention["proposal"] = {
        "eligible": True,
        "suppressed_reason": "",
        "key": "proposal-visible-gate",
        "summary": "Capture the visible proposal gate.",
        "markdown_text": proposal_text,
        "plain_text": proposal_text,
        "confirmation_text": "apply this proposal",
        "action_surfaces": ["casebook"],
        "semantic_signature": ["proposal-visible-gate"],
    }
    bundle["intervention_bundle"] = intervention

    decision = visibility_broker.build_visible_intervention_decision(
        repo_root=tmp_path,
        bundle=bundle,
        host_family="codex",
        turn_phase="post_bash_checkpoint",
        session_id="visibility-session",
        include_proposal=True,
        include_closeout=False,
    )
    visibility_broker.append_decision_events(
        repo_root=tmp_path,
        bundle=bundle,
        decision=decision,
        render_surface="codex_post_tool_use",
    )
    hidden = delivery_ledger.delivery_snapshot(
        repo_root=tmp_path,
        host_family="codex",
        session_id="visibility-session",
    )

    assert hidden["visible_event_count"] == 0
    assert hidden["counts_by_kind"]["capture_proposed"] == 1
    assert hidden["latest_event"]["delivery_status"] == "assistant_render_required"

    confirmed = visibility_broker.confirm_assistant_chat_delivery(
        repo_root=tmp_path,
        host_family="codex",
        session_id="visibility-session",
        last_assistant_message=f"Rendered in chat.\n\n{decision.visible_markdown}",
        render_surface="codex_status_probe",
    )
    visible = delivery_ledger.delivery_snapshot(
        repo_root=tmp_path,
        host_family="codex",
        session_id="visibility-session",
    )

    assert any(row["kind"] == "capture_proposed" for row in confirmed)
    assert visible["visible_event_count"] >= 1
    assert visible["pending_proposal_state"]["pending_count"] == 1
    assert visible["latest_visible_event"]["delivery_status"] == "assistant_chat_confirmed"


def test_status_probe_moves_unproven_session_to_chat_confirmed(tmp_path: Path) -> None:
    _seed_codex_repo(tmp_path)
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Observation hidden in fallback context.",
        session_id="status-session",
        host_family="codex",
        intervention_key="iv-status",
        turn_phase="post_bash_checkpoint",
        display_markdown="---\n**Odylith Observation:** Status should confirm this.\n---",
        delivery_channel="assistant_visible_fallback",
        delivery_status="assistant_render_required",
        render_surface="codex_post_tool_use",
    )

    unproven = host_intervention_status.inspect_intervention_status(
        repo_root=tmp_path,
        host_family="codex",
        session_id="status-session",
    )
    proven = host_intervention_status.inspect_intervention_status(
        repo_root=tmp_path,
        host_family="codex",
        session_id="status-session",
        last_assistant_message="The chat now shows **Odylith Observation:** Status should confirm this.",
    )

    assert unproven["chat_visible_proof"]["status"] == "pending_confirmation"
    assert unproven["delivery_ledger"]["unconfirmed_event_count"] == 1
    assert proven["chat_visible_proof"]["status"] == "proven_this_session"
    assert proven["chat_confirmed_event_count"] == 1
    assert proven["delivery_ledger"]["latest_visible_event"]["delivery_status"] == "assistant_chat_confirmed"
    latest_event = stream_state.load_recent_intervention_events(
        repo_root=tmp_path,
        session_id="status-session",
        limit=1,
    )[-1]
    assert latest_event["display_markdown"].startswith("---\n\n")


def test_codex_and_claude_share_broker_semantics_for_post_tool_visibility(tmp_path: Path) -> None:
    codex = visibility_broker.build_visible_intervention_decision(
        repo_root=tmp_path,
        bundle=_bundle(host_family="codex", session_id="codex-session"),
        host_family="codex",
        turn_phase="post_bash_checkpoint",
        session_id="codex-session",
        include_proposal=False,
        include_closeout=False,
    )
    claude = visibility_broker.build_visible_intervention_decision(
        repo_root=tmp_path,
        bundle=_bundle(host_family="claude", session_id="claude-session"),
        host_family="claude",
        turn_phase="post_edit_checkpoint",
        session_id="claude-session",
        include_proposal=False,
        include_closeout=False,
    )

    assert codex.visible_markdown == claude.visible_markdown
    assert codex.delivery_status == "assistant_render_required"
    assert claude.delivery_status == "assistant_render_required"
    assert codex.proof_required is True
    assert claude.proof_required is True


def test_broker_does_not_downgrade_to_ready_when_prior_hidden_beat_is_unconfirmed(
    tmp_path: Path,
) -> None:
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Earlier manual proof.",
        session_id="pending-session",
        host_family="codex",
        intervention_key="iv-visible",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** Earlier manual proof.",
        delivery_channel="manual_visible_command",
        delivery_status="manual_visible",
        render_surface="codex_visible_intervention",
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending hidden proof.",
        session_id="pending-session",
        host_family="codex",
        intervention_key="iv-pending",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** Pending hidden proof.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
        render_surface="codex_post_tool_use",
    )

    decision = visibility_broker.build_visible_intervention_decision(
        repo_root=tmp_path,
        bundle=_bundle(session_id="pending-session"),
        host_family="codex",
        turn_phase="post_bash_checkpoint",
        session_id="pending-session",
        include_proposal=False,
        include_closeout=False,
    )

    assert decision.delivery_channel == "assistant_visible_fallback"
    assert decision.delivery_status == "assistant_render_required"
    assert decision.proof_required is True
    assert decision.visibility_summary["visible_event_count"] == 1
    assert decision.visibility_summary["unconfirmed_event_count"] == 1


def test_broker_decision_fingerprints_context_execution_memory_tribunal_and_visibility(
    tmp_path: Path,
) -> None:
    decision = visibility_broker.build_visible_intervention_decision(
        repo_root=tmp_path,
        bundle=_bundle(),
        host_family="codex",
        turn_phase="post_bash_checkpoint",
        session_id="visibility-session",
        include_proposal=False,
        include_closeout=False,
    )

    fingerprints = decision.source_fingerprints or {}
    assert fingerprints["context_packet"]
    assert fingerprints["execution_engine"]
    assert fingerprints["memory"]
    assert fingerprints["tribunal"]
    assert fingerprints["visibility"]
    assert decision.visibility_summary["proof_required"] is True
