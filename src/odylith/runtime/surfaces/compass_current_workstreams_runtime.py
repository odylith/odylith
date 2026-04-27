"""Rank Compass workstreams that should stay visible in the current slice."""

from __future__ import annotations

from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.governance.delivery import scope_signal_ladder


def _normalized_id(value: Any) -> str:
    """Return a stable identifier string for row comparisons and sorting."""
    return str(value or "").strip()


def _status(value: Any) -> str:
    """Normalize a status token to lower-case comparison form."""
    return _normalized_id(value).lower()


def _active_wave(row: Mapping[str, Any]) -> bool:
    """Return whether any execution-wave program for the row is active."""
    programs = row.get("execution_wave_programs", [])
    if not isinstance(programs, Sequence):
        return False
    return any(
        isinstance(program, Mapping) and bool(program.get("has_active_wave"))
        for program in programs
    )


def _release_flags(row: Mapping[str, Any]) -> tuple[bool, bool]:
    """Return whether the row belongs to the current and/or active release."""
    release = row.get("release")
    if not isinstance(release, Mapping):
        return False, False
    aliases = {
        _normalized_id(alias).lower()
        for alias in release.get("aliases", [])
        if _normalized_id(alias)
    } if isinstance(release.get("aliases"), list) else set()
    is_current = "current" in aliases
    is_active = _status(release.get("status")) == "active"
    return is_current, is_active


def _row_idea_id(row: Mapping[str, Any]) -> str:
    """Read the normalized workstream id for a Compass row."""
    return _normalized_id(row.get("idea_id"))


def _eligible_row(
    *,
    row: Mapping[str, Any],
    event_count: int,
    recent_completed: bool,
) -> bool:
    """Return whether the row should be preserved in the current-workstream list."""
    signal = row.get("scope_signal")
    scope_rank = scope_signal_ladder.scope_signal_rank(signal or {}) if isinstance(signal, Mapping) else 0
    is_current_release, is_active_release = _release_flags(row)
    return any(
        (
            _status(row.get("status")) in {"implementation", "planning"},
            event_count > 0,
            recent_completed,
            _active_wave(row),
            is_current_release,
            is_active_release,
            scope_rank >= scope_signal_ladder.DEFAULT_PROMOTED_DEFAULT_RANK,
        )
    )


def _sort_key(
    *,
    row: Mapping[str, Any],
    event_count: int,
    recent_completed: bool,
) -> tuple[int, int, int, int, int, int, int, int, int, str]:
    """Sort visible workstreams by live relevance before falling back to id."""
    signal = row.get("scope_signal")
    scope_rank = scope_signal_ladder.scope_signal_rank(signal or {}) if isinstance(signal, Mapping) else 0
    promoted_default = bool(signal.get("promoted_default")) if isinstance(signal, Mapping) else False
    is_current_release, is_active_release = _release_flags(row)
    status = _status(row.get("status"))
    active_wave = _active_wave(row)
    highlighted = any(
        (
            event_count > 0,
            recent_completed,
            active_wave,
            is_current_release,
            promoted_default,
        )
    )
    status_rank = {
        "implementation": 3,
        "planning": 2,
        "queued": 1 if (active_wave or is_current_release or is_active_release or event_count > 0) else 0,
        "finished": 1 if recent_completed else 0,
    }.get(status, 0)
    return (
        0 if highlighted else 1,
        0 if active_wave else 1,
        0 if is_current_release else 1,
        0 if event_count > 0 else 1,
        -int(event_count),
        0 if recent_completed else 1,
        0 if is_active_release else 1,
        0 if promoted_default else 1,
        -int(scope_rank),
        -int(status_rank),
        _row_idea_id(row),
    )


def _event_counts_by_workstream(window_events: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Count recent activity events per workstream id."""
    event_counts: dict[str, int] = {}
    for row in window_events:
        if not isinstance(row, Mapping):
            continue
        for raw_id in row.get("workstreams", []):
            idea_id = _normalized_id(raw_id)
            if not idea_id:
                continue
            event_counts[idea_id] = int(event_counts.get(idea_id, 0) or 0) + 1
    return event_counts


def _recent_completed_ids(rows: Sequence[Mapping[str, str]]) -> set[str]:
    """Collect recently completed workstream ids from Compass history rows."""
    return {
        _normalized_id(row.get("backlog"))
        for row in rows
        if isinstance(row, Mapping) and _normalized_id(row.get("backlog"))
    }


def select_current_workstream_rows(
    *,
    all_rows: Sequence[Mapping[str, Any]],
    window_events: Sequence[Mapping[str, Any]],
    recent_completed_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, Any]]:
    """Choose and rank the workstream rows that deserve current visibility."""
    by_id: dict[str, dict[str, Any]] = {}
    ordered_rows: list[dict[str, Any]] = []
    for raw in all_rows:
        if not isinstance(raw, Mapping):
            continue
        row = dict(raw)
        idea_id = _row_idea_id(row)
        if not idea_id or idea_id in by_id:
            continue
        by_id[idea_id] = row
        ordered_rows.append(row)

    event_counts_by_ws = _event_counts_by_workstream(window_events)
    recent_completed_ids = _recent_completed_ids(recent_completed_rows)

    candidates = [
        row
        for row in ordered_rows
        if _eligible_row(
            row=row,
            event_count=int(event_counts_by_ws.get(_row_idea_id(row), 0) or 0),
            recent_completed=_row_idea_id(row) in recent_completed_ids,
        )
    ]
    if not candidates:
        candidates = ordered_rows

    ranked = sorted(
        candidates,
        key=lambda row: _sort_key(
            row=row,
            event_count=int(event_counts_by_ws.get(_row_idea_id(row), 0) or 0),
            recent_completed=_row_idea_id(row) in recent_completed_ids,
        ),
    )
    return ranked


__all__ = ["select_current_workstream_rows"]
