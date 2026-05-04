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
_INSTALL_MANAGED_PREFIXES = (
    ".claude/",
    ".codex/",
    ".agents/",
    "odylith/agents-guidelines/",
    "odylith/runtime/source/",
    "odylith/skills/",
    "odylith/surfaces/",
)
_INSTALL_MANAGED_PATHS = {
    "AGENTS.md",
    "CLAUDE.md",
    "odylith/AGENTS.md",
    "odylith/CLAUDE.md",
    "odylith/README.md",
}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _normalize_repo_path_token(path: object) -> str:
    token = str(path).strip().replace("\\", "/")
    while token.startswith("./"):
        token = token[2:]
    return token


def _file_fingerprint(path: Path) -> tuple[int, str, int]:
    try:
        payload = path.read_bytes()
    except OSError:
        return 0, "", 0
    return len(payload), _sha256_bytes(payload), payload.count(b"\n")


def _generated_surface_category(path: str) -> str:
    rel = _normalize_repo_path_token(path)
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


def _normalized_changed_paths(paths: list[str] | tuple[str, ...]) -> list[str]:
    return sorted(
        {
            _normalize_repo_path_token(path)
            for path in paths
            if str(path).strip()
        }
    )


def _migration_result_paths(migration_results: object) -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    if not isinstance(migration_results, (list, tuple)):
        return rows
    for raw_result in migration_results:
        if not isinstance(raw_result, Mapping):
            continue
        migration_id = str(raw_result.get("migration_id") or "").strip()
        if not migration_id:
            continue
        written = _normalized_changed_paths(
            tuple(str(path) for path in raw_result.get("written_paths", ()) or ())
        )
        removed = _normalized_changed_paths(
            tuple(str(path) for path in raw_result.get("removed_paths", ()) or ())
        )
        if not written and not removed:
            continue
        rows[migration_id] = {
            "written_paths": written,
            "removed_paths": removed,
            "path_count": len(set(written) | set(removed)),
        }
    return rows


def _is_source_truth_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _SURFACE_SOURCE_PREFIXES)


def _is_install_managed_path(path: str) -> bool:
    return path in _INSTALL_MANAGED_PATHS or any(path.startswith(prefix) for prefix in _INSTALL_MANAGED_PREFIXES)


def _path_review_category(path: str, *, migration_paths: set[str], generated_paths: set[str]) -> str:
    if path in migration_paths:
        return "required_migration"
    if path in generated_paths or _generated_surface_category(path):
        return "generated_refresh"
    if path == GENERATED_CHANGE_MANIFEST_REL or path.startswith(".odylith/runtime/logs/upgrade-"):
        return "upgrade_report"
    if path.startswith(".odylith/"):
        return "runtime_state"
    if _is_source_truth_path(path):
        return "source_truth"
    if _is_install_managed_path(path):
        return "install_managed_asset"
    return "manual_review_required"


def upgrade_change_review_payload(
    *,
    pre_existing_dirty_paths: list[str] | tuple[str, ...],
    post_upgrade_dirty_paths: list[str] | tuple[str, ...],
    migration_results: object,
    generated_change_manifest: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Classify upgrade dirt so generated refresh churn is reviewable."""
    pre_existing = _normalized_changed_paths(pre_existing_dirty_paths)
    post_upgrade = _normalized_changed_paths(post_upgrade_dirty_paths)
    newly_dirty = sorted(set(post_upgrade) - set(pre_existing))
    migrations = _migration_result_paths(migration_results)
    migration_paths = {
        path
        for migration in migrations.values()
        for path in (
            *(str(item) for item in migration.get("written_paths", ()) or ()),
            *(str(item) for item in migration.get("removed_paths", ()) or ()),
        )
    }
    generated_entries = (
        tuple(generated_change_manifest.get("entries", ()) or ())
        if isinstance(generated_change_manifest, Mapping)
        else ()
    )
    generated_paths = {
        _normalize_repo_path_token(entry.get("path") or "")
        for entry in generated_entries
        if isinstance(entry, Mapping) and str(entry.get("path") or "").strip()
    }
    generated_by_category: dict[str, list[str]] = {}
    for entry in generated_entries:
        if not isinstance(entry, Mapping):
            continue
        category = str(entry.get("category") or "generated_refresh").strip() or "generated_refresh"
        path = _normalize_repo_path_token(entry.get("path") or "")
        if path:
            generated_by_category.setdefault(category, []).append(path)
    categories: dict[str, list[str]] = {}
    for path in post_upgrade:
        category = _path_review_category(path, migration_paths=migration_paths, generated_paths=generated_paths)
        categories.setdefault(category, []).append(path)
    for paths in categories.values():
        paths.sort()
    pre_existing_touched_by_migrations = sorted(set(pre_existing) & migration_paths)
    manual_review_paths = sorted(categories.get("manual_review_required", []))
    return {
        "schema": "odylith.upgrade-change-review.v1",
        "review_note": (
            "Separates required migration writes, generated refresh churn, install-managed assets, "
            "runtime/report state, and paths requiring manual review."
        ),
        "pre_existing_dirty_paths": pre_existing,
        "post_upgrade_dirty_paths": post_upgrade,
        "newly_dirty_paths": newly_dirty,
        "pre_existing_dirty_touched_by_migrations": pre_existing_touched_by_migrations,
        "required_migrations": migrations,
        "generated_refreshes": {
            "path_count": len(generated_paths),
            "by_category": {category: sorted(paths) for category, paths in sorted(generated_by_category.items())},
            "manifest_path": str(
                generated_change_manifest.get("path") or GENERATED_CHANGE_MANIFEST_REL
            )
            if isinstance(generated_change_manifest, Mapping)
            else GENERATED_CHANGE_MANIFEST_REL,
            "content_fingerprint": str(generated_change_manifest.get("content_fingerprint") or "")
            if isinstance(generated_change_manifest, Mapping)
            else "",
        },
        "categories": {category: {"count": len(paths), "paths": paths} for category, paths in sorted(categories.items())},
        "manual_review_required": {
            "count": len(manual_review_paths),
            "paths": manual_review_paths,
        },
    }


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
    normalized_paths = {_normalize_repo_path_token(path) for path in changed_paths if str(path).strip()}
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
        change_review = report.get("change_review")
        if isinstance(change_review, Mapping):
            categories = change_review.get("categories")
            required = change_review.get("required_migrations")
            manual = change_review.get("manual_review_required")
            migration_path_count = 0
            if isinstance(required, Mapping):
                for row in required.values():
                    if isinstance(row, Mapping):
                        try:
                            migration_path_count += int(row.get("path_count") or 0)
                        except (TypeError, ValueError):
                            continue
            install_managed_count = 0
            if isinstance(categories, Mapping) and isinstance(categories.get("install_managed_asset"), Mapping):
                try:
                    install_managed_count = int(categories["install_managed_asset"].get("count") or 0)
                except (TypeError, ValueError):
                    install_managed_count = 0
            try:
                manual_count = int(manual.get("count") or 0) if isinstance(manual, Mapping) else 0
            except (TypeError, ValueError):
                manual_count = 0
            lines.append(
                "Last upgrade change review: "
                f"required_migration_paths={migration_path_count}; "
                f"install_managed_assets={install_managed_count}; "
                f"manual_review_required={manual_count}"
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
