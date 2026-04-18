"""Migration helpers for the v0.1.11 visible-intervention value engine cutover."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.install.fs import atomic_write_text, display_path
from odylith.install.managed_runtime import managed_runtime_site_packages_roots
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


def _normalize_version(value: str) -> str:
    """Normalize version tokens so callers may pass `v0.x.y` or `0.x.y`."""
    return str(value or "").strip().lstrip("v")


def _version_key(value: str) -> tuple[int, int, int, str]:
    """Build a sortable key for semantic-ish version comparisons."""
    token = _normalize_version(value)
    parts = token.split(".", 2)
    if len(parts) < 3:
        return (-1, -1, -1, token)
    try:
        major = int(parts[0])
        minor = int(parts[1])
        patch_raw = parts[2]
        patch_token = "".join(ch for ch in patch_raw if ch.isdigit())
        suffix = patch_raw[len(patch_token):]
        return (major, minor, int(patch_token or 0), suffix)
    except ValueError:
        return (-1, -1, -1, token)


def _is_at_least(value: str, baseline: str) -> bool:
    """Return whether one normalized version is at least the baseline."""
    return _version_key(value) >= _version_key(baseline)


def _is_before(value: str, baseline: str) -> bool:
    """Return whether one normalized version is strictly before the baseline."""
    return bool(_normalize_version(value)) and _version_key(value) < _version_key(baseline)


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


def _should_apply_migration(
    *,
    previous_version: str,
    target_version: str,
    source_artifacts: Sequence[Path],
    runtime_artifacts: Sequence[Path],
    ledger_exists: bool,
) -> bool:
    """Return whether the migration still needs to run for this install posture."""
    return _is_at_least(target_version, TARGET_VERSION) and (
        not previous_version
        or _is_before(previous_version, TARGET_VERSION)
        or _artifact_exists(source_artifacts)
        or _artifact_exists(runtime_artifacts)
        or not ledger_exists
    )


def migrate_visible_intervention_value_engine(
    *,
    repo_root: str | Path,
    previous_version: str = "",
    target_version: str = "",
    runtime_root: str | Path | None = None,
) -> ValueEngineMigrationResult:
    """Apply the v0.1.11 value-engine migration when the install is in scope."""
    root = Path(repo_root).expanduser().resolve()
    target = _normalize_version(target_version)
    previous = _normalize_version(previous_version)
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


__all__ = [
    "MIGRATION_ID",
    "MIGRATION_SCHEMA_VERSION",
    "TARGET_VERSION",
    "VALUE_CORPUS_RELATIVE_PATH",
    "ValueEngineMigrationResult",
    "migrate_visible_intervention_value_engine",
]
