"""Odylith Context Engine Memory Snapshot Runtime helpers for the Odylith context engine layer."""

from __future__ import annotations

def _store():
    from odylith.runtime.context_engine import odylith_context_engine_store as store

    return store


import contextlib
import datetime as dt
import json
import os
from pathlib import Path
import re
import time
from typing import Any
from typing import Mapping
from typing import Sequence


def _build_judgment_memory_snapshot(
    *,
    repo_root: Path,
    projection_updated_utc: str,
    backlog_projection: Mapping[str, Any],
    plan_projection: Mapping[str, Any],
    bug_projection: Sequence[Mapping[str, Any]],
    diagram_projection: Sequence[Mapping[str, Any]],
    runtime_state: Mapping[str, Any],
    optimization: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    benchmark_report: Mapping[str, Any],
    recent_bootstrap_packets: Sequence[Mapping[str, Any]],
    active_sessions: Sequence[Mapping[str, Any]],
    repo_dirty_paths: Sequence[str],
    welcome_state: Mapping[str, Any],
    previous_snapshot: Mapping[str, Any] | None,
    retrieval_state: str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    previous = dict(previous_snapshot) if isinstance(previous_snapshot, Mapping) else {}
    backlog_rows = [
        dict(row)
        for bucket in ("active", "execution", "finished", "parked")
        for row in backlog_projection.get(bucket, [])
        if isinstance(backlog_projection.get(bucket), list) and isinstance(row, Mapping)
    ]
    backlog_titles = {
        str(row.get("idea_id", "")).strip().upper(): str(row.get("title", "")).strip()
        for row in backlog_rows
        if str(row.get("idea_id", "")).strip()
    }
    finished_backlog_rows = [
        dict(row)
        for row in backlog_projection.get("finished", [])
        if isinstance(backlog_projection.get("finished"), list) and isinstance(row, Mapping)
    ]
    plan_done_rows = [
        dict(row)
        for row in plan_projection.get("done", [])
        if isinstance(plan_projection.get("done"), list) and isinstance(row, Mapping)
    ]
    plan_done_rows.sort(key=lambda row: (str(row.get("Updated", "")).strip(), str(row.get("Created", "")).strip()), reverse=True)
    active_plan_rows = [
        dict(row)
        for row in plan_projection.get("active", [])
        if isinstance(plan_projection.get("active"), list) and isinstance(row, Mapping)
    ]
    open_bug_rows = [
        dict(row)
        for row in bug_projection
        if isinstance(row, Mapping) and str(row.get("Status", "")).strip().lower() == "open"
    ]
    critical_open_bugs = [
        row
        for row in open_bug_rows
        if str(row.get("Severity", "")).strip().lower() in _store()._BUG_CRITICAL_SEVERITIES
    ]
    benchmark_comparison = (
        dict(benchmark_report.get("comparison", {}))
        if isinstance(benchmark_report.get("comparison"), Mapping)
        else {}
    )
    benchmark_acceptance = (
        dict(benchmark_report.get("acceptance", {}))
        if isinstance(benchmark_report.get("acceptance"), Mapping)
        else {}
    )
    benchmark_checks = (
        dict(benchmark_acceptance.get("checks", {}))
        if isinstance(benchmark_acceptance.get("checks"), Mapping)
        else {}
    )
    benchmark_path = (_store().runtime_root(repo_root=root) / "odylith-benchmarks" / "latest.v1.json").resolve()
    benchmark_path_ref = _store()._relative_repo_path(repo_root=root, path=benchmark_path)

    decision_items: list[dict[str, Any]] = []
    for row in plan_done_rows[:3]:
        backlog_id = _store()._workstream_token(str(row.get("Backlog", "")).strip())
        plan_path_ref = _store()._parse_link_target(str(row.get("Plan", "")))
        title = backlog_titles.get(backlog_id) or _store()._humanize_slug(Path(plan_path_ref or "done-plan").stem)
        decision_items.append(
            _store()._judgment_memory_item(
                kind="done_plan",
                summary=f"{title} closed and is now retained as a done plan.",
                recorded_utc=str(row.get("Updated", "")).strip() or str(row.get("Created", "")).strip(),
                source_path=plan_path_ref,
                source_kind="repo_truth",
                surfaces=("radar", "technical_plans"),
            )
        )
    if benchmark_comparison:
        decision_items.append(
            _store()._judgment_memory_item(
                kind="proof_outcome",
                summary=(
                    "Latest benchmark proof is "
                    f"{str(benchmark_acceptance.get('status', '')).strip() or 'unrated'} "
                    f"with recall delta {float(benchmark_comparison.get('required_path_recall_delta', 0.0) or 0.0):+.3f} "
                    f"and validation delta {float(benchmark_comparison.get('validation_success_delta', 0.0) or 0.0):+.3f}."
                ),
                recorded_utc=str(benchmark_report.get("generated_utc", "")).strip(),
                source_path=benchmark_path_ref,
                source_kind="benchmark_report",
                surfaces=("benchmark", "context_engine"),
            )
        )
    decision_state = "strong" if len(decision_items) >= 3 else "partial" if decision_items else "cold"
    decision_area = _store()._judgment_memory_area(
        key="decisions",
        label="Decision memory",
        state=decision_state,
        summary=(
            f"{len(decision_items)} recent decisions and proof outcomes are retained from done plans and benchmark proof."
            if decision_items
            else "No durable decisions or proof outcomes are retained yet."
        ),
        items=decision_items[:4],
        provenance=[
            _store()._provenance_item(
                label="Done plans",
                source_kind="repo_truth",
                path="odylith/technical-plans/done/",
                updated_utc=str(plan_done_rows[0].get("Updated", "")).strip() if plan_done_rows else "",
                trust="authoritative",
            ),
            _store()._provenance_item(
                label="Benchmark report",
                source_kind="benchmark_report",
                path=benchmark_path_ref if benchmark_comparison else "",
                updated_utc=str(benchmark_report.get("generated_utc", "")).strip(),
                trust="derived_runtime",
            ),
        ],
    )

    daemon_usage = _store().odylith_context_cache.read_json_object(_store().daemon_usage_path(repo_root=root))
    workspace_key = str(daemon_usage.get("workspace_key", "")).strip() if isinstance(daemon_usage, Mapping) else ""
    branch_name = _store()._git_branch_name(repo_root=root)
    head_oid = _store()._git_head_oid(repo_root=root)
    actor_name = _store()._git_stdout(repo_root=root, args=("config", "--get", "user.name"))
    actor_email = _store()._git_stdout(repo_root=root, args=("config", "--get", "user.email"))
    actor_label = " ".join(token for token in (actor_name, f"<{actor_email}>") if token).strip() or str(os.environ.get("USER", "")).strip()
    workspace_items: list[dict[str, Any]] = []
    if workspace_key or branch_name or head_oid:
        workspace_items.append(
            _store()._judgment_memory_item(
                kind="workspace",
                summary=(
                    f"Workspace `{workspace_key or _store().workspace_daemon_key(repo_root=root)}` is on `{branch_name or 'detached'}` at "
                    f"{(head_oid[:8] if head_oid else 'unknown')} with {len(repo_dirty_paths)} meaningful dirty path(s)."
                ),
                recorded_utc=(
                    str(daemon_usage.get("last_request_utc", "")).strip()
                    if isinstance(daemon_usage, Mapping)
                    else projection_updated_utc
                ),
                source_path=_store()._relative_repo_path(repo_root=root, path=_store().daemon_usage_path(repo_root=root)),
                source_kind="runtime_state",
                surfaces=("context_engine", "sessions"),
            )
        )
    if actor_label:
        workspace_items.append(
            _store()._judgment_memory_item(
                kind="actor",
                summary=f"Actor identity resolves locally as {actor_label}.",
                recorded_utc=projection_updated_utc,
                source_kind="local_git",
                surfaces=("workspace", "actor"),
            )
        )
    if active_sessions:
        session_row = dict(active_sessions[0])
        workspace_items.append(
            _store()._judgment_memory_item(
                kind="session",
                summary=(
                    f"{len(active_sessions)} active session(s) are currently tracked; the newest claim is "
                    f"`{str(session_row.get('session_id', '')).strip() or 'unknown'}`."
                ),
                recorded_utc=str(session_row.get("updated_utc", "")).strip(),
                source_path=":.odylith/runtime/sessions/",
                source_kind="runtime_state",
                surfaces=("sessions",),
            )
        )
    workspace_state = "strong" if workspace_items and actor_email and branch_name and (workspace_key or active_sessions) else "partial" if workspace_items else "cold"
    workspace_area = _store()._judgment_memory_area(
        key="workspace_actor",
        label="Workspace and actor memory",
        state=workspace_state,
        summary=(
            "Workspace, branch, actor, and session identity are retained as compact local memory."
            if workspace_items
            else "No stable workspace or actor identity has been retained yet."
        ),
        items=workspace_items[:3],
        provenance=[
            _store()._provenance_item(
                label="Git identity",
                source_kind="local_git",
                updated_utc=projection_updated_utc,
                trust="local_observation",
            ),
            _store()._provenance_item(
                label="Daemon usage",
                source_kind="runtime_state",
                path=_store()._relative_repo_path(repo_root=root, path=_store().daemon_usage_path(repo_root=root)),
                updated_utc=str(daemon_usage.get("last_request_utc", "")).strip() if isinstance(daemon_usage, Mapping) else "",
                trust="derived_runtime",
            ),
        ],
    )

    outcome_items: list[dict[str, Any]] = []
    if benchmark_comparison:
        outcome_items.append(
            _store()._judgment_memory_item(
                kind="benchmark_delta",
                summary=(
                    f"Benchmark deltas are recall {float(benchmark_comparison.get('required_path_recall_delta', 0.0) or 0.0):+.3f}, "
                    f"validation {float(benchmark_comparison.get('validation_success_delta', 0.0) or 0.0):+.3f}, "
                    f"latency {float(benchmark_comparison.get('median_latency_delta_ms', 0.0) or 0.0):+.3f} ms, and "
                    f"prompt tokens {float(benchmark_comparison.get('median_prompt_token_delta', 0.0) or 0.0):+.1f}."
                ),
                recorded_utc=str(benchmark_report.get("generated_utc", "")).strip(),
                source_path=benchmark_path_ref,
                source_kind="benchmark_report",
                surfaces=("benchmark",),
            )
        )
    for row in finished_backlog_rows[:2]:
        backlog_id = str(row.get("idea_id", "")).strip().upper()
        title = str(row.get("title", "")).strip() or backlog_id
        outcome_items.append(
            _store()._judgment_memory_item(
                kind="finished_workstream",
                summary=f"{title} is now retained as a finished governed outcome.",
                recorded_utc=str(backlog_projection.get("updated_utc", "")).strip(),
                source_path=_store()._parse_link_target(str(row.get("link", ""))),
                source_kind="repo_truth",
                surfaces=("radar",),
            )
        )
    outcome_state = "strong" if benchmark_comparison and finished_backlog_rows else "partial" if outcome_items else "cold"
    outcome_area = _store()._judgment_memory_area(
        key="outcomes",
        label="Outcome memory",
        state=outcome_state,
        summary=(
            f"{len(outcome_items)} outcome signal(s) are retained from benchmark proof and finished workstreams."
            if outcome_items
            else "No durable outcome memory is retained yet."
        ),
        items=outcome_items[:4],
        provenance=[
            _store()._provenance_item(
                label="Finished workstreams",
                source_kind="repo_truth",
                path="odylith/radar/source/INDEX.md",
                updated_utc=str(backlog_projection.get("updated_utc", "")).strip(),
                trust="authoritative",
            ),
            _store()._provenance_item(
                label="Benchmark report",
                source_kind="benchmark_report",
                path=benchmark_path_ref if benchmark_comparison else "",
                updated_utc=str(benchmark_report.get("generated_utc", "")).strip(),
                trust="derived_runtime",
            ),
        ],
    )

    negative_items: list[dict[str, Any]] = []
    retained_open_bugs = critical_open_bugs[:3] if critical_open_bugs else open_bug_rows[:3]
    for row in retained_open_bugs:
        negative_items.append(
            _store()._judgment_memory_item(
                kind="open_bug",
                summary=(
                    f"{str(row.get('Title', '')).strip()} remains {str(row.get('Severity', '')).strip()} and "
                    f"{str(row.get('Status', '')).strip().lower()}."
                ),
                recorded_utc=str(row.get("Date", "")).strip(),
                source_path=_store()._parse_link_target(str(row.get("Link", ""))),
                source_kind="casebook",
                severity=str(row.get("Severity", "")).strip(),
                surfaces=("casebook",),
            )
        )
    if benchmark_comparison and float(benchmark_comparison.get("median_total_payload_token_delta", 0.0) or 0.0) > 0.0:
        negative_items.append(
            _store()._judgment_memory_item(
                kind="budget_drag",
                summary=(
                    f"Total Odylith payload is still {float(benchmark_comparison.get('median_total_payload_token_delta', 0.0) or 0.0):+.1f} "
                    "tokens heavier than the full-scan baseline."
                ),
                recorded_utc=str(benchmark_report.get("generated_utc", "")).strip(),
                source_path=benchmark_path_ref,
                source_kind="benchmark_report",
                severity="P1",
                next_move="Trim runtime-contract overhead without giving back recall or validation gains.",
                surfaces=("benchmark", "packet_budget"),
            )
        )
    negative_state = "strong" if critical_open_bugs or len(negative_items) >= 2 else "partial" if negative_items else "cold"
    negative_area = _store()._judgment_memory_area(
        key="negative",
        label="Negative memory",
        state=negative_state,
        summary=(
            f"{len(negative_items)} unresolved failure or drag signal(s) are retained from bugs and benchmark proof."
            if negative_items
            else "No retained failure or drag signals are recorded yet."
        ),
        items=negative_items[:4],
        provenance=[
            _store()._provenance_item(
                label="Casebook bugs",
                source_kind="casebook",
                path="odylith/casebook/bugs/INDEX.md",
                updated_utc=_store()._latest_updated_utc(*[str(row.get("Date", "")).strip() for row in retained_open_bugs]),
                trust="authoritative",
            ),
            _store()._provenance_item(
                label="Benchmark gate",
                source_kind="benchmark_report",
                path=benchmark_path_ref if benchmark_comparison else "",
                updated_utc=str(benchmark_report.get("generated_utc", "")).strip(),
                trust="derived_runtime",
            ),
        ],
    )

    current_starter = (
        dict(welcome_state.get("chosen_slice", {}))
        if isinstance(welcome_state.get("chosen_slice"), Mapping)
        else {}
    )
    previous_starter = dict(previous.get("starter_slice", {})) if isinstance(previous.get("starter_slice"), Mapping) else {}
    starter_path = str(current_starter.get("path", "")).strip() or str(previous_starter.get("path", "")).strip()
    starter_workstream = _store()._workstream_token(str(previous_starter.get("workstream_id", "")).strip())
    if starter_path:
        for packet in recent_bootstrap_packets:
            if not isinstance(packet, Mapping):
                continue
            packet_workstream = _store()._payload_workstream_hint(packet)
            packet_paths = (
                [str(token).strip() for token in packet.get("changed_paths", []) if str(token).strip()]
                if isinstance(packet.get("changed_paths"), list)
                else []
            )
            if packet_workstream and any(
                _store()._repo_paths_overlap(repo_root=root, left=packet_path, right=starter_path)
                for packet_path in packet_paths
            ):
                starter_workstream = packet_workstream
                break
    if starter_path and not starter_workstream:
        for session_row in active_sessions:
            if not isinstance(session_row, Mapping):
                continue
            session_workstream = _store()._workstream_token(str(session_row.get("workstream", "")).strip())
            session_paths = (
                [str(token).strip() for token in session_row.get("claimed_paths", []) if str(token).strip()]
                if isinstance(session_row.get("claimed_paths"), list)
                else []
            )
            if session_workstream and any(
                _store()._repo_paths_overlap(repo_root=root, left=session_path, right=starter_path)
                for session_path in session_paths
            ):
                starter_workstream = session_workstream
                break
    starter_status = "cold"
    first_seen_utc = str(previous_starter.get("first_seen_utc", "")).strip() or projection_updated_utc
    if starter_path and bool(welcome_state.get("show")):
        starter_status = "suggested"
    elif starter_path and previous_starter:
        starter_status = "established"
    elif starter_path:
        starter_status = "inferred"
    onboarding_items: list[dict[str, Any]] = []
    if starter_path:
        onboarding_items.append(
            _store()._judgment_memory_item(
                kind="starter_slice",
                summary=(
                    f"Starter slice is `{starter_path}` with seam "
                    f"{str(current_starter.get('seam', '')).strip() or str(previous_starter.get('seam', '')).strip() or 'not recorded'}"
                    + (f" and workstream `{starter_workstream}`." if starter_workstream else ".")
                ),
                recorded_utc=str(previous_starter.get("last_seen_utc", "")).strip() or projection_updated_utc,
                source_kind="onboarding_observation",
                surfaces=("dashboard", "radar", "registry", "atlas"),
            )
        )
    if recent_bootstrap_packets:
        packet = dict(recent_bootstrap_packets[0])
        packet_paths = [str(token).strip() for token in packet.get("changed_paths", []) if str(token).strip()] if isinstance(packet.get("changed_paths"), list) else []
        onboarding_items.append(
            _store()._judgment_memory_item(
                kind="bootstrap_packet",
                summary=(
                    f"Latest bootstrap session `{str(packet.get('session_id', '')).strip() or 'unknown'}` grounded "
                    f"{packet_paths[0] if packet_paths else starter_path or 'the current slice'}."
                ),
                recorded_utc=str(packet.get("bootstrapped_at", "")).strip(),
                source_path=":.odylith/runtime/bootstraps/",
                source_kind="runtime_state",
                surfaces=("bootstrap", "sessions"),
            )
        )
    onboarding_state = "strong" if starter_path and recent_bootstrap_packets else "partial" if onboarding_items else "cold"
    starter_slice_payload = {
        "path": starter_path,
        "seam": str(current_starter.get("seam", "")).strip() or str(previous_starter.get("seam", "")).strip(),
        "component_label": str(current_starter.get("component_label", "")).strip()
        or str(previous_starter.get("component_label", "")).strip(),
        "workstream_id": starter_workstream,
        "first_seen_utc": first_seen_utc,
        "last_seen_utc": projection_updated_utc or _store()._utc_now(),
        "status": starter_status,
    }
    onboarding_area = _store()._judgment_memory_area(
        key="onboarding",
        label="Onboarding memory",
        state=onboarding_state,
        summary=(
            "Odylith retains the first governed slice and the latest bootstrap evidence for it."
            if starter_path and recent_bootstrap_packets
            else "Odylith retains or infers the current governed slice, but bootstrap evidence is still limited."
            if onboarding_items
            else "No onboarding slice or bootstrap evidence has been retained yet."
        ),
        items=onboarding_items[:3],
        provenance=[
            _store()._provenance_item(
                label="Shell onboarding",
                source_kind="onboarding_observation",
                updated_utc=projection_updated_utc,
                trust="derived_runtime",
            ),
            _store()._provenance_item(
                label="Bootstrap packets",
                source_kind="runtime_state",
                path=":.odylith/runtime/bootstraps/",
                updated_utc=str(recent_bootstrap_packets[0].get("bootstrapped_at", "")).strip() if recent_bootstrap_packets else "",
                trust="derived_runtime",
            ),
        ],
    )

    contradiction_items: list[dict[str, Any]] = []
    if retrieval_state == "strong" and decision_state != "strong":
        contradiction_items.append(
            _store()._judgment_memory_item(
                kind="retrieval_vs_judgment",
                summary="Retrieval memory is strong, but durable decision memory is still only partially grounded.",
                recorded_utc=projection_updated_utc,
                source_kind="runtime_state",
                next_move="Keep raising durable judgment quality until it matches retrieval readiness.",
                surfaces=("retrieval", "judgment"),
            )
        )
    if benchmark_comparison and float(benchmark_comparison.get("median_prompt_token_delta", 0.0) or 0.0) < 0.0 and float(benchmark_comparison.get("median_total_payload_token_delta", 0.0) or 0.0) > 0.0:
        contradiction_items.append(
            _store()._judgment_memory_item(
                kind="prompt_vs_payload",
                summary=(
                    f"Agent prompts are {float(benchmark_comparison.get('median_prompt_token_delta', 0.0) or 0.0):+.1f} tokens leaner than baseline, "
                    f"but the full Odylith payload is still {float(benchmark_comparison.get('median_total_payload_token_delta', 0.0) or 0.0):+.1f} tokens heavier."
                ),
                recorded_utc=str(benchmark_report.get("generated_utc", "")).strip(),
                source_path=benchmark_path_ref,
                source_kind="benchmark_report",
                next_move="Trim runtime-contract overhead while keeping dense prompt wins intact.",
                surfaces=("benchmark", "packet_budget"),
            )
        )
    if critical_open_bugs and not active_plan_rows:
        contradiction_items.append(
            _store()._judgment_memory_item(
                kind="bugs_without_active_plan",
                summary=(
                    f"Casebook still carries {len(critical_open_bugs)} open critical bug(s), but Plans has no active implementation lane bound to them."
                ),
                recorded_utc=_store()._latest_updated_utc(*[str(row.get("Date", "")).strip() for row in critical_open_bugs]),
                source_path="odylith/casebook/bugs/INDEX.md",
                source_kind="casebook",
                next_move="Bind the current critical bug cluster to one governed implementation slice before more fixes drift outside plan truth.",
                surfaces=("casebook", "technical_plans", "radar"),
            )
        )
    if critical_open_bugs and str(benchmark_acceptance.get("status", "")).strip().lower() in {"provisional_pass", "pass"}:
        contradiction_items.append(
            _store()._judgment_memory_item(
                kind="proof_vs_open_risk",
                summary="Benchmark proof is green, but critical open bugs still keep the release/install lane operationally risky.",
                recorded_utc=_store()._latest_updated_utc(
                    str(benchmark_report.get("generated_utc", "")).strip(),
                    *[str(row.get("Date", "")).strip() for row in critical_open_bugs],
                ),
                source_path=benchmark_path_ref,
                source_kind="benchmark_report",
                next_move="Keep benchmark proof and Casebook reality aligned by closing or rebinding the critical bug cluster.",
                surfaces=("benchmark", "casebook"),
            )
        )
    if bool(welcome_state.get("show")) and not recent_bootstrap_packets:
        contradiction_items.append(
            _store()._judgment_memory_item(
                kind="suggested_without_bootstrap",
                summary="Odylith can name a first governed slice, but no bootstrap-session evidence has been captured for it yet.",
                recorded_utc=projection_updated_utc,
                source_kind="onboarding_observation",
                next_move="Run one grounded bootstrap session on the suggested slice to warm judgment memory.",
                surfaces=("dashboard", "bootstrap"),
            )
        )
    contradiction_state = "strong" if len(contradiction_items) >= 2 else "partial" if contradiction_items else "cold"
    contradiction_area = _store()._judgment_memory_area(
        key="contradictions",
        label="Contradiction memory",
        state=contradiction_state,
        summary=(
            f"{len(contradiction_items)} cross-surface contradiction(s) are retained as named memory."
            if contradiction_items
            else "No durable cross-surface contradictions are retained yet."
        ),
        items=contradiction_items[:4],
        provenance=[
            _store()._provenance_item(
                label="Repo truth and runtime posture",
                source_kind="repo_truth",
                path="odylith/radar/source/INDEX.md",
                updated_utc=str(backlog_projection.get("updated_utc", "")).strip(),
                trust="authoritative",
            ),
            _store()._provenance_item(
                label="Benchmark proof",
                source_kind="benchmark_report",
                path=benchmark_path_ref if benchmark_comparison else "",
                updated_utc=str(benchmark_report.get("generated_utc", "")).strip(),
                trust="derived_runtime",
            ),
        ],
    )

    provisional_areas = [
        decision_area,
        workspace_area,
        contradiction_area,
        negative_area,
        outcome_area,
        onboarding_area,
    ]
    freshness_items = [
        _store()._judgment_memory_item(
            kind="area_freshness",
            summary=f"{str(area.get('label', '')).strip()} is {str(dict(area.get('freshness', {})).get('bucket', '')).strip() or 'unknown'}.",
            recorded_utc=str(area.get("updated_utc", "")).strip(),
            source_kind="derived_runtime",
        )
        for area in provisional_areas
        if str(area.get("updated_utc", "")).strip()
    ]
    fresh_or_recent = sum(
        1
        for area in provisional_areas
        if str(dict(area.get("freshness", {})).get("bucket", "")).strip() in {"fresh", "recent"}
    )
    freshness_state = "strong" if provisional_areas and fresh_or_recent >= max(2, len(provisional_areas) // 2) else "partial" if freshness_items else "cold"
    freshness_area = _store()._judgment_memory_area(
        key="freshness",
        label="Freshness memory",
        state=freshness_state,
        summary=(
            f"{fresh_or_recent} memory area(s) are still fresh or recent."
            if freshness_items
            else "No memory freshness evidence is retained yet."
        ),
        items=freshness_items[:4],
        provenance=[
            _store()._provenance_item(
                label="Runtime snapshot timestamps",
                source_kind="runtime_state",
                path=":.odylith/runtime/",
                updated_utc=projection_updated_utc,
                trust="derived_runtime",
            ),
        ],
    )

    source_counts: dict[str, int] = {}
    for area in [*provisional_areas, freshness_area]:
        for provenance_row in area.get("provenance", []):
            if not isinstance(provenance_row, Mapping):
                continue
            kind = str(provenance_row.get("source_kind", "")).strip()
            if not kind:
                continue
            source_counts[kind] = source_counts.get(kind, 0) + 1
    provenance_items = [
        _store()._judgment_memory_item(
            kind="source_kind",
            summary=f"{_store()._humanize_slug(kind)} contributes to {count} judgment area(s).",
            recorded_utc=projection_updated_utc,
            source_kind="provenance",
        )
        for kind, count in sorted(source_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    provenance_state = "strong" if len(source_counts) >= 4 else "partial" if provenance_items else "cold"
    provenance_area = _store()._judgment_memory_area(
        key="provenance",
        label="Provenance memory",
        state=provenance_state,
        summary=(
            f"{len(source_counts)} distinct evidence source kind(s) back the current judgment memory."
            if provenance_items
            else "No provenance coverage is retained yet."
        ),
        items=provenance_items[:5],
        provenance=[
            _store()._provenance_item(
                label="Judgment sources",
                source_kind="provenance",
                path=_store()._relative_repo_path(repo_root=root, path=_store().judgment_memory_path(repo_root=root)),
                updated_utc=projection_updated_utc,
                trust="derived_runtime",
            ),
        ],
    )

    areas = [
        decision_area,
        workspace_area,
        contradiction_area,
        freshness_area,
        negative_area,
        outcome_area,
        onboarding_area,
        provenance_area,
    ]
    counts: dict[str, int] = {}
    gaps: list[str] = []
    for row in areas:
        state = str(row.get("state", "")).strip() or "unknown"
        counts[state] = counts.get(state, 0) + 1
        if state in {"partial", "cold"}:
            label = str(row.get("label", "")).strip() or "Judgment memory"
            summary = str(row.get("summary", "")).strip()
            gaps.append(f"{label}: {summary}" if summary else label)
    snapshot = {
        "contract": "judgment_memory.v1",
        "version": "v1",
        "generated_utc": _store()._utc_now(),
        "storage_path": _store()._relative_repo_path(repo_root=root, path=_store().judgment_memory_path(repo_root=root)),
        "starter_slice": starter_slice_payload if starter_path else {},
        "status": _store()._memory_snapshot_status_from_counts(counts),
        "headline": _store()._judgment_memory_headline(areas),
        "counts": counts,
        "gap_count": len(gaps),
        "areas": areas,
        "gaps": gaps,
    }
    return snapshot


def _build_memory_areas_snapshot(
    *,
    enabled: bool,
    authoritative_truth: Mapping[str, Any],
    compiler_state: Mapping[str, Any],
    guidance_catalog: Mapping[str, Any],
    runtime_state: Mapping[str, Any],
    entity_counts: Mapping[str, Any],
    backend_transition: Mapping[str, Any],
    optimization: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    judgment_memory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not enabled:
        areas = [
            _store()._memory_area_entry(
                key=key,
                label=label,
                state="disabled",
                summary="Odylith is disabled, so this memory area is suppressed for ablation runs.",
            )
            for key, label in (
                ("repo_truth", "Repo truth"),
                ("retrieval", "Retrieval memory"),
                ("guidance", "Guidance memory"),
                ("session_packets", "Session packet memory"),
                ("outcomes", "Outcome memory"),
                ("decisions", "Decision memory"),
                ("collaboration", "Collaboration memory"),
                ("contradictions", "Contradiction memory"),
            )
        ]
        return {
            "contract": "memory_areas.v1",
            "status": "disabled",
            "headline": "Odylith is disabled, so memory-area posture is suppressed for this run.",
            "counts": {"disabled": len(areas)},
            "gap_count": len(areas),
            "areas": areas,
            "gaps": [
                "Odylith is disabled; memory-area posture and gap analysis are intentionally suppressed."
            ],
        }

    read_only_repo_truth = bool(authoritative_truth.get("read_only_repo_truth"))
    compiler_ready = bool(compiler_state.get("ready"))
    guidance_chunks = int(guidance_catalog.get("chunk_count", 0) or 0)
    guidance_docs = int(guidance_catalog.get("source_doc_count", 0) or 0)
    guidance_families = int(guidance_catalog.get("task_family_count", 0) or 0)
    active_sessions = int(runtime_state.get("active_sessions", 0) or 0)
    bootstrap_packets = int(runtime_state.get("bootstrap_packets", 0) or 0)
    indexed_entities = int(entity_counts.get("indexed_entity_count", 0) or 0)
    evidence_documents = int(entity_counts.get("evidence_documents", 0) or 0)
    sample_size = int(optimization.get("sample_size", 0) or 0)
    coverage_rate = float(
        optimization.get("coverage_rate", evaluation.get("coverage_rate", 0.0)) or 0.0
    )
    satisfaction_rate = float(
        optimization.get("satisfaction_rate", evaluation.get("satisfaction_rate", 0.0)) or 0.0
    )
    transition_status = str(backend_transition.get("status", "")).strip().lower()
    actual_backend = (
        dict(backend_transition.get("actual_local_backend", {}))
        if isinstance(backend_transition.get("actual_local_backend"), Mapping)
        else {}
    )
    actual_storage = str(actual_backend.get("storage", "")).strip() or "compiler snapshot"
    actual_sparse = str(actual_backend.get("sparse_recall", "")).strip() or "repo scan fallback"

    retrieval_state = _store()._derive_retrieval_memory_state(
        transition_status=transition_status,
        indexed_entities=indexed_entities,
        evidence_documents=evidence_documents,
        compiler_ready=compiler_ready,
    )

    guidance_state = "cold"
    if guidance_chunks > 0 and guidance_families > 0:
        guidance_state = "strong"
    elif guidance_chunks > 0 or guidance_docs > 0 or guidance_families > 0:
        guidance_state = "partial"

    session_state = "cold"
    if active_sessions > 0:
        session_state = "strong"
    elif bootstrap_packets > 0:
        session_state = "partial"

    outcome_state = "cold"
    if sample_size >= 5 or coverage_rate >= 0.5 or satisfaction_rate >= 0.5:
        outcome_state = "strong"
    elif sample_size > 0 or coverage_rate > 0.0 or satisfaction_rate > 0.0:
        outcome_state = "partial"

    judgment_areas = [
        dict(row)
        for row in dict(judgment_memory or {}).get("areas", [])
        if isinstance(dict(judgment_memory or {}).get("areas"), list) and isinstance(row, Mapping)
    ]
    judgment_by_key = {
        str(row.get("key", "")).strip(): row
        for row in judgment_areas
        if str(row.get("key", "")).strip()
    }
    decisions_row = dict(judgment_by_key.get("decisions", {}))
    collaboration_row = dict(judgment_by_key.get("workspace_actor", {}))
    contradictions_row = dict(judgment_by_key.get("contradictions", {}))
    outcomes_row = dict(judgment_by_key.get("outcomes", {}))

    areas = [
        _store()._memory_area_entry(
            key="repo_truth",
            label="Repo truth",
            state="strong" if read_only_repo_truth else "partial",
            summary=(
                "Git-tracked backlog, plans, bugs, diagrams, components, and code remain authoritative."
                if read_only_repo_truth
                else "Repo truth exists, but the read-only authority boundary is not fully enforced."
            ),
        ),
        _store()._memory_area_entry(
            key="retrieval",
            label="Retrieval memory",
            state=retrieval_state,
            summary=(
                f"{actual_storage} / {actual_sparse} is active across {indexed_entities} indexed entities and {evidence_documents} retained evidence docs."
                if retrieval_state != "cold"
                else "No meaningful indexed retrieval footprint is materialized yet."
            ),
        ),
        _store()._memory_area_entry(
            key="guidance",
            label="Guidance memory",
            state=guidance_state,
            summary=(
                f"{guidance_chunks} compiled guidance chunks across {guidance_docs} docs and {guidance_families} task families shape packet grounding."
                if guidance_state != "cold"
                else "No compiled guidance catalog is ready yet."
            ),
        ),
        _store()._memory_area_entry(
            key="session_packets",
            label="Session packet memory",
            state=session_state,
            summary=(
                f"{active_sessions} active sessions and {bootstrap_packets} retained bootstrap packet(s) are available for recent-session recall."
                if session_state == "strong"
                else f"{bootstrap_packets} retained bootstrap packet(s) are available, but no active session memory is warm."
                if session_state == "partial"
                else "No active session or bootstrap packet memory is warm yet."
            ),
        ),
        _store()._memory_area_entry(
            key="outcomes",
            label="Outcome memory",
            state=str(outcomes_row.get("state", "")).strip() or outcome_state,
            summary=(
                str(outcomes_row.get("summary", "")).strip()
                or (
                    f"{sample_size} sampled packet(s), {coverage_rate:.0%} coverage, and {satisfaction_rate:.0%} satisfaction are available for outcome learning."
                    if outcome_state != "cold"
                    else "No meaningful optimization or evaluation outcome memory is available yet."
                )
            ),
        ),
        _store()._memory_area_entry(
            key="decisions",
            label="Decision memory",
            state=str(decisions_row.get("state", "")).strip() or "planned",
            summary=(
                str(decisions_row.get("summary", "")).strip()
                or "Resolved decisions, reversals, and proof outcomes are not first-class durable memory yet."
            ),
        ),
        _store()._memory_area_entry(
            key="collaboration",
            label="Workspace and actor memory",
            state=str(collaboration_row.get("state", "")).strip() or "planned",
            summary=(
                str(collaboration_row.get("summary", "")).strip()
                or "Workspace, actor, and shared-ownership memory are not first-class durable memory yet."
            ),
        ),
        _store()._memory_area_entry(
            key="contradictions",
            label="Contradiction memory",
            state=str(contradictions_row.get("state", "")).strip() or "planned",
            summary=(
                str(contradictions_row.get("summary", "")).strip()
                or "Cross-surface disagreements are detected per run, but they are not stored as durable named memory yet."
            ),
        ),
    ]
    counts: dict[str, int] = {}
    gaps: list[str] = []
    for row in areas:
        state = str(row.get("state", "")).strip() or "unknown"
        counts[state] = counts.get(state, 0) + 1
        if state in {"partial", "cold", "planned"}:
            label = str(row.get("label", "")).strip() or "Memory area"
            summary = str(row.get("summary", "")).strip()
            gaps.append(f"{label}: {summary}" if summary else label)
    return {
        "contract": "memory_areas.v1",
        "status": _store()._memory_snapshot_status_from_counts(counts),
        "headline": _store()._memory_areas_headline(areas),
        "counts": counts,
        "gap_count": len(gaps),
        "areas": areas,
        "gaps": gaps,
    }


def _odylith_disabled_memory_snapshot(
    *,
    repo_root: Path,
    switch_snapshot: Mapping[str, Any],
    optimization_snapshot: Mapping[str, Any],
    evaluation_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    disabled_judgment_areas = [
        _store()._judgment_memory_area(
            key=key,
            label=label,
            state="disabled",
            summary="Odylith is disabled, so this judgment-memory area is suppressed for ablation runs.",
            items=[],
            provenance=[],
        )
        for key, label in (
            ("decisions", "Decision memory"),
            ("workspace_actor", "Workspace and actor memory"),
            ("contradictions", "Contradiction memory"),
            ("freshness", "Freshness memory"),
            ("negative", "Negative memory"),
            ("outcomes", "Outcome memory"),
            ("onboarding", "Onboarding memory"),
            ("provenance", "Provenance memory"),
        )
    ]
    payload = {
        "contract": "memory_snapshot.v1",
        "version": "v1",
        "generated_utc": _store()._utc_now(),
        "status": "disabled",
        "status_reason": "odylith_disabled",
        "odylith_switch": dict(switch_snapshot),
        "engine": {
            "name": "odylith-context-engine",
            "product_layer": "",
            "storage_mode": "disabled_for_ablation",
            "authoritative_truth": "repo_tracked",
            "enabled": False,
            "backend": {},
            "target_backend": {},
            "backend_transition": {
                "status": "disabled_for_ablation",
                "v1_standardization_complete": False,
                "gaps": ["odylith_disabled"],
            },
        },
        "backend_transition": {
            "status": "disabled_for_ablation",
            "v1_standardization_complete": False,
            "actual_local_backend": {},
            "target_local_backend": {},
            "future_shared_candidate": {},
            "gaps": ["odylith_disabled"],
            "guardrails": {
                "local_first": True,
                "remote_required": False,
                "vector_first_allowed": False,
                "hybrid_rerank_role": "disabled_for_ablation",
            },
        },
        "authoritative_truth": {
            "source": "git_tracked_repo_truth",
            "mutable_runtime_root": ".odylith/runtime",
            "cache_root": ".odylith/cache/odylith-context-engine",
            "read_only_repo_truth": True,
        },
        "projection_state": {
            "projection_fingerprint": "",
            "projection_scope": "",
            "updated_utc": "",
            "tables": {},
        },
        "entity_counts": {"indexed_entity_count": 0},
        "guidance_catalog": {
            "contract": "guidance_catalog.v1",
            "version": "v1",
            "chunk_count": 0,
            "source_doc_count": 0,
            "task_family_count": 0,
            "catalog_fingerprint": "",
            "compiled_path": "",
            "compiled_bytes": 0,
        },
        "retrieval_pipeline": {
            "order": [],
            "capabilities": {
                "exact_lookup": False,
                "sparse_recall": False,
                "typed_graph_expansion": False,
                "miss_recovery": False,
                "packet_budgeting": False,
                "routing_handoff": False,
                "vector_first": False,
                "hybrid_rerank_enabled": False,
                "storage_backend_actual": "",
                "storage_backend_target": "",
                "sparse_backend_actual": "",
                "sparse_backend_target": "",
                "target_backend_standardized": False,
                "miss_recovery_mode": "",
                "future_shared_candidate": "",
            },
        },
        "runtime_state": {
            "active_sessions": 0,
            "bootstrap_packets": 0,
            "projection_snapshot_path": "",
            "projection_snapshot_bytes": 0,
            "compiler_manifest_path": "",
            "compiler_manifest_bytes": 0,
            "odylith_memory_root": str(_store().odylith_memory_backend.local_backend_root(repo_root=repo_root)),
            "judgment_memory_path": str(_store().judgment_memory_path(repo_root=repo_root)),
        },
        "optimization": {
            "contract": "optimization_snapshot.v1",
            "status": str(optimization_snapshot.get("status", "")).strip() or "disabled",
            "sample_size": int(optimization_snapshot.get("sample_size", 0) or 0),
            "overall": dict(optimization_snapshot.get("overall", {}))
            if isinstance(optimization_snapshot.get("overall"), Mapping)
            else {},
            "coverage_rate": float(evaluation_snapshot.get("coverage_rate", 0.0) or 0.0),
            "satisfaction_rate": float(evaluation_snapshot.get("satisfaction_rate", 0.0) or 0.0),
        },
        "ingest_policy": {
            "allowlisted_sources": [],
            "secret_redaction_required": True,
            "provenance_required": True,
            "repo_truth_read_only": True,
        },
        "recommendations": [
            "Odylith is disabled; derived memory and retrieval contracts are suppressed for ablation studies."
        ],
    }
    payload["judgment_memory"] = {
        "contract": "judgment_memory.v1",
        "version": "v1",
        "generated_utc": _store()._utc_now(),
        "storage_path": _store()._relative_repo_path(repo_root=repo_root, path=_store().judgment_memory_path(repo_root=repo_root)),
        "status": "disabled",
        "headline": "Odylith is disabled, so durable judgment memory is suppressed for this run.",
        "counts": {"disabled": len(disabled_judgment_areas)},
        "gap_count": len(disabled_judgment_areas),
        "areas": disabled_judgment_areas,
        "gaps": [
            "Odylith is disabled; durable judgment memory and persisted local memory are intentionally suppressed."
        ],
        "starter_slice": {},
    }
    payload["memory_areas"] = _build_memory_areas_snapshot(
        enabled=False,
        authoritative_truth=payload.get("authoritative_truth", {}),
        compiler_state={},
        guidance_catalog=payload.get("guidance_catalog", {}),
        runtime_state=payload.get("runtime_state", {}),
        entity_counts=payload.get("entity_counts", {}),
        backend_transition=payload.get("backend_transition", {}),
        optimization=payload.get("optimization", {}),
        evaluation=evaluation_snapshot,
        judgment_memory=payload.get("judgment_memory", {}),
    )
    payload["headline"] = str(payload["memory_areas"].get("headline", "")).strip()
    return payload


def load_runtime_memory_snapshot(
    *,
    repo_root: Path,
    optimization_snapshot: Mapping[str, Any] | None = None,
    evaluation_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize the current local derived memory/retrieval substrate."""

    root = Path(repo_root).resolve()
    odylith_switch = _store()._odylith_switch_snapshot(repo_root=root)
    if not bool(odylith_switch.get("enabled", True)):
        optimization = (
            dict(optimization_snapshot)
            if isinstance(optimization_snapshot, Mapping)
            else _store().load_runtime_optimization_snapshot(repo_root=root)
        )
        evaluation = (
            dict(evaluation_snapshot)
            if isinstance(evaluation_snapshot, Mapping)
            else load_runtime_evaluation_snapshot(repo_root=root)
        )
        return _odylith_disabled_memory_snapshot(
            repo_root=root,
            switch_snapshot=odylith_switch,
            optimization_snapshot=optimization,
            evaluation_snapshot=evaluation,
        )

    state = _store().read_runtime_state(repo_root=root)
    guidance_catalog = _store().tooling_guidance_catalog.load_guidance_catalog(repo_root=root)
    guidance_summary = _store().tooling_guidance_catalog.compact_catalog_summary(guidance_catalog)
    optimization = (
        dict(optimization_snapshot)
        if isinstance(optimization_snapshot, Mapping)
        else _store().load_runtime_optimization_snapshot(repo_root=root)
    )
    evaluation = (
        dict(evaluation_snapshot)
        if isinstance(evaluation_snapshot, Mapping)
        else load_runtime_evaluation_snapshot(repo_root=root)
    )

    projection_state: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = {
        "workstreams": 0,
        "plans": 0,
        "bugs": 0,
        "diagrams": 0,
        "components": 0,
        "component_specs": 0,
        "traceability_edges": 0,
        "engineering_notes": 0,
        "code_artifacts": 0,
        "code_edges": 0,
        "test_cases": 0,
        "test_history": 0,
        "delivery_surfaces": 0,
        "evidence_documents": 0,
    }
    with contextlib.suppress(RuntimeError):
        connection = _store()._connect(root)
        try:
            for row in connection.execute(
                "SELECT name, row_count, updated_utc FROM projection_state ORDER BY name"
            ).fetchall():
                projection_state[str(row["name"]).strip()] = {
                    "row_count": int(row["row_count"] or 0),
                    "updated_utc": str(row["updated_utc"] or "").strip(),
                }
            counts.update(
                {
                    "workstreams": _store()._table_row_count(connection, "workstreams"),
                    "plans": _store()._table_row_count(connection, "plans"),
                    "bugs": _store()._table_row_count(connection, "bugs"),
                    "diagrams": _store()._table_row_count(connection, "diagrams"),
                    "components": _store()._table_row_count(connection, "components"),
                    "component_specs": _store()._table_row_count(connection, "component_specs"),
                    "traceability_edges": _store()._table_row_count(connection, "traceability_edges"),
                    "engineering_notes": _store()._table_row_count(connection, "engineering_notes"),
                    "code_artifacts": _store()._table_row_count(connection, "code_artifacts"),
                    "code_edges": _store()._table_row_count(connection, "code_edges"),
                    "test_cases": _store()._table_row_count(connection, "test_cases"),
                    "test_history": _store()._table_row_count(connection, "test_history"),
                    "delivery_surfaces": _store()._table_row_count(connection, "delivery_surfaces"),
                }
            )
        finally:
            connection.close()

    projection_snapshot_file = _store().projection_snapshot_path(repo_root=root)
    compiler_manifest_path = _store().odylith_projection_bundle.manifest_path(repo_root=root)
    architecture_bundle_path = _store().odylith_architecture_mode.bundle_path(repo_root=root)
    guidance_catalog_path = _store().tooling_guidance_catalog.compiled_catalog_path(repo_root=root)
    active_sessions = len(_store().list_session_states(repo_root=root, prune=False))
    bootstrap_packets = len(list(_store().bootstraps_root(repo_root=root).glob("*.json")))
    indexed_entity_count = sum(
        counts.get(key, 0)
        for key in (
            "workstreams",
            "plans",
            "bugs",
            "diagrams",
            "components",
            "engineering_notes",
            "code_artifacts",
            "test_cases",
        )
    )
    local_backend_status = _store().odylith_memory_backend.backend_runtime_status(repo_root=root)
    local_backend_manifest = (
        dict(local_backend_status.get("manifest", {}))
        if isinstance(local_backend_status.get("manifest"), Mapping)
        else {}
    )
    compiler_manifest = _store().odylith_projection_bundle.load_bundle_manifest(repo_root=root)
    architecture_bundle = _store().odylith_architecture_mode.load_architecture_bundle(repo_root=root)
    counts["evidence_documents"] = int(local_backend_manifest.get("document_count", 0) or 0)
    observed_backend = {
        "provider": str(local_backend_status.get("provider", "")).strip() or _store()._FALLBACK_LOCAL_MEMORY_BACKEND["provider"],
        "storage": str(local_backend_status.get("storage", "")).strip() or _store()._FALLBACK_LOCAL_MEMORY_BACKEND["storage"],
        "sparse_recall": str(local_backend_status.get("sparse_recall", "")).strip()
        or _store()._FALLBACK_LOCAL_MEMORY_BACKEND["sparse_recall"],
        "graph_expansion": _store()._FALLBACK_LOCAL_MEMORY_BACKEND["graph_expansion"],
        "mode": _store()._FALLBACK_LOCAL_MEMORY_BACKEND["mode"],
    }
    target_backend = dict(_store()._TARGET_LOCAL_MEMORY_BACKEND)
    backend_gaps: list[str] = []
    if str(observed_backend.get("storage", "")).strip() != str(target_backend.get("storage", "")).strip():
        backend_gaps.append("columnar_store_not_enabled")
    if str(observed_backend.get("sparse_recall", "")).strip() != str(target_backend.get("sparse_recall", "")).strip():
        backend_gaps.append("tantivy_sparse_recall_not_enabled")
    standardization_complete = not backend_gaps
    backend_status_token = str(local_backend_status.get("status", "")).strip()
    convergence_state = (
        "error"
        if backend_status_token == "error"
        else "standardized"
        if standardization_complete
        else "pending_target_swap"
    )
    memory_proof_signature = _store()._memory_backend_proof_signature(
        state=state,
        backend_manifest=local_backend_manifest,
    )
    memory_proof = _store()._runtime_proof_section(repo_root=root, section="memory_backend")
    effective_backend = dict(observed_backend)
    effective_backend_gaps = list(backend_gaps)
    effective_standardization_complete = standardization_complete
    effective_convergence_state = convergence_state
    backend_evidence_source = "live_backend"
    sticky_signature = (
        dict(memory_proof.get("signature", {}))
        if isinstance(memory_proof.get("signature"), Mapping)
        else {}
    )
    sticky_backend = (
        dict(memory_proof.get("actual_local_backend", {}))
        if isinstance(memory_proof.get("actual_local_backend"), Mapping)
        else {}
    )
    sticky_standardized = bool(memory_proof.get("v1_standardization_complete"))
    sticky_manifest_ready = bool(local_backend_manifest.get("ready")) or str(local_backend_manifest.get("status", "")).strip() == "ready"
    sticky_manifest_present = bool(
        sticky_manifest_ready
        or int(local_backend_manifest.get("document_count", 0) or 0) > 0
        or int(local_backend_manifest.get("edge_count", 0) or 0) > 0
    )
    if (
        not effective_standardization_complete
        and sticky_standardized
        and sticky_backend
        and _store()._memory_backend_sticky_snapshot_compatible(
            live_signature=memory_proof_signature,
            sticky_signature=sticky_signature,
            observed_backend=observed_backend,
            sticky_backend=sticky_backend,
        )
        and backend_status_token != "error"
        and sticky_manifest_present
    ):
        effective_backend = dict(sticky_backend)
        effective_backend_gaps = []
        effective_standardization_complete = True
        effective_convergence_state = "standardized"
        backend_evidence_source = "sticky_snapshot"
    if effective_standardization_complete and backend_evidence_source == "live_backend":
        _store()._persist_runtime_proof_section(
            repo_root=root,
            section="memory_backend",
            payload={
                "status": effective_convergence_state,
                "v1_standardization_complete": True,
                "actual_local_backend": dict(effective_backend),
                "observed_local_backend": dict(observed_backend),
                "target_local_backend": dict(target_backend),
                "signature": memory_proof_signature,
                "backend_status": backend_status_token,
                "evidence_source": backend_evidence_source,
            },
        )
    remote_config = _store().odylith_remote_retrieval.remote_config(repo_root=root)
    backlog_projection = _store()._load_backlog_projection(repo_root=root)
    plan_projection = _store()._load_plan_projection(repo_root=root)
    bug_projection = _store()._load_bug_projection(repo_root=root)
    diagram_projection = _store()._load_diagram_projection(repo_root=root)
    recent_bootstrap_packets = _store()._load_recent_bootstrap_packets(repo_root=root, bootstrap_limit=3)
    active_session_rows = _store().list_session_states(repo_root=root, prune=False)
    repo_dirty_paths = _store().governance.collect_meaningful_changed_paths(repo_root=root, changed_paths=(), include_git=True)
    previous_judgment_memory = _store().odylith_context_cache.read_json_object(_store().judgment_memory_path(repo_root=root))
    from odylith.runtime.surfaces import shell_onboarding

    welcome_state = shell_onboarding.build_welcome_state(repo_root=root)
    degraded_fallback_posture = (
        dict(optimization.get("degraded_fallback_posture", {}))
        if isinstance(optimization.get("degraded_fallback_posture"), Mapping)
        else {}
    )
    governance_runtime_first = (
        dict(optimization.get("governance_runtime_first_posture", {}))
        if isinstance(optimization.get("governance_runtime_first_posture"), Mapping)
        else {}
    )
    payload = {
        "contract": "memory_snapshot.v1",
        "version": "v1",
        "generated_utc": _store()._utc_now(),
        "status": "active" if projection_state or str(state.get("updated_utc", "")).strip() else "cold",
        "odylith_switch": odylith_switch,
        "engine": {
            "name": "odylith-context-engine",
            "product_layer": "memory_retrieval",
            "storage_mode": "local_derived",
            "authoritative_truth": "repo_tracked",
            "backend": effective_backend,
            "target_backend": target_backend,
            "backend_evidence_source": backend_evidence_source,
            "backend_transition": {
                "status": effective_convergence_state,
                "v1_standardization_complete": effective_standardization_complete,
                "gaps": effective_backend_gaps,
            },
        },
        "backend_transition": {
            "status": effective_convergence_state,
            "v1_standardization_complete": effective_standardization_complete,
            "actual_local_backend": effective_backend,
            "observed_local_backend": observed_backend,
            "target_local_backend": target_backend,
            "future_shared_candidate": dict(_store()._FUTURE_SHARED_MEMORY_BACKEND),
            "gaps": effective_backend_gaps,
            "evidence_source": backend_evidence_source,
            "signature": memory_proof_signature,
            "local_backend_status": {
                key: value
                for key, value in local_backend_status.items()
                if key in {"status", "ready", "dependencies", "manifest"}
            },
            "guardrails": {
                "local_first": True,
                "remote_required": False,
                "vector_first_allowed": False,
                "hybrid_rerank_role": "secondary_optional",
            },
        },
        "repo_scan_degraded_fallback": degraded_fallback_posture,
        "governance_runtime_first": governance_runtime_first,
        "authoritative_truth": {
            "source": "git_tracked_repo_truth",
            "mutable_runtime_root": ".odylith/runtime",
            "cache_root": ".odylith/cache/odylith-context-engine",
            "read_only_repo_truth": True,
        },
        "projection_state": {
            "projection_fingerprint": str(state.get("projection_fingerprint", "")).strip(),
            "projection_scope": str(state.get("projection_scope", "")).strip(),
            "updated_utc": str(state.get("updated_utc", "")).strip(),
            "tables": projection_state,
        },
        "compiler_state": {
            "version": str(compiler_manifest.get("version", "")).strip() or "v1",
            "ready": bool(compiler_manifest.get("ready")),
            "compiled_utc": str(compiler_manifest.get("compiled_utc", "")).strip(),
            "projection_fingerprint": str(compiler_manifest.get("projection_fingerprint", "")).strip(),
            "projection_scope": str(compiler_manifest.get("projection_scope", "")).strip(),
            "document_count": int(compiler_manifest.get("document_count", 0) or 0),
            "edge_count": int(compiler_manifest.get("edge_count", 0) or 0),
            "documents_path": str(compiler_manifest.get("documents_path", "")).strip(),
            "edges_path": str(compiler_manifest.get("edges_path", "")).strip(),
            "architecture_bundle_path": str(architecture_bundle_path),
            "architecture_bundle_ready": bool(architecture_bundle.get("ready")),
            "architecture_bundle_counts": dict(architecture_bundle.get("counts", {}))
            if isinstance(architecture_bundle.get("counts"), Mapping)
            else {},
        },
        "entity_counts": {
            **counts,
            "indexed_entity_count": indexed_entity_count,
        },
        "guidance_catalog": {
            "contract": "guidance_catalog.v1",
            "version": str(guidance_summary.get("version", "")).strip() or "v1",
            "chunk_count": int(guidance_summary.get("chunk_count", 0) or 0),
            "source_doc_count": int(guidance_summary.get("source_doc_count", 0) or 0),
            "task_family_count": len(
                [
                    str(token).strip()
                    for token in guidance_summary.get("task_families", [])
                    if str(token).strip()
                ]
            )
            if isinstance(guidance_summary.get("task_families"), list)
            else int(guidance_summary.get("task_family_count", 0) or 0),
            "catalog_fingerprint": str(guidance_catalog.get("catalog_fingerprint", "")).strip(),
            "compiled_path": str(guidance_catalog_path),
            "compiled_bytes": _store()._safe_file_size(guidance_catalog_path),
        },
        "retrieval_pipeline": {
            "order": [
                "exact_lookup",
                "sparse_recall",
                "typed_graph_expansion",
                "policy_filtering",
                "optional_hybrid_rerank",
                "packet_compaction",
                "routing_handoff",
            ],
            "capabilities": {
                "exact_lookup": True,
                "sparse_recall": True,
                "typed_graph_expansion": True,
                "miss_recovery": True,
                "packet_budgeting": True,
                "routing_handoff": True,
                "vector_first": False,
                "storage_backend_actual": str(effective_backend.get("storage", "")).strip(),
                "storage_backend_target": str(target_backend.get("storage", "")).strip(),
                "sparse_backend_actual": str(effective_backend.get("sparse_recall", "")).strip(),
                "sparse_backend_target": str(target_backend.get("sparse_recall", "")).strip(),
                "target_backend_standardized": effective_standardization_complete,
                "miss_recovery_mode": "tantivy_sparse_recall"
                if effective_standardization_complete
                else "repo_scan_fallback",
                "hybrid_rerank_available": effective_standardization_complete,
                "hybrid_rerank_enabled": _store()._env_truthy("ODYLITH_HYBRID_RERANK"),
                "future_shared_candidate": str(_store()._FUTURE_SHARED_MEMORY_BACKEND.get("provider", "")).strip(),
            },
        },
        "runtime_state": {
            "active_sessions": active_sessions,
            "bootstrap_packets": bootstrap_packets,
            "projection_snapshot_path": str(projection_snapshot_file),
            "projection_snapshot_bytes": _store()._safe_file_size(projection_snapshot_file),
            "compiler_manifest_path": str(compiler_manifest_path),
            "compiler_manifest_bytes": _store()._safe_file_size(compiler_manifest_path),
            "architecture_bundle_path": str(architecture_bundle_path),
            "architecture_bundle_bytes": _store()._safe_file_size(architecture_bundle_path),
            "odylith_memory_root": str(_store().odylith_memory_backend.local_backend_root(repo_root=root)),
            "judgment_memory_path": str(_store().judgment_memory_path(repo_root=root)),
        },
        "optimization": {
            "contract": "optimization_snapshot.v1",
            "status": str(optimization.get("status", "")).strip(),
            "sample_size": int(optimization.get("sample_size", 0) or 0),
            "overall": dict(optimization.get("overall", {}))
            if isinstance(optimization.get("overall"), Mapping)
            else {},
            "coverage_rate": float(evaluation.get("coverage_rate", 0.0) or 0.0),
            "satisfaction_rate": float(evaluation.get("satisfaction_rate", 0.0) or 0.0),
        },
        "remote_retrieval": {
            "provider": str(remote_config.get("provider", "")).strip(),
            "enabled": bool(remote_config.get("enabled")),
            "configured": bool(remote_config.get("configured")),
            "status": str(remote_config.get("status", "")).strip(),
            "mode": str(remote_config.get("mode", "")).strip(),
            "base_url": str(remote_config.get("base_url", "")).strip(),
            "schema": str(remote_config.get("schema", "")).strip(),
            "namespace": str(remote_config.get("namespace", "")).strip(),
            "issues": list(remote_config.get("issues", [])) if isinstance(remote_config.get("issues"), list) else [],
            "action": str(remote_config.get("action", "")).strip(),
            "state": dict(remote_config.get("state", {})) if isinstance(remote_config.get("state"), Mapping) else {},
        },
        "ingest_policy": {
            "allowlisted_sources": [
                "backlog_markdown",
                "plan_markdown",
                "bug_markdown",
                "component_registry",
                "mermaid_catalog",
                "delivery_intelligence_artifacts",
                "engineering_guidance",
                "python_source",
                "pytest_source",
            ],
            "secret_redaction_required": True,
            "provenance_required": True,
            "repo_truth_read_only": True,
        },
    }
    payload["judgment_memory"] = _build_judgment_memory_snapshot(
        repo_root=root,
        projection_updated_utc=str(state.get("updated_utc", "")).strip(),
        backlog_projection=backlog_projection,
        plan_projection=plan_projection,
        bug_projection=bug_projection,
        diagram_projection=diagram_projection,
        runtime_state=payload.get("runtime_state", {}),
        optimization=optimization,
        evaluation=evaluation,
        benchmark_report=_store()._load_latest_benchmark_report_snapshot(repo_root=root),
        recent_bootstrap_packets=recent_bootstrap_packets,
        active_sessions=active_session_rows,
        repo_dirty_paths=repo_dirty_paths,
        welcome_state=welcome_state,
        previous_snapshot=previous_judgment_memory,
        retrieval_state=_store()._derive_retrieval_memory_state(
            transition_status=effective_convergence_state,
            indexed_entities=indexed_entity_count,
            evidence_documents=counts["evidence_documents"],
            compiler_ready=bool(compiler_manifest.get("ready")),
        ),
    )
    _store().odylith_context_cache.write_json_if_changed(
        repo_root=root,
        path=_store().judgment_memory_path(repo_root=root),
        payload=payload["judgment_memory"],
        lock_key=str(_store().judgment_memory_path(repo_root=root)),
    )
    payload["memory_areas"] = _build_memory_areas_snapshot(
        enabled=True,
        authoritative_truth=payload.get("authoritative_truth", {}),
        compiler_state=payload.get("compiler_state", {}),
        guidance_catalog=payload.get("guidance_catalog", {}),
        runtime_state=payload.get("runtime_state", {}),
        entity_counts=payload.get("entity_counts", {}),
        backend_transition=payload.get("backend_transition", {}),
        optimization=payload.get("optimization", {}),
        evaluation=evaluation,
        judgment_memory=payload.get("judgment_memory", {}),
    )
    payload["headline"] = str(payload["memory_areas"].get("headline", "")).strip()
    return payload


def _architecture_evaluation_snapshot(
    *,
    repo_root: Path,
    corpus: Mapping[str, Any],
    focus_limit: int = 4,
    timing_limit: int = 48,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    architecture_cases = _store().odylith_benchmark_contract.architecture_benchmark_scenarios(corpus)
    if not architecture_cases:
        return {
            "status": "unseeded",
            "corpus_size": 0,
            "covered_case_count": 0,
            "satisfied_case_count": 0,
            "coverage_rate": 0.0,
            "satisfaction_rate": 0.0,
            "avg_latency_ms": 0.0,
            "avg_estimated_bytes": 0.0,
            "avg_estimated_tokens": 0.0,
            "focus_cases": [],
            "recommendations": [
                "Architecture benchmark lane is not seeded yet; add architecture cases before treating architecture copilot posture as measured."
            ],
        }
    timing_rows = [
        row
        for row in _store().odylith_control_state.load_timing_rows(repo_root=root, limit=max(1, int(timing_limit)))
        if str(row.get("category", "")).strip() == "reasoning"
        and str(row.get("operation", "")).strip() == "architecture"
    ]
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    covered_count = 0
    satisfied_count = 0
    case_rows: list[dict[str, Any]] = []
    matched_timings: list[dict[str, Any]] = []
    for case in architecture_cases:
        match_spec = dict(case.get("match", {})) if isinstance(case.get("match"), Mapping) else {}
        expect_spec = dict(case.get("expect", {})) if isinstance(case.get("expect"), Mapping) else {}
        latest_timing = next(
            (row for row in timing_rows if _store()._architecture_timing_matches_evaluation_case(row, match_spec)),
            None,
        )
        case_status = "unmatched"
        expectation_details: dict[str, Any] = {}
        if latest_timing is not None:
            covered_count += 1
            matched_timings.append(dict(latest_timing))
            expectation_ok, expectation_details = _store()._architecture_timing_satisfies_evaluation_expectations(
                latest_timing,
                expect_spec,
            )
            if expectation_ok:
                satisfied_count += 1
                case_status = "satisfied"
            else:
                case_status = "drift"
        metadata = dict(latest_timing.get("metadata", {})) if isinstance(latest_timing, Mapping) and isinstance(latest_timing.get("metadata"), Mapping) else {}
        case_rows.append(
            {
                "case_id": str(case.get("case_id", "")).strip(),
                "label": str(case.get("label", "")).strip() or str(case.get("case_id", "")).strip(),
                "priority": str(case.get("priority", "medium")).strip().lower() or "medium",
                "status": case_status,
                "summary": str(case.get("summary", "")).strip(),
                "latest_match_utc": str(latest_timing.get("ts_iso", "")).strip() if latest_timing else "",
                "duration_ms": round(float(latest_timing.get("duration_ms", 0.0) or 0.0), 3) if latest_timing else 0.0,
                "confidence_tier": str(metadata.get("confidence_tier", "")).strip(),
                "full_scan_recommended": bool(metadata.get("full_scan_recommended")) if latest_timing else False,
                "expectation_details": expectation_details,
            }
        )
    case_rows.sort(
        key=lambda row: (
            {"drift": 0, "unmatched": 1, "satisfied": 2}.get(str(row.get("status", "")).strip(), 9),
            priority_order.get(str(row.get("priority", "medium")).strip(), 9),
            str(row.get("label", "")).strip(),
        )
    )
    corpus_size = len(architecture_cases)
    coverage_rate = round(covered_count / max(1, corpus_size), 3)
    satisfaction_rate = round(satisfied_count / max(1, covered_count), 3) if covered_count else 0.0
    avg_latency_ms = round(
        sum(float(row.get("duration_ms", 0.0) or 0.0) for row in matched_timings) / max(1, len(matched_timings)),
        3,
    ) if matched_timings else 0.0
    avg_estimated_bytes = round(
        sum(float(dict(row.get("metadata", {})).get("estimated_bytes", 0.0) or 0.0) for row in matched_timings) / max(1, len(matched_timings)),
        3,
    ) if matched_timings else 0.0
    avg_estimated_tokens = round(
        sum(float(dict(row.get("metadata", {})).get("estimated_tokens", 0.0) or 0.0) for row in matched_timings) / max(1, len(matched_timings)),
        3,
    ) if matched_timings else 0.0
    recommendations: list[str] = []
    if not timing_rows:
        recommendations.append(
            f"Architecture benchmark lane is seeded but has no recent dossier evidence yet; run `{_store().display_command('context-engine', '--repo-root', '.', 'architecture', '<path>')}` on a benchmarked slice."
        )
    drift_cases = [str(row.get("label", "")).strip() for row in case_rows if str(row.get("status", "")).strip() == "drift"]
    unmatched_cases = [str(row.get("label", "")).strip() for row in case_rows if str(row.get("status", "")).strip() == "unmatched"]
    if drift_cases:
        recommendations.append(
            f"Architecture dossier drifted from expected posture for {', '.join(drift_cases[:2])}; inspect the latest dossier before trusting architecture copilot automation."
        )
    if unmatched_cases:
        recommendations.append(
            f"Architecture benchmark coverage is incomplete for {', '.join(unmatched_cases[:2])}; exercise those topology slices before tightening policy further."
        )
    if not recommendations:
        recommendations.append(
            "Architecture benchmark lane is currently healthy; use it as the acceptance baseline for future architecture-copilot changes."
        )
    signature = _store()._architecture_evaluation_proof_signature(
        repo_root=root,
        corpus=corpus,
    )
    live_snapshot = {
        "status": "active" if timing_rows else "seeded_no_evidence",
        "corpus_size": corpus_size,
        "covered_case_count": covered_count,
        "satisfied_case_count": satisfied_count,
        "coverage_rate": coverage_rate,
        "satisfaction_rate": satisfaction_rate,
        "avg_latency_ms": avg_latency_ms,
        "avg_estimated_bytes": avg_estimated_bytes,
        "avg_estimated_tokens": avg_estimated_tokens,
        "focus_cases": case_rows[: max(1, int(focus_limit))],
        "recommendations": recommendations[:3],
        "evidence_source": "live_timings",
        "signature": signature,
    }
    sticky = _store()._runtime_proof_section(repo_root=root, section="architecture_evaluation")
    sticky_signature = (
        dict(sticky.get("signature", {}))
        if isinstance(sticky.get("signature"), Mapping)
        else {}
    )
    sticky_compatible = _store()._architecture_evaluation_signatures_compatible(signature, sticky_signature)
    if (
        int(live_snapshot.get("covered_case_count", 0) or 0) > 0
        and sticky_compatible
        and _store()._architecture_evaluation_snapshot_strength(sticky)
        > _store()._architecture_evaluation_snapshot_strength(live_snapshot)
    ):
        merged = dict(sticky)
        merged["status"] = "active"
        merged["evidence_source"] = "sticky_snapshot"
        merged["live_window_empty"] = False
        merged["live_window_partial"] = True
        return merged
    if int(live_snapshot.get("covered_case_count", 0) or 0) > 0:
        _store()._persist_runtime_proof_section(
            repo_root=root,
            section="architecture_evaluation",
            payload=live_snapshot,
        )
        return live_snapshot
    if int(sticky.get("covered_case_count", 0) or 0) > 0 and sticky_compatible:
        merged = dict(sticky)
        merged["status"] = "active"
        merged["evidence_source"] = "sticky_snapshot"
        merged["live_window_empty"] = True
        return merged
    return live_snapshot


def load_runtime_evaluation_snapshot(
    *,
    repo_root: Path,
    bootstrap_limit: int = 24,
) -> dict[str, Any]:
    """Summarize benchmark-corpus coverage and drift against recent runtime packets."""

    root = Path(repo_root).resolve()
    odylith_switch = _store()._odylith_switch_snapshot(repo_root=root)
    if not bool(odylith_switch.get("enabled", True)):
        return _store()._odylith_disabled_evaluation_snapshot(
            repo_root=root,
            switch_snapshot=odylith_switch,
        )
    corpus = _store().odylith_context_cache.read_json_object(_store().optimization_evaluation_corpus_path(repo_root=root))
    if not isinstance(corpus, Mapping):
        corpus = {}
    cases = _store().odylith_benchmark_contract.packet_benchmark_scenarios(corpus)
    program = dict(corpus.get("program", {})) if isinstance(corpus.get("program"), Mapping) else {}
    architecture_snapshot = _architecture_evaluation_snapshot(
        repo_root=root,
        corpus=corpus,
        focus_limit=4,
        timing_limit=max(24, bootstrap_limit * 2),
    )

    def _normalized_program_snapshot(default_status: str) -> dict[str, str]:
        status = str(program.get("status", default_status)).strip().lower() or default_status
        active_wave_id = str(program.get("active_wave_id", "W2")).strip() or "W2"
        active_workstream_id = str(program.get("active_workstream_id", "B-241")).strip() or "B-241"
        if status == "complete":
            active_wave_id = ""
            active_workstream_id = ""
        return {
            "umbrella_id": str(program.get("umbrella_id", "B-238")).strip() or "B-238",
            "status": status,
            "active_wave_id": active_wave_id,
            "active_workstream_id": active_workstream_id,
        }

    if not cases:
        return {
            "contract": "evaluation_snapshot.v1",
            "version": "v1",
            "generated_utc": _store()._utc_now(),
            "odylith_switch": odylith_switch,
            "status": "unseeded",
            "program": _normalized_program_snapshot("planned"),
            "corpus_size": 0,
            "covered_case_count": 0,
            "satisfied_case_count": 0,
            "coverage_rate": 0.0,
            "satisfaction_rate": 0.0,
            "family_distribution": {},
            "status_distribution": {},
            "focus_cases": [],
            "architecture": architecture_snapshot,
            "recommendations": [
                "Benchmark corpus is not seeded yet; add Wave 2 benchmark cases before treating evaluation posture as meaningful."
            ],
        }

    packets = _store()._load_recent_bootstrap_packets(repo_root=root, bootstrap_limit=bootstrap_limit)
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    family_distribution = _store()._sorted_count_map([str(row.get("family", "")).strip() for row in cases])
    covered_count = 0
    satisfied_count = 0
    case_rows: list[dict[str, Any]] = []
    for case in cases:
        match_spec = dict(case.get("match", {})) if isinstance(case.get("match"), Mapping) else {}
        expect_spec = dict(case.get("expect", {})) if isinstance(case.get("expect"), Mapping) else {}
        latest_packet = next((packet for packet in packets if _store()._packet_matches_evaluation_case(packet, match_spec)), None)
        case_status = "unmatched"
        expectation_details: dict[str, Any] = {}
        if latest_packet is not None:
            covered_count += 1
            expectation_ok, expectation_details = _store()._packet_satisfies_evaluation_expectations(latest_packet, expect_spec)
            if expectation_ok:
                satisfied_count += 1
                case_status = "satisfied"
            else:
                case_status = "drift"
        case_rows.append(
            {
                "case_id": str(case.get("case_id", "")).strip(),
                "label": str(case.get("label", "")).strip(),
                "family": str(case.get("family", "")).strip(),
                "priority": str(case.get("priority", "medium")).strip().lower() or "medium",
                "status": case_status,
                "summary": str(case.get("summary", "")).strip(),
                "latest_match_utc": str(latest_packet.get("bootstrapped_at", "")).strip() if latest_packet else "",
                "matched_workstream": str(latest_packet.get("workstream", "")).strip() if latest_packet else "",
                "observed_packet_state": str(latest_packet.get("packet_state", "")).strip() if latest_packet else "",
                "expected_packet_state": sorted(_store()._expected_token_set(expect_spec.get("packet_state"))),
                "expectation_details": expectation_details,
            }
        )
    case_rows.sort(
        key=lambda row: (
            {"drift": 0, "unmatched": 1, "satisfied": 2}.get(str(row.get("status", "")).strip(), 9),
            priority_order.get(str(row.get("priority", "medium")).strip(), 9),
            str(row.get("label", "")).strip(),
        )
    )
    corpus_size = len(cases)
    coverage_rate = round(covered_count / max(1, corpus_size), 3)
    satisfaction_rate = round(satisfied_count / max(1, covered_count), 3) if covered_count else 0.0
    status_distribution = _store()._sorted_count_map([str(row.get("status", "")).strip() for row in case_rows])
    recommendations: list[str] = []
    if not packets:
        recommendations.append(
            f"Benchmark corpus is seeded but no recent runtime packet evidence is available yet; run `{_store().display_command('context-engine', '--repo-root', '.', 'bootstrap-session', '<path>')}` on a benchmarked slice."
        )
    drift_cases = [str(row.get("label", "")).strip() for row in case_rows if str(row.get("status", "")).strip() == "drift"]
    unmatched_cases = [str(row.get("label", "")).strip() for row in case_rows if str(row.get("status", "")).strip() == "unmatched"]
    if drift_cases:
        recommendations.append(
            f"Recent packets drifted from expected posture for {', '.join(drift_cases[:2])}; inspect the latest matching bootstrap packet before widening the next tuning change."
        )
    if unmatched_cases:
        recommendations.append(
            f"Uncovered benchmark cases remain: {', '.join(unmatched_cases[:2])}. Exercise those slices before treating Wave 2 coverage as representative."
        )
    if not recommendations:
        recommendations.append(
            "Wave 2 benchmark coverage is healthy on the current sample; use these cases as the comparison baseline for later routing or retrieval changes."
        )
    return {
        "contract": "evaluation_snapshot.v1",
        "version": "v1",
        "generated_utc": _store()._utc_now(),
        "odylith_switch": odylith_switch,
        "status": "active" if packets else "seeded_no_evidence",
        "program": _normalized_program_snapshot("active"),
        "corpus_size": corpus_size,
        "covered_case_count": covered_count,
        "satisfied_case_count": satisfied_count,
        "coverage_rate": coverage_rate,
        "satisfaction_rate": satisfaction_rate,
        "family_distribution": family_distribution,
        "status_distribution": status_distribution,
        "focus_cases": case_rows[:4],
        "architecture": architecture_snapshot,
        "recommendations": recommendations[:3],
    }
