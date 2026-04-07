"""Runtime payload builder extracted from the Compass runtime."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import datetime as dt
from pathlib import Path
from typing import Any, Mapping

from odylith.runtime.surfaces import compass_execution_focus_runtime


def _host():
    from odylith.runtime.surfaces import compass_dashboard_runtime as host

    return host


def _scoped_brief_provider_allowed(*, refresh_profile: str) -> bool:
    profile = str(refresh_profile or "full").strip().lower() or "full"
    if profile == "shell-safe":
        return False
    # Full refresh now regenerates scoped standup briefs too so the selected
    # workstream view does not stay pinned to deterministic local narration
    # after a completed refresh. Reusable exact-cache hits still keep repeated
    # refreshes bounded inside the narrator.
    if profile == "full":
        return True
    return False


def _is_default_traceability_warning(row: Mapping[str, Any]) -> bool:
    severity = str(row.get("severity", "")).strip().lower()
    audience = str(row.get("audience", "operator")).strip().lower() or "operator"
    surface_visibility = str(row.get("surface_visibility", "")).strip().lower()
    if surface_visibility not in {"default", "diagnostics"}:
        if audience == "maintainer" or severity not in {"warning", "error"}:
            surface_visibility = "diagnostics"
        else:
            surface_visibility = "default"
    return audience != "maintainer" and surface_visibility == "default" and severity in {"warning", "error"}


def _build_runtime_payload(
    *,
    repo_root: Path,
    backlog_index_path: Path,
    plan_index_path: Path,
    bugs_index_path: Path,
    traceability_graph_path: Path,
    mermaid_catalog_path: Path,
    codex_stream_path: Path,
    max_review_age_days: int,
    active_window_minutes: int,
    runtime_mode: str,
    refresh_profile: str = "full",
) -> dict[str, Any]:
    host = _host()
    _load_json = host._load_json
    execution_wave_view_model = host.execution_wave_view_model
    _load_component_index_runtime = host._load_component_index_runtime
    _parse_backlog_rows = host._parse_backlog_rows
    _parse_plan_active_rows = host._parse_plan_active_rows
    _parse_bugs_rows = host._parse_bugs_rows
    _COMPASS_TZ = host._COMPASS_TZ
    _git_identity = host._git_identity
    _collect_git_commits = host._collect_git_commits
    _collect_git_local_changes = host._collect_git_local_changes
    _collect_workstream_path_index = host._collect_workstream_path_index
    _map_paths_to_workstreams = host._map_paths_to_workstreams
    _safe_iso = host._safe_iso
    _local_change_event_ts = host._local_change_event_ts
    _local_change_summary = host._local_change_summary
    _build_plan_timeline_events = host._build_plan_timeline_events
    _build_bug_timeline_events = host._build_bug_timeline_events
    _load_codex_stream_events = host._load_codex_stream_events
    _normalize_repo_token = host._normalize_repo_token
    _resolve = host._resolve
    _parse_markdown_metadata_and_sections = host._parse_markdown_metadata_and_sections
    _collect_plan_progress = host._collect_plan_progress
    _build_window_activity = host._build_window_activity
    _DATE_RE = host._DATE_RE
    _timeline_projection = host._timeline_projection
    _split_workstream_ids = host._split_workstream_ids
    _cost_base_index = host._cost_base_index
    _cost_with_activity = host._cost_with_activity
    _component_rows_for_workstream = host._component_rows_for_workstream
    _select_timeline_source_events = host._select_timeline_source_events
    _event_public_payload = host._event_public_payload
    _build_prompt_transactions = host._build_prompt_transactions
    _extract_link_target = host._extract_link_target
    _select_current_workstream_rows = host._select_current_workstream_rows
    _filter_execution_wave_payload_for_current_context = host._filter_execution_wave_payload_for_current_context
    _resolve_index_link_to_repo_path = host._resolve_index_link_to_repo_path
    _extract_workstream_tokens_from_text = host._extract_workstream_tokens_from_text
    _parse_date = host._parse_date
    _WORKSTREAM_ID_RE = host._WORKSTREAM_ID_RE
    _collect_recent_completed_plan_rows = host._collect_recent_completed_plan_rows
    _is_bug_date_within_window = host._is_bug_date_within_window
    _self_host_snapshot = host._self_host_snapshot
    _self_host_risk_rows = host._self_host_risk_rows
    _build_window_event_counts = host._build_window_event_counts
    _filter_transactions_by_window = host._filter_transactions_by_window
    _is_generated_only_local_change_event = host._is_generated_only_local_change_event
    _is_generated_only_transaction = host._is_generated_only_transaction
    _build_risk_posture_summary = host._build_risk_posture_summary
    _scope_risk_rows = host._scope_risk_rows
    _build_global_standup_fact_packet = host._build_global_standup_fact_packet
    _global_brief_provider_allowed = host._global_brief_provider_allowed
    _build_scoped_standup_fact_packet = host._build_scoped_standup_fact_packet
    _as_repo_path = host._as_repo_path
    _COMPASS_TIMEZONE = host._COMPASS_TIMEZONE
    _compact_odylith_runtime_summary = host._compact_odylith_runtime_summary
    _TIMELINE_EVENT_LOOKBACK_HOURS = host._TIMELINE_EVENT_LOOKBACK_HOURS
    _TIMELINE_EVENT_MAX_ROWS = host._TIMELINE_EVENT_MAX_ROWS
    _DEFAULT_RECENT_FOCUS_WINDOW_MINUTES = host._DEFAULT_RECENT_FOCUS_WINDOW_MINUTES
    governance = host.governance
    odylith_reasoning = host.odylith_reasoning
    compass_standup_brief_narrator = host.compass_standup_brief_narrator
    odylith_context_engine_store = host.odylith_context_engine_store
    _build_execution_focus_payload = compass_execution_focus_runtime._build_execution_focus_payload
    traceability_graph = _load_json(traceability_graph_path)
    execution_waves_all = execution_wave_view_model.build_execution_wave_view_payload(traceability_graph)
    mermaid_catalog = _load_json(mermaid_catalog_path)
    component_index = _load_component_index_runtime(
        repo_root=repo_root,
        runtime_mode=runtime_mode,
    )

    active_backlog_rows, execution_backlog_rows = _parse_backlog_rows(
        repo_root=repo_root,
        index_path=backlog_index_path,
        runtime_mode=runtime_mode,
    )
    active_plan_rows = _parse_plan_active_rows(
        repo_root=repo_root,
        index_path=plan_index_path,
        runtime_mode=runtime_mode,
    )
    bug_rows = _parse_bugs_rows(
        repo_root=repo_root,
        index_path=bugs_index_path,
        runtime_mode=runtime_mode,
    )

    now = dt.datetime.now(tz=_COMPASS_TZ)
    now_utc = dt.datetime.now(tz=dt.timezone.utc)
    today = now.date()

    identity_name, identity_email = _git_identity(repo_root)
    commits = _collect_git_commits(
        repo_root,
        since_hours=48,
        my_name=identity_name,
        my_email=identity_email,
    )
    local_changes = _collect_git_local_changes(repo_root)

    ws_path_index = _collect_workstream_path_index(
        repo_root=repo_root,
        traceability_graph=traceability_graph,
        mermaid_catalog=mermaid_catalog,
    )

    events: list[dict[str, Any]] = []
    for commit in commits:
        files = [str(item) for item in commit.get("files", []) if str(item).strip()]
        ws_ids = _map_paths_to_workstreams(files, ws_path_index)
        ts = commit.get("ts")
        if not isinstance(ts, dt.datetime):
            continue
        events.append(
            {
                "id": f"commit:{commit.get('sha', '')}",
                "kind": "commit",
                "ts": ts.astimezone(_COMPASS_TZ),
                "ts_iso": _safe_iso(ts),
                "summary": str(commit.get("subject", "")).strip() or "Commit",
                "author": str(commit.get("author_name", "")).strip(),
                "sha": str(commit.get("sha", "")).strip(),
                "files": files,
                "workstreams": ws_ids,
                "source": "git",
            }
        )

    for row in local_changes:
        path = str(row.get("path", "")).strip()
        ws_ids = _map_paths_to_workstreams([path], ws_path_index)
        status = str(row.get("status", "")).strip() or "M"
        change_ts = _local_change_event_ts(
            repo_root=repo_root,
            path=path,
            fallback=now,
        )
        events.append(
            {
                "id": f"local:{status}:{path}",
                "kind": "local_change",
                "ts": change_ts,
                "ts_iso": _safe_iso(change_ts),
                "summary": _local_change_summary(status_token=status, path=path),
                "author": "local",
                "sha": "",
                "files": [path],
                "workstreams": ws_ids,
                "source": "local",
            }
        )

    events.extend(
        _build_plan_timeline_events(
            repo_root=repo_root,
            now=now,
            plan_index_path=plan_index_path,
            active_plan_rows=active_plan_rows,
            ws_path_index=ws_path_index,
        )
    )
    events.extend(
        _build_bug_timeline_events(
            repo_root=repo_root,
            now=now,
            bugs_index_path=bugs_index_path,
            bug_rows=bug_rows,
            ws_path_index=ws_path_index,
        )
    )
    events.extend(
        _load_codex_stream_events(
            repo_root=repo_root,
            stream_path=codex_stream_path,
            ws_path_index=ws_path_index,
        )
    )

    events.sort(key=lambda item: item.get("ts", now), reverse=True)

    workstream_rows = traceability_graph.get("workstreams", [])
    ws_payloads: list[dict[str, Any]] = []

    active_plan_map: dict[str, str] = {}
    for row in active_plan_rows:
        backlog_token = str(row.get("Backlog", "")).strip().strip("`")
        plan_token = str(row.get("Plan", "")).strip().strip("`")
        if backlog_token:
            active_plan_map[backlog_token] = plan_token

    for row in workstream_rows if isinstance(workstream_rows, list) else []:
        if not isinstance(row, Mapping):
            continue
        idea_id = str(row.get("idea_id", "")).strip()
        if not idea_id:
            continue

        idea_file = _normalize_repo_token(str(row.get("idea_file", "")), repo_root=repo_root)
        idea_path = _resolve(repo_root, idea_file) if idea_file else None
        metadata: dict[str, str] = {}
        sections: dict[str, str] = {}
        if idea_path is not None and idea_path.is_file():
            metadata, sections = _parse_markdown_metadata_and_sections(idea_path)

        promoted_plan = str(row.get("promoted_to_plan", "")).strip()
        plan_path_token = promoted_plan or active_plan_map.get(idea_id, "")
        plan_progress = _collect_plan_progress(_resolve(repo_root, plan_path_token) if plan_path_token else Path(""))

        ws_events_48 = [
            event
            for event in events
            if idea_id in [str(token) for token in event.get("workstreams", [])]
        ]
        ws_events_24 = _build_window_activity(ws_events_48, now=now, hours=24)

        commit_48 = sum(1 for event in ws_events_48 if event.get("kind") == "commit")
        local_48 = sum(1 for event in ws_events_48 if event.get("kind") == "local_change")
        commit_24 = sum(1 for event in ws_events_24 if event.get("kind") == "commit")
        local_24 = sum(1 for event in ws_events_24 if event.get("kind") == "local_change")

        last_activity_ts: dt.datetime | None = None
        if ws_events_48:
            token = ws_events_48[0].get("ts")
            if isinstance(token, dt.datetime):
                last_activity_ts = token

        start_date = ""
        plan_created = str(plan_progress.get("created", "")).strip()
        if _DATE_RE.fullmatch(plan_created):
            start_date = plan_created
        else:
            idea_date = str(metadata.get("date", "")).strip()
            if _DATE_RE.fullmatch(idea_date):
                start_date = idea_date

        age_days = 0
        if start_date:
            try:
                age_days = max(0, (today - dt.date.fromisoformat(start_date)).days)
            except ValueError:
                age_days = 0

        eta_days, eta_confidence = _timeline_projection(
            age_days=age_days,
            total_tasks=int(plan_progress.get("total_tasks", 0) or 0),
            done_tasks=int(plan_progress.get("done_tasks", 0) or 0),
        )
        lineage = {
            "reopens": _split_workstream_ids(row.get("workstream_reopens", "")),
            "reopened_by": _split_workstream_ids(row.get("workstream_reopened_by", "")),
            "split_from": _split_workstream_ids(row.get("workstream_split_from", "")),
            "split_into": _split_workstream_ids(row.get("workstream_split_into", "")),
            "merged_into": _split_workstream_ids(row.get("workstream_merged_into", "")),
            "merged_from": _split_workstream_ids(row.get("workstream_merged_from", "")),
        }

        base_cost = _cost_base_index(
            sizing=str(metadata.get("sizing", "")).strip(),
            complexity=str(metadata.get("complexity", "")).strip(),
        )
        cost_24, band_24 = _cost_with_activity(base_cost, commit_count=commit_24, local_count=local_24)
        cost_48, band_48 = _cost_with_activity(base_cost, commit_count=commit_48, local_count=local_48)

        ws_payloads.append(
            {
                "idea_id": idea_id,
                "title": str(row.get("title", "")).strip() or str(metadata.get("title", "")).strip() or idea_id,
                "status": str(row.get("status", "")).strip() or str(metadata.get("status", "")).strip(),
                "priority": str(metadata.get("priority", "")).strip(),
                "sizing": str(metadata.get("sizing", "")).strip(),
                "complexity": str(metadata.get("complexity", "")).strip(),
                "ordering_score": str(metadata.get("ordering_score", "")).strip(),
                "implemented_summary": str(metadata.get("implemented_summary", "")).strip(),
                "why": {
                    "problem": str(sections.get("Problem", "")).strip(),
                    "customer": str(sections.get("Customer", "")).strip(),
                    "proposed_solution": str(sections.get("Proposed Solution", "")).strip(),
                    "opportunity": str(sections.get("Opportunity", "")).strip(),
                    "why_now": str(sections.get("Why Now", "")).strip(),
                    "founder_pov": str(sections.get("Product View", sections.get("Founder POV", ""))).strip(),
                },
                "links": {
                    "idea_file": idea_file,
                    "plan_file": _normalize_repo_token(plan_path_token),
                },
                "registry_components": _component_rows_for_workstream(
                    component_index=component_index,
                    workstream_id=idea_id,
                ),
                "execution_wave_programs": execution_waves_all.get("workstreams", {}).get(idea_id, []),
                "plan": {
                    "created": str(plan_progress.get("created", "")).strip(),
                    "updated": str(plan_progress.get("updated", "")).strip(),
                    "total_tasks": int(plan_progress.get("total_tasks", 0) or 0),
                    "done_tasks": int(plan_progress.get("done_tasks", 0) or 0),
                    "progress_ratio": float(plan_progress.get("progress_ratio", 0.0) or 0.0),
                    "next_tasks": [str(item) for item in plan_progress.get("next_tasks", [])],
                },
                "activity": {
                    "24h": {
                        "commit_count": commit_24,
                        "local_change_count": local_24,
                        "file_touch_count": len({file for event in ws_events_24 for file in event.get("files", [])}),
                    },
                    "48h": {
                        "commit_count": commit_48,
                        "local_change_count": local_48,
                        "file_touch_count": len({file for event in ws_events_48 for file in event.get("files", [])}),
                    },
                },
                "timeline": {
                    "start_date": start_date,
                    "last_activity_iso": _safe_iso(last_activity_ts) if last_activity_ts else "",
                    "age_days": age_days,
                    "eta_days": eta_days,
                    "eta_confidence": eta_confidence,
                },
                "lineage": lineage,
                "cost": {
                    "base_index": base_cost,
                    "24h": {"index": cost_24, "band": band_24},
                    "48h": {"index": cost_48, "band": band_48},
                },
            }
        )

    ws_payloads.sort(key=lambda row: (str(row.get("status", "")) not in {"planning", "implementation"}, str(row.get("idea_id", ""))))
    all_ws_payloads = list(ws_payloads)

    timeline_source_events = _select_timeline_source_events(
        events=events,
        now=now,
        lookback_hours=_TIMELINE_EVENT_LOOKBACK_HOURS,
        max_rows=_TIMELINE_EVENT_MAX_ROWS,
    )
    timeline_events = [_event_public_payload(event) for event in timeline_source_events]
    timeline_transactions = _build_prompt_transactions(
        events=timeline_source_events,
        inactivity_minutes=2,
        repo_root=repo_root,
    )
    execution_focus = _build_execution_focus_payload(
        transactions=timeline_transactions,
        now=now,
        active_window_minutes=active_window_minutes,
        recent_window_minutes=_DEFAULT_RECENT_FOCUS_WINDOW_MINUTES,
    )

    queued_top: list[dict[str, Any]] = []
    for row in active_backlog_rows[:6]:
        idea_id = str(row.get("idea_id", "")).strip()
        queued_top.append(
            {
                "rank": str(row.get("rank", "")).strip(),
                "idea_id": idea_id,
                "title": str(row.get("title", "")).strip(),
                "ordering_score": str(row.get("ordering_score", "")).strip(),
                "priority": str(row.get("priority", "")).strip(),
                "link": _normalize_repo_token(
                    _extract_link_target(str(row.get("link", ""))),
                    repo_root=repo_root,
                ),
            }
        )

    next_actions: list[dict[str, str]] = []
    next_action_keys: set[tuple[str, str]] = set()
    for ws in all_ws_payloads:
        if str(ws.get("status", "")).strip() not in {"planning", "implementation"}:
            continue
        tasks = ws.get("plan", {}).get("next_tasks", []) if isinstance(ws.get("plan"), Mapping) else []
        for task in tasks:
            token = str(task).strip()
            if not token:
                continue
            idea_id = str(ws.get("idea_id", "")).strip()
            key = (idea_id, token)
            if key in next_action_keys:
                continue
            next_action_keys.add(key)
            next_actions.append(
                {
                    "idea_id": idea_id,
                    "title": str(ws.get("title", "")).strip(),
                    "action": token,
                    "source": "plan",
                }
            )
            if len(next_actions) >= 8:
                break
        if len(next_actions) >= 8:
            break

    for row in queued_top:
        if len(next_actions) >= 12:
            break
        idea_id = str(row.get("idea_id", "")).strip()
        action = "Prepare promotion plan and implementation breakdown"
        key = (idea_id, action)
        if key in next_action_keys:
            continue
        next_action_keys.add(key)
        next_actions.append(
            {
                "idea_id": idea_id,
                "title": str(row.get("title", "")).strip(),
                "action": action,
                "source": "queue",
            }
        )

    window_events_by_hours: dict[int, list[dict[str, Any]]] = {}
    window_transactions_by_hours: dict[int, list[dict[str, Any]]] = {}
    recent_completed_rows_by_hours: dict[int, list[dict[str, str]]] = {}

    def _window_events(hours: int) -> list[dict[str, Any]]:
        cached = window_events_by_hours.get(hours)
        if cached is not None:
            return cached
        built = [
            row
            for row in _build_window_activity(events, now=now, hours=hours)
            if not _is_generated_only_local_change_event(row)
        ]
        window_events_by_hours[hours] = built
        return built

    def _window_transactions(hours: int) -> list[dict[str, Any]]:
        cached = window_transactions_by_hours.get(hours)
        if cached is not None:
            return cached
        built = [
            row
            for row in _filter_transactions_by_window(
                timeline_transactions,
                now=now,
                hours=hours,
            )
            if not _is_generated_only_transaction(row)
        ]
        window_transactions_by_hours[hours] = built
        return built

    def _recent_completed_rows(hours: int) -> list[dict[str, str]]:
        cached = recent_completed_rows_by_hours.get(hours)
        if cached is not None:
            return cached
        built = _collect_recent_completed_plan_rows(
            plan_index_path,
            repo_root=repo_root,
            now=now,
            hours=hours,
        )
        recent_completed_rows_by_hours[hours] = built
        return built

    recent_completed_rows_48h = _recent_completed_rows(48)
    ws_payloads = _select_current_workstream_rows(
        all_rows=all_ws_payloads,
        window_events_48h=_window_events(48),
        recent_completed_rows_48h=recent_completed_rows_48h,
    )
    execution_waves = _filter_execution_wave_payload_for_current_context(
        payload=execution_waves_all,
        current_workstream_rows=ws_payloads,
    )

    bug_items: list[dict[str, Any]] = []
    open_critical = 0
    for row in bug_rows:
        severity = str(row.get("Severity", "")).strip()
        status = odylith_context_engine_store.canonicalize_bug_status(str(row.get("Status", "")).strip())
        title = str(row.get("Title", "")).strip()
        date = str(row.get("Date", "")).strip()
        link = _resolve_index_link_to_repo_path(
            repo_root=repo_root,
            index_path=bugs_index_path,
            markdown_link=str(row.get("Link", "")),
        )
        is_open = status.lower() != "closed"
        is_critical = severity in {"P0", "P1"} and is_open
        if is_critical:
            open_critical += 1
        bug_workstreams = sorted(
            {
                *(_extract_workstream_tokens_from_text(title)),
                *(_extract_workstream_tokens_from_text(link)),
            }
        )
        bug_items.append(
            {
                "date": date,
                "title": title,
                "severity": severity,
                "status": status,
                "link": _normalize_repo_token(link, repo_root=repo_root),
                "is_open_critical": is_critical,
                "workstreams": bug_workstreams,
            }
        )

    warnings = traceability_graph.get("warning_items", [])
    traceability_risks: list[dict[str, str]] = []
    traceability_critical: list[dict[str, str]] = []
    traceability_warnings: list[dict[str, str]] = []
    if isinstance(warnings, list):
        for row in warnings:
            if not isinstance(row, Mapping):
                continue
            if not _is_default_traceability_warning(row):
                continue
            severity = str(row.get("severity", "")).strip().lower()
            entry = {
                "idea_id": str(row.get("idea_id", "")).strip(),
                "severity": severity,
                "category": str(row.get("category", "")).strip(),
                "message": str(row.get("message", "")).strip(),
                "action": str(row.get("action", "")).strip(),
                "source": str(row.get("source", "")).strip(),
            }
            traceability_risks.append(entry)
            if severity == "error":
                traceability_critical.append(entry)
            else:
                traceability_warnings.append(entry)

    stale_diagrams: list[dict[str, Any]] = []
    diagrams = mermaid_catalog.get("diagrams", [])
    if isinstance(diagrams, list):
        for row in diagrams:
            if not isinstance(row, Mapping):
                continue
            reviewed = _parse_date(str(row.get("last_reviewed_utc", "")).strip())
            if reviewed is None:
                continue
            age = (today - reviewed).days
            if age <= max_review_age_days:
                continue
            related_ws = _split_workstream_ids(row.get("related_workstreams", []))
            stale_diagrams.append(
                {
                    "diagram_id": str(row.get("diagram_id", "")).strip(),
                    "title": str(row.get("title", "")).strip(),
                    "last_reviewed_utc": reviewed.isoformat(),
                    "age_days": age,
                    "workstreams": related_ws,
                }
            )

    ws_index: dict[str, dict[str, Any]] = {}
    for row in all_ws_payloads:
        idea_id = str(row.get("idea_id", "")).strip()
        if idea_id:
            ws_index[idea_id] = row

    active_ws_rows = [
        row for row in all_ws_payloads if str(row.get("status", "")).strip() in {"planning", "implementation"}
    ]
    generated_utc = now_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    reasoning_config = odylith_reasoning.reasoning_config_from_env(repo_root=repo_root)
    reasoning_provider = odylith_reasoning.provider_from_config(
        reasoning_config,
        repo_root=repo_root,
        require_auto_mode=False,
        allow_implicit_local_provider=True,
    )

    self_host = _self_host_snapshot(repo_root=repo_root)
    self_host_risks = _self_host_risk_rows(snapshot=self_host, local_date=now.date().isoformat())

    def _summarize_window(hours: int) -> tuple[dict[str, int], dict[str, Any], dict[str, dict[str, Any]]]:
        window_events = _window_events(hours)
        window_transactions = _window_transactions(hours)
        commits_count = sum(1 for event in window_events if event.get("kind") == "commit")
        local_count = sum(1 for event in window_events if event.get("kind") == "local_change")
        event_counts_by_ws = _build_window_event_counts(window_events)
        touched_ws = [
            ws_id
            for ws_id, _ in sorted(
                event_counts_by_ws.items(),
                key=lambda item: (-int(item[1]), item[0]),
            )
            if ws_id
        ]
        touched_ws_set = set(touched_ws)
        recent_completed_rows = _recent_completed_rows(hours)
        active_ws = len(active_ws_rows)
        touched_active_ws = (
            len(
                {
                    str(row.get("idea_id", "")).strip()
                    for row in active_ws_rows
                    if str(row.get("idea_id", "")).strip() in touched_ws_set
                }
            )
            if active_ws_rows
            else 0
        )
        window_open_critical = sum(
            1
            for row in bug_items
            if bool(row.get("is_open_critical"))
            and _is_bug_date_within_window(
                date_token=str(row.get("date", "")).strip(),
                now=now,
                hours=hours,
            )
        )
        risk_posture_window = _build_risk_posture_summary(
            open_critical=window_open_critical,
            traceability_risks=traceability_risks,
            stale_diagrams=stale_diagrams,
        )
        global_risk_rows = _scope_risk_rows(
            ws_id=None,
            bug_items=bug_items,
            traceability_risks=traceability_risks,
            stale_diagrams=stale_diagrams,
        )
        kpis = {
            "commits": commits_count,
            "local_changes": local_count,
            "touched_workstreams": len(touched_ws_set),
            "active_workstreams": active_ws,
            "critical_risks": window_open_critical + len(traceability_critical) + len(stale_diagrams),
            "recent_completed_plans": len(recent_completed_rows),
            "active_touched_workstreams": touched_active_ws,
        }

        recent_completed: list[dict[str, str]] = []
        for item in recent_completed_rows:
            normalized: dict[str, str] = dict(item)
            backlog = str(item.get("backlog", "")).strip()
            ws = ws_index.get(backlog)
            if ws is not None:
                normalized["title"] = str(ws.get("title", "")).strip()
            recent_completed.append(normalized)

        focus_rows: list[dict[str, Any]] = []
        seen_focus_ids: set[str] = set()
        active_ids = {
            str(row.get("idea_id", "")).strip()
            for row in active_ws_rows
            if str(row.get("idea_id", "")).strip()
        }

        def _append_focus_row(ws_id: str) -> None:
            token = str(ws_id).strip()
            if not token or token in seen_focus_ids:
                return
            ws = ws_index.get(token)
            if ws is None:
                return
            seen_focus_ids.add(token)
            focus_rows.append(ws)

        for ws_id in touched_ws:
            if ws_id in active_ids:
                _append_focus_row(ws_id)
            if len(focus_rows) >= 2:
                break
        for ws_id in touched_ws:
            _append_focus_row(ws_id)
            if len(focus_rows) >= 2:
                break
        for item in recent_completed:
            _append_focus_row(str(item.get("backlog", "")).strip())
            if len(focus_rows) >= 2:
                break
        for row in active_ws_rows:
            _append_focus_row(str(row.get("idea_id", "")).strip())
            if len(focus_rows) >= 2:
                break
        for row in ws_payloads:
            _append_focus_row(str(row.get("idea_id", "")).strip())
            if len(focus_rows) >= 2:
                break

        focus_ids = {str(item.get("idea_id", "")).strip() for item in focus_rows if str(item.get("idea_id", "")).strip()}
        focus_actions = [item for item in next_actions if str(item.get("idea_id", "")).strip() in focus_ids]
        window_kpis = dict(kpis)
        if self_host_risks:
            window_kpis["critical_risks"] = int(window_kpis.get("critical_risks", 0) or 0) + len(self_host_risks)
        global_fact_packet = _build_global_standup_fact_packet(
            ws_rows=focus_rows,
            ws_index=ws_index,
            active_ws_rows=active_ws_rows,
            event_counts_by_ws=event_counts_by_ws,
            next_actions=focus_actions or next_actions,
            recent_completed=recent_completed,
            window_events=window_events,
            window_transactions=window_transactions,
            window_hours=hours,
            risk_rows=global_risk_rows,
            risk_summary=risk_posture_window,
            kpis=window_kpis,
            self_host_snapshot=self_host,
            self_host_risks=self_host_risks,
            now=now,
        )
        global_allow_provider = _global_brief_provider_allowed(
            repo_root=repo_root,
            fact_packet=global_fact_packet,
            window_hours=hours,
            refresh_profile=refresh_profile,
        )
        standup_global = compass_standup_brief_narrator.build_standup_brief(
            repo_root=repo_root,
            fact_packet=global_fact_packet,
            generated_utc=generated_utc,
            config=reasoning_config,
            provider=reasoning_provider,
            allow_provider=global_allow_provider,
            prefer_provider=global_allow_provider,
        )
        standup_scoped: dict[str, dict[str, Any]] = {}
        scoped_packets: list[tuple[str, dict[str, Any]]] = []
        # Scoped dashboard refresh stays bounded in shell-safe mode. Full
        # refresh can regenerate scoped provider briefs, but the work is fanned
        # out with a small worker pool so the shell path does not block on a
        # fully serial provider walk.
        scoped_allow_provider = _scoped_brief_provider_allowed(refresh_profile=refresh_profile)
        for ws in ws_payloads:
            ws_id = str(ws.get("idea_id", "")).strip()
            if not ws_id:
                continue
            scoped_risk_rows = _scope_risk_rows(
                ws_id=ws_id,
                bug_items=bug_items,
                traceability_risks=traceability_risks,
                stale_diagrams=stale_diagrams,
            )
            scoped_risk_summary = _build_risk_posture_summary(
                open_critical=len(scoped_risk_rows.get("bugs", [])),
                traceability_risks=scoped_risk_rows.get("traceability", []),
                stale_diagrams=scoped_risk_rows.get("stale_diagrams", []),
            )
            scoped_fact_packet = _build_scoped_standup_fact_packet(
                row=ws,
                next_actions=next_actions,
                recent_completed=recent_completed,
                window_events=window_events,
                window_transactions=window_transactions,
                window_hours=hours,
                risk_rows=scoped_risk_rows,
                risk_summary=scoped_risk_summary,
                self_host_snapshot=self_host,
                now=now,
            )
            scoped_packets.append((ws_id, scoped_fact_packet))

        def _build_scoped_brief(entry: tuple[str, dict[str, Any]]) -> tuple[str, dict[str, Any]]:
            ws_id, scoped_fact_packet = entry
            return ws_id, compass_standup_brief_narrator.build_standup_brief(
                repo_root=repo_root,
                fact_packet=scoped_fact_packet,
                generated_utc=generated_utc,
                config=reasoning_config,
                provider=None,
                allow_provider=scoped_allow_provider,
            )
        if scoped_allow_provider and len(scoped_packets) > 1:
            max_workers = min(4, len(scoped_packets))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for ws_id, brief in executor.map(_build_scoped_brief, scoped_packets):
                    standup_scoped[ws_id] = brief
        else:
            for ws_id, scoped_fact_packet in scoped_packets:
                built_ws_id, brief = _build_scoped_brief((ws_id, scoped_fact_packet))
                standup_scoped[built_ws_id] = brief

        return window_kpis, standup_global, standup_scoped

    kpi_24h, standup_brief_24h, standup_brief_scoped_24h = _summarize_window(24)
    kpi_48h, standup_brief_48h, standup_brief_scoped_48h = _summarize_window(48)
    digest_24h = compass_standup_brief_narrator.brief_to_digest_lines(standup_brief_24h)
    digest_48h = compass_standup_brief_narrator.brief_to_digest_lines(standup_brief_48h)
    digest_scoped_24h = {
        ws_id: compass_standup_brief_narrator.brief_to_digest_lines(brief)
        for ws_id, brief in standup_brief_scoped_24h.items()
    }
    digest_scoped_48h = {
        ws_id: compass_standup_brief_narrator.brief_to_digest_lines(brief)
        for ws_id, brief in standup_brief_scoped_48h.items()
    }
    governance_summary = governance.build_governance_summary(
        repo_root=repo_root,
        changed_paths=governance.collect_git_changed_paths(repo_root=repo_root),
        force=False,
        impact_mode="selective",
        stream_path=codex_stream_path,
    )
    payload: dict[str, Any] = {
        "version": "v1",
        "generated_utc": generated_utc,
        "now_local_iso": now.replace(microsecond=0).isoformat(),
        "time_context": {
            "timezone": _COMPASS_TIMEZONE,
            "label": "San Francisco",
        },
        "identity": {
            "name": identity_name,
            "email": identity_email,
            "source": "git-config" if (identity_name or identity_email) else "unknown",
        },
        "sources": {
            "backlog_index": _as_repo_path(repo_root, backlog_index_path),
            "plan_index": _as_repo_path(repo_root, plan_index_path),
            "bugs_index": _as_repo_path(repo_root, bugs_index_path),
            "traceability_graph": _as_repo_path(repo_root, traceability_graph_path),
            "mermaid_catalog": _as_repo_path(repo_root, mermaid_catalog_path),
            "codex_stream": _as_repo_path(repo_root, codex_stream_path),
        },
        "kpis": {
            "24h": kpi_24h,
            "48h": kpi_48h,
        },
        "digest": {
            "24h": digest_24h,
            "48h": digest_48h,
        },
        "digest_scoped": {
            "24h": digest_scoped_24h,
            "48h": digest_scoped_48h,
        },
        "standup_brief": {
            "24h": standup_brief_24h,
            "48h": standup_brief_48h,
        },
        "standup_brief_scoped": {
            "24h": standup_brief_scoped_24h,
            "48h": standup_brief_scoped_48h,
        },
        "odylith_runtime": _compact_odylith_runtime_summary(repo_root=repo_root),
        "self_host": self_host,
        "governance": governance_summary,
        "workstream_catalog": all_ws_payloads,
        "current_workstreams": ws_payloads,
        "execution_waves": execution_waves,
        "next_actions": next_actions,
        "timeline_events": timeline_events,
        "timeline_transactions": timeline_transactions,
        "execution_focus": execution_focus,
        "risks": {
            "bugs": bug_items,
            "self_host": self_host_risks,
            "traceability": traceability_risks,
            "traceability_critical": traceability_critical,
            "traceability_warnings": traceability_warnings,
            "stale_diagrams": stale_diagrams,
        },
        "history": {
            "retention_days": 0,
            "dates": [],
        },
        "queue": {
            "top": queued_top,
            "execution": [
                {
                    "idea_id": str(row.get("idea_id", "")).strip(),
                    "title": str(row.get("title", "")).strip(),
                    "status": str(row.get("status", "")).strip(),
                }
                for row in execution_backlog_rows
            ],
        },
        "contracts": {
            "workstream_id_pattern": _WORKSTREAM_ID_RE.pattern,
            "history_date_pattern": _DATE_RE.pattern,
        },
    }
    return payload
