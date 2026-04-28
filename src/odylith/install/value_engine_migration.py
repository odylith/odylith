"""Migration helpers for the v0.1.11 visible-intervention value engine cutover."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.install.fs import atomic_write_text, display_path
from odylith.install.managed_runtime import managed_runtime_site_packages_roots
from odylith.install.versioning import is_at_least, is_before, normalize_version
from odylith.runtime.common.product_assets import bundled_product_root

MIGRATION_ID = "v0.1.11-visible-intervention-value-engine"
MIGRATION_SCHEMA_VERSION = "odylith-value-engine-migration.v1"
TARGET_VERSION = "0.1.11"
VALUE_CORPUS_RELATIVE_PATH = Path("odylith/runtime/source/intervention-value-adjudication-corpus.v1.json")
_OLD_SIGNAL_RANKER_SOURCE_PATHS: tuple[Path, ...] = (
    Path("odylith/runtime/source/intervention-signal-ranker-corpus.v1.json"),
    Path("odylith/runtime/source/intervention-signal-ranker-calibration.v1.json"),
    Path("odylith/runtime/source/intervention-signal-ranker-report.v1.json"),
    Path("odylith/runtime/source/intervention-signal-ranker-report.v1.md"),
    Path("odylith/runtime/source/intervention_signal_ranker_corpus.v1.json"),
    Path("odylith/runtime/source/intervention_signal_ranker_calibration.v1.json"),
    Path("odylith/runtime/source/intervention_signal_ranker_report.v1.json"),
    Path("odylith/runtime/source/intervention_signal_ranker_report.v1.md"),
)
_OLD_RUNTIME_PACKAGE_RELATIVE_PATHS: tuple[Path, ...] = (
    Path("odylith/runtime/intervention_engine/signal_ranker.py"),
    Path("odylith/runtime/intervention_engine/calibration/intervention_signal_ranker_corpus.v1.json"),
    Path("odylith/runtime/intervention_engine/calibration/intervention_signal_ranker_calibration.v1.json"),
    Path("odylith/runtime/intervention_engine/calibration"),
)


@dataclass(frozen=True)
class ValueEngineMigrationResult:
    """Result payload for the visible-intervention value-engine migration."""

    migration_id: str
    applied: bool
    previous_version: str
    target_version: str
    removed_paths: tuple[str, ...] = ()
    written_paths: tuple[str, ...] = ()
    skipped_reason: str = ""
    ledger_path: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return the migration result as a JSON-serializable payload."""
        return {
            "schema_version": MIGRATION_SCHEMA_VERSION,
            "migration_id": self.migration_id,
            "applied": bool(self.applied),
            "previous_version": self.previous_version,
            "target_version": self.target_version,
            "removed_paths": list(self.removed_paths),
            "written_paths": list(self.written_paths),
            "skipped_reason": self.skipped_reason,
            "ledger_path": self.ledger_path,
        }


@dataclass(frozen=True)
class ValueEngineMigrationInspection:
    """Evidence used by the migration runtime to plan the value-engine cutover."""

    migration_id: str
    previous_version: str
    target_version: str
    target_in_window: bool
    previous_requires_migration: bool
    legacy_artifacts_present: bool
    value_corpus_present: bool
    ledger_exists: bool
    ledger_valid: bool
    ledger_stale_reason: str
    ledger_path: str
    planned_paths: tuple[str, ...]

    @property
    def verification_passed(self) -> bool:
        """Return whether the recorded migration still matches the desired state."""
        if not self.ledger_valid:
            return False
        if self.target_in_window and not self.value_corpus_present:
            return False
        return not self.legacy_artifacts_present

    def as_dict(self) -> dict[str, Any]:
        """Return the inspection as a JSON-serializable payload."""
        return {
            "migration_id": self.migration_id,
            "previous_version": self.previous_version,
            "target_version": self.target_version,
            "target_in_window": self.target_in_window,
            "previous_requires_migration": self.previous_requires_migration,
            "legacy_artifacts_present": self.legacy_artifacts_present,
            "value_corpus_present": self.value_corpus_present,
            "ledger_exists": self.ledger_exists,
            "ledger_valid": self.ledger_valid,
            "ledger_stale_reason": self.ledger_stale_reason,
            "ledger_path": self.ledger_path,
            "planned_paths": list(self.planned_paths),
            "verification_passed": self.verification_passed,
        }


def _ledger_path(*, repo_root: Path) -> Path:
    """Return the ledger path that records this migration's completion."""
    return repo_root / ".odylith" / "state" / "migrations" / f"{MIGRATION_ID}.v1.json"


def _old_source_artifact_paths(*, repo_root: Path) -> list[Path]:
    """Return the legacy source artifacts removed by this migration."""
    return [repo_root / relative_path for relative_path in _OLD_SIGNAL_RANKER_SOURCE_PATHS]

def _old_runtime_artifact_paths(*, runtime_root: Path | None) -> list[Path]:
    """Return the legacy runtime artifacts removed by this migration."""
    paths: list[Path] = []
    for site_root in managed_runtime_site_packages_roots(runtime_root):
        paths.extend(site_root / relative_path for relative_path in _OLD_RUNTIME_PACKAGE_RELATIVE_PATHS)
    return paths


def _artifact_exists(paths: Sequence[Path]) -> bool:
    """Return whether any migration target artifact still exists."""
    return any(path.exists() for path in paths)


def _value_corpus_source() -> Path:
    """Return the bundled replacement corpus shipped with the product."""
    return bundled_product_root() / "runtime" / "source" / VALUE_CORPUS_RELATIVE_PATH.name


def _copy_value_corpus(*, repo_root: Path) -> tuple[str, ...]:
    """Copy the bundled value corpus into the repo when it changed."""
    source_path = _value_corpus_source()
    if not source_path.is_file():
        return ()
    target_path = repo_root / VALUE_CORPUS_RELATIVE_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    source_text = source_path.read_text(encoding="utf-8")
    current_text = target_path.read_text(encoding="utf-8") if target_path.is_file() else ""
    if current_text == source_text:
        return ()
    atomic_write_text(target_path, source_text, encoding="utf-8")
    return (display_path(repo_root=repo_root, path=target_path),)


def _remove_paths(*, repo_root: Path, paths: Sequence[Path]) -> tuple[str, ...]:
    """Remove legacy files and directories, returning the removed display paths."""
    removed: list[str] = []
    for path in paths:
        if path.is_symlink() or path.is_file():
            path.unlink()
            removed.append(display_path(repo_root=repo_root, path=path))
        elif path.is_dir():
            for child in sorted(path.rglob("*"), key=lambda item: len(item.parts), reverse=True):
                if child.is_symlink() or child.is_file():
                    child.unlink()
                    removed.append(display_path(repo_root=repo_root, path=child))
                elif child.is_dir():
                    child.rmdir()
            path.rmdir()
            removed.append(display_path(repo_root=repo_root, path=path))
    return tuple(removed)


def _write_ledger(*, repo_root: Path, payload: Mapping[str, Any]) -> str:
    """Write the migration ledger with the current UTC timestamp."""
    path = _ledger_path(repo_root=repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = dict(payload)
    normalized["recorded_utc"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    atomic_write_text(path, json.dumps(normalized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return display_path(repo_root=repo_root, path=path)


def _read_ledger(*, repo_root: Path) -> tuple[bool, str]:
    """Return whether the ledger is parseable and belongs to this migration."""
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
    return True, ""


def _planned_paths(*, repo_root: Path, runtime_root: Path | None) -> tuple[str, ...]:
    """Return every path the value-engine migration may inspect or mutate."""
    paths = [
        _ledger_path(repo_root=repo_root),
        repo_root / VALUE_CORPUS_RELATIVE_PATH,
        *_old_source_artifact_paths(repo_root=repo_root),
        *_old_runtime_artifact_paths(runtime_root=runtime_root),
    ]
    return tuple(dict.fromkeys(display_path(repo_root=repo_root, path=path) for path in paths))


def _should_apply_migration(
    *,
    previous_version: str,
    target_version: str,
    source_artifacts: Sequence[Path],
    runtime_artifacts: Sequence[Path],
    ledger_exists: bool,
) -> bool:
    """Return whether the migration still needs to run for this install posture."""
    if not is_at_least(target_version, TARGET_VERSION):
        return False
    if _artifact_exists(source_artifacts) or _artifact_exists(runtime_artifacts):
        return True
    if ledger_exists:
        return False
    return not previous_version or is_before(previous_version, TARGET_VERSION)


def migrate_visible_intervention_value_engine(
    *,
    repo_root: str | Path,
    previous_version: str = "",
    target_version: str = "",
    runtime_root: str | Path | None = None,
) -> ValueEngineMigrationResult:
    """Apply the v0.1.11 value-engine migration when the install is in scope."""
    root = Path(repo_root).expanduser().resolve()
    target = normalize_version(target_version)
    previous = normalize_version(previous_version)
    runtime = Path(runtime_root).expanduser().resolve() if runtime_root is not None else None
    source_artifacts = _old_source_artifact_paths(repo_root=root)
    runtime_artifacts = _old_runtime_artifact_paths(runtime_root=runtime)
    ledger_path = _ledger_path(repo_root=root)
    should_run = _should_apply_migration(
        previous_version=previous,
        target_version=target,
        source_artifacts=source_artifacts,
        runtime_artifacts=runtime_artifacts,
        ledger_exists=ledger_path.is_file(),
    )
    if not should_run:
        return ValueEngineMigrationResult(
            migration_id=MIGRATION_ID,
            applied=False,
            previous_version=previous,
            target_version=target,
            skipped_reason="target_not_in_v0_1_11_migration_window",
            ledger_path=display_path(repo_root=root, path=ledger_path),
        )
    removed = _remove_paths(repo_root=root, paths=source_artifacts + runtime_artifacts)
    written = _copy_value_corpus(repo_root=root)
    payload = {
        "schema_version": MIGRATION_SCHEMA_VERSION,
        "migration_id": MIGRATION_ID,
        "applied": True,
        "previous_version": previous,
        "target_version": target,
        "removed_paths": list(removed),
        "written_paths": list(written),
        "runtime_posture": "deterministic_utility_v1",
        "backward_compatibility": "cut_hard",
        "notes": (
            "v0.1.11 removes the block-first signal ranker and migrates installed state "
            "to the proposition-first visible intervention value engine."
        ),
    }
    ledger_path = _write_ledger(repo_root=root, payload=payload)
    return ValueEngineMigrationResult(
        migration_id=MIGRATION_ID,
        applied=True,
        previous_version=previous,
        target_version=target,
        removed_paths=removed,
        written_paths=written,
        ledger_path=ledger_path,
    )


def inspect_visible_intervention_value_engine_migration(
    *,
    repo_root: str | Path,
    previous_version: str = "",
    target_version: str = "",
    runtime_root: str | Path | None = None,
) -> ValueEngineMigrationInspection:
    """Inspect the v0.1.11 migration state without writing local state."""
    root = Path(repo_root).expanduser().resolve()
    target = normalize_version(target_version)
    previous = normalize_version(previous_version)
    runtime = Path(runtime_root).expanduser().resolve() if runtime_root is not None else None
    source_artifacts = _old_source_artifact_paths(repo_root=root)
    runtime_artifacts = _old_runtime_artifact_paths(runtime_root=runtime)
    ledger_path = _ledger_path(repo_root=root)
    ledger_valid, ledger_stale_reason = _read_ledger(repo_root=root)
    return ValueEngineMigrationInspection(
        migration_id=MIGRATION_ID,
        previous_version=previous,
        target_version=target,
        target_in_window=is_at_least(target, TARGET_VERSION),
        previous_requires_migration=not previous or is_before(previous, TARGET_VERSION),
        legacy_artifacts_present=_artifact_exists(source_artifacts) or _artifact_exists(runtime_artifacts),
        value_corpus_present=(root / VALUE_CORPUS_RELATIVE_PATH).is_file(),
        ledger_exists=ledger_path.is_file(),
        ledger_valid=ledger_valid,
        ledger_stale_reason="" if ledger_valid or not ledger_path.is_file() else ledger_stale_reason,
        ledger_path=display_path(repo_root=root, path=ledger_path),
        planned_paths=_planned_paths(repo_root=root, runtime_root=runtime),
    )


def record_visible_intervention_value_engine_migration_satisfied(
    *,
    repo_root: str | Path,
    previous_version: str = "",
    target_version: str = "",
    runtime_root: str | Path | None = None,
    repo_scenario: str = "",
    plan_fingerprint: str = "",
) -> ValueEngineMigrationResult:
    """Record a no-op ledger when the desired value-engine state is already present."""
    root = Path(repo_root).expanduser().resolve()
    target = normalize_version(target_version)
    previous = normalize_version(previous_version)
    inspection = inspect_visible_intervention_value_engine_migration(
        repo_root=root,
        previous_version=previous,
        target_version=target,
        runtime_root=runtime_root,
    )
    if not inspection.target_in_window:
        return ValueEngineMigrationResult(
            migration_id=MIGRATION_ID,
            applied=False,
            previous_version=previous,
            target_version=target,
            skipped_reason="target_not_in_v0_1_11_migration_window",
            ledger_path=inspection.ledger_path,
        )
    if inspection.legacy_artifacts_present:
        raise ValueError("cannot record value-engine migration as satisfied while legacy signal-ranker artifacts remain")
    if not inspection.value_corpus_present:
        raise ValueError("cannot record value-engine migration as satisfied before the value-engine corpus exists")
    payload = {
        "schema_version": MIGRATION_SCHEMA_VERSION,
        "migration_id": MIGRATION_ID,
        "applied": False,
        "satisfied_unrecorded": True,
        "previous_version": previous,
        "target_version": target,
        "repo_scenario": str(repo_scenario or "").strip(),
        "plan_fingerprint": str(plan_fingerprint or "").strip(),
        "removed_paths": [],
        "written_paths": [],
        "verification_result": {
            "status": "passed",
            "legacy_artifacts_present": False,
            "value_corpus_present": True,
        },
        "runtime_posture": "deterministic_utility_v1",
        "backward_compatibility": "cut_hard",
        "notes": "Desired value-engine migration state was already present; the migration runtime wrote the missing ledger.",
    }
    ledger_path = _write_ledger(repo_root=root, payload=payload)
    return ValueEngineMigrationResult(
        migration_id=MIGRATION_ID,
        applied=False,
        previous_version=previous,
        target_version=target,
        skipped_reason="satisfied_unrecorded_ledger_written",
        ledger_path=ledger_path,
    )


def visible_intervention_value_engine_migration_pending(
    *,
    repo_root: str | Path,
    previous_version: str = "",
    target_version: str = "",
    runtime_root: str | Path | None = None,
) -> bool:
    """Return whether the v0.1.11 migration would still write local state."""
    root = Path(repo_root).expanduser().resolve()
    target = normalize_version(target_version)
    previous = normalize_version(previous_version)
    runtime = Path(runtime_root).expanduser().resolve() if runtime_root is not None else None
    return _should_apply_migration(
        previous_version=previous,
        target_version=target,
        source_artifacts=_old_source_artifact_paths(repo_root=root),
        runtime_artifacts=_old_runtime_artifact_paths(runtime_root=runtime),
        ledger_exists=_ledger_path(repo_root=root).is_file(),
    )


def visible_intervention_value_engine_migration_ledger_path(*, repo_root: str | Path) -> str:
    """Return the repo-relative ledger path for dry-run and doctor reporting."""
    root = Path(repo_root).expanduser().resolve()
    return display_path(repo_root=root, path=_ledger_path(repo_root=root))


__all__ = [
    "MIGRATION_ID",
    "MIGRATION_SCHEMA_VERSION",
    "TARGET_VERSION",
    "VALUE_CORPUS_RELATIVE_PATH",
    "ValueEngineMigrationInspection",
    "ValueEngineMigrationResult",
    "inspect_visible_intervention_value_engine_migration",
    "migrate_visible_intervention_value_engine",
    "record_visible_intervention_value_engine_migration_satisfied",
    "visible_intervention_value_engine_migration_ledger_path",
    "visible_intervention_value_engine_migration_pending",
]
