from __future__ import annotations

from pathlib import Path

from odylith.runtime.reasoning import remediator


def _dossier(
    *,
    case_id: str,
    scenario: str,
    code_references: list[str] | None = None,
    changed_artifacts: list[str] | None = None,
    render_drift: bool = False,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "subject": {"label": case_id},
        "decision_at_stake": f"Decision for {case_id}",
        "baseline": {"primary_scenario": scenario},
        "observations": {
            "code_references": code_references or [],
            "changed_artifacts": changed_artifacts or [],
            "render_drift": render_drift,
        },
    }


def _adjudication(case_id: str) -> dict[str, object]:
    return {
        "outcome_id": f"outcome-{case_id}",
    }


def _prescriber(case_id: str) -> dict[str, object]:
    return {
        "claim": f"Resolve {case_id}",
    }


def test_compile_correction_packet_returns_deterministic_refresh_for_render_drift(tmp_path: Path) -> None:
    packet = remediator.compile_correction_packet(
        repo_root=tmp_path,
        dossier=_dossier(
            case_id="case-render",
            scenario="stale_authority",
            code_references=["src/odylith/runtime/surfaces/render_tooling_dashboard.py"],
            changed_artifacts=["odylith/index.html"],
            render_drift=True,
        ),
        adjudication=_adjudication("case-render"),
        prescriber=_prescriber("case-render"),
    )

    assert packet["execution_mode"] == "deterministic"
    assert packet["commands"]
    assert packet["execution_governance"]["admissibility"]["outcome"] == "admit"
    assert packet["execution_governance"]["contract"]["authoritative_lane"] == "reasoning.remediator.authoritative"


def test_compile_correction_packet_returns_ai_engine_for_evaluator_changes(tmp_path: Path) -> None:
    packet = remediator.compile_correction_packet(
        repo_root=tmp_path,
        dossier=_dossier(
            case_id="case-b061",
            scenario="unsafe_closeout",
            code_references=["src/odylith/runtime/reasoning/odylith_reasoning.py"],
            changed_artifacts=["odylith/runtime/odylith-reasoning.v4.json"],
        ),
        adjudication=_adjudication("case-b061"),
        prescriber=_prescriber("case-b061"),
    )

    assert packet["execution_mode"] == "ai_engine"
    assert packet["ai_handoff"]["allowed_paths"]
    assert packet["execution_governance"]["admissibility"]["outcome"] == "admit"
    assert packet["execution_governance"]["contract"]["host_profile"]["host_family"]


def test_compile_correction_packet_returns_hybrid_for_semantic_closeout_dispute(tmp_path: Path) -> None:
    packet = remediator.compile_correction_packet(
        repo_root=tmp_path,
        dossier=_dossier(
            case_id="case-b033",
            scenario="unsafe_closeout",
            code_references=["src/odylith/runtime/surfaces/render_backlog_ui.py"],
            changed_artifacts=["odylith/radar/traceability-graph.v1.json"],
        ),
        adjudication=_adjudication("case-b033"),
        prescriber=_prescriber("case-b033"),
    )

    assert packet["execution_mode"] == "hybrid"
    assert packet["commands"]
    assert packet["ai_handoff"]["allowed_paths"]
    assert packet["execution_governance"]["validation_matrix"]["archetype"] == "generic"


def test_compile_correction_packet_returns_manual_when_no_bounded_fix_exists(tmp_path: Path) -> None:
    packet = remediator.compile_correction_packet(
        repo_root=tmp_path,
        dossier=_dossier(
            case_id="case-manual",
            scenario="clear_path",
        ),
        adjudication=_adjudication("case-manual"),
        prescriber=_prescriber("case-manual"),
    )

    assert packet["execution_mode"] == "manual"
    assert packet["commands"] == []
    assert packet["execution_governance"]["contract"]["execution_mode"] == "recover"


def test_packet_summary_exposes_execution_governance_posture(tmp_path: Path) -> None:
    packet = remediator.compile_correction_packet(
        repo_root=tmp_path,
        dossier=_dossier(
            case_id="case-summary",
            scenario="stale_authority",
            code_references=["src/odylith/runtime/surfaces/render_tooling_dashboard.py"],
            changed_artifacts=["odylith/index.html"],
            render_drift=True,
        ),
        adjudication=_adjudication("case-summary"),
        prescriber=_prescriber("case-summary"),
    )

    summary = remediator.packet_summary(packet)

    assert summary["execution_governance_outcome"] == "admit"
    assert summary["execution_governance_mode"] == "implement"
    assert summary["execution_governance_authoritative_lane"] == "reasoning.remediator.authoritative"


def test_apply_deterministic_packet_refuses_non_admissible_execution(tmp_path: Path) -> None:
    packet = {
        "id": "pkt-case-deny",
        "execution_mode": "deterministic",
        "commands": [["/usr/bin/true"]],
        "execution_governance": {
            "admissibility": {
                "outcome": "deny",
                "rationale": "action is outside the contract's allowed move set",
            }
        },
    }

    result = remediator.apply_deterministic_packet(repo_root=tmp_path, packet=packet)

    assert result["ok"] is False
    assert result["returncode"] == 2
    assert "not admissible" in result["error"]
