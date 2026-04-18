"""Program Wave Execution Engine helpers for the Odylith governance layer."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.execution_engine.contract import ContradictionRecord
from odylith.runtime.governance import authoring_execution_policy
from odylith.runtime.governance import execution_wave_contract
from odylith.runtime.governance import validate_backlog_contract as backlog_contract

_ROLE_TO_FIELD = {
    "primary": "primary_workstreams",
    "carried": "carried_workstreams",
    "in_band": "in_band_workstreams",
}


def _metadata_list(spec: backlog_contract.IdeaSpec, key: str) -> list[str]:
    raw = str(spec.metadata.get(key, "")).strip()
    if not raw:
        return []
    return [token.strip() for token in raw.split(",") if token.strip()]


def _governed_child_scope(umbrella_spec: backlog_contract.IdeaSpec) -> list[str]:
    umbrella_id = str(umbrella_spec.metadata.get("idea_id", "")).strip()
    return [umbrella_id, *_metadata_list(umbrella_spec, "workstream_children")]


def _find_wave(document: Mapping[str, Any], wave_id: str) -> dict[str, Any]:
    token = str(wave_id or "").strip()
    for wave in document.get("waves", []):
        if isinstance(wave, Mapping) and str(wave.get("wave_id", "")).strip() == token:
            return dict(wave)
    raise ValueError(f"unknown wave `{wave_id}`")


def _wave_member_ids(wave: Mapping[str, Any]) -> list[str]:
    members: list[str] = []
    for field_name in _ROLE_TO_FIELD.values():
        for item in wave.get(field_name, []):
            token = str(item or "").strip()
            if token and token not in members:
                members.append(token)
    return members


def _program_dependency_contradictions(
    *,
    document: Mapping[str, Any],
    activate_wave: str,
) -> tuple[ContradictionRecord, ...]:
    target_wave = str(activate_wave or "").strip()
    if not target_wave:
        return ()
    wave = _find_wave(document, target_wave)
    completed_wave_ids = {
        str(row.get("wave_id", "")).strip()
        for row in document.get("waves", [])
        if isinstance(row, Mapping) and str(row.get("status", "")).strip() == "complete"
    }
    missing = [dep for dep in wave.get("depends_on", []) if str(dep).strip() not in completed_wave_ids]
    if not missing:
        return ()
    dependency_label = ", ".join(str(item).strip() for item in missing if str(item).strip())
    return (
        ContradictionRecord(
            source="program_state",
            claim=f"wave `{target_wave}` depends on `{dependency_label}`",
            conflicting_evidence=f"intended action activates `{target_wave}` before dependency closure",
            severity="high",
            blocks_execution=True,
        ),
    )


def program_governance_decision(
    *,
    repo_root: Path,
    umbrella_spec: backlog_contract.IdeaSpec,
    document: Mapping[str, Any],
    args: argparse.Namespace,
) -> authoring_execution_policy.GovernedAuthoringDecision:
    umbrella_id = str(umbrella_spec.metadata.get("idea_id", "")).strip()
    governed_scope = _governed_child_scope(umbrella_spec)
    action = f"mutate_program_{str(args.program_command).strip().replace('-', '_')}"
    extra_contradictions = ()
    if str(args.program_command).strip() == "update" and str(args.activate_wave or "").strip():
        extra_contradictions = _program_dependency_contradictions(
            document=document,
            activate_wave=str(args.activate_wave or "").strip(),
        )
    return authoring_execution_policy.evaluate_governed_authoring_action(
        action=action,
        objective=f"Maintain the authoritative execution-wave program for umbrella `{umbrella_id}`.",
        authoritative_lane="governance.program_wave.authoritative",
        target_scope=governed_scope or [umbrella_id],
        requested_scope=[umbrella_id],
        governed_scope=governed_scope or [umbrella_id],
        resource_set=[
            execution_wave_contract.program_relative_path(umbrella_id),
            str(umbrella_spec.path.relative_to(repo_root)),
        ],
        success_criteria=[
            f"execution-wave program for `{umbrella_id}` stays authoritative",
            "umbrella metadata stays aligned with the execution-wave source contract",
        ],
        validation_plan=["odylith validate backlog-contract --repo-root ."],
        allowed_moves=[action, "re_anchor"],
        critical_path=[action, "validate_backlog_contract"],
        extra_contradictions=extra_contradictions,
        preferred_alternative=f"odylith program status {umbrella_id}",
    )


def wave_governance_decision(
    *,
    repo_root: Path,
    umbrella_spec: backlog_contract.IdeaSpec,
    document: Mapping[str, Any],
    args: argparse.Namespace,
) -> authoring_execution_policy.GovernedAuthoringDecision:
    umbrella_id = str(umbrella_spec.metadata.get("idea_id", "")).strip()
    action = f"mutate_wave_{str(args.wave_command).strip().replace('-', '_')}"
    requested_scope = [umbrella_id]
    governed_scope = _governed_child_scope(umbrella_spec) or [umbrella_id]
    preferred_alternative = f"odylith wave status {umbrella_id} {str(args.wave_id or '').strip()}"
    if str(args.wave_command).strip() in {"update", "unassign", "gate-add", "gate-remove"}:
        wave = _find_wave(document, args.wave_id)
        if str(args.wave_command).strip() == "unassign":
            workstream_id = str(args.workstream_id or "").strip().upper()
            requested_scope = [umbrella_id, workstream_id]
            governed_scope = [umbrella_id, *_wave_member_ids(wave)]
        elif str(args.wave_command).strip() == "gate-add":
            workstream_id = str(args.workstream_id or "").strip().upper()
            requested_scope = [umbrella_id, workstream_id]
            governed_scope = [umbrella_id, *_wave_member_ids(wave)]
            preferred_alternative = f"odylith wave assign {umbrella_id} {str(args.wave_id).strip()} {workstream_id} --role primary"
        elif str(args.wave_command).strip() == "gate-remove":
            workstream_id = str(args.workstream_id or "").strip().upper()
            requested_scope = [umbrella_id, workstream_id]
            governed_scope = [
                umbrella_id,
                *[
                    str(row.get("workstream_id", "")).strip()
                    for row in wave.get("gate_refs", [])
                    if isinstance(row, Mapping) and str(row.get("workstream_id", "")).strip()
                ],
            ]
    if str(args.wave_command).strip() == "assign":
        workstream_id = str(args.workstream_id or "").strip().upper()
        requested_scope = [umbrella_id, workstream_id]
        governed_scope = _governed_child_scope(umbrella_spec) or [umbrella_id]
        preferred_alternative = f"odylith program status {umbrella_id}"
    return authoring_execution_policy.evaluate_governed_authoring_action(
        action=action,
        objective=f"Maintain the authoritative wave membership and gate posture for umbrella `{umbrella_id}`.",
        authoritative_lane="governance.program_wave.authoritative",
        target_scope=governed_scope,
        requested_scope=requested_scope,
        governed_scope=governed_scope,
        resource_set=[
            execution_wave_contract.program_relative_path(umbrella_id),
            str(umbrella_spec.path.relative_to(repo_root)),
        ],
        success_criteria=[
            f"wave posture for `{umbrella_id}` remains authoritative",
            "wave mutations stay inside the governed umbrella scope",
        ],
        validation_plan=["odylith validate backlog-contract --repo-root ."],
        allowed_moves=[action, "re_anchor"],
        critical_path=[action, "validate_backlog_contract"],
        preferred_alternative=preferred_alternative,
    )
