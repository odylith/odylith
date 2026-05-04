from __future__ import annotations

import json
import shutil
from pathlib import Path

from odylith.install.atlas_surface_migration import MIGRATION_ID as ATLAS_SURFACE_MIGRATION_ID
from odylith.install.casebook_metadata_migration import (
    MIGRATION_ID as CASEBOOK_METADATA_MIGRATION_ID,
    STATUS_FSM_MIGRATION_ID as CASEBOOK_STATUS_FSM_MIGRATION_ID,
)
from odylith.runtime.surfaces import auto_update_mermaid_diagrams

from tests.integration.install.simulator import InstallLifecycleSimulator, VerifiedReleaseLifecycleSimulator

VALUE_ENGINE_MIGRATION_ID = "v0.1.11-visible-intervention-value-engine"
HISTORICAL_0_1_RELEASES_BEFORE_0_1_14 = (
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


def _write_legacy_casebook_metadata_bug(repo_root: Path) -> Path:
    bug_path = repo_root / "odylith" / "casebook" / "bugs" / "2026-05-01-legacy-casebook-labels.md"
    bug_path.parent.mkdir(parents=True, exist_ok=True)
    bug_path.write_text(
        "\n".join(
            [
                "- Bug ID: CB-999",
                "",
                "- Status: Mitigated locally; pending platform release",
                "",
                "- Created: 2026-05-01",
                "",
                "- Fixed: Pending release/deploy",
                "",
                "- Severity: P1",
                "",
                "- Reproducibility: Consistent",
                "",
                "- Type: OSW template upgrade repair / coroutine scheduler runtime / LocalStack proof UX",
                "",
                "- Description: Legacy Casebook metadata migration fixture.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return bug_path


def _patch_mermaid_render(monkeypatch) -> None:
    def fake_render_batch(*, repo_root: Path, render_jobs, cli_version: str) -> None:
        assert cli_version
        for job in render_jobs:
            svg_path = repo_root / str(job["source_svg"])
            png_path = repo_root / str(job["source_png"])
            svg_path.parent.mkdir(parents=True, exist_ok=True)
            svg_path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80" viewBox="0 0 120 80">'
                '<g class="cluster"><rect style="fill:#effcf9 !important;stroke:#9bd8cf !important;"></rect></g>'
                "</svg>\n",
                encoding="utf-8",
            )
            png_path.write_bytes(b"atlas")

    monkeypatch.setattr(auto_update_mermaid_diagrams, "_render_diagrams_batch", fake_render_batch)


def _write_legacy_atlas_surface(repo_root: Path) -> None:
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


def test_lifecycle_simulator_covers_first_install_upgrade_and_rollback(tmp_path: Path, monkeypatch) -> None:
    sim = InstallLifecycleSimulator(tmp_path=tmp_path, monkeypatch=monkeypatch)
    sim.register_release("1.2.4")

    assert sim.install("1.2.3") == 0
    assert sim.state()["active_version"] == "1.2.3"
    assert sim.pin().odylith_version == "1.2.3"
    assert sim.status().detached is False

    sim.write_pin("1.2.4")
    assert sim.upgrade() == 0
    assert sim.state()["active_version"] == "1.2.4"
    assert sim.pin().odylith_version == "1.2.4"
    assert sim.active_runtime_name() == "1.2.4"

    assert sim.rollback_previous() == 0
    status = sim.status()
    assert status.active_version == "1.2.3"
    assert status.pinned_version == "1.2.4"
    assert status.diverged_from_pin is True
    assert status.detached is False
    assert sim.active_runtime_name() == "1.2.3"


def test_lifecycle_simulator_proves_historical_upgrades_to_0_1_13(tmp_path: Path, monkeypatch) -> None:
    target_version = "0.1.13"
    expected_plan_state = {
        "0.1.10": "selected",
        "0.1.11": "skipped",
        "0.1.12": "skipped",
    }

    for from_version, migration_state in expected_plan_state.items():
        case_root = tmp_path / from_version.replace(".", "_")
        case_root.mkdir()
        sim = InstallLifecycleSimulator(tmp_path=case_root, monkeypatch=monkeypatch)
        sim.register_release(target_version)

        assert sim.install(from_version) == 0
        legacy_bug_path = _write_legacy_casebook_metadata_bug(sim.repo_root)

        if from_version == "0.1.10":
            value_corpus = sim.repo_root / "odylith/runtime/source/intervention-value-adjudication-corpus.v1.json"
            value_corpus.unlink(missing_ok=True)
            old_ranker = sim.repo_root / "odylith/runtime/source/intervention-signal-ranker-corpus.v1.json"
            old_ranker.parent.mkdir(parents=True, exist_ok=True)
            old_ranker.write_text('{"schema_version":"legacy-signal-ranker-test"}\n', encoding="utf-8")

        sim.write_pin(target_version)

        assert sim.upgrade() == 0
        assert sim.status().active_version == target_version
        assert sim.pin().odylith_version == target_version
        assert sim.active_runtime_name() == target_version

        activated_events = [
            entry
            for entry in sim.install_ledger()
            if entry.get("operation") == "upgrade" and entry.get("status") == "activated"
        ]
        assert activated_events
        upgrade_event = activated_events[-1]
        assert upgrade_event["previous_version"] == from_version
        assert upgrade_event["active_version"] == target_version
        assert upgrade_event["migration_plan"]["target_version"] == target_version

        value_engine_state = upgrade_event["migration_plan"]["ledger_state"][VALUE_ENGINE_MIGRATION_ID]
        assert value_engine_state == migration_state
        assert upgrade_event["migration_plan"]["ledger_state"][CASEBOOK_METADATA_MIGRATION_ID] == "selected"
        assert not upgrade_event["migration_plan"]["blocked"]

        migration_results = {result["migration_id"]: result for result in upgrade_event["migration_results"]}
        assert migration_results[CASEBOOK_METADATA_MIGRATION_ID]["state"] == "applied"
        legacy_text = legacy_bug_path.read_text(encoding="utf-8")
        assert "- Status: Mitigated" in legacy_text
        assert "- Fixed: Pending" in legacy_text
        assert "- Type: UX" in legacy_text
        payload_text = (sim.repo_root / "odylith" / "casebook" / "casebook-payload.v1.js").read_text(encoding="utf-8")
        assert "Mitigated locally; pending platform release" not in payload_text
        assert "Pending release/deploy" not in payload_text
        assert "OSW template upgrade repair" not in payload_text

        if from_version == "0.1.10":
            assert (sim.repo_root / "odylith/runtime/source/intervention-value-adjudication-corpus.v1.json").is_file()
            assert not (sim.repo_root / "odylith/runtime/source/intervention-signal-ranker-corpus.v1.json").exists()
            assert migration_results[VALUE_ENGINE_MIGRATION_ID]["state"] == "applied"


def test_lifecycle_simulator_proves_historical_upgrades_to_0_1_14(tmp_path: Path, monkeypatch) -> None:
    target_version = "0.1.14"
    _patch_mermaid_render(monkeypatch)

    for from_version in HISTORICAL_0_1_RELEASES_BEFORE_0_1_14:
        case_root = tmp_path / f"v014_{from_version.replace('.', '_')}"
        case_root.mkdir()
        sim = InstallLifecycleSimulator(tmp_path=case_root, monkeypatch=monkeypatch)
        sim.register_release(target_version)

        assert sim.install(from_version) == 0
        legacy_bug_path = _write_legacy_casebook_metadata_bug(sim.repo_root)
        _write_legacy_atlas_surface(sim.repo_root)
        sim.write_pin(target_version)

        assert sim.upgrade() == 0
        assert sim.status().active_version == target_version
        assert sim.pin().odylith_version == target_version

        activated_events = [
            entry
            for entry in sim.install_ledger()
            if entry.get("operation") == "upgrade" and entry.get("status") == "activated"
        ]
        assert activated_events
        upgrade_event = activated_events[-1]
        assert upgrade_event["previous_version"] == from_version
        assert upgrade_event["active_version"] == target_version
        assert upgrade_event["migration_plan"]["target_version"] == target_version
        assert upgrade_event["migration_plan"]["ledger_state"][CASEBOOK_STATUS_FSM_MIGRATION_ID] == "selected"
        assert upgrade_event["migration_plan"]["ledger_state"][ATLAS_SURFACE_MIGRATION_ID] == "selected"
        assert not upgrade_event["migration_plan"]["blocked"]

        migration_results = {result["migration_id"]: result for result in upgrade_event["migration_results"]}
        assert migration_results[CASEBOOK_STATUS_FSM_MIGRATION_ID]["state"] == "applied"
        assert migration_results[ATLAS_SURFACE_MIGRATION_ID]["state"] == "applied"
        assert (sim.repo_root / ".odylith/state/migrations/v0.1.14-casebook-status-fsm.v1.json").is_file()
        assert (sim.repo_root / ".odylith/state/migrations/v0.1.14-atlas-render-surface-polish.v1.json").is_file()
        legacy_text = legacy_bug_path.read_text(encoding="utf-8")
        assert "- Status: Mitigated" in legacy_text
        assert "- Fixed: Pending" in legacy_text
        assert "- Type: UX" in legacy_text
        payload_text = (sim.repo_root / "odylith" / "casebook" / "casebook-payload.v1.js").read_text(encoding="utf-8")
        assert '"status": "Mitigated"' in payload_text
        assert '"status_token": "mitigated"' in payload_text
        atlas_html = (sim.repo_root / "odylith" / "atlas" / "atlas.html").read_text(encoding="utf-8")
        assert ".viewer-stage::before" not in atlas_html
        assert "background: #ffffff;" in atlas_html


def test_lifecycle_simulator_blocks_migration_release_activation(tmp_path: Path, monkeypatch) -> None:
    sim = InstallLifecycleSimulator(tmp_path=tmp_path, monkeypatch=monkeypatch)
    sim.register_release("1.2.4", migration_required=True)

    assert sim.install("1.2.3") == 0
    sim.write_pin("1.2.4")

    assert sim.upgrade() == 2
    assert sim.status().active_version == "1.2.3"
    assert sim.pin().odylith_version == "1.2.4"


def test_lifecycle_simulator_recovers_after_failed_upgrade_smoke(tmp_path: Path, monkeypatch) -> None:
    sim = InstallLifecycleSimulator(tmp_path=tmp_path, monkeypatch=monkeypatch)
    sim.register_release("1.2.4")

    assert sim.install("1.2.3") == 0
    sim.write_pin("1.2.4")
    sim.fail_smoke_for("1.2.4")

    assert sim.upgrade() == 1
    assert sim.status().active_version == "1.2.3"
    assert sim.active_runtime_name() == "1.2.3"

    failed_events = [entry for entry in sim.install_ledger() if entry.get("operation") == "upgrade" and entry.get("status") == "failed"]
    assert len(failed_events) == 1
    assert failed_events[0]["target_version"] == "1.2.4"


def test_lifecycle_simulator_exercises_source_local_override_and_repair(tmp_path: Path, monkeypatch) -> None:
    sim = InstallLifecycleSimulator(tmp_path=tmp_path, monkeypatch=monkeypatch)
    sim.promote_to_product_repo(version="1.2.3")

    assert sim.install("1.2.3") == 0
    assert sim.upgrade_source_local() == 0

    status = sim.status()
    assert status.active_version == "source-local"
    assert status.detached is True
    assert status.last_known_good_version == "1.2.3"

    current_link = sim.repo_root / ".odylith" / "runtime" / "current"
    source_runtime_root = current_link.resolve()
    current_link.unlink()
    shutil.rmtree(source_runtime_root)

    assert sim.doctor(repair=True) == 0
    repaired_status = sim.status()
    assert repaired_status.active_version == "1.2.3"
    assert repaired_status.detached is False
    assert repaired_status.last_known_good_version == "1.2.3"
    assert sim.active_runtime_name() == "1.2.3"


def test_verified_release_lifecycle_simulator_exercises_runtime_staging_path(tmp_path: Path, monkeypatch) -> None:
    sim = VerifiedReleaseLifecycleSimulator(tmp_path=tmp_path, monkeypatch=monkeypatch)
    sim.register_verified_release("1.2.4")

    assert sim.install("1.2.3") == 0
    sim.write_pin("1.2.4")

    assert sim.upgrade() == 0
    status = sim.status()
    state = sim.state()
    assert status.active_version == "1.2.4"
    assert status.detached is False
    assert sim.active_runtime_name() == "1.2.4"
    assert sim.runtime_install_marker("1.2.4").endswith("odylith-1.2.4-py3-none-any.whl")
    assert state["installed_versions"]["1.2.4"]["verification"]["wheel_sha256"] == "sha256-1.2.4"
    assert (
        sim.repo_root / ".odylith" / "cache" / "releases" / "1.2.4" / "odylith-1.2.4-py3-none-any.whl"
    ).is_file()


def test_verified_release_lifecycle_simulator_preserves_previous_runtime_after_failed_smoke(tmp_path: Path, monkeypatch) -> None:
    sim = VerifiedReleaseLifecycleSimulator(tmp_path=tmp_path, monkeypatch=monkeypatch)
    sim.register_verified_release("1.2.4")

    assert sim.install("1.2.3") == 0
    sim.write_pin("1.2.4")
    sim.fail_smoke_for("1.2.4")

    assert sim.upgrade() == 1
    status = sim.status()
    assert status.active_version == "1.2.3"
    assert sim.active_runtime_name() == "1.2.3"
    assert sim.runtime_install_marker("1.2.4").endswith("odylith-1.2.4-py3-none-any.whl")
