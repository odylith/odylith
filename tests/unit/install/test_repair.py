from __future__ import annotations

import signal
from pathlib import Path

from odylith.install import repair, runtime


def _repo_root(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    return repo_root


def _make_runtime(repo_root: Path) -> Path:
    version_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    python = version_root / "bin" / "python"
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    python.chmod(0o755)
    return version_root


def test_reset_local_state_preserves_runtime_launcher_and_versions(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    version_root = _make_runtime(repo_root)
    runtime.switch_runtime(repo_root=repo_root, target=version_root)
    runtime.ensure_launcher(repo_root=repo_root, fallback_python=version_root / "bin" / "python")

    cache_file = repo_root / ".odylith" / "cache" / "odylith-context-engine" / "guidance" / "compiled-catalog-v1.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("poisoned\n", encoding="utf-8")

    state_file = repo_root / ".odylith" / "runtime" / "odylith-context-engine-state.v1.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text('{"poisoned":true}\n', encoding="utf-8")

    tuning_file = repo_root / ".odylith" / "subagent_orchestrator" / "tuning.v1.json"
    tuning_file.parent.mkdir(parents=True, exist_ok=True)
    tuning_file.write_text('{"version":"v1"}\n', encoding="utf-8")

    removed = repair.reset_local_state(repo_root=repo_root)

    assert ".odylith/cache" in removed
    assert ".odylith/subagent_orchestrator" in removed
    assert ".odylith/runtime/odylith-context-engine-state.v1.json" in removed
    assert not cache_file.exists()
    assert not state_file.exists()
    assert not tuning_file.exists()
    assert (repo_root / ".odylith" / "bin" / "odylith").is_file()
    assert (repo_root / ".odylith" / "runtime" / "current").is_symlink()
    assert version_root.is_dir()


def test_reset_local_state_stops_live_context_engine_daemon_before_cleanup(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    repo_root = _repo_root(tmp_path)
    pid_path = repo_root / ".odylith" / "runtime" / "odylith-context-engine.pid"
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text("4242\n", encoding="utf-8")

    alive = {"value": True}
    kill_calls: list[int] = []
    kill_signal = getattr(signal, "SIGKILL", signal.SIGTERM)

    monkeypatch.setattr(repair, "_pid_alive", lambda pid: bool(alive["value"]))
    monkeypatch.setattr(repair.time, "sleep", lambda _: None)

    def _fake_kill(pid: int, sig: int) -> None:
        kill_calls.append(sig)
        if sig == kill_signal:
            alive["value"] = False

    monkeypatch.setattr(repair.os, "kill", _fake_kill)

    removed = repair.reset_local_state(repo_root=repo_root)

    assert kill_calls[0] == signal.SIGTERM
    assert kill_calls[-1] == kill_signal
    assert ".odylith/runtime/odylith-context-engine.pid" in removed
