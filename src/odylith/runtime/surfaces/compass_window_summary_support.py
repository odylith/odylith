"""Shared Compass window-summary assembly for runtime payload generation."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from typing import Sequence

from odylith.runtime.governance.delivery import scope_signal_ladder
from odylith.runtime.surfaces import compass_standup_brief_narrator
from odylith.runtime.surfaces import compass_standup_runtime_reuse
from odylith.runtime.surfaces import compass_window_update_index


@dataclass
class CompassWindowSummary:
    kpis: dict[str, int]
    global_brief: dict[str, Any]
    scoped_briefs: dict[str, dict[str, Any]]
    scoped_packets: dict[str, dict[str, Any]]
    runtime_window: dict[str, Any]
    global_fact_packet: dict[str, Any]


@dataclass
class CompassWindowSummaryContext:
    repo_root: Path
    plan_index_path: Path
    now: dt.datetime
    all_ws_payloads: list[dict[str, Any]]
    ws_payloads: list[dict[str, Any]]
    active_ws_rows: list[dict[str, Any]]
    ws_index: dict[str, dict[str, Any]]
    events: list[dict[str, Any]]
    timeline_transactions: list[dict[str, Any]]
    next_actions: list[dict[str, str]]
    bug_items: list[dict[str, Any]]
    traceability_risks: list[dict[str, str]]
    traceability_critical: list[dict[str, str]]
    stale_diagrams: list[dict[str, Any]]
    self_host: dict[str, Any]
    self_host_risks: list[dict[str, Any]]
    generated_utc: str
    reasoning_config: Any
    prior_runtime_state: dict[str, Any]
    delivery_workstreams: dict[str, Any]
    progress_callback: Any | None
    build_window_activity: Any
    filter_transactions_by_window: Any
    collect_recent_completed_plan_rows: Any
    build_window_event_counts: Any
    build_risk_posture_summary: Any
    scope_risk_rows: Any
    build_global_standup_fact_packet: Any
    build_scoped_standup_fact_packet: Any
    reusable_brief_sections_for_fact_packet: Any
    brief_with_known_failure_state: Any
    inactive_scoped_standup_brief: Any
    verified_scoped_window_ids: Any
    window_row_has_workstream: Any
    row_is_verified_scoped_signal: Any
    row_is_governance_only_local_change: Any
    window_row_workstreams: Any
    is_generated_only_local_change_event: Any
    is_generated_only_transaction: Any
    is_bug_date_within_window: Any
    scoped_verified_max_fanout: int
    window_events_by_hours: dict[int, list[dict[str, Any]]]
    window_transactions_by_hours: dict[int, list[dict[str, Any]]]
    recent_completed_rows_by_hours: dict[int, list[dict[str, str]]]


def _cached_window_events(
    *,
    context: CompassWindowSummaryContext,
    hours: int,
) -> list[dict[str, Any]]:
    cached = context.window_events_by_hours.get(hours)
    if cached is not None:
        return cached
    built = [
        row
        for row in context.build_window_activity(context.events, now=context.now, hours=hours)
        if not context.is_generated_only_local_change_event(row)
    ]
    context.window_events_by_hours[hours] = built
    return built


def _cached_window_transactions(
    *,
    context: CompassWindowSummaryContext,
    hours: int,
) -> list[dict[str, Any]]:
    cached = context.window_transactions_by_hours.get(hours)
    if cached is not None:
        return cached
    built = [
        row
        for row in context.filter_transactions_by_window(
            context.timeline_transactions,
            now=context.now,
            hours=hours,
        )
        if not context.is_generated_only_transaction(row)
    ]
    context.window_transactions_by_hours[hours] = built
    return built


def _cached_recent_completed_rows(
    *,
    context: CompassWindowSummaryContext,
    hours: int,
) -> list[dict[str, str]]:
    cached = context.recent_completed_rows_by_hours.get(hours)
    if cached is not None:
        return cached
    built = context.collect_recent_completed_plan_rows(
        context.plan_index_path,
        repo_root=context.repo_root,
        now=context.now,
        hours=hours,
    )
    context.recent_completed_rows_by_hours[hours] = built
    return built


def _emit_progress(progress_callback: Any | None, *, stage: str, message: str) -> None:
    if not callable(progress_callback):
        return
    progress_callback(stage, {"message": str(message).strip()})


def summarize_window(
    *,
    context: CompassWindowSummaryContext,
    hours: int,
) -> CompassWindowSummary:
    window_events = _cached_window_events(context=context, hours=hours)
    window_transactions = _cached_window_transactions(context=context, hours=hours)
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
    event_counts_by_ws = context.build_window_event_counts(window_events)
    touched_ws = [
        ws_id
        for ws_id, _ in sorted(
            event_counts_by_ws.items(),
            key=lambda item: (-int(item[1]), item[0]),
        )
        if ws_id
    ]
    touched_ws_set = set(touched_ws)
    recent_completed_rows = _cached_recent_completed_rows(context=context, hours=hours)
    active_ws = len(context.active_ws_rows)
    touched_active_ws = (
        len(
            {
                str(row.get("idea_id", "")).strip()
                for row in context.active_ws_rows
                if str(row.get("idea_id", "")).strip() in touched_ws_set
            }
        )
        if context.active_ws_rows
        else 0
    )
    window_open_critical = sum(
        1
        for row in context.bug_items
        if bool(row.get("is_open_critical"))
        and context.is_bug_date_within_window(
            date_token=str(row.get("date", "")).strip(),
            now=context.now,
            hours=hours,
        )
    )
    risk_posture_window = context.build_risk_posture_summary(
        open_critical=window_open_critical,
        traceability_risks=context.traceability_risks,
        stale_diagrams=context.stale_diagrams,
    )
    global_risk_rows = context.scope_risk_rows(
        ws_id=None,
        bug_items=context.bug_items,
        traceability_risks=context.traceability_risks,
        stale_diagrams=context.stale_diagrams,
    )
    kpis = {
        "commits": commits_count,
        "local_changes": local_count,
        "touched_workstreams": len(touched_ws_set),
        "active_workstreams": active_ws,
        "critical_risks": window_open_critical + len(context.traceability_critical) + len(context.stale_diagrams),
        "recent_completed_plans": len(recent_completed_rows),
        "active_touched_workstreams": touched_active_ws,
    }

    recent_completed: list[dict[str, str]] = []
    for item in recent_completed_rows:
        normalized: dict[str, str] = dict(item)
        backlog = str(item.get("backlog", "")).strip()
        ws = context.ws_index.get(backlog)
        if ws is not None:
            normalized["title"] = str(ws.get("title", "")).strip()
        recent_completed.append(normalized)

    focus_rows: list[dict[str, Any]] = []
    seen_focus_ids: set[str] = set()
    active_ids = {
        str(row.get("idea_id", "")).strip()
        for row in context.active_ws_rows
        if str(row.get("idea_id", "")).strip()
    }

    def _append_focus_row(ws_id: str) -> None:
        token = str(ws_id).strip()
        if not token or token in seen_focus_ids:
            return
        ws = context.ws_index.get(token)
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
    for row in context.active_ws_rows:
        _append_focus_row(str(row.get("idea_id", "")).strip())
        if len(focus_rows) >= 2:
            break
    for row in context.ws_payloads:
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
        for row in context.all_ws_payloads
        if str(row.get("idea_id", "")).strip() in (completed_ids | event_ids | transaction_ids)
    }
    known_workstream_ids = {
        str(row.get("idea_id", "")).strip()
        for row in context.all_ws_payloads
        if str(row.get("idea_id", "")).strip()
    }
    window_verified_ids = context.verified_scoped_window_ids(
        known_ids=known_workstream_ids,
        recent_completed=recent_completed,
        window_events=window_events,
        window_transactions=window_transactions,
    )
    window_scope_signals: dict[str, dict[str, Any]] = {}
    window_promoted_ids: set[str] = set()
    for row in context.all_ws_payloads:
        ws_id = str(row.get("idea_id", "")).strip()
        if not ws_id:
            continue
        matching_rows = [
            item
            for item in [*window_events, *window_transactions]
            if isinstance(item, Mapping) and context.window_row_has_workstream(row=item, ws_id=ws_id)
        ]
        verified_row_count = sum(1 for item in matching_rows if context.row_is_verified_scoped_signal(item))
        has_any_window_signal = bool(ws_id in completed_ids or matching_rows)
        governance_only_local_change = bool(matching_rows) and all(
            context.row_is_governance_only_local_change(item)
            for item in matching_rows
        )
        broad_fanout_only = bool(matching_rows) and not verified_row_count and all(
            len(context.window_row_workstreams(item)) > int(context.scoped_verified_max_fanout)
            for item in matching_rows
        )
        signal = scope_signal_ladder.compass_window_scope_signal(
            scope_id=ws_id,
            workstream_row=row,
            delivery_snapshot=context.delivery_workstreams.get(ws_id, {}),
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
        for row in context.all_ws_payloads:
            ws_id = str(row.get("idea_id", "")).strip()
            if ws_id in window_promoted_ids:
                _append_focus_row(ws_id)
    _emit_progress(
        context.progress_callback,
        stage="window_facts_prepared",
        message=(
            f"{hours}h: {len(window_active_ids)} active scopes, "
            f"{len(window_verified_ids)} verified scoped, {len(window_promoted_ids)} promoted, "
            f"{len(window_events)} events, {len(window_transactions)} transactions, "
            f"{len(recent_completed)} recent completions"
        ),
    )

    focus_ids = {str(item.get("idea_id", "")).strip() for item in focus_rows if str(item.get("idea_id", "")).strip()}
    focus_actions = [item for item in context.next_actions if str(item.get("idea_id", "")).strip() in focus_ids]
    window_kpis = dict(kpis)
    if context.self_host_risks:
        window_kpis["critical_risks"] = int(window_kpis.get("critical_risks", 0) or 0) + len(context.self_host_risks)
    window_key = f"{int(hours)}h"
    prior_window_runtime = compass_standup_runtime_reuse.window_runtime_state(
        context.prior_runtime_state,
        window_key=window_key,
    )
    prior_global_brief = compass_standup_runtime_reuse.window_global_brief(
        context.prior_runtime_state,
        window_key=window_key,
    )
    prior_scoped_briefs = compass_standup_runtime_reuse.window_scoped_briefs(
        context.prior_runtime_state,
        window_key=window_key,
    )
    global_reuse_fingerprint = compass_standup_runtime_reuse.global_reuse_fingerprint(
        window_hours=hours,
        focus_rows=focus_rows,
        active_ws_rows=context.active_ws_rows,
        touched_workstreams=touched_ws,
        next_actions=focus_actions or context.next_actions,
        recent_completed=recent_completed,
        execution_updates=execution_update_index.get("global", []),
        transaction_updates=transaction_update_index.get("global", []),
        kpis=window_kpis,
        risk_summary=risk_posture_window,
        self_host_snapshot=context.self_host,
    )
    standup_runtime_window: dict[str, Any] = {
        "global_reuse_fingerprint": global_reuse_fingerprint,
        "scoped_reuse_fingerprints": {},
        "verified_scope_ids": sorted(window_verified_ids),
        "promoted_scope_ids": sorted(window_promoted_ids),
        "scope_signals": window_scope_signals,
    }
    global_fact_packet = context.build_global_standup_fact_packet(
        ws_rows=focus_rows,
        ws_index=context.ws_index,
        active_ws_rows=context.active_ws_rows,
        event_counts_by_ws=event_counts_by_ws,
        next_actions=focus_actions or context.next_actions,
        recent_completed=recent_completed,
        window_events=window_events,
        window_transactions=window_transactions,
        execution_updates=execution_update_index.get("global", []),
        transaction_updates=transaction_update_index.get("global", []),
        window_hours=hours,
        risk_rows=global_risk_rows,
        risk_summary=risk_posture_window,
        kpis=window_kpis,
        self_host_snapshot=context.self_host,
        self_host_risks=context.self_host_risks,
        now=context.now,
    )
    reusable_global_sections = context.reusable_brief_sections_for_fact_packet(
        brief=prior_global_brief,
        fact_packet=global_fact_packet,
    )
    if (
        str(prior_window_runtime.get("global_reuse_fingerprint", "")).strip() == global_reuse_fingerprint
        and reusable_global_sections is not None
    ):
        standup_global = compass_standup_runtime_reuse.reuse_ready_brief(
            brief=prior_global_brief,
            generated_utc=context.generated_utc,
            fingerprint=f"salient:{global_reuse_fingerprint}",
            sections=reusable_global_sections,
        )
    else:
        standup_global = compass_standup_brief_narrator.build_standup_brief(
            repo_root=context.repo_root,
            fact_packet=global_fact_packet,
            generated_utc=context.generated_utc,
            config=context.reasoning_config,
            provider=None,
            allow_provider=False,
            prefer_provider=False,
        )
        standup_global = context.brief_with_known_failure_state(
            repo_root=context.repo_root,
            window_key=window_key,
            fact_packet=global_fact_packet,
            generated_utc=context.generated_utc,
            brief=standup_global,
        )
    standup_scoped: dict[str, dict[str, Any]] = {}
    scoped_packet_index: dict[str, dict[str, Any]] = {}
    for ws in context.all_ws_payloads:
        ws_id = str(ws.get("idea_id", "")).strip()
        if not ws_id:
            continue
        if ws_id not in window_verified_ids:
            standup_scoped[ws_id] = context.inactive_scoped_standup_brief(
                ws_id=ws_id,
                window_hours=hours,
                generated_utc=context.generated_utc,
            )
            continue
        scoped_risk_rows = context.scope_risk_rows(
            ws_id=ws_id,
            bug_items=context.bug_items,
            traceability_risks=context.traceability_risks,
            stale_diagrams=context.stale_diagrams,
        )
        scoped_risk_summary = context.build_risk_posture_summary(
            open_critical=len(scoped_risk_rows.get("bugs", [])),
            traceability_risks=scoped_risk_rows.get("traceability", []),
            stale_diagrams=scoped_risk_rows.get("stale_diagrams", []),
        )
        scoped_reuse_fingerprint = compass_standup_runtime_reuse.scoped_reuse_fingerprint(
            row=ws,
            window_hours=hours,
            next_action_tokens=[
                str(item.get("action", "")).strip()
                for item in context.next_actions
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
            self_host_snapshot=context.self_host,
        )
        standup_runtime_window["scoped_reuse_fingerprints"][ws_id] = scoped_reuse_fingerprint
        scoped_fact_packet = context.build_scoped_standup_fact_packet(
            row=ws,
            next_actions=context.next_actions,
            recent_completed=recent_completed,
            window_events=window_events,
            window_transactions=window_transactions,
            execution_updates=execution_update_index.get("by_workstream", {}).get(ws_id, []),
            transaction_updates=transaction_update_index.get("by_workstream", {}).get(ws_id, []),
            window_hours=hours,
            risk_rows=scoped_risk_rows,
            risk_summary=scoped_risk_summary,
            self_host_snapshot=context.self_host,
            now=context.now,
        )
        scoped_packet_index[ws_id] = scoped_fact_packet
        reusable_scoped_sections = context.reusable_brief_sections_for_fact_packet(
            brief=prior_scoped_briefs.get(ws_id),
            fact_packet=scoped_fact_packet,
        )
        prior_scoped_runtime = prior_window_runtime.get("scoped_reuse_fingerprints", {})
        if (
            isinstance(prior_scoped_runtime, Mapping)
            and str(prior_scoped_runtime.get(ws_id, "")).strip() == scoped_reuse_fingerprint
            and reusable_scoped_sections is not None
        ):
            standup_scoped[ws_id] = compass_standup_runtime_reuse.reuse_ready_brief(
                brief=prior_scoped_briefs[ws_id],
                generated_utc=context.generated_utc,
                fingerprint=f"salient:{scoped_reuse_fingerprint}",
                sections=reusable_scoped_sections,
            )
            continue
        standup_scoped[ws_id] = compass_standup_brief_narrator.build_standup_brief(
            repo_root=context.repo_root,
            fact_packet=scoped_fact_packet,
            generated_utc=context.generated_utc,
            config=context.reasoning_config,
            provider=None,
            allow_provider=False,
            prefer_provider=False,
        )
        standup_scoped[ws_id] = context.brief_with_known_failure_state(
            repo_root=context.repo_root,
            window_key=window_key,
            fact_packet=scoped_fact_packet,
            generated_utc=context.generated_utc,
            brief=standup_scoped[ws_id],
            scope_id=ws_id,
        )
    _emit_progress(
        context.progress_callback,
        stage="standup_briefs_built",
        message=(
            f"{hours}h: global {str(standup_global.get('source', '')).strip().lower() or 'unknown'}, "
            f"scoped provider={sum(1 for brief in standup_scoped.values() if str(brief.get('source', '')).strip().lower() == 'provider')}, "
            f"cache={sum(1 for brief in standup_scoped.values() if str(brief.get('source', '')).strip().lower() == 'cache')}, "
            f"inactive={sum(1 for brief in standup_scoped.values() if str(brief.get('source', '')).strip().lower() == 'unavailable')}"
        ),
    )

    return CompassWindowSummary(
        kpis=window_kpis,
        global_brief=standup_global,
        scoped_briefs=standup_scoped,
        scoped_packets=scoped_packet_index,
        runtime_window=standup_runtime_window,
        global_fact_packet=global_fact_packet,
    )
