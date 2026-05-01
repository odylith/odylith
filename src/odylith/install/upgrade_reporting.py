"""Upgrade transaction reports and doctor observability lines."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Mapping

from odylith.install.lock_hygiene import LOCK_NOTE_THRESHOLD, lock_hygiene_summary

GENERATED_CHANGE_MANIFEST_REL = "odylith/upgrade-generated-changes.v1.json"

_SURFACE_SOURCE_PREFIXES = (
    "odylith/atlas/source/",
    "odylith/casebook/bugs/",
    "odylith/radar/source/",
    "odylith/registry/source/",
    "odylith/technical-plans/",
)

_DASHBOARD_MANIFEST_KEYS = (
    "surfaces",
    "mode",
    "reason",
    "command",
    "returncode",
    "success",
    "fresh",
    "timeout_detected",
    "message",
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_fingerprint(path: Path) -> tuple[int, str, int]:
    try:
        payload = path.read_bytes()
    except OSError:
        return 0, "", 0
    return len(payload), _sha256_bytes(payload), payload.count(b"\n")


def _generated_surface_category(path: str) -> str:
    rel = path.strip().replace("\\", "/").lstrip("./")
    if not rel or rel == GENERATED_CHANGE_MANIFEST_REL:
        return ""
    if rel.startswith(_SURFACE_SOURCE_PREFIXES):
        return ""
    if rel.startswith("src/odylith/bundle/assets/odylith/"):
        return "bundle_surface_mirror"
    if rel == "odylith/index.html" or rel.startswith("odylith/tooling-"):
        return "tooling_shell"
    for surface in ("atlas", "casebook", "compass", "radar", "registry"):
        if rel.startswith(f"odylith/{surface}/"):
            return surface
    return ""


def _compact_dashboard_details(details: Mapping[str, object] | None) -> dict[str, object]:
    if not details:
        return {}
    return {key: json_ready(details[key]) for key in _DASHBOARD_MANIFEST_KEYS if key in details}


def generated_change_manifest_payload(
    *,
    repo_root: Path,
    changed_paths: list[str] | tuple[str, ...],
    active_version: str,
    previous_version: str,
    pinned_version: str,
    dashboard_details: Mapping[str, object] | None = None,
) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    other_changed_paths: list[str] = []
    normalized_paths = {
        str(path).strip().replace("\\", "/").lstrip("./")
        for path in changed_paths
        if str(path).strip()
    }
    for raw_path in sorted(normalized_paths):
        if raw_path == GENERATED_CHANGE_MANIFEST_REL:
            continue
        category = _generated_surface_category(raw_path)
        if not category:
            other_changed_paths.append(raw_path)
            continue
        absolute_path = repo_root / raw_path
        exists = absolute_path.exists()
        byte_count, sha256, line_count = _file_fingerprint(absolute_path) if exists else (0, "", 0)
        entries.append(
            {
                "path": raw_path,
                "category": category,
                "state": "present" if exists else "deleted",
                "byte_count": byte_count,
                "line_count": line_count,
                "sha256": sha256,
            }
        )
    by_category: dict[str, dict[str, int]] = {}
    for entry in entries:
        category = str(entry["category"])
        bucket = by_category.setdefault(category, {"count": 0, "bytes": 0})
        bucket["count"] += 1
        bucket["bytes"] += int(entry["byte_count"])
    fingerprint_source = {
        "entries": entries,
        "by_category": by_category,
        "dashboard_refresh": _compact_dashboard_details(dashboard_details),
    }
    fingerprint = _sha256_bytes(json.dumps(fingerprint_source, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return {
        "schema": "odylith.generated-change-manifest.v1",
        "review_note": (
            "Compact review manifest for generated Odylith surface churn. "
            "Reviewers can inspect these hashes and counts before opening large generated JS/JSON diffs."
        ),
        "active_version": active_version,
        "previous_version": previous_version,
        "pinned_version": pinned_version,
        "manifest_path": GENERATED_CHANGE_MANIFEST_REL,
        "content_fingerprint": fingerprint,
        "generated_changed_count": len(entries),
        "generated_changed_bytes": sum(int(entry["byte_count"]) for entry in entries),
        "by_category": by_category,
        "entries": entries,
        "other_changed_paths": other_changed_paths,
        "dashboard_refresh": _compact_dashboard_details(dashboard_details),
    }


def write_generated_change_manifest(
    *,
    repo_root: Path,
    changed_paths: list[str] | tuple[str, ...],
    active_version: str,
    previous_version: str,
    pinned_version: str,
    dashboard_details: Mapping[str, object] | None = None,
) -> dict[str, object]:
    payload = generated_change_manifest_payload(
        repo_root=repo_root,
        changed_paths=changed_paths,
        active_version=active_version,
        previous_version=previous_version,
        pinned_version=pinned_version,
        dashboard_details=dashboard_details,
    )
    manifest_path = repo_root / GENERATED_CHANGE_MANIFEST_REL
    if int(payload["generated_changed_count"]) == 0:
        return {
            "path": GENERATED_CHANGE_MANIFEST_REL,
            "written": False,
            "changed": False,
            "reason": "no generated surface changes",
            "generated_changed_count": 0,
            "generated_changed_bytes": 0,
            "content_fingerprint": payload["content_fingerprint"],
        }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    previous = manifest_path.read_text(encoding="utf-8") if manifest_path.exists() else ""
    changed = previous != rendered
    if changed:
        manifest_path.write_text(rendered, encoding="utf-8")
    return {
        "path": GENERATED_CHANGE_MANIFEST_REL,
        "written": True,
        "changed": changed,
        "generated_changed_count": payload["generated_changed_count"],
        "generated_changed_bytes": payload["generated_changed_bytes"],
        "content_fingerprint": payload["content_fingerprint"],
        "by_category": payload["by_category"],
        "entries": payload["entries"],
    }


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
        generated_manifest = report.get("generated_change_manifest")
        if isinstance(generated_manifest, Mapping):
            manifest_path = str(generated_manifest.get("path") or "").strip()
            try:
                generated_count = int(generated_manifest.get("generated_changed_count") or 0)
            except (TypeError, ValueError):
                generated_count = 0
            fingerprint = str(generated_manifest.get("content_fingerprint") or "").strip()
            if manifest_path and generated_count:
                lines.append(
                    "Last upgrade generated changes: "
                    f"{generated_count} generated path(s); manifest: {manifest_path}; "
                    f"fingerprint={fingerprint[:12]}"
                )
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
