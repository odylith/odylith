"""Upgrade transaction reports and doctor observability lines."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Mapping

from odylith.install.lock_hygiene import LOCK_NOTE_THRESHOLD, lock_hygiene_summary


def json_ready(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_ready(item) for item in value]
    return value


def lifecycle_plan_payload(plan: object) -> dict[str, object]:
    return {
        "command": str(getattr(plan, "command", "") or "").strip(),
        "headline": str(getattr(plan, "headline", "") or "").strip(),
        "metadata": json_ready(dict(getattr(plan, "metadata", {}) or {})),
        "steps": [
            {
                "label": str(getattr(step, "label", "") or "").strip(),
                "mutation_classes": [
                    str(token).strip()
                    for token in getattr(step, "mutation_classes", ()) or ()
                    if str(token).strip()
                ],
                "paths": [
                    str(token).strip()
                    for token in getattr(step, "paths", ()) or ()
                    if str(token).strip()
                ],
                "detail": str(getattr(step, "detail", "") or "").strip(),
            }
            for step in tuple(getattr(plan, "steps", ()) or ())
        ],
        "dirty_overlap": [
            str(token).strip()
            for token in getattr(plan, "dirty_overlap", ()) or ()
            if str(token).strip()
        ],
        "notes": [
            str(token).strip()
            for token in getattr(plan, "notes", ()) or ()
            if str(token).strip()
        ],
    }


def upgrade_summary_payload(summary: object) -> dict[str, object]:
    return {
        "active_version": str(getattr(summary, "active_version", "") or "").strip(),
        "previous_version": str(getattr(summary, "previous_version", "") or "").strip(),
        "pinned_version": str(getattr(summary, "pinned_version", "") or "").strip(),
        "pin_changed": bool(getattr(summary, "pin_changed", False)),
        "repo_role": str(getattr(summary, "repo_role", "") or "").strip(),
        "followed_latest": bool(getattr(summary, "followed_latest", False)),
        "release_tag": str(getattr(summary, "release_tag", "") or "").strip(),
        "release_url": str(getattr(summary, "release_url", "") or "").strip(),
        "release_published_at": str(getattr(summary, "release_published_at", "") or "").strip(),
        "launcher_path": str(getattr(summary, "launcher_path", "") or "").strip(),
        "retention_warnings": [
            str(item).strip()
            for item in getattr(summary, "retention_warnings", ()) or ()
            if str(item).strip()
        ],
        "migration_plan": json_ready(getattr(summary, "migration_plan", {}) or {}),
        "migration_results": json_ready(getattr(summary, "migration_results", ()) or ()),
        "verification": json_ready(getattr(summary, "verification", {}) or {}),
    }


def phase_payload(
    *,
    name: str,
    started_at: datetime,
    finished_at: datetime,
    status: str,
    details: Mapping[str, object] | None = None,
) -> dict[str, object]:
    return {
        "name": name,
        "status": status,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        "details": json_ready(dict(details or {})),
    }


def write_upgrade_report(*, repo_root: Path, report: dict[str, object], started_at: datetime) -> Path:
    logs_dir = repo_root / ".odylith" / "runtime" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    report_path = logs_dir / f"upgrade-{started_at.strftime('%Y%m%dT%H%M%SZ')}.json"
    payload = dict(report)
    payload["report_path"] = str(report_path)
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["report_path"] = str(report_path)
    return report_path


def latest_upgrade_report(*, repo_root: Path) -> tuple[Path, dict[str, object]] | None:
    logs_dir = repo_root / ".odylith" / "runtime" / "logs"
    if not logs_dir.is_dir():
        return None
    candidates = sorted(logs_dir.glob("upgrade-*.json"))
    for report_path in reversed(candidates):
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            return report_path, payload
    return None


def repo_relative_path(*, repo_root: Path, path: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return str(path)


def doctor_operational_observability_lines(*, repo_root: Path, status: object | None) -> list[str]:
    lines: list[str] = []
    latest_report = latest_upgrade_report(repo_root=repo_root)
    if latest_report is not None:
        report_path, report = latest_report
        report_status = str(report.get("status") or "unknown").strip()
        finished_at = str(report.get("finished_at") or "").strip()
        lines.append(
            "Last upgrade: "
            f"{report_status}"
            + (f" at {finished_at}" if finished_at else "")
            + f" (report: {repo_relative_path(repo_root=repo_root, path=report_path)})"
        )
        dashboard = report.get("dashboard_refresh")
        if isinstance(dashboard, Mapping):
            mode = str(dashboard.get("mode") or "unknown").strip()
            fresh = "yes" if bool(dashboard.get("fresh") or dashboard.get("success")) else "no"
            timed_out = "yes" if bool(dashboard.get("timeout_detected")) else "no"
            lines.append(f"Last upgrade dashboard refresh: mode={mode}; fresh={fresh}; timeout_detected={timed_out}")
    if status is not None:
        rollback_target = str(getattr(status, "last_known_good_version", "") or "").strip()
        if rollback_target:
            lines.append(f"Rollback target: {rollback_target}")
    lock_summary = lock_hygiene_summary(repo_root=repo_root)
    if lock_summary.zero_byte_files >= LOCK_NOTE_THRESHOLD:
        lines.append(
            "Lock note: "
            f"{lock_summary.zero_byte_files} zero-byte lock placeholders exist under .odylith/locks; "
            "run `./.odylith/bin/odylith doctor --repo-root . --repair` to compact stale placeholders."
        )
    return lines


def git_status_paths(*, repo_root: Path) -> list[str]:
    if not (repo_root / ".git").exists():
        return []
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain", "--untracked-files=all"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if completed.returncode != 0:
        return []
    paths: list[str] = []
    for raw_line in completed.stdout.splitlines():
        line = str(raw_line or "")
        if len(line) < 4:
            continue
        token = line[3:].strip().strip('"')
        if " -> " in token:
            token = token.split(" -> ", 1)[1].strip()
        if token:
            paths.append(token)
    return sorted(set(paths))
