"""Registry specs for release migrations known to the install runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from odylith.install.atlas_surface_migration import (
    MIGRATION_ID as ATLAS_SURFACE_MIGRATION_ID,
    TARGET_VERSION as ATLAS_SURFACE_TARGET_VERSION,
)
from odylith.install.casebook_metadata_migration import (
    MIGRATION_ID as CASEBOOK_METADATA_MIGRATION_ID,
    STATUS_FSM_MIGRATION_ID as CASEBOOK_STATUS_FSM_MIGRATION_ID,
    STATUS_FSM_TARGET_VERSION as CASEBOOK_STATUS_FSM_TARGET_VERSION,
    TARGET_VERSION as CASEBOOK_METADATA_TARGET_VERSION,
)
from odylith.install.legacy_install_migration import LEGACY_ROOT_MIGRATION_ID
from odylith.install.value_engine_migration import (
    MIGRATION_ID as VALUE_ENGINE_MIGRATION_ID,
    TARGET_VERSION as VALUE_ENGINE_TARGET_VERSION,
)

_REQUIRED_FIXTURES = (
    "dry_run",
    "apply",
    "rerun",
    "stale_ledger",
    "skipped_version",
    "historical_range",
)


@dataclass(frozen=True)
class MigrationDefinition:
    """Registered release migration contract."""

    migration_id: str
    introduced_version: str
    from_version_range: str
    to_version_range: str
    scenario_predicates: tuple[str, ...]
    required_manifest_fields: tuple[str, ...]
    write_set: tuple[str, ...]
    rollback_scope: str
    validation_commands: tuple[str, ...]
    automatic: bool = True
    coverage_fixtures: tuple[str, ...] = _REQUIRED_FIXTURES

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-ready definition payload."""
        return {
            "migration_id": self.migration_id,
            "introduced_version": self.introduced_version,
            "from_version_range": self.from_version_range,
            "to_version_range": self.to_version_range,
            "scenario_predicates": list(self.scenario_predicates),
            "required_manifest_fields": list(self.required_manifest_fields),
            "write_set": list(self.write_set),
            "rollback_scope": self.rollback_scope,
            "validation_commands": list(self.validation_commands),
            "automatic": self.automatic,
            "coverage_fixtures": list(self.coverage_fixtures),
        }


def registered_migration_specs() -> tuple[dict[str, Any], ...]:
    """Return constructor-ready migration registry specs."""
    return (
        {
            "migration_id": LEGACY_ROOT_MIGRATION_ID,
            "introduced_version": "0.1.12",
            "from_version_range": "legacy odyssey/.odyssey roots present",
            "to_version_range": "Odylith layout before runtime activation",
            "scenario_predicates": ("legacy_odyssey",),
            "required_manifest_fields": (),
            "write_set": (
                "odyssey/",
                ".odyssey/",
                "odylith/",
                ".odylith/",
                ".gitignore",
            ),
            "rollback_scope": "repo root rename/merge migration; recover through Git before runtime activation if interrupted",
            "validation_commands": (
                "PYTHONPATH=src python -m pytest -q tests/integration/install/test_manager.py -k legacy",
                "PYTHONPATH=src python -m pytest -q tests/unit/install/test_migration_runtime.py",
            ),
        },
        {
            "migration_id": VALUE_ENGINE_MIGRATION_ID,
            "introduced_version": VALUE_ENGINE_TARGET_VERSION,
            "from_version_range": "<0.1.11 or legacy signal-ranker artifacts present",
            "to_version_range": ">=0.1.11",
            "scenario_predicates": (
                "healthy_pinned_consumer",
                "already_current_consumer",
                "product_repo_pinned_dogfood",
                "release_marked_migration_required",
            ),
            "required_manifest_fields": ("migration_required", "repo_schema_version"),
            "write_set": (
                ".odylith/state/migrations/v0.1.11-visible-intervention-value-engine.v1.json",
                "odylith/runtime/source/intervention-value-adjudication-corpus.v1.json",
                "odylith/runtime/source/intervention-signal-ranker-*.json",
                ".odylith/runtime/versions/*/site-packages/odylith/runtime/intervention_engine/signal_ranker.py",
            ),
            "rollback_scope": "repo-local migration writes; runtime rollback remains owned by upgrade activation",
            "validation_commands": (
                "PYTHONPATH=src python -m pytest -q tests/unit/install/test_migration_runtime.py tests/unit/install/test_value_engine_migration.py",
                "PYTHONPATH=src python -m pytest -q tests/integration/install/test_manager.py tests/integration/install/test_lifecycle_simulator.py",
            ),
        },
        {
            "migration_id": CASEBOOK_METADATA_MIGRATION_ID,
            "introduced_version": CASEBOOK_METADATA_TARGET_VERSION,
            "from_version_range": "<0.1.13 or legacy verbose Casebook metadata present",
            "to_version_range": ">=0.1.13",
            "scenario_predicates": (
                "healthy_pinned_consumer",
                "already_current_consumer",
                "release_marked_migration_required",
                "generated_surface_stale_runtime_healthy",
            ),
            "required_manifest_fields": ("migration_required", "repo_schema_version"),
            "write_set": (
                "odylith/casebook/bugs/*.md",
                "odylith/casebook/bugs/INDEX.md",
                "odylith/casebook/casebook.html",
                "odylith/casebook/casebook-payload.v1.js",
                "odylith/casebook/casebook-app.v1.js",
                "odylith/casebook/casebook-detail-shard-*.v1.js",
                ".odylith/state/migrations/v0.1.13-casebook-compact-metadata.v1.json",
            ),
            "rollback_scope": "repo-local Casebook source and generated surface writes; recover through Git if interrupted",
            "validation_commands": (
                "PYTHONPATH=src python -m pytest -q tests/unit/install/test_casebook_metadata_migration.py tests/unit/install/test_migration_runtime.py",
                "PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_casebook_bug_index.py tests/unit/runtime/test_casebook_source_validation.py tests/unit/runtime/test_render_casebook_dashboard.py",
                "PYTHONPATH=src python -m pytest -q tests/integration/install/test_lifecycle_simulator.py::test_lifecycle_simulator_proves_historical_upgrades_to_0_1_13",
            ),
        },
        {
            "migration_id": CASEBOOK_STATUS_FSM_MIGRATION_ID,
            "introduced_version": CASEBOOK_STATUS_FSM_TARGET_VERSION,
            "from_version_range": "<0.1.14 or Casebook surface not rendered under the controlled status FSM",
            "to_version_range": ">=0.1.14",
            "scenario_predicates": (
                "healthy_pinned_consumer",
                "already_current_consumer",
                "release_marked_migration_required",
                "generated_surface_stale_runtime_healthy",
            ),
            "required_manifest_fields": ("migration_required", "repo_schema_version"),
            "write_set": (
                "odylith/casebook/bugs/*.md",
                "odylith/casebook/bugs/INDEX.md",
                "odylith/casebook/casebook.html",
                "odylith/casebook/casebook-payload.v1.js",
                "odylith/casebook/casebook-app.v1.js",
                "odylith/casebook/casebook-detail-shard-*.v1.js",
                ".odylith/state/migrations/v0.1.14-casebook-status-fsm.v1.json",
            ),
            "rollback_scope": "repo-local Casebook source and generated surface writes; recover through Git if interrupted",
            "validation_commands": (
                "PYTHONPATH=src python -m pytest -q tests/unit/install/test_casebook_metadata_migration.py tests/unit/install/test_migration_runtime.py",
                "PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_casebook_bug_index.py tests/unit/runtime/test_casebook_source_validation.py tests/unit/runtime/test_render_casebook_dashboard.py",
                "PYTHONPATH=src python -m pytest -q tests/integration/install/test_lifecycle_simulator.py::test_lifecycle_simulator_proves_historical_upgrades_to_0_1_14",
            ),
        },
        {
            "migration_id": ATLAS_SURFACE_MIGRATION_ID,
            "introduced_version": ATLAS_SURFACE_TARGET_VERSION,
            "from_version_range": "<0.1.14 or Atlas generated render surfaces not rendered under the current diagram style fingerprint",
            "to_version_range": ">=0.1.14",
            "scenario_predicates": (
                "healthy_pinned_consumer",
                "already_current_consumer",
                "release_marked_migration_required",
                "generated_surface_stale_runtime_healthy",
            ),
            "required_manifest_fields": ("migration_required", "repo_schema_version"),
            "write_set": (
                "odylith/atlas/source/catalog/diagrams.v1.json",
                "odylith/atlas/source/*.svg",
                "odylith/atlas/source/*.png",
                "odylith/atlas/atlas.html",
                "odylith/atlas/mermaid-payload.v1.js",
                "odylith/atlas/mermaid-app.v1.js",
                "odylith/radar/traceability-graph.v1.json",
                ".odylith/state/migrations/v0.1.14-atlas-render-surface-polish.v1.json",
            ),
            "rollback_scope": "repo-local Atlas generated surface writes; recover through Git if interrupted",
            "validation_commands": (
                "PYTHONPATH=src python -m pytest -q tests/unit/install/test_atlas_surface_migration.py tests/unit/install/test_migration_runtime.py",
                "PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_diagram_freshness.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_build_traceability_graph.py",
                "PYTHONPATH=src python src/odylith/cli.py validate topology-integrity --repo-root .",
                "PYTHONPATH=src python -m pytest -q tests/integration/install/test_lifecycle_simulator.py::test_lifecycle_simulator_proves_historical_upgrades_to_0_1_14",
            ),
        },
    )


__all__ = ["MigrationDefinition", "registered_migration_specs"]
