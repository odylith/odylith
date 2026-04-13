"""Runtime payload builder extracted from the Compass runtime."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.governance.delivery import scope_signal_ladder
from odylith.runtime.governance import proof_state as proof_state_runtime
from odylith.runtime.governance import workstream_progress as workstream_progress_runtime
from odylith.runtime.surfaces import compass_governance_source_runtime
from odylith.runtime.surfaces import compass_refresh_contract
from odylith.runtime.surfaces import compass_execution_focus_runtime
from odylith.runtime.surfaces import compass_standup_brief_maintenance
from odylith.runtime.surfaces import compass_standup_runtime_reuse
from odylith.runtime.surfaces import compass_window_update_index


def _host():
    from odylith.runtime.surfaces import compass_dashboard_runtime as host

    return host


def _emit_refresh_progress(
    progress_callback: Any | None,
    *,
    stage: str,
    message: str,
) -> None:
    if not callable(progress_callback):
        return
    progress_callback(stage, {"message": str(message).strip()})


def _brief_source_counts(briefs: Mapping[str, Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for brief in briefs.values():
        if not isinstance(brief, Mapping):
            continue
        source = str(brief.get("source", "")).strip().lower() or "unknown"
        counts[source] = int(counts.get(source, 0) or 0) + 1
    return counts


def _format_brief_source_counts(counts: Mapping[str, int]) -> str:
    ordered = [
        ("provider", "provider"),
        ("cache", "cache"),
        ("unavailable", "inactive"),
        ("unknown", "unknown"),
    ]
    parts = [
        f"{label}={int(counts.get(source, 0) or 0)}"
        for source, label in ordered
        if int(counts.get(source, 0) or 0) > 0
    ]
    return ", ".join(parts) if parts else "no scoped briefs"


def _reusable_brief_sections_for_fact_packet(
    *,
    brief: Mapping[str, Any],
    fact_packet: Mapping[str, Any],
) -> list[dict[str, Any]] | None:
    if not compass_standup_runtime_reuse.brief_ready_without_notice(brief):
        return None
    raw_sections = brief.get("sections")
    if not isinstance(raw_sections, Sequence) or not raw_sections:
        return None
    narrator = _host().compass_standup_brief_narrator
    return narrator._validated_cached_sections(  # noqa: SLF001
        raw_sections=raw_sections,
        fact_packet=fact_packet,
        cached_evidence_lookup=brief.get("evidence_lookup", {}),
    )


def _brief_with_known_failure_state(
    *,
    repo_root: Path,
    window_key: str,
    fact_packet: Mapping[str, Any],
    generated_utc: str,
    brief: Mapping[str, Any],
    scope_id: str = "",
) -> dict[str, Any]:
    if not isinstance(brief, Mapping):
        return dict(brief)
    if str(brief.get("status", "")).strip().lower() != "unavailable":
        return dict(brief)
    if str(brief.get("source", "")).strip().lower() != "unavailable":
        return dict(brief)
    diagnostics = brief.get("diagnostics") if isinstance(brief.get("diagnostics"), Mapping) else {}
    reason = str(diagnostics.get("reason", "")).strip().lower()
    if reason not in {"provider_deferred", "provider_unavailable"}:
        return dict(brief)
    known_failure = compass_standup_brief_maintenance.failure_brief_for_fact_packet(
        repo_root=repo_root,
        window_key=window_key,
        fact_packet=fact_packet,
        generated_utc=generated_utc,
        scope_id=scope_id,
    )
    return dict(known_failure) if isinstance(known_failure, Mapping) else dict(brief)


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


def _window_row_has_workstream(*, row: Mapping[str, Any], ws_id: str) -> bool:
    token = str(ws_id).strip()
    if not token:
        return False
    workstreams = row.get("workstreams")
    if not isinstance(workstreams, list):
        return False
    return any(str(item).strip() == token for item in workstreams)


_SCOPED_VERIFIED_MAX_FANOUT = scope_signal_ladder.SCOPED_FANOUT_CAP
_SCOPED_GOVERNANCE_ONLY_PREFIXES = scope_signal_ladder.GOVERNANCE_ONLY_PREFIXES


def _window_row_workstreams(row: Mapping[str, Any]) -> list[str]:
    workstreams = row.get("workstreams")
    if not isinstance(workstreams, list):
        return []
    deduped: list[str] = []
    seen: set[str] = set()
    for item in workstreams:
        token = str(item).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _window_row_files(row: Mapping[str, Any]) -> list[str]:
    files = row.get("files")
    if not isinstance(files, list):
        return []
    deduped: list[str] = []
    seen: set[str] = set()
    for item in files:
        token = str(item).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _is_scoped_governance_only_file(file_path: str) -> bool:
    token = str(file_path).strip()
    if not token:
        return False
    return any(token.startswith(prefix) for prefix in _SCOPED_GOVERNANCE_ONLY_PREFIXES)


def _row_is_governance_only_local_change(row: Mapping[str, Any]) -> bool:
    files = _window_row_files(row)
    if not files:
        return False
    if str(row.get("kind", "")).strip() == "local_change":
        return all(_is_scoped_governance_only_file(item) for item in files)
    raw_events = row.get("events")
    event_kinds = {
        str(item.get("kind", "")).strip()
        for item in (raw_events if isinstance(raw_events, list) else [])
        if isinstance(item, Mapping) and str(item.get("kind", "")).strip()
    }
    if event_kinds and any(kind != "local_change" for kind in event_kinds):
        return False
    return all(_is_scoped_governance_only_file(item) for item in files)


def _row_is_verified_scoped_signal(row: Mapping[str, Any]) -> bool:
    workstreams = _window_row_workstreams(row)
    if not workstreams:
        return False
    if len(workstreams) > _SCOPED_VERIFIED_MAX_FANOUT:
        return False
    if _row_is_governance_only_local_change(row):
        return False
    return True


def _verified_scoped_window_ids(
    *,
    known_ids: set[str],
    recent_completed: Sequence[Mapping[str, Any]],
    window_events: Sequence[Mapping[str, Any]],
    window_transactions: Sequence[Mapping[str, Any]],
) -> set[str]:
    verified: set[str] = set()
    for item in recent_completed:
        token = str(item.get("backlog", "")).strip()
        if token and token in known_ids:
            verified.add(token)
    for rows in (window_events, window_transactions):
        for row in rows:
            if not isinstance(row, Mapping) or not _row_is_verified_scoped_signal(row):
                continue
            for token in _window_row_workstreams(row):
                if token in known_ids:
                    verified.add(token)
    return verified


def _workstream_has_window_activity(
    *,
    ws_id: str,
    recent_completed: list[dict[str, str]],
    window_events: list[dict[str, Any]],
    window_transactions: list[dict[str, Any]],
) -> bool:
    token = str(ws_id).strip()
    if not token:
        return False
    if any(str(item.get("backlog", "")).strip() == token for item in recent_completed):
        return True
    if any(_window_row_has_workstream(row=row, ws_id=token) for row in window_events if isinstance(row, Mapping)):
        return True
    return any(
        _window_row_has_workstream(row=row, ws_id=token)
        for row in window_transactions
        if isinstance(row, Mapping)
    )


def _inactive_scoped_standup_brief(
    *,
    ws_id: str,
    window_hours: int,
    generated_utc: str,
) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "source": "unavailable",
        "fingerprint": "",
        "generated_utc": generated_utc,
        "diagnostics": {
            "reason": "scoped_window_inactive",
            "title": "Nothing moved in this window",
            "message": (
                f"{str(ws_id).strip() or 'This scope'} was quiet in the last {int(window_hours)} hours, "
                "so Compass has nothing new to brief for that scope."
            ),
        },
        "sections": [],
        "evidence_lookup": {},
    }


def _brief_section_bullets(*, brief: Mapping[str, Any], section_key: str) -> list[str]:
    raw_sections = brief.get("sections")
    if not isinstance(raw_sections, list):
        return []
    for row in raw_sections:
        if not isinstance(row, Mapping) or str(row.get("key", "")).strip() != section_key:
            continue
        raw_bullets = row.get("bullets")
        if not isinstance(raw_bullets, list):
            return []
        return [str(item.get("text", "")).strip() for item in raw_bullets if isinstance(item, Mapping) and str(item.get("text", "")).strip()]
    return []


def _fact_packet_section_facts(*, fact_packet: Mapping[str, Any], section_key: str) -> list[dict[str, Any]]:
    raw_sections = fact_packet.get("sections")
    if not isinstance(raw_sections, list):
        return []
    for row in raw_sections:
        if not isinstance(row, Mapping) or str(row.get("key", "")).strip() != section_key:
            continue
        raw_facts = row.get("facts")
        if not isinstance(raw_facts, list):
            return []
        return [dict(item) for item in raw_facts if isinstance(item, Mapping)]
    return []


def _compose_global_fact_packet_from_scoped_briefs(
    *,
    base_fact_packet: Mapping[str, Any],
    scoped_briefs_by_scope: Mapping[str, Mapping[str, Any]],
    ordered_scope_ids: list[str],
) -> dict[str, Any]:
    host = _host()
    narrator = host.compass_standup_brief_narrator
    section_specs = narrator.STANDUP_BRIEF_SECTIONS
    section_rows: dict[str, list[dict[str, Any]]] = {key: [] for key, _label in section_specs}
    facts: list[dict[str, Any]] = []
    fact_counter = 1
    seen_text: dict[str, set[str]] = {key: set() for key, _label in section_specs}

    def _append_fact(
        *,
        section_key: str,
        text: str,
        source: str,
        kind: str,
        workstreams: list[str] | None = None,
        voice_hint: str = "operator",
    ) -> None:
        nonlocal fact_counter
        normalized_text = str(text).strip()
        if not normalized_text or normalized_text.lower() in seen_text[section_key]:
            return
        seen_text[section_key].add(normalized_text.lower())
        fact = {
            "id": f"F-{fact_counter:03d}",
            "section_key": section_key,
            "voice_hint": voice_hint,
            "priority": 100 - fact_counter,
            "text": normalized_text,
            "source": source,
            "kind": kind,
            "workstreams": [token for token in (workstreams or []) if str(token).strip()],
        }
        fact_counter += 1
        facts.append(fact)
        section_rows[section_key].append(fact)

    ready_scope_ids = [
        ws_id
        for ws_id in ordered_scope_ids
        if isinstance(scoped_briefs_by_scope.get(ws_id), Mapping)
        and str(scoped_briefs_by_scope[ws_id].get("status", "")).strip().lower() == "ready"
    ]
    if not ready_scope_ids:
        return dict(base_fact_packet)

    for ws_id in ready_scope_ids[:2]:
        bullets = _brief_section_bullets(brief=scoped_briefs_by_scope[ws_id], section_key="completed")
        if bullets:
            _append_fact(
                section_key="completed",
                text=bullets[0],
                source="scoped_brief",
                kind="scoped_completed",
                workstreams=[ws_id],
            )

    for ws_id in ready_scope_ids[:3]:
        bullets = _brief_section_bullets(brief=scoped_briefs_by_scope[ws_id], section_key="current_execution")
        if bullets:
            _append_fact(
                section_key="current_execution",
                text=bullets[0],
                source="scoped_brief",
                kind="scoped_current_execution",
                workstreams=[ws_id],
            )

    coverage_facts = [
        fact
        for fact in _fact_packet_section_facts(fact_packet=base_fact_packet, section_key="current_execution")
        if str(fact.get("kind", "")).strip().lower() == "window_coverage"
    ]
    if coverage_facts:
        coverage = coverage_facts[0]
        _append_fact(
            section_key="current_execution",
            text=str(coverage.get("text", "")).strip(),
            source="portfolio",
            kind="window_coverage",
            workstreams=[str(token).strip() for token in coverage.get("workstreams", []) if str(token).strip()],
        )

    for ws_id in ready_scope_ids[:2]:
        bullets = _brief_section_bullets(brief=scoped_briefs_by_scope[ws_id], section_key="next_planned")
        if bullets:
            _append_fact(
                section_key="next_planned",
                text=bullets[0],
                source="scoped_brief",
                kind="scoped_next_planned",
                workstreams=[ws_id],
            )

    for ws_id in ready_scope_ids[:3]:
        bullets = _brief_section_bullets(brief=scoped_briefs_by_scope[ws_id], section_key="risks_to_watch")
        if bullets:
            _append_fact(
                section_key="risks_to_watch",
                text=bullets[0],
                source="scoped_brief",
                kind="scoped_risk",
                workstreams=[ws_id],
            )

    for section_key, _label in section_specs:
        if section_rows[section_key]:
            continue
        for fact in _fact_packet_section_facts(fact_packet=base_fact_packet, section_key=section_key)[:2]:
            _append_fact(
                section_key=section_key,
                text=str(fact.get("text", "")).strip(),
                source=str(fact.get("source", "")).strip() or "fact_packet",
                kind=str(fact.get("kind", "")).strip() or "fallback",
                workstreams=[str(token).strip() for token in fact.get("workstreams", []) if str(token).strip()],
                voice_hint=str(fact.get("voice_hint", "")).strip().lower() or "operator",
            )

    sections = [
        {
            "key": key,
            "label": label,
            "facts": section_rows[key][:6],
        }
        for key, label in section_specs
    ]
    return {
        "version": str(base_fact_packet.get("version", "")).strip() or narrator.STANDUP_BRIEF_SCHEMA_VERSION,
        "window": str(base_fact_packet.get("window", "")).strip(),
        "scope": dict(base_fact_packet.get("scope", {})) if isinstance(base_fact_packet.get("scope", {}), Mapping) else {},
        "summary": dict(base_fact_packet.get("summary", {})) if isinstance(base_fact_packet.get("summary", {}), Mapping) else {},
        "sections": sections,
        "facts": facts,
    }


def _current_runtime_payload(repo_root: Path) -> dict[str, Any]:
    payload = odylith_context_cache.read_json_object(
        Path(repo_root).resolve() / "odylith" / "compass" / "runtime" / "current.v1.json"
    )
    return dict(payload) if isinstance(payload, Mapping) else {}


def _cached_governance_summary_for_shell_safe(
    *,
    repo_root: Path,
    refresh_profile: str,
) -> dict[str, Any] | None:
    del refresh_profile
    payload = _current_runtime_payload(repo_root)
    governance_summary = payload.get("governance")
    return dict(governance_summary) if isinstance(governance_summary, Mapping) else None


def _cached_odylith_runtime_summary_for_shell_safe(
    *,
    repo_root: Path,
    refresh_profile: str,
) -> dict[str, Any] | None:
    del refresh_profile
    payload = _current_runtime_payload(repo_root)
    runtime_summary = payload.get("odylith_runtime")
    return dict(runtime_summary) if isinstance(runtime_summary, Mapping) else None


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
    refresh_profile: str = "shell-safe",
    progress_callback: Any | None = None,
) -> dict[str, Any]:
    host = _host()
    _load_json = host._load_json
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
    governance_context = compass_governance_source_runtime.build_live_governance_context(
        repo_root=repo_root,
        traceability_graph=traceability_graph,
        traceability_signature=odylith_context_cache.fingerprint_paths([traceability_graph_path]),
    )
    live_traceability_graph = (
        dict(governance_context.get("traceability_graph", {}))
        if isinstance(governance_context.get("traceability_graph"), Mapping)
        else dict(traceability_graph)
    )
    execution_waves_all = (
        dict(governance_context.get("execution_waves", {}))
        if isinstance(governance_context.get("execution_waves"), Mapping)
        else {}
    )
    mermaid_catalog = _load_json(mermaid_catalog_path)
    workstream_rows = governance_context.get("workstream_rows", [])
    diagram_rows = mermaid_catalog.get("diagrams", []) if isinstance(mermaid_catalog.get("diagrams"), list) else []
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
    _emit_refresh_progress(
        progress_callback,
        stage="projection_inputs_loaded",
        message=(
            f"loaded {len(workstream_rows) if isinstance(workstream_rows, list) else 0} workstreams, "
            f"{len(active_plan_rows)} active plans, {len(bug_rows)} bugs, and {len(diagram_rows)} diagrams"
        ),
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
        traceability_graph=live_traceability_graph,
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
    _emit_refresh_progress(
        progress_callback,
        stage="activity_events_collected",
        message=f"collected {len(commits)} commits, {len(local_changes)} local changes, and {len(events)} timeline events",
    )

    release_workstream_rows = (
        dict(governance_context.get("release_workstreams", {}))
        if isinstance(governance_context.get("release_workstreams"), Mapping)
        else {}
    )
    release_summary = (
        dict(governance_context.get("release_summary", {}))
        if isinstance(governance_context.get("release_summary"), Mapping)
        else {}
    )
    ws_payloads: list[dict[str, Any]] = []

    active_plan_map: dict[str, str] = {}
    for row in active_plan_rows:
        backlog_token = str(row.get("Backlog", "")).strip().strip("`")
        plan_token = str(row.get("Plan", "")).strip().strip("`")
        if backlog_token:
            active_plan_map[backlog_token] = plan_token

    delivery_surface_payload = odylith_context_engine_store.load_delivery_surface_payload(
        repo_root=repo_root,
        surface="compass",
        runtime_mode=runtime_mode,
        buckets=("workstreams",),
        include_shell_snapshots=False,
    )
    delivery_workstreams = (
        dict(delivery_surface_payload.get("workstreams", {}))
        if isinstance(delivery_surface_payload.get("workstreams"), Mapping)
        else {}
    )

    for row in workstream_rows if isinstance(workstream_rows, list) else []:
        if not isinstance(row, Mapping):
            continue
        idea_id = str(row.get("idea_id", "")).strip()
        if not idea_id:
            continue
        release_row = (
            dict(release_workstream_rows.get(idea_id, {}))
            if isinstance(release_workstream_rows.get(idea_id), Mapping)
            else {}
        )
        active_release = (
            dict(release_row.get("active_release", {}))
            if isinstance(release_row.get("active_release"), Mapping)
            else {}
        )
        execution_wave_programs = execution_waves_all.get("workstreams", {}).get(idea_id, [])
        if not execution_wave_programs and isinstance(execution_waves_all.get("programs"), list):
            execution_wave_programs = [
                dict(program)
                for program in execution_waves_all.get("programs", [])
                if isinstance(program, Mapping) and str(program.get("umbrella_id", "")).strip() == idea_id
            ]

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
        workstream_status = str(row.get("status", "")).strip() or str(metadata.get("status", "")).strip()
        workstream_progress = workstream_progress_runtime.derive_workstream_progress(
            status=workstream_status,
            plan=plan_progress,
        )
        delivery_snapshot = (
            dict(delivery_workstreams.get(idea_id, {}))
            if isinstance(delivery_workstreams.get(idea_id), Mapping)
            else {}
        )
        delivery_readout = (
            dict(delivery_snapshot.get("operator_readout", {}))
            if isinstance(delivery_snapshot.get("operator_readout"), Mapping)
            else {}
        )
        delivery_proof_state = proof_state_runtime.normalize_proof_state(
            delivery_snapshot.get("proof_state", {})
        )
        delivery_claim_guard = (
            dict(delivery_snapshot.get("claim_guard", {}))
            if isinstance(delivery_snapshot.get("claim_guard"), Mapping)
            else {}
        )

        ws_payloads.append(
            {
                "idea_id": idea_id,
                "title": str(row.get("title", "")).strip() or str(metadata.get("title", "")).strip() or idea_id,
                "status": workstream_status,
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
                "execution_wave_programs": [
                    dict(item)
                    for item in execution_wave_programs
                    if isinstance(item, Mapping)
                ],
                "release": active_release,
                "release_history_summary": str(row.get("release_history_summary", "")).strip(),
                "plan": {
                    "created": str(plan_progress.get("created", "")).strip(),
                    "updated": str(plan_progress.get("updated", "")).strip(),
                    "all_total_tasks": int(plan_progress.get("all_total_tasks", 0) or 0),
                    "all_done_tasks": int(plan_progress.get("all_done_tasks", 0) or 0),
                    "total_tasks": int(plan_progress.get("total_tasks", 0) or 0),
                    "done_tasks": int(plan_progress.get("done_tasks", 0) or 0),
                    "progress_ratio": float(plan_progress.get("progress_ratio", 0.0) or 0.0),
                    "progress_basis": str(plan_progress.get("progress_basis", "")).strip(),
                    "display_progress_ratio": workstream_progress.get("display_progress_ratio"),
                    "display_progress_label": str(workstream_progress.get("display_progress_label", "")).strip(),
                    "display_progress_state": str(workstream_progress.get("display_progress_state", "")).strip(),
                    "progress_classification": str(workstream_progress.get("classification", "")).strip(),
                    "checklist_label": str(workstream_progress.get("checklist_label", "")).strip(),
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
                "proof_state": delivery_proof_state,
                "claim_guard": delivery_claim_guard,
                "proof_state_resolution": (
                    dict(delivery_snapshot.get("proof_state_resolution", {}))
                    if isinstance(delivery_snapshot.get("proof_state_resolution"), Mapping)
                    else {}
                ),
                "scope_signal": (
                    dict(delivery_snapshot.get("scope_signal", {}))
                    if isinstance(delivery_snapshot.get("scope_signal"), Mapping)
                    else {}
                ),
                "proof_refs": [
                    dict(item)
                    for item in delivery_readout.get("proof_refs", [])
                    if isinstance(item, Mapping)
                ] if isinstance(delivery_readout.get("proof_refs"), list) else [],
                "proof_summary_lines": proof_state_runtime.proof_preview_lines(
                    delivery_proof_state,
                    compact=False,
                    limit=6,
                ),
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

    current_workstreams_by_window = {
        "24h": _select_current_workstream_rows(
            all_rows=all_ws_payloads,
            window_events=_window_events(24),
            recent_completed_rows=_recent_completed_rows(24),
        ),
        "48h": _select_current_workstream_rows(
            all_rows=all_ws_payloads,
            window_events=_window_events(48),
            recent_completed_rows=_recent_completed_rows(48),
        ),
    }
    ws_payloads = list(current_workstreams_by_window["48h"])
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

    warnings = live_traceability_graph.get("warning_items", [])
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
    if isinstance(diagram_rows, list):
        for row in diagram_rows:
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
    prior_runtime_state = compass_standup_runtime_reuse.prior_runtime_state(
        payload=_current_runtime_payload(repo_root),
    )
    self_host = _self_host_snapshot(repo_root=repo_root, refresh_profile=refresh_profile)
    self_host_risks = _self_host_risk_rows(snapshot=self_host, local_date=now.date().isoformat())
    _emit_refresh_progress(
        progress_callback,
        stage="execution_projection_built",
        message=(
            f"projected {len(all_ws_payloads)} workstreams, {len(ws_payloads)} current rows, "
            f"{len(timeline_transactions)} transactions, and {len(next_actions)} next actions"
        ),
    )

    def _summarize_window(
        hours: int,
    ) -> tuple[dict[str, int], dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
        window_events = _window_events(hours)
        window_transactions = _window_transactions(hours)
        execution_update_index = compass_window_update_index.build_execution_update_index(
            window_events,
            max_items=3,
        )
        transaction_update_index = compass_window_update_index.build_transaction_update_index(
            window_transactions,
            max_items=3,
        )
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

        completed_ids = {
            str(item.get("backlog", "")).strip()
            for item in recent_completed
            if str(item.get("backlog", "")).strip()
        }
        event_ids = {
            str(token).strip()
            for row in window_events
            if isinstance(row, Mapping)
            for token in row.get("workstreams", [])
            if str(token).strip()
        }
        transaction_ids = {
            str(token).strip()
            for row in window_transactions
            if isinstance(row, Mapping)
            for token in row.get("workstreams", [])
            if str(token).strip()
        }
        window_active_ids = {
            str(row.get("idea_id", "")).strip()
            for row in all_ws_payloads
            if str(row.get("idea_id", "")).strip() in (completed_ids | event_ids | transaction_ids)
        }
        known_workstream_ids = {
            str(row.get("idea_id", "")).strip()
            for row in all_ws_payloads
            if str(row.get("idea_id", "")).strip()
        }
        window_verified_ids = _verified_scoped_window_ids(
            known_ids=known_workstream_ids,
            recent_completed=recent_completed,
            window_events=window_events,
            window_transactions=window_transactions,
        )
        window_scope_signals: dict[str, dict[str, Any]] = {}
        window_promoted_ids: set[str] = set()
        for row in all_ws_payloads:
            ws_id = str(row.get("idea_id", "")).strip()
            if not ws_id:
                continue
            matching_rows = [
                item
                for item in [*window_events, *window_transactions]
                if isinstance(item, Mapping) and _window_row_has_workstream(row=item, ws_id=ws_id)
            ]
            verified_row_count = sum(1 for item in matching_rows if _row_is_verified_scoped_signal(item))
            has_any_window_signal = bool(ws_id in completed_ids or matching_rows)
            governance_only_local_change = bool(matching_rows) and all(
                _row_is_governance_only_local_change(item)
                for item in matching_rows
            )
            broad_fanout_only = bool(matching_rows) and not verified_row_count and all(
                len(_window_row_workstreams(item)) > _SCOPED_VERIFIED_MAX_FANOUT
                for item in matching_rows
            )
            signal = scope_signal_ladder.compass_window_scope_signal(
                scope_id=ws_id,
                workstream_row=row,
                delivery_snapshot=delivery_workstreams.get(ws_id, {}),
                has_any_window_signal=has_any_window_signal,
                verified_completion=ws_id in completed_ids,
                verified_row_count=verified_row_count,
                broad_fanout_only=broad_fanout_only,
                governance_only_local_change=governance_only_local_change,
                window_active=ws_id in window_active_ids,
            )
            window_scope_signals[ws_id] = signal
            if scope_signal_ladder.scope_signal_rank(signal) >= 2:
                window_verified_ids.add(ws_id)
            if scope_signal_ladder.scope_signal_rank(signal) >= scope_signal_ladder.DEFAULT_PROMOTED_DEFAULT_RANK:
                window_promoted_ids.add(ws_id)

        if window_promoted_ids:
            focus_rows = []
            seen_focus_ids.clear()
            for ws_id in touched_ws:
                if ws_id in active_ids and ws_id in window_promoted_ids:
                    _append_focus_row(ws_id)
            for ws_id in touched_ws:
                if ws_id in window_promoted_ids:
                    _append_focus_row(ws_id)
            for item in recent_completed:
                ws_id = str(item.get("backlog", "")).strip()
                if ws_id in window_promoted_ids:
                    _append_focus_row(ws_id)
            for row in all_ws_payloads:
                ws_id = str(row.get("idea_id", "")).strip()
                if ws_id in window_promoted_ids:
                    _append_focus_row(ws_id)
        _emit_refresh_progress(
            progress_callback,
            stage="window_facts_prepared",
            message=(
                f"{hours}h: {len(window_active_ids)} active scopes, "
                f"{len(window_verified_ids)} verified scoped, {len(window_promoted_ids)} promoted, "
                f"{len(window_events)} events, {len(window_transactions)} transactions, "
                f"{len(recent_completed)} recent completions"
            ),
        )

        focus_ids = {str(item.get("idea_id", "")).strip() for item in focus_rows if str(item.get("idea_id", "")).strip()}
        focus_actions = [item for item in next_actions if str(item.get("idea_id", "")).strip() in focus_ids]
        window_kpis = dict(kpis)
        if self_host_risks:
            window_kpis["critical_risks"] = int(window_kpis.get("critical_risks", 0) or 0) + len(self_host_risks)
        window_key = f"{int(hours)}h"
        prior_window_runtime = compass_standup_runtime_reuse.window_runtime_state(
            prior_runtime_state,
            window_key=window_key,
        )
        prior_global_brief = compass_standup_runtime_reuse.window_global_brief(
            prior_runtime_state,
            window_key=window_key,
        )
        prior_scoped_briefs = compass_standup_runtime_reuse.window_scoped_briefs(
            prior_runtime_state,
            window_key=window_key,
        )
        global_reuse_fingerprint = compass_standup_runtime_reuse.global_reuse_fingerprint(
            window_hours=hours,
            focus_rows=focus_rows,
            active_ws_rows=active_ws_rows,
            touched_workstreams=touched_ws,
            next_actions=focus_actions or next_actions,
            recent_completed=recent_completed,
            execution_updates=execution_update_index.get("global", []),
            transaction_updates=transaction_update_index.get("global", []),
            kpis=window_kpis,
            risk_summary=risk_posture_window,
            self_host_snapshot=self_host,
        )
        standup_runtime_window: dict[str, Any] = {
            "global_reuse_fingerprint": global_reuse_fingerprint,
            "scoped_reuse_fingerprints": {},
            "verified_scope_ids": sorted(window_verified_ids),
            "promoted_scope_ids": sorted(window_promoted_ids),
            "scope_signals": window_scope_signals,
        }
        global_fact_packet = _build_global_standup_fact_packet(
            ws_rows=focus_rows,
            ws_index=ws_index,
            active_ws_rows=active_ws_rows,
            event_counts_by_ws=event_counts_by_ws,
            next_actions=focus_actions or next_actions,
            recent_completed=recent_completed,
            window_events=window_events,
            window_transactions=window_transactions,
            execution_updates=execution_update_index.get("global", []),
            transaction_updates=transaction_update_index.get("global", []),
            window_hours=hours,
            risk_rows=global_risk_rows,
            risk_summary=risk_posture_window,
            kpis=window_kpis,
            self_host_snapshot=self_host,
            self_host_risks=self_host_risks,
            now=now,
        )
        standup_global: dict[str, Any] = {}
        reusable_global_sections = _reusable_brief_sections_for_fact_packet(
            brief=prior_global_brief,
            fact_packet=global_fact_packet,
        )
        if (
            str(prior_window_runtime.get("global_reuse_fingerprint", "")).strip() == global_reuse_fingerprint
            and reusable_global_sections is not None
        ):
            standup_global = compass_standup_runtime_reuse.reuse_ready_brief(
                brief=prior_global_brief,
                generated_utc=generated_utc,
                fingerprint=f"salient:{global_reuse_fingerprint}",
                sections=reusable_global_sections,
            )
        else:
            standup_global = compass_standup_brief_narrator.build_standup_brief(
                repo_root=repo_root,
                fact_packet=global_fact_packet,
                generated_utc=generated_utc,
                config=reasoning_config,
                provider=None,
                allow_provider=False,
                prefer_provider=False,
            )
            standup_global = _brief_with_known_failure_state(
                repo_root=repo_root,
                window_key=window_key,
                fact_packet=global_fact_packet,
                generated_utc=generated_utc,
                brief=standup_global,
            )
        standup_scoped: dict[str, dict[str, Any]] = {}
        scoped_packet_index: dict[str, dict[str, Any]] = {}
        # Scoped brief generation reuses exact same-packet narration first, then
        # returns explicit unavailability when no live or exact-replay brief exists.
        for ws in all_ws_payloads:
            ws_id = str(ws.get("idea_id", "")).strip()
            if not ws_id:
                continue
            if ws_id not in window_verified_ids:
                standup_scoped[ws_id] = _inactive_scoped_standup_brief(
                    ws_id=ws_id,
                    window_hours=hours,
                    generated_utc=generated_utc,
                )
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
            scoped_reuse_fingerprint = compass_standup_runtime_reuse.scoped_reuse_fingerprint(
                row=ws,
                window_hours=hours,
                next_action_tokens=[
                    str(item.get("action", "")).strip()
                    for item in next_actions
                    if str(item.get("idea_id", "")).strip() == ws_id and str(item.get("action", "")).strip()
                ][:2],
                completed_deliverables=[
                    str(item.get("plan", "")).strip()
                    for item in recent_completed
                    if str(item.get("backlog", "")).strip() == ws_id and str(item.get("plan", "")).strip()
                ][:2],
                execution_updates=execution_update_index.get("by_workstream", {}).get(ws_id, []),
                transaction_updates=transaction_update_index.get("by_workstream", {}).get(ws_id, []),
                risk_summary=scoped_risk_summary,
                self_host_snapshot=self_host,
            )
            standup_runtime_window["scoped_reuse_fingerprints"][ws_id] = scoped_reuse_fingerprint
            scoped_fact_packet = _build_scoped_standup_fact_packet(
                row=ws,
                next_actions=next_actions,
                recent_completed=recent_completed,
                window_events=window_events,
                window_transactions=window_transactions,
                execution_updates=execution_update_index.get("by_workstream", {}).get(ws_id, []),
                transaction_updates=transaction_update_index.get("by_workstream", {}).get(ws_id, []),
                window_hours=hours,
                risk_rows=scoped_risk_rows,
                risk_summary=scoped_risk_summary,
                self_host_snapshot=self_host,
                now=now,
            )
            scoped_packet_index[ws_id] = scoped_fact_packet
            reusable_scoped_sections = _reusable_brief_sections_for_fact_packet(
                brief=prior_scoped_briefs.get(ws_id),
                fact_packet=scoped_fact_packet,
            )
            if (
                str((prior_window_runtime.get("scoped_reuse_fingerprints", {}) if isinstance(prior_window_runtime.get("scoped_reuse_fingerprints", {}), Mapping) else {}).get(ws_id, "")).strip() == scoped_reuse_fingerprint
                and reusable_scoped_sections is not None
            ):
                standup_scoped[ws_id] = compass_standup_runtime_reuse.reuse_ready_brief(
                    brief=prior_scoped_briefs[ws_id],
                    generated_utc=generated_utc,
                    fingerprint=f"salient:{scoped_reuse_fingerprint}",
                    sections=reusable_scoped_sections,
                )
                continue
            standup_scoped[ws_id] = compass_standup_brief_narrator.build_standup_brief(
                repo_root=repo_root,
                fact_packet=scoped_fact_packet,
                generated_utc=generated_utc,
                config=reasoning_config,
                provider=None,
                allow_provider=False,
                prefer_provider=False,
            )
            standup_scoped[ws_id] = _brief_with_known_failure_state(
                repo_root=repo_root,
                window_key=window_key,
                fact_packet=scoped_fact_packet,
                generated_utc=generated_utc,
                brief=standup_scoped[ws_id],
                scope_id=ws_id,
            )
        _emit_refresh_progress(
            progress_callback,
            stage="standup_briefs_built",
            message=(
                f"{hours}h: global {str(standup_global.get('source', '')).strip().lower() or 'unknown'}, "
                f"scoped {_format_brief_source_counts(_brief_source_counts(standup_scoped))}"
            ),
        )

        return window_kpis, standup_global, standup_scoped, scoped_packet_index, standup_runtime_window, global_fact_packet

    kpi_24h, standup_brief_24h, standup_brief_scoped_24h, scoped_packets_24h, standup_runtime_24h, global_packet_24h = _summarize_window(24)
    kpi_48h, standup_brief_48h, standup_brief_scoped_48h, scoped_packets_48h, standup_runtime_48h, global_packet_48h = _summarize_window(48)
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
    if str(refresh_profile).strip().lower() == compass_refresh_contract.DEFAULT_REFRESH_PROFILE:
        compass_standup_brief_maintenance.enqueue_request(
            repo_root=repo_root,
            generated_utc=generated_utc,
            runtime_input_fingerprint="",
            global_fact_packets={
                "24h": global_packet_24h,
                "48h": global_packet_48h,
            },
            global_briefs={
                "24h": standup_brief_24h,
                "48h": standup_brief_48h,
            },
            scoped_fact_packets={
                "24h": scoped_packets_24h,
                "48h": scoped_packets_48h,
            },
            scoped_briefs={
                "24h": standup_brief_scoped_24h,
                "48h": standup_brief_scoped_48h,
            },
            scope_signals={
                "24h": standup_runtime_24h.get("scope_signals", {}),
                "48h": standup_runtime_48h.get("scope_signals", {}),
            },
        )
    governance_summary = _cached_governance_summary_for_shell_safe(
        repo_root=repo_root,
        refresh_profile=refresh_profile,
    )
    if governance_summary is None:
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
            "agent_stream": _as_repo_path(repo_root, codex_stream_path),
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
        "standup_runtime": {
            "24h": standup_runtime_24h,
            "48h": standup_runtime_48h,
        },
        "verified_scoped_workstreams": {
            "24h": list(standup_runtime_24h.get("verified_scope_ids", [])),
            "48h": list(standup_runtime_48h.get("verified_scope_ids", [])),
        },
        "promoted_scoped_workstreams": {
            "24h": list(standup_runtime_24h.get("promoted_scope_ids", [])),
            "48h": list(standup_runtime_48h.get("promoted_scope_ids", [])),
        },
        "window_scope_signals": {
            "24h": dict(standup_runtime_24h.get("scope_signals", {})),
            "48h": dict(standup_runtime_48h.get("scope_signals", {})),
        },
        "odylith_runtime": (
            _cached_odylith_runtime_summary_for_shell_safe(
                repo_root=repo_root,
                refresh_profile=refresh_profile,
            )
            or _compact_odylith_runtime_summary(repo_root=repo_root)
        ),
        "self_host": self_host,
        "governance": governance_summary,
        "workstream_catalog": all_ws_payloads,
        "current_workstreams_by_window": {
            "24h": current_workstreams_by_window["24h"],
            "48h": current_workstreams_by_window["48h"],
        },
        "current_workstreams": ws_payloads,
        "execution_waves": execution_waves,
        "release_summary": release_summary,
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
