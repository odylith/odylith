"""Precomputed window-update indexes for Compass standup hot paths."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.surfaces import compass_briefing_support
from odylith.runtime.surfaces import compass_dashboard_base as compass_base
from odylith.runtime.surfaces import compass_transaction_runtime


def _finalize_candidate_buckets(
    *,
    primary: Sequence[Mapping[str, Any]],
    secondary: Sequence[Mapping[str, Any]],
    max_items: int,
) -> list[dict[str, str]]:
    updates: list[dict[str, str]] = []
    for bucket in (
        compass_briefing_support._ordered_update_candidates(primary),
        compass_briefing_support._ordered_update_candidates(secondary),
    ):
        for candidate in bucket:
            updates.append(
                {
                    "kind": str(candidate.get("kind", "")).strip(),
                    "summary": str(candidate.get("summary", "")).strip(),
                }
            )
            if len(updates) >= max_items:
                return updates
    return updates


def build_execution_update_index(
    window_events: Sequence[Mapping[str, Any]],
    *,
    max_items: int = 3,
    max_workstream_fanout: int = 4,
) -> dict[str, Any]:
    allowed = {
        "statement",
        "implementation",
        "decision",
        "plan_completion",
        "commit",
        "plan_update",
    }
    global_primary: list[dict[str, Any]] = []
    global_secondary: list[dict[str, Any]] = []
    global_seen: set[str] = set()
    scoped_primary: dict[str, list[dict[str, Any]]] = defaultdict(list)
    scoped_secondary: dict[str, list[dict[str, Any]]] = defaultdict(list)
    scoped_seen: dict[str, set[str]] = defaultdict(set)

    for event in window_events:
        kind = str(event.get("kind", "")).strip()
        if kind not in allowed:
            continue
        ws_tokens = tuple(
            str(token).strip()
            for token in event.get("workstreams", [])
            if str(token).strip()
        )
        strict_signal_kind = kind in {"statement", "implementation", "decision"}
        if max_workstream_fanout > 0 and len(ws_tokens) > max_workstream_fanout and not strict_signal_kind:
            continue
        summary = compass_base._humanize_execution_event_summary(
            kind=kind,
            summary=str(event.get("summary", "")).strip(),
        )
        normalized_summary = compass_briefing_support._sanitize_digest_summary(summary)
        if not normalized_summary or compass_briefing_support._looks_generic_churn_summary(normalized_summary):
            continue
        if normalized_summary.lower() in {"execution update", "updated code"}:
            continue
        ts = event.get("ts")
        sort_ts = ts.timestamp() if isinstance(ts, dt.datetime) else 0.0
        candidate = {
            "kind": kind,
            "summary": normalized_summary,
            "_score": compass_briefing_support._narrative_signal_score(
                normalized_summary,
                files=[str(item) for item in event.get("files", []) if str(item).strip()],
            ),
            "_sort_ts": sort_ts,
        }
        primary_bucket = kind in {"statement", "implementation", "decision", "commit"} and not compass_briefing_support._is_synthetic_plan_execution_signal(
            kind=kind,
            source=str(event.get("source", "")).strip(),
            summary=normalized_summary,
        )
        if primary_bucket:
            candidate["_score"] = int(candidate.get("_score", 0) or 0) + 60

        key = normalized_summary.lower()
        if key not in global_seen:
            global_seen.add(key)
            if primary_bucket:
                global_primary.append(candidate)
            else:
                global_secondary.append(candidate)
        for ws_id in ws_tokens:
            scoped_seen_bucket = scoped_seen[ws_id]
            if key in scoped_seen_bucket:
                continue
            scoped_seen_bucket.add(key)
            if primary_bucket:
                scoped_primary[ws_id].append(candidate)
            else:
                scoped_secondary[ws_id].append(candidate)

    scoped: dict[str, list[dict[str, str]]] = {}
    for ws_id in set(scoped_primary) | set(scoped_secondary):
        scoped[ws_id] = _finalize_candidate_buckets(
            primary=scoped_primary.get(ws_id, ()),
            secondary=scoped_secondary.get(ws_id, ()),
            max_items=max_items,
        )
    return {
        "global": _finalize_candidate_buckets(
            primary=global_primary,
            secondary=global_secondary,
            max_items=max_items,
        ),
        "by_workstream": scoped,
    }


def build_transaction_update_index(
    window_transactions: Sequence[Mapping[str, Any]],
    *,
    max_items: int = 3,
    max_workstream_fanout: int = 16,
) -> dict[str, Any]:
    global_primary: list[dict[str, Any]] = []
    global_secondary: list[dict[str, Any]] = []
    global_seen: set[str] = set()
    scoped_primary: dict[str, list[dict[str, Any]]] = defaultdict(list)
    scoped_secondary: dict[str, list[dict[str, Any]]] = defaultdict(list)
    scoped_seen: dict[str, set[str]] = defaultdict(set)

    for row in window_transactions:
        ws_tokens = tuple(
            str(token).strip()
            for token in row.get("workstreams", [])
            if str(token).strip()
        )
        files = [
            str(token).strip()
            for token in row.get("files", [])
            if str(token).strip()
        ]
        source_files, generated_files = compass_transaction_runtime._split_source_vs_generated_files(files)
        non_plan_source_files = [
            str(path).strip()
            for path in source_files
            if not str(path).startswith(("odylith/technical-plans/", "docs/", "agents-guidelines/", "skills/"))
        ]
        has_non_plan_surface = bool(non_plan_source_files)
        event_count = int(row.get("event_count", 0) or 0)
        if not source_files and generated_files and event_count >= 12:
            continue

        context = compass_base._narrative_excerpt(
            str(row.get("context", "")).strip(),
            max_sentences=1,
            max_chars=220,
        ).strip()
        headline = compass_base._narrative_excerpt(
            str(row.get("headline", "")).strip(),
            max_sentences=1,
            max_chars=220,
        ).strip()
        summary = context or headline
        primary_event_summary = ""
        event_rows = row.get("events", [])
        for item in event_rows:
            if not isinstance(item, Mapping):
                continue
            item_kind = str(item.get("kind", "")).strip()
            if item_kind not in {"implementation", "decision", "statement", "commit"}:
                continue
            item_summary = compass_base._humanize_execution_event_summary(
                kind=item_kind,
                summary=str(item.get("summary", "")).strip(),
            )
            if not item_summary:
                continue
            if compass_briefing_support._is_synthetic_plan_execution_signal(
                kind=item_kind,
                source=str(item.get("source", "")).strip(),
                summary=item_summary,
            ):
                continue
            primary_event_summary = item_summary
            break

        summary_lower = compass_base._normalize_sentence(summary).lower()
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
            summary = compass_transaction_runtime._local_change_headline_phrase(
                local_events=synthetic_local_events,
                files_count=len(non_plan_source_files),
            )

        normalized_summary = compass_briefing_support._sanitize_digest_summary(summary)
        if not normalized_summary or compass_briefing_support._looks_generic_churn_summary(normalized_summary):
            continue
        if normalized_summary.lower() in {"execution update", "updated code"}:
            continue

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
            if compass_briefing_support._is_synthetic_plan_execution_signal(
                kind=item_kind,
                source=str(item.get("source", "")).strip(),
                summary=str(item.get("summary", "")).strip(),
            ):
                continue
            has_meaningful_primary_signal = True
            break

        is_plan_only = bool(event_kinds) and event_kinds.issubset({"plan_update", "plan_completion"})
        ts = compass_transaction_runtime._transaction_end_ts(row)
        sort_ts = ts.timestamp() if isinstance(ts, dt.datetime) else 0.0
        candidate = {
            "kind": "transaction",
            "summary": normalized_summary,
            "_score": compass_briefing_support._narrative_signal_score(
                normalized_summary,
                files=source_files,
            ),
            "_sort_ts": sort_ts,
        }
        if has_meaningful_primary_signal:
            candidate["_score"] = int(candidate.get("_score", 0) or 0) + 120
        if has_non_plan_surface and not is_plan_only:
            candidate["_score"] = int(candidate.get("_score", 0) or 0) + 18
        if is_plan_only:
            candidate["_score"] = int(candidate.get("_score", 0) or 0) - 30

        key = normalized_summary.lower()
        allow_global = not (max_workstream_fanout > 0 and len(ws_tokens) > max_workstream_fanout)
        if allow_global and key not in global_seen:
            global_seen.add(key)
            if has_meaningful_primary_signal or int(candidate.get("_score", 0) or 0) >= 20:
                global_primary.append(candidate)
            else:
                global_secondary.append(candidate)
        for ws_id in ws_tokens:
            scoped_seen_bucket = scoped_seen[ws_id]
            if key in scoped_seen_bucket:
                continue
            scoped_seen_bucket.add(key)
            if has_meaningful_primary_signal or int(candidate.get("_score", 0) or 0) >= 20:
                scoped_primary[ws_id].append(candidate)
            else:
                scoped_secondary[ws_id].append(candidate)

    scoped: dict[str, list[dict[str, str]]] = {}
    for ws_id in set(scoped_primary) | set(scoped_secondary):
        scoped[ws_id] = _finalize_candidate_buckets(
            primary=scoped_primary.get(ws_id, ()),
            secondary=scoped_secondary.get(ws_id, ()),
            max_items=max_items,
        )
    return {
        "global": _finalize_candidate_buckets(
            primary=global_primary,
            secondary=global_secondary,
            max_items=max_items,
        ),
        "by_workstream": scoped,
    }


__all__ = [
    "build_execution_update_index",
    "build_transaction_update_index",
]
