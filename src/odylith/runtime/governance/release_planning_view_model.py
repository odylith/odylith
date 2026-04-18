"""Release Planning View Model helpers for the Odylith governance layer."""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from typing import Mapping

from odylith.runtime.governance import release_planning_contract


def _surface_release_label(release: Any) -> str:
    if isinstance(release, release_planning_contract.ReleaseRecord):
        return (
            str(release.effective_name).strip()
            or str(release.release_id).strip()
        )
    if isinstance(release, Mapping):
        return (
            str(release.get("effective_name", "")).strip()
            or str(release.get("name", "")).strip()
            or str(release.get("version", "")).strip()
            or str(release.get("tag", "")).strip()
            or str(release.get("display_label", "")).strip()
            or str(release.get("release_id", "")).strip()
        )
    return str(release or "").strip()


def _release_row(
    *,
    state: release_planning_contract.ReleasePlanningState,
    release: release_planning_contract.ReleaseRecord,
    active_workstreams: list[str],
    completed_workstreams: list[str],
) -> dict[str, Any]:
    aliases = state.aliases_for_release(release.release_id)
    row = release.as_dict(
        aliases=aliases,
        active_workstreams=active_workstreams,
        completed_workstreams=completed_workstreams,
    ) | {
        "active_workstream_count": len(active_workstreams),
        "completed_workstream_count": len(completed_workstreams),
    }
    row["display_label"] = _surface_release_label(row) or str(release.release_id).strip()
    return row


def _history_label(
    *,
    state: release_planning_contract.ReleasePlanningState,
    release_id: str,
) -> str:
    release = state.releases_by_id.get(str(release_id or "").strip())
    if release is None:
        return str(release_id or "").strip()
    return _surface_release_label(release)


def _completed_release_id(
    *,
    state: release_planning_contract.ReleasePlanningState,
    workstream_id: str,
    active_release_id: str,
    history: tuple[release_planning_contract.ReleaseHistoryEntry, ...],
) -> str:
    if state.workstream_status_by_id.get(str(workstream_id).strip(), "") != "finished":
        return ""
    if not history:
        return ""
    latest = history[-1]
    if str(latest.action).strip().lower() != "remove":
        return ""
    release_id = str(latest.release_id).strip()
    if not release_id or release_id == str(active_release_id).strip():
        return ""
    return release_id


def build_release_view_payload(
    *,
    state: release_planning_contract.ReleasePlanningState,
) -> dict[str, Any]:
    active_workstreams_by_release: dict[str, list[str]] = defaultdict(list)
    for workstream_id, release_id in state.active_release_by_workstream.items():
        active_workstreams_by_release[str(release_id).strip()].append(str(workstream_id).strip())

    completed_workstreams_by_release: dict[str, list[str]] = defaultdict(list)
    for workstream_id, history in state.history_by_workstream.items():
        completed_release_id = _completed_release_id(
            state=state,
            workstream_id=workstream_id,
            active_release_id=state.active_release_by_workstream.get(workstream_id, ""),
            history=tuple(history),
        )
        if completed_release_id:
            completed_workstreams_by_release[completed_release_id].append(str(workstream_id).strip())

    catalog = [
        _release_row(
            state=state,
            release=release,
            active_workstreams=sorted(active_workstreams_by_release.get(release.release_id, [])),
            completed_workstreams=sorted(completed_workstreams_by_release.get(release.release_id, [])),
        )
        for release in sorted(
            state.releases_by_id.values(),
            key=lambda row: row.release_id,
        )
    ]
    catalog_by_id = {
        str(row.get("release_id", "")).strip(): row
        for row in catalog
        if str(row.get("release_id", "")).strip()
    }

    alias_rows = {
        alias: dict(catalog_by_id.get(release_id, {}))
        for alias, release_id in sorted(state.alias_to_release_id.items())
        if release_id in catalog_by_id
    }
    current_release = dict(alias_rows.get("current", {}))
    next_release = dict(alias_rows.get("next", {}))

    workstreams: dict[str, dict[str, Any]] = {}
    for workstream_id in sorted(
        set(state.history_by_workstream.keys()) | set(state.active_release_by_workstream.keys())
    ):
        active_release_id = state.active_release_by_workstream.get(workstream_id, "")
        active_release = dict(catalog_by_id.get(active_release_id, {}))
        history = [
            {
                **entry.as_dict(),
                "release_label": _history_label(state=state, release_id=entry.release_id),
                "from_release_label": _history_label(state=state, release_id=entry.from_release_id),
                "to_release_label": _history_label(state=state, release_id=entry.to_release_id),
            }
            for entry in state.history_by_workstream.get(workstream_id, ())
        ]
        summary_parts: list[str] = []
        if active_release:
            summary_parts.append(f"Active: {_surface_release_label(active_release) or active_release_id}")
        if history:
            latest = history[-1]
            if latest.get("action") == "move":
                summary_parts.append(
                    f"Latest move: {latest.get('from_release_label') or latest.get('from_release_id')} -> {latest.get('to_release_label') or latest.get('to_release_id')}"
                )
            elif latest.get("action") == "add":
                summary_parts.append(
                    f"Added to {latest.get('release_label') or latest.get('release_id')}"
                )
            elif latest.get("action") == "remove":
                summary_parts.append(
                    f"Removed from {latest.get('release_label') or latest.get('release_id')}"
                )
        workstreams[workstream_id] = {
            "active_release_id": active_release_id,
            "active_release": active_release,
            "history": history,
            "history_summary": " · ".join(part for part in summary_parts if part),
        }

    return {
        "catalog": catalog,
        "aliases": alias_rows,
        "current_release": current_release,
        "next_release": next_release,
        "workstreams": workstreams,
        "summary": {
            "release_count": len(catalog),
            "alias_count": len(alias_rows),
            "active_assignment_count": len(state.active_release_by_workstream),
        },
    }


def build_release_view_from_repo(
    *,
    repo_root,
    idea_specs: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], list[str], release_planning_contract.ReleasePlanningState]:
    state, errors = release_planning_contract.validate_release_planning(
        repo_root=repo_root,
        idea_specs=idea_specs,
    )
    return build_release_view_payload(state=state), errors, state


__all__ = [
    "build_release_view_from_repo",
    "build_release_view_payload",
]
