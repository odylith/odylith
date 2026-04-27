"""Compass runtime payload, digest, and history builders.

This module owns the high-churn runtime shaping that used to live inside the
monolithic Compass renderer file. It deliberately imports the shared Compass
base helpers wholesale so the first decomposition slice can stay behavior
identical while the facade remains stable.
"""

from __future__ import annotations

import base64
import datetime as dt
import gzip
import json
import math
from pathlib import Path
import re
import shutil
from typing import Any, Mapping, Sequence

from odylith.runtime.governance import agent_governance_intelligence as governance
from odylith.runtime.surfaces import compass_briefing_support
from odylith.runtime.surfaces import compass_outcome_digest_runtime
from odylith.runtime.surfaces import compass_standup_fact_packets
from odylith.runtime.surfaces import compass_standup_brief_narrator
from odylith.runtime.surfaces import compass_self_host_runtime
from odylith.runtime.surfaces import compass_transaction_runtime
from odylith.runtime.surfaces import compass_execution_focus_runtime
from odylith.runtime.surfaces import compass_current_workstreams_runtime
from odylith.runtime.surfaces import compass_runtime_payload_runtime
from odylith.runtime.surfaces import compass_refresh_contract
from odylith.runtime.governance import execution_wave_view_model
from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import odylith_context_engine_store
from odylith.runtime.context_engine import odylith_runtime_surface_summary
from odylith.runtime.surfaces.compass_dashboard_base import *  # noqa: F401,F403


DEFAULT_HISTORY_RETENTION_DAYS = 15
_EMBEDDED_HISTORY_SNAPSHOT_ENCODING = "gzip+base64+json"
_COMPASS_RUNTIME_JS_ASSIGNMENT_PREFIX = "window.__ODYLITH_COMPASS_RUNTIME__ = "


def _global_brief_provider_allowed(
    *,
    repo_root: Path,
    fact_packet: Mapping[str, Any],
    window_hours: int,
    refresh_profile: str,
) -> bool:
    if not compass_refresh_contract.allow_global_provider(refresh_profile):
        return False
    return _global_brief_should_use_provider(
        repo_root=repo_root,
        fact_packet=fact_packet,
        window_hours=window_hours,
    )


def _global_brief_should_use_provider(
    *,
    repo_root: Path,
    fact_packet: Mapping[str, Any],
    window_hours: int,
) -> bool:
    del repo_root
    window_token = str(fact_packet.get("window", "")).strip().lower()
    if window_token in {"24h", "48h"}:
        return True
    return int(window_hours) in {24, 48}


def _timeline_event_priority(row: Mapping[str, Any]) -> int:
    kind = str(row.get("kind", "")).strip().lower()
    kind_score = {
        "implementation": 100,
        "decision": 95,
        "statement": 90,
        "plan_completion": 84,
        "plan_update": 80,
        "bug_resolved": 74,
        "bug_update": 70,
        "bug_watch": 66,
        "commit": 58,
        "local_change": 44,
    }.get(kind, 50)

    ws = [str(item).strip() for item in row.get("workstreams", []) if str(item).strip()]
    if ws:
        kind_score += 24

    files = [str(item).strip() for item in row.get("files", []) if str(item).strip()]
    source_files, generated_files = _split_source_vs_generated_files(files)
    if source_files:
        kind_score += min(12, len(source_files))
    if generated_files and not source_files:
        kind_score -= 36
    elif generated_files:
        kind_score -= 8
    return kind_score


def _select_timeline_source_events(
    *,
    events: Sequence[Mapping[str, Any]],
    now: dt.datetime,
    lookback_hours: int = _TIMELINE_EVENT_LOOKBACK_HOURS,
    max_rows: int = _TIMELINE_EVENT_MAX_ROWS,
) -> list[dict[str, Any]]:
    typed: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, Mapping):
            continue
        ts = event.get("ts")
        if not isinstance(ts, dt.datetime):
            continue
        typed.append(dict(event))

    if not typed:
        return []

    lookback = max(24, int(lookback_hours))
    cutoff = now - dt.timedelta(hours=lookback)
    recent = [row for row in typed if isinstance(row.get("ts"), dt.datetime) and row["ts"] >= cutoff]
    pool = recent if recent else typed

    ranked = sorted(
        pool,
        key=lambda row: (
            _timeline_event_priority(row),
            row.get("ts", now),
            str(row.get("id", "")).strip(),
        ),
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    generated_noise: list[dict[str, Any]] = []
    max_allowed = max(64, int(max_rows))
    for row in ranked:
        kind = str(row.get("kind", "")).strip().lower()
        files = [str(item).strip() for item in row.get("files", []) if str(item).strip()]
        source_files, generated_files = _split_source_vs_generated_files(files)
        generated_only_local = kind == "local_change" and not source_files and bool(generated_files)
        if generated_only_local:
            generated_noise.append(row)
            continue
        selected.append(row)
        if len(selected) >= max_allowed:
            break

    if len(selected) < max_allowed and generated_noise:
        dynamic_noise_budget = max(16, max_allowed // 4)
        noise_budget = min(
            _TIMELINE_GENERATED_NOISE_MAX_ROWS,
            dynamic_noise_budget,
            max_allowed - len(selected),
        )
        selected.extend(generated_noise[:noise_budget])

    selected.sort(
        key=lambda row: (
            row.get("ts", now),
            str(row.get("id", "")).strip(),
        ),
        reverse=True,
    )
    return selected


def _self_host_snapshot(*, repo_root: Path, refresh_profile: str = "shell-safe") -> dict[str, Any]:
    return compass_self_host_runtime.self_host_snapshot(
        repo_root=repo_root,
        prefer_cached=True,
    )


def _self_host_risk_rows(*, snapshot: Mapping[str, Any], local_date: str) -> list[dict[str, Any]]:
    return compass_self_host_runtime.self_host_risk_rows(snapshot=snapshot, local_date=local_date)


def _self_host_release_eligibility_label(value: object) -> str:
    return compass_self_host_runtime.self_host_release_eligibility_label(value)


def _self_host_status_fact(snapshot: Mapping[str, Any]) -> dict[str, Any] | None:
    return compass_self_host_runtime.self_host_status_fact(
        snapshot,
        standup_fact_builder=_standup_fact,
    )


def _transaction_scope_phrase(workstreams: Sequence[str]) -> str:
    return compass_transaction_runtime._transaction_scope_phrase(workstreams)


def _is_generated_narrative_file(path: str) -> bool:
    return compass_transaction_runtime._is_generated_narrative_file(path)


def _is_generated_narrative_token(token: str) -> bool:
    return compass_transaction_runtime._is_generated_narrative_token(token)


def _split_source_vs_generated_files_cached(files: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return compass_transaction_runtime._split_source_vs_generated_files_cached(files)


def _normalized_file_tuple(files: Sequence[str]) -> tuple[str, ...]:
    return compass_transaction_runtime._normalized_file_tuple(files)


def _split_source_vs_generated_files(files: Sequence[str]) -> tuple[list[str], list[str]]:
    return compass_transaction_runtime._split_source_vs_generated_files(files)


def _local_change_surface_label(path: str) -> str:
    return compass_transaction_runtime._local_change_surface_label(path)


def _is_generated_only_local_change_event(row: Mapping[str, Any]) -> bool:
    return compass_transaction_runtime._is_generated_only_local_change_event(row)


def _is_generated_only_transaction(row: Mapping[str, Any]) -> bool:
    return compass_transaction_runtime._is_generated_only_transaction(row)


def _local_change_headline_phrase(
    *,
    local_events: Sequence[Mapping[str, Any]],
    files_count: int,
) -> str:
    return compass_transaction_runtime._local_change_headline_phrase(
        local_events=local_events,
        files_count=files_count,
    )


def _is_generic_transaction_headline(text: str) -> bool:
    return compass_transaction_runtime._is_generic_transaction_headline(text)


def _select_transaction_headline_hint(tx_events: Sequence[Mapping[str, Any]]) -> str:
    return compass_transaction_runtime._select_transaction_headline_hint(tx_events)


def _plan_update_headline(*, summary: str, scope: str) -> str:
    return compass_transaction_runtime._plan_update_headline(summary=summary, scope=scope)


def _lineage_transaction_headline(*, summaries: Sequence[str], scope: str) -> str:
    return compass_transaction_runtime._lineage_transaction_headline(summaries=summaries, scope=scope)


def _build_transaction_headline(
    *,
    tx_events: Sequence[Mapping[str, Any]],
    tx_context: str,
    workstreams: Sequence[str],
    files_count: int,
) -> str:
    return compass_transaction_runtime._build_transaction_headline(
        tx_events=tx_events,
        tx_context=tx_context,
        workstreams=workstreams,
        files_count=files_count,
    )


def _is_transaction_support_file(path: str, *, repo_root: Path | None = None) -> bool:
    return compass_transaction_runtime._is_transaction_support_file(path, repo_root=repo_root)


def _transaction_shadow_facts(
    row: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    return compass_transaction_runtime._transaction_shadow_facts(row, repo_root=repo_root)


def _should_suppress_shadowed_auto_transaction_facts(
    candidate_facts: Mapping[str, Any],
    other_facts: Mapping[str, Any],
    *,
    proximity_minutes: int = 10,
) -> bool:
    return compass_transaction_runtime._should_suppress_shadowed_auto_transaction_facts(
        candidate_facts,
        other_facts,
        proximity_minutes=proximity_minutes,
    )


def _compact_shadowed_auto_transactions(
    payloads: Sequence[Mapping[str, Any]],
    *,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    return compass_transaction_runtime._compact_shadowed_auto_transactions(payloads, repo_root=repo_root)


def _build_prompt_transactions(
    *,
    events: Sequence[Mapping[str, Any]],
    inactivity_minutes: int = 2,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    return compass_transaction_runtime._build_prompt_transactions(
        events=events,
        inactivity_minutes=inactivity_minutes,
        repo_root=repo_root,
    )


def _build_execution_focus_payload(
    *,
    transactions: Sequence[Mapping[str, Any]],
    now: dt.datetime,
    active_window_minutes: int = _DEFAULT_ACTIVE_WINDOW_MINUTES,
    recent_window_minutes: int = _DEFAULT_RECENT_FOCUS_WINDOW_MINUTES,
) -> dict[str, Any]:
    return compass_execution_focus_runtime._build_execution_focus_payload(
        transactions=transactions,
        now=now,
        active_window_minutes=active_window_minutes,
        recent_window_minutes=recent_window_minutes,
    )


def _cost_base_index(*, sizing: str, complexity: str) -> int:
    size = _SIZE_SCORE.get(str(sizing or "").strip(), 3)
    comp = _COMPLEXITY_SCORE.get(str(complexity or "").strip(), 2)
    raw = (size * 10) + (comp * 8)
    min_raw = (_SIZE_SCORE["XS"] * 10) + (_COMPLEXITY_SCORE["Low"] * 8)
    max_raw = (_SIZE_SCORE["XL"] * 10) + (_COMPLEXITY_SCORE["VeryHigh"] * 8)
    if max_raw <= min_raw:
        return 50
    ratio = (raw - min_raw) / (max_raw - min_raw)
    return int(max(0, min(100, round(ratio * 100))))


def _cost_with_activity(base_index: int, *, commit_count: int, local_count: int) -> tuple[int, str]:
    intensity = min(1.0, ((commit_count * 2) + local_count) / 12.0)
    modifier = int(round(intensity * 20))
    score = int(max(0, min(100, base_index + modifier)))
    if score >= 70:
        band = "High"
    elif score >= 40:
        band = "Medium"
    else:
        band = "Low"
    return score, band


def _timeline_projection(*, age_days: int, total_tasks: int, done_tasks: int) -> tuple[int | None, str]:
    if total_tasks <= 0:
        return None, "low"
    if done_tasks <= 0:
        return None, "low"
    if done_tasks >= total_tasks:
        return 0, "high"
    if age_days < 2 or total_tasks < 3:
        return None, "low"

    throughput = done_tasks / max(age_days, 1)
    if throughput <= 0:
        return None, "low"
    remaining = max(0, total_tasks - done_tasks)
    eta = int(math.ceil(remaining / throughput))

    if total_tasks >= 10 and done_tasks >= 4:
        confidence = "high"
    elif total_tasks >= 5 and done_tasks >= 2:
        confidence = "medium"
    else:
        confidence = "low"
    return eta, confidence


def _collect_recent_completed_plan_rows(
    plan_index_path: Path,
    *,
    repo_root: Path,
    now: dt.datetime,
    hours: int,
) -> list[dict[str, str]]:
    content = _read_text(plan_index_path)
    rows: list[dict[str, str]] = []
    cutoff = now - dt.timedelta(hours=max(1, int(hours)))
    for line in content.splitlines():
        if not line.startswith("| `odylith/technical-plans/done/"):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) < 5:
            continue
        plan_token = cells[0].strip("`")
        status = cells[1]
        updated_token = cells[3]
        backlog_token = cells[4].strip("`")
        if not _WORKSTREAM_ID_RE.fullmatch(backlog_token):
            continue
        plan_path = _resolve(repo_root, plan_token)
        ts = _file_mtime(plan_path)
        if ts is None:
            updated_date = _parse_date(updated_token)
            if updated_date is None:
                continue
            # Plan index rows only carry dates; keep inclusion day-based so
            # completed-plan metrics remain stable across time-of-day.
            if not _is_bug_date_within_window(date_token=updated_date.isoformat(), now=now, hours=hours):
                continue
            ts = _date_midday_local(updated_date, tz=now.tzinfo)
        elif ts < cutoff:
            continue
        rows.append(
            {
                "plan": plan_token,
                "status": status,
                "updated": ts.date().isoformat(),
                "backlog": backlog_token,
            }
        )
    return rows


def _collect_recent_completed_plan_rows_for_timeline(
    plan_index_path: Path,
    *,
    repo_root: Path,
    now: dt.datetime,
    hours: int,
) -> list[dict[str, str]]:
    content = _read_text(plan_index_path)
    rows: list[dict[str, str]] = []
    cutoff = now - dt.timedelta(hours=max(1, int(hours)))
    for line in content.splitlines():
        if not line.startswith("| `odylith/technical-plans/done/"):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) < 5:
            continue
        plan_token = cells[0].strip("`")
        status = cells[1]
        updated_token = cells[3]
        backlog_token = cells[4].strip("`")
        plan_path = _resolve(repo_root, plan_token)
        ts = _file_mtime(plan_path)
        if ts is None:
            updated_date = _parse_date(updated_token)
            if updated_date is None:
                continue
            # Plan index rows only carry dates; keep inclusion day-based so
            # timeline completion events do not flap with local run time.
            if not _is_bug_date_within_window(date_token=updated_date.isoformat(), now=now, hours=hours):
                continue
            ts = _date_midday_local(updated_date, tz=now.tzinfo)
        elif ts < cutoff:
            continue
        rows.append(
            {
                "plan": plan_token,
                "status": status,
                "updated": ts.date().isoformat(),
                "backlog": backlog_token,
            }
        )
    return rows


def _collect_plan_checked_signals(plan_path: Path) -> tuple[list[str], list[str]]:
    decisions: list[str] = []
    completed_tasks: list[str] = []
    if not plan_path.is_file():
        return decisions, completed_tasks

    for raw in plan_path.read_text(encoding="utf-8").splitlines():
        match = _CHECKBOX_RE.match(raw)
        if match is None:
            continue
        if str(match.group("mark")).lower() != "x":
            continue
        body = " ".join(str(match.group("body")).split()).strip()
        if not body:
            continue
        lowered = body.lower()
        if lowered.startswith("risk:") or lowered.startswith("mitigation:"):
            continue
        if lowered.startswith("decision:"):
            decision = body.split(":", 1)[1].strip() if ":" in body else body
            if decision and decision not in decisions:
                decisions.append(decision)
            continue
        if body not in completed_tasks:
            completed_tasks.append(body)

    return decisions[:3], completed_tasks[:4]


_periodize = compass_briefing_support._periodize
_risk_phrase = compass_briefing_support._risk_phrase
_sentence_without_period = compass_briefing_support._sentence_without_period
_use_story_text = compass_briefing_support._use_story_text
_normalize_why_fragment = compass_briefing_support._normalize_why_fragment
_architecture_consequence_text = compass_briefing_support._architecture_consequence_text
_ws_why_context = compass_briefing_support._ws_why_context


def _ws_why_summary(row: Mapping[str, Any]) -> tuple[str, str]:
    return compass_briefing_support._ws_why_summary(row)


_ws_label = compass_briefing_support._ws_label
_plan_deliverable_label = compass_briefing_support._plan_deliverable_label


def _build_plan_timeline_events(
    *,
    repo_root: Path,
    now: dt.datetime,
    plan_index_path: Path,
    active_plan_rows: Sequence[Mapping[str, str]],
    ws_path_index: Mapping[str, set[str]],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for idx, row in enumerate(active_plan_rows, start=1):
        plan_token = str(row.get("Plan", "")).strip().strip("`")
        if not plan_token:
            continue
        plan_path = _resolve(repo_root, plan_token)
        ts = _file_mtime(plan_path)
        if ts is None:
            updated_date = _parse_date(str(row.get("Updated", "")).strip())
            if updated_date is None:
                continue
            ts = _date_midday_local(updated_date, tz=now.tzinfo)

        backlog_token = str(row.get("Backlog", "")).strip().strip("`")
        status_token = str(row.get("Status", "")).strip() or "In progress"
        deliverable = _plan_deliverable_label(plan_token) or Path(plan_token).name.replace(".md", "")

        ws_ids: list[str] = []
        if _WORKSTREAM_ID_RE.fullmatch(backlog_token):
            ws_ids.append(backlog_token)
        ws_ids.extend(_map_paths_to_workstreams([plan_token], ws_path_index))
        ws_ids = sorted({token for token in ws_ids if _WORKSTREAM_ID_RE.fullmatch(token)})
        ws_scope = ws_ids[0] if ws_ids else "unscoped"

        progress = _collect_plan_progress(plan_path)
        done_tasks = int(progress.get("done_tasks", 0) or 0)
        total_tasks = int(progress.get("total_tasks", 0) or 0)
        if total_tasks > 0:
            summary = (
                f"Plan updated: {deliverable} ({ws_scope}) is {status_token}; "
                f"checklist {done_tasks}/{total_tasks} complete."
            )
        else:
            summary = (
                f"Plan updated: {deliverable} ({ws_scope}) is {status_token}; "
                "checklist baseline is being finalized."
            )
        events.append(
            {
                "id": f"plan:update:{idx}:{plan_token}",
                "kind": "plan_update",
                "ts": ts,
                "ts_iso": _safe_iso(ts),
                "summary": _normalize_sentence(summary),
                "author": "plan",
                "sha": "",
                "files": [plan_token],
                "workstreams": ws_ids,
                "source": "plan_index",
            }
        )

        decisions, completed_tasks = _collect_plan_checked_signals(plan_path)
        if decisions:
            decision_summary = f"Decision captured in {deliverable}: {decisions[0]}."
            events.append(
                {
                    "id": f"plan:decision:{idx}:{plan_token}",
                    "kind": "decision",
                    "ts": ts,
                    "ts_iso": _safe_iso(ts),
                    "summary": _normalize_sentence(decision_summary),
                    "author": "plan",
                    "sha": "",
                    "files": [plan_token],
                    "workstreams": ws_ids,
                    "source": "plan_file",
                }
            )
        if completed_tasks:
            impl_summary = f"Implementation checkpoint in {deliverable}: completed {completed_tasks[0]}."
            events.append(
                {
                    "id": f"plan:implementation:{idx}:{plan_token}",
                    "kind": "implementation",
                    "ts": ts,
                    "ts_iso": _safe_iso(ts),
                    "summary": _normalize_sentence(impl_summary),
                    "author": "plan",
                    "sha": "",
                    "files": [plan_token],
                    "workstreams": ws_ids,
                    "source": "plan_file",
                }
            )

    completed_rows = _collect_recent_completed_plan_rows_for_timeline(
        plan_index_path=plan_index_path,
        repo_root=repo_root,
        now=now,
        hours=48,
    )
    for idx, row in enumerate(completed_rows, start=1):
        plan_token = str(row.get("plan", "")).strip()
        if not plan_token:
            continue
        plan_path = _resolve(repo_root, plan_token)
        ts = _file_mtime(plan_path)
        if ts is None:
            updated_date = _parse_date(str(row.get("updated", "")).strip())
            if updated_date is None:
                continue
            ts = _date_midday_local(updated_date, tz=now.tzinfo)

        backlog_token = str(row.get("backlog", "")).strip()
        ws_ids: list[str] = []
        if _WORKSTREAM_ID_RE.fullmatch(backlog_token):
            ws_ids.append(backlog_token)
        ws_ids.extend(_map_paths_to_workstreams([plan_token], ws_path_index))
        ws_ids = sorted({token for token in ws_ids if _WORKSTREAM_ID_RE.fullmatch(token)})

        deliverable = _plan_deliverable_label(plan_token) or Path(plan_token).name.replace(".md", "")
        if ws_ids:
            summary = f"Plan milestone completed: {deliverable} closed for {ws_ids[0]}."
        else:
            summary = f"Plan milestone completed: {deliverable} closed."
        events.append(
            {
                "id": f"plan:complete:{idx}:{plan_token}",
                "kind": "plan_completion",
                "ts": ts,
                "ts_iso": _safe_iso(ts),
                "summary": _normalize_sentence(summary),
                "author": "plan",
                "sha": "",
                "files": [plan_token],
                "workstreams": ws_ids,
                "source": "plan_index",
            }
        )

    return events


def _build_bug_timeline_events(
    *,
    repo_root: Path,
    now: dt.datetime,
    bugs_index_path: Path,
    bug_rows: Sequence[Mapping[str, str]],
    ws_path_index: Mapping[str, set[str]],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    cutoff = now - dt.timedelta(hours=48)

    for idx, row in enumerate(bug_rows, start=1):
        severity = str(row.get("Severity", "")).strip().upper()
        if severity not in {"P0", "P1", "P2", "P3"}:
            continue
        status = str(row.get("Status", "")).strip()
        title = " ".join(str(row.get("Title", "")).split()).strip() or "Untitled bug"

        link_path = _resolve_index_link_to_repo_path(
            repo_root=repo_root,
            index_path=bugs_index_path,
            markdown_link=str(row.get("Link", "")),
        )
        bug_path = _resolve(repo_root, link_path) if link_path else None
        ts = _file_mtime(bug_path) if bug_path is not None else None
        if ts is None:
            date_token = _parse_date(str(row.get("Date", "")).strip())
            if date_token is not None:
                ts = _date_midday_local(date_token, tz=now.tzinfo)
            else:
                ts = now

        ws_ids: list[str] = []
        ws_ids.extend(_extract_workstream_tokens_from_text(title))
        if link_path:
            ws_ids.extend(_map_paths_to_workstreams([link_path], ws_path_index))
        ws_ids = sorted({token for token in ws_ids if _WORKSTREAM_ID_RE.fullmatch(token)})

        files = [link_path] if link_path else []
        status_lower = status.lower()
        is_resolved = status_lower in {"fixed", "closed"}
        is_critical = severity in {"P0", "P1"}

        if is_critical and not is_resolved:
            summary = f"Critical bug remains open ({severity}): {title}."
            events.append(
                {
                    "id": f"bug:watch:{idx}:{severity}",
                    "kind": "bug_watch",
                    "ts": ts,
                    "ts_iso": _safe_iso(ts),
                    "summary": _normalize_sentence(summary),
                    "author": "bugs",
                    "sha": "",
                    "files": files,
                    "workstreams": ws_ids,
                    "source": "bugs_index",
                }
            )
            continue

        if ts < cutoff:
            continue

        if is_critical and is_resolved:
            kind = "bug_resolved"
            summary = f"Critical bug resolved ({severity}): {title}."
        else:
            kind = "bug_update"
            summary = f"Bug status update ({severity}, {status or 'Unknown'}): {title}."
        events.append(
            {
                "id": f"bug:{kind}:{idx}:{severity}",
                "kind": kind,
                "ts": ts,
                "ts_iso": _safe_iso(ts),
                "summary": _normalize_sentence(summary),
                "author": "bugs",
                "sha": "",
                "files": files,
                "workstreams": ws_ids,
                "source": "bugs_index",
            }
        )

    return events


_estimate_remaining_days = compass_briefing_support._estimate_remaining_days
_build_completed_group_lines = compass_briefing_support._build_completed_group_lines
_action_tokens_for_workstream = compass_briefing_support._action_tokens_for_workstream


def _build_window_event_counts(
    window_events: Sequence[Mapping[str, Any]],
    *,
    max_workstream_fanout: int = 4,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in window_events:
        ws_tokens = sorted(
            {
                str(token).strip()
                for token in event.get("workstreams", [])
                if str(token).strip()
            }
        )
        if not ws_tokens:
            continue
        if len(ws_tokens) > max_workstream_fanout:
            continue
        for ws_id in ws_tokens:
            counts[ws_id] = counts.get(ws_id, 0) + 1

    if counts:
        return counts

    # Fallback: if every event is high-fanout, keep a conservative signal instead of going empty.
    fallback: dict[str, int] = {}
    for event in window_events:
        ws_tokens = {
            str(token).strip()
            for token in event.get("workstreams", [])
            if str(token).strip()
        }
        for ws_id in ws_tokens:
            fallback[ws_id] = fallback.get(ws_id, 0) + 1
    return fallback


_sanitize_digest_summary = compass_briefing_support._sanitize_digest_summary
_looks_generic_churn_summary = compass_briefing_support._looks_generic_churn_summary
_surface_signal_score = compass_briefing_support._surface_signal_score
_narrative_signal_score = compass_briefing_support._narrative_signal_score
_ordered_update_candidates = compass_briefing_support._ordered_update_candidates
_is_synthetic_plan_execution_signal = compass_briefing_support._is_synthetic_plan_execution_signal
_collect_window_execution_updates = compass_briefing_support._collect_window_execution_updates
_transaction_end_ts = compass_transaction_runtime._transaction_end_ts


def _filter_transactions_by_window(
    transactions: Sequence[Mapping[str, Any]],
    *,
    now: dt.datetime,
    hours: int,
) -> list[dict[str, Any]]:
    cutoff = now - dt.timedelta(hours=max(1, int(hours)))
    selected: list[dict[str, Any]] = []
    for row in transactions:
        if not isinstance(row, Mapping):
            continue
        ts = _transaction_end_ts(row)
        if ts is None or ts < cutoff:
            continue
        selected.append(dict(row))
    selected.sort(
        key=lambda row: (
            _transaction_end_ts(row) or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
            str(row.get("id", "")).strip(),
        ),
        reverse=True,
    )
    return selected


def _collect_window_transaction_updates(
    window_transactions: Sequence[Mapping[str, Any]],
    *,
    ws_id: str | None = None,
    max_items: int = 2,
    max_workstream_fanout: int = 16,
) -> list[dict[str, str]]:
    return compass_outcome_digest_runtime._collect_window_transaction_updates(
        window_transactions,
        ws_id=ws_id,
        max_items=max_items,
        max_workstream_fanout=max_workstream_fanout,
    )


_progress_story = compass_briefing_support._progress_story
_execution_status_phrase = compass_briefing_support._execution_status_phrase
_clean_execution_clause = compass_briefing_support._clean_execution_clause
_normalize_action_task = compass_briefing_support._normalize_action_task
_action_clause_for_narrative = compass_briefing_support._action_clause_for_narrative
_timeline_clause = compass_briefing_support._timeline_clause


def _build_outcome_digest_for_workstream(
    *,
    row: Mapping[str, Any],
    next_actions: list[dict[str, str]],
    recent_completed: list[dict[str, str]],
    window_events: Sequence[Mapping[str, Any]],
    window_transactions: Sequence[Mapping[str, Any]],
    risk_posture: str,
) -> list[str]:
    return compass_outcome_digest_runtime._build_outcome_digest_for_workstream(
        row=row,
        next_actions=next_actions,
        recent_completed=recent_completed,
        window_events=window_events,
        window_transactions=window_transactions,
        risk_posture=risk_posture,
    )


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
    return compass_outcome_digest_runtime._build_outcome_digest_global(
        ws_rows=ws_rows,
        ws_index=ws_index,
        active_ws_rows=active_ws_rows,
        event_counts_by_ws=event_counts_by_ws,
        next_actions=next_actions,
        recent_completed=recent_completed,
        risks_summary=risks_summary,
        window_events=window_events,
        window_transactions=window_transactions,
        window_hours=window_hours,
    )


def _build_risk_posture_summary(
    *,
    open_critical: int,
    traceability_risks: Sequence[Mapping[str, Any]],
    stale_diagrams: Sequence[Mapping[str, Any]],
) -> str:
    flags: list[str] = []
    if open_critical > 0:
        flags.append("critical bugs require immediate containment")
    if len(traceability_risks) > 0:
        flags.append("traceability warnings need cleanup")
    if len(stale_diagrams) > 0:
        flags.append("diagram reviews are stale")
    if not flags:
        return "Risk posture: no critical blockers are currently surfaced."
    if len(flags) == 1:
        return f"Risk posture: {flags[0]}."
    return f"Risk posture: {'; '.join(flags)}."


_decapitalize_clause = compass_briefing_support._decapitalize_clause
_standup_fact = compass_briefing_support._standup_fact
_finalize_standup_fact_packet = compass_briefing_support._finalize_standup_fact_packet
_wave_context_summary = compass_briefing_support._wave_context_summary
_lineage_context_summary = compass_briefing_support._lineage_context_summary
_forcing_function_text = compass_briefing_support._forcing_function_text
_follow_on_text = compass_briefing_support._follow_on_text
_scope_risk_rows = compass_briefing_support._scope_risk_rows
_risk_facts = compass_briefing_support._risk_facts
_wave_context_clause = compass_briefing_support._wave_context_clause
_latest_window_activity_iso = compass_briefing_support._latest_window_activity_iso
_matches_freshness_scope = compass_briefing_support._matches_freshness_scope
_latest_evidence_marker = compass_briefing_support._latest_evidence_marker
_freshness_bucket = compass_briefing_support._freshness_bucket
_freshness_age_label = compass_briefing_support._freshness_age_label
_freshness_fact_text = compass_briefing_support._freshness_fact_text
_scoped_fallback_next_text = compass_briefing_support._scoped_fallback_next_text
_global_fallback_next_text = compass_briefing_support._global_fallback_next_text
_scoped_fallback_risk_text = compass_briefing_support._scoped_fallback_risk_text
_global_fallback_risk_text = compass_briefing_support._global_fallback_risk_text


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
    return compass_standup_fact_packets._build_scoped_standup_fact_packet(
        row=row,
        next_actions=next_actions,
        recent_completed=recent_completed,
        window_events=window_events,
        window_transactions=window_transactions,
        execution_updates=execution_updates,
        transaction_updates=transaction_updates,
        window_hours=window_hours,
        risk_rows=risk_rows,
        risk_summary=risk_summary,
        self_host_snapshot=self_host_snapshot,
        now=now,
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
    return compass_standup_fact_packets._build_global_standup_fact_packet(
        ws_rows=ws_rows,
        ws_index=ws_index,
        active_ws_rows=active_ws_rows,
        event_counts_by_ws=event_counts_by_ws,
        next_actions=next_actions,
        recent_completed=recent_completed,
        window_events=window_events,
        window_transactions=window_transactions,
        execution_updates=execution_updates,
        transaction_updates=transaction_updates,
        window_hours=window_hours,
        risk_rows=risk_rows,
        risk_summary=risk_summary,
        kpis=kpis,
        self_host_snapshot=self_host_snapshot,
        self_host_risks=self_host_risks,
        now=now,
    )


def _select_current_workstream_rows(
    *,
    all_rows: Sequence[Mapping[str, Any]],
    window_events: Sequence[Mapping[str, Any]] | None = None,
    recent_completed_rows: Sequence[Mapping[str, str]] | None = None,
    window_events_48h: Sequence[Mapping[str, Any]] | None = None,
    recent_completed_rows_48h: Sequence[Mapping[str, str]] | None = None,
) -> list[dict[str, Any]]:
    selected_window_events = list(window_events) if window_events is not None else list(window_events_48h or [])
    selected_recent_completed = (
        list(recent_completed_rows)
        if recent_completed_rows is not None
        else list(recent_completed_rows_48h or [])
    )
    return compass_current_workstreams_runtime.select_current_workstream_rows(
        all_rows=all_rows,
        window_events=selected_window_events,
        recent_completed_rows=selected_recent_completed,
    )


def _execution_wave_program_member_ids(program: Mapping[str, Any]) -> set[str]:
    """Collect all member workstream ids referenced by one execution-wave program."""

    member_ids: set[str] = set()
    for wave in program.get("waves", []):
        if not isinstance(wave, Mapping):
            continue
        for member in wave.get("all_workstreams", []):
            if not isinstance(member, Mapping):
                continue
            token = str(member.get("idea_id", "")).strip()
            if token:
                member_ids.add(token)
    return member_ids


def _is_fully_closed_execution_wave_program(program: Mapping[str, Any]) -> bool:
    """Return whether a program is fully closed and therefore optional in Compass."""

    umbrella_status = str(program.get("umbrella_status", "")).strip().lower()
    terminal_umbrella = umbrella_status in {"finished", "parked", "superseded"}
    waves = [wave for wave in program.get("waves", []) if isinstance(wave, Mapping)]
    if not terminal_umbrella or not waves:
        return False
    return all(str(wave.get("status", "")).strip().lower() == "complete" for wave in waves)


def _filter_execution_wave_payload_for_current_context(
    *,
    payload: Mapping[str, Any],
    current_workstream_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bound Compass execution-wave programs to live context while keeping a catalog."""

    programs = [row for row in payload.get("programs", []) if isinstance(row, Mapping)]
    workstreams = payload.get("workstreams", {})
    if not isinstance(workstreams, Mapping):
        workstreams = {}

    live_ids = {
        str(row.get("idea_id", "")).strip()
        for row in current_workstream_rows
        if isinstance(row, Mapping) and str(row.get("idea_id", "")).strip()
    }
    filtered_programs: list[Mapping[str, Any]] = []
    for program in programs:
        if not _is_fully_closed_execution_wave_program(program):
            filtered_programs.append(program)
            continue
        umbrella_id = str(program.get("umbrella_id", "")).strip()
        member_ids = _execution_wave_program_member_ids(program)
        if umbrella_id in live_ids or member_ids.intersection(live_ids):
            filtered_programs.append(program)

    return {
        "summary": {
            "program_count": len(filtered_programs),
            "catalog_program_count": len(programs),
            "wave_count": sum(int(row.get("wave_count", 0) or 0) for row in filtered_programs),
            "active_wave_count": sum(int(row.get("active_wave_count", 0) or 0) for row in filtered_programs),
            "blocked_wave_count": sum(int(row.get("blocked_wave_count", 0) or 0) for row in filtered_programs),
            "workstream_count": len(workstreams),
        },
        "programs": list(filtered_programs),
        "program_catalog": list(programs),
        "workstreams": dict(workstreams),
    }


def _is_bug_date_within_window(*, date_token: str, now: dt.datetime, hours: int) -> bool:
    """Return whether a bug index row should count in a rolling window KPI.

    Bug rows only carry a calendar date (no timestamp), so this uses day-level
    inclusion anchored to the current Compass timezone date window.
    """

    raw = str(date_token).strip()
    if not raw:
        return True
    parsed = _parse_date(raw)
    if parsed is None:
        return True
    window_start_date = (now - dt.timedelta(hours=max(1, int(hours)))).date()
    window_end_date = now.date()
    return window_start_date <= parsed <= window_end_date


def _compact_odylith_runtime_summary(*, repo_root: Path) -> dict[str, Any]:
    """Return a bounded Odylith runtime posture summary for Compass."""
    return odylith_runtime_surface_summary.load_runtime_surface_summary(repo_root=repo_root)


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
    return compass_runtime_payload_runtime._build_runtime_payload(
        repo_root=repo_root,
        backlog_index_path=backlog_index_path,
        plan_index_path=plan_index_path,
        bugs_index_path=bugs_index_path,
        traceability_graph_path=traceability_graph_path,
        mermaid_catalog_path=mermaid_catalog_path,
        codex_stream_path=codex_stream_path,
        max_review_age_days=max_review_age_days,
        active_window_minutes=active_window_minutes,
        runtime_mode=runtime_mode,
        refresh_profile=refresh_profile,
        progress_callback=progress_callback,
    )


def _prune_history(history_dir: Path, *, retention_days: int, today: dt.date) -> list[str]:
    history_dir.mkdir(parents=True, exist_ok=True)
    kept: list[str] = []
    for path in sorted(history_dir.glob("*.v1.json")):
        if path.name == "index.v1.json":
            continue
        token = path.name.replace(".v1.json", "")
        date = _parse_date(token)
        if date is None:
            continue
        age = (today - date).days
        if age > retention_days:
            path.unlink(missing_ok=True)
            continue
        kept.append(date.isoformat())
    kept.sort(reverse=True)
    return kept


def _history_archive_dir(history_dir: Path) -> Path:
    return history_dir / "archive"


def _history_restore_pins_path(history_dir: Path) -> Path:
    return history_dir / "restore-pins.v1.json"


def _load_json_assignment(path: Path, *, prefix: str) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if not raw.startswith(prefix):
        return None
    payload_text = raw[len(prefix) :].strip()
    if payload_text.endswith(";"):
        payload_text = payload_text[:-1].strip()
    if not payload_text:
        return None
    try:
        payload = json.loads(payload_text)
    except Exception:
        return None
    return dict(payload) if isinstance(payload, Mapping) else None


def _load_current_runtime_payload(runtime_dir: Path) -> dict[str, Any] | None:
    current_json_path = runtime_dir / "current.v1.json"
    if current_json_path.is_file():
        try:
            payload = _load_json(current_json_path)
        except Exception:
            payload = None
        if isinstance(payload, Mapping):
            return dict(payload)
    return _load_json_assignment(
        runtime_dir / "current.v1.js",
        prefix=_COMPASS_RUNTIME_JS_ASSIGNMENT_PREFIX,
    )


def _clear_legacy_history_archive(*, history_dir: Path) -> tuple[Path, ...]:
    removed: list[Path] = []
    pins_path = _history_restore_pins_path(history_dir)
    if pins_path.is_file() or pins_path.is_symlink():
        pins_path.unlink()
        removed.append(pins_path)
    archive_dir = _history_archive_dir(history_dir)
    if archive_dir.is_dir() and not archive_dir.is_symlink():
        shutil.rmtree(archive_dir)
        removed.append(archive_dir)
    elif archive_dir.is_file() or archive_dir.is_symlink():
        archive_dir.unlink()
        removed.append(archive_dir)
    return tuple(removed)


def _empty_history_archive_meta() -> dict[str, Any]:
    return {
        "compressed": False,
        "path": "",
        "count": 0,
        "dates": [],
        "newest_date": "",
        "oldest_date": "",
    }


def _normalize_history_date_tokens(values: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = str(raw or "").strip()
        if not token:
            continue
        parsed = _parse_date(token)
        if parsed is None or parsed.isoformat() != token:
            raise ValueError(f"invalid Compass history date: {raw}")
        if token in seen:
            continue
        seen.add(token)
        normalized.append(token)
    normalized.sort(reverse=True)
    return normalized


def _history_archive_meta(history_dir: Path) -> dict[str, Any]:
    del history_dir
    return _empty_history_archive_meta()


def load_history_retention_days(*, runtime_dir: Path) -> int:
    history_dir = runtime_dir / "history"
    index_path = history_dir / "index.v1.json"
    if index_path.is_file():
        try:
            payload = _load_json(index_path)
        except Exception:
            payload = None
        history = payload if isinstance(payload, Mapping) else None
        if isinstance(history, Mapping):
            value = history.get("retention_days")
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                parsed = 0
            if parsed >= 1:
                return parsed

    payload = _load_current_runtime_payload(runtime_dir)
    history = payload.get("history") if isinstance(payload, Mapping) else None
    if isinstance(history, Mapping):
        value = history.get("retention_days")
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = 0
        if parsed >= 1:
            return parsed
    return DEFAULT_HISTORY_RETENTION_DAYS


def restore_archived_history_dates(
    *,
    repo_root: Path,
    runtime_dir: Path,
    dates: Sequence[str],
) -> tuple[list[str], list[str], Path]:
    del repo_root, runtime_dir, dates
    raise ValueError(
        "Compass history beyond retention is deleted instead of archived; restore-history is no longer available"
    )


def migrate_legacy_history_layout(*, repo_root: Path, runtime_dir: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    resolved_runtime_dir = Path(runtime_dir).resolve()
    history_dir = resolved_runtime_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    removed_paths = []
    for path in _clear_legacy_history_archive(history_dir=history_dir):
        try:
            removed_paths.append(str(path.relative_to(root)))
        except ValueError:
            removed_paths.append(str(path))

    retention_days = load_history_retention_days(runtime_dir=resolved_runtime_dir)
    payload = _load_current_runtime_payload(resolved_runtime_dir)
    rewritten = False
    kept_dates: list[str] = []
    if isinstance(payload, Mapping):
        _write_runtime_snapshots(
            repo_root=root,
            runtime_dir=resolved_runtime_dir,
            payload=dict(payload),
            retention_days=retention_days,
        )
        rewritten = True
        kept_dates = list(
            (_load_json(history_dir / "index.v1.json").get("dates", []))
            if (history_dir / "index.v1.json").is_file()
            else []
        )

    if not rewritten:
        today = dt.datetime.now(tz=_COMPASS_TZ).date()
        kept_dates = _prune_history(history_dir, retention_days=retention_days, today=today)
        index_payload = {
            "version": "v1",
            "generated_utc": "",
            "retention_days": retention_days,
            "dates": kept_dates,
            "restored_dates": [],
            "archive": _empty_history_archive_meta(),
        }
        index_path = history_dir / "index.v1.json"
        if index_path.is_file():
            try:
                existing_index = _load_json(index_path)
            except Exception:
                existing_index = {}
            index_payload["generated_utc"] = str(existing_index.get("generated_utc", "")).strip()
        odylith_context_cache.write_text_if_changed(
            repo_root=root,
            path=index_path,
            content=json.dumps(index_payload, indent=2) + "\n",
            lock_key=str(index_path),
        )
        history_js_path = history_dir / "embedded.v1.js"
        if kept_dates or history_js_path.is_file():
            embedded_history_payload = _build_embedded_history_payload(
                history_dir=history_dir,
                kept_dates=kept_dates,
                history_meta=index_payload,
            )
            odylith_context_cache.write_text_if_changed(
                repo_root=root,
                path=history_js_path,
                content="window.__ODYLITH_COMPASS_HISTORY__ = "
                + json.dumps(embedded_history_payload, separators=(",", ":"))
                + ";\n",
                lock_key=str(history_js_path),
            )
        return {
            "removed_paths": removed_paths,
            "retention_days": retention_days,
            "kept_dates": kept_dates,
            "rewritten": rewritten,
        }

    return {
        "removed_paths": removed_paths,
        "retention_days": retention_days,
        "kept_dates": kept_dates,
        "rewritten": rewritten,
    }


def _build_embedded_history_payload(
    *,
    history_dir: Path,
    kept_dates: Sequence[str],
    history_meta: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the local-file-safe retained history map used by Compass HTML.

    Browsers routinely block `fetch()` against sibling `file:` JSON resources, but they
    still permit static `<script src>` loading for local JS files. Compass therefore
    publishes a generated history JS bundle that mirrors retained daily snapshots and
    normalizes each embedded payload onto the current retained-history metadata so the
    calendar controls remain stable while switching between past days.
    """

    def _encode_snapshot(snapshot: Mapping[str, Any]) -> dict[str, str]:
        raw = json.dumps(snapshot, separators=(",", ":")).encode("utf-8")
        compressed = gzip.compress(raw, compresslevel=9)
        return {
            "encoding": _EMBEDDED_HISTORY_SNAPSHOT_ENCODING,
            "payload": base64.b64encode(compressed).decode("ascii"),
        }

    snapshots: dict[str, Any] = {}
    for token in _normalize_history_date_tokens([str(item) for item in kept_dates]):
        path = history_dir / f"{token}.v1.json"
        try:
            if not path.is_file():
                continue
            snapshot = _load_json(path)
        except Exception:
            continue
        snapshot_history = snapshot.get("history")
        if isinstance(snapshot_history, Mapping):
            merged_history = dict(snapshot_history)
        else:
            merged_history = {}
        merged_history["retention_days"] = int(history_meta.get("retention_days", 0) or 0)
        merged_history["dates"] = list(history_meta.get("dates", [])) if isinstance(history_meta.get("dates"), list) else []
        merged_history["restored_dates"] = (
            list(history_meta.get("restored_dates", []))
            if isinstance(history_meta.get("restored_dates"), list)
            else []
        )
        merged_history["archive"] = _empty_history_archive_meta()
        snapshot["history"] = merged_history
        snapshots[token] = _encode_snapshot(snapshot)
    return {
        "version": "v1",
        "generated_utc": str(history_meta.get("generated_utc", "")).strip(),
        "retention_days": int(history_meta.get("retention_days", 0) or 0),
        "dates": list(history_meta.get("dates", [])) if isinstance(history_meta.get("dates"), list) else [],
        "restored_dates": (
            list(history_meta.get("restored_dates", []))
            if isinstance(history_meta.get("restored_dates"), list)
            else []
        ),
        "archive": _empty_history_archive_meta(),
        "snapshots": snapshots,
    }


def _write_runtime_snapshots(
    *,
    repo_root: Path,
    runtime_dir: Path,
    payload: dict[str, Any],
    retention_days: int,
) -> tuple[Path, Path, Path, Path, Path]:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    history_dir = runtime_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_js_path = history_dir / "embedded.v1.js"

    today = dt.datetime.now(tz=_COMPASS_TZ).date()
    daily_path = history_dir / f"{today.isoformat()}.v1.json"
    current_json_path = runtime_dir / "current.v1.json"
    current_js_path = runtime_dir / "current.v1.js"

    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=current_json_path,
        content=json.dumps(payload, indent=2) + "\n",
        lock_key=str(current_json_path),
    )
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=current_js_path,
        content="window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        lock_key=str(current_js_path),
    )
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=daily_path,
        content=json.dumps(payload, indent=2) + "\n",
        lock_key=str(daily_path),
    )

    _clear_legacy_history_archive(history_dir=history_dir)
    kept_dates = _prune_history(history_dir, retention_days=retention_days, today=today)
    active_restored_dates: list[str] = []
    archive_meta = _history_archive_meta(history_dir)
    index_payload = {
        "version": "v1",
        "generated_utc": payload.get("generated_utc", ""),
        "retention_days": retention_days,
        "dates": kept_dates,
        "restored_dates": active_restored_dates,
        "archive": archive_meta,
    }
    index_path = history_dir / "index.v1.json"
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=index_path,
        content=json.dumps(index_payload, indent=2) + "\n",
        lock_key=str(index_path),
    )

    history = payload.get("history")
    if isinstance(history, dict):
        history["retention_days"] = retention_days
        history["dates"] = kept_dates
        history["restored_dates"] = active_restored_dates
        history["archive"] = archive_meta
        odylith_context_cache.write_text_if_changed(
            repo_root=repo_root,
            path=current_json_path,
            content=json.dumps(payload, indent=2) + "\n",
            lock_key=str(current_json_path),
        )
        odylith_context_cache.write_text_if_changed(
            repo_root=repo_root,
            path=current_js_path,
            content="window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
            lock_key=str(current_js_path),
        )
        odylith_context_cache.write_text_if_changed(
            repo_root=repo_root,
            path=daily_path,
            content=json.dumps(payload, indent=2) + "\n",
            lock_key=str(daily_path),
        )

    embedded_history_payload = _build_embedded_history_payload(
        history_dir=history_dir,
        kept_dates=kept_dates,
        history_meta=index_payload,
    )
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=history_js_path,
        content="window.__ODYLITH_COMPASS_HISTORY__ = " + json.dumps(embedded_history_payload, separators=(",", ":")) + ";\n",
        lock_key=str(history_js_path),
    )

    return current_json_path, current_js_path, daily_path, index_path, history_js_path


__all__ = [
    name
    for name in globals()
    if name.startswith('_') and name not in {'__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__spec__'}
]
