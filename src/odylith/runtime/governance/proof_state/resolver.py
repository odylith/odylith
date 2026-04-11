from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from .contract import PROOF_STATUSES
from .contract import WORK_CATEGORIES
from .contract import build_claim_guard
from .contract import frontier_has_advanced
from .contract import normalize_deployment_truth
from .contract import normalize_proof_state
from .ledger import load_live_proof_lanes
from .ledger import persist_live_proof_lanes
from .readout import proof_drift_warning
from .readout import proof_reopen_signal


_BUG_METADATA_RE = re.compile(r"^-\s*([A-Za-z0-9/() _.`'-]+):\s*(.*)$")
_PLAN_METADATA_RE = re.compile(r"^([A-Za-z0-9/() _.`'-]+):\s*(.*)$")
_WORKSTREAM_RE = re.compile(r"\bB-\d{3,}\b")
_BUG_ID_RE = re.compile(r"\bCB-\d{3,}\b")
_SOURCE_PRECEDENCE = {"casebook": 0, "plan": 1, "inferred": 2}


def _normalize_token(value: Any) -> str:
    return str(value or "").strip()


def _parse_bug_fields(lines: Sequence[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    current_key = ""
    current_lines: list[str] = []
    for raw in lines:
        stripped = raw.rstrip()
        match = _BUG_METADATA_RE.match(stripped.strip())
        if match:
            if current_key:
                fields[current_key] = "\n".join(line.rstrip() for line in current_lines).strip()
            current_key = _normalize_token(match.group(1))
            initial = _normalize_token(match.group(2))
            current_lines = [initial] if initial else []
            continue
        if current_key:
            current_lines.append(stripped)
    if current_key:
        fields[current_key] = "\n".join(line.rstrip() for line in current_lines).strip()
    return fields


def _parse_plan_fields(lines: Sequence[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw in lines[:80]:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _PLAN_METADATA_RE.match(stripped)
        if match:
            fields[_normalize_token(match.group(1))] = _normalize_token(match.group(2))
    return fields


def _extract_workstreams(text: str) -> list[str]:
    return sorted({token.upper() for token in _WORKSTREAM_RE.findall(str(text or "").upper())})


def _current_local_head(repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return _normalize_token(completed.stdout)


def _bug_proof_rows(repo_root: Path) -> list[dict[str, Any]]:
    bug_root = repo_root / "odylith" / "casebook" / "bugs"
    rows: list[dict[str, Any]] = []
    if not bug_root.is_dir():
        return rows
    for path in sorted(bug_root.glob("*.md")):
        if path.name in {"INDEX.md", "AGENTS.md", "CLAUDE.md"}:
            continue
        text = path.read_text(encoding="utf-8")
        fields = _parse_bug_fields(text.splitlines())
        lane_id = _normalize_token(fields.get("Proof Lane ID"))
        blocker = _normalize_token(fields.get("Current Blocker"))
        fingerprint = _normalize_token(fields.get("Failure Fingerprint"))
        first_phase = _normalize_token(fields.get("First Failing Phase"))
        clearance = _normalize_token(fields.get("Clearance Condition"))
        proof_status = _normalize_token(fields.get("Current Proof Status"))
        if not any((lane_id, blocker, fingerprint, first_phase, clearance, proof_status)):
            continue
        workstreams = _extract_workstreams(
            "\n".join(
                token
                for token in (
                    fields.get("Linked Workstream", ""),
                    fields.get("Description", ""),
                    fields.get("Impact", ""),
                    fields.get("Trigger Path", ""),
                )
                if token
            )
        )
        rows.append(
            {
                "source": "casebook",
                "source_path": str(path.relative_to(repo_root)).replace("\\", "/"),
                "lane_id": lane_id or _normalize_token(fields.get("Bug ID")).replace("CB-", "lane-cb-").lower(),
                "linked_bug_id": _normalize_token(fields.get("Bug ID")),
                "current_blocker": blocker,
                "failure_fingerprint": fingerprint,
                "first_failing_phase": first_phase,
                "clearance_condition": clearance,
                "proof_status": proof_status if proof_status in PROOF_STATUSES else "diagnosed",
                "workstreams": workstreams,
                "raw_text": text,
            }
        )
    return rows


def _plan_proof_rows(repo_root: Path) -> list[dict[str, Any]]:
    plan_root = repo_root / "odylith" / "technical-plans"
    rows: list[dict[str, Any]] = []
    if not plan_root.is_dir():
        return rows
    for path in sorted(plan_root.rglob("*.md")):
        if path.name in {"INDEX.md", "AGENTS.md", "CLAUDE.md"}:
            continue
        text = path.read_text(encoding="utf-8")
        fields = _parse_plan_fields(text.splitlines())
        lane_id = _normalize_token(fields.get("Proof Lane ID"))
        blocker = _normalize_token(fields.get("Current Blocker"))
        fingerprint = _normalize_token(fields.get("Failure Fingerprint"))
        first_phase = _normalize_token(fields.get("First Failing Phase"))
        clearance = _normalize_token(fields.get("Clearance Condition"))
        proof_status = _normalize_token(fields.get("Current Proof Status"))
        if not any((lane_id, blocker, fingerprint, first_phase, clearance, proof_status)):
            continue
        backlog = _normalize_token(fields.get("Backlog"))
        rows.append(
            {
                "source": "plan",
                "source_path": str(path.relative_to(repo_root)).replace("\\", "/"),
                "lane_id": lane_id or backlog.lower().replace("B-", "lane-b-"),
                "linked_bug_id": "",
                "current_blocker": blocker,
                "failure_fingerprint": fingerprint,
                "first_failing_phase": first_phase,
                "clearance_condition": clearance,
                "proof_status": proof_status if proof_status in PROOF_STATUSES else "diagnosed",
                "workstreams": [backlog] if backlog else [],
                "raw_text": text,
            }
        )
    return rows


def _stream_proof_events(repo_root: Path) -> list[dict[str, Any]]:
    path = agent_runtime_contract.resolve_agent_stream_path(repo_root=repo_root)
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for raw in path.read_text(encoding="utf-8").splitlines():
        token = raw.strip()
        if not token:
            continue
        try:
            payload = json.loads(token)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if not any(
            _normalize_token(payload.get(field))
            for field in (
                "proof_lane",
                "proof_fingerprint",
                "proof_phase",
                "evidence_tier",
                "proof_status",
                "work_category",
            )
        ):
            continue
        rows.append(payload)
    return rows


def _match_lane_id_from_event(event: Mapping[str, Any], source_rows: Sequence[Mapping[str, Any]]) -> str:
    lane_id = _normalize_token(event.get("proof_lane"))
    if lane_id:
        return lane_id
    workstreams = {
        _normalize_token(token)
        for token in event.get("workstreams", [])
        if _normalize_token(token)
    } if isinstance(event.get("workstreams"), list) else set()
    candidates = [
        row for row in source_rows
        if workstreams & {_normalize_token(token) for token in row.get("workstreams", []) if _normalize_token(token)}
    ]
    if len(candidates) == 1:
        return _normalize_token(candidates[0].get("lane_id"))
    return ""


def _merge_live_proof_lanes(
    *,
    existing: Mapping[str, Mapping[str, Any]],
    source_rows: Sequence[Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    merged = {
        lane_id: dict(row)
        for lane_id, row in existing.items()
        if _normalize_token(lane_id) and isinstance(row, Mapping)
    }
    for row in source_rows:
        lane_id = _normalize_token(row.get("lane_id"))
        if not lane_id:
            continue
        lane = dict(merged.get(lane_id, {}))
        if isinstance(row.get("workstreams"), list):
            existing_workstreams = lane.get("workstreams", []) if isinstance(lane.get("workstreams"), list) else []
            lane["workstreams"] = sorted(
                {
                    _normalize_token(token)
                    for token in [*existing_workstreams, *row.get("workstreams", [])]
                    if _normalize_token(token)
                }
            )
        merged[lane_id] = lane
    for event in events:
        lane_id = _match_lane_id_from_event(event, source_rows)
        if not lane_id:
            continue
        lane = dict(merged.get(lane_id, {}))
        proof_status = _normalize_token(event.get("proof_status"))
        fingerprint = _normalize_token(event.get("proof_fingerprint")) or _normalize_token(lane.get("failure_fingerprint"))
        if proof_status in PROOF_STATUSES:
            lane["proof_status"] = proof_status
        if fingerprint:
            previous_fingerprint = _normalize_token(lane.get("failure_fingerprint"))
            if previous_fingerprint and previous_fingerprint == fingerprint:
                lane["repeated_fingerprint_count"] = int(lane.get("repeated_fingerprint_count", 0) or 0) + 1
            lane["failure_fingerprint"] = fingerprint
        phase = _normalize_token(event.get("proof_phase"))
        if phase:
            lane["frontier_phase"] = phase
        evidence_tier = _normalize_token(event.get("evidence_tier"))
        if evidence_tier:
            lane["evidence_tier"] = evidence_tier
        work_category = _normalize_token(event.get("work_category"))
        if work_category in WORK_CATEGORIES:
            recent = [
                _normalize_token(token)
                for token in lane.get("recent_work_categories", [])
                if _normalize_token(token) in WORK_CATEGORIES
            ] if isinstance(lane.get("recent_work_categories"), list) else []
            recent.append(work_category)
            lane["recent_work_categories"] = recent[-6:]
        event_workstreams = [
            _normalize_token(token)
            for token in event.get("workstreams", [])
            if _normalize_token(token)
        ] if isinstance(event.get("workstreams"), list) else []
        if event_workstreams:
            existing_workstreams = lane.get("workstreams", []) if isinstance(lane.get("workstreams"), list) else []
            lane["workstreams"] = sorted(
                {
                    _normalize_token(token)
                    for token in [*existing_workstreams, *event_workstreams]
                    if _normalize_token(token)
                }
            )
        existing_truth = normalize_deployment_truth(lane.get("deployment_truth"))
        event_truth = normalize_deployment_truth(event.get("deployment_truth"))
        merged_truth = {
            field: (
                event_truth[field]
                if event_truth[field] != "unknown"
                else existing_truth[field]
            )
            for field in event_truth
        }
        if proof_status == "falsified_live" and merged_truth.get("last_live_failing_commit") == "unknown":
            merged_truth["last_live_failing_commit"] = next(
                (
                    merged_truth[field]
                    for field in ("published_source_commit", "pushed_head", "local_head")
                    if merged_truth.get(field) not in {"", "unknown"}
                ),
                "unknown",
            )
        if any(value != "unknown" for value in merged_truth.values()):
            lane["deployment_truth"] = merged_truth
        if proof_status == "falsified_live":
            lane["last_falsification"] = {
                "recorded_at": _normalize_token(event.get("ts_iso")),
                "failure_fingerprint": fingerprint,
                "frontier_phase": phase,
            }
        merged[lane_id] = lane
    return merged


def _scope_workstreams(snapshot: Mapping[str, Any]) -> list[str]:
    evidence = dict(snapshot.get("evidence_context", {})) if isinstance(snapshot.get("evidence_context"), Mapping) else {}
    rows = [
        _normalize_token(token)
        for token in evidence.get("linked_workstreams", [])
        if _normalize_token(token)
    ] if isinstance(evidence.get("linked_workstreams"), list) else []
    if _normalize_token(snapshot.get("scope_type")) == "workstream":
        scope_id = _normalize_token(snapshot.get("scope_id"))
        if scope_id:
            rows.insert(0, scope_id)
    deduped: list[str] = []
    seen: set[str] = set()
    for token in rows:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _scope_bug_refs(snapshot: Mapping[str, Any]) -> dict[str, list[str]]:
    evidence = dict(snapshot.get("evidence_context", {})) if isinstance(snapshot.get("evidence_context"), Mapping) else {}
    bug_ids: list[str] = []
    bug_paths: list[str] = []
    if _normalize_token(snapshot.get("scope_type")) == "bug":
        scope_id = _normalize_token(snapshot.get("scope_id"))
        if scope_id:
            bug_ids.append(scope_id)
            bug_paths.append(scope_id)
    if isinstance(evidence.get("linked_bug_ids"), list):
        bug_ids.extend(_normalize_token(token) for token in evidence.get("linked_bug_ids", []))
    if isinstance(evidence.get("linked_bug_paths"), list):
        bug_paths.extend(_normalize_token(token) for token in evidence.get("linked_bug_paths", []))

    def _dedupe(values: Sequence[str]) -> list[str]:
        rows: list[str] = []
        seen: set[str] = set()
        for raw in values:
            token = _normalize_token(raw)
            if not token or token in seen:
                continue
            seen.add(token)
            rows.append(token)
        return rows

    return {
        "bug_ids": _dedupe(bug_ids),
        "bug_paths": _dedupe(bug_paths),
    }


def _scope_has_bug_refs(snapshot: Mapping[str, Any]) -> bool:
    refs = _scope_bug_refs(snapshot)
    return bool(refs["bug_ids"] or refs["bug_paths"])


def _resolved_source_rows(snapshot: Mapping[str, Any], source_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    bug_refs = _scope_bug_refs(snapshot)
    bug_ids = set(bug_refs["bug_ids"])
    bug_paths = set(bug_refs["bug_paths"])
    if bug_ids or bug_paths:
        bug_rows = [
            dict(row)
            for row in source_rows
            if (
                _normalize_token(row.get("linked_bug_id")) in bug_ids
                or _normalize_token(row.get("source_path")) in bug_paths
            )
        ]
        bug_lane_ids = sorted(
            {
                _normalize_token(row.get("lane_id"))
                for row in bug_rows
                if _normalize_token(row.get("lane_id"))
            }
        )
        if len(bug_lane_ids) == 1:
            lane_id = bug_lane_ids[0]
            rows = [
                dict(row)
                for row in source_rows
                if _normalize_token(row.get("lane_id")) == lane_id
            ]
            rows.sort(key=lambda row: (0 if row.get("source") == "casebook" else 1, _normalize_token(row.get("lane_id"))))
            return rows
        bug_rows.sort(key=lambda row: (0 if row.get("source") == "casebook" else 1, _normalize_token(row.get("lane_id"))))
        return bug_rows

    workstreams = set(_scope_workstreams(snapshot))
    rows = [
        dict(row)
        for row in source_rows
        if workstreams & {_normalize_token(token) for token in row.get("workstreams", []) if _normalize_token(token)}
    ]
    rows.sort(key=lambda row: (0 if row.get("source") == "casebook" else 1, _normalize_token(row.get("lane_id"))))
    return rows


def _merge_source_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any] | None, list[str]]:
    lane_ids = sorted(
        {
            _normalize_token(row.get("lane_id"))
            for row in rows
            if _normalize_token(row.get("lane_id"))
        }
    )
    if len(lane_ids) != 1:
        return None, lane_ids
    lane_rows = sorted(
        (dict(row) for row in rows if _normalize_token(row.get("lane_id")) == lane_ids[0]),
        key=lambda row: (_SOURCE_PRECEDENCE.get(_normalize_token(row.get("source")), 99), _normalize_token(row.get("source_path"))),
    )
    merged: dict[str, Any] = {"lane_id": lane_ids[0]}
    for row in lane_rows:
        for field in (
            "linked_bug_id",
            "current_blocker",
            "failure_fingerprint",
            "first_failing_phase",
            "clearance_condition",
            "proof_status",
            "source",
            "source_path",
        ):
            if _normalize_token(merged.get(field)):
                continue
            token = _normalize_token(row.get(field))
            if token:
                merged[field] = token
    merged["workstreams"] = sorted(
        {
            _normalize_token(token)
            for row in lane_rows
            for token in row.get("workstreams", [])
            if _normalize_token(token)
        }
    )
    return merged, lane_ids


def _inferred_live_rows(
    snapshot: Mapping[str, Any],
    live_lanes: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    workstreams = set(_scope_workstreams(snapshot))
    rows: list[dict[str, Any]] = []
    for lane_id, row in live_lanes.items():
        if not isinstance(row, Mapping):
            continue
        lane_workstreams = {
            _normalize_token(token)
            for token in row.get("workstreams", [])
            if _normalize_token(token)
        } if isinstance(row.get("workstreams"), list) else set()
        if workstreams and not (workstreams & lane_workstreams):
            continue
        rows.append(
            {
                "source": "inferred",
                "source_path": "",
                "lane_id": _normalize_token(lane_id) or _normalize_token(row.get("lane_id")),
                "linked_bug_id": _normalize_token(row.get("linked_bug_id")),
                "current_blocker": _normalize_token(row.get("current_blocker")),
                "failure_fingerprint": _normalize_token(row.get("failure_fingerprint")),
                "first_failing_phase": _normalize_token(row.get("first_failing_phase")),
                "clearance_condition": _normalize_token(row.get("clearance_condition")),
                "proof_status": _normalize_token(row.get("proof_status")) if _normalize_token(row.get("proof_status")) in PROOF_STATUSES else "diagnosed",
                "workstreams": sorted(lane_workstreams),
            }
        )
    rows.sort(key=lambda row: _normalize_token(row.get("lane_id")))
    return rows


def _allowed_next_work(status: str) -> list[str]:
    if status == "live_verified":
        return ["closeout", "secondary hardening", "docs"]
    return ["primary fix", "validating test", "deploy instruction"]


def _deprioritized(status: str) -> list[str]:
    if status == "live_verified":
        return []
    return ["docs", "UX polish", "broader hardening"]


def _resolved_proof_state(
    *,
    repo_root: Path,
    snapshot: Mapping[str, Any],
    source_row: Mapping[str, Any],
    live_lane: Mapping[str, Any],
) -> dict[str, Any]:
    source_status = _normalize_token(source_row.get("proof_status"))
    live_status = _normalize_token(live_lane.get("proof_status"))
    status = live_status if live_status in PROOF_STATUSES else (source_status if source_status in PROOF_STATUSES else "diagnosed")
    deployment_truth = normalize_deployment_truth(live_lane.get("deployment_truth"))
    if deployment_truth.get("local_head") == "unknown":
        local_head = _current_local_head(repo_root)
        if local_head:
            deployment_truth["local_head"] = local_head
    state = {
        "lane_id": _normalize_token(source_row.get("lane_id")) or _normalize_token(live_lane.get("lane_id")),
        "current_blocker": _normalize_token(source_row.get("current_blocker")) or _normalize_token(live_lane.get("current_blocker")),
        "failure_fingerprint": _normalize_token(live_lane.get("failure_fingerprint")) or _normalize_token(source_row.get("failure_fingerprint")),
        "first_failing_phase": _normalize_token(source_row.get("first_failing_phase")) or _normalize_token(live_lane.get("first_failing_phase")),
        "frontier_phase": _normalize_token(live_lane.get("frontier_phase")) or _normalize_token(source_row.get("first_failing_phase")),
        "clearance_condition": _normalize_token(source_row.get("clearance_condition")) or _normalize_token(live_lane.get("clearance_condition")),
        "proof_status": status,
        "evidence_tier": _normalize_token(live_lane.get("evidence_tier")),
        "last_falsification": dict(live_lane.get("last_falsification", {})) if isinstance(live_lane.get("last_falsification"), Mapping) else {},
        "allowed_next_work": _allowed_next_work(status),
        "deprioritized_until_cleared": _deprioritized(status),
        "linked_bug_id": _normalize_token(source_row.get("linked_bug_id")),
        "repeated_fingerprint_count": int(live_lane.get("repeated_fingerprint_count", 0) or 0),
        "deployment_truth": deployment_truth,
        "source": _normalize_token(source_row.get("source")),
        "source_path": _normalize_token(source_row.get("source_path")),
        "recent_work_categories": [
            _normalize_token(token)
            for token in live_lane.get("recent_work_categories", [])
            if _normalize_token(token) in WORK_CATEGORIES
        ] if isinstance(live_lane.get("recent_work_categories"), list) else [],
        "resolution_state": _normalize_token(source_row.get("source")) == "inferred" and "inferred" or "resolved",
    }
    normalized = normalize_proof_state(state)
    if frontier_has_advanced(normalized):
        normalized["proof_status"] = "live_verified"
        normalized["evidence_tier"] = "live_verified"
        normalized["allowed_next_work"] = _allowed_next_work("live_verified")
        normalized["deprioritized_until_cleared"] = _deprioritized("live_verified")
    warnings: list[str] = []
    reopen = proof_reopen_signal(normalized)
    if reopen:
        warning = str(reopen.get("summary", "")).strip()
        if warning:
            warnings.append(warning)
    drift_warning = proof_drift_warning(normalized)
    if drift_warning:
        warnings.append(drift_warning)
    if warnings:
        normalized["warnings"] = warnings
    return normalized


def resolve_scope_collection_proof_state(
    scopes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    states = [
        normalize_proof_state(scope.get("proof_state", {}))
        for scope in scopes
        if isinstance(scope, Mapping) and isinstance(scope.get("proof_state"), Mapping)
    ]
    explicit_resolutions = [
        dict(scope.get("proof_state_resolution", {}))
        for scope in scopes
        if isinstance(scope, Mapping) and isinstance(scope.get("proof_state_resolution"), Mapping)
    ]
    lane_ids = sorted(
        {
            _normalize_token(row.get("lane_id"))
            for row in states
            if _normalize_token(row.get("lane_id"))
        }
    )
    if len(lane_ids) == 1 and states:
        primary = next(
            (
                row for row in states
                if _normalize_token(row.get("lane_id")) == lane_ids[0]
            ),
            states[0],
        )
        claim_guard = {}
        for scope in scopes:
            if not isinstance(scope, Mapping):
                continue
            scope_state = normalize_proof_state(scope.get("proof_state", {}))
            if _normalize_token(scope_state.get("lane_id")) != lane_ids[0]:
                continue
            if isinstance(scope.get("claim_guard"), Mapping):
                claim_guard = dict(scope.get("claim_guard", {}))
                break
        return {
            "proof_state": primary,
            "claim_guard": claim_guard or build_claim_guard(primary),
            "proof_state_resolution": {"state": "resolved", "lane_ids": lane_ids},
        }
    if len(lane_ids) > 1:
        return {"proof_state_resolution": {"state": "ambiguous", "lane_ids": lane_ids}}
    explicit_lane_ids = sorted(
        {
            _normalize_token(lane_id)
            for resolution in explicit_resolutions
            for lane_id in resolution.get("lane_ids", [])
            if _normalize_token(lane_id)
        }
    )
    if len(explicit_lane_ids) > 1:
        return {"proof_state_resolution": {"state": "ambiguous", "lane_ids": explicit_lane_ids}}
    if any(_normalize_token(resolution.get("state")) == "none" for resolution in explicit_resolutions):
        return {"proof_state_resolution": {"state": "none", "lane_ids": []}}
    return {"proof_state_resolution": {"state": "none", "lane_ids": []}}


def annotate_scopes_with_proof_state(
    *,
    repo_root: Path,
    scopes: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    bug_rows = _bug_proof_rows(root)
    plan_rows = _plan_proof_rows(root)
    source_rows = [*bug_rows, *plan_rows]
    existing_live_lanes = load_live_proof_lanes(repo_root=root)
    live_lanes = _merge_live_proof_lanes(
        existing=existing_live_lanes,
        source_rows=source_rows,
        events=_stream_proof_events(root),
    )
    if live_lanes != existing_live_lanes:
        persist_live_proof_lanes(repo_root=root, live_proof_lanes=live_lanes)

    prepared: list[dict[str, Any]] = []
    for snapshot in scopes:
        clone = dict(snapshot)
        candidates = _resolved_source_rows(clone, source_rows)
        source_row, lane_ids = _merge_source_rows(candidates)
        if source_row is None and not lane_ids and not _scope_has_bug_refs(clone):
            inferred_candidates = _inferred_live_rows(clone, live_lanes)
            source_row, lane_ids = _merge_source_rows(inferred_candidates)
        if source_row is not None and len(lane_ids) == 1:
            lane_id = _normalize_token(source_row.get("lane_id"))
            proof_state = _resolved_proof_state(
                repo_root=root,
                snapshot=clone,
                source_row=source_row,
                live_lane=live_lanes.get(lane_id, {}),
            )
            clone["proof_state"] = proof_state
            clone["claim_guard"] = build_claim_guard(proof_state)
            clone["proof_state_resolution"] = {
                "state": "resolved",
                "lane_ids": [lane_id],
            }
        elif len(lane_ids) > 1:
            clone["proof_state_resolution"] = {
                "state": "ambiguous",
                "lane_ids": lane_ids,
            }
        else:
            clone["proof_state_resolution"] = {"state": "none", "lane_ids": []}
        prepared.append(clone)

    scope_lookup = {
        _normalize_token(snapshot.get("scope_key")): snapshot
        for snapshot in prepared
        if _normalize_token(snapshot.get("scope_key"))
    }
    aggregated: list[dict[str, Any]] = []
    for snapshot in prepared:
        clone = dict(snapshot)
        if _normalize_token(clone.get("scope_type")) in {"surface", "grid"} and "proof_state" not in clone:
            diagnostics = dict(clone.get("diagnostics", {})) if isinstance(clone.get("diagnostics"), Mapping) else {}
            child_keys = [
                _normalize_token(token)
                for token in diagnostics.get("child_scope_keys", [])
                if _normalize_token(token)
            ] if isinstance(diagnostics.get("child_scope_keys"), list) else []
            child_states = [
                dict(scope_lookup[key].get("proof_state", {}))
                for key in child_keys
                if key in scope_lookup and isinstance(scope_lookup[key].get("proof_state"), Mapping)
            ]
            lane_ids = sorted({
                _normalize_token(row.get("lane_id"))
                for row in child_states
                if _normalize_token(row.get("lane_id"))
            })
            ambiguous_lane_ids = sorted(
                {
                    _normalize_token(lane_id)
                    for key in child_keys
                    if key in scope_lookup and isinstance(scope_lookup[key].get("proof_state_resolution"), Mapping)
                    for lane_id in scope_lookup[key].get("proof_state_resolution", {}).get("lane_ids", [])
                    if _normalize_token(lane_id)
                }
            )
            if len(lane_ids) == 1:
                clone["proof_state"] = normalize_proof_state(child_states[0])
                clone["claim_guard"] = build_claim_guard(clone["proof_state"])
                clone["proof_state_resolution"] = {"state": "resolved", "lane_ids": lane_ids}
            elif len(ambiguous_lane_ids) > 1:
                clone["proof_state_resolution"] = {"state": "ambiguous", "lane_ids": ambiguous_lane_ids}
        aggregated.append(clone)
    return aggregated
