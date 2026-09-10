"""A failed upgrade activation must not commit a new operator pin."""

import json
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

from odylith.install import manager
from odylith.install.state import version_pin_path
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary as mutations
from tests.integration.install.simulator import InstallLifecycleSimulator


def _pin_state(path: Path):
    return (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) if path.exists() else None


def _installed_case(tmp_path, monkeypatch, pin_intent):
    sim = InstallLifecycleSimulator(tmp_path=tmp_path, monkeypatch=monkeypatch)
    sim.register_release("1.2.4")
    sim.write_pin("1.2.4" if pin_intent == "target" else "1.2.3")
    pin_path = version_pin_path(repo_root=sim.repo_root)
    pin = json.loads(pin_path.read_text())
    pin["operator_note"] = "Preserve this release decision and its formatting."
    pin_path.write_text(json.dumps(pin, indent=4) + "\n\n", encoding="utf-8")
    pin_path.chmod(0o640)
    assert sim.install("1.2.3") == 0
    if pin_intent == "absent":
        # Publish the fixture's explicit absent-pin precondition, not unmanaged drift.
        def remove_fixture_pin(_repository_lock_fd):
            pin_path.unlink()
            return 0

        assert mutations.run_with_greenfield_managed_mutation_boundary(
            repo_root=sim.repo_root, command_tokens=("upgrade",), operation=remove_fixture_pin,
        ) == 0
    else:
        assert _pin_state(pin_path) == (json.dumps(pin, indent=4).encode() + b"\n\n", 0o640)
    generations.require_greenfield_working_generation(sim.repo_root)
    return sim, pin_path


@pytest.mark.parametrize("pin_intent", ("old", "target"))
@pytest.mark.parametrize("failure", ("nonzero", "exception"))
def test_failed_activation_preserves_exact_pin_and_allows_next_command(tmp_path, monkeypatch, pin_intent, failure):
    sim, pin_path = _installed_case(tmp_path, monkeypatch, pin_intent)
    before_pin = _pin_state(pin_path)
    entry = sim.repo_root / "odylith/index.html"
    before_entry = entry.read_bytes()
    launcher = sim.repo_root / ".odylith/bin/odylith"
    before_launcher = _pin_state(launcher)
    observed_pins = []

    def smoke(*, python, repo_root):
        assert python.parent.parent.name == "1.2.4"
        assert repo_root == sim.repo_root
        observed_pins.append(_pin_state(pin_path))
        if failure == "exception":
            raise OSError("simulated activation exception")
        return SimpleNamespace(returncode=1, stdout="smoke stdout retained", stderr="simulated smoke failure")

    monkeypatch.setattr(manager, "_run_odylith_smoke", smoke)
    assert sim.upgrade_to("1.2.4", write_pin=True) == 1
    assert observed_pins == [before_pin]
    assert _pin_state(pin_path) == before_pin
    assert entry.read_bytes() == before_entry
    assert _pin_state(launcher) == before_launcher
    assert sim.active_runtime_name() == "1.2.3"
    assert sim.status().active_version == "1.2.3"
    failures = [row for row in sim.install_ledger() if row.get("operation") == "upgrade" and row.get("status") == "failed"]
    assert len(failures) == 1
    assert failures[0]["previous_version"] == "1.2.3"
    assert failures[0]["target_version"] == "1.2.4"
    assert failures[0]["stderr"] == ("simulated activation exception" if failure == "exception" else "simulated smoke failure")
    assert failures[0]["stdout"] == ("" if failure == "exception" else "smoke stdout retained")
    generations.require_greenfield_working_generation(sim.repo_root)

    monkeypatch.setattr(manager, "_run_odylith_smoke", lambda **_: SimpleNamespace(returncode=0, stdout="", stderr=""))
    assert sim.upgrade_to("1.2.4", write_pin=True) == 0
    assert sim.active_runtime_name() == "1.2.4"
    assert sim.pin().odylith_version == "1.2.4"
    generations.require_greenfield_working_generation(sim.repo_root)


@pytest.mark.parametrize("pin_intent", ("old", "target"))
def test_successful_activation_adopts_target_pin_only_after_smoke(tmp_path, monkeypatch, pin_intent):
    sim, pin_path = _installed_case(tmp_path, monkeypatch, pin_intent)
    before_pin = _pin_state(pin_path)
    observed_pins = []

    def smoke(**_):
        observed_pins.append(_pin_state(pin_path))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(manager, "_run_odylith_smoke", smoke)
    assert sim.upgrade_to("1.2.4", write_pin=True) == 0
    assert observed_pins == [before_pin]
    assert sim.pin().odylith_version == "1.2.4"
    assert sim.active_runtime_name() == "1.2.4"
    generations.require_greenfield_working_generation(sim.repo_root)


@pytest.mark.parametrize("entrypoint", ("cli", "manager"))
def test_absent_pin_is_preserved_by_pre_activation_refusal(tmp_path, monkeypatch, entrypoint):
    # Current migration admission rejects this state before activation smoke.
    sim, pin_path = _installed_case(tmp_path, monkeypatch, "absent")
    entry = sim.repo_root / "odylith/index.html"
    before_entry = entry.read_bytes()
    launcher = sim.repo_root / ".odylith/bin/odylith"
    before_launcher = _pin_state(launcher)
    monkeypatch.setattr(manager, "_run_odylith_smoke", lambda **_: pytest.fail("missing pin reached smoke"))
    if entrypoint == "cli":
        assert sim.upgrade_to("1.2.4", write_pin=True) == 2
    else:
        with pytest.raises(ValueError, match="repo pin is missing or invalid"):
            manager.upgrade_install(
                repo_root=sim.repo_root, release_repo="fixture/releases", version="1.2.4", write_pin=True,
            )
    assert not pin_path.exists()
    assert entry.read_bytes() == before_entry
    assert _pin_state(launcher) == before_launcher
    assert sim.active_runtime_name() == "1.2.3"
    failures = [row for row in sim.install_ledger() if row.get("operation") == "upgrade" and row.get("status") == "failed"]
    assert failures == []
    generations.require_greenfield_working_generation(sim.repo_root)
