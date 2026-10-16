"""Derive readable Project focus text from source-backed work signals."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.project_intelligence.summary import concise_text
from odylith.runtime.project_intelligence.utils import list_value, sentence, short


def backlog_rows_by_id(backlog: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Index Radar rows once so focus, jobs, and boundaries read the same source truth."""

    rows = [
        dict(row)
        for collection in ("execution", "queued", "finished")
        for row in list_value(backlog.get(collection))
        if isinstance(row, Mapping)
    ]
    return {
        str(row.get("idea_id", "")).strip(): row
        for row in rows
        if str(row.get("idea_id", "")).strip()
    }


def project_focus_text(
    raw_focus: object,
    *,
    active_workstreams: Sequence[str],
    backlog: Mapping[str, Any],
    release_label: str,
    fallback: str,
) -> str:
    """Prefer meaningful workstream intent when runtime activity text is too generic."""

    focus = concise_text(raw_focus, limit=145, fallback="")
    if focus and not _is_low_information_focus(focus):
        return focus
    titles = _active_workstream_titles(active_workstreams=active_workstreams, backlog=backlog)
    if titles:
        return short(_join_titles(titles), limit=145)
    return focus or concise_text(fallback, limit=145, fallback="Current source-backed work is active.")


def _active_workstream_titles(*, active_workstreams: Sequence[str], backlog: Mapping[str, Any]) -> list[str]:
    rows_by_id = backlog_rows_by_id(backlog)
    titles: list[str] = []
    seen: set[str] = set()
    for workstream_id in active_workstreams:
        row = rows_by_id.get(str(workstream_id).strip(), {})
        title = sentence(row.get("title"), str(workstream_id).strip())
        if not title:
            continue
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        titles.append(title)
    return titles[:3]


def _is_low_information_focus(value: str) -> bool:
    text = " ".join(str(value or "").strip().lower().split())
    if not text:
        return True
    patterns = (
        r"^(updated|added|changed|deleted)\s+.+(\s+and\s+\d+\s+other\s+areas)?$",
        r"^\d+\s+(files?|paths?|areas?)\s+(updated|changed|modified)$",
    )
    return any(re.match(pattern, text) for pattern in patterns)


def _join_titles(titles: Sequence[str]) -> str:
    items = [str(title).strip() for title in titles if str(title).strip()]
    if not items:
        return "current source-backed work"
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]}; {items[1]}"
    return f"{items[0]}, {items[1]}, and {items[2]}"
