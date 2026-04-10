from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.governance import validate_backlog_contract as backlog_contract
from odylith.runtime.governance import release_planning_view_model

_ACTIVE_WORKSTREAM_STATUSES = {"planning", "implementation"}


def _load_idea_specs(*, repo_root: Path) -> dict[str, backlog_contract.IdeaSpec]:
    ideas_root = Path(repo_root).resolve() / "odylith" / "radar" / "source" / "ideas"
    if not ideas_root.is_dir():
        return {}
    specs: dict[str, backlog_contract.IdeaSpec] = {}
    for path in sorted(ideas_root.rglob("*.md")):
        spec = backlog_contract._parse_idea_spec(path)  # noqa: SLF001
        idea_id = str(spec.metadata.get("idea_id", "")).strip().upper()
        if backlog_contract._IDEA_ID_RE.fullmatch(idea_id):  # noqa: SLF001
            specs[idea_id] = spec
    return specs


def load_release_view_from_source(*, repo_root: Path) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    idea_specs = _load_idea_specs(repo_root=repo_root)
    payload, errors, _state = release_planning_view_model.build_release_view_from_repo(
        repo_root=Path(repo_root).resolve(),
        idea_specs=idea_specs,
    )
    workstream_status_by_id = {
        idea_id: str(spec.metadata.get("status", "")).strip().lower()
        for idea_id, spec in idea_specs.items()
    }
    return payload, workstream_status_by_id, list(errors)


def _workstream_ids(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    return sorted(
        {
            str(item).strip().upper()
            for item in items
            if backlog_contract._IDEA_ID_RE.fullmatch(str(item).strip().upper())  # noqa: SLF001
        }
    )


def _runtime_workstream_ids(payload: Mapping[str, Any]) -> list[str]:
    current = payload.get("current_workstreams")
    if not isinstance(current, list):
        return []
    return sorted(
        {
            str(row.get("idea_id", "")).strip().upper()
            for row in current
            if isinstance(row, Mapping)
            and backlog_contract._IDEA_ID_RE.fullmatch(str(row.get("idea_id", "")).strip().upper())  # noqa: SLF001
        }
    )


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _load_compass_release_truth_from_traceability(
    *,
    repo_root: Path,
) -> tuple[dict[str, Any], list[str]]:
    payload = _read_json_object(
        Path(repo_root).resolve() / "odylith" / "radar" / "traceability-graph.v1.json"
    )
    if not payload:
        return {}, []
    current_release = (
        dict(payload.get("current_release", {}))
        if isinstance(payload.get("current_release"), Mapping)
        else {}
    )
    if not current_release:
        return {}, []
    rows = payload.get("workstreams")
    current_workstreams = sorted(
        {
            str(row.get("idea_id", "")).strip().upper()
            for row in rows
            if isinstance(row, Mapping)
            and str(row.get("status", "")).strip().lower() in _ACTIVE_WORKSTREAM_STATUSES
            and backlog_contract._IDEA_ID_RE.fullmatch(str(row.get("idea_id", "")).strip().upper())  # noqa: SLF001
        }
    ) if isinstance(rows, list) else []
    return current_release, current_workstreams


def _format_workstreams(items: list[str]) -> str:
    if not items:
        return "none"
    return ", ".join(items)


def build_compass_runtime_truth_drift(
    *,
    repo_root: Path,
    runtime_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(runtime_payload or {})
    if not payload:
        return {}

    source_current_release, source_current_workstreams = _load_compass_release_truth_from_traceability(
        repo_root=repo_root
    )
    truth_source = "traceability_graph"
    if not source_current_release:
        source_release_view, workstream_status_by_id, _errors = load_release_view_from_source(repo_root=repo_root)
        source_current_release = (
            dict(source_release_view.get("current_release", {}))
            if isinstance(source_release_view.get("current_release"), Mapping)
            else {}
        )
        source_current_workstreams = sorted(
            {
                idea_id
                for idea_id, status in workstream_status_by_id.items()
                if status in _ACTIVE_WORKSTREAM_STATUSES
            }
        )
        truth_source = "release_source"
    runtime_release_summary = (
        dict(payload.get("release_summary", {}))
        if isinstance(payload.get("release_summary"), Mapping)
        else {}
    )
    runtime_current_release = (
        dict(runtime_release_summary.get("current_release", {}))
        if isinstance(runtime_release_summary.get("current_release"), Mapping)
        else {}
    )

    source_current_release_id = str(source_current_release.get("release_id", "")).strip()
    runtime_current_release_id = str(runtime_current_release.get("release_id", "")).strip()
    source_active_members = _workstream_ids(source_current_release.get("active_workstreams"))
    runtime_active_members = _workstream_ids(runtime_current_release.get("active_workstreams"))
    source_completed_members = _workstream_ids(source_current_release.get("completed_workstreams"))
    runtime_completed_members = _workstream_ids(runtime_current_release.get("completed_workstreams"))

    runtime_current_workstreams = _runtime_workstream_ids(payload)

    reason_codes: list[str] = []
    if source_current_release_id != runtime_current_release_id:
        reason_codes.append("current_release_id")
    if source_active_members != runtime_active_members:
        reason_codes.append("active_release_membership")
    if source_completed_members != runtime_completed_members:
        reason_codes.append("completed_release_membership")
    if source_current_workstreams != runtime_current_workstreams:
        reason_codes.append("current_workstreams")
    if not reason_codes:
        return {}

    release_label = (
        str(source_current_release.get("display_label", "")).strip()
        or str(source_current_release.get("effective_name", "")).strip()
        or str(source_current_release.get("version", "")).strip()
        or source_current_release_id
        or runtime_current_release_id
        or "the current release"
    )
    body_parts: list[str] = []
    if any(
        code in reason_codes
        for code in ("current_release_id", "active_release_membership", "completed_release_membership")
    ):
        body_parts.append(
            f"Release truth for {release_label} now targets {_format_workstreams(source_active_members)} "
            f"and completes {_format_workstreams(source_completed_members)}, while the visible Compass snapshot targets "
            f"{_format_workstreams(runtime_active_members)} and completes {_format_workstreams(runtime_completed_members)}."
        )
    if "current_workstreams" in reason_codes:
        body_parts.append(
            f"Source truth current workstreams are {_format_workstreams(source_current_workstreams)}, "
            f"while the visible snapshot lists {_format_workstreams(runtime_current_workstreams)}."
        )
    warning = " ".join(body_parts).strip()
    if warning:
        warning += " Run `odylith compass refresh --repo-root .` to refresh the Compass runtime snapshot."

    return {
        "visible": True,
        "reason_codes": reason_codes,
        "source_current_release_id": source_current_release_id,
        "runtime_current_release_id": runtime_current_release_id,
        "truth_source": truth_source,
        "source_active_members": source_active_members,
        "runtime_active_members": runtime_active_members,
        "source_completed_members": source_completed_members,
        "runtime_completed_members": runtime_completed_members,
        "source_current_workstreams": source_current_workstreams,
        "runtime_current_workstreams": runtime_current_workstreams,
        "warning": warning,
    }


__all__ = [
    "build_compass_runtime_truth_drift",
    "load_release_view_from_source",
]
