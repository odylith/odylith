"""Release migration coverage, fixture proof, and lifecycle bypass validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from odylith.install.destructive_write_scenarios import (
    destructive_write_fixture_matrix,
    destructive_write_scenarios,
    missing_destructive_write_proofs,
)
from odylith.install.migration_definitions import MigrationDefinition
from odylith.install.migration_observer import (
    SurfaceMigrationObserverReport,
    observe_surface_migration_needs,
)
from odylith.install.migration_runtime import registered_migrations
from odylith.install.versioning import normalize_version


@dataclass(frozen=True)
class ReleaseMigrationGateReport:
    """Release gate report for migration registry coverage."""

    ok: bool
    registered_migrations: tuple[MigrationDefinition, ...]
    covered_version_ranges: tuple[str, ...]
    fixture_matrix: dict[str, dict[str, bool]]
    destructive_write_matrix: dict[str, dict[str, bool]]
    surface_migration_observer: SurfaceMigrationObserverReport
    blocked_manual_migrations: tuple[str, ...]
    ungated_lifecycle_paths: tuple[str, ...]
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        """Return the report as a JSON-ready payload."""
        return {
            "schema_version": "odylith.release-migration-gate.v1",
            "ok": self.ok,
            "registered_migrations": [definition.as_dict() for definition in self.registered_migrations],
            "covered_version_ranges": list(self.covered_version_ranges),
            "fixture_matrix": dict(self.fixture_matrix),
            "destructive_write_scenarios": [scenario.as_dict() for scenario in destructive_write_scenarios()],
            "destructive_write_matrix": dict(self.destructive_write_matrix),
            "surface_migration_observer": self.surface_migration_observer.as_dict(),
            "blocked_manual_migrations": list(self.blocked_manual_migrations),
            "ungated_lifecycle_paths": list(self.ungated_lifecycle_paths),
            "notes": list(self.notes),
        }


def _release_manifest_paths(repo_root: Path) -> tuple[Path, ...]:
    return (
        repo_root / "dist" / "release-manifest.json",
        repo_root / ".odylith" / "cache" / "release-manifest.json",
    )


def _load_manifest_for_gate(repo_root: Path) -> dict[str, object]:
    for path in _release_manifest_paths(repo_root):
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, Mapping):
            return dict(payload)
    return {}


def _fixture_matrix(repo_root: Path, definitions: Sequence[MigrationDefinition]) -> dict[str, dict[str, bool]]:
    fixture_files = (
        repo_root / "tests" / "unit" / "install" / "test_migration_runtime.py",
        repo_root / "tests" / "unit" / "install" / "test_value_engine_migration.py",
        repo_root / "tests" / "integration" / "install" / "test_manager.py",
        repo_root / "tests" / "integration" / "install" / "test_lifecycle_simulator.py",
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in fixture_files if path.is_file())
    matrix: dict[str, dict[str, bool]] = {}
    for definition in definitions:
        matrix[definition.migration_id] = {
            fixture: f"{definition.migration_id}:{fixture}" in combined
            for fixture in definition.coverage_fixtures
        }
    return matrix


def _ungated_lifecycle_paths(repo_root: Path) -> tuple[str, ...]:
    banned = (
        "migrate_visible_intervention_value_engine",
        "migrate_legacy_install_if_needed",
        "visible_intervention_value_engine_migration_pending",
        "visible_intervention_value_engine_migration_ledger_path",
        "value_engine_migration_payload",
    )
    allowed = {
        Path("src/odylith/install/migration_runtime.py"),
        Path("src/odylith/install/value_engine_migration.py"),
        Path("src/odylith/install/legacy_install_migration.py"),
    }
    findings: list[str] = []
    for relative in (
        Path("src/odylith/install/manager.py"),
        Path("src/odylith/install/bootstrap_assets.py"),
        Path("src/odylith/cli.py"),
    ):
        path = repo_root / relative
        if relative in allowed or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for token in banned:
            if token in text:
                findings.append(f"{relative.as_posix()} references {token}")
    return tuple(findings)


def validate_release_migration_gate(
    *,
    repo_root: str | Path,
    target_version: str = "",
    release_manifest: Mapping[str, object] | None = None,
    changed_paths: Sequence[str] | None = None,
    base_ref: str = "",
) -> ReleaseMigrationGateReport:
    """Validate that release migration requirements are registered and fixture-proven."""
    root = Path(repo_root).expanduser().resolve()
    definitions = registered_migrations()
    manifest = dict(release_manifest if release_manifest is not None else _load_manifest_for_gate(root))
    observer_target = str(target_version or manifest.get("version") or manifest.get("tag") or "")
    surface_observer = observe_surface_migration_needs(
        repo_root=root,
        target_version=observer_target,
        changed_paths=changed_paths,
        base_ref=base_ref,
        require_release_scope=changed_paths is None,
    )
    blocked_manual: list[str] = []
    if surface_observer.scope_error:
        blocked_manual.append(surface_observer.scope_error)
    if bool(manifest.get("migration_required")):
        target = normalize_version(target_version or manifest.get("version") or manifest.get("tag"))
        if not any(definition.covers_manifest_target(target) for definition in definitions):
            blocked_manual.append(
                f"migration_required manifest for {target or 'unknown target'} has no registered migration definition"
            )
    matrix = _fixture_matrix(root, definitions)
    for migration_id, coverage in matrix.items():
        missing = [fixture for fixture, present in coverage.items() if not present]
        if missing:
            blocked_manual.append(f"{migration_id} fixture coverage missing: {', '.join(missing)}")
    destructive_matrix = destructive_write_fixture_matrix(repo_root=root)
    blocked_manual.extend(missing_destructive_write_proofs(repo_root=root))
    for need in surface_observer.needs:
        if need.need_id in surface_observer.blocked_need_ids:
            blocked_manual.append(f"{need.need_id} surface migration assessment incomplete: {need.governance_prompt}")
    ungated = _ungated_lifecycle_paths(root)
    covered_ranges = tuple(
        f"{definition.migration_id}: {definition.from_version_range} -> {definition.to_version_range}"
        for definition in definitions
    )
    notes = (
        "Release migration gate checks registry definitions, fixture coverage, and lifecycle bypasses.",
        "Destructive-write guardrails are tracked as first-class adoption-risk fixtures.",
        "Consumer-visible surface changes are observed and must have completed migration assessment records.",
        "Generated dashboard refresh is intentionally outside migration scope.",
    )
    return ReleaseMigrationGateReport(
        ok=not blocked_manual and not ungated and surface_observer.ok,
        registered_migrations=definitions,
        covered_version_ranges=covered_ranges,
        fixture_matrix=matrix,
        destructive_write_matrix=destructive_matrix,
        surface_migration_observer=surface_observer,
        blocked_manual_migrations=tuple(blocked_manual),
        ungated_lifecycle_paths=ungated,
        notes=notes,
    )
