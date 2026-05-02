"""Migrate legacy Casebook metadata into the v0.1.13 compact label contract."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from odylith.install.fs import atomic_write_text, display_path
from odylith.install.versioning import is_at_least, is_before, normalize_version
from odylith.runtime.common import casebook_metadata
from odylith.runtime.governance import sync_casebook_bug_index

MIGRATION_ID = "v0.1.13-casebook-compact-metadata"
MIGRATION_SCHEMA_VERSION = "odylith-casebook-metadata-migration.v1"
TARGET_VERSION = "0.1.13"
CASEBOOK_BUGS_RELATIVE_PATH = Path("odylith/casebook/bugs")
CASEBOOK_SURFACE_RELATIVE_PATH = Path("odylith/casebook/casebook.html")
_CASEBOOK_SURFACE_REQUIRED_PATHS = (
    Path("odylith/casebook/casebook.html"),
    Path("odylith/casebook/casebook-payload.v1.js"),
    Path("odylith/casebook/casebook-app.v1.js"),
)
_FIXED_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class CasebookMetadataMigrationInspection:
    """Read-only evidence used to plan the v0.1.13 Casebook migration."""

    migration_id: str
    previous_version: str
    target_version: str
    target_in_window: bool
    previous_requires_migration: bool
    source_paths_needing_migration: tuple[str, ...]
    generated_surface_violations: tuple[str, ...]
    ledger_exists: bool
    ledger_valid: bool
    ledger_stale_reason: str
    ledger_path: str
    planned_paths: tuple[str, ...]

    @property
    def verification_passed(self) -> bool:
        """Return whether the ledger and current Casebook state still verify."""
        return (
            self.ledger_valid
            and not self.source_paths_needing_migration
            and not self.generated_surface_violations
        )

    @property
    def migration_required(self) -> bool:
        """Return whether applying the migration would still write local state."""
        if not self.target_in_window:
            return False
        if self.source_paths_needing_migration or self.generated_surface_violations:
            return True
        return self.previous_requires_migration and not self.ledger_exists

    def as_dict(self) -> dict[str, Any]:
        """Return the inspection as a JSON-serializable payload."""
        return {
            "migration_id": self.migration_id,
            "previous_version": self.previous_version,
            "target_version": self.target_version,
            "target_in_window": self.target_in_window,
            "previous_requires_migration": self.previous_requires_migration,
            "source_paths_needing_migration": list(self.source_paths_needing_migration),
            "generated_surface_violations": list(self.generated_surface_violations),
            "ledger_exists": self.ledger_exists,
            "ledger_valid": self.ledger_valid,
            "ledger_stale_reason": self.ledger_stale_reason,
            "ledger_path": self.ledger_path,
            "planned_paths": list(self.planned_paths),
            "verification_passed": self.verification_passed,
            "migration_required": self.migration_required,
        }


@dataclass(frozen=True)
class CasebookMetadataMigrationResult:
    """Result payload for the v0.1.13 Casebook compact-label migration."""

    migration_id: str
    applied: bool
    previous_version: str
    target_version: str
    written_paths: tuple[str, ...] = ()
    removed_paths: tuple[str, ...] = ()
    skipped_reason: str = ""
    ledger_path: str = ""
    verification_result: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the migration result as a JSON-serializable payload."""
        return {
            "schema_version": MIGRATION_SCHEMA_VERSION,
            "migration_id": self.migration_id,
            "applied": bool(self.applied),
            "previous_version": self.previous_version,
            "target_version": self.target_version,
            "written_paths": list(self.written_paths),
            "removed_paths": list(self.removed_paths),
            "skipped_reason": self.skipped_reason,
            "ledger_path": self.ledger_path,
            "verification_result": dict(self.verification_result or {}),
        }


def _ledger_path(*, repo_root: Path) -> Path:
    return repo_root / ".odylith" / "state" / "migrations" / f"{MIGRATION_ID}.v1.json"


def _read_ledger(*, repo_root: Path) -> tuple[bool, str]:
    path = _ledger_path(repo_root=repo_root)
    if not path.is_file():
        return False, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"unreadable ledger: {exc.__class__.__name__}"
    if not isinstance(payload, Mapping):
        return False, "ledger payload is not an object"
    if str(payload.get("migration_id") or "").strip() != MIGRATION_ID:
        return False, "ledger migration_id mismatch"
    if str(payload.get("schema_version") or "").strip() != MIGRATION_SCHEMA_VERSION:
        return False, "ledger schema_version mismatch"
    verification = payload.get("verification_result")
    if not isinstance(verification, Mapping) or str(verification.get("status") or "").strip() != "passed":
        return False, "ledger verification_result did not pass"
    return True, ""


def _write_ledger(
    *,
    repo_root: Path,
    previous_version: str,
    target_version: str,
    written_paths: Iterable[str],
    removed_paths: Iterable[str],
    verification_result: Mapping[str, Any],
) -> str:
    path = _ledger_path(repo_root=repo_root)
    payload = {
        "schema_version": MIGRATION_SCHEMA_VERSION,
        "migration_id": MIGRATION_ID,
        "recorded_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "previous_version": previous_version,
        "target_version": target_version,
        "written_paths": list(written_paths),
        "removed_paths": list(removed_paths),
        "verification_result": dict(verification_result),
        "notes": (
            "v0.1.13 normalizes legacy Casebook Status, Fixed, and Type prose "
            "into compact labels and rerenders the Casebook dashboard payload."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return display_path(repo_root=repo_root, path=path)


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _casebook_path_fingerprints(*, repo_root: Path) -> dict[str, str]:
    roots = (
        repo_root / CASEBOOK_BUGS_RELATIVE_PATH,
        repo_root / "odylith" / "casebook",
    )
    fingerprints: dict[str, str] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                fingerprints[display_path(repo_root=repo_root, path=path)] = _file_digest(path)
    return fingerprints


def _changed_paths(before: Mapping[str, str], after: Mapping[str, str]) -> tuple[str, ...]:
    changed = sorted(path for path, content in after.items() if before.get(path) != content)
    return tuple(changed)


def _removed_paths(before: Mapping[str, str], after: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(sorted(path for path in before if path not in after))


def _planned_paths(*, repo_root: Path) -> tuple[str, ...]:
    paths = [
        *sync_casebook_bug_index.casebook_bug_metadata_migration_targets(repo_root=repo_root),
        repo_root / CASEBOOK_BUGS_RELATIVE_PATH / "INDEX.md",
        *[repo_root / token for token in _CASEBOOK_SURFACE_REQUIRED_PATHS],
        *sorted((repo_root / "odylith" / "casebook").glob("casebook-detail-shard-*.v1.js")),
        _ledger_path(repo_root=repo_root),
    ]
    return tuple(dict.fromkeys(display_path(repo_root=repo_root, path=path) for path in paths))


def _source_paths_needing_migration(*, repo_root: Path) -> tuple[str, ...]:
    return tuple(
        display_path(repo_root=repo_root, path=path)
        for path in sync_casebook_bug_index.casebook_bug_metadata_migration_targets(repo_root=repo_root)
    )


def _casebook_bug_source_exists(*, repo_root: Path) -> bool:
    root = repo_root / CASEBOOK_BUGS_RELATIVE_PATH
    return root.is_dir() and any(path.is_file() for path in root.rglob("*.md") if path.name != "INDEX.md")


def _generated_surface_violations(*, repo_root: Path) -> tuple[str, ...]:
    if not _casebook_bug_source_exists(repo_root=repo_root):
        return ()
    missing = [
        display_path(repo_root=repo_root, path=repo_root / path)
        for path in _CASEBOOK_SURFACE_REQUIRED_PATHS
        if not (repo_root / path).is_file()
    ]
    violations = [f"missing generated Casebook surface: {path}" for path in missing]
    casebook_root = repo_root / "odylith" / "casebook"
    payload_paths = [
        casebook_root / "casebook-payload.v1.js",
        *sorted(casebook_root.glob("casebook-detail-shard-*.v1.js")),
    ]
    for path in payload_paths:
        if not path.is_file():
            continue
        try:
            payloads = _json_payloads_from_js(path)
        except (OSError, UnicodeDecodeError) as exc:
            rel = display_path(repo_root=repo_root, path=path)
            violations.append(f"{rel}: unreadable generated Casebook surface: {exc.__class__.__name__}")
            continue
        for payload in payloads:
            violations.extend(_metadata_payload_violations(repo_root=repo_root, path=path, payload=payload))
    return tuple(dict.fromkeys(violations))


def _json_payloads_from_js(path: Path) -> tuple[dict[str, Any], ...]:
    text = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    payloads: list[dict[str, Any]] = []
    for match in re.finditer(r"\{", text):
        try:
            value, _end = decoder.raw_decode(text[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            payloads.append(value)
    return tuple(payloads)


def _walk_dicts(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _metadata_payload_violations(*, repo_root: Path, path: Path, payload: Mapping[str, Any]) -> tuple[str, ...]:
    violations: list[str] = []
    rel = display_path(repo_root=repo_root, path=path)
    for row in _walk_dicts(payload):
        fields = row.get("fields")
        if isinstance(fields, Mapping):
            status = str(fields.get("Status") or "").strip()
            fixed = str(fields.get("Fixed") or "").strip()
            bug_type = str(fields.get("Type") or "").strip()
            if status and not _status_is_compact(status):
                violations.append(f"{rel}: verbose Casebook Status {status!r}")
            if fixed and not _fixed_is_compact(fixed):
                violations.append(f"{rel}: verbose Casebook Fixed {fixed!r}")
            if bug_type and not _type_is_compact(bug_type):
                violations.append(f"{rel}: verbose Casebook Type {bug_type!r}")
        if ("bug_id" in row or "bug_key" in row) and "status" in row:
            status = str(row.get("status") or "").strip()
            if status and not _status_is_compact(status):
                violations.append(f"{rel}: verbose Casebook row status {status!r}")
    return tuple(violations)


def _status_is_compact(value: str) -> bool:
    return casebook_metadata.casebook_token_is_valid(value) and casebook_metadata.canonical_casebook_status(value) == value


def _fixed_is_compact(value: str) -> bool:
    return (
        _FIXED_DATE_RE.fullmatch(value) is not None
        or (
            casebook_metadata.casebook_token_is_valid(value)
            and casebook_metadata.canonical_casebook_fixed(value) == value
        )
    )


def _type_is_compact(value: str) -> bool:
    return (
        casebook_metadata.casebook_token_is_valid(value)
        and casebook_metadata.canonical_casebook_display_type(value) == value
    )


def inspect_casebook_compact_metadata_migration(
    *,
    repo_root: str | Path,
    previous_version: str = "",
    target_version: str = "",
) -> CasebookMetadataMigrationInspection:
    """Inspect the v0.1.13 Casebook metadata migration state without writing."""
    root = Path(repo_root).expanduser().resolve()
    previous = normalize_version(previous_version)
    target = normalize_version(target_version)
    ledger_valid, ledger_stale_reason = _read_ledger(repo_root=root)
    ledger = _ledger_path(repo_root=root)
    return CasebookMetadataMigrationInspection(
        migration_id=MIGRATION_ID,
        previous_version=previous,
        target_version=target,
        target_in_window=is_at_least(target, TARGET_VERSION),
        previous_requires_migration=not previous or is_before(previous, TARGET_VERSION),
        source_paths_needing_migration=_source_paths_needing_migration(repo_root=root),
        generated_surface_violations=_generated_surface_violations(repo_root=root),
        ledger_exists=ledger.is_file(),
        ledger_valid=ledger_valid,
        ledger_stale_reason="" if ledger_valid or not ledger.is_file() else ledger_stale_reason,
        ledger_path=display_path(repo_root=root, path=ledger),
        planned_paths=_planned_paths(repo_root=root),
    )


def casebook_compact_metadata_decision_state(
    *,
    repo_scenario: str,
    inspection: CasebookMetadataMigrationInspection,
) -> tuple[str, str]:
    """Return the migration-runtime state and reason for the inspection."""
    scenario = str(repo_scenario or "").strip()
    if scenario == "legacy_odyssey":
        if inspection.target_in_window:
            return "selected", "Casebook compact metadata migration runs after the legacy root migration"
        return "skipped", "target version is not in target window for the v0.1.13 Casebook metadata migration"
    if scenario == "detached_source_local":
        return "blocked", "release migrations are blocked while the product repo is in detached source-local posture"
    if scenario == "product_repo_pinned_dogfood":
        return (
            "skipped",
            "product repo Casebook source truth is validated by maintainer release gates, not consumer migration apply",
        )
    if not inspection.target_in_window:
        return "skipped", "target version is not in target window for the v0.1.13 Casebook metadata migration"
    if inspection.ledger_exists and not inspection.ledger_valid:
        return "ledger_stale", f"migration ledger is stale: {inspection.ledger_stale_reason}"
    if inspection.verification_passed:
        return "skipped", "ledger and verification already satisfy the v0.1.13 Casebook metadata migration"
    if inspection.migration_required:
        return "selected", "legacy Casebook metadata or stale generated Casebook surfaces require automatic migration"
    return "skipped", "migration predicates do not require local Casebook metadata changes"


def migrate_casebook_compact_metadata(
    *,
    repo_root: str | Path,
    previous_version: str = "",
    target_version: str = "",
) -> CasebookMetadataMigrationResult:
    """Apply the v0.1.13 Casebook compact metadata migration when in scope."""
    root = Path(repo_root).expanduser().resolve()
    previous = normalize_version(previous_version)
    target = normalize_version(target_version)
    inspection = inspect_casebook_compact_metadata_migration(
        repo_root=root,
        previous_version=previous,
        target_version=target,
    )
    if not inspection.target_in_window:
        return CasebookMetadataMigrationResult(
            migration_id=MIGRATION_ID,
            applied=False,
            previous_version=previous,
            target_version=target,
            skipped_reason="target_not_in_v0_1_13_migration_window",
            ledger_path=inspection.ledger_path,
        )
    if inspection.verification_passed:
        return CasebookMetadataMigrationResult(
            migration_id=MIGRATION_ID,
            applied=False,
            previous_version=previous,
            target_version=target,
            skipped_reason="ledger_and_casebook_metadata_already_verify",
            ledger_path=inspection.ledger_path,
            verification_result={"status": "passed", "mode": "already_verified"},
        )
    before = _casebook_path_fingerprints(repo_root=root)
    sync_casebook_bug_index.sync_casebook_bug_index(repo_root=root, migrate_bug_ids=True)
    from odylith.runtime.surfaces import render_casebook_dashboard

    render_rc = render_casebook_dashboard.main(
        [
            "--repo-root",
            str(root),
            "--output",
            CASEBOOK_SURFACE_RELATIVE_PATH.as_posix(),
            "--runtime-mode",
            "standalone",
        ]
    )
    if render_rc != 0:
        raise RuntimeError("Casebook dashboard render failed during v0.1.13 Casebook metadata migration")
    after = _casebook_path_fingerprints(repo_root=root)
    verification = inspect_casebook_compact_metadata_migration(
        repo_root=root,
        previous_version=previous,
        target_version=target,
    )
    verification_result = {
        "status": "passed" if not verification.source_paths_needing_migration and not verification.generated_surface_violations else "failed",
        "source_paths_needing_migration": list(verification.source_paths_needing_migration),
        "generated_surface_violations": list(verification.generated_surface_violations),
    }
    if verification_result["status"] != "passed":
        raise RuntimeError("Casebook compact metadata migration did not verify after apply")
    written = _changed_paths(before, after)
    removed = _removed_paths(before, after)
    ledger_path = _write_ledger(
        repo_root=root,
        previous_version=previous,
        target_version=target,
        written_paths=written,
        removed_paths=removed,
        verification_result=verification_result,
    )
    return CasebookMetadataMigrationResult(
        migration_id=MIGRATION_ID,
        applied=True,
        previous_version=previous,
        target_version=target,
        written_paths=written,
        removed_paths=removed,
        ledger_path=ledger_path,
        verification_result=verification_result,
    )


def casebook_compact_metadata_migration_ledger_path(*, repo_root: str | Path) -> str:
    """Return the repo-relative ledger path for planning and doctor output."""
    root = Path(repo_root).expanduser().resolve()
    return display_path(repo_root=root, path=_ledger_path(repo_root=root))


__all__ = [
    "CASEBOOK_BUGS_RELATIVE_PATH",
    "MIGRATION_ID",
    "MIGRATION_SCHEMA_VERSION",
    "TARGET_VERSION",
    "CasebookMetadataMigrationInspection",
    "CasebookMetadataMigrationResult",
    "casebook_compact_metadata_decision_state",
    "casebook_compact_metadata_migration_ledger_path",
    "inspect_casebook_compact_metadata_migration",
    "migrate_casebook_compact_metadata",
]
