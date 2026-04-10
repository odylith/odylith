"""Outcome-digest and transaction-summary helpers for Compass runtime."""

from __future__ import annotations

import datetime as dt
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.governance import workstream_progress as workstream_progress_runtime


def _host():
    from odylith.runtime.surfaces import compass_dashboard_runtime as host

    return host


def _collect_window_transaction_updates(
    window_transactions: Sequence[Mapping[str, Any]],
    *,
    ws_id: str | None = None,
    max_items: int = 2,
    max_workstream_fanout: int = 16,
) -> list[dict[str, str]]:
    host = _host()
    _split_source_vs_generated_files = host._split_source_vs_generated_files
    _narrative_excerpt = host._narrative_excerpt
    _humanize_execution_event_summary = host._humanize_execution_event_summary
    _is_synthetic_plan_execution_signal = host._is_synthetic_plan_execution_signal
    _normalize_sentence = host._normalize_sentence
    _local_change_headline_phrase = host._local_change_headline_phrase
    _sanitize_digest_summary = host._sanitize_digest_summary
    _looks_generic_churn_summary = host._looks_generic_churn_summary
    _transaction_end_ts = host._transaction_end_ts
    _narrative_signal_score = host._narrative_signal_score
    _ordered_update_candidates = host._ordered_update_candidates

    prioritized: list[dict[str, str]] = []
    fallback: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in window_transactions:
        ws_tokens = [
            str(token).strip()
            for token in row.get("workstreams", [])
            if str(token).strip()
        ]
        if ws_id and ws_id not in ws_tokens:
            continue
        if ws_id is None and max_workstream_fanout > 0 and len(ws_tokens) > max_workstream_fanout:
            continue

        files = [
            str(token).strip()
            for token in row.get("files", [])
            if str(token).strip()
        ]
        source_files, generated_files = _split_source_vs_generated_files(files)
        non_plan_source_files = [
            str(path).strip()
            for path in source_files
            if not str(path).startswith(("odylith/technical-plans/", "docs/", "agents-guidelines/", "skills/"))
        ]
        has_non_plan_surface = bool(non_plan_source_files)
        event_count = int(row.get("event_count", 0) or 0)
        if not source_files and generated_files and event_count >= 12:
            continue

        context = _narrative_excerpt(str(row.get("context", "")).strip(), max_sentences=1, max_chars=220).strip()
        headline = _narrative_excerpt(str(row.get("headline", "")).strip(), max_sentences=1, max_chars=220).strip()
        summary = context or headline
        primary_event_summary = ""
        for item in row.get("events", []):
            if not isinstance(item, Mapping):
                continue
            item_kind = str(item.get("kind", "")).strip()
            if item_kind not in {"implementation", "decision", "statement", "commit"}:
                continue
            item_summary = _humanize_execution_event_summary(
                kind=item_kind,
                summary=str(item.get("summary", "")).strip(),
            )
            if not item_summary:
                continue
            if _is_synthetic_plan_execution_signal(
                kind=item_kind,
                source=str(item.get("source", "")).strip(),
                summary=item_summary,
            ):
                continue
            primary_event_summary = item_summary
            break

        summary_lower = _normalize_sentence(summary).lower()
        summary_looks_plan_only = (
            summary_lower.startswith("plan status")
            or summary_lower.startswith("plan kickoff")
            or summary_lower.startswith("plan milestone")
            or summary_lower.startswith("plan updated")
            or summary_lower.startswith("implementation checkpoint in ")
            or summary_lower.startswith("decision captured in ")
        )
        if primary_event_summary and (not summary or summary_looks_plan_only):
            summary = primary_event_summary
        elif summary_looks_plan_only and has_non_plan_surface:
            synthetic_local_events = [
                {"files": [path], "summary": f"Modified {path}"}
                for path in non_plan_source_files[:12]
            ]
            summary = _local_change_headline_phrase(
                local_events=synthetic_local_events,
                files_count=len(non_plan_source_files),
            )

        normalized_summary = _sanitize_digest_summary(summary)
        if not normalized_summary:
            continue
        if _looks_generic_churn_summary(normalized_summary):
            continue
        if normalized_summary.lower() in {"execution update", "updated code"}:
            continue
        if normalized_summary in seen:
            continue
        seen.add(normalized_summary)
        event_rows = row.get("events", [])
        event_kinds = {
            str(item.get("kind", "")).strip()
            for item in event_rows
            if isinstance(item, Mapping)
        }
        has_meaningful_primary_signal = False
        for item in event_rows:
            if not isinstance(item, Mapping):
                continue
            item_kind = str(item.get("kind", "")).strip()
            if item_kind not in {"implementation", "decision", "statement", "commit"}:
                continue
            if _is_synthetic_plan_execution_signal(
                kind=item_kind,
                source=str(item.get("source", "")).strip(),
                summary=str(item.get("summary", "")).strip(),
            ):
                continue
            has_meaningful_primary_signal = True
            break

        is_plan_only = bool(event_kinds) and event_kinds.issubset({"plan_update", "plan_completion"})
        ts = _transaction_end_ts(row)
        sort_ts = ts.timestamp() if isinstance(ts, dt.datetime) else 0.0
        candidate_score = _narrative_signal_score(normalized_summary, files=source_files)
        if has_meaningful_primary_signal:
            candidate_score += 120
        if has_non_plan_surface and not is_plan_only:
            candidate_score += 18
        if is_plan_only:
            candidate_score -= 30
        candidate = {
            "kind": "transaction",
            "summary": normalized_summary,
            "_score": candidate_score,
            "_sort_ts": sort_ts,
        }
        if has_meaningful_primary_signal or candidate_score >= 20:
            prioritized.append(candidate)
        else:
            fallback.append(candidate)

    updates: list[dict[str, str]] = []
    for bucket in (
        _ordered_update_candidates(prioritized),
        _ordered_update_candidates(fallback),
    ):
        for candidate in bucket:
            updates.append(candidate)
            if len(updates) >= max_items:
                return updates
    return updates


def _build_outcome_digest_for_workstream(
    *,
    row: Mapping[str, Any],
    next_actions: list[dict[str, str]],
    recent_completed: list[dict[str, str]],
    window_events: Sequence[Mapping[str, Any]],
    window_transactions: Sequence[Mapping[str, Any]],
    risk_posture: str,
) -> list[str]:
    host = _host()
    _estimate_remaining_days = host._estimate_remaining_days
    _ws_why_context = host._ws_why_context
    _ws_label = host._ws_label
    _collect_window_execution_updates = host._collect_window_execution_updates
    _progress_story = host._progress_story
    _execution_status_phrase = host._execution_status_phrase
    _clean_execution_clause = host._clean_execution_clause
    _periodize = host._periodize
    _timeline_clause = host._timeline_clause
    _action_tokens_for_workstream = host._action_tokens_for_workstream
    _plan_deliverable_label = host._plan_deliverable_label
    _risk_phrase = host._risk_phrase
    _normalize_sentence = host._normalize_sentence

    idea_id = str(row.get("idea_id", "")).strip()
    plan = row.get("plan", {})
    if not isinstance(plan, Mapping):
        plan = {}
    done_tasks = int(plan.get("done_tasks", 0) or 0)
    total_tasks = int(plan.get("total_tasks", 0) or 0)
    status = str(row.get("status", "")).strip() or "unknown"
    eta_days, eta_source = _estimate_remaining_days(row)

    why_context = _ws_why_context(row)
    purpose = why_context.get("purpose", "")
    benefit = why_context.get("benefit", "")
    use_story = why_context.get("use_story", "") or purpose
    architecture_consequence = why_context.get("architecture_consequence", "") or benefit
    label = _ws_label(row)

    completed_match = [item for item in recent_completed if str(item.get("backlog", "")).strip() == idea_id]
    transaction_updates = _collect_window_transaction_updates(window_transactions, ws_id=idea_id, max_items=2)
    transaction_update_summaries = [
        str(item.get("summary", "")).strip()
        for item in transaction_updates
        if str(item.get("summary", "")).strip()
    ]

    if completed_match:
        deliverables = [_plan_deliverable_label(str(item.get("plan", "")).strip()) for item in completed_match]
        deliverables = [item for item in deliverables if item]
        if deliverables:
            if len(deliverables) == 1:
                completed_line = f"Completed in this window: {label} closed {deliverables[0]}."
            else:
                completed_line = f"Completed in this window: {label} closed {deliverables[0]} and {deliverables[1]}."
        else:
            completed_line = f"Completed in this window: {label} closed a verified milestone."
        if transaction_update_summaries:
            completed_line = completed_line.rstrip(".") + f" Execution highlights: {transaction_update_summaries[0]}."
    elif transaction_update_summaries:
        if len(transaction_update_summaries) == 1:
            completed_line = (
                f"Completed in this window: milestone closeout is still in progress for {label}, "
                f"and implementation delivery moved forward with {transaction_update_summaries[0]}."
            )
        else:
            completed_line = (
                f"Completed in this window: milestone closeout is still in progress for {label}, and implementation delivery moved "
                f"forward with {transaction_update_summaries[0]}; {transaction_update_summaries[1]}."
            )
    else:
        completed_line = (
            f"Completed in this window: no milestone closeout recorded for {label}; "
            "implementation groundwork remains in progress."
        )

    current_actions = _action_tokens_for_workstream(next_actions, idea_id, max_items=1)
    timeline_updates = _collect_window_execution_updates(window_events, ws_id=idea_id, max_items=2)
    timeline_update_summaries = [
        str(item.get("summary", "")).strip()
        for item in timeline_updates
        if str(item.get("summary", "")).strip()
    ]
    execution_highlights = list(dict.fromkeys(transaction_update_summaries + timeline_update_summaries))
    progress_story = _progress_story(done_tasks=done_tasks, total_tasks=total_tasks)
    timeline_update_text = execution_highlights[0] if execution_highlights else ""
    has_execution_signal = bool(execution_highlights)
    status_phrase = _execution_status_phrase(
        status=status,
        has_execution_signal=has_execution_signal,
        progress_ratio=float(plan.get("progress_ratio", 0.0) or 0.0),
    )
    if execution_highlights:
        implementation_update = _clean_execution_clause(timeline_update_text)
    elif current_actions:
        implementation_update = _clean_execution_clause(current_actions[0])
    else:
        implementation_update = "Implementation setup is active and the next coded slice is being prepared"
    recent_highlights = [item for item in execution_highlights if item and item != implementation_update]
    highlight_clause = f"Recent highlights: {recent_highlights[0]}; " if recent_highlights else ""
    checklist_posture = _periodize(progress_story.capitalize()).rstrip(".")
    current_execution_line = (
        "Current execution: "
        f"Lane state: {label} is {status_phrase}; "
        f"Implementation update: {implementation_update}; "
        f"{highlight_clause}"
        f"Checklist posture: {checklist_posture}; "
        f"Timeline: {_timeline_clause(eta_days=eta_days, eta_source=eta_source, status=status, has_execution_signal=has_execution_signal)}."
    )

    next_tokens = _action_tokens_for_workstream(next_actions, idea_id, max_items=2)
    if next_tokens:
        if len(next_tokens) == 1:
            next_line = f"Next planned: complete {next_tokens[0]} and land it as merged delivery artifacts for {label}."
        else:
            next_line = (
                f"Next planned: complete {next_tokens[0]}, then {next_tokens[1]} to move {label} "
                "from planning into executable delivery."
            )
    else:
        next_line = f"Next planned: convert remaining {idea_id} plan items into merged implementation artifacts and close planning gaps."

    why_benefit_line = (
        f"Why this matters: {use_story or f'{idea_id} is a prerequisite lane for dependent platform execution.'} "
        f"Architecture consequence: {architecture_consequence or f'{idea_id} gives operators a clearer contract and lowers coordination risk across dependent workstreams.'}"
    )
    risk_line = f"Risks to watch: {_periodize(_risk_phrase(risk_posture))}"

    return [
        _normalize_sentence(completed_line),
        _normalize_sentence(current_execution_line),
        _normalize_sentence(next_line),
        _normalize_sentence(why_benefit_line),
        _normalize_sentence(risk_line),
    ]


def _build_outcome_digest_global(
    *,
    ws_rows: list[dict[str, Any]],
    ws_index: Mapping[str, Mapping[str, Any]],
    active_ws_rows: Sequence[Mapping[str, Any]],
    event_counts_by_ws: Mapping[str, int],
    next_actions: list[dict[str, str]],
    recent_completed: list[dict[str, str]],
    risks_summary: str,
    window_events: Sequence[Mapping[str, Any]],
    window_transactions: Sequence[Mapping[str, Any]],
    window_hours: int,
) -> list[str]:
    host = _host()
    _ws_why_context = host._ws_why_context
    _ws_label = host._ws_label
    _estimate_remaining_days = host._estimate_remaining_days
    _build_completed_group_lines = host._build_completed_group_lines
    _collect_window_execution_updates = host._collect_window_execution_updates
    _narrative_excerpt = host._narrative_excerpt
    _action_tokens_for_workstream = host._action_tokens_for_workstream
    _execution_status_phrase = host._execution_status_phrase
    _clean_execution_clause = host._clean_execution_clause
    _periodize = host._periodize
    _timeline_clause = host._timeline_clause
    _risk_phrase = host._risk_phrase
    _normalize_sentence = host._normalize_sentence

    focused = ws_rows[:2]
    focused_primary = focused[0] if focused else {}
    primary_why_context = _ws_why_context(focused_primary if isinstance(focused_primary, Mapping) else {})
    primary_purpose = primary_why_context.get("purpose", "")
    primary_benefit = primary_why_context.get("benefit", "")
    primary_use_story = primary_why_context.get("use_story", "") or primary_purpose
    primary_architecture_consequence = primary_why_context.get("architecture_consequence", "") or primary_benefit
    primary_label = _ws_label(focused_primary) if focused_primary else "current priority lane"
    primary_status = str(focused_primary.get("status", "")).strip() if isinstance(focused_primary, Mapping) else "unknown"
    eta_days, eta_source = _estimate_remaining_days(focused_primary if isinstance(focused_primary, Mapping) else {})

    active_ids = [
        str(row.get("idea_id", "")).strip()
        for row in active_ws_rows
        if str(row.get("idea_id", "")).strip()
    ]
    active_count = len(active_ids)

    completed_group_lines = _build_completed_group_lines(recent_completed, ws_index=ws_index)
    window_update_tokens = _collect_window_execution_updates(window_events, max_items=2)
    window_update_summaries = [str(row.get("summary", "")).strip() for row in window_update_tokens if str(row.get("summary", "")).strip()]
    transaction_updates = _collect_window_transaction_updates(window_transactions, max_items=2)
    transaction_update_summaries = [
        str(item.get("summary", "")).strip()
        for item in transaction_updates
        if str(item.get("summary", "")).strip()
    ]
    execution_highlights = list(dict.fromkeys(transaction_update_summaries + window_update_summaries))
    if completed_group_lines:
        completed_line = f"Completed in this window: {' | '.join(completed_group_lines)}."
        if execution_highlights:
            completed_line = completed_line.rstrip(".") + f" Execution highlights: {execution_highlights[0]}."
    elif execution_highlights:
        if len(execution_highlights) == 1:
            completed_line = (
                "Completed in this window: milestone closeout is still in progress, and implementation delivery moved forward with "
                f"{execution_highlights[0]}."
            )
        else:
            completed_line = (
                "Completed in this window: milestone closeout is still in progress, and implementation delivery moved forward with "
                f"{execution_highlights[0]}; {execution_highlights[1]}."
            )
    else:
        completed_line = f"Completed in this window: no milestone closeout was recorded in the last {window_hours}h."

    progress_summary = workstream_progress_runtime.summarize_active_progress(
        [row for row in active_ws_rows if isinstance(row, Mapping)]
    )
    progressed_count = int(progress_summary.get("tracked", 0) or 0) + int(progress_summary.get("closed", 0) or 0)
    active_untracked_count = int(progress_summary.get("active_untracked", 0) or 0)

    ranked_activity = sorted(
        [(ws_id, int(count)) for ws_id, count in event_counts_by_ws.items() if ws_id],
        key=lambda item: (-item[1], item[0]),
    )
    top_activity_labels: list[str] = []
    for ws_id, _count in ranked_activity[:2]:
        ws_row = ws_index.get(ws_id, {})
        top_activity_labels.append(_narrative_excerpt(_ws_label(ws_row) if ws_row else ws_id, max_sentences=1, max_chars=110))

    current_focus_actions = _action_tokens_for_workstream(
        next_actions,
        str(focused_primary.get("idea_id", "")).strip() if isinstance(focused_primary, Mapping) else "",
        max_items=1,
    )
    primary_progress_ratio = 0.0
    if isinstance(focused_primary, Mapping):
        plan_payload = focused_primary.get("plan", {})
        if isinstance(plan_payload, Mapping):
            primary_progress_ratio = float(plan_payload.get("progress_ratio", 0.0) or 0.0)
    has_execution_signal = bool(execution_highlights)
    status_phrase = _execution_status_phrase(
        status=primary_status,
        has_execution_signal=has_execution_signal,
        progress_ratio=primary_progress_ratio,
    )
    if execution_highlights:
        implementation_update = _clean_execution_clause(execution_highlights[0])
    elif current_focus_actions:
        implementation_update = _clean_execution_clause(current_focus_actions[0])
    else:
        implementation_update = "Implementation setup is active and the next coded slice is being prepared"
    secondary_highlights = [item for item in execution_highlights if item and item != implementation_update]
    highlight_clause = f"Recent highlights: {secondary_highlights[0]}; " if secondary_highlights else ""

    if active_count <= 0:
        base_update = "no active implementation lane is currently open for this scope"
    elif progressed_count <= 0:
        if active_untracked_count > 0:
            base_update = "active lanes are in implementation, but checklist progress is not yet captured"
        else:
            base_update = "active lanes are in planning setup and closure execution is starting"
    elif progressed_count >= active_count:
        base_update = "active lanes are translating plans into concrete implementation outcomes"
    else:
        if active_untracked_count > 0:
            base_update = "planning and implementation are running in parallel, and some implementation lanes still lack captured checklist progress"
        else:
            base_update = "planning and implementation are running in parallel across active lanes"

    if top_activity_labels:
        focus_scope = (
            top_activity_labels[0]
            if len(top_activity_labels) == 1
            else f"{top_activity_labels[0]} and {top_activity_labels[1]}"
        )
        focus_clause = f"Focus lanes: {focus_scope}"
    else:
        focus_clause = f"Portfolio posture: {_periodize(base_update).rstrip('.')}"
    current_execution_line = (
        "Current execution: "
        f"Lane state: {primary_label} is {status_phrase}; "
        f"Implementation update: {implementation_update}; "
        f"{highlight_clause}"
        f"Timeline: {_timeline_clause(eta_days=eta_days, eta_source=eta_source, status=primary_status, has_execution_signal=has_execution_signal)}; "
        f"{focus_clause}."
    )
    why_focus = _narrative_excerpt(
        primary_use_story or "focused execution remains prerequisite for dependent follow-on workstreams.",
        max_sentences=1,
        max_chars=280,
    )
    impact_focus = _narrative_excerpt(
        primary_architecture_consequence
        or "gives operators a clearer contract and lower coordination risk across dependent work.",
        max_sentences=1,
        max_chars=280,
    )
    why_benefit_line = f"Why this matters: {why_focus} Architecture consequence: {impact_focus}"

    action_tokens: list[str] = []
    for item in next_actions:
        action = _narrative_excerpt(str(item.get("action", "")).strip(), max_sentences=1, max_chars=180)
        action = action.rstrip(" .;")
        if not action:
            continue
        idea_id = str(item.get("idea_id", "")).strip()
        ws_row = ws_index.get(idea_id, {})
        label = _ws_label(ws_row) if ws_row else (idea_id or str(item.get("title", "")).strip() or "active workstream")
        label = _narrative_excerpt(label, max_sentences=1, max_chars=96)
        action_tokens.append(f"{label}: {action}")
        if len(action_tokens) >= 2:
            break
    if action_tokens:
        if len(action_tokens) == 1:
            next_line = f"Next planned: {action_tokens[0]}."
        else:
            next_line = f"Next planned: {action_tokens[0]}; then {action_tokens[1]}."
    else:
        next_line = "Next planned: prioritize remaining active-plan checklist items."
    risk_line = f"Risks to watch: {_periodize(_risk_phrase(risks_summary))}"

    return [
        _normalize_sentence(completed_line),
        _normalize_sentence(current_execution_line),
        _normalize_sentence(next_line),
        _normalize_sentence(why_benefit_line),
        _normalize_sentence(risk_line),
    ]
