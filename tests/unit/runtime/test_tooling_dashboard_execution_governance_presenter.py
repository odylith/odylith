from __future__ import annotations

from odylith.runtime.surfaces import tooling_dashboard_execution_governance_presenter as presenter
from odylith.runtime.surfaces import tooling_dashboard_shell_presenter


def test_build_latest_packet_summary_preserves_explicit_falsy_governance_fields() -> None:
    summary = presenter.build_latest_packet_summary(
        {
            "workstream": "B-072",
            "packet_state": "gated_ambiguous",
            "execution_governance_present": True,
            "execution_governance_outcome": "defer",
            "execution_governance_mode": "verify",
            "execution_governance_current_phase": "status_synthesis",
            "execution_governance_next_move": "verify.selected_matrix",
            "execution_governance_blocker": "waiting for rollout evidence",
            "execution_governance_closure": "incomplete",
            "execution_governance_wait_status": "",
            "execution_governance_resume_token": "",
            "execution_governance_validation_archetype": "deploy",
            "execution_governance_validation_minimum_pass_count": 6,
            "execution_governance_validation_derived_from": ("mode:verify", "closure:incomplete"),
            "execution_governance_contradiction_count": 0,
            "execution_governance_history_rule_count": 2,
            "execution_governance_history_rule_hits": ("partial_scope_requires_closure",),
            "execution_governance_pressure_signals": ("denials:2",),
            "execution_governance_nearby_denial_actions": ("explore.broad_reset",),
            "execution_governance_authoritative_lane": "context_engine.governance_slice.authoritative",
            "execution_governance_host_family": "claude",
            "execution_governance_host_supports_native_spawn": False,
            "execution_governance_target_lane": "consumer",
            "execution_governance_candidate_target_count": 2,
            "execution_governance_diagnostic_anchor_count": 1,
            "execution_governance_has_writable_targets": False,
            "execution_governance_requires_more_consumer_context": False,
            "execution_governance_consumer_failover": "",
            "execution_governance_commentary_mode": "task_first_minimal",
            "execution_governance_runtime_invalidated_by_step": "render_compass_dashboard",
            "execution_governance_requires_reanchor": False,
            "estimated_tokens": 321,
            "packet_strategy": "balanced",
            "budget_mode": "balanced",
            "retrieval_focus": "expand_coverage",
            "speed_mode": "balanced",
            "reliability": "guarded",
            "packet_alignment_state": "aligned",
            "advised_yield_state": "wasteful",
        }
    )

    assert summary["present"] is True
    assert summary["host_supports_native_spawn_known"] is True
    assert summary["host_supports_native_spawn"] is False
    assert summary["requires_more_consumer_context_known"] is True
    assert summary["requires_more_consumer_context"] is False
    assert summary["has_writable_targets_known"] is True
    assert summary["has_writable_targets"] is False
    assert summary["validation_derived_from"] == ["mode:verify", "closure:incomplete"]
    assert summary["history_rule_hits"] == ["partial_scope_requires_closure"]
    assert summary["pressure_signals"] == ["denials:2"]
    assert summary["nearby_denial_actions"] == ["explore.broad_reset"]
    assert summary["runtime_invalidated_by_step"] == "render_compass_dashboard"
    assert summary["requires_reanchor"] is False


def test_render_latest_packet_html_surfaces_pressure_resume_and_denied_moves() -> None:
    html = presenter.render_latest_packet_html(
        presenter.build_latest_packet_summary(
            {
                "workstream": "B-072",
                "execution_governance_present": True,
                "execution_governance_outcome": "deny",
                "execution_governance_mode": "recover",
                "execution_governance_next_move": "recover.current_blocker",
                "execution_governance_current_phase": "recover",
                "execution_governance_last_successful_phase": "submit",
                "execution_governance_blocker": "waiting approval",
                "execution_governance_closure": "safe",
                "execution_governance_wait_status": "awaiting_callback",
                "execution_governance_wait_detail": "github actions run 991",
                "execution_governance_resume_token": "resume:B-072",
                "execution_governance_validation_archetype": "recover",
                "execution_governance_validation_derived_from": ["mode:recover"],
                "execution_governance_authoritative_lane": "context_engine.governance_slice.authoritative",
                "execution_governance_history_rule_hits": ["lane_drift_preflight"],
                "execution_governance_pressure_signals": ["wait:awaiting_callback", "denials:2"],
                "execution_governance_nearby_denial_actions": ["explore.broad_reset"],
                "execution_governance_runtime_invalidated_by_step": "render_compass_dashboard",
                "execution_governance_host_family": "claude",
                "execution_governance_host_supports_native_spawn": False,
                "execution_governance_target_lane": "dev_maintainer",
                "execution_governance_requires_more_consumer_context": True,
                "execution_governance_consumer_failover": "maintainer_ready_feedback_plus_bounded_narrowing",
                "execution_governance_requires_reanchor": True,
            }
        )
    )

    assert "Latest Governed Packet" in html
    assert "recover.current_blocker" in html
    assert "waiting approval" in html
    assert "wait:awaiting_callback" in html
    assert "Resume via `resume:B-072`." in html
    assert "Prefer `explore.broad_reset` only after the current frontier changes." in html
    assert "Runtime invalidated by `render_compass_dashboard`." in html
    assert "Serial host execution" in html


def test_shell_curated_status_html_includes_latest_governed_packet_card() -> None:
    html = tooling_dashboard_shell_presenter._render_curated_system_status_html(
        {
            "status": "ready",
            "latest_packet": presenter.build_latest_packet_summary(
                {
                    "workstream": "B-072",
                    "execution_governance_present": True,
                    "execution_governance_outcome": "admit",
                    "execution_governance_mode": "implement",
                    "execution_governance_next_move": "implement.target_scope",
                    "execution_governance_validation_archetype": "generic",
                    "execution_governance_authoritative_lane": "context_engine.governance_slice.authoritative",
                }
            ),
        }
    )

    assert "Telemetry Snapshot" in html
    assert "Latest Governed Packet" in html
    assert "implement.target_scope" in html
    assert "context_engine.governance_slice.authoritative" in html
