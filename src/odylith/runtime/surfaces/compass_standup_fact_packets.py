"""Standup fact-packet builders extracted from Compass runtime."""

from __future__ import annotations

import datetime as dt
import re
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.governance import workstream_progress as workstream_progress_runtime
from odylith.runtime.surfaces import compass_briefing_support
from odylith.runtime.surfaces import compass_dashboard_base as compass_base
from odylith.runtime.surfaces import compass_outcome_digest_runtime
from odylith.runtime.surfaces import compass_self_host_runtime
from odylith.runtime.surfaces import compass_standup_brief_narrator


_ACTION_LEAD_RE = re.compile(
    r"^(?:add|align|audit|backfill|bind|build|capture|carry|clean(?:\s+up)?|close|codify|collapse|"
    r"complete|convert|cut|define|deliver|document|enable|enforce|finish|harden|implement|introduce|"
    r"keep|land|make|migrate|move|pull|publish|re-?add|reconcile|refresh|remove|replace|reuse|seed|"
    r"ship|stabilize|stop|tighten|unify|update|validate|verify|wire)\b",
    re.IGNORECASE,
)

_COMPASS_TZ = compass_base._COMPASS_TZ
_action_clause_for_narrative = compass_briefing_support._action_clause_for_narrative
_action_tokens_for_workstream = compass_briefing_support._action_tokens_for_workstream
_build_completed_group_lines = compass_briefing_support._build_completed_group_lines
_collect_window_execution_updates = compass_briefing_support._collect_window_execution_updates
_collect_window_transaction_updates = compass_outcome_digest_runtime._collect_window_transaction_updates
_decapitalize_clause = compass_briefing_support._decapitalize_clause
_estimate_remaining_days = compass_briefing_support._estimate_remaining_days
_execution_status_phrase = compass_briefing_support._execution_status_phrase
_finalize_standup_fact_packet = compass_briefing_support._finalize_standup_fact_packet
_follow_on_text = compass_briefing_support._follow_on_text
_forcing_function_text = compass_briefing_support._forcing_function_text
_freshness_age_label = compass_briefing_support._freshness_age_label
_freshness_bucket = compass_briefing_support._freshness_bucket
_freshness_fact_text = compass_briefing_support._freshness_fact_text
_global_fallback_next_text = compass_briefing_support._global_fallback_next_text
_global_fallback_risk_text = compass_briefing_support._global_fallback_risk_text
_latest_evidence_marker = compass_briefing_support._latest_evidence_marker
_latest_window_activity_iso = compass_briefing_support._latest_window_activity_iso
_lineage_context_summary = compass_briefing_support._lineage_context_summary
_narrative_excerpt = compass_base._narrative_excerpt
_normalize_action_task = compass_briefing_support._normalize_action_task
_plan_deliverable_label = compass_briefing_support._plan_deliverable_label
_progress_story = compass_briefing_support._progress_story
_risk_facts = compass_briefing_support._risk_facts
_safe_iso = compass_base._safe_iso
_scoped_fallback_next_text = compass_briefing_support._scoped_fallback_next_text
_scoped_fallback_risk_text = compass_briefing_support._scoped_fallback_risk_text
_standup_fact = compass_briefing_support._standup_fact
_timeline_clause = compass_briefing_support._timeline_clause
_wave_context_summary = compass_briefing_support._wave_context_summary
_ws_label = compass_briefing_support._ws_label
_ws_why_context = compass_briefing_support._ws_why_context


def _self_host_status_fact(snapshot: Mapping[str, Any]) -> dict[str, Any] | None:
    return compass_self_host_runtime.self_host_status_fact(
        snapshot,
        standup_fact_builder=_standup_fact,
    )


def _sentence(text: str) -> str:
    token = str(text or "").strip().rstrip(".")
    if not token:
        return ""
    return token[0].upper() + token[1:] + "."


def _movement_fact_text(summary: str) -> str:
    return _sentence(summary)


def _direction_fact_text(
    *,
    label: str,
    status_phrase: str,
    direction_text: str,
) -> str:
    action = str(direction_text or "").strip().rstrip(".")
    if not action:
        return _sentence(f"{label} is {status_phrase}")
    match_candidate = action.lstrip("`'\"“”‘’")
    if not _ACTION_LEAD_RE.match(match_candidate):
        action = f"land {action}"
    return _sentence(f"{action}; {label} is {status_phrase}")


def _progress_fact_text(*, done_tasks: int, total_tasks: int, progress_story: str) -> str:
    story = str(progress_story or "").strip().rstrip(".")
    if total_tasks > 0:
        return _sentence(f"Checklist is {done_tasks}/{total_tasks}; {story}")
    return _sentence(story)


def _timeline_fact_text(timeline_story: str) -> str:
    story = str(timeline_story or "").strip().rstrip(".")
    if not story:
        return ""
    if story.lower().startswith(("projected ", "provisional ")):
        return _sentence(f"ETA is {story}")
    return _sentence(story)


def _direction_clause_for_story(
    *,
    label: str,
    purpose: str,
    benefit: str,
    use_story: str,
    architecture_consequence: str,
) -> str:
    direction_source = benefit or architecture_consequence or use_story or purpose
    direction_source = _narrative_excerpt(direction_source, max_sentences=1, max_chars=180)
    if (
        direction_source.lower().startswith("for operators who ")
        or direction_source.lower().startswith("if ")
        or "product claim" in direction_source.lower()
    ):
        direction_source = _narrative_excerpt(
            architecture_consequence or benefit or use_story or purpose,
            max_sentences=1,
            max_chars=180,
        )
    for prefix in (
        "The architecture move is to ",
        "The architecture move is ",
        "The change now is to ",
        "The change is to ",
    ):
        if direction_source.startswith(prefix):
            direction_source = direction_source[len(prefix):].strip()
            break
    direction_source = direction_source.replace(
        ", which gives operators a clearer contract and lower coordination risk.",
        "",
    ).replace(
        " which gives operators a clearer contract and lower coordination risk.",
        "",
    ).strip()
    if direction_source.lower().startswith(("this gives operators a clearer contract", "gives operators a clearer contract")):
        direction_source = _narrative_excerpt(
            purpose or benefit or use_story or label,
            max_sentences=1,
            max_chars=180,
        )
    direction_lead = direction_source.lstrip("`'\"“”‘’").replace("`", "")
    if _ACTION_LEAD_RE.match(direction_lead):
        return direction_source
    return _action_clause_for_narrative(direction_source) or direction_source


def _build_scoped_standup_fact_packet(
    *,
    row: Mapping[str, Any],
    next_actions: Sequence[Mapping[str, str]],
    recent_completed: Sequence[Mapping[str, str]],
    window_events: Sequence[Mapping[str, Any]],
    window_transactions: Sequence[Mapping[str, Any]],
    execution_updates: Sequence[Mapping[str, Any]] | None = None,
    transaction_updates: Sequence[Mapping[str, Any]] | None = None,
    window_hours: int,
    risk_rows: Mapping[str, Sequence[Mapping[str, Any]]],
    risk_summary: str,
    self_host_snapshot: Mapping[str, Any] | None = None,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    now_value = now if isinstance(now, dt.datetime) else dt.datetime.now(tz=_COMPASS_TZ)
    idea_id = str(row.get("idea_id", "")).strip()
    label = _ws_label(row)
    why_context = _ws_why_context(row)
    purpose = why_context.get("purpose", "")
    benefit = why_context.get("benefit", "")
    use_story = why_context.get("use_story", "") or purpose
    architecture_consequence = why_context.get("architecture_consequence", "") or benefit
    direction_clause = _direction_clause_for_story(
        label=label,
        purpose=purpose,
        benefit=benefit,
        use_story=use_story,
        architecture_consequence=architecture_consequence,
    )
    status = str(row.get("status", "")).strip() or "unknown"
    plan = row.get("plan", {}) if isinstance(row.get("plan"), Mapping) else {}
    progress_ratio = float(plan.get("progress_ratio", 0.0) or 0.0)
    done_tasks = int(plan.get("done_tasks", 0) or 0)
    total_tasks = int(plan.get("total_tasks", 0) or 0)
    eta_days, eta_source = _estimate_remaining_days(row)
    section_candidates: dict[str, list[dict[str, Any]]] = {
        key: [] for key, _label in compass_standup_brief_narrator.STANDUP_BRIEF_SECTIONS
    }

    completed_match = [item for item in recent_completed if str(item.get("backlog", "")).strip() == idea_id]
    deliverables = [
        _plan_deliverable_label(str(item.get("plan", "")).strip())
        for item in completed_match
    ]
    deliverables = [item for item in deliverables if item]
    transaction_updates = (
        [dict(item) for item in transaction_updates if isinstance(item, Mapping)]
        if isinstance(transaction_updates, Sequence)
        else _collect_window_transaction_updates(window_transactions, ws_id=idea_id, max_items=2)
    )
    execution_updates = (
        [dict(item) for item in execution_updates if isinstance(item, Mapping)]
        if isinstance(execution_updates, Sequence)
        else _collect_window_execution_updates(window_events, ws_id=idea_id, max_items=2)
    )
    execution_highlights = [
        str(item.get("summary", "")).strip()
        for item in (list(transaction_updates) + list(execution_updates))
        if str(item.get("summary", "")).strip()
    ]
    execution_highlights = list(dict.fromkeys(execution_highlights))
    filtered_execution_highlights = [
        summary
        for summary in execution_highlights
        if not any(
            token in summary.lower()
            for token in (
                "activated odylith runtime",
                "detached source-local self-host mode",
                "repo pin is",
                "governance runtime surfaces",
                "governed planning surfaces",
                "packet-level bundle",
                "plan updated:",
                "checklist progress updated",
            )
        )
    ]
    next_tokens = _action_tokens_for_workstream(next_actions, idea_id, max_items=2)
    status_phrase = _execution_status_phrase(
        status=status,
        has_execution_signal=bool(filtered_execution_highlights or execution_highlights),
        progress_ratio=progress_ratio,
    )
    progress_story = _progress_story(done_tasks=done_tasks, total_tasks=total_tasks)
    timeline_story = _timeline_clause(
        eta_days=eta_days,
        eta_source=eta_source,
        status=status,
        has_execution_signal=bool(filtered_execution_highlights or execution_highlights),
    )
    timeline = row.get("timeline", {}) if isinstance(row.get("timeline"), Mapping) else {}
    latest_evidence_ts, freshness_source = _latest_evidence_marker(
        window_events=window_events,
        window_transactions=window_transactions,
        ws_id=idea_id,
        fallback_last_activity_iso=str(timeline.get("last_activity_iso", "")).strip(),
    )
    freshness_bucket = _freshness_bucket(latest_ts=latest_evidence_ts, now=now_value)
    freshness_age_label = _freshness_age_label(latest_ts=latest_evidence_ts, now=now_value)
    freshness_text = _freshness_fact_text(
        label=label,
        freshness_bucket=freshness_bucket,
        freshness_age_label=freshness_age_label,
        source_kind=freshness_source,
    )
    fallback_next_text = _scoped_fallback_next_text(
        label=label,
        purpose=purpose,
        status=status,
        done_tasks=done_tasks,
        total_tasks=total_tasks,
        freshness_bucket=freshness_bucket,
    )
    wave_context = _wave_context_summary(row)
    lineage_context = _lineage_context_summary(row)

    if deliverables:
        joined = deliverables[0] if len(deliverables) == 1 else f"{deliverables[0]} and {deliverables[1]}"
        section_candidates["completed"].append(
            _standup_fact(
                section_key="completed",
                voice_hint="operator",
                priority=100,
                text=f"Closed cleanly in this window: {joined}.",
                source="plan_completion",
                kind="plan_completion",
                workstreams=[idea_id],
            )
        )
    else:
        section_candidates["completed"].append(
            _standup_fact(
                section_key="completed",
                voice_hint="executive",
                priority=62,
                text=_sentence(f"Nothing fully closed for {label} in the last {window_hours} hours"),
                source="window",
                kind="window_summary",
                workstreams=[idea_id],
            )
        )
    for index, summary in enumerate((filtered_execution_highlights or execution_highlights)[:2]):
        section_candidates["completed"].append(
            _standup_fact(
                section_key="completed",
                voice_hint="operator",
                priority=94 - index,
                text=_movement_fact_text(summary),
                source="transaction_or_event",
                kind="execution_highlight",
                workstreams=[idea_id],
            )
        )

    direction_text = _decapitalize_clause(
        direction_clause or f"keep {label} moving through the dependent delivery work"
    )
    include_self_host_status = False
    scope_context = " ".join(part for part in [label, purpose, benefit, use_story] if part).lower()
    if isinstance(self_host_snapshot, Mapping) and scope_context:
        include_self_host_status = any(
            token in scope_context
            for token in (
                "toolchain",
                "lane boundary",
                "pinned dogfood",
                "source-local",
                "maintainer execution",
                "consumer execution",
            )
        )
    section_candidates["current_execution"].append(
        _standup_fact(
            section_key="current_execution",
            voice_hint="executive",
            priority=100,
            text=_direction_fact_text(
                label=label,
                status_phrase=status_phrase,
                direction_text=direction_text,
            ),
            source="workstream_metadata",
            kind="direction",
            workstreams=[idea_id],
        )
    )
    if include_self_host_status:
        self_host_status = _self_host_status_fact(self_host_snapshot)
        if self_host_status is not None:
            section_candidates["current_execution"].append(self_host_status)
    section_candidates["current_execution"].append(
        _standup_fact(
            section_key="current_execution",
            voice_hint="operator",
            priority=90,
            text=_progress_fact_text(
                done_tasks=done_tasks,
                total_tasks=total_tasks,
                progress_story=progress_story,
            ),
            source="plan",
            kind="checklist",
            workstreams=[idea_id],
        )
    )
    section_candidates["current_execution"].append(
        _standup_fact(
            section_key="current_execution",
            voice_hint="operator",
            priority=86,
            text=_timeline_fact_text(timeline_story),
            source="timeline",
            kind="timeline",
            workstreams=[idea_id],
        )
    )
    if freshness_text:
        section_candidates["current_execution"].append(
            _standup_fact(
                section_key="current_execution",
                voice_hint="operator",
                priority=80,
                text=freshness_text,
                source="freshness",
                kind="freshness",
                workstreams=[idea_id],
            )
        )
    for extra_index, extra_text in enumerate([wave_context, lineage_context], start=1):
        if not extra_text:
            continue
        section_candidates["current_execution"].append(
            _standup_fact(
                section_key="current_execution",
                voice_hint="operator",
                priority=82 - extra_index,
                text=extra_text,
                source="topology",
                kind="topology",
                workstreams=[idea_id],
            )
        )

    fallback_risk_text = _scoped_fallback_risk_text(
        label=label,
        total_tasks=total_tasks,
        done_tasks=done_tasks,
        eta_days=eta_days,
        eta_source=eta_source,
        wave_context=wave_context,
        risk_summary=risk_summary,
        freshness_bucket=freshness_bucket,
        freshness_text=freshness_text,
    )
    next_context = purpose
    if (
        str(next_context or "").strip().lower().startswith("for operators who ")
        or str(next_context or "").strip().lower().startswith("if ")
        or "product claim" in str(next_context or "").strip().lower()
    ):
        next_context = benefit or architecture_consequence or purpose

    if next_tokens:
        section_candidates["next_planned"].append(
            _standup_fact(
                section_key="next_planned",
                voice_hint="operator",
                priority=100,
                text=_forcing_function_text(action=next_tokens[0], label=label, purpose=next_context),
                source="plan",
                kind="forcing_function",
                workstreams=[idea_id],
            )
        )
    if len(next_tokens) > 1:
        section_candidates["next_planned"].append(
            _standup_fact(
                section_key="next_planned",
                voice_hint="operator",
                priority=90,
                text=_follow_on_text(action=next_tokens[1], label=label, benefit=benefit),
                source="plan",
                kind="follow_on",
                workstreams=[idea_id],
            )
        )
    elif wave_context:
        section_candidates["next_planned"].append(
            _standup_fact(
                section_key="next_planned",
                voice_hint="operator",
                priority=84,
                text=wave_context,
                source="topology",
                kind="unblock_context",
                workstreams=[idea_id],
            )
        )
    else:
        section_candidates["next_planned"].append(
            _standup_fact(
                section_key="next_planned",
                voice_hint="operator",
                priority=76,
                text=fallback_next_text,
                source="plan",
                kind="fallback_next",
                workstreams=[idea_id],
            )
        )

    section_candidates["risks_to_watch"].extend(
        _risk_facts(
            ws_id=idea_id,
            risk_rows=risk_rows,
            risk_summary=risk_summary,
            fallback_text=fallback_risk_text,
        )
    )

    return _finalize_standup_fact_packet(
        window_key=f"{int(window_hours)}h",
        scope={
            "mode": "scoped",
            "idea_id": idea_id,
            "label": label,
            "status": status,
        },
        summary={
            "window_hours": int(window_hours),
            "purpose": purpose,
            "benefit": benefit,
            "use_story": use_story,
            "architecture_consequence": architecture_consequence,
            "risk_summary": risk_summary,
            "self_host": {
                "repo_role": str(self_host_snapshot.get("repo_role", "")).strip()
                if isinstance(self_host_snapshot, Mapping)
                else "",
                "posture": str(self_host_snapshot.get("posture", "")).strip()
                if isinstance(self_host_snapshot, Mapping)
                else "",
                "runtime_source": str(self_host_snapshot.get("runtime_source", "")).strip()
                if isinstance(self_host_snapshot, Mapping)
                else "",
                "pinned_version": str(self_host_snapshot.get("pinned_version", "")).strip()
                if isinstance(self_host_snapshot, Mapping)
                else "",
                "active_version": str(self_host_snapshot.get("active_version", "")).strip()
                if isinstance(self_host_snapshot, Mapping)
                else "",
                "launcher_present": bool(self_host_snapshot.get("launcher_present"))
                if isinstance(self_host_snapshot, Mapping)
                else False,
                "release_eligible": self_host_snapshot.get("release_eligible")
                if isinstance(self_host_snapshot, Mapping)
                else None,
            },
            "freshness": {
                "bucket": freshness_bucket,
                "latest_evidence_utc": _safe_iso(latest_evidence_ts) if latest_evidence_ts else "",
                "source": freshness_source,
            },
            "storyline": {
                "flagship_lane": label,
                "direction": direction_text,
                "proof": (filtered_execution_highlights or execution_highlights)[0]
                if (filtered_execution_highlights or execution_highlights)
                else "",
                "forcing_function": next_tokens[0] if next_tokens else fallback_next_text,
                "use_story": use_story,
                "architecture_consequence": architecture_consequence,
                "watch_item": fallback_risk_text,
            },
        },
        section_candidates=section_candidates,
    )


def _build_global_standup_fact_packet(
    *,
    ws_rows: Sequence[Mapping[str, Any]],
    ws_index: Mapping[str, Mapping[str, Any]],
    active_ws_rows: Sequence[Mapping[str, Any]],
    event_counts_by_ws: Mapping[str, int],
    next_actions: Sequence[Mapping[str, str]],
    recent_completed: Sequence[Mapping[str, str]],
    window_events: Sequence[Mapping[str, Any]],
    window_transactions: Sequence[Mapping[str, Any]],
    execution_updates: Sequence[Mapping[str, Any]] | None = None,
    transaction_updates: Sequence[Mapping[str, Any]] | None = None,
    window_hours: int,
    risk_rows: Mapping[str, Sequence[Mapping[str, Any]]],
    risk_summary: str,
    kpis: Mapping[str, Any],
    self_host_snapshot: Mapping[str, Any],
    self_host_risks: Sequence[Mapping[str, Any]],
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    now_value = now if isinstance(now, dt.datetime) else dt.datetime.now(tz=_COMPASS_TZ)
    focused_primary = dict(ws_rows[0]) if ws_rows else {}
    primary_label = _ws_label(focused_primary) if focused_primary else "current priority lane"
    primary_status = str(focused_primary.get("status", "")).strip() or "unknown"
    primary_why_context = _ws_why_context(focused_primary)
    primary_purpose = primary_why_context.get("purpose", "")
    primary_benefit = primary_why_context.get("benefit", "")
    primary_use_story = primary_why_context.get("use_story", "") or primary_purpose
    primary_architecture_consequence = primary_why_context.get("architecture_consequence", "") or primary_benefit
    direction_clause = _direction_clause_for_story(
        label=primary_label,
        purpose=primary_purpose,
        benefit=primary_benefit,
        use_story=primary_use_story,
        architecture_consequence=primary_architecture_consequence,
    )
    primary_plan = focused_primary.get("plan", {}) if isinstance(focused_primary.get("plan"), Mapping) else {}
    primary_progress_ratio = float(primary_plan.get("progress_ratio", 0.0) or 0.0)
    eta_days, eta_source = _estimate_remaining_days(focused_primary if focused_primary else {})
    execution_updates = (
        [dict(item) for item in execution_updates if isinstance(item, Mapping)]
        if isinstance(execution_updates, Sequence)
        else _collect_window_execution_updates(window_events, max_items=3)
    )
    transaction_updates = (
        [dict(item) for item in transaction_updates if isinstance(item, Mapping)]
        if isinstance(transaction_updates, Sequence)
        else _collect_window_transaction_updates(window_transactions, max_items=3)
    )
    execution_highlights = [
        str(item.get("summary", "")).strip()
        for item in (list(transaction_updates) + list(execution_updates))
        if str(item.get("summary", "")).strip()
    ]
    execution_highlights = list(dict.fromkeys(execution_highlights))
    filtered_execution_highlights = [
        summary
        for summary in execution_highlights
        if not any(
            token in summary.lower()
            for token in (
                "activated odylith runtime",
                "detached source-local self-host mode",
                "repo pin is",
                "plan updated:",
                "checklist progress updated",
            )
        )
    ]
    status_phrase = _execution_status_phrase(
        status=primary_status,
        has_execution_signal=bool(filtered_execution_highlights or execution_highlights),
        progress_ratio=primary_progress_ratio,
    )
    timeline_story = _timeline_clause(
        eta_days=eta_days,
        eta_source=eta_source,
        status=primary_status,
        has_execution_signal=bool(filtered_execution_highlights or execution_highlights),
    )
    latest_evidence_ts, freshness_source = _latest_evidence_marker(
        window_events=window_events,
        window_transactions=window_transactions,
        ws_id=None,
        fallback_last_activity_iso=_latest_window_activity_iso(active_ws_rows or ws_rows),
    )
    freshness_bucket = _freshness_bucket(latest_ts=latest_evidence_ts, now=now_value)
    freshness_age_label = _freshness_age_label(latest_ts=latest_evidence_ts, now=now_value)
    freshness_text = _freshness_fact_text(
        label=primary_label,
        freshness_bucket=freshness_bucket,
        freshness_age_label=freshness_age_label,
        source_kind=freshness_source,
    )
    completed_group_lines = _build_completed_group_lines(recent_completed, ws_index=ws_index)
    focus_row_ids = {
        str(row.get("idea_id", "")).strip()
        for row in ws_rows
        if isinstance(row, Mapping) and str(row.get("idea_id", "")).strip()
    }
    ranked_activity = sorted(
        [(ws_id, int(count)) for ws_id, count in event_counts_by_ws.items() if ws_id and ws_id in focus_row_ids],
        key=lambda item: (-item[1], item[0]),
    )
    if not ranked_activity:
        active_ids = {
            str(row.get("idea_id", "")).strip()
            for row in active_ws_rows
            if isinstance(row, Mapping) and str(row.get("idea_id", "")).strip()
        }
        ranked_activity = sorted(
            [(ws_id, int(count)) for ws_id, count in event_counts_by_ws.items() if ws_id and ws_id in active_ids],
            key=lambda item: (-item[1], item[0]),
        )
    top_activity_labels: list[str] = []
    for ws_id, _count in ranked_activity[:2]:
        ws_row = ws_index.get(ws_id, {})
        label = _ws_label(ws_row) if ws_row else ws_id
        top_activity_labels.append(_narrative_excerpt(label, max_sentences=1, max_chars=120))
    window_coverage_ids = [
        ws_id
        for ws_id, _count in ranked_activity
        if ws_id
    ]
    if not window_coverage_ids:
        window_coverage_ids = [ws_id for ws_id in focus_row_ids if ws_id]
    window_coverage_ids = list(dict.fromkeys(window_coverage_ids))
    window_coverage_sample = window_coverage_ids[:6]
    if len(window_coverage_ids) <= 1:
        window_coverage_text = (
            f"Work stayed inside {window_coverage_sample[0]}."
            if window_coverage_sample
            else "Work stayed inside the primary lane."
        )
    elif len(window_coverage_ids) <= len(window_coverage_sample):
        if len(window_coverage_sample) == 2:
            joined_sample = " and ".join(window_coverage_sample)
        else:
            joined_sample = ", ".join(window_coverage_sample[:-1]) + f", and {window_coverage_sample[-1]}"
        window_coverage_text = f"Work moved across {len(window_coverage_ids)} workstreams: {joined_sample}."
    else:
        if len(window_coverage_sample) == 1:
            sample_text = window_coverage_sample[0]
        elif len(window_coverage_sample) == 2:
            sample_text = " and ".join(window_coverage_sample)
        else:
            sample_text = ", ".join(window_coverage_sample[:-1]) + f", and {window_coverage_sample[-1]}"
        window_coverage_text = f"Most of the movement this window sat in {sample_text}."
    active_count = len([row for row in active_ws_rows if isinstance(row, Mapping)])
    progress_summary = workstream_progress_runtime.summarize_active_progress(
        [row for row in active_ws_rows if isinstance(row, Mapping)]
    )
    progressed_count = int(progress_summary.get("tracked", 0) or 0) + int(progress_summary.get("closed", 0) or 0)
    active_untracked_count = int(progress_summary.get("active_untracked", 0) or 0)
    fallback_next_text = _global_fallback_next_text(
        primary_label=primary_label,
        primary_purpose=primary_purpose,
        active_count=active_count,
        freshness_bucket=freshness_bucket,
    )
    include_self_host_status = False
    scope_context = " ".join(
        part for part in [primary_label, primary_purpose, primary_benefit, primary_use_story] if part
    ).lower()
    if isinstance(self_host_snapshot, Mapping) and scope_context:
        include_self_host_status = any(
            token in scope_context
            for token in (
                "toolchain",
                "launcher",
                "lane boundary",
                "pinned dogfood",
                "source-local",
                "maintainer execution",
                "consumer execution",
            )
        )
    section_candidates: dict[str, list[dict[str, Any]]] = {
        key: [] for key, _label in compass_standup_brief_narrator.STANDUP_BRIEF_SECTIONS
    }

    if completed_group_lines:
        section_candidates["completed"].append(
            _standup_fact(
                section_key="completed",
                voice_hint="operator",
                priority=100,
                text=f"Closed cleanly in this window: {'; '.join(completed_group_lines[:2])}.",
                source="plan_completion",
                kind="plan_completion",
            )
        )
    else:
        section_candidates["completed"].append(
            _standup_fact(
                section_key="completed",
                voice_hint="executive",
                priority=64,
                text=_sentence(f"Nothing fully closed across the portfolio in the last {window_hours} hours"),
                source="window",
                kind="window_summary",
            )
        )
    for index, summary in enumerate(execution_highlights[:2]):
        if summary not in filtered_execution_highlights and completed_group_lines:
            continue
        section_candidates["completed"].append(
            _standup_fact(
                section_key="completed",
                voice_hint="operator",
                priority=94 - index,
                text=_movement_fact_text(summary),
                source="transaction_or_event",
                kind="execution_highlight",
            )
        )

    executive_direction = _decapitalize_clause(
        direction_clause or "keep the dependent follow-on workstreams moving"
    )
    section_candidates["current_execution"].append(
        _standup_fact(
            section_key="current_execution",
            voice_hint="executive",
            priority=100,
            text=_direction_fact_text(
                label=primary_label,
                status_phrase=status_phrase,
                direction_text=executive_direction,
            ),
            source="workstream_metadata",
            kind="direction",
            workstreams=[
                str(focused_primary.get("idea_id", "")).strip()
            ] if focused_primary else [],
        )
    )
    if include_self_host_status:
        self_host_status = _self_host_status_fact(self_host_snapshot)
        if self_host_status is not None:
            section_candidates["current_execution"].append(self_host_status)
    portfolio_posture = ""
    if active_count <= 0:
        portfolio_posture = "No implementation lane is moving right now."
    elif progressed_count >= active_count and active_count > 0:
        portfolio_posture = "Every active lane has moved beyond planning and into implementation."
    elif progressed_count > 0:
        if active_untracked_count > 0:
            portfolio_posture = (
                "Implementation is moving, but some active lanes still do not have checklist progress captured."
            )
        else:
            portfolio_posture = "Implementation is moving while some active lanes are still clearing plan setup."
    else:
        if active_untracked_count > 0:
            portfolio_posture = "Implementation has started, but checklist progress is not captured yet."
        else:
            portfolio_posture = "Most active lanes are still setting up the first implementation slice."
    if top_activity_labels:
        portfolio_posture = portfolio_posture.rstrip(".") + f" Heaviest movement is in {', '.join(top_activity_labels)}."
    section_candidates["current_execution"].append(
            _standup_fact(
                section_key="current_execution",
                voice_hint="operator",
                priority=66,
                text=portfolio_posture,
                source="portfolio",
                kind="portfolio_posture",
            )
        )
    if top_activity_labels:
        section_candidates["current_execution"].append(
            _standup_fact(
                section_key="current_execution",
                voice_hint="operator",
                priority=54,
                text=window_coverage_text,
                source="portfolio",
                kind="window_coverage",
                workstreams=window_coverage_ids,
            )
        )
    section_candidates["current_execution"].append(
            _standup_fact(
                section_key="current_execution",
                voice_hint="operator",
                priority=72,
                text=_timeline_fact_text(timeline_story),
                source="timeline",
                kind="timeline",
            )
        )
    if freshness_text:
        section_candidates["current_execution"].append(
            _standup_fact(
                section_key="current_execution",
                voice_hint="operator",
                priority=78,
                text=freshness_text,
                source="freshness",
                kind="freshness",
            )
        )

    next_action_tokens: list[str] = []
    for item in next_actions:
        action = _normalize_action_task(
            _narrative_excerpt(str(item.get("action", "")).strip(), max_sentences=1, max_chars=160)
        ).rstrip(" .;")
        if not action:
            continue
        action = action.replace("to the tracked corpus: ", "through ")
        action = action.replace("to the tracked corpus", "into coverage")
        action = action.replace("tracked corpus", "coverage")
        idea_id = str(item.get("idea_id", "")).strip()
        ws_row = ws_index.get(idea_id, {})
        label = _ws_label(ws_row) if ws_row else (idea_id or str(item.get("title", "")).strip() or "active workstream")
        next_action_tokens.append(f"{label}: {action}")
        if len(next_action_tokens) >= 2:
            break
    fallback_risk_text = _global_fallback_risk_text(
        active_ws_rows=active_ws_rows,
        primary_label=primary_label,
        eta_days=eta_days,
        eta_source=eta_source,
        risk_summary=risk_summary,
        freshness_bucket=freshness_bucket,
        freshness_text=freshness_text,
    )
    if next_action_tokens:
        section_candidates["next_planned"].append(
            _standup_fact(
                section_key="next_planned",
                voice_hint="operator",
                priority=100,
                text=f"{next_action_tokens[0]}.",
                source="plan",
                kind="forcing_function",
            )
        )
    if len(next_action_tokens) > 1:
        section_candidates["next_planned"].append(
            _standup_fact(
                section_key="next_planned",
                voice_hint="operator",
                priority=92,
                text=f"{next_action_tokens[1]}.",
                source="plan",
                kind="follow_on",
            )
        )
    elif not next_action_tokens:
        section_candidates["next_planned"].append(
            _standup_fact(
                section_key="next_planned",
                voice_hint="operator",
                priority=78,
                text=fallback_next_text,
                source="plan",
                kind="fallback_next",
            )
        )

    section_candidates["risks_to_watch"].extend(
        _risk_facts(
            ws_id=None,
            risk_rows=risk_rows,
            risk_summary=risk_summary,
            fallback_text=fallback_risk_text,
        )
    )
    if self_host_risks:
        first_self_host_risk = dict(self_host_risks[0])
        severity = str(first_self_host_risk.get("severity", "")).strip().lower()
        priority = 96 if severity == "error" else 88
        message = _narrative_excerpt(
            str(first_self_host_risk.get("message", "")).strip(),
            max_sentences=1,
            max_chars=240,
        )
        if message:
            section_candidates["risks_to_watch"].append(
                _standup_fact(
                    section_key="risks_to_watch",
                    voice_hint="operator",
                    priority=priority,
                    text=message,
                    source="self_host",
                    kind="self_host_posture",
                )
            )

    return _finalize_standup_fact_packet(
        window_key=f"{int(window_hours)}h",
        scope={
            "mode": "global",
            "idea_id": "",
            "label": "Global",
            "status": "mixed",
        },
        summary={
            "window_hours": int(window_hours),
            "active_workstreams": active_count,
            "touched_workstreams": int(kpis.get("touched_workstreams", 0) or 0),
            "recent_completed_plans": int(kpis.get("recent_completed_plans", 0) or 0),
            "critical_risks": int(kpis.get("critical_risks", 0) or 0),
            "purpose": primary_purpose,
            "benefit": primary_benefit,
            "use_story": primary_use_story,
            "architecture_consequence": primary_architecture_consequence,
            "risk_summary": risk_summary,
            "freshness": {
                "bucket": freshness_bucket,
                "latest_evidence_utc": _safe_iso(latest_evidence_ts) if latest_evidence_ts else "",
                "source": freshness_source,
            },
            "self_host": {
                "repo_role": str(self_host_snapshot.get("repo_role", "")).strip(),
                "posture": str(self_host_snapshot.get("posture", "")).strip(),
                "runtime_source": str(self_host_snapshot.get("runtime_source", "")).strip(),
                "pinned_version": str(self_host_snapshot.get("pinned_version", "")).strip(),
                "active_version": str(self_host_snapshot.get("active_version", "")).strip(),
                "launcher_present": bool(self_host_snapshot.get("launcher_present")),
                "release_eligible": self_host_snapshot.get("release_eligible"),
            },
            "storyline": {
                "flagship_lane": primary_label,
                "direction": executive_direction,
                "proof": filtered_execution_highlights[0] if filtered_execution_highlights else "",
                "forcing_function": next_action_tokens[0] if next_action_tokens else fallback_next_text,
                "use_story": primary_use_story,
                "architecture_consequence": primary_architecture_consequence,
                "watch_item": fallback_risk_text,
            },
        },
        section_candidates=section_candidates,
    )
