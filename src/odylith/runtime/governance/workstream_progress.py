"""Shared workstream progress semantics for governed surfaces."""

from __future__ import annotations

from typing import Any
from typing import Mapping
from typing import Sequence

_TERMINAL_STATUSES = {"finished", "complete", "parked", "superseded"}
_PLANNING_STATUSES = {"planning", "queued"}
_ACTIVE_STATUSES = {"implementation"}


def _coerce_ratio(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        if 0.0 <= float(value) <= 1.0:
            return float(value)
        return None
    token = str(value).strip()
    if not token:
        return None
    try:
        numeric = float(token)
    except ValueError:
        return None
    if 0.0 <= numeric <= 1.0:
        return numeric
    return None


def normalize_status(status: str) -> str:
    return str(status or "").strip().lower()


def classify_workstream_progress(*, status: str, plan: Mapping[str, Any] | None) -> str:
    plan_row = plan if isinstance(plan, Mapping) else {}
    status_token = normalize_status(status)
    total_tasks = max(0, int(plan_row.get("total_tasks", 0) or 0))
    done_tasks = max(0, int(plan_row.get("done_tasks", 0) or 0))
    if total_tasks > 0 and done_tasks > total_tasks:
        done_tasks = total_tasks

    if status_token in _TERMINAL_STATUSES:
        return "closed"
    if total_tasks <= 0:
        if status_token in _ACTIVE_STATUSES:
            return "active_untracked"
        if status_token in _PLANNING_STATUSES:
            return "not_started"
        return "no_checklist"
    if done_tasks > 0:
        return "tracked"
    if status_token in _ACTIVE_STATUSES:
        return "active_untracked"
    if status_token in _PLANNING_STATUSES:
        return "not_started"
    return "checklist_only"


def derive_workstream_progress(*, status: str, plan: Mapping[str, Any] | None) -> dict[str, Any]:
    plan_row = plan if isinstance(plan, Mapping) else {}
    status_token = normalize_status(status)
    total_tasks = max(0, int(plan_row.get("total_tasks", 0) or 0))
    done_tasks = max(0, int(plan_row.get("done_tasks", 0) or 0))
    if total_tasks > 0 and done_tasks > total_tasks:
        done_tasks = total_tasks

    raw_ratio = _coerce_ratio(plan_row.get("progress_ratio"))
    if raw_ratio is None and total_tasks > 0:
        raw_ratio = round(done_tasks / total_tasks, 4)
    checklist_label = f"Checklist {done_tasks}/{total_tasks}" if total_tasks > 0 else ""
    classification = classify_workstream_progress(status=status_token, plan=plan_row)

    display_ratio: float | None
    display_label = ""
    display_state = "none"
    if classification == "closed":
        display_ratio = 1.0
        display_label = "100% progress"
        display_state = "percent"
    elif classification == "tracked":
        display_ratio = raw_ratio if raw_ratio is not None else round(done_tasks / total_tasks, 4)
        display_label = f"{int(round(display_ratio * 100))}% progress"
        display_state = "percent"
    elif classification == "not_started":
        display_ratio = 0.0
        display_label = "0% progress"
        display_state = "percent"
    elif classification in {"active_untracked", "checklist_only"}:
        display_ratio = None
        display_label = checklist_label or "Progress not yet captured"
        display_state = "checklist_only" if checklist_label else "unknown"
    else:
        display_ratio = None
        display_state = "unknown"

    return {
        "classification": classification,
        "display_progress_ratio": display_ratio,
        "display_progress_label": display_label,
        "display_progress_state": display_state,
        "checklist_label": checklist_label,
        "raw_progress_ratio": raw_ratio,
        "has_execution_underway": classification in {"closed", "tracked", "active_untracked"},
        "has_tracked_checklist_progress": classification in {"closed", "tracked"},
        "status": status_token,
    }


def summarize_active_progress(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    summary = {
        "closed": 0,
        "tracked": 0,
        "active_untracked": 0,
        "not_started": 0,
        "checklist_only": 0,
        "no_checklist": 0,
    }
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        progress = derive_workstream_progress(
            status=str(row.get("status", "")).strip(),
            plan=row.get("plan", {}) if isinstance(row.get("plan"), Mapping) else {},
        )
        classification = str(progress.get("classification", "")).strip()
        if classification in summary:
            summary[classification] += 1
        else:
            summary["no_checklist"] += 1
    return summary


__all__ = [
    "classify_workstream_progress",
    "derive_workstream_progress",
    "normalize_status",
    "summarize_active_progress",
]
