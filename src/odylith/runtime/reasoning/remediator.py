"""Compile approval-gated remediation packets for Odylith Tribunal cases.

Remediator is intentionally conservative:
- it compiles only bounded, reviewable packets;
- deterministic execution is limited to known local script flows;
- semantic code changes are delegated through backend-agnostic AI-engine
  packets instead of being executed implicitly;
- packets carry validation, rollback, and stale-detection metadata so Odylith
  can fail closed when the case facts drift after approval.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

from odylith.runtime.common.command_surface import display_command
from odylith.runtime.context_engine import execution_engine_handshake
from odylith.runtime.execution_engine import policy as execution_policy
from odylith.runtime.execution_engine import resource_closure as execution_resource_closure
from odylith.runtime.execution_engine import runtime_surface_governance
from odylith.runtime.execution_engine import validation as execution_validation
from odylith.runtime.execution_engine.contract import ExecutionContract
from odylith.runtime.execution_engine.contract import detect_execution_host_profile


DEFAULT_DECISION_LEDGER_PATH = "odylith/runtime/odylith-decisions.v1.jsonl"
EXECUTION_MODES: frozenset[str] = frozenset({"deterministic", "ai_engine", "hybrid", "manual"})
_EVALUATOR_PATH_PREFIXES: tuple[str, ...] = (
    "src/odylith/runtime/governance/delivery_intelligence_engine.py",
    "src/odylith/runtime/reasoning/odylith_reasoning.py",
    "src/odylith/runtime/governance/sync_workstream_artifacts.py",
    "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
    "src/odylith/runtime/context_engine/odylith_context_engine.py",
)


def _dedupe_paths(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _packet_fingerprint(case_id: str, outcome_id: str, mode: str, touched_paths: Sequence[str], goal: str) -> str:
    payload = {
        "case_id": case_id,
        "outcome_id": outcome_id,
        "mode": mode,
        "touched_paths": list(touched_paths),
        "goal": goal,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _looks_like_evaluator_change(paths: Sequence[str]) -> bool:
    for raw in paths:
        token = str(raw or "").strip()
        if any(token == prefix or token.startswith(prefix) for prefix in _EVALUATOR_PATH_PREFIXES):
            return True
    return False


def _packet_primary_action(mode: str) -> str:
    if mode == "deterministic":
        return "implement.packet_commands"
    if mode == "ai_engine":
        return "implement.ai_packet"
    if mode == "hybrid":
        return "implement.packet_commands"
    return "manual.review"


def _packet_allowed_moves(mode: str) -> list[str]:
    moves = ["re_anchor", "verify.packet_validation"]
    if mode in {"deterministic", "hybrid"}:
        moves.append("implement.packet_commands")
    if mode in {"ai_engine", "hybrid"}:
        moves.append("implement.ai_packet")
    if mode == "manual":
        moves.append("manual.review")
    return moves


def _packet_forbidden_moves(mode: str) -> list[str]:
    moves = ["implement.unbounded_scope"]
    if mode == "manual":
        moves.extend(("implement.packet_commands", "implement.ai_packet"))
    return moves


def _packet_execution_engine(packet: Mapping[str, Any]) -> dict[str, Any]:
    mode = str(packet.get("execution_mode", "manual")).strip() or "manual"
    case_id = str(packet.get("case_id", "")).strip() or "case"
    goal = str(packet.get("goal", "")).strip() or f"Execute the approved remediation packet for {case_id}."
    touched_paths = _dedupe_paths(
        [str(token).strip() for token in packet.get("touched_paths", []) if str(token).strip()]
    )
    target_scope = touched_paths or [case_id]
    host_profile = detect_execution_host_profile()
    contract = ExecutionContract.create(
        objective=goal,
        authoritative_lane="reasoning.remediator.authoritative",
        target_scope=target_scope,
        environment="repo_local",
        resource_set=target_scope,
        success_criteria=_dedupe_paths(
            [
                str(token).strip()
                for token in packet.get("expected_evidence_after_success", [])
                if str(token).strip()
            ]
        )
        or [goal],
        validation_plan=_dedupe_paths(
            [str(token).strip() for token in packet.get("validation_steps", []) if str(token).strip()]
        )
        or ["verify.packet_validation"],
        allowed_moves=_packet_allowed_moves(mode),
        forbidden_moves=_packet_forbidden_moves(mode),
        external_dependencies=[],
        critical_path=[mode, *target_scope[:2]],
        host_profile=host_profile,
        execution_mode="recover" if mode == "manual" else "implement",
    )
    action = _packet_primary_action(mode)
    closure = execution_resource_closure.classify_resource_closure(target_scope)
    validation_matrix = execution_validation.synthesize_validation_matrix(contract)
    admissibility = execution_policy.evaluate_admissibility(
        contract,
        action,
        requested_scope=target_scope,
    )
    return {
        "contract": contract.to_dict(),
        "admissibility": admissibility.to_dict(),
        "resource_closure": closure.to_dict(),
        "validation_matrix": validation_matrix.to_dict(),
    }


def _with_execution_engine(packet: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(packet)
    payload["execution_engine"] = _packet_execution_engine(payload)
    return payload


def _sync_packet(*, case_id: str, outcome_id: str, touched_paths: Sequence[str], goal: str) -> dict[str, Any]:
    fingerprint = _packet_fingerprint(case_id, outcome_id, "deterministic", touched_paths, goal)
    return _with_execution_engine({
        "id": f"pkt-{case_id}",
        "fingerprint": fingerprint,
        "case_id": case_id,
        "outcome_id": outcome_id,
        "execution_mode": "deterministic",
        "approval_scope": "operator",
        "goal": goal,
        "preconditions": [
            "The dossier fingerprint still matches the approved packet fingerprint.",
            "The touched path set is still limited to render/runtime artifact refresh scope.",
        ],
        "touched_paths": list(touched_paths),
        "commands": [
            ["odylith", "sync", "--repo-root", ".", "--force"],
        ],
        "ai_handoff": {},
        "validation_steps": [
            display_command("sync", "--repo-root", ".", "--check-only", "--check-clean"),
        ],
        "rollback_steps": [
            "Revert the touched generated artifacts and rerun sync validation.",
        ],
        "stale_conditions": [
            "Case dossier fingerprint changes after approval.",
            "Touched path set expands beyond the approved refresh scope.",
        ],
        "expected_evidence_after_success": [
            "Rendered artifacts and runtime snapshots validate cleanly.",
            "No stale generated workstream surfaces remain in git status.",
        ],
        "status": "draft",
    })


def _traceability_packet(*, case_id: str, outcome_id: str, goal: str) -> dict[str, Any]:
    touched_paths = [
        "odylith/radar/source/ideas/",
        "odylith/radar/traceability-autofix-report.v1.json",
    ]
    fingerprint = _packet_fingerprint(case_id, outcome_id, "deterministic", touched_paths, goal)
    return _with_execution_engine({
        "id": f"pkt-{case_id}",
        "fingerprint": fingerprint,
        "case_id": case_id,
        "outcome_id": outcome_id,
        "execution_mode": "deterministic",
        "approval_scope": "operator",
        "goal": goal,
        "preconditions": [
            "Traceability metadata remains missing or stale for the approved case.",
            "The autofix report still contains no unresolved conflicts that require manual judgment.",
        ],
        "touched_paths": touched_paths,
        "commands": [
            ["odylith", "sync", "--repo-root", ".", "--force"],
        ],
        "ai_handoff": {},
        "validation_steps": [
            display_command("sync", "--repo-root", ".", "--check-only", "--check-clean"),
        ],
        "rollback_steps": [
            "Revert the touched backlog idea specs and traceability report, then rerun validation.",
        ],
        "stale_conditions": [
            "Traceability facts or path ownership changed after approval.",
        ],
        "expected_evidence_after_success": [
            "Traceability autofix report is current.",
            "Workstream artifacts validate cleanly after sync.",
        ],
        "status": "draft",
    })


def _ai_packet(
    *,
    case_id: str,
    outcome_id: str,
    goal: str,
    subject: str,
    touched_paths: Sequence[str],
    constraints: Sequence[str],
    validation_steps: Sequence[str],
    rollback_steps: Sequence[str],
) -> dict[str, Any]:
    fingerprint = _packet_fingerprint(case_id, outcome_id, "ai_engine", touched_paths, goal)
    return _with_execution_engine({
        "id": f"pkt-{case_id}",
        "fingerprint": fingerprint,
        "case_id": case_id,
        "outcome_id": outcome_id,
        "execution_mode": "ai_engine",
        "approval_scope": "operator",
        "goal": goal,
        "preconditions": [
            "The case still requires semantic judgment or code changes.",
            "The touched path allowlist remains valid for the approved scope.",
        ],
        "touched_paths": list(touched_paths),
        "commands": [],
        "ai_handoff": {
            "subject": subject,
            "goal": goal,
            "allowed_paths": list(touched_paths),
            "constraints": list(constraints),
            "validation_steps": list(validation_steps),
            "rollback_steps": list(rollback_steps),
        },
        "validation_steps": list(validation_steps),
        "rollback_steps": list(rollback_steps),
        "stale_conditions": [
            "Case dossier fingerprint changes after approval.",
            "Touched path set expands beyond the approved allowlist.",
            "The configured AI engine is unavailable or untrusted at execution time.",
        ],
        "expected_evidence_after_success": [
            "Allowed paths contain the full semantic fix.",
            "Validation steps pass on the updated implementation.",
        ],
        "status": "draft",
    })


def _hybrid_packet(
    *,
    case_id: str,
    outcome_id: str,
    goal: str,
    subject: str,
    touched_paths: Sequence[str],
    constraints: Sequence[str],
) -> dict[str, Any]:
    fingerprint = _packet_fingerprint(case_id, outcome_id, "hybrid", touched_paths, goal)
    return _with_execution_engine({
        "id": f"pkt-{case_id}",
        "fingerprint": fingerprint,
        "case_id": case_id,
        "outcome_id": outcome_id,
        "execution_mode": "hybrid",
        "approval_scope": "operator",
        "goal": goal,
        "preconditions": [
            "The deterministic narrowing step still applies to the current case facts.",
            "The semantic change remains bounded to the approved allowlist after the deterministic prep step.",
        ],
        "touched_paths": list(touched_paths),
        "commands": [
            ["odylith", "sync", "--repo-root", ".", "--check-only", "--check-clean"],
        ],
        "ai_handoff": {
            "subject": subject,
            "goal": goal,
            "allowed_paths": list(touched_paths),
            "constraints": list(constraints),
            "validation_steps": [
                "python -m pytest tests/unit/runtime -q",
            ],
            "rollback_steps": [
                "Revert only the touched allowlisted files and rerun validation.",
            ],
        },
        "validation_steps": [
            "python -m pytest tests/unit/runtime -q",
        ],
        "rollback_steps": [
            "Revert the allowlisted files and rerun the validation steps.",
        ],
        "stale_conditions": [
            "Deterministic prep changes the touched-path scope materially.",
            "Case dossier fingerprint changes after approval.",
        ],
        "expected_evidence_after_success": [
            "Deterministic prep stays clean and the delegated semantic fix validates.",
        ],
        "status": "draft",
    })


def compile_correction_packet(
    *,
    repo_root: Path,
    dossier: Mapping[str, Any],
    adjudication: Mapping[str, Any],
    prescriber: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile one bounded correction packet for an adjudicated case."""

    case_id = str(dossier.get("case_id", "")).strip() or "case"
    outcome_id = str(adjudication.get("outcome_id", "")).strip() or f"outcome-{case_id}"
    subject = str(dossier.get("subject", {}).get("label", "")).strip() if isinstance(dossier.get("subject"), Mapping) else case_id
    observations = dossier.get("observations", {}) if isinstance(dossier.get("observations"), Mapping) else {}
    touched_paths = _dedupe_paths(
        [
            *(
                observations.get("code_references", [])
                if isinstance(observations.get("code_references"), list)
                else []
            ),
            *(
                observations.get("changed_artifacts", [])
                if isinstance(observations.get("changed_artifacts"), list)
                else []
            ),
        ]
    )
    scenario = str(dossier.get("baseline", {}).get("primary_scenario", "")).strip() if isinstance(dossier.get("baseline"), Mapping) else ""
    prescriber_claim = str(prescriber.get("claim", "")).strip()
    decision_at_stake = str(dossier.get("decision_at_stake", "")).strip()

    deterministic_refresh = bool(observations.get("render_drift", False)) or (
        scenario in {"stale_authority", "cross_surface_conflict"}
        and not _looks_like_evaluator_change(touched_paths)
        and any(
            token.startswith(("odylith/", "odylith/atlas/source/", "src/odylith/runtime/surfaces/render_"))
            for token in touched_paths
        )
    )
    if deterministic_refresh:
        return _sync_packet(
            case_id=case_id,
            outcome_id=outcome_id,
            touched_paths=touched_paths or ["odylith/", "odylith/atlas/source/"],
            goal=prescriber_claim or f"Refresh the impacted derived surfaces for {subject}.",
        )

    traceability_candidate = any(token.startswith("odylith/radar/source/ideas/") for token in touched_paths) and scenario == "orphan_activity"
    if traceability_candidate:
        return _traceability_packet(
            case_id=case_id,
            outcome_id=outcome_id,
            goal=prescriber_claim or f"Backfill missing traceability metadata for {subject}.",
        )

    if _looks_like_evaluator_change(touched_paths):
        return _ai_packet(
            case_id=case_id,
            outcome_id=outcome_id,
            goal=prescriber_claim or f"Make the evaluator trust semantics for {subject} explicit.",
            subject=subject,
            touched_paths=touched_paths or list(_EVALUATOR_PATH_PREFIXES),
            constraints=[
                "Preserve approval-gated behavior.",
                "Keep product language backend-agnostic.",
                "Do not hand-edit generated artifacts.",
            ],
            validation_steps=[
                "python -m pytest tests/unit/runtime -q",
            ],
            rollback_steps=[
                "Revert the touched evaluator files only and rerun validation.",
            ],
        )

    if scenario in {"unsafe_closeout", "cross_surface_conflict", "false_priority"} and touched_paths:
        return _hybrid_packet(
            case_id=case_id,
            outcome_id=outcome_id,
            goal=prescriber_claim or f"Resolve the ownership or authority ambiguity for {subject}.",
            subject=subject,
            touched_paths=touched_paths,
            constraints=[
                f"Keep the change bounded to the case decision: {decision_at_stake or subject}.",
                "Do not mutate approval or clearance state directly.",
            ],
        )

    fingerprint = _packet_fingerprint(case_id, outcome_id, "manual", touched_paths, prescriber_claim or decision_at_stake)
    return _with_execution_engine({
        "id": f"pkt-{case_id}",
        "fingerprint": fingerprint,
        "case_id": case_id,
        "outcome_id": outcome_id,
        "execution_mode": "manual",
        "approval_scope": "operator",
        "goal": prescriber_claim or decision_at_stake or f"Resolve the remaining ambiguity for {subject}.",
        "preconditions": [
            "The case still lacks a bounded deterministic or delegated fix path.",
        ],
        "touched_paths": list(touched_paths),
        "commands": [],
        "ai_handoff": {},
        "validation_steps": [
            "Open proof and complete the discriminating check manually.",
        ],
        "rollback_steps": [
            "No automated rollback; the operator must decide the next state manually.",
        ],
        "stale_conditions": [
            "Case dossier fingerprint changes before manual review completes.",
        ],
        "expected_evidence_after_success": [
            "The manual check either resolves the case or reopens it with stronger evidence.",
        ],
        "status": "draft",
    })


def packet_summary(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Return the small packet shape Odylith needs for posture and UI surfaces."""

    execution_engine = {}
    if isinstance(packet.get("execution_engine"), Mapping):
        execution_engine = execution_engine_handshake.compact_execution_engine_snapshot_for_packet(
            payload=packet,
            context_packet={},
        )
    execution_summary = runtime_surface_governance.summary_fields_from_execution_engine(
        execution_engine
    )
    summary = {
        "id": str(packet.get("id", "")).strip(),
        "case_id": str(packet.get("case_id", "")).strip(),
        "outcome_id": str(packet.get("outcome_id", "")).strip(),
        "fingerprint": str(packet.get("fingerprint", "")).strip(),
        "execution_mode": str(packet.get("execution_mode", "manual")).strip() or "manual",
        "goal": str(packet.get("goal", "")).strip(),
        "approval_scope": str(packet.get("approval_scope", "operator")).strip() or "operator",
        "touched_paths": [
            str(token).strip()
            for token in packet.get("touched_paths", [])
            if str(token).strip()
        ],
        "status": str(packet.get("status", "draft")).strip() or "draft",
    }
    summary.update(execution_summary)
    return summary


def apply_deterministic_packet(*, repo_root: Path, packet: Mapping[str, Any]) -> dict[str, Any]:
    """Execute one deterministic packet.

    The caller is responsible for approval checks. This function only runs
    packets already classified as deterministic and returns a structured result
    so the CLI or Odylith can record the outcome in the decision ledger.
    """

    mode = str(packet.get("execution_mode", "")).strip()
    if mode != "deterministic":
        return {
            "ok": False,
            "error": f"packet `{packet.get('id', '')}` is not deterministic",
            "returncode": 2,
        }

    commands = packet.get("commands", [])
    if not isinstance(commands, list) or not commands:
        return {
            "ok": False,
            "error": f"packet `{packet.get('id', '')}` has no deterministic commands",
            "returncode": 2,
        }

    execution_engine = (
        execution_engine_handshake.compact_execution_engine_snapshot_for_packet(
            payload=packet,
            context_packet={},
        )
        if isinstance(packet.get("execution_engine"), Mapping)
        else _packet_execution_engine(packet)
    )
    execution_summary = runtime_surface_governance.summary_fields_from_execution_engine(
        execution_engine
    )
    admissibility = (
        dict(execution_engine.get("admissibility", {}))
        if isinstance(execution_engine.get("admissibility"), Mapping)
        else {}
    )
    outcome = str(execution_summary.get("execution_engine_outcome", "")).strip() or str(
        admissibility.get("outcome", "")
    ).strip()
    if outcome not in {"", "admit"}:
        return {
            "ok": False,
            "error": (
                f"packet `{packet.get('id', '')}` is not admissible for deterministic execution: "
                f"{str(admissibility.get('rationale', '')).strip() or 'contract denied execution'}"
            ),
            "returncode": 2,
            "execution_engine": execution_engine,
        }

    for command in commands:
        if not isinstance(command, list) or not command:
            return {
                "ok": False,
                "error": f"packet `{packet.get('id', '')}` contains an invalid command entry",
                "returncode": 2,
            }
        completed = subprocess.run(command, cwd=str(repo_root), check=False, text=True)
        if completed.returncode != 0:
            return {
                "ok": False,
                "error": f"command failed: {' '.join(command)}",
                "returncode": int(completed.returncode),
            }

    return {
        "ok": True,
        "error": "",
        "returncode": 0,
        "execution_engine": execution_engine,
    }


__all__ = [
    "DEFAULT_DECISION_LEDGER_PATH",
    "EXECUTION_MODES",
    "apply_deterministic_packet",
    "compile_correction_packet",
    "packet_summary",
]
