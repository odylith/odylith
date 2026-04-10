"""Shared plan progress extraction helpers for dashboard surfaces.

This module reads plan markdown files and derives deterministic checklist
progress for surfaces that need a lightweight progress signal without
re-implementing markdown parsing in multiple renderers.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CHECKBOX_RE = re.compile(r"^\s*-\s*\[(?P<mark>[xX ])\]\s+(?P<body>.+?)\s*$")
_HEADER_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$")
_EXCLUDED_PROGRESS_SECTIONS = {
    "Defer",
    "Impacted Areas",
    "Learnings",
    "Non-Goals",
    "Open Questions",
    "Open Questions/Decisions",
    "Risks & Mitigations",
    "Traceability",
}
_EXCLUDED_NEXT_TASK_SECTIONS = {
    *_EXCLUDED_PROGRESS_SECTIONS,
}


def collect_plan_progress(plan_path: Path) -> dict[str, Any]:
    created = ""
    updated = ""
    all_total = 0
    all_done = 0
    total = 0
    done = 0
    next_tasks: list[str] = []
    current_section = ""

    if not plan_path.is_file():
        return {
            "path": "",
            "created": "",
            "updated": "",
            "all_total_tasks": 0,
            "all_done_tasks": 0,
            "total_tasks": 0,
            "done_tasks": 0,
            "progress_ratio": 0.0,
            "progress_basis": "execution_checklist",
            "next_tasks": [],
        }

    for raw in plan_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        header_match = _HEADER_RE.match(raw)
        if header_match is not None:
            current_section = str(header_match.group("title")).strip()
            continue
        if line.startswith("Created:"):
            token = line[len("Created:") :].strip()
            if _DATE_RE.fullmatch(token):
                created = token
        elif line.startswith("Updated:"):
            token = line[len("Updated:") :].strip()
            if _DATE_RE.fullmatch(token):
                updated = token

        match = _CHECKBOX_RE.match(raw)
        if match is None:
            continue
        body = str(match.group("body")).strip()
        all_total += 1
        checked = str(match.group("mark")).lower() == "x"
        if checked:
            all_done += 1
        lowered = body.lower()
        if lowered.startswith("risk:") or lowered.startswith("mitigation:"):
            continue
        if current_section in _EXCLUDED_PROGRESS_SECTIONS:
            continue
        total += 1
        if checked:
            done += 1
        else:
            if current_section in _EXCLUDED_NEXT_TASK_SECTIONS:
                continue
            if len(next_tasks) < 6:
                next_tasks.append(body)

    ratio = (done / total) if total > 0 else 0.0
    return {
        "path": plan_path.as_posix(),
        "created": created,
        "updated": updated,
        "all_total_tasks": all_total,
        "all_done_tasks": all_done,
        "total_tasks": total,
        "done_tasks": done,
        "progress_ratio": round(ratio, 4),
        "progress_basis": "execution_checklist",
        "next_tasks": next_tasks,
    }


__all__ = ["collect_plan_progress"]
