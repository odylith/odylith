from __future__ import annotations

import shutil
from pathlib import Path

from tests.integration.install.simulator import InstallLifecycleSimulator, VerifiedReleaseLifecycleSimulator


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
