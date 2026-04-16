"""Execution-focus helpers extracted from the Compass runtime."""

from __future__ import annotations

import datetime as dt
from typing import Any, Mapping, Sequence


def _host():
    from odylith.runtime.surfaces import compass_dashboard_runtime as host

    return host


def _build_execution_focus_payload(
    *,
    transactions: Sequence[Mapping[str, Any]],
    now: dt.datetime,
    active_window_minutes: int,
    recent_window_minutes: int,
) -> dict[str, Any]:
    host = _host()
    _DEFAULT_ACTIVE_WINDOW_MINUTES = host._DEFAULT_ACTIVE_WINDOW_MINUTES
    _DEFAULT_RECENT_FOCUS_WINDOW_MINUTES = host._DEFAULT_RECENT_FOCUS_WINDOW_MINUTES
    _split_source_vs_generated_files = host._split_source_vs_generated_files
    _parse_iso_ts = host._parse_iso_ts
    _safe_iso = host._safe_iso
    active_window = dt.timedelta(minutes=max(1, active_window_minutes))
    recent_window = dt.timedelta(minutes=max(1, recent_window_minutes))
    score_weights: dict[str, int] = {
        "implementation": 16,
        "decision": 14,
        "statement": 12,
        "commit": 8,
        "local_change": 6,
        "plan_update": 3,
        "plan_completion": 3,
        "bug_resolved": 2,
        "bug_update": 1,
        "bug_watch": -6,
    }
    risk_kinds = {"bug_watch", "bug_update", "bug_resolved"}
    implementation_signal_kinds = {"implementation", "decision", "statement"}
    change_signal_kinds = {"commit", "local_change"}
    row_facts_cache: dict[int, dict[str, Any]] = {}

    def _row_facts(row: Mapping[str, Any]) -> dict[str, Any]:
        cached = row_facts_cache.get(id(row))
        if cached is not None:
            return cached

        raw_events = row.get("events", [])
        events = []
        if isinstance(raw_events, Sequence):
            for event in raw_events:
                if isinstance(event, Mapping):
                    events.append(event)

        kind_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}
        for event in events:
            kind = str(event.get("kind", "")).strip().lower()
            if kind:
                kind_counts[kind] = kind_counts.get(kind, 0) + 1
            source = str(event.get("source", "")).strip().lower()
            if source:
                source_counts[source] = source_counts.get(source, 0) + 1

        source_files, generated_files = _split_source_vs_generated_files(row.get("files", []))
        implementation_signal_count = sum(
            int(kind_counts.get(kind, 0) or 0) for kind in implementation_signal_kinds
        )
        change_signal_count = sum(int(kind_counts.get(kind, 0) or 0) for kind in change_signal_kinds)
        activity_signal_count = sum(
            int(count or 0)
            for kind, count in kind_counts.items()
            if str(kind).strip() and str(kind).strip() not in risk_kinds
        )
        risk_signal_count = sum(int(kind_counts.get(kind, 0) or 0) for kind in risk_kinds)
        context = str(row.get("context", "")).strip()
        has_implementation_signal = False
        if implementation_signal_count > 0:
            has_implementation_signal = True
        elif source_files and change_signal_count > 0:
            has_implementation_signal = True
        elif context and source_files and activity_signal_count > 0:
            has_implementation_signal = True

        generated_only_batch = not source_files and bool(generated_files)
        generated_count = len(generated_files)
        event_count = int(row.get("event_count", 0) or 0)
        generated_bulk_flood = (
            not source_files
            and (
                generated_count >= 24
                or event_count >= 40
                or (generated_count >= 10 and event_count >= 16)
            )
        )

        end_ts = _parse_iso_ts(str(row.get("end_ts_iso", "")).strip())
        last_event_ts = end_ts or _parse_iso_ts(str(row.get("start_ts_iso", "")).strip())
        event_age = (now - last_event_ts) if last_event_ts is not None else None
        is_active = bool(event_age is not None and event_age <= active_window)
        is_recent = bool(event_age is not None and event_age <= recent_window)

        focus_score = sum(
            int(count or 0) * int(score_weights.get(kind, 0))
            for kind, count in kind_counts.items()
        )
        if has_implementation_signal:
            focus_score += 20
        if source_files:
            focus_score += min(12, len(source_files))
        if bool(row.get("explicit_open")):
            focus_score += 6
        if context:
            focus_score += 6
        tx_id = str(row.get("transaction_id", "")).strip()
        if tx_id and not tx_id.startswith("txn:global:auto-"):
            focus_score += 2
        if activity_signal_count > 0:
            focus_score += 4
        if activity_signal_count == 0 and risk_signal_count > 0:
            focus_score -= 12
        if generated_only_batch:
            focus_score -= 24
        if generated_bulk_flood:
            focus_score -= 80

        cached = {
            "events": events,
            "kind_counts": kind_counts,
            "source_counts": source_counts,
            "source_files": source_files,
            "generated_files": generated_files,
            "activity_signal_count": activity_signal_count,
            "risk_signal_count": risk_signal_count,
            "has_implementation_signal": has_implementation_signal,
            "generated_only_batch": generated_only_batch,
            "generated_bulk_flood": generated_bulk_flood,
            "last_event_ts": last_event_ts,
            "is_active": is_active,
            "is_recent": is_recent,
            "focus_score": focus_score,
        }
        row_facts_cache[id(row)] = cached
        return cached

    def _last_event_ts(row: Mapping[str, Any]) -> dt.datetime | None:
        return _row_facts(row)["last_event_ts"]

    def _event_age(row: Mapping[str, Any]) -> dt.timedelta | None:
        last_ts = _last_event_ts(row)
        if last_ts is None:
            return None
        return now - last_ts

    def _is_active(row: Mapping[str, Any]) -> bool:
        return bool(_row_facts(row)["is_active"])

    def _is_recent(row: Mapping[str, Any]) -> bool:
        return bool(_row_facts(row)["is_recent"])

    def _iter_events(row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        return list(_row_facts(row)["events"])

    def _kind_counts(row: Mapping[str, Any]) -> dict[str, int]:
        return dict(_row_facts(row)["kind_counts"])

    def _source_counts(row: Mapping[str, Any]) -> dict[str, int]:
        return dict(_row_facts(row)["source_counts"])

    def _file_split(row: Mapping[str, Any]) -> tuple[list[str], list[str]]:
        facts = _row_facts(row)
        return list(facts["source_files"]), list(facts["generated_files"])

    def _implementation_signal_count(kind_counts: Mapping[str, int]) -> int:
        return sum(int(kind_counts.get(kind, 0) or 0) for kind in implementation_signal_kinds)

    def _change_signal_count(kind_counts: Mapping[str, int]) -> int:
        return sum(int(kind_counts.get(kind, 0) or 0) for kind in change_signal_kinds)

    def _activity_signal_count(kind_counts: Mapping[str, int]) -> int:
        return sum(
            int(count or 0)
            for kind, count in kind_counts.items()
            if str(kind).strip() and str(kind).strip() not in risk_kinds
        )

    def _risk_signal_count(kind_counts: Mapping[str, int]) -> int:
        return sum(int(kind_counts.get(kind, 0) or 0) for kind in risk_kinds)

    def _has_implementation_signal(row: Mapping[str, Any]) -> bool:
        return bool(_row_facts(row)["has_implementation_signal"])

    def _is_generated_only_batch(row: Mapping[str, Any]) -> bool:
        return bool(_row_facts(row)["generated_only_batch"])

    def _is_generated_bulk_flood(row: Mapping[str, Any]) -> bool:
        return bool(_row_facts(row)["generated_bulk_flood"])

    def _focus_score(row: Mapping[str, Any]) -> int:
        return int(_row_facts(row)["focus_score"])

    def _focus_rank(row: Mapping[str, Any]) -> tuple[int, int, int, int, int, int, int, int, int, dt.datetime, str]:
        kind_counts = _kind_counts(row)
        activity_count = _activity_signal_count(kind_counts)
        has_impl_signal = _has_implementation_signal(row)
        source_files, _generated_files = _file_split(row)
        last_ts = _last_event_ts(row)
        if last_ts is None:
            last_ts = dt.datetime.min.replace(tzinfo=dt.timezone.utc)
        return (
            1 if (_is_active(row) and has_impl_signal) else 0,
            1 if _is_active(row) else 0,
            1 if (_is_recent(row) and has_impl_signal) else 0,
            1 if has_impl_signal else 0,
            0 if _is_generated_bulk_flood(row) else 1,
            0 if _is_generated_only_batch(row) else 1,
            len(source_files),
            1 if bool(row.get("explicit_open")) else 0,
            1 if str(row.get("context", "")).strip() else 0,
            activity_count,
            _focus_score(row),
            last_ts,
            str(row.get("id", "")).strip(),
        )

    def _focus_reason(*, row: Mapping[str, Any], activity_count: int, risk_count: int, selection_mode: str) -> str:
        if selection_mode and selection_mode not in {"active_implementation"}:
            return selection_mode
        if bool(row.get("explicit_open")):
            return "explicit_open_transaction"
        if activity_count > 0 and str(row.get("context", "")).strip():
            return "context_and_activity"
        if activity_count > 0:
            return "recent_activity_signal"
        if risk_count > 0:
            return "risk_signal_only"
        return "recent_transaction"

    def _latest_implementation_iso(rows: Sequence[Mapping[str, Any]]) -> str:
        latest: dt.datetime | None = None
        for row in rows:
            if not _has_implementation_signal(row):
                continue
            ts = _last_event_ts(row)
            if ts is None:
                continue
            if latest is None or ts > latest:
                latest = ts
        return _safe_iso(latest) if latest else ""

    def _select_focus_row(
        rows: Sequence[Mapping[str, Any]],
    ) -> tuple[Mapping[str, Any] | None, str, bool, bool, str]:
        ranked = sorted(list(rows), key=_focus_rank, reverse=True)
        if not ranked:
            return None, "none", False, False, ""

        active_impl = [
            row
            for row in ranked
            if _is_active(row) and _has_implementation_signal(row) and not _is_generated_only_batch(row)
        ]
        recent_impl = [
            row
            for row in ranked
            if _is_recent(row) and _has_implementation_signal(row) and not _is_generated_only_batch(row)
        ]
        active_non_generated = [
            row for row in ranked if _is_active(row) and not _is_generated_only_batch(row)
        ]
        recent_non_generated = [
            row for row in ranked if _is_recent(row) and not _is_generated_only_batch(row)
        ]
        non_generated = [row for row in ranked if not _is_generated_only_batch(row)]

        latest_impl_iso = _latest_implementation_iso(ranked)
        has_live_implementation = bool(active_impl)
        has_recent_implementation = bool(recent_impl)

        if active_impl:
            return active_impl[0], "active_implementation", has_live_implementation, has_recent_implementation, latest_impl_iso
        if recent_impl:
            return (
                recent_impl[0],
                "recent_implementation_fallback",
                has_live_implementation,
                has_recent_implementation,
                latest_impl_iso,
            )
        if active_non_generated:
            return (
                active_non_generated[0],
                "active_non_implementation",
                has_live_implementation,
                has_recent_implementation,
                latest_impl_iso,
            )
        if recent_non_generated:
            return (
                recent_non_generated[0],
                "recent_non_implementation",
                has_live_implementation,
                has_recent_implementation,
                latest_impl_iso,
            )
        if non_generated:
            return (
                non_generated[0],
                "degraded_non_generated",
                has_live_implementation,
                has_recent_implementation,
                latest_impl_iso,
            )
        return ranked[0], "generated_batch_fallback", has_live_implementation, has_recent_implementation, latest_impl_iso

    def _focus_entry(
        row: Mapping[str, Any] | None,
        *,
        selection_mode: str,
        has_live_implementation: bool,
        has_recent_implementation: bool,
        latest_implementation_iso: str,
    ) -> dict[str, Any]:
        if not isinstance(row, Mapping):
            return {
                "is_active": False,
                "transaction_id": "",
                "session_id": "",
                "context": "",
                "headline": "",
                "last_event_iso": "",
                "start_ts_iso": "",
                "workstreams": [],
                "event_count": 0,
                "files_count": 0,
                "kind_counts": {},
                "source_counts": {},
                "activity_signal_count": 0,
                "risk_signal_count": 0,
                "top_files": [],
                "source_files_count": 0,
                "generated_files_count": 0,
                "generated_only_batch": False,
                "latest_event_kind": "",
                "latest_event_summary": "",
                "focus_reason": "none",
                "selection_mode": selection_mode,
                "has_live_implementation": has_live_implementation,
                "has_recent_implementation": has_recent_implementation,
                "latest_implementation_iso": latest_implementation_iso,
            }
        kind_counts = _kind_counts(row)
        source_counts = _source_counts(row)
        activity_count = _activity_signal_count(kind_counts)
        risk_count = _risk_signal_count(kind_counts)
        events = _iter_events(row)
        latest_event = events[0] if events else {}
        files = [
            str(token).strip()
            for token in row.get("files", [])
            if str(token).strip()
        ]
        source_files, generated_files = _split_source_vs_generated_files(files)
        ordered_files = source_files + generated_files
        return {
            "is_active": _is_active(row),
            "transaction_id": str(row.get("transaction_id", "")).strip(),
            "session_id": str(row.get("session_id", "")).strip(),
            "context": str(row.get("context", "")).strip(),
            "headline": str(row.get("headline", "")).strip(),
            "last_event_iso": str(row.get("end_ts_iso", "")).strip(),
            "start_ts_iso": str(row.get("start_ts_iso", "")).strip(),
            "workstreams": [
                str(token).strip()
                for token in row.get("workstreams", [])
                if str(token).strip()
            ],
            "event_count": int(row.get("event_count", 0) or 0),
            "files_count": int(row.get("files_count", 0) or 0),
            "kind_counts": kind_counts,
            "source_counts": source_counts,
            "activity_signal_count": activity_count,
            "risk_signal_count": risk_count,
            "top_files": ordered_files[:8],
            "source_files_count": len(source_files),
            "generated_files_count": len(generated_files),
            "generated_only_batch": not source_files and bool(generated_files),
            "latest_event_kind": str(latest_event.get("kind", "")).strip(),
            "latest_event_summary": str(latest_event.get("summary", "")).strip(),
            "has_implementation_signal": _has_implementation_signal(row),
            "focus_reason": _focus_reason(
                row=row,
                activity_count=activity_count,
                risk_count=risk_count,
                selection_mode=selection_mode,
            ),
            "selection_mode": selection_mode,
            "has_live_implementation": has_live_implementation,
            "has_recent_implementation": has_recent_implementation,
            "latest_implementation_iso": latest_implementation_iso,
        }

    sorted_rows = sorted(list(transactions), key=_focus_rank, reverse=True)
    (
        global_pick,
        global_mode,
        global_has_live_impl,
        global_has_recent_impl,
        global_latest_impl_iso,
    ) = _select_focus_row(sorted_rows)

    by_workstream: dict[str, dict[str, Any]] = {}
    candidates_by_ws: dict[str, list[Mapping[str, Any]]] = {}
    for row in sorted_rows:
        for ws_id in row.get("workstreams", []):
            token = str(ws_id).strip()
            if not token:
                continue
            candidates_by_ws.setdefault(token, []).append(row)

    for ws_id, rows in candidates_by_ws.items():
        (
            pick,
            selection_mode,
            has_live_implementation,
            has_recent_implementation,
            latest_implementation_iso,
        ) = _select_focus_row(rows)
        by_workstream[ws_id] = _focus_entry(
            pick,
            selection_mode=selection_mode,
            has_live_implementation=has_live_implementation,
            has_recent_implementation=has_recent_implementation,
            latest_implementation_iso=latest_implementation_iso,
        )

    return {
        "active_window_minutes": max(1, active_window_minutes),
        "recent_window_minutes": max(1, recent_window_minutes),
        "global": _focus_entry(
            global_pick,
            selection_mode=global_mode,
            has_live_implementation=global_has_live_impl,
            has_recent_implementation=global_has_recent_impl,
            latest_implementation_iso=global_latest_impl_iso,
        ),
        "by_workstream": by_workstream,
    }
