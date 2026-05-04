from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.install import migration_observer, migration_runtime
from odylith.install.atlas_surface_migration import (
    MIGRATION_ID as ATLAS_SURFACE_MIGRATION_ID,
)
from odylith.install.casebook_metadata_migration import (
    MIGRATION_ID as CASEBOOK_METADATA_MIGRATION_ID,
    STATUS_FSM_MIGRATION_ID as CASEBOOK_STATUS_FSM_MIGRATION_ID,
)
from odylith.install.value_engine_migration import (
    MIGRATION_ID,
    VALUE_CORPUS_RELATIVE_PATH,
    record_visible_intervention_value_engine_migration_satisfied,
)

FIXTURE_COVERAGE_TOKENS = (
    "dry_run",
    "apply",
    "rerun",
    "stale_ledger",
    "skipped_version",
    "historical_range",
)
MIGRATION_FIXTURE_COVERAGE_MARKERS = (
    "legacy-odyssey-root-migration:dry_run",
    "legacy-odyssey-root-migration:apply",
    "legacy-odyssey-root-migration:rerun",
    "legacy-odyssey-root-migration:stale_ledger",
    "legacy-odyssey-root-migration:skipped_version",
    "legacy-odyssey-root-migration:historical_range",
    "v0.1.11-visible-intervention-value-engine:dry_run",
    "v0.1.11-visible-intervention-value-engine:apply",
    "v0.1.11-visible-intervention-value-engine:rerun",
    "v0.1.11-visible-intervention-value-engine:stale_ledger",
    "v0.1.11-visible-intervention-value-engine:skipped_version",
    "v0.1.11-visible-intervention-value-engine:historical_range",
    "v0.1.13-casebook-compact-metadata:dry_run",
    "v0.1.13-casebook-compact-metadata:apply",
    "v0.1.13-casebook-compact-metadata:rerun",
    "v0.1.13-casebook-compact-metadata:stale_ledger",
    "v0.1.13-casebook-compact-metadata:skipped_version",
    "v0.1.13-casebook-compact-metadata:historical_range",
    "v0.1.14-casebook-status-fsm:dry_run",
    "v0.1.14-casebook-status-fsm:apply",
    "v0.1.14-casebook-status-fsm:rerun",
    "v0.1.14-casebook-status-fsm:stale_ledger",
    "v0.1.14-casebook-status-fsm:skipped_version",
    "v0.1.14-casebook-status-fsm:historical_range",
    "v0.1.14-atlas-render-surface-polish:dry_run",
    "v0.1.14-atlas-render-surface-polish:apply",
    "v0.1.14-atlas-render-surface-polish:rerun",
    "v0.1.14-atlas-render-surface-polish:stale_ledger",
    "v0.1.14-atlas-render-surface-polish:skipped_version",
    "v0.1.14-atlas-render-surface-polish:historical_range",
)
HISTORICAL_0_1_RELEASES_BEFORE_0_1_14 = (
    "",
    "0.1.0",
    "0.1.1",
    "0.1.2",
    "0.1.3",
    "0.1.4",
    "0.1.5",
    "0.1.6",
    "0.1.7",
    "0.1.8",
    "0.1.9",
    "0.1.10",
    "0.1.11",
    "0.1.12",
    "0.1.13",
)


def _seed_repo(repo_root: Path, *, active_version: str = "0.1.10") -> None:
    (repo_root / "AGENTS.md").write_text("# Repo\n", encoding="utf-8")
    (repo_root / "odylith" / "runtime" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / ".odylith" / "bin").mkdir(parents=True, exist_ok=True)
    (repo_root / ".odylith" / "bin" / "odylith").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (repo_root / ".odylith" / "install.json").write_text(
        json.dumps(
            {
                "active_version": active_version,
                "last_known_good_version": active_version,
                "activation_history": ["0.1.9", active_version],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (repo_root / "odylith" / "runtime" / "source" / "product-version.v1.json").write_text(
        json.dumps(
            {
                "schema_version": "odylith-product.v1",
                "odylith_version": active_version,
                "repo_schema_version": 1,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _seed_casebook_bug(repo_root: Path) -> None:
    bug_path = repo_root / "odylith" / "casebook" / "bugs" / "2026-04-26-legacy-casebook-labels.md"
    bug_path.parent.mkdir(parents=True, exist_ok=True)
    bug_path.write_text(
        "\n".join(
            [
                "- Bug ID: CB-155",
                "- Status: Mitigated locally; pending platform release",
                "- Created: 2026-04-26",
                "- Fixed: Pending release/deploy",
                "- Severity: P1",
                "- Type: OSW template upgrade repair / coroutine scheduler runtime / LocalStack proof UX",
                "",
                "- Description: Legacy Casebook metadata leaked prose into detail labels.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _seed_atlas_catalog(repo_root: Path) -> None:
    atlas_root = repo_root / "odylith" / "atlas"
    source_root = atlas_root / "source"
    catalog_path = source_root / "catalog" / "diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    (source_root / "migration-fixture.mmd").write_text(
        "flowchart TB\n  subgraph Lane[Lane]\n    A[Source] --> B[Render]\n  end\n",
        encoding="utf-8",
    )
    (source_root / "migration-fixture.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><g class="cluster"><rect style=""></rect></g></svg>\n',
        encoding="utf-8",
    )
    (source_root / "migration-fixture.png").write_bytes(b"old")
    catalog_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "diagrams": [
                    {
                        "diagram_id": "D-900",
                        "slug": "migration-fixture",
                        "title": "Migration Fixture",
                        "kind": "flowchart",
                        "status": "active",
                        "owner": "product",
                        "last_reviewed_utc": "2026-04-01",
                        "source_mmd": "odylith/atlas/source/migration-fixture.mmd",
                        "source_svg": "odylith/atlas/source/migration-fixture.svg",
                        "source_png": "odylith/atlas/source/migration-fixture.png",
                        "summary": "Atlas migration fixture.",
                        "change_watch_paths": ["odylith/atlas/source/migration-fixture.mmd"],
                        "components": [{"name": "atlas", "description": "Atlas surface."}],
                    }
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (atlas_root / "atlas.html").write_text(".viewer-stage::before { background-size: 42px 42px; }\n", encoding="utf-8")
    (atlas_root / "mermaid-payload.v1.js").write_text("window.__MERMAID_PAYLOAD__ = {};\n", encoding="utf-8")
    (atlas_root / "mermaid-app.v1.js").write_text("", encoding="utf-8")


def _write_install_state(repo_root: Path, payload: dict[str, object]) -> None:
    (repo_root / ".odylith").mkdir(parents=True, exist_ok=True)
    (repo_root / ".odylith" / "install.json").write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _seed_current_runtime(repo_root: Path, *, version: str, verification: dict[str, object] | None = None) -> Path:
    version_root = repo_root / ".odylith" / "runtime" / "versions" / version
    version_root.mkdir(parents=True, exist_ok=True)
    current = repo_root / ".odylith" / "runtime" / "current"
    current.parent.mkdir(parents=True, exist_ok=True)
    if current.exists() or current.is_symlink():
        current.unlink()
    current.symlink_to(version_root)
    if verification is not None:
        (version_root / "runtime-verification.v1.json").write_text(
            json.dumps(
                {
                    "schema_version": "odylith-runtime-verification.v1",
                    "version": version,
                    "verification": verification,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return version_root


def test_registered_value_engine_definition_has_release_gate_fixture_coverage() -> None:
    definition = next(
        item for item in migration_runtime.registered_migrations() if item.migration_id == MIGRATION_ID
    )

    assert definition.migration_id == MIGRATION_ID
    assert definition.introduced_version == "0.1.11"
    assert set(FIXTURE_COVERAGE_TOKENS).issubset(definition.coverage_fixtures)
    assert definition.automatic is True


def test_registered_casebook_metadata_definition_has_release_gate_fixture_coverage() -> None:
    definition = next(
        item for item in migration_runtime.registered_migrations() if item.migration_id == CASEBOOK_METADATA_MIGRATION_ID
    )

    assert definition.migration_id == CASEBOOK_METADATA_MIGRATION_ID
    assert definition.introduced_version == "0.1.13"
    assert set(FIXTURE_COVERAGE_TOKENS).issubset(definition.coverage_fixtures)
    assert definition.automatic is True


def test_registered_casebook_status_fsm_definition_has_release_gate_fixture_coverage() -> None:
    definition = next(
        item for item in migration_runtime.registered_migrations() if item.migration_id == CASEBOOK_STATUS_FSM_MIGRATION_ID
    )

    assert definition.migration_id == CASEBOOK_STATUS_FSM_MIGRATION_ID
    assert definition.introduced_version == "0.1.14"
    assert set(FIXTURE_COVERAGE_TOKENS).issubset(definition.coverage_fixtures)
    assert definition.automatic is True


def test_registered_atlas_surface_definition_has_release_gate_fixture_coverage() -> None:
    definition = next(
        item for item in migration_runtime.registered_migrations() if item.migration_id == ATLAS_SURFACE_MIGRATION_ID
    )

    assert definition.migration_id == ATLAS_SURFACE_MIGRATION_ID
    assert definition.introduced_version == "0.1.14"
    assert set(FIXTURE_COVERAGE_TOKENS).issubset(definition.coverage_fixtures)
    assert definition.automatic is True


def test_every_registered_upgrade_migration_has_full_lifecycle_fixture_coverage() -> None:
    expected_markers = set(MIGRATION_FIXTURE_COVERAGE_MARKERS)

    for definition in migration_runtime.registered_migrations():
        assert set(FIXTURE_COVERAGE_TOKENS).issubset(definition.coverage_fixtures)
        for token in FIXTURE_COVERAGE_TOKENS:
            assert f"{definition.migration_id}:{token}" in expected_markers


def _decision_for(plan: migration_runtime.MigrationPlan, migration_id: str) -> migration_runtime.MigrationDecision:
    return next(decision for decision in plan.decisions if decision.migration_id == migration_id)


def test_classifies_first_install_without_install_shape(tmp_path: Path) -> None:
    scenario = migration_runtime.classify_repo_migration_scenario(
        repo_root=tmp_path,
        target_version="0.1.12",
    )

    assert scenario.scenario == migration_runtime.SCENARIO_FIRST_INSTALL
    assert scenario.state["install_state_exists"] is False


def test_classifies_source_local_as_release_migration_blocked(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="product_repo",
        previous_version="source-local",
        target_version="0.1.12",
        source_repo=True,
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_DETACHED_SOURCE_LOCAL
    assert plan.blocked
    assert "source-local" in plan.blocked_reason


def test_missing_pin_blocks_release_migration_with_repair_command(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    (tmp_path / "odylith" / "runtime" / "source" / "product-version.v1.json").unlink()

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_MISSING_INVALID_PIN
    assert plan.blocked
    assert "repo pin is missing or invalid" in plan.blocked_reason


def test_missing_launcher_blocks_release_migration_as_repair_only(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    (tmp_path / ".odylith" / "bin" / "odylith").unlink()

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_MISSING_LAUNCHER
    assert ".odylith/bin/odylith" in plan.blocked[0].planned_paths
    assert "launcher is missing" in plan.blocked_reason


def test_legacy_odyssey_roots_are_planned_and_applied_first(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "odyssey" / "runtime" / "source").mkdir(parents=True)
    (tmp_path / "odyssey" / "runtime" / "source" / "product-version.v1.json").write_text(
        '{"schema_version":"odyssey-product.v1","odyssey_version":"0.1.10","repo_schema_version":1}\n',
        encoding="utf-8",
    )
    (tmp_path / ".odyssey" / "bin").mkdir(parents=True)
    (tmp_path / ".odyssey" / "bin" / "odyssey").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (tmp_path / ".odyssey" / "install.json").write_text(
        '{"active_version":"0.1.10","last_known_good_version":"0.1.10","activation_history":["0.1.9","0.1.10"]}\n',
        encoding="utf-8",
    )

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_LEGACY_ODYSSEY
    assert plan.selected[0].migration_id == migration_runtime.LEGACY_ROOT_MIGRATION_ID
    results = migration_runtime.apply_repo_state_migrations(plan=plan)
    assert results[0].migration_id == migration_runtime.LEGACY_ROOT_MIGRATION_ID
    assert (tmp_path / "odylith").is_dir()
    assert not (tmp_path / "odyssey").exists()
    assert (tmp_path / results[0].ledger_path).is_file()


def test_legacy_odyssey_product_conflict_blocks_before_overwrite(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Repo\n", encoding="utf-8")
    target_guidance = tmp_path / "odylith" / "AGENTS.md"
    target_guidance.parent.mkdir(parents=True)
    target_guidance.write_text("# Current Odylith guidance\n", encoding="utf-8")
    source_guidance = tmp_path / "odyssey" / "AGENTS.md"
    source_guidance.parent.mkdir(parents=True)
    source_guidance.write_text("# Legacy Odyssey guidance\n", encoding="utf-8")
    (tmp_path / ".odyssey" / "install.json").parent.mkdir(parents=True)
    (tmp_path / ".odyssey" / "install.json").write_text('{"active_version":"0.1.10"}\n', encoding="utf-8")

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_LEGACY_ODYSSEY
    assert plan.blocked
    assert "would overwrite existing Odylith paths" in plan.blocked_reason
    assert "odylith/AGENTS.md" in plan.blocked_reason
    with pytest.raises(ValueError, match="would overwrite"):
        migration_runtime.apply_repo_state_migrations(plan=plan)
    assert target_guidance.read_text(encoding="utf-8") == "# Current Odylith guidance\n"
    assert source_guidance.read_text(encoding="utf-8") == "# Legacy Odyssey guidance\n"


def test_legacy_odyssey_state_conflict_blocks_before_deleting_state(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Repo\n", encoding="utf-8")
    old_state = tmp_path / ".odyssey" / "install.json"
    new_state = tmp_path / ".odylith" / "install.json"
    old_state.parent.mkdir(parents=True)
    new_state.parent.mkdir(parents=True)
    old_state.write_text('{"active_version":"0.1.10","launcher_path":".odyssey/bin/odyssey"}\n', encoding="utf-8")
    new_state.write_text('{"active_version":"0.1.11","launcher_path":".odylith/bin/odylith"}\n', encoding="utf-8")
    (tmp_path / "odyssey").mkdir()

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_LEGACY_ODYSSEY
    assert plan.blocked
    assert ".odylith/install.json" in plan.blocked_reason
    with pytest.raises(ValueError, match="would overwrite"):
        migration_runtime.apply_repo_state_migrations(plan=plan)
    assert old_state.read_text(encoding="utf-8") == '{"active_version":"0.1.10","launcher_path":".odyssey/bin/odyssey"}\n'
    assert new_state.read_text(encoding="utf-8") == '{"active_version":"0.1.11","launcher_path":".odylith/bin/odylith"}\n'


def test_product_repo_pinned_dogfood_is_not_reported_as_consumer_noop(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    (tmp_path / ".odylith" / "install.json").write_text(
        '{"active_version":"0.1.11","last_known_good_version":"0.1.11","activation_history":["0.1.10","0.1.11"]}\n',
        encoding="utf-8",
    )

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="product_repo",
        previous_version="0.1.11",
        target_version="0.1.11",
        pinned_version="0.1.11",
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_PRODUCT_REPO_PINNED_DOGFOOD
    assert plan.no_op is True
    assert "maintainer release gates" in _decision_for(plan, MIGRATION_ID).reason


def test_product_repo_dogfood_is_not_blocked_by_missing_wrapped_runtime_verification(tmp_path: Path) -> None:
    _seed_repo(tmp_path, active_version="0.1.11")
    _seed_current_runtime(tmp_path, version="0.1.11")

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="product_repo",
        previous_version="0.1.11",
        target_version="0.1.11",
        pinned_version="0.1.11",
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_PRODUCT_REPO_PINNED_DOGFOOD
    assert not plan.blocked


def test_consumer_runtime_without_verification_blocks_same_version_release_migration(tmp_path: Path) -> None:
    _seed_repo(tmp_path, active_version="0.1.11")
    _seed_current_runtime(tmp_path, version="0.1.11")

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.11",
        target_version="0.1.11",
        pinned_version="0.1.11",
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_RUNTIME_VERIFICATION_MISSING
    assert plan.blocked
    assert "verification evidence is missing" in plan.blocked_reason


def test_staged_target_runtime_without_verification_blocks_before_activation(tmp_path: Path) -> None:
    _seed_repo(tmp_path, active_version="0.1.10")
    staged_runtime = tmp_path / ".odylith" / "runtime" / "versions" / "0.1.12"
    staged_runtime.mkdir(parents=True)

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
        runtime_root=staged_runtime,
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_RUNTIME_VERIFICATION_MISSING
    assert "verification evidence is missing" in plan.blocked_reason


def test_staged_target_runtime_accepts_installer_verification_evidence(tmp_path: Path) -> None:
    _seed_repo(tmp_path, active_version="0.1.10")
    staged_runtime = tmp_path / ".odylith" / "runtime" / "versions" / "0.1.12"
    staged_runtime.mkdir(parents=True)

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
        runtime_root=staged_runtime,
        runtime_verification={"wheel_sha256": "verified-by-installer"},
    )

    assert plan.scenario.scenario != migration_runtime.SCENARIO_RUNTIME_VERIFICATION_MISSING
    assert plan.blocked_reason == ""
    assert plan.scenario.state["runtime_verification_present"] is True


def test_missing_install_state_blocks_release_migration_as_repair_only(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    (tmp_path / ".odylith" / "install.json").unlink()

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_MISSING_INSTALL_STATE
    assert ".odylith/install.json" in plan.blocked[0].planned_paths
    assert "install state is missing" in plan.blocked_reason


def test_stale_install_state_blocks_release_migration_with_pointer_paths(tmp_path: Path) -> None:
    _seed_repo(tmp_path, active_version="0.1.9")
    _seed_current_runtime(tmp_path, version="0.1.10", verification={"wheel_sha256": "runtime-0.1.10"})

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_STALE_INSTALL_STATE
    assert ".odylith/runtime/current" in plan.blocked[0].planned_paths
    assert "install state disagree" in plan.blocked_reason


def test_partial_failed_upgrade_blocks_before_release_migration(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    _write_install_state(
        tmp_path,
        {
            "active_version": "0.1.10",
            "last_known_good_version": "0.1.9",
            "activation_history": ["0.1.9", "0.1.10"],
        },
    )
    logs_dir = tmp_path / ".odylith" / "runtime" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "upgrade-20260427T120000Z.json").write_text(
        '{"schema_version":"odylith.upgrade-report.v1","status":"failed","failed_phase":"runtime_activation"}\n',
        encoding="utf-8",
    )

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_PARTIAL_FAILED_UPGRADE
    assert "previous upgrade failed" in plan.blocked_reason


def test_repo_schema_mismatch_blocks_until_schema_migration_is_registered(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
        release_manifest={"repo_schema_version": 2},
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_REPO_SCHEMA_MISMATCH
    assert "repo_schema_version does not match" in plan.blocked_reason


def test_repo_schema_mismatch_outranks_migration_required(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
        release_manifest={"migration_required": True, "repo_schema_version": 2},
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_REPO_SCHEMA_MISMATCH
    assert "repo_schema_version does not match" in plan.blocked_reason


def test_rollback_target_missing_blocks_replacing_active_runtime(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    _write_install_state(
        tmp_path,
        {
            "active_version": "0.1.10",
            "last_known_good_version": "0.1.10",
            "activation_history": ["0.1.10"],
        },
    )

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_ROLLBACK_TARGET_MISSING
    assert "rollback target" in plan.blocked_reason


def test_previous_version_does_not_drive_live_state_classification(tmp_path: Path) -> None:
    _seed_repo(tmp_path, active_version="0.1.12")

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
        pinned_version="0.1.12",
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_ALREADY_CURRENT_CONSUMER
    assert not any(
        decision.migration_id == f"repo-state:{migration_runtime.SCENARIO_STALE_INSTALL_STATE}"
        for decision in plan.blocked
    )


def test_lock_cache_sludge_is_reported_without_blocking_release_migration(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    locks_dir = tmp_path / ".odylith" / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    for index in range(migration_runtime.LOCK_NOTE_THRESHOLD):
        (locks_dir / f"placeholder-{index}.lock").touch()

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_LOCK_CACHE_SLUDGE
    assert plan.scenario.state["zero_byte_lock_files"] == migration_runtime.LOCK_NOTE_THRESHOLD
    assert not any(decision.migration_id.startswith("repo-state:") for decision in plan.blocked)


def test_generated_surfaces_stale_are_reported_separately_from_release_migration(tmp_path: Path) -> None:
    _seed_repo(tmp_path, active_version="0.1.11")

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.11",
        target_version="0.1.12",
    )

    assert plan.scenario.scenario == migration_runtime.SCENARIO_GENERATED_SURFACE_STALE
    assert plan.scenario.state["generated_surface_stale"] is True
    assert not any(decision.migration_id.startswith("repo-state:") for decision in plan.blocked)


def test_selects_value_engine_migration_when_corpus_is_missing(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
    )

    assert [decision.state for decision in plan.selected] == [migration_runtime.STATE_SELECTED]
    assert plan.ledger_state[MIGRATION_ID] == migration_runtime.STATE_SELECTED
    assert plan.no_op is False


def test_reports_satisfied_unrecorded_when_clean_artifacts_have_no_ledger(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    corpus = tmp_path / VALUE_CORPUS_RELATIVE_PATH
    corpus.parent.mkdir(parents=True, exist_ok=True)
    corpus.write_text('{"schema_version":"value-corpus-test"}\n', encoding="utf-8")

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
    )

    assert [decision.state for decision in plan.selected] == [migration_runtime.STATE_SATISFIED_UNRECORDED]
    results = migration_runtime.apply_release_migrations(plan=plan)
    assert results[0].state == migration_runtime.STATE_SATISFIED_UNRECORDED
    assert (tmp_path / results[0].ledger_path).is_file()


def test_stale_ledger_blocks_normal_upgrade(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    ledger = tmp_path / ".odylith/state/migrations/v0.1.11-visible-intervention-value-engine.v1.json"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("{not json", encoding="utf-8")

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
    )

    assert plan.blocked[0].state == migration_runtime.STATE_LEDGER_STALE
    assert "stale" in plan.blocked_reason


def test_valid_ledger_missing_value_corpus_repairs_same_version_install(tmp_path: Path) -> None:
    _seed_repo(tmp_path, active_version="0.1.12")
    _seed_current_runtime(tmp_path, version="0.1.12", verification={"wheel_sha256": "runtime-0.1.12"})
    ledger = tmp_path / ".odylith/state/migrations/v0.1.11-visible-intervention-value-engine.v1.json"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        json.dumps(
            {
                "schema_version": "odylith-value-engine-migration.v1",
                "migration_id": "v0.1.11-visible-intervention-value-engine",
                "applied": True,
                "previous_version": "0.1.10",
                "target_version": "0.1.12",
                "written_paths": ["odylith/runtime/source/intervention-value-adjudication-corpus.v1.json"],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.12",
        target_version="0.1.12",
        pinned_version="0.1.12",
    )

    decision = _decision_for(plan, MIGRATION_ID)
    assert not plan.blocked
    assert decision.state == migration_runtime.STATE_SELECTED
    assert "artifacts need repair" in decision.reason
    results = migration_runtime.apply_release_migrations(plan=plan)
    assert results[0].state == migration_runtime.STATE_APPLIED
    assert (tmp_path / VALUE_CORPUS_RELATIVE_PATH).is_file()
    assert (tmp_path / results[0].ledger_path).is_file()


def test_complete_ledger_skips_value_engine_rerun(tmp_path: Path) -> None:
    _seed_repo(tmp_path, active_version="0.1.11")
    corpus = tmp_path / VALUE_CORPUS_RELATIVE_PATH
    corpus.parent.mkdir(parents=True, exist_ok=True)
    corpus.write_text('{"schema_version":"value-corpus-test"}\n', encoding="utf-8")
    record_visible_intervention_value_engine_migration_satisfied(
        repo_root=tmp_path,
        previous_version="0.1.10",
        target_version="0.1.12",
    )

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.11",
        target_version="0.1.12",
    )

    assert plan.no_op is True
    assert _decision_for(plan, MIGRATION_ID).reason.startswith("ledger and verification")


def test_migration_required_without_registered_target_blocks(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.9",
        target_version="0.1.10",
        release_manifest={"migration_required": True, "repo_schema_version": 1},
    )

    assert plan.blocked
    assert "no registered migration" in plan.blocked_reason


def test_migration_required_with_registered_target_uses_value_engine_plan(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.10",
        target_version="0.1.12",
        release_manifest={"migration_required": True, "repo_schema_version": 1},
    )

    assert plan.satisfies_manifest_requirement() is True
    assert _decision_for(plan, MIGRATION_ID).state == migration_runtime.STATE_SELECTED
    assert "no registered migration" not in plan.blocked_reason


def test_migration_required_future_release_does_not_pass_on_noop_registered_migration(tmp_path: Path) -> None:
    _seed_repo(tmp_path, active_version="1.2.3")

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="1.2.3",
        target_version="1.2.4",
        release_manifest={"migration_required": True, "repo_schema_version": 1},
    )

    assert plan.satisfies_manifest_requirement() is False
    assert plan.blocked
    assert "no registered migration" in plan.blocked_reason


def test_casebook_metadata_migration_is_selected_for_prior_versions_to_v013(tmp_path: Path) -> None:
    for previous_version in ("0.1.10", "0.1.11", "0.1.12"):
        repo_root = tmp_path / previous_version.replace(".", "_")
        repo_root.mkdir()
        _seed_repo(repo_root, active_version=previous_version)
        _seed_casebook_bug(repo_root)

        plan = migration_runtime.plan_release_migrations(
            repo_root=repo_root,
            repo_role="consumer_repo",
            previous_version=previous_version,
            target_version="0.1.13",
            release_manifest={"migration_required": True, "repo_schema_version": 1},
        )

        decision = _decision_for(plan, CASEBOOK_METADATA_MIGRATION_ID)
        assert decision.state == migration_runtime.STATE_SELECTED
        assert plan.satisfies_manifest_requirement() is True
        assert "no registered migration" not in plan.blocked_reason


def test_casebook_status_fsm_migration_is_selected_for_supported_versions_to_v014(tmp_path: Path) -> None:
    for previous_version in ("0.1.10", "0.1.11", "0.1.12", "0.1.13"):
        repo_root = tmp_path / f"status_{previous_version.replace('.', '_')}"
        repo_root.mkdir()
        _seed_repo(repo_root, active_version=previous_version)
        _seed_casebook_bug(repo_root)

        plan = migration_runtime.plan_release_migrations(
            repo_root=repo_root,
            repo_role="consumer_repo",
            previous_version=previous_version,
            target_version="0.1.14",
            release_manifest={"migration_required": True, "repo_schema_version": 1},
        )

        decision = _decision_for(plan, CASEBOOK_STATUS_FSM_MIGRATION_ID)
        assert decision.state == migration_runtime.STATE_SELECTED
        assert plan.satisfies_manifest_requirement() is True
        assert "no registered migration" not in plan.blocked_reason


def test_atlas_surface_migration_is_selected_for_supported_versions_to_v014(tmp_path: Path) -> None:
    for previous_version in ("0.1.10", "0.1.11", "0.1.12", "0.1.13"):
        repo_root = tmp_path / f"atlas_{previous_version.replace('.', '_')}"
        repo_root.mkdir()
        _seed_repo(repo_root, active_version=previous_version)
        _seed_atlas_catalog(repo_root)

        plan = migration_runtime.plan_release_migrations(
            repo_root=repo_root,
            repo_role="consumer_repo",
            previous_version=previous_version,
            target_version="0.1.14",
            release_manifest={"migration_required": True, "repo_schema_version": 1},
        )

        decision = _decision_for(plan, ATLAS_SURFACE_MIGRATION_ID)
        assert decision.state == migration_runtime.STATE_SELECTED
        assert plan.satisfies_manifest_requirement() is True
        assert "no registered migration" not in plan.blocked_reason


def test_release_migrations_cover_any_historical_0_1_release_to_v014(tmp_path: Path) -> None:
    value_engine_required_versions = {
        "",
        "0.1.0",
        "0.1.1",
        "0.1.2",
        "0.1.3",
        "0.1.4",
        "0.1.5",
        "0.1.6",
        "0.1.7",
        "0.1.8",
        "0.1.9",
        "0.1.10",
    }

    for index, previous_version in enumerate(HISTORICAL_0_1_RELEASES_BEFORE_0_1_14):
        active_version = previous_version or "0.1.0"
        repo_root = tmp_path / f"historical_{index:02d}_{active_version.replace('.', '_')}"
        repo_root.mkdir()
        _seed_repo(repo_root, active_version=active_version)
        _seed_casebook_bug(repo_root)
        _seed_atlas_catalog(repo_root)

        plan = migration_runtime.plan_release_migrations(
            repo_root=repo_root,
            repo_role="consumer_repo",
            previous_version=previous_version,
            target_version="0.1.14",
            release_manifest={"migration_required": True, "repo_schema_version": 1},
        )

        assert not plan.blocked, (previous_version, plan.blocked_reason)
        assert plan.satisfies_manifest_requirement() is True
        assert plan.ledger_state[CASEBOOK_METADATA_MIGRATION_ID] == migration_runtime.STATE_SELECTED
        assert plan.ledger_state[CASEBOOK_STATUS_FSM_MIGRATION_ID] == migration_runtime.STATE_SELECTED
        assert plan.ledger_state[ATLAS_SURFACE_MIGRATION_ID] == migration_runtime.STATE_SELECTED
        expected_value_state = (
            migration_runtime.STATE_SELECTED
            if previous_version in value_engine_required_versions
            else migration_runtime.STATE_SKIPPED
        )
        assert plan.ledger_state[MIGRATION_ID] == expected_value_state


def test_casebook_metadata_migration_skips_index_only_repos_without_blocking_manifest(tmp_path: Path) -> None:
    _seed_repo(tmp_path, active_version="0.1.12")
    index_path = tmp_path / "odylith" / "casebook" / "bugs" / "INDEX.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("# Bugs Index\n", encoding="utf-8")

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.12",
        target_version="0.1.13",
        release_manifest={"migration_required": True, "repo_schema_version": 1},
    )

    decision = _decision_for(plan, CASEBOOK_METADATA_MIGRATION_ID)
    assert decision.state == migration_runtime.STATE_SKIPPED
    assert decision.reason == "repo has no Casebook bug source records to migrate"
    assert plan.satisfies_manifest_requirement() is True
    assert "no registered migration" not in plan.blocked_reason


def test_casebook_metadata_migration_ledger_stale_blocks_upgrade(tmp_path: Path) -> None:
    _seed_repo(tmp_path, active_version="0.1.12")
    ledger = tmp_path / ".odylith/state/migrations/v0.1.13-casebook-compact-metadata.v1.json"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("{not json", encoding="utf-8")

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.12",
        target_version="0.1.13",
    )

    decision = _decision_for(plan, CASEBOOK_METADATA_MIGRATION_ID)
    assert decision.state == migration_runtime.STATE_LEDGER_STALE
    assert "migration ledger is stale" in plan.blocked_reason


def test_casebook_status_fsm_migration_ledger_stale_blocks_upgrade(tmp_path: Path) -> None:
    _seed_repo(tmp_path, active_version="0.1.13")
    _seed_casebook_bug(tmp_path)
    ledger = tmp_path / ".odylith/state/migrations/v0.1.14-casebook-status-fsm.v1.json"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("{not json", encoding="utf-8")

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.13",
        target_version="0.1.14",
    )

    decision = _decision_for(plan, CASEBOOK_STATUS_FSM_MIGRATION_ID)
    assert decision.state == migration_runtime.STATE_LEDGER_STALE
    assert "migration ledger is stale" in plan.blocked_reason


def test_atlas_surface_migration_ledger_stale_blocks_upgrade(tmp_path: Path) -> None:
    _seed_repo(tmp_path, active_version="0.1.13")
    _seed_atlas_catalog(tmp_path)
    ledger = tmp_path / ".odylith/state/migrations/v0.1.14-atlas-render-surface-polish.v1.json"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("{not json", encoding="utf-8")

    plan = migration_runtime.plan_release_migrations(
        repo_root=tmp_path,
        repo_role="consumer_repo",
        previous_version="0.1.13",
        target_version="0.1.14",
    )

    decision = _decision_for(plan, ATLAS_SURFACE_MIGRATION_ID)
    assert decision.state == migration_runtime.STATE_LEDGER_STALE
    assert "migration ledger is stale" in plan.blocked_reason


def test_surface_migration_observer_classifies_consumer_visible_surface_paths(tmp_path: Path) -> None:
    report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=(
            "odylith/skills/odylith-sync/SKILL.md",
            "src/odylith/runtime/surfaces/render_casebook_dashboard.py",
            "src/odylith/install/agents.py",
            "src/odylith/cli.py",
            "README.md",
            "odylith/radar/source/ideas/2026-04/generated.md",
        ),
    )

    assert report.ok is False
    assert {need.need_id for need in report.needs} == {
        "browser-surfaces",
        "guidance-and-skills",
        "install-managed-assets",
        "operator-cli-contracts",
        "public-docs-and-release-guidance",
    }
    assert "odylith/radar/source/ideas/2026-04/generated.md" not in report.changed_paths
    assert all(need.governance_marker.startswith("migration-observer:0.1.12:") for need in report.needs)
    assert all(need.governance_marker != need.marker_family for need in report.needs)
    assert all(len(need.change_fingerprint) == 12 for need in report.needs)


def test_surface_migration_observer_passes_only_completed_target_specific_records(tmp_path: Path) -> None:
    first_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/skills/odylith-sync/SKILL.md",),
    )
    marker = first_report.needs[0].governance_marker
    record = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "migration.md"
    record.parent.mkdir(parents=True)
    record.write_text(
        "\n".join(
            [
                "status: finished",
                "idea_id: B-999",
                "title: Surface migration proof",
                "",
                "## Migration Observer Needs",
                f"- `{marker}`",
                "- stale prose token `migration-observer:0.1.11:guidance-and-skills` should not satisfy 0.1.12",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/skills/odylith-sync/SKILL.md",),
    )
    stale_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.13",
        changed_paths=("odylith/skills/odylith-sync/SKILL.md",),
    )

    assert report.ok is True
    assert report.blocked_need_ids == ()
    assert report.records[0].workstream_id == "B-999"
    assert stale_report.ok is False
    assert stale_report.blocked_need_ids == ("guidance-and-skills",)


def test_surface_migration_observer_requires_change_fingerprint_not_class_marker(tmp_path: Path) -> None:
    record = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "class-marker.md"
    record.parent.mkdir(parents=True)
    record.write_text(
        "\n".join(
            [
                "status: finished",
                "idea_id: B-997",
                "title: Class marker is not enough",
                "",
                "- `migration-observer:0.1.12:guidance-and-skills`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/skills/odylith-sync/SKILL.md",),
    )

    assert report.ok is False
    assert report.needs[0].marker_family in report.records[0].markers
    assert report.needs[0].governance_marker not in report.records[0].markers
    assert report.blocked_need_ids == ("guidance-and-skills",)


def test_surface_migration_observer_rechecks_same_path_when_content_changes(tmp_path: Path) -> None:
    skill_path = tmp_path / "odylith" / "skills" / "sample" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("first guidance contract\n", encoding="utf-8")
    first_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/skills/sample/SKILL.md",),
    )
    marker = first_report.needs[0].governance_marker
    record = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "migration.md"
    record.parent.mkdir(parents=True)
    record.write_text(
        "\n".join(
            [
                "status: finished",
                "idea_id: B-996",
                "title: Exact content marker",
                "",
                f"- `{marker}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    covered_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/skills/sample/SKILL.md",),
    )
    skill_path.write_text("second guidance contract\n", encoding="utf-8")
    changed_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/skills/sample/SKILL.md",),
    )

    assert covered_report.ok is True
    assert changed_report.ok is False
    assert changed_report.needs[0].governance_marker != marker
    assert changed_report.blocked_need_ids == ("guidance-and-skills",)


def test_surface_migration_observer_fingerprint_ignores_rendered_observer_markers(tmp_path: Path) -> None:
    rendered = tmp_path / "odylith" / "radar" / "radar.html"
    rendered.parent.mkdir(parents=True)
    rendered.write_text(
        "rendered release note migration-observer:0.1.12:browser-surfaces:aaaaaaaaaaaa\n"
        '<script src="backlog-payload.v1.js?v=aaaaaaaaaaaa"></script>\n',
        encoding="utf-8",
    )
    first_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/radar/radar.html",),
    )
    marker = first_report.needs[0].governance_marker
    record = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "migration.md"
    record.parent.mkdir(parents=True)
    record.write_text(
        "\n".join(
            [
                "status: finished",
                "idea_id: B-995",
                "title: Rendered observer marker proof",
                "",
                f"- `{marker}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    rendered.write_text(
        f"rendered release note {marker}\n"
        '<script src="backlog-payload.v1.js?v=bbbbbbbbbbbb"></script>\n',
        encoding="utf-8",
    )

    covered_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/radar/radar.html",),
    )

    assert covered_report.ok is True
    assert covered_report.needs[0].governance_marker == marker
    assert covered_report.blocked_need_ids == ()


def test_surface_migration_observer_fingerprint_ignores_added_observer_marker_lines(tmp_path: Path) -> None:
    rendered = tmp_path / "odylith" / "radar" / "radar.html"
    rendered.parent.mkdir(parents=True)
    rendered.write_text(
        "rendered release note without observer marker\n"
        '<script src="backlog-payload.v1.js?v=aaaaaaaaaaaa"></script>\n',
        encoding="utf-8",
    )
    first_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/radar/radar.html",),
    )
    marker = first_report.needs[0].governance_marker
    record = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "migration.md"
    record.parent.mkdir(parents=True)
    record.write_text(
        "\n".join(
            [
                "status: finished",
                "idea_id: B-994",
                "title: Added observer marker proof",
                "",
                "Assessment: generated browser refresh is covered by the renderer migration.",
                f"- `{marker}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    rendered.write_text(
        "rendered release note without observer marker\n"
        "Migration observer markers:\n"
        f"- `{marker}`\n"
        '<script src="backlog-payload.v1.js?v=bbbbbbbbbbbb"></script>\n',
        encoding="utf-8",
    )

    covered_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/radar/radar.html",),
    )

    assert covered_report.ok is True
    assert covered_report.needs[0].governance_marker == marker
    assert covered_report.blocked_need_ids == ()


def test_surface_migration_observer_fingerprint_ignores_generated_derivative_churn(tmp_path: Path) -> None:
    changed_paths = (
        "odylith/runtime/delivery_intelligence.v4.json",
        "odylith/atlas/source/catalog/diagrams.v1.json",
        "odylith/registry/source/components/radar/FORENSICS.v1.json",
    )
    for index, token in enumerate(changed_paths, start=1):
        path = tmp_path / token
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"generated": index, "marker": "migration-observer:0.1.12:browser-surfaces:aaaaaaaaaaaa"}),
            encoding="utf-8",
        )

    first_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=changed_paths,
    )
    markers = [need.governance_marker for need in first_report.needs]
    record = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "migration.md"
    record.parent.mkdir(parents=True)
    record.write_text(
        "\n".join(
            [
                "status: finished",
                "idea_id: B-994",
                "title: Generated derivative churn proof",
                "",
                *(f"- `{marker}`" for marker in markers),
                "",
            ]
        ),
        encoding="utf-8",
    )
    for index, token in enumerate(changed_paths, start=10):
        (tmp_path / token).write_text(
            json.dumps({"generated": index, "marker": "migration-observer:0.1.12:browser-surfaces:bbbbbbbbbbbb"}),
            encoding="utf-8",
        )

    covered_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=changed_paths,
    )

    assert covered_report.ok is True
    assert {need.governance_marker for need in covered_report.needs} == set(markers)
    assert covered_report.blocked_need_ids == ()


def test_surface_migration_observer_rejects_incomplete_records_with_matching_markers(tmp_path: Path) -> None:
    first_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("src/odylith/cli.py",),
    )
    marker = first_report.needs[0].governance_marker
    record = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "queued.md"
    record.parent.mkdir(parents=True)
    record.write_text(
        "\n".join(
            [
                "status: queued",
                "idea_id: B-998",
                "title: Queued surface migration assessment",
                "",
                f"- `{marker}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("src/odylith/cli.py",),
    )

    assert report.ok is False
    assert report.records[0].completed() is False
    assert report.blocked_need_ids == ("operator-cli-contracts",)


def test_release_gate_blocks_surface_changes_without_completed_observer_record(tmp_path: Path) -> None:
    report = migration_runtime.validate_release_migration_gate(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("src/odylith/install/agents.py",),
    )

    assert report.ok is False
    assert report.surface_migration_observer.blocked_need_ids == ("install-managed-assets",)
    assert any("surface migration assessment incomplete" in item for item in report.blocked_manual_migrations)


def test_release_gate_reports_registered_migrations_and_no_lifecycle_bypass() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    report = migration_runtime.validate_release_migration_gate(
        repo_root=repo_root,
        target_version="0.1.12",
        changed_paths=(),
    )

    assert report.ok is True
    assert not report.ungated_lifecycle_paths
    assert report.fixture_matrix[migration_runtime.LEGACY_ROOT_MIGRATION_ID]["apply"] is True
    assert report.fixture_matrix[MIGRATION_ID]["dry_run"] is True
    assert report.fixture_matrix[MIGRATION_ID]["stale_ledger"] is True
    assert report.destructive_write_matrix["host.claude.preverified-settings"][
        "test_install_bundle_preserves_host_settings_when_runtime_download_fails"
    ] is True
    assert report.destructive_write_matrix["migration.legacy-product-conflict"][
        "test_legacy_odyssey_product_conflict_blocks_before_overwrite"
    ] is True
    assert report.destructive_write_matrix["governance.first-install-authoring-order"][
        "test_first_install_governance_records_can_be_created_in_every_surface_order"
    ] is True
    assert "destructive_write_scenarios" in report.as_dict()
    assert report.surface_migration_observer.ok is True
    assert report.as_dict()["surface_migration_observer"]["schema_version"] == (
        migration_observer.OBSERVER_SCHEMA_VERSION
    )


def test_release_gate_blocks_migration_required_manifest_without_definition(tmp_path: Path) -> None:
    report = migration_runtime.validate_release_migration_gate(
        repo_root=tmp_path,
        target_version="0.1.10",
        release_manifest={"migration_required": True, "repo_schema_version": 1},
    )

    assert report.ok is False
    assert any("no registered migration definition" in item for item in report.blocked_manual_migrations)
    assert json.loads(json.dumps(report.as_dict()))["ok"] is False
