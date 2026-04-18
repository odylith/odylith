from __future__ import annotations

import contextlib
import json
import os
import signal
from pathlib import Path
import time

from odylith.install.fs import display_path, remove_path
from odylith.install.paths import repo_runtime_paths
from odylith.runtime.context_engine import odylith_control_state
from odylith.runtime.context_engine import odylith_context_engine_store
from odylith.runtime.evaluation import odylith_benchmark_runner
from odylith.runtime.memory import odylith_memory_backend
from odylith.runtime.memory import odylith_projection_snapshot
from odylith.runtime.memory import odylith_remote_retrieval

_DAEMON_METADATA_FILENAME = "odylith-context-engine-daemon.json"


def reset_local_state(*, repo_root: str | Path) -> list[str]:
    """Delete local-only mutable Odylith state that can poison future runs."""

    root = Path(repo_root).expanduser().resolve()
    _stop_live_context_engine_daemon(root)
    paths = repo_runtime_paths(root)
    runtime_root = paths.runtime_dir
    targets = (
        paths.cache_dir,
        paths.state_root / "locks",
        paths.state_root / "compass",
        paths.state_root / "subagent_router",
        paths.state_root / "subagent_orchestrator",
        odylith_benchmark_runner.benchmark_root(repo_root=root),
        odylith_projection_snapshot.compiler_root(repo_root=root),
        odylith_memory_backend.local_backend_root(repo_root=root),
        odylith_context_engine_store.sessions_root(repo_root=root),
        odylith_context_engine_store.bootstraps_root(repo_root=root),
        odylith_control_state.state_path(repo_root=root),
        odylith_control_state.events_path(repo_root=root),
        odylith_control_state.timings_path(repo_root=root),
        odylith_context_engine_store.daemon_usage_path(repo_root=root),
        odylith_context_engine_store.proof_surfaces_path(repo_root=root),
        odylith_context_engine_store.pid_path(repo_root=root),
        odylith_context_engine_store.stop_path(repo_root=root),
        odylith_context_engine_store.socket_path(repo_root=root),
        runtime_root / _DAEMON_METADATA_FILENAME,
        odylith_remote_retrieval.remote_state_path(repo_root=root),
        odylith_remote_retrieval.sync_manifest_path(repo_root=root),
    )
    removed: list[str] = []
    seen: set[Path] = set()
    for target in targets:
        resolved = Path(target).expanduser().resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if _remove_target(resolved):
            removed.append(display_path(repo_root=root, path=resolved))
    return removed


def _read_pid(path: Path) -> int:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    return True


def _metadata_pid(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(payload, dict):
        return 0
    try:
        return int(payload.get("pid", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _stop_live_context_engine_daemon(root: Path) -> None:
    pid = _read_pid(odylith_context_engine_store.pid_path(repo_root=root))
    if pid <= 0:
        pid = _metadata_pid(root / ".odylith" / "runtime" / _DAEMON_METADATA_FILENAME)
    if not _pid_alive(pid):
        return
    stop_path = odylith_context_engine_store.stop_path(repo_root=root)
    stop_path.parent.mkdir(parents=True, exist_ok=True)
    stop_path.write_text("stop\n", encoding="utf-8")
    with contextlib.suppress(OSError):
        os.kill(pid, signal.SIGTERM)
    for _ in range(20):
        if not _pid_alive(pid):
            return
        time.sleep(0.1)
    kill_signal = getattr(signal, "SIGKILL", signal.SIGTERM)
    with contextlib.suppress(OSError):
        os.kill(pid, kill_signal)
    for _ in range(20):
        if not _pid_alive(pid):
            return
        time.sleep(0.1)


def _remove_target(path: Path) -> bool:
    if path.is_symlink() or path.exists():
        remove_path(path)
        return True
    return False


__all__ = ["reset_local_state"]
