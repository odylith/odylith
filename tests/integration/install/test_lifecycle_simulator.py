from __future__ import annotations

import shutil
from pathlib import Path

from odylith.install.casebook_metadata_migration import MIGRATION_ID as CASEBOOK_METADATA_MIGRATION_ID

from tests.integration.install.simulator import InstallLifecycleSimulator, VerifiedReleaseLifecycleSimulator

VALUE_ENGINE_MIGRATION_ID = "v0.1.11-visible-intervention-value-engine"


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
