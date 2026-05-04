from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from odylith.install import manager


def test_start_preflight_uses_fast_runtime_checks_for_bootstrap(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    bin_dir = repo_root / ".odylith" / "bin"
    bin_dir.mkdir(parents=True)
    for name in ("odylith", "odylith-bootstrap"):
        launcher = bin_dir / name
        launcher.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        launcher.chmod(0o755)

    state_path = tmp_path / "state.json"
    profile_path = tmp_path / "consumer-profile.json"
    pin_path = tmp_path / "version.json"
    for path in (state_path, profile_path, pin_path):
        path.write_text("{}", encoding="utf-8")

    calls: dict[str, bool] = {}
    monkeypatch.setattr(manager, "_has_customer_starter_tree", lambda *, repo_root: True)
    monkeypatch.setattr(manager, "install_state_path", lambda *, repo_root: state_path)
    monkeypatch.setattr(manager, "consumer_profile_path", lambda *, repo_root: profile_path)
    monkeypatch.setattr(manager, "version_pin_path", lambda *, repo_root: pin_path)

    def fake_version_status(*, repo_root, deep_integrity=True):
        calls["version_deep_integrity"] = deep_integrity
        return SimpleNamespace(
            repo_role=manager.CONSUMER_REPO_ROLE,
            posture=manager.PINNED_RELEASE_POSTURE,
            runtime_source=manager.PINNED_RUNTIME_SOURCE,
        )

    monkeypatch.setattr(manager, "version_status", fake_version_status)

    def fake_doctor_runtime(*, repo_root, repair, deep_integrity=True):
        calls["doctor_deep_integrity"] = deep_integrity
        return True, []

    monkeypatch.setattr(manager, "doctor_runtime", fake_doctor_runtime)

    preflight = manager.evaluate_start_preflight(repo_root=repo_root)

    assert preflight.lane == "bootstrap"
    assert calls["version_deep_integrity"] is False
    assert calls["doctor_deep_integrity"] is False
