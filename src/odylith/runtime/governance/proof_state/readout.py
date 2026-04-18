"""Readout helpers for the Odylith governance proof state layer."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .contract import WORK_CATEGORIES
from .contract import normalize_proof_state


def proof_resolution_message(proof_state_resolution: Mapping[str, Any] | Any) -> str:
    resolution = dict(proof_state_resolution) if isinstance(proof_state_resolution, Mapping) else {}
    state = str(resolution.get("state", "")).strip().lower()
    lane_ids = [
        str(token).strip()
        for token in resolution.get("lane_ids", [])
        if str(token).strip()
    ] if isinstance(resolution.get("lane_ids"), list) else []
    if state == "ambiguous":
        suffix = f": {', '.join(lane_ids)}" if lane_ids else ""
        return f"Proof state is ambiguous across multiple blocker lanes{suffix}."
    if state == "none":
        return "No dominant proof lane is resolved for this scope yet."
    return ""


def proof_drift_warning(proof_state: Mapping[str, Any] | Any) -> str:
    state = normalize_proof_state(proof_state)
    status = str(state.get("proof_status", "")).strip()
    if status in {"", "live_verified"}:
        return ""
    categories = [
        str(token).strip()
        for token in state.get("recent_work_categories", [])
        if str(token).strip() in WORK_CATEGORIES
    ]
    if not categories:
        return ""
    non_primary = [token for token in categories if token != "primary_blocker"]
    if len(non_primary) <= len(categories) // 2:
        return ""
    blocker = str(state.get("current_blocker", "the current blocker")).strip() or "the current blocker"
    return f"Recent activity is skewing away from the primary blocker while {blocker} is still open."


def proof_reopen_signal(proof_state: Mapping[str, Any] | Any) -> dict[str, Any]:
    state = normalize_proof_state(proof_state)
    fingerprint = str(state.get("failure_fingerprint", "")).strip()
    last_falsification = (
        dict(state.get("last_falsification", {}))
        if isinstance(state.get("last_falsification"), Mapping)
        else {}
    )
    falsified_fingerprint = str(last_falsification.get("failure_fingerprint", "")).strip()
    if not fingerprint or not falsified_fingerprint or fingerprint != falsified_fingerprint:
        return {}
    blocker = str(state.get("current_blocker", "the current blocker")).strip() or "the current blocker"
    linked_bug_id = str(state.get("linked_bug_id", "")).strip()
    repeated_count = max(1, int(state.get("repeated_fingerprint_count", 0) or 0))
    summary = f"Previous fix did not clear the live blocker; keep {blocker} pinned as the active seam."
    if linked_bug_id:
        summary += f" Reuse Casebook bug {linked_bug_id} rather than opening a new blocker record."
    return {
        "same_fingerprint_reopened": True,
        "linked_bug_id": linked_bug_id,
        "repeated_fingerprint_count": repeated_count,
        "summary": summary,
    }


def proof_highlights(proof_state: Mapping[str, Any] | Any) -> list[str]:
    state = normalize_proof_state(proof_state)
    rows: list[str] = []
    blocker = str(state.get("current_blocker", "")).strip()
    if blocker:
        rows.append(f"Current blocker: {blocker}")
    fingerprint = str(state.get("failure_fingerprint", "")).strip()
    if fingerprint:
        rows.append(f"Failure fingerprint: {fingerprint}")
    phase = str(state.get("frontier_phase", "")).strip()
    if phase:
        rows.append(f"Frontier: {phase}")
    evidence_tier = str(state.get("evidence_tier", "")).strip()
    if evidence_tier:
        rows.append(f"Evidence tier: {evidence_tier.replace('_', ' ')}")
    reopen = proof_reopen_signal(state)
    if reopen:
        rows.append(str(reopen.get("summary", "")).strip())
    warning = proof_drift_warning(state)
    if warning:
        rows.append(warning)
    return rows[:4]


def proof_preview_lines(
    proof_state: Mapping[str, Any] | Any,
    *,
    compact: bool = False,
    limit: int = 6,
) -> list[str]:
    state = normalize_proof_state(proof_state)
    if not state:
        return []

    rows: list[str] = []
    blocker = str(state.get("current_blocker", "")).strip()
    if blocker:
        rows.append(f"Current blocker: {blocker}")
    fingerprint = str(state.get("failure_fingerprint", "")).strip()
    if fingerprint:
        rows.append(f"Failure fingerprint: {fingerprint}")
    frontier = str(state.get("frontier_phase", "")).strip()
    if frontier:
        rows.append(f"Frontier: {frontier}")
    evidence_tier = str(state.get("evidence_tier", "")).strip()
    if evidence_tier:
        rows.append(f"Evidence tier: {evidence_tier.replace('_', ' ')}")
    if not compact:
        clearance = str(state.get("clearance_condition", "")).strip()
        if clearance:
            rows.append(f"Clear only when: {clearance}")
        last_falsification = (
            dict(state.get("last_falsification", {}))
            if isinstance(state.get("last_falsification"), Mapping)
            else {}
        )
        recorded_at = str(last_falsification.get("recorded_at", "")).strip()
        if recorded_at:
            rows.append(f"Last falsification: {recorded_at}")
    reopen = proof_reopen_signal(state)
    if reopen:
        rows.append(str(reopen.get("summary", "")).strip())
    warning = proof_drift_warning(state)
    if warning:
        rows.append(warning)
    return rows[: max(1, int(limit))]


def build_proof_refs(
    *,
    proof_state: Mapping[str, Any] | Any,
    scope_workstreams: Sequence[str],
) -> list[dict[str, str]]:
    state = normalize_proof_state(proof_state)
    rows: list[dict[str, str]] = []
    bug_id = str(state.get("linked_bug_id", "")).strip()
    workstream = next((str(token).strip() for token in scope_workstreams if str(token).strip()), "")
    fingerprint = str(state.get("failure_fingerprint", "")).strip()
    if bug_id:
        rows.append(
            {
                "kind": "bug",
                "value": bug_id,
                "label": "Current blocker",
                "surface": "casebook",
                "anchor": "current-blocker",
                "fact_tag": "blocker",
            }
        )
    if workstream:
        rows.append(
            {
                "kind": "workstream",
                "value": workstream,
                "label": "Proof frontier",
                "surface": "compass",
                "anchor": "timeline-audit",
                "fact_tag": "frontier",
            }
        )
    if fingerprint and bug_id:
        rows.append(
            {
                "kind": "bug",
                "value": bug_id,
                "label": "Last falsification",
                "surface": "casebook",
                "anchor": "last-falsification",
                "fact_tag": "falsification",
            }
        )
    if workstream:
        rows.append(
            {
                "kind": "workstream",
                "value": workstream,
                "label": "Deployment truth",
                "surface": "compass",
                "anchor": "current-workstreams",
                "fact_tag": "deployment_truth",
            }
        )
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (row.get("kind", ""), row.get("value", ""), row.get("label", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped[:4]
