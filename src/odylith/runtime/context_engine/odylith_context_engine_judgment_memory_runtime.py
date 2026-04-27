"""Judgment-memory synthesis for the context-engine runtime memory snapshot."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence


def build_judgment_memory_snapshot(
    *,
    context_engine_store: Any,
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
    plan_done_rows.sort(
        key=lambda row: (str(row.get("Updated", "")).strip(), str(row.get("Created", "")).strip()),
        reverse=True,
    )
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
        if str(row.get("Severity", "")).strip().lower() in context_engine_store._BUG_CRITICAL_SEVERITIES
    ]
    from odylith.runtime.evaluation import odylith_benchmark_runner

    runtime_benchmark_report = odylith_benchmark_runner.load_latest_runtime_benchmark_report(repo_root=root)
    benchmark_report = (
        dict(runtime_benchmark_report)
        if isinstance(runtime_benchmark_report, Mapping) and runtime_benchmark_report
        else dict(benchmark_report)
    )
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
    benchmark_path = (context_engine_store.runtime_root(repo_root=root) / "odylith-benchmarks" / "latest.v1.json").resolve()
    benchmark_path_ref = context_engine_store._relative_repo_path(repo_root=root, path=benchmark_path)

    decision_items: list[dict[str, Any]] = []
    for row in plan_done_rows[:3]:
        backlog_id = context_engine_store._workstream_token(str(row.get("Backlog", "")).strip())
        plan_path_ref = context_engine_store._parse_link_target(str(row.get("Plan", "")))
        title = backlog_titles.get(backlog_id) or context_engine_store._humanize_slug(Path(plan_path_ref or "done-plan").stem)
        decision_items.append(
            context_engine_store._judgment_memory_item(
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
            context_engine_store._judgment_memory_item(
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
    decision_area = context_engine_store._judgment_memory_area(
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
            context_engine_store._provenance_item(
                label="Done plans",
                source_kind="repo_truth",
                path="odylith/technical-plans/done/",
                updated_utc=str(plan_done_rows[0].get("Updated", "")).strip() if plan_done_rows else "",
                trust="authoritative",
            ),
            context_engine_store._provenance_item(
                label="Benchmark report",
                source_kind="benchmark_report",
                path=benchmark_path_ref if benchmark_comparison else "",
                updated_utc=str(benchmark_report.get("generated_utc", "")).strip(),
                trust="derived_runtime",
            ),
        ],
    )

    daemon_usage = context_engine_store.odylith_context_cache.read_json_object(context_engine_store.daemon_usage_path(repo_root=root))
    workspace_key = str(daemon_usage.get("workspace_key", "")).strip() if isinstance(daemon_usage, Mapping) else ""
    branch_name = context_engine_store._git_branch_name(repo_root=root)
    head_oid = context_engine_store._git_head_oid(repo_root=root)
    actor_name = context_engine_store._git_stdout(repo_root=root, args=("config", "--get", "user.name"))
    actor_email = context_engine_store._git_stdout(repo_root=root, args=("config", "--get", "user.email"))
    actor_label = " ".join(token for token in (actor_name, f"<{actor_email}>") if token).strip() or str(os.environ.get("USER", "")).strip()
    workspace_items: list[dict[str, Any]] = []
    if workspace_key or branch_name or head_oid:
        workspace_items.append(
            context_engine_store._judgment_memory_item(
                kind="workspace",
                summary=(
                    f"Workspace `{workspace_key or context_engine_store.workspace_daemon_key(repo_root=root)}` is on `{branch_name or 'detached'}` at "
                    f"{(head_oid[:8] if head_oid else 'unknown')} with {len(repo_dirty_paths)} meaningful dirty path(s)."
                ),
                recorded_utc=(
                    str(daemon_usage.get("last_request_utc", "")).strip()
                    if isinstance(daemon_usage, Mapping)
                    else projection_updated_utc
                ),
                source_path=context_engine_store._relative_repo_path(repo_root=root, path=context_engine_store.daemon_usage_path(repo_root=root)),
                source_kind="runtime_state",
                surfaces=("context_engine", "sessions"),
            )
        )
    if actor_label:
        workspace_items.append(
            context_engine_store._judgment_memory_item(
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
            context_engine_store._judgment_memory_item(
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
    workspace_area = context_engine_store._judgment_memory_area(
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
            context_engine_store._provenance_item(
                label="Git identity",
                source_kind="local_git",
                updated_utc=projection_updated_utc,
                trust="local_observation",
            ),
            context_engine_store._provenance_item(
                label="Daemon usage",
                source_kind="runtime_state",
                path=context_engine_store._relative_repo_path(repo_root=root, path=context_engine_store.daemon_usage_path(repo_root=root)),
                updated_utc=str(daemon_usage.get("last_request_utc", "")).strip() if isinstance(daemon_usage, Mapping) else "",
                trust="derived_runtime",
            ),
        ],
    )

    outcome_items: list[dict[str, Any]] = []
    if benchmark_comparison:
        outcome_items.append(
            context_engine_store._judgment_memory_item(
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
        outcome_items.append(
            context_engine_store._judgment_memory_item(
                kind="finished_workstream",
                summary=f"{str(row.get('title', '')).strip() or str(row.get('idea_id', '')).strip()} is now retained as a finished governed outcome.",
                recorded_utc=str(row.get("date", "")).strip() or str(row.get("updated_utc", "")).strip(),
                source_path=context_engine_store._parse_link_target(str(row.get("link", ""))),
                source_kind="repo_truth",
                surfaces=("radar",),
            )
        )
    outcome_state = "strong" if len(outcome_items) >= 2 else "partial" if outcome_items else "cold"
    outcome_area = context_engine_store._judgment_memory_area(
        key="outcomes",
        label="Outcome memory",
        state=outcome_state,
        summary=(
            f"{len(outcome_items)} outcome signal(s) are retained from benchmark proof and finished workstreams."
            if outcome_items
            else "No durable outcome memory has been retained yet."
        ),
        items=outcome_items[:4],
        provenance=[
            context_engine_store._provenance_item(
                label="Finished workstreams",
                source_kind="repo_truth",
                path="odylith/radar/source/INDEX.md",
                updated_utc=str(backlog_projection.get("updated_utc", "")).strip(),
                trust="authoritative",
            ),
            context_engine_store._provenance_item(
                label="Benchmark report",
                source_kind="benchmark_report",
                path=benchmark_path_ref if benchmark_comparison else "",
                updated_utc=str(benchmark_report.get("generated_utc", "")).strip(),
                trust="derived_runtime",
            ),
        ],
    )

    retained_open_bugs = critical_open_bugs[:3]
    negative_items: list[dict[str, Any]] = []
    for row in retained_open_bugs:
        negative_items.append(
            context_engine_store._judgment_memory_item(
                kind="open_bug",
                summary=f"{str(row.get('Title', '')).strip() or str(row.get('Bug ID', '')).strip()} remains {str(row.get('Severity', '')).strip() or 'open'} and open.",
                recorded_utc=str(row.get("Date", "")).strip(),
                source_path=context_engine_store._parse_link_target(str(row.get("Link", ""))),
                source_kind="casebook",
                severity=str(row.get("Severity", "")).strip(),
                surfaces=("casebook",),
            )
        )
    if benchmark_comparison and float(benchmark_comparison.get("median_total_payload_token_delta", 0.0) or 0.0) > 0.0:
        negative_items.append(
            context_engine_store._judgment_memory_item(
                kind="budget_drag",
                summary=(
                    f"Total Odylith payload is still {float(benchmark_comparison.get('median_total_payload_token_delta', 0.0) or 0.0):+.1f} tokens heavier than the full-scan baseline."
                ),
                recorded_utc=str(benchmark_report.get("generated_utc", "")).strip(),
                source_path=benchmark_path_ref,
                source_kind="benchmark_report",
                severity="P1" if benchmark_checks else "",
                next_move="Trim runtime-contract overhead without giving back recall or validation gains.",
                surfaces=("benchmark", "packet_budget"),
            )
        )
    negative_state = "strong" if len(negative_items) >= 2 or retained_open_bugs else "partial" if negative_items else "cold"
    negative_area = context_engine_store._judgment_memory_area(
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
            context_engine_store._provenance_item(
                label="Casebook bugs",
                source_kind="casebook",
                path="odylith/casebook/bugs/INDEX.md",
                updated_utc=context_engine_store._latest_updated_utc(*[str(row.get("Date", "")).strip() for row in retained_open_bugs]),
                trust="authoritative",
            ),
            context_engine_store._provenance_item(
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
    starter_status = "current" if str(current_starter.get("path", "")).strip() else "inferred" if starter_path else ""
    starter_workstream = context_engine_store._workstream_token(str(previous_starter.get("workstream_id", "")).strip())
    first_seen_utc = str(previous_starter.get("first_seen_utc", "")).strip()
    onboarding_items: list[dict[str, Any]] = []
    if starter_path:
        for packet in recent_bootstrap_packets:
            packet_workstream = context_engine_store._payload_workstream_hint(packet)
            packet_paths = [
                str(token).strip()
                for token in packet.get("changed_paths", [])
                if isinstance(packet.get("changed_paths"), list) and str(token).strip()
            ]
            packet_path = packet_paths[0] if packet_paths else ""
            if (
                packet_path
                and context_engine_store._repo_paths_overlap(repo_root=root, left=packet_path, right=starter_path)
                and not first_seen_utc
            ):
                first_seen_utc = str(packet.get("bootstrapped_at", "")).strip()
                starter_workstream = packet_workstream or starter_workstream
                break
        if not starter_workstream:
            for session_row in active_sessions:
                session_workstream = context_engine_store._workstream_token(str(session_row.get("workstream", "")).strip())
                session_path = str(session_row.get("path", "")).strip()
                if (
                    session_workstream
                    and session_path
                    and context_engine_store._repo_paths_overlap(repo_root=root, left=session_path, right=starter_path)
                ):
                    starter_workstream = session_workstream
                    if not first_seen_utc:
                        first_seen_utc = str(session_row.get("started_utc", "")).strip()
                    break
    if starter_path:
        onboarding_items.append(
            context_engine_store._judgment_memory_item(
                kind="starter_slice",
                summary=(
                    f"Odylith retains the first governed slice at `{starter_path}`"
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
            context_engine_store._judgment_memory_item(
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
        "last_seen_utc": projection_updated_utc or context_engine_store._utc_now(),
        "status": starter_status,
    }
    onboarding_area = context_engine_store._judgment_memory_area(
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
            context_engine_store._provenance_item(
                label="Shell onboarding",
                source_kind="onboarding_observation",
                updated_utc=projection_updated_utc,
                trust="derived_runtime",
            ),
            context_engine_store._provenance_item(
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
            context_engine_store._judgment_memory_item(
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
            context_engine_store._judgment_memory_item(
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
    if (
        str(benchmark_acceptance.get("status", "")).strip().lower() in {"provisional_pass", "pass"}
        and float(benchmark_comparison.get("median_total_payload_token_delta", 0.0) or 0.0) > 0.0
    ):
        contradiction_items.append(
            context_engine_store._judgment_memory_item(
                kind="quality_vs_payload_cost",
                summary="Benchmark proof is green, but the full Odylith runtime payload is still materially heavier than baseline.",
                recorded_utc=str(benchmark_report.get("generated_utc", "")).strip(),
                source_path=benchmark_path_ref,
                source_kind="benchmark_report",
                next_move="Reduce runtime-contract overhead without giving back the hard-quality gain.",
                surfaces=("benchmark", "packet_budget"),
            )
        )
    if critical_open_bugs and not active_plan_rows:
        contradiction_items.append(
            context_engine_store._judgment_memory_item(
                kind="bugs_without_active_plan",
                summary=(
                    f"Casebook still carries {len(critical_open_bugs)} open critical bug(s), but Plans has no active implementation lane bound to them."
                ),
                recorded_utc=context_engine_store._latest_updated_utc(*[str(row.get("Date", "")).strip() for row in critical_open_bugs]),
                source_path="odylith/casebook/bugs/INDEX.md",
                source_kind="casebook",
                next_move="Bind the current critical bug cluster to one governed implementation slice before more fixes drift outside plan truth.",
                surfaces=("casebook", "technical_plans", "radar"),
            )
        )
    if critical_open_bugs and str(benchmark_acceptance.get("status", "")).strip().lower() in {"provisional_pass", "pass"}:
        contradiction_items.append(
            context_engine_store._judgment_memory_item(
                kind="proof_vs_open_risk",
                summary="Benchmark proof is green, but critical open bugs still keep the release/install lane operationally risky.",
                recorded_utc=context_engine_store._latest_updated_utc(
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
            context_engine_store._judgment_memory_item(
                kind="suggested_without_bootstrap",
                summary="Odylith can name a first governed slice, but no bootstrap-session evidence has been captured for it yet.",
                recorded_utc=projection_updated_utc,
                source_kind="onboarding_observation",
                next_move="Run one grounded bootstrap session on the suggested slice to warm judgment memory.",
                surfaces=("dashboard", "bootstrap"),
            )
        )
    contradiction_state = "strong" if len(contradiction_items) >= 2 else "partial" if contradiction_items else "cold"
    contradiction_area = context_engine_store._judgment_memory_area(
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
            context_engine_store._provenance_item(
                label="Repo truth and runtime posture",
                source_kind="repo_truth",
                path="odylith/radar/source/INDEX.md",
                updated_utc=str(backlog_projection.get("updated_utc", "")).strip(),
                trust="authoritative",
            ),
            context_engine_store._provenance_item(
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
        context_engine_store._judgment_memory_item(
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
    freshness_area = context_engine_store._judgment_memory_area(
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
            context_engine_store._provenance_item(
                label="Runtime snapshot timestamps",
                source_kind="runtime_state",
                path=":.odylith/runtime/",
                updated_utc=projection_updated_utc,
                trust="derived_runtime",
            ),
        ],
    )

    areas = [
        decision_area,
        workspace_area,
        outcome_area,
        negative_area,
        onboarding_area,
        contradiction_area,
        freshness_area,
    ]
    kind_counts: dict[str, int] = {}
    for area in areas:
        for item in area.get("items", []):
            if not isinstance(item, Mapping):
                continue
            kind = str(item.get("kind", "")).strip()
            if not kind:
                continue
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
    provenance_items = [
        context_engine_store._judgment_memory_item(
            kind="kind_presence",
            summary=f"{context_engine_store._humanize_slug(kind)} contributes to {count} judgment area(s).",
            recorded_utc=projection_updated_utc,
            source_kind="derived_runtime",
        )
        for kind, count in sorted(kind_counts.items())
    ]
    provenance_area = context_engine_store._judgment_memory_area(
        key="provenance",
        label="Provenance memory",
        state="strong" if provenance_items else "cold",
        summary=(
            f"{len(kind_counts)} durable judgment signal kind(s) are currently retained."
            if provenance_items
            else "No retained judgment provenance is available yet."
        ),
        items=provenance_items[:4],
        provenance=[
            context_engine_store._provenance_item(
                label="Judgment memory cache",
                source_kind="runtime_state",
                path=context_engine_store._relative_repo_path(repo_root=root, path=context_engine_store.judgment_memory_path(repo_root=root)),
                updated_utc=projection_updated_utc,
                trust="derived_runtime",
            ),
        ],
    )
    areas.append(provenance_area)

    counts: dict[str, int] = {}
    gaps: list[str] = []
    for area in areas:
        state = str(area.get("state", "")).strip() or "unknown"
        counts[state] = counts.get(state, 0) + 1
        if state in {"partial", "cold"}:
            summary = str(area.get("summary", "")).strip()
            label = str(area.get("label", "")).strip() or "Judgment area"
            gaps.append(f"{label}: {summary}" if summary else label)
    return {
        "contract": "judgment_memory.v1",
        "version": "v1",
        "generated_utc": context_engine_store._utc_now(),
        "storage_path": context_engine_store._relative_repo_path(repo_root=root, path=context_engine_store.judgment_memory_path(repo_root=root)),
        "starter_slice": starter_slice_payload,
        "status": context_engine_store._memory_snapshot_status_from_counts(counts),
        "headline": context_engine_store._judgment_memory_headline(areas),
        "counts": counts,
        "gap_count": len(gaps),
        "areas": areas,
        "gaps": gaps,
    }
