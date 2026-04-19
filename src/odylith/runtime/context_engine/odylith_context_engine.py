"""Serve and inspect the local Odylith Context Engine projections."""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import json
import os
from pathlib import Path
import select
import secrets
import signal
import socket
import subprocess
import socketserver
import sys
import threading
import time
from typing import Any, Mapping, Sequence

from odylith.runtime.governance import agent_governance_intelligence as governance
from odylith.runtime.evaluation import odylith_ablation
from odylith.runtime.evaluation import odylith_benchmark_runner
from odylith.runtime.memory import odylith_memory_backend
from odylith.runtime.memory import odylith_remote_retrieval
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import odylith_context_engine_compass_runtime_cache
from odylith.runtime.context_engine import odylith_context_engine_daemon_wait_runtime
from odylith.runtime.context_engine import odylith_context_engine_dossier_compaction_runtime as dossier_compaction_runtime
from odylith.runtime.context_engine import odylith_context_engine_packet_session_runtime as packet_session_runtime
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.context_engine import runtime_read_session
from odylith.runtime.common.command_surface import module_invocation

_WORKSPACE_PYTHON_HANDOFF_ENV = "ODYLITH_CONTEXT_ENGINE_WORKSPACE_PYTHON_HANDOFF"
_WORKSPACE_PYTHON_OPT_IN_ENV = "ODYLITH_CONTEXT_ENGINE_ALLOW_WORKSPACE_PYTHON"
_BACKGROUND_AUTOSPAWN_ALLOW_ENV = "ODYLITH_CONTEXT_ENGINE_ALLOW_BACKGROUND_AUTOSPAWN"
_BACKGROUND_AUTOSPAWN_DISABLE_ENV = "ODYLITH_CONTEXT_ENGINE_DISABLE_BACKGROUND_AUTOSPAWN"
_AUTOSPAWN_IDLE_TIMEOUT_ENV = "ODYLITH_CONTEXT_ENGINE_AUTOSPAWN_IDLE_TIMEOUT_SECONDS"
_WORKSPACE_PYTHON_SUPPORT_CACHE: dict[str, bool] = {}
_REASONING_SCOPE = "reasoning"
_DAEMON_METADATA_FILENAME = "odylith-context-engine-daemon.json"
_DAEMON_SPAWN_REASON_EXPLICIT = "explicit"
_DAEMON_SPAWN_REASON_AUTOSPAWN = "autospawn"
_DEFAULT_AUTOSPAWN_IDLE_TIMEOUT_SECONDS = 120
_DAEMON_REQUEST_MAX_BYTES = 64 * 1024
_DAEMON_ACTIVITY_LOCK = threading.Lock()
_DAEMON_ACTIVITY: dict[str, float] = {}
_DAEMON_SESSION_ACTIVITY: dict[str, dict[str, float]] = {}


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith context-engine",
        description="Manage the local Odylith Context Engine projection store.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument(
        "--client-mode",
        choices=("auto", "local", "daemon"),
        default="auto",
        help="Use the daemon-backed thin client when available; `local` bypasses the daemon.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    warmup = subparsers.add_parser("warmup", help="Build or refresh local projections.")
    warmup.add_argument("--force", action="store_true", help="Force rebuilding all projections.")
    warmup.add_argument(
        "--scope",
        choices=("default", "reasoning", "full"),
        default="full",
        help="Projection scope to build (`full` includes engineering/code/test intelligence).",
    )

    serve = subparsers.add_parser("serve", help="Continuously keep projections warm.")
    serve.add_argument("--force", action="store_true", help="Force rebuilding all projections on the first pass.")
    serve.add_argument("--interval-seconds", type=int, default=5, help="Polling interval for the runtime loop.")
    serve.add_argument(
        "--watcher-backend",
        choices=("auto", "watchman", "watchdog", "git-fsmonitor", "poll"),
        default="auto",
        help="Invalidation backend to use for the serve loop.",
    )
    serve.add_argument(
        "--scope",
        choices=("default", "reasoning", "full"),
        default="full",
        help="Projection scope to maintain in the serve loop.",
    )
    serve.add_argument(
        "--spawn-reason",
        choices=(_DAEMON_SPAWN_REASON_EXPLICIT, _DAEMON_SPAWN_REASON_AUTOSPAWN),
        default=_DAEMON_SPAWN_REASON_EXPLICIT,
        help=argparse.SUPPRESS,
    )
    serve.add_argument(
        "--idle-timeout-seconds",
        type=int,
        default=0,
        help=argparse.SUPPRESS,
    )

    query = subparsers.add_parser(
        "query",
        help="Search the local projection store and report when a raw repo scan is still recommended.",
    )
    query.add_argument("text", help="Query text.")
    query.add_argument("--limit", type=int, default=12, help="Maximum result count.")
    query.add_argument(
        "--kind",
        action="append",
        default=[],
        help="Restrict to one or more entity kinds (repeatable).",
    )

    surface_read = subparsers.add_parser(
        "surface-read",
        help="Read dashboard surface list/detail/document payloads from the local runtime store.",
    )
    surface_read.add_argument(
        "entity",
        choices=(
            "backlog-list",
            "backlog-detail",
            "backlog-document",
            "governance-detail",
            "registry-list",
            "registry-detail",
        ),
        help="Surface payload to read.",
    )
    surface_read.add_argument("--workstream", default="", help="Workstream id for backlog detail/document reads.")
    surface_read.add_argument("--component", default="", help="Component id for registry detail reads.")
    surface_read.add_argument(
        "--path",
        action="append",
        default=[],
        help="Optional repo-relative path seed for governance-detail reads (repeatable).",
    )
    surface_read.add_argument("--session-id", default="", help="Optional stable session identifier for governance-detail reads.")
    surface_read.add_argument(
        "--claim-path",
        action="append",
        default=[],
        help="Optional repo-relative claimed path for governance-detail reads (repeatable).",
    )
    surface_read.add_argument(
        "--working-tree-scope",
        choices=("repo", "session"),
        default="repo",
        help="Governance-detail working-tree scope when session claims are provided.",
    )
    surface_read.add_argument(
        "--view",
        choices=("spec", "plan"),
        default="spec",
        help="Document variant for backlog-document reads.",
    )

    context = subparsers.add_parser("context", help="Resolve one repo entity/path into a local context dossier.")
    context.add_argument("ref", help="Entity id, component name, or repo-relative path.")
    context.add_argument(
        "--kind",
        choices=(
            "workstream",
            "release",
            "plan",
            "bug",
            "diagram",
            "component",
            "doc",
            "runbook",
            "code",
            "test",
            *store.ENGINEERING_NOTE_KINDS,
        ),
        default="",
        help="Optional explicit entity kind.",
    )
    context.add_argument("--event-limit", type=int, default=2, help="Maximum linked agent events to return.")
    context.add_argument("--relation-limit", type=int, default=2, help="Maximum relation rows to return.")

    impact = subparsers.add_parser("impact", help="Resolve architecture impact for one or more changed paths.")
    impact.add_argument("paths", nargs="*", help="Changed repo-relative paths.")
    impact.add_argument("--working-tree", action="store_true", help="Use meaningful changed paths from the git working tree.")
    impact.add_argument(
        "--working-tree-scope",
        choices=("repo", "session"),
        default="repo",
        help="When `--working-tree` is set, use the full repo dirty set or only paths scoped by the explicit session seed paths.",
    )
    impact.add_argument("--session-id", default="", help="Optional stable session identifier for session-scoped working-tree resolution.")
    impact.add_argument(
        "--claim-path",
        action="append",
        default=[],
        help="Extra repo-relative paths to treat as session-owned seeds when `--working-tree-scope session` is used.",
    )
    impact.add_argument("--test-limit", type=int, default=12, help="Maximum recommended test rows.")

    architecture = subparsers.add_parser(
        "architecture",
        help="Resolve plane/stack topology grounding and diagram-watch gaps for one or more changed paths.",
    )
    architecture.add_argument("paths", nargs="*", help="Changed repo-relative paths.")
    architecture.add_argument("--working-tree", action="store_true", help="Use meaningful changed paths from the git working tree.")
    architecture.add_argument(
        "--working-tree-scope",
        choices=("repo", "session"),
        default="repo",
        help="When `--working-tree` is set, use the full repo dirty set or only paths scoped by the explicit session seed paths.",
    )
    architecture.add_argument("--session-id", default="", help="Optional stable session identifier for session-scoped working-tree resolution.")
    architecture.add_argument(
        "--claim-path",
        action="append",
        default=[],
        help="Extra repo-relative paths to treat as session-owned seeds when `--working-tree-scope session` is used.",
    )

    governance_slice = subparsers.add_parser(
        "governance-slice",
        help="Build a compact governance and delivery-truth packet for paths, workstreams, or components.",
    )
    governance_slice.add_argument("paths", nargs="*", help="Optional explicit repo-relative changed paths.")
    governance_slice.add_argument("--workstream", default="", help="Optional explicit workstream id.")
    governance_slice.add_argument("--component", default="", help="Optional explicit component id.")
    governance_slice.add_argument("--working-tree", action="store_true", help="Use meaningful changed paths from the git working tree.")
    governance_slice.add_argument(
        "--working-tree-scope",
        choices=("repo", "session"),
        default="repo",
        help="When `--working-tree` is set, use the full repo dirty set or only paths scoped by the explicit session seed paths.",
    )
    governance_slice.add_argument("--session-id", default="", help="Optional stable session identifier for session-scoped routing.")
    governance_slice.add_argument(
        "--claim-path",
        action="append",
        default=[],
        help="Extra repo-relative paths to treat as session-owned seeds when `--working-tree-scope session` is used.",
    )

    session_brief = subparsers.add_parser(
        "session-brief",
        help="Build one deterministic coding-agent session dossier and refresh the local session heartbeat.",
    )
    session_brief.add_argument("paths", nargs="*", help="Optional explicit repo-relative changed paths.")
    session_brief.add_argument("--working-tree", action="store_true", help="Include meaningful changed paths from the git working tree.")
    session_brief.add_argument(
        "--working-tree-scope",
        choices=("repo", "session"),
        default="session",
        help="When `--working-tree` is set, use the full repo dirty set or only paths scoped to this session's explicit/claimed history.",
    )
    session_brief.add_argument("--session-id", default="", help="Optional stable session identifier.")
    session_brief.add_argument("--workstream", default="", help="Optional explicit workstream id.")
    session_brief.add_argument("--intent", default="", help="Optional short session intent summary.")
    session_brief.add_argument(
        "--surface",
        action="append",
        default=[],
        help="Generated/dashboard surfaces this session expects to touch (repeatable).",
    )
    session_brief.add_argument(
        "--visible-text",
        action="append",
        default=[],
        help="Copied UI or screenshot-visible text to treat as grounding literals (repeatable).",
    )
    session_brief.add_argument("--active-tab", default="", help="Optional active dashboard tab or route hint.")
    session_brief.add_argument("--user-turn-id", default="", help="Optional stable upstream turn identifier.")
    session_brief.add_argument(
        "--supersedes-turn-id",
        default="",
        help="Optional prior turn id this turn supersedes for narration purposes.",
    )
    session_brief.add_argument(
        "--claim-mode",
        choices=("shared", "exclusive"),
        default="shared",
        help="Advisory lease mode for this session's claimed workstream/files/surfaces.",
    )
    session_brief.add_argument(
        "--claim-path",
        action="append",
        default=[],
        help="Extra repo-relative paths this session expects to touch even if they are not yet changed.",
    )
    session_brief.add_argument(
        "--lease-seconds",
        type=int,
        default=15 * 60,
        help="Advisory lease duration for the session claim record.",
    )

    bootstrap = subparsers.add_parser(
        "bootstrap-session",
        help="Build a compact fresh-session bootstrap packet and refresh the local session heartbeat.",
    )
    bootstrap.add_argument("paths", nargs="*", help="Optional explicit repo-relative changed paths.")
    bootstrap.add_argument("--working-tree", action="store_true", help="Include meaningful changed paths from the git working tree.")
    bootstrap.add_argument(
        "--working-tree-scope",
        choices=("repo", "session"),
        default="session",
        help="When `--working-tree` is set, use the full repo dirty set or only paths scoped to this session's explicit/claimed history.",
    )
    bootstrap.add_argument("--session-id", default="", help="Optional stable session identifier.")
    bootstrap.add_argument("--workstream", default="", help="Optional explicit workstream id.")
    bootstrap.add_argument("--intent", default="", help="Optional short session intent summary.")
    bootstrap.add_argument(
        "--surface",
        action="append",
        default=[],
        help="Generated/dashboard surfaces this session expects to touch (repeatable).",
    )
    bootstrap.add_argument(
        "--visible-text",
        action="append",
        default=[],
        help="Copied UI or screenshot-visible text to treat as grounding literals (repeatable).",
    )
    bootstrap.add_argument("--active-tab", default="", help="Optional active dashboard tab or route hint.")
    bootstrap.add_argument("--user-turn-id", default="", help="Optional stable upstream turn identifier.")
    bootstrap.add_argument(
        "--supersedes-turn-id",
        default="",
        help="Optional prior turn id this turn supersedes for narration purposes.",
    )
    bootstrap.add_argument(
        "--claim-mode",
        choices=("shared", "exclusive"),
        default="shared",
        help="Advisory lease mode for this session's claimed workstream/files/surfaces.",
    )
    bootstrap.add_argument(
        "--claim-path",
        action="append",
        default=[],
        help="Extra repo-relative paths this session expects to touch even if they are not yet changed.",
    )
    bootstrap.add_argument(
        "--lease-seconds",
        type=int,
        default=15 * 60,
        help="Advisory lease duration for the session claim record.",
    )
    bootstrap.add_argument("--doc-limit", type=int, default=8, help="Maximum relevant docs to include.")
    bootstrap.add_argument("--command-limit", type=int, default=10, help="Maximum recommended commands to include.")
    bootstrap.add_argument("--test-limit", type=int, default=8, help="Maximum recommended tests to include.")

    doctor = subparsers.add_parser("doctor", help="Report local watcher readiness and optionally bootstrap the best fallback.")
    doctor.add_argument(
        "--bootstrap-watcher",
        action="store_true",
        help="Bootstrap Git fsmonitor when it is the best available local watcher-assisted fallback.",
    )

    benchmark = subparsers.add_parser(
        "benchmark",
        help="Run the local benchmark harness with explicit quick versus proof profiles.",
    )
    benchmark.add_argument(
        "--profile",
        choices=tuple(odylith_benchmark_runner.BENCHMARK_PROFILES),
        default=odylith_benchmark_runner.DEFAULT_CLI_BENCHMARK_PROFILE,
        help=(
            "Benchmark profile to run. `quick` is the default bounded live matched-pair smoke lane; "
            "`proof` is the full-corpus live publication proof for `odylith_on` versus `odylith_off`; "
            "`diagnostic` isolates packet and prompt creation without running the live host pair."
        ),
    )
    benchmark.add_argument(
        "--mode",
        action="append",
        default=[],
        choices=tuple(odylith_benchmark_runner.PUBLIC_CLI_MODES),
        help=(
            "Benchmark mode to run (repeatable). Defaults follow the selected profile; "
            "use `odylith_off` for the raw host CLI lane."
        ),
    )
    benchmark.add_argument(
        "--cache-profile",
        action="append",
        default=[],
        choices=tuple(sorted({"cold", *odylith_benchmark_runner.DEFAULT_CACHE_PROFILES})),
        help=(
            "Benchmark cache profile to run (repeatable). Defaults follow the selected profile; "
            "add `cold` when you explicitly want cold process-cache measurement."
        ),
    )
    benchmark.add_argument(
        "--case-id",
        action="append",
        default=[],
        help="Restrict execution to one or more seeded benchmark case ids (repeatable).",
    )
    benchmark.add_argument(
        "--family",
        action="append",
        default=[],
        help="Restrict execution to one or more benchmark families (repeatable).",
    )
    benchmark.add_argument(
        "--shard-count",
        type=int,
        default=1,
        help="Split the selected scenario set into N deterministic shards.",
    )
    benchmark.add_argument(
        "--shard-index",
        type=int,
        default=1,
        help="1-based shard index to run when `--shard-count` is set.",
    )
    benchmark.add_argument("--limit", type=int, default=0, help="Optional maximum number of benchmark scenarios to execute.")
    benchmark.add_argument(
        "--no-write-report",
        action="store_true",
        help="Do not write the latest/history benchmark report files under `.odylith/runtime/odylith-benchmarks/`.",
    )
    benchmark.add_argument(
        "--json",
        action="store_true",
        help="Print the full machine-readable report instead of only the compact summary.",
    )

    subparsers.add_parser("memory-snapshot", help="Show the current typed local memory/retrieval snapshot.")
    odylith_switch = subparsers.add_parser(
        "odylith-switch",
        help="Inspect or persist the Odylith ablation switch.",
    )
    odylith_mode = odylith_switch.add_mutually_exclusive_group()
    odylith_mode.add_argument("--enable", action="store_true", help="Enable Odylith.")
    odylith_mode.add_argument("--disable", action="store_true", help="Disable Odylith and related contracts.")
    odylith_mode.add_argument("--clear", action="store_true", help="Clear the persisted local switch file.")
    odylith_switch.add_argument("--note", default="", help="Optional note to store with the local switch file.")
    remote_sync = subparsers.add_parser(
        "odylith-remote-sync",
        help="Feed the current Odylith evidence set into an optional Vespa remote retrieval service.",
    )
    remote_sync.add_argument("--dry-run", action="store_true", help="Report what would be synced without remote writes.")
    subparsers.add_parser("status", help="Show runtime daemon/store status.")
    subparsers.add_parser("stop", help="Stop a running runtime daemon loop.")
    return parser.parse_args(argv)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _terminate_background_process(process: subprocess.Popen[Any], *, timeout_seconds: float = 2.0) -> bool:
    if process.poll() is not None:
        return True
    process_pid = int(getattr(process, "pid", 0) or 0)
    if os.name == "posix" and process_pid > 0:
        with contextlib.suppress(OSError, ProcessLookupError):
            os.killpg(process_pid, signal.SIGTERM)
    else:
        with contextlib.suppress(Exception):
            process.terminate()
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=timeout_seconds)
    if process.poll() is not None:
        return True
    kill_signal = getattr(signal, "SIGKILL", signal.SIGTERM)
    if os.name == "posix" and process_pid > 0:
        with contextlib.suppress(OSError, ProcessLookupError):
            os.killpg(process_pid, kill_signal)
    else:
        with contextlib.suppress(Exception):
            process.kill()
    with contextlib.suppress(Exception):
        process.wait(timeout=timeout_seconds)
    return process.poll() is not None


def _candidate_workspace_python(*, repo_root: Path) -> Path | None:
    candidate = Path(repo_root).resolve() / ".venv" / "bin" / "python"
    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        return None
    return candidate


def _python_supports_odylith_memory_backend(python_path: Path) -> bool:
    token = str(Path(python_path))
    cached = _WORKSPACE_PYTHON_SUPPORT_CACHE.get(token)
    if cached is not None:
        return cached
    try:
        completed = subprocess.run(
            [
                token,
                "-c",
                (
                    "import importlib.util; "
                    "mods=('lancedb','pyarrow','tantivy'); "
                    "raise SystemExit(0 if all(importlib.util.find_spec(m) is not None for m in mods) else 1)"
                ),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        _WORKSPACE_PYTHON_SUPPORT_CACHE[token] = False
        return False
    supported = int(completed.returncode) == 0
    _WORKSPACE_PYTHON_SUPPORT_CACHE[token] = supported
    return supported


def _preferred_odylith_python(*, repo_root: Path) -> str:
    current_python = str(Path(sys.executable))
    if os.environ.get(_WORKSPACE_PYTHON_HANDOFF_ENV):
        return current_python
    if str(os.environ.get(_WORKSPACE_PYTHON_OPT_IN_ENV, "")).strip() != "1":
        return current_python
    if odylith_memory_backend.backend_dependencies_available():
        return current_python
    candidate = _candidate_workspace_python(repo_root=repo_root)
    if candidate is None or str(candidate) == current_python:
        return current_python
    if not _python_supports_odylith_memory_backend(candidate):
        return current_python
    return str(candidate)


def _run_workspace_python_handoff(*, repo_root: Path, python_path: str, argv: Sequence[str]) -> int:
    env = dict(os.environ)
    env[_WORKSPACE_PYTHON_HANDOFF_ENV] = "1"
    completed = subprocess.run(
        module_invocation("context-engine", *list(argv), python_path=python_path),
        cwd=str(Path(repo_root).resolve()),
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if completed.stdout:
        sys.stdout.write(completed.stdout)
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    return int(completed.returncode)


def _read_pid(path: Path) -> int | None:
    if not path.is_file():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _daemon_metadata_path(*, repo_root: Path) -> Path:
    return (store.runtime_root(repo_root=repo_root) / _DAEMON_METADATA_FILENAME).resolve()


def _read_daemon_metadata(*, repo_root: Path) -> dict[str, Any]:
    path = _daemon_metadata_path(repo_root=repo_root)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, Mapping):
        return {}
    try:
        idle_timeout_seconds = int(payload.get("idle_timeout_seconds", 0) or 0)
    except (TypeError, ValueError):
        idle_timeout_seconds = 0
    spawn_reason = str(payload.get("spawn_reason", "")).strip().lower()
    if spawn_reason not in {_DAEMON_SPAWN_REASON_EXPLICIT, _DAEMON_SPAWN_REASON_AUTOSPAWN}:
        spawn_reason = ""
    try:
        pid = int(payload.get("pid", 0) or 0)
    except (TypeError, ValueError):
        pid = 0
    return {
        "pid": pid,
        "spawn_reason": spawn_reason,
        "idle_timeout_seconds": max(0, idle_timeout_seconds),
        "started_utc": str(payload.get("started_utc", "")).strip(),
        "auth_token": str(payload.get("auth_token", "")).strip(),
    }


def _harden_private_runtime_artifact(path: Path, *, mode: int = 0o600) -> None:
    with contextlib.suppress(OSError):
        os.chmod(path, mode)


def _write_daemon_metadata(*, repo_root: Path, spawn_reason: str, idle_timeout_seconds: int, auth_token: str = "") -> None:
    normalized_reason = str(spawn_reason or _DAEMON_SPAWN_REASON_EXPLICIT).strip().lower()
    if normalized_reason not in {_DAEMON_SPAWN_REASON_EXPLICIT, _DAEMON_SPAWN_REASON_AUTOSPAWN}:
        normalized_reason = _DAEMON_SPAWN_REASON_EXPLICIT
    path = _daemon_metadata_path(repo_root=repo_root)
    odylith_context_cache.write_json_if_changed(
        repo_root=repo_root,
        path=path,
        payload={
            "pid": os.getpid(),
            "spawn_reason": normalized_reason,
            "idle_timeout_seconds": max(0, int(idle_timeout_seconds)),
            "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "auth_token": str(auth_token or "").strip(),
        },
        lock_key=str(path),
    )
    _harden_private_runtime_artifact(path)


def _write_pid(*, repo_root: Path) -> None:
    path = store.pid_path(repo_root=repo_root)
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=path,
        content=f"{os.getpid()}\n",
        lock_key=str(path),
    )
    _harden_private_runtime_artifact(path)


def _clear_pid(*, repo_root: Path) -> None:
    path = store.pid_path(repo_root=repo_root)
    with odylith_context_cache.advisory_lock(repo_root=repo_root, key=str(path)):
        if path.exists():
            path.unlink()


def _clear_daemon_metadata(*, repo_root: Path) -> None:
    path = _daemon_metadata_path(repo_root=repo_root)
    with odylith_context_cache.advisory_lock(repo_root=repo_root, key=str(path)):
        if path.exists():
            path.unlink()


def _daemon_owner_pid(*, repo_root: Path) -> int | None:
    pid = _read_pid(store.pid_path(repo_root=repo_root))
    if pid:
        return pid
    metadata_pid = int(_read_daemon_metadata(repo_root=repo_root).get("pid", 0) or 0)
    return metadata_pid or None


def _runtime_status_payload(*, repo_root: Path) -> dict[str, Any]:
    prune_summary = store.prune_runtime_records(repo_root=repo_root)
    state = store.read_runtime_state(repo_root=repo_root)
    pid = _read_pid(store.pid_path(repo_root=repo_root))
    alive = bool(pid and _pid_alive(pid))
    watcher_report = store.watcher_backend_report(repo_root=repo_root)
    pid_file = store.pid_path(repo_root=repo_root)
    socket_file = store.socket_path(repo_root=repo_root)
    stop_file = store.stop_path(repo_root=repo_root)
    metadata_file = _daemon_metadata_path(repo_root=repo_root)
    daemon_metadata = _read_daemon_metadata(repo_root=repo_root)
    daemon_transport = _read_daemon_transport(repo_root=repo_root) or {}
    daemon_usage = store.read_runtime_daemon_usage(repo_root=repo_root)
    stale_daemon_artifacts: list[str] = []
    if pid_file.exists() and not alive:
        stale_daemon_artifacts.append("pid")
    if socket_file.exists() and not alive:
        stale_daemon_artifacts.append("socket")
    if stop_file.exists() and not alive:
        stale_daemon_artifacts.append("stop")
    if metadata_file.exists() and not alive:
        stale_daemon_artifacts.append("metadata")
    active_sessions = store.list_session_states(repo_root=repo_root, prune=False)
    current_backend = state.get(
        "watcher_backend",
        watcher_report.get("preferred_backend", store.preferred_watcher_backend(repo_root=repo_root)),
    )
    preferred_backend = watcher_report.get("preferred_backend", store.preferred_watcher_backend(repo_root=repo_root))
    odylith_switch = odylith_ablation.build_odylith_switch_snapshot(repo_root=repo_root)
    optimization_snapshot = store.load_runtime_optimization_snapshot(repo_root=repo_root)
    evaluation_snapshot = store.load_runtime_evaluation_snapshot(repo_root=repo_root)
    orchestration_adoption_snapshot = store.load_orchestration_adoption_snapshot(repo_root=repo_root)
    memory_snapshot = store.load_runtime_memory_snapshot(
        repo_root=repo_root,
        optimization_snapshot=optimization_snapshot,
        evaluation_snapshot=evaluation_snapshot,
    )
    benchmark_report = odylith_benchmark_runner.compact_report_summary(
        odylith_benchmark_runner.load_latest_benchmark_report(repo_root=repo_root)
    )
    benchmark_progress = odylith_benchmark_runner.compact_progress_summary(
        odylith_benchmark_runner.load_benchmark_progress(repo_root=repo_root)
    )
    return {
        "repo_root": str(repo_root),
        "daemon_pid": pid or 0,
        "daemon_alive": alive,
        "daemon_spawn_reason": str(daemon_metadata.get("spawn_reason", "")).strip(),
        "daemon_idle_timeout_seconds": int(daemon_metadata.get("idle_timeout_seconds", 0) or 0),
        "daemon_started_utc": str(daemon_metadata.get("started_utc", "")).strip(),
        "watcher_backend": current_backend,
        "preferred_watcher_backend": preferred_backend,
        "watcher_report": watcher_report,
        "daemon_restart_recommended": bool(alive and str(current_backend).strip() != str(preferred_backend).strip()),
        "updated_utc": state.get("updated_utc", ""),
        "projection_fingerprint": state.get("projection_fingerprint", ""),
        "projection_scope": state.get("projection_scope", ""),
        "updated_projections": list(state.get("updated_projections", [])),
        "active_sessions": len(active_sessions),
        "bootstrap_packets": int(prune_summary.get("bootstrap_packets", 0) or 0),
        "pruned_runtime_records": prune_summary,
        "projection_snapshot_path": str(store.projection_snapshot_path(repo_root=repo_root)),
        "state_path": str(store.state_path(repo_root=repo_root)),
        "socket_path": str(store.socket_path(repo_root=repo_root)),
        "daemon_transport": daemon_transport,
        "daemon_usage": daemon_usage,
        "stale_daemon_artifacts": stale_daemon_artifacts,
        "timings": store.load_runtime_timing_summary(repo_root=repo_root, limit=8),
        "odylith_switch": odylith_switch,
        "memory_snapshot": memory_snapshot,
        "optimization_snapshot": optimization_snapshot,
        "evaluation_snapshot": evaluation_snapshot,
        "orchestration_adoption_snapshot": orchestration_adoption_snapshot,
        "benchmark_report": benchmark_report,
        "benchmark_progress": benchmark_progress,
    }


def _memory_area_count_summary(memory_areas: Mapping[str, Any]) -> str:
    counts = dict(memory_areas.get("counts", {})) if isinstance(memory_areas.get("counts"), Mapping) else {}
    parts = [
        f"{label}={int(counts.get(label, 0) or 0)}"
        for label in ("strong", "partial", "cold", "planned", "disabled")
        if int(counts.get(label, 0) or 0) > 0
    ]
    return ", ".join(parts)


def _print_runtime_status(payload: Mapping[str, Any]) -> None:
    print("odylith context engine status")
    print(f"- repo_root: {payload.get('repo_root', '')}")
    daemon_pid = int(payload.get("daemon_pid", 0) or 0)
    print(f"- daemon_pid: {daemon_pid or '-'}")
    print(f"- daemon_alive: {'yes' if bool(payload.get('daemon_alive')) else 'no'}")
    daemon_spawn_reason = str(payload.get("daemon_spawn_reason", "")).strip()
    if daemon_spawn_reason:
        print(f"- daemon_spawn_reason: {daemon_spawn_reason}")
    daemon_idle_timeout_seconds = int(payload.get("daemon_idle_timeout_seconds", 0) or 0)
    if daemon_idle_timeout_seconds > 0:
        print(f"- daemon_idle_timeout_seconds: {daemon_idle_timeout_seconds}")
    daemon_started_utc = str(payload.get("daemon_started_utc", "")).strip()
    if daemon_started_utc:
        print(f"- daemon_started_utc: {daemon_started_utc}")
    print(f"- watcher_backend: {payload.get('watcher_backend', store.preferred_watcher_backend())}")
    print(f"- preferred_watcher_backend: {payload.get('preferred_watcher_backend', store.preferred_watcher_backend())}")
    watcher_report = payload.get("watcher_report", {})
    if isinstance(watcher_report, Mapping):
        git_fsmonitor_state = "active" if bool(watcher_report.get("git_fsmonitor_active")) else "supported" if bool(watcher_report.get("git_fsmonitor_supported")) else "unavailable"
        print(
            "- watcher_capabilities: "
            f"watchman={'yes' if bool(watcher_report.get('watchman_available')) else 'no'}, "
            f"watchdog={'yes' if bool(watcher_report.get('watchdog_available')) else 'no'}, "
            f"git_fsmonitor={git_fsmonitor_state}"
        )
        if bool(watcher_report.get("bootstrap_recommended")):
            print("- watcher_bootstrap_recommended: yes")
    if bool(payload.get("daemon_restart_recommended")):
        print("- daemon_restart_recommended: yes")
    print(f"- updated_utc: {payload.get('updated_utc', '')}")
    print(f"- projection_fingerprint: {payload.get('projection_fingerprint', '')}")
    print(f"- projection_scope: {payload.get('projection_scope', '')}")
    print(f"- updated_projections: {', '.join(payload.get('updated_projections', [])) or 'none'}")
    print(f"- active_sessions: {payload.get('active_sessions', 0)}")
    print(f"- bootstrap_packets: {payload.get('bootstrap_packets', 0)}")
    print(f"- projection_snapshot_path: {payload.get('projection_snapshot_path', '')}")
    print(f"- state_path: {payload.get('state_path', '')}")
    print(f"- socket_path: {payload.get('socket_path', '')}")
    daemon_transport = payload.get("daemon_transport", {})
    if isinstance(daemon_transport, Mapping) and str(daemon_transport.get("transport", "")).strip():
        print(f"- daemon_transport: {daemon_transport.get('transport', '')}")
    daemon_usage = payload.get("daemon_usage", {})
    if isinstance(daemon_usage, Mapping):
        workspace_key = str(daemon_usage.get("workspace_key", "")).strip()
        if workspace_key:
            print(f"- daemon_workspace_key: {workspace_key}")
        request_count = int(daemon_usage.get("request_count", 0) or 0)
        session_scoped_request_count = int(daemon_usage.get("session_scoped_request_count", 0) or 0)
        unique_session_namespace_count = int(daemon_usage.get("unique_session_namespace_count", 0) or 0)
        if request_count > 0:
            print(
                "- daemon_usage: "
                f"requests={request_count}, "
                f"session_scoped={session_scoped_request_count}, "
                f"unique_session_namespaces={unique_session_namespace_count}"
            )
        last_command = str(daemon_usage.get("last_command", "")).strip()
        last_request_utc = str(daemon_usage.get("last_request_utc", "")).strip()
        if last_command or last_request_utc:
            print(
                "- daemon_last_request: "
                f"command={last_command or '-'}, "
                f"updated_utc={last_request_utc or '-'}"
            )
        last_session_namespace = str(daemon_usage.get("last_session_namespace", "")).strip()
        if last_session_namespace:
            print(f"- daemon_last_session_namespace: {last_session_namespace}")
    stale_artifacts = payload.get("stale_daemon_artifacts", [])
    if isinstance(stale_artifacts, list) and stale_artifacts:
        print(f"- stale_daemon_artifacts: {', '.join(str(item) for item in stale_artifacts if str(item).strip())}")
    pruned = payload.get("pruned_runtime_records", {})
    if isinstance(pruned, Mapping):
        pruned_summary = ", ".join(
            f"{key}={int(value)}"
            for key, value in pruned.items()
            if str(key).endswith("_pruned") and int(value or 0) > 0
        )
        if pruned_summary:
            print(f"- pruned_runtime_records: {pruned_summary}")
    timings = payload.get("timings", {})
    operations = timings.get("operations", []) if isinstance(timings, Mapping) else []
    if isinstance(operations, list) and operations:
        summary = ", ".join(
            f"{str(row.get('operation', '')).strip()}={float(row.get('latest_ms', 0.0) or 0.0):.1f}ms"
            for row in operations[:4]
            if isinstance(row, Mapping)
        )
        if summary:
            print(f"- recent_timing_ops: {summary}")
    odylith_switch = payload.get("odylith_switch", {})
    odylith_enabled = True
    if isinstance(odylith_switch, Mapping):
        odylith_enabled = bool(odylith_switch.get("enabled", True))
        print(
            "- odylith: "
            f"{'enabled' if odylith_enabled else 'disabled'}, "
            f"source={str(odylith_switch.get('source', '')).strip() or 'default'}, "
            f"mode={str(odylith_switch.get('mode', '')).strip() or ('enabled' if odylith_enabled else 'disabled')}"
        )
        if str(odylith_switch.get("note", "")).strip():
            print(f"- odylith_note: {str(odylith_switch.get('note', '')).strip()}")
    if not odylith_enabled:
        print("- odylith_related_contracts: suppressed_for_ablation")
        return
    memory_snapshot = payload.get("memory_snapshot", {})
    if isinstance(memory_snapshot, Mapping):
        engine = memory_snapshot.get("engine", {})
        runtime_state = memory_snapshot.get("runtime_state", {})
        guidance_catalog = memory_snapshot.get("guidance_catalog", {})
        entity_counts = memory_snapshot.get("entity_counts", {})
        memory_areas = memory_snapshot.get("memory_areas", {})
        judgment_memory = memory_snapshot.get("judgment_memory", {})
        degraded_fallback = memory_snapshot.get("repo_scan_degraded_fallback", {})
        governance_runtime_first = memory_snapshot.get("governance_runtime_first", {})
        backend = engine.get("backend", {}) if isinstance(engine, Mapping) else {}
        target_backend = engine.get("target_backend", {}) if isinstance(engine, Mapping) else {}
        backend_transition = engine.get("backend_transition", {}) if isinstance(engine, Mapping) else {}
        if isinstance(runtime_state, Mapping) and isinstance(guidance_catalog, Mapping) and isinstance(entity_counts, Mapping):
            print(
                "- memory: "
                f"actual={str(backend.get('storage', '')).strip() or '-'} / {str(backend.get('sparse_recall', '')).strip() or '-'}, "
                f"target={str(target_backend.get('storage', '')).strip() or '-'} / {str(target_backend.get('sparse_recall', '')).strip() or '-'}, "
                f"transition={str(backend_transition.get('status', '')).strip() or '-'}, "
                f"source={str(memory_snapshot.get('backend_transition', {}).get('evidence_source', '')).strip() or 'live_backend'}, "
                f"indexed_entities={int(entity_counts.get('indexed_entity_count', 0) or 0)}, "
                f"guidance_chunks={int(guidance_catalog.get('chunk_count', 0) or 0)}, "
                f"bootstrap_packets={int(runtime_state.get('bootstrap_packets', 0) or 0)}"
            )
        if isinstance(memory_areas, Mapping):
            count_summary = _memory_area_count_summary(memory_areas)
            if count_summary:
                print(f"- memory_areas: {count_summary}")
            headline = str(memory_areas.get("headline", "")).strip()
            if headline:
                print(f"- memory_headline: {headline}")
        if isinstance(judgment_memory, Mapping):
            count_summary = _memory_area_count_summary(judgment_memory)
            if count_summary:
                print(f"- judgment_memory: {count_summary}")
            headline = str(judgment_memory.get("headline", "")).strip()
            if headline:
                print(f"- judgment_headline: {headline}")
        remote_retrieval = memory_snapshot.get("remote_retrieval", {})
        if isinstance(remote_retrieval, Mapping):
            print(
                "- remote_retrieval: "
                f"enabled={'yes' if bool(remote_retrieval.get('enabled')) else 'no'}, "
                f"mode={str(remote_retrieval.get('mode', '')).strip() or 'disabled'}, "
                f"provider={str(remote_retrieval.get('provider', '')).strip() or '-'}"
            )
        if isinstance(degraded_fallback, Mapping):
            print(
                "- repo_scan_degraded_fallback: "
                f"rate={float(degraded_fallback.get('repo_scan_degraded_fallback_rate', 0.0) or 0.0):.3f}, "
                f"reasons={','.join(str(key) for key in dict(degraded_fallback.get('repo_scan_degraded_reason_distribution', {})).keys()) or '-'}"
            )
            print(
                "- grounding_failure_split: "
                f"hard={float(degraded_fallback.get('hard_grounding_failure_rate', 0.0) or 0.0):.3f}, "
                f"soft={float(degraded_fallback.get('soft_widening_rate', 0.0) or 0.0):.3f}, "
                f"visible_receipt={float(degraded_fallback.get('visible_fallback_receipt_rate', 0.0) or 0.0):.3f}"
            )
        if isinstance(governance_runtime_first, Mapping):
            print(
                "- governance_runtime_first: "
                f"usage_rate={float(governance_runtime_first.get('usage_rate', 0.0) or 0.0):.3f}, "
                f"fallback_rate={float(governance_runtime_first.get('fallback_rate', 0.0) or 0.0):.3f}, "
                f"samples={int(governance_runtime_first.get('sample_size', 0) or 0)}, "
                f"source={str(governance_runtime_first.get('evidence_source', '')).strip() or 'live_timings'}"
            )
    optimization = payload.get("optimization_snapshot", {})
    if isinstance(optimization, Mapping):
        overall = optimization.get("overall", {})
        packet_posture = optimization.get("packet_posture", {})
        quality_posture = optimization.get("quality_posture", {})
        evaluation_posture = optimization.get("evaluation_posture", {})
        intent_posture = optimization.get("intent_posture", {})
        learning_loop = optimization.get("learning_loop", {})
        if isinstance(overall, Mapping):
            print(
                "- optimization: "
                f"level={overall.get('level', 'minimal')}, "
                f"score={overall.get('score', 0)}, "
                f"samples={int(optimization.get('sample_size', 0) or 0)}"
            )
        if isinstance(packet_posture, Mapping):
            print(
                "- optimization_packet_posture: "
                f"avg_tokens={packet_posture.get('avg_tokens', 0)}, "
                f"avg_bytes={packet_posture.get('avg_bytes', 0)}, "
                f"within_budget_rate={packet_posture.get('within_budget_rate', 0)}"
            )
        if isinstance(quality_posture, Mapping):
            print(
                "- optimization_quality_posture: "
                f"avg_utility_score={quality_posture.get('avg_utility_score', 0)}, "
                f"route_ready_rate={quality_posture.get('route_ready_rate', 0)}, "
                f"native_spawn_ready_rate={quality_posture.get('native_spawn_ready_rate', 0)}"
            )
        if isinstance(evaluation_posture, Mapping):
            router_outcomes = evaluation_posture.get("router_outcomes", {})
            orchestration_feedback = evaluation_posture.get("orchestration_feedback", {})
            control_posture = evaluation_posture.get("control_posture", {})
            if isinstance(router_outcomes, Mapping) and isinstance(orchestration_feedback, Mapping) and isinstance(control_posture, Mapping):
                print(
                    "- optimization_evaluation_posture: "
                    f"router_acceptance_rate={router_outcomes.get('acceptance_rate', 0)}, "
                    f"router_failure_rate={router_outcomes.get('failure_rate', 0)}, "
                    f"parallel_failure_rate={orchestration_feedback.get('parallel_failure_rate', 0)}, "
                    f"control={str(control_posture.get('depth', '')).strip() or '-'}"
                    f"/{str(control_posture.get('delegation', '')).strip() or '-'}"
                    f"/{str(control_posture.get('parallelism', '')).strip() or '-'}"
                )
        if isinstance(intent_posture, Mapping):
            print(
                "- optimization_intent_posture: "
                f"top_family={intent_posture.get('top_family', '-') or '-'}, "
                f"explicit_rate={intent_posture.get('explicit_rate', 0)}, "
                f"high_confidence_rate={intent_posture.get('high_confidence_rate', 0)}"
            )
        if isinstance(learning_loop, Mapping):
            print(
                "- optimization_learning_loop: "
                f"state={str(learning_loop.get('state', '')).strip() or '-'}, "
                f"events={int(learning_loop.get('event_count', 0) or 0)}, "
                f"packet_trend={str(learning_loop.get('packet_trend', '')).strip() or '-'}, "
                f"router_trend={str(learning_loop.get('router_trend', '')).strip() or '-'}"
            )
    orchestration_adoption = payload.get("orchestration_adoption_snapshot", {})
    if isinstance(orchestration_adoption, Mapping):
        print(
            "- orchestration_adoption: "
            f"samples={int(orchestration_adoption.get('sample_size', 0) or 0)}, "
            f"packet_present_rate={float(orchestration_adoption.get('packet_present_rate', 0.0) or 0.0):.3f}, "
            f"auto_grounded_rate={float(orchestration_adoption.get('auto_grounded_rate', 0.0) or 0.0):.3f}, "
            f"requires_widening_rate={float(orchestration_adoption.get('requires_widening_rate', 0.0) or 0.0):.3f}, "
            f"grounded_delegate_rate={float(orchestration_adoption.get('grounded_delegate_rate', 0.0) or 0.0):.3f}, "
            f"workspace_daemon_reused_rate={float(orchestration_adoption.get('workspace_daemon_reused_rate', 0.0) or 0.0):.3f}, "
            f"session_namespaced_rate={float(orchestration_adoption.get('session_namespaced_rate', 0.0) or 0.0):.3f}, "
            f"source={str(orchestration_adoption.get('evidence_source', '')).strip() or 'live_decision_ledgers'}"
        )
        recommendations = optimization.get("recommendations", [])
        if isinstance(recommendations, list) and recommendations:
            print(f"- optimization_recommendation: {str(recommendations[0]).strip()}")
    evaluation = payload.get("evaluation_snapshot", {})
    if isinstance(evaluation, Mapping):
        program = evaluation.get("program", {})
        if isinstance(program, Mapping):
            print(
                "- evaluation: "
                f"status={evaluation.get('status', 'unseeded')}, "
                f"program_status={program.get('status', 'active') or 'active'}, "
                f"cases={int(evaluation.get('corpus_size', 0) or 0)}, "
                f"covered={int(evaluation.get('covered_case_count', 0) or 0)}, "
                f"satisfied={int(evaluation.get('satisfied_case_count', 0) or 0)}, "
                f"active_wave={program.get('active_wave_id', '-') or '-'}"
            )
        architecture = evaluation.get("architecture", {})
        if isinstance(architecture, Mapping):
            print(
                "- evaluation_architecture: "
                f"status={architecture.get('status', 'unseeded')}, "
                f"cases={int(architecture.get('corpus_size', 0) or 0)}, "
                f"covered={int(architecture.get('covered_case_count', 0) or 0)}, "
                f"satisfied={int(architecture.get('satisfied_case_count', 0) or 0)}, "
                f"avg_latency_ms={float(architecture.get('avg_latency_ms', 0.0) or 0.0):.1f}, "
                f"source={str(architecture.get('evidence_source', '')).strip() or 'live_timings'}"
            )
        recommendations = evaluation.get("recommendations", [])
        if isinstance(recommendations, list) and recommendations:
            print(f"- evaluation_recommendation: {str(recommendations[0]).strip()}")
        architecture_recommendations = architecture.get("recommendations", []) if isinstance(architecture, Mapping) else []
        if isinstance(architecture_recommendations, list) and architecture_recommendations:
            print(f"- evaluation_architecture_recommendation: {str(architecture_recommendations[0]).strip()}")
    benchmark_report = payload.get("benchmark_report", {})
    benchmark_progress = payload.get("benchmark_progress", {})
    if isinstance(benchmark_progress, Mapping) and str(benchmark_progress.get("status", "")).strip():
        print(
            "- benchmark_progress: "
            f"status={benchmark_progress.get('status', '')}, "
            f"completed={int(benchmark_progress.get('completed_scenarios', 0) or 0)}/"
            f"{int(benchmark_progress.get('scenario_count', 0) or 0)}, "
            f"current={benchmark_progress.get('current_scenario_id', '') or '-'}"
            f"/{benchmark_progress.get('current_mode', '') or '-'}"
        )
    if isinstance(benchmark_report, Mapping) and str(benchmark_report.get("status", "")).strip():
        print(
            "- benchmark_report: "
            f"status={benchmark_report.get('status', '')}, "
            f"scenarios={int(benchmark_report.get('scenario_count', 0) or 0)}, "
            f"comparison={benchmark_report.get('candidate_mode', '') or '-'} vs "
            f"{benchmark_report.get('baseline_mode', '') or '-'}"
        )
        print(
            "- benchmark_deltas: "
            f"latency_ms={float(benchmark_report.get('latency_delta_ms', 0.0) or 0.0):.3f}, "
            f"prompt_tokens={float(benchmark_report.get('prompt_token_delta', benchmark_report.get('token_delta', 0.0)) or 0.0):.3f}, "
            f"total_tokens={float(benchmark_report.get('total_payload_token_delta', 0.0) or 0.0):.3f}, "
            f"required_path_recall={float(benchmark_report.get('required_path_recall_delta', 0.0) or 0.0):.3f}, "
            f"validation_success={float(benchmark_report.get('validation_success_delta', 0.0) or 0.0):.3f}"
        )


def _daemon_socket_available(*, repo_root: Path) -> bool:
    pid = _read_pid(store.pid_path(repo_root=repo_root))
    if not (pid and _pid_alive(pid)):
        return False
    return _read_daemon_transport(repo_root=repo_root) is not None


def _normalize_loopback_host(value: Any) -> str:
    token = str(value or "").strip().lower()
    if not token:
        return "127.0.0.1"
    if token in {"127.0.0.1", "localhost", "::1"}:
        return token
    return ""


def _read_daemon_transport(*, repo_root: Path) -> dict[str, Any] | None:
    socket_path = store.socket_path(repo_root=repo_root)
    owner_pid = _daemon_owner_pid(repo_root=repo_root)
    if not owner_pid or not _pid_alive(owner_pid):
        return None
    try:
        if socket_path.is_socket():
            return {
                "transport": "unix",
                "path": str(socket_path),
            }
    except OSError:
        return None
    if not socket_path.is_file():
        return None
    try:
        payload = json.loads(socket_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, Mapping):
        return None
    transport = str(payload.get("transport", "")).strip().lower()
    if transport == "inproc":
        owner_key = str(payload.get("repo_root", "")).strip()
        try:
            owner_pid = int(payload.get("pid", 0) or 0)
        except (TypeError, ValueError):
            return None
        if owner_pid != os.getpid():
            return None
        if owner_key != _inproc_daemon_key(repo_root=repo_root):
            return None
        if owner_key not in _INPROC_DAEMON_REGISTRY:
            return None
        return {
            "transport": "inproc",
            "repo_root": owner_key,
            "pid": owner_pid,
        }
    if transport != "tcp":
        return None
    host = _normalize_loopback_host(payload.get("host", ""))
    if not host:
        return None
    try:
        port = int(payload.get("port", 0) or 0)
    except (TypeError, ValueError):
        return None
    try:
        transport_pid = int(payload.get("pid", 0) or 0)
    except (TypeError, ValueError):
        transport_pid = 0
    if port <= 0:
        return None
    if transport_pid > 0 and transport_pid != owner_pid:
        return None
    return {
        "transport": "tcp",
        "host": host,
        "port": port,
        "pid": owner_pid,
    }


def _daemon_request(
    *,
    repo_root: Path,
    command: str,
    payload: Mapping[str, Any] | None = None,
    required: bool,
    timeout_seconds: float = 5.0,
) -> dict[str, Any] | None:
    started_at = time.perf_counter()
    daemon_metadata = _read_daemon_metadata(repo_root=repo_root)
    transport = _read_daemon_transport(repo_root=repo_root)
    if transport is None:
        if required:
            raise RuntimeError("odylith context engine daemon unavailable")
        return None
    if str(transport.get("transport", "")).strip() == "inproc":
        try:
            daemon_payload = _dispatch_daemon_command(
                repo_root=repo_root,
                command=str(command).strip(),
                payload=dict(payload or {}),
            )
        except Exception as exc:
            if required:
                raise RuntimeError("odylith context engine daemon request failed") from exc
            return None
        store.record_runtime_timing(
            repo_root=repo_root,
            category="daemon",
            operation=str(command).strip() or "request",
            duration_ms=(time.perf_counter() - started_at) * 1000.0,
            metadata={"required": bool(required), "transport": "inproc"},
        )
        return dict(daemon_payload) if isinstance(daemon_payload, Mapping) else {"value": daemon_payload}
    if str(transport.get("transport", "")).strip() == "tcp":
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connect_target: Any = (
            str(transport.get("host", "")).strip() or "127.0.0.1",
            int(transport.get("port", 0) or 0),
        )
    else:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connect_target = str(transport.get("path", "")).strip() or str(store.socket_path(repo_root=repo_root))
    sock.settimeout(timeout_seconds)
    try:
        sock.connect(connect_target)
        request = {
            "command": str(command).strip(),
            "payload": dict(payload or {}),
        }
        auth_token = str(daemon_metadata.get("auth_token", "")).strip()
        if auth_token:
            request["auth_token"] = auth_token
        rendered = json.dumps(request, sort_keys=True).encode("utf-8") + b"\n"
        sock.sendall(rendered)
        sock.shutdown(socket.SHUT_WR)
        chunks: list[bytes] = []
        while True:
            data = sock.recv(65536)
            if not data:
                break
            chunks.append(data)
    except OSError as exc:
        if required:
            raise RuntimeError("odylith context engine daemon request failed") from exc
        return None
    finally:
        with contextlib.suppress(OSError):
            sock.close()
    if not chunks:
        if required:
            raise RuntimeError("odylith context engine daemon returned no response")
        return None
    try:
        response = json.loads(b"".join(chunks).decode("utf-8"))
    except json.JSONDecodeError as exc:
        if required:
            raise RuntimeError("odylith context engine daemon returned invalid JSON") from exc
        return None
    if not isinstance(response, Mapping):
        if required:
            raise RuntimeError("odylith context engine daemon returned an invalid payload")
        return None
    if not bool(response.get("ok", False)):
        message = str(response.get("error", "")).strip() or "odylith context engine daemon request failed"
        if required:
            raise RuntimeError(message)
        return None
    daemon_payload = response.get("payload", {})
    store.record_runtime_timing(
        repo_root=repo_root,
        category="daemon",
        operation=str(command).strip() or "request",
        duration_ms=(time.perf_counter() - started_at) * 1000.0,
        metadata={
            "required": bool(required),
            "transport": str(transport.get("transport", "")).strip() or "unknown",
            "authenticated": bool(str(daemon_metadata.get("auth_token", "")).strip()),
        },
    )
    return dict(daemon_payload) if isinstance(daemon_payload, Mapping) else {"value": daemon_payload}


def _client_mode_required(client_mode: str) -> bool:
    return str(client_mode or "auto").strip().lower() == "daemon"


def _odylith_env_override_force_local_truth(*, repo_root: Path) -> bool:
    snapshot = odylith_ablation.build_odylith_switch_snapshot(repo_root=repo_root)
    return bool(snapshot.get("env_override_active"))


def _should_try_daemon(*, client_mode: str, repo_root: Path | None = None) -> bool:
    if repo_root is not None and _odylith_env_override_force_local_truth(repo_root=repo_root):
        return False
    return str(client_mode or "auto").strip().lower() in {"auto", "daemon"}


_AUTOSPAWN_COMMANDS = frozenset({"query", "context", "impact", "architecture", "governance-slice", "session-brief", "bootstrap-session"})
_INPROC_DAEMON_REGISTRY: set[str] = set()


def _inproc_daemon_key(*, repo_root: Path) -> str:
    return str(Path(repo_root).resolve())


def _clear_stale_daemon_artifacts(*, repo_root: Path) -> None:
    pid = _read_pid(store.pid_path(repo_root=repo_root))
    if pid and _pid_alive(pid):
        return
    for path in (
        store.pid_path(repo_root=repo_root),
        store.socket_path(repo_root=repo_root),
        store.stop_path(repo_root=repo_root),
        _daemon_metadata_path(repo_root=repo_root),
    ):
        with contextlib.suppress(FileNotFoundError, OSError):
            path.unlink()


def _autospawn_idle_timeout_seconds() -> int:
    raw = str(os.environ.get(_AUTOSPAWN_IDLE_TIMEOUT_ENV, "")).strip()
    try:
        parsed = int(raw) if raw else _DEFAULT_AUTOSPAWN_IDLE_TIMEOUT_SECONDS
    except ValueError:
        parsed = _DEFAULT_AUTOSPAWN_IDLE_TIMEOUT_SECONDS
    return max(30, parsed)


def _background_autospawn_block_reason(*, repo_root: Path) -> str:
    if str(os.environ.get(_BACKGROUND_AUTOSPAWN_DISABLE_ENV, "")).strip() == "1":
        return "env_disabled"
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return "pytest"
    if os.environ.get("CI"):
        return "ci"
    if not (Path(repo_root).resolve() / ".git").exists():
        return "non_git_repo"
    if str(os.environ.get(_BACKGROUND_AUTOSPAWN_ALLOW_ENV, "")).strip() == "1":
        return ""
    # Detached background daemons are opt-in only. Auto mode may still reuse an
    # already-running daemon, but it must not silently leave a new daemon behind.
    return "not_opted_in"


def _spawn_daemon_background(*, repo_root: Path, scope: str = "full") -> bool:
    started_at = time.perf_counter()
    spawned = False
    ready = False
    startup_reaped = False
    waiting_for_existing = False
    existing_pid: int | None = None
    spawned_process: subprocess.Popen[Any] | None = None
    idle_timeout_seconds = _autospawn_idle_timeout_seconds()
    with odylith_context_cache.advisory_lock(repo_root=repo_root, key=f"{store.pid_path(repo_root=repo_root)}.autospawn"):
        if _daemon_socket_available(repo_root=repo_root):
            return False
        existing_pid = _daemon_owner_pid(repo_root=repo_root)
        if existing_pid and _pid_alive(existing_pid):
            waiting_for_existing = True
        else:
            _clear_stale_daemon_artifacts(repo_root=repo_root)
            cmd = [
                *module_invocation(
                    "context-engine",
                    "--repo-root",
                    str(repo_root),
                    python_path=_preferred_odylith_python(repo_root=repo_root),
                ),
                "serve",
                "--scope",
                str(scope or "full"),
                "--watcher-backend",
                "auto",
                "--spawn-reason",
                _DAEMON_SPAWN_REASON_AUTOSPAWN,
                "--idle-timeout-seconds",
                str(idle_timeout_seconds),
            ]
            try:
                spawned_process = subprocess.Popen(  # noqa: S603
                    cmd,
                    cwd=str(repo_root),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                spawned = True
            except OSError:
                spawned = False
    if spawned or waiting_for_existing:
        for _ in range(50):
            if _daemon_socket_available(repo_root=repo_root):
                ready = True
                break
            if waiting_for_existing and existing_pid and not _pid_alive(existing_pid):
                break
            time.sleep(0.1)
    if spawned and not ready and spawned_process is not None:
        startup_reaped = _terminate_background_process(spawned_process)
        _clear_stale_daemon_artifacts(repo_root=repo_root)
    store.record_runtime_timing(
        repo_root=repo_root,
        category="daemon",
        operation="autospawn",
        duration_ms=(time.perf_counter() - started_at) * 1000.0,
        metadata={
            "scope": str(scope or "full"),
            "spawned": bool(spawned),
            "ready": bool(ready),
            "startup_reaped": bool(startup_reaped),
            "waiting_for_existing": bool(waiting_for_existing),
            "idle_timeout_seconds": idle_timeout_seconds,
        },
    )
    return ready


def _maybe_autospawn_daemon(*, repo_root: Path, client_mode: str, command: str) -> bool:
    normalized_mode = str(client_mode or "auto").strip().lower()
    normalized_command = str(command or "").strip()
    if normalized_mode != "auto":
        return False
    if _odylith_env_override_force_local_truth(repo_root=repo_root):
        return False
    if normalized_command not in _AUTOSPAWN_COMMANDS:
        return False
    if _daemon_socket_available(repo_root=repo_root):
        return False
    if _background_autospawn_block_reason(repo_root=repo_root):
        return False
    return _spawn_daemon_background(repo_root=repo_root, scope=_REASONING_SCOPE)


def _record_daemon_client_activity(*, repo_root: Path, session_namespace: str = "") -> None:
    key = _inproc_daemon_key(repo_root=repo_root)
    now = time.monotonic()
    with _DAEMON_ACTIVITY_LOCK:
        _DAEMON_ACTIVITY[key] = now
        namespace_token = str(session_namespace or "").strip()
        if namespace_token:
            _DAEMON_SESSION_ACTIVITY.setdefault(key, {})[namespace_token] = now


def _last_daemon_client_activity(*, repo_root: Path) -> float | None:
    key = _inproc_daemon_key(repo_root=repo_root)
    with _DAEMON_ACTIVITY_LOCK:
        return _DAEMON_ACTIVITY.get(key)


def _clear_daemon_client_activity(*, repo_root: Path) -> None:
    key = _inproc_daemon_key(repo_root=repo_root)
    with _DAEMON_ACTIVITY_LOCK:
        _DAEMON_ACTIVITY.pop(key, None)
        _DAEMON_SESSION_ACTIVITY.pop(key, None)


def _autospawn_daemon_idle_expired(*, repo_root: Path, spawn_reason: str, idle_timeout_seconds: int) -> bool:
    if str(spawn_reason or "").strip().lower() != _DAEMON_SPAWN_REASON_AUTOSPAWN:
        return False
    timeout = max(0, int(idle_timeout_seconds))
    if timeout <= 0:
        return False
    last_activity = _last_daemon_client_activity(repo_root=repo_root)
    if last_activity is None:
        return False
    return (time.monotonic() - last_activity) >= timeout


def _return_local_result_with_optional_autospawn(
    *,
    repo_root: Path,
    client_mode: str,
    command: str,
    exit_code: int,
) -> int:
    if int(exit_code) == 0:
        _maybe_autospawn_daemon(
            repo_root=repo_root,
            client_mode=client_mode,
            command=command,
        )
    return int(exit_code)


def _run_warmup(*, repo_root: Path, force: bool, reason: str, scope: str) -> int:
    summary = store.warm_projections(repo_root=repo_root, force=force, reason=reason, scope=scope)
    print("odylith context engine warmup passed")
    print(f"- repo_root: {repo_root}")
    print(f"- updated_utc: {summary.get('updated_utc', '')}")
    print(f"- projection_fingerprint: {summary.get('projection_fingerprint', '')}")
    print(f"- projection_scope: {summary.get('projection_scope', '')}")
    print(f"- watcher_backend: {summary.get('watcher_backend', '')}")
    print(f"- updated_projections: {', '.join(summary.get('updated_projections', [])) or 'none'}")
    return 0


def _run_status(*, repo_root: Path) -> int:
    _print_runtime_status(_runtime_status_payload(repo_root=repo_root))
    return 0


def _run_memory_snapshot(*, repo_root: Path) -> int:
    with runtime_read_session.activate_runtime_read_session(repo_root=repo_root, requested_scope="full"):
        store._warm_runtime(repo_root=repo_root, runtime_mode="auto", reason="memory_snapshot", scope="full")  # noqa: SLF001
        optimization_snapshot = store.load_runtime_optimization_snapshot(repo_root=repo_root)
        evaluation_snapshot = store.load_runtime_evaluation_snapshot(repo_root=repo_root)
        payload = store.load_runtime_memory_snapshot(
            repo_root=repo_root,
            optimization_snapshot=optimization_snapshot,
            evaluation_snapshot=evaluation_snapshot,
        )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _run_odylith_switch(
    *,
    repo_root: Path,
    enable: bool,
    disable: bool,
    clear: bool,
    note: str,
) -> int:
    action = "status"
    if clear:
        odylith_ablation.clear_odylith_switch(repo_root=repo_root)
        action = "clear"
    elif enable:
        odylith_ablation.write_odylith_switch(repo_root=repo_root, enabled=True, note=note)
        action = "enable"
    elif disable:
        odylith_ablation.write_odylith_switch(repo_root=repo_root, enabled=False, note=note)
        action = "disable"
    payload = {
        "requested_action": action,
        "effective_switch": odylith_ablation.build_odylith_switch_snapshot(repo_root=repo_root),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _doctor_payload(*, repo_root: Path, bootstrap_watcher: bool) -> dict[str, Any]:
    bootstrap_result: dict[str, Any] = {
        "status": "not-requested",
        "supported": False,
        "active": False,
        "started": False,
        "detail": "",
    }
    if bootstrap_watcher:
        bootstrap_result = store.bootstrap_git_fsmonitor(repo_root=repo_root)
    status_payload = _runtime_status_payload(repo_root=repo_root)
    watcher_report = status_payload.get("watcher_report", {}) if isinstance(status_payload.get("watcher_report"), Mapping) else {}
    recommendation = "poll fallback remains the only available watcher mode in this environment."
    if bool(watcher_report.get("watchman_available")):
        recommendation = "watchman is available; use `serve --watcher-backend auto` or restart the daemon to switch onto watchman."
    elif bool(watcher_report.get("watchdog_available")):
        recommendation = "watchdog is available; use `serve --watcher-backend auto` or restart the daemon to switch onto watchdog."
    elif bool(watcher_report.get("git_fsmonitor_active")):
        recommendation = "git fsmonitor is active; `serve --watcher-backend auto` will use the git-fsmonitor-assisted fallback."
    elif bool(watcher_report.get("git_fsmonitor_supported")):
        recommendation = "git fsmonitor is supported but inactive; run `odylith context-engine --repo-root . doctor --bootstrap-watcher` to start the best local watcher-assisted fallback."
    payload = {
        "status": status_payload,
        "bootstrap": bootstrap_result,
        "recommendation": recommendation,
    }
    return payload


def _print_doctor_payload(payload: Mapping[str, Any]) -> None:
    print("odylith context engine doctor")
    status_payload = payload.get("status", {})
    if isinstance(status_payload, Mapping):
        print(f"- daemon_alive: {'yes' if bool(status_payload.get('daemon_alive')) else 'no'}")
        print(f"- watcher_backend: {status_payload.get('watcher_backend', '')}")
        print(f"- preferred_watcher_backend: {status_payload.get('preferred_watcher_backend', '')}")
        watcher_report = status_payload.get("watcher_report", {})
        if isinstance(watcher_report, Mapping):
            print(f"- watchman_available: {'yes' if bool(watcher_report.get('watchman_available')) else 'no'}")
            print(f"- watchdog_available: {'yes' if bool(watcher_report.get('watchdog_available')) else 'no'}")
            print(f"- git_fsmonitor_supported: {'yes' if bool(watcher_report.get('git_fsmonitor_supported')) else 'no'}")
            print(f"- git_fsmonitor_active: {'yes' if bool(watcher_report.get('git_fsmonitor_active')) else 'no'}")
            if str(watcher_report.get("git_fsmonitor_detail", "")).strip():
                print(f"- git_fsmonitor_detail: {watcher_report.get('git_fsmonitor_detail', '')}")
            if bool(watcher_report.get("bootstrap_recommended")):
                print("- watcher_bootstrap_recommended: yes")
        if bool(status_payload.get("daemon_restart_recommended")):
            print("- daemon_restart_recommended: yes")
    bootstrap = payload.get("bootstrap", {})
    if isinstance(bootstrap, Mapping):
        print(f"- bootstrap_status: {bootstrap.get('status', 'not-requested')}")
        if str(bootstrap.get("detail", "")).strip():
            print(f"- bootstrap_detail: {bootstrap.get('detail', '')}")
    print(f"- recommendation: {payload.get('recommendation', '')}")


def _run_doctor(*, repo_root: Path, bootstrap_watcher: bool) -> int:
    payload = _doctor_payload(repo_root=repo_root, bootstrap_watcher=bootstrap_watcher)
    _print_doctor_payload(payload)
    bootstrap = payload.get("bootstrap", {})
    if bootstrap_watcher and isinstance(bootstrap, Mapping) and str(bootstrap.get("status", "")).strip() == "failed":
        return 2
    return 0


def _run_benchmark(
    *,
    repo_root: Path,
    benchmark_profile: str,
    modes: Sequence[str],
    cache_profiles: Sequence[str],
    case_ids: Sequence[str],
    families: Sequence[str],
    shard_count: int,
    shard_index: int,
    limit: int,
    write_report: bool,
    json_output: bool,
) -> int:
    report = odylith_benchmark_runner.run_benchmarks(
        repo_root=repo_root,
        benchmark_profile=benchmark_profile,
        modes=modes,
        cache_profiles=cache_profiles,
        case_ids=case_ids,
        families=families,
        shard_count=shard_count,
        shard_index=shard_index,
        limit=max(0, int(limit)),
        write_report=write_report,
    )
    if json_output:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    print(str(report.get("summary_text", "")).strip() or "odylith benchmark report unavailable")
    if write_report:
        print(f"- latest_report_path: {odylith_benchmark_runner.latest_report_path(repo_root=repo_root)}")
        print(
            "- history_report_path: "
            f"{odylith_benchmark_runner.history_report_path(repo_root=repo_root, report_id=str(report.get('report_id', '')).strip())}"
        )
    return 0


def _run_stop(*, repo_root: Path) -> int:
    pid_file = store.pid_path(repo_root=repo_root)
    pid = _read_pid(pid_file)
    stop_file = store.stop_path(repo_root=repo_root)
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=stop_file,
        content="stop\n",
        lock_key=str(stop_file),
    )
    if pid and _pid_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        for _ in range(20):
            if not _pid_alive(pid):
                break
            time.sleep(0.1)
        if _pid_alive(pid):
            kill_signal = getattr(signal, "SIGKILL", signal.SIGTERM)
            with contextlib.suppress(OSError):
                os.kill(pid, kill_signal)
            for _ in range(20):
                if not _pid_alive(pid):
                    break
                time.sleep(0.1)
        _clear_stale_daemon_artifacts(repo_root=repo_root)
        if _pid_alive(pid):
            print(f"odylith context engine stop requested for pid {pid}, but the daemon is still alive", file=sys.stderr)
            return 1
        print(f"odylith context engine stop requested for pid {pid}")
        return 0
    _clear_stale_daemon_artifacts(repo_root=repo_root)
    print("odylith context engine stop requested (no live pid found)")
    return 0


def _run_query(*, repo_root: Path, text: str, limit: int, kinds: Sequence[str]) -> int:
    with runtime_read_session.activate_runtime_read_session(repo_root=repo_root, requested_scope="reasoning"):
        payload = store.search_entities_payload(
            repo_root=repo_root,
            query=text,
            limit=limit,
            kinds=kinds,
        )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _run_odylith_remote_sync(*, repo_root: Path, dry_run: bool) -> int:
    remote_config = odylith_remote_retrieval.remote_config(repo_root=repo_root)
    if str(remote_config.get("status", "")).strip() in {"disabled", "misconfigured"}:
        payload = odylith_remote_retrieval.sync_remote(
            repo_root=repo_root,
            documents=[],
            dry_run=bool(dry_run),
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    expected_projection_fingerprint = store.projection_input_fingerprint(repo_root=repo_root, scope="full")
    if not odylith_memory_backend.local_backend_ready_for_projection(
        repo_root=repo_root,
        projection_fingerprint=expected_projection_fingerprint,
        projection_scope="full",
    ):
        store.warm_projections(repo_root=repo_root, force=False, reason="odylith_remote_sync", scope="full")
    documents = odylith_memory_backend.all_documents(repo_root=repo_root, include_embedding=True)
    if not documents:
        connection = store._connect(repo_root)  # noqa: SLF001
        try:
            documents = odylith_memory_backend.projection_documents(connection=connection)
        finally:
            connection.close()
    payload = odylith_remote_retrieval.sync_remote(
        repo_root=repo_root,
        documents=documents,
        dry_run=bool(dry_run),
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _run_context(
    *,
    repo_root: Path,
    ref: str,
    kind: str,
    event_limit: int,
    relation_limit: int,
) -> int:
    with runtime_read_session.activate_runtime_read_session(repo_root=repo_root, requested_scope="reasoning"):
        payload = dossier_compaction_runtime.compact_context_dossier_for_delivery(
            store.load_context_dossier(
                repo_root=repo_root,
                ref=ref,
                kind=str(kind or "").strip() or None,
                event_limit=max(1, int(event_limit)),
                relation_limit=max(1, int(relation_limit)),
            ),
            event_limit=max(1, int(event_limit)),
            relation_limit_per_kind=max(1, int(relation_limit)),
            delivery_limit=1,
        )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _surface_payload_json_ready(value: Any) -> Any:
    if hasattr(value, "as_dict") and callable(value.as_dict):
        return _surface_payload_json_ready(value.as_dict())
    if dataclasses.is_dataclass(value):
        return _surface_payload_json_ready(dataclasses.asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _surface_payload_json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_surface_payload_json_ready(item) for item in value]
    return value


def _surface_read_payload(
    *,
    repo_root: Path,
    entity: str,
    workstream: str,
    component: str,
    paths: Sequence[str],
    session_id: str,
    claim_paths: Sequence[str],
    working_tree_scope: str,
    case: str,
    view: str,
) -> Any:
    token = str(entity).strip().lower()
    if token == "backlog-list":
        return store.load_backlog_list(repo_root=repo_root, runtime_mode="auto")
    if token == "backlog-detail":
        workstream_token = str(workstream).strip()
        if not workstream_token:
            raise ValueError("--workstream is required for backlog-detail")
        return store.load_backlog_detail(
            repo_root=repo_root,
            workstream_id=workstream_token,
            runtime_mode="auto",
        )
    if token == "backlog-document":
        workstream_token = str(workstream).strip()
        if not workstream_token:
            raise ValueError("--workstream is required for backlog-document")
        return store.load_backlog_document(
            repo_root=repo_root,
            workstream_id=workstream_token,
            view=str(view).strip().lower() or "spec",
            runtime_mode="auto",
        )
    if token == "governance-detail":
        if not str(workstream).strip() and not str(component).strip() and not any(str(path).strip() for path in paths):
            raise ValueError("--workstream, --component, or --path is required for governance-detail")
        return store.build_governance_slice(
            repo_root=repo_root,
            changed_paths=[str(path).strip() for path in paths if str(path).strip()],
            workstream=str(workstream).strip(),
            component=str(component).strip(),
            session_id=str(session_id).strip(),
            claimed_paths=[str(path).strip() for path in claim_paths if str(path).strip()],
            working_tree_scope=str(working_tree_scope).strip() or "repo",
            runtime_mode="auto",
        )
    if token == "registry-list":
        return store.load_registry_list(repo_root=repo_root, runtime_mode="auto")
    if token == "registry-detail":
        component_token = str(component).strip()
        if not component_token:
            raise ValueError("--component is required for registry-detail")
        return store.load_registry_detail(
            repo_root=repo_root,
            component_id=component_token,
            runtime_mode="auto",
        )
    raise ValueError(f"unsupported surface-read entity: {entity}")


def _run_surface_read(
    *,
    repo_root: Path,
    entity: str,
    workstream: str,
    component: str,
    paths: Sequence[str],
    session_id: str,
    claim_paths: Sequence[str],
    working_tree_scope: str,
    case: str,
    view: str,
) -> int:
    requested_scope = "reasoning" if str(entity).strip().lower() == "governance-detail" else "default"
    with runtime_read_session.activate_runtime_read_session(repo_root=repo_root, requested_scope=requested_scope):
        payload = _surface_read_payload(
            repo_root=repo_root,
            entity=entity,
            workstream=workstream,
            component=component,
            paths=paths,
            session_id=session_id,
            claim_paths=claim_paths,
            working_tree_scope=working_tree_scope,
            case=case,
            view=view,
        )
    print(json.dumps(_surface_payload_json_ready(payload), indent=2, ensure_ascii=False))
    return 0


def _run_impact(
    *,
    repo_root: Path,
    paths: Sequence[str],
    use_working_tree: bool,
    working_tree_scope: str,
    session_id: str,
    claim_paths: Sequence[str],
    test_limit: int,
) -> int:
    with runtime_read_session.activate_runtime_read_session(repo_root=repo_root, requested_scope="reasoning"):
        payload = store.build_impact_report(
            repo_root=repo_root,
            changed_paths=paths,
            use_working_tree=use_working_tree,
            working_tree_scope=working_tree_scope,
            session_id=session_id,
            claimed_paths=claim_paths,
            test_limit=max(1, int(test_limit)),
        )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _run_architecture(
    *,
    repo_root: Path,
    paths: Sequence[str],
    use_working_tree: bool,
    working_tree_scope: str,
    session_id: str,
    claim_paths: Sequence[str],
) -> int:
    with runtime_read_session.activate_runtime_read_session(repo_root=repo_root, requested_scope="reasoning"):
        payload = store.build_architecture_audit(
            repo_root=repo_root,
            changed_paths=paths,
            use_working_tree=use_working_tree,
            working_tree_scope=working_tree_scope,
            session_id=session_id,
            claimed_paths=claim_paths,
        )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _run_governance_slice(
    *,
    repo_root: Path,
    paths: Sequence[str],
    workstream: str,
    component: str,
    use_working_tree: bool,
    working_tree_scope: str,
    session_id: str,
    claim_paths: Sequence[str],
) -> int:
    with runtime_read_session.activate_runtime_read_session(repo_root=repo_root, requested_scope="reasoning"):
        payload = store.build_governance_slice(
            repo_root=repo_root,
            changed_paths=paths,
            workstream=workstream,
            component=component,
            use_working_tree=use_working_tree,
            working_tree_scope=working_tree_scope,
            session_id=session_id,
            claimed_paths=claim_paths,
        )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _run_session_brief(
    *,
    repo_root: Path,
    paths: Sequence[str],
    use_working_tree: bool,
    working_tree_scope: str,
    session_id: str,
    workstream: str,
    intent: str,
    surfaces: Sequence[str],
    visible_text: Sequence[str],
    active_tab: str,
    user_turn_id: str,
    supersedes_turn_id: str,
    claim_mode: str,
    claim_paths: Sequence[str],
    lease_seconds: int,
) -> int:
    with runtime_read_session.activate_runtime_read_session(repo_root=repo_root, requested_scope="reasoning"):
        payload = packet_session_runtime.build_session_brief(
            repo_root=repo_root,
            changed_paths=paths,
            use_working_tree=use_working_tree,
            working_tree_scope=working_tree_scope,
            session_id=session_id,
            workstream=workstream,
            intent=intent,
            generated_surfaces=surfaces,
            visible_text=visible_text,
            active_tab=active_tab,
            user_turn_id=user_turn_id,
            supersedes_turn_id=supersedes_turn_id,
            claim_mode=claim_mode,
            claimed_paths=claim_paths,
            lease_seconds=max(60, int(lease_seconds)),
        )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _run_bootstrap_session(
    *,
    repo_root: Path,
    paths: Sequence[str],
    use_working_tree: bool,
    working_tree_scope: str,
    session_id: str,
    workstream: str,
    intent: str,
    surfaces: Sequence[str],
    visible_text: Sequence[str],
    active_tab: str,
    user_turn_id: str,
    supersedes_turn_id: str,
    claim_mode: str,
    claim_paths: Sequence[str],
    lease_seconds: int,
    doc_limit: int,
    command_limit: int,
    test_limit: int,
) -> int:
    with runtime_read_session.activate_runtime_read_session(repo_root=repo_root, requested_scope="reasoning"):
        payload = packet_session_runtime.build_session_bootstrap(
            repo_root=repo_root,
            changed_paths=paths,
            use_working_tree=use_working_tree,
            working_tree_scope=working_tree_scope,
            session_id=session_id,
            workstream=workstream,
            intent=intent,
            generated_surfaces=surfaces,
            visible_text=visible_text,
            active_tab=active_tab,
            user_turn_id=user_turn_id,
            supersedes_turn_id=supersedes_turn_id,
            claim_mode=claim_mode,
            claimed_paths=claim_paths,
            lease_seconds=max(60, int(lease_seconds)),
            doc_limit=max(1, int(doc_limit)),
            command_limit=max(1, int(command_limit)),
            test_limit=max(1, int(test_limit)),
        )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _dispatch_daemon_command(*, repo_root: Path, command: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    request_scope = store.runtime_request_namespace_from_payload(
        repo_root=repo_root,
        command=command,
        payload=payload,
    )
    _record_daemon_client_activity(
        repo_root=repo_root,
        session_namespace=str(request_scope.get("session_namespace", "")).strip(),
    )
    store.record_runtime_daemon_usage(
        repo_root=repo_root,
        command=command,
        payload=payload,
    )
    if command == "warmup":
        summary = store.warm_projections(
            repo_root=repo_root,
            force=bool(payload.get("force")),
            reason=str(payload.get("reason", "daemon")).strip() or "daemon",
            scope=str(payload.get("scope", "full")).strip() or "full",
        )
        odylith_context_engine_daemon_wait_runtime.record_projection_fingerprint(
            repo_root=repo_root,
            projection_fingerprint=str(summary.get("projection_fingerprint", "")).strip(),
        )
        return summary
    if command == "status":
        return _runtime_status_payload(repo_root=repo_root)
    if command == "wait-projection-change":
        current_status = _runtime_status_payload(repo_root=repo_root)
        return odylith_context_engine_daemon_wait_runtime.wait_for_projection_change(
            repo_root=repo_root,
            since_fingerprint=str(payload.get("since_fingerprint", "")).strip(),
            current_fingerprint=str(current_status.get("projection_fingerprint", "")).strip(),
            timeout_seconds=float(payload.get("timeout_seconds", 60.0) or 60.0),
        )
    if command == "compass-runtime-get":
        cached = odylith_context_engine_compass_runtime_cache.load_runtime_payload(
            repo_root=repo_root,
            input_fingerprint=str(payload.get("input_fingerprint", "")).strip(),
            refresh_profile=str(payload.get("refresh_profile", "")).strip(),
        )
        return {
            "hit": bool(isinstance(cached, Mapping) and cached),
            "payload": dict(cached) if isinstance(cached, Mapping) else {},
        }
    if command == "compass-runtime-put":
        return odylith_context_engine_compass_runtime_cache.record_runtime_payload(
            repo_root=repo_root,
            input_fingerprint=str(payload.get("input_fingerprint", "")).strip(),
            refresh_profile=str(payload.get("refresh_profile", "")).strip(),
            payload=dict(payload.get("runtime_payload", {})) if isinstance(payload.get("runtime_payload"), Mapping) else {},
        )
    if command == "memory-snapshot":
        optimization_snapshot = store.load_runtime_optimization_snapshot(repo_root=repo_root)
        evaluation_snapshot = store.load_runtime_evaluation_snapshot(repo_root=repo_root)
        return store.load_runtime_memory_snapshot(
            repo_root=repo_root,
            optimization_snapshot=optimization_snapshot,
            evaluation_snapshot=evaluation_snapshot,
        )
    if command == "query":
        return store.search_entities_payload(
            repo_root=repo_root,
            query=str(payload.get("text", "")).strip(),
            limit=max(1, int(payload.get("limit", 12) or 12)),
            kinds=[str(kind).strip() for kind in payload.get("kinds", []) if str(kind).strip()]
            if isinstance(payload.get("kinds"), list)
            else [],
        )
    if command == "surface-read":
        return _surface_payload_json_ready(
            _surface_read_payload(
                repo_root=repo_root,
                entity=str(payload.get("entity", "")).strip(),
                workstream=str(payload.get("workstream", "")).strip(),
                component=str(payload.get("component", "")).strip(),
                paths=[str(path).strip() for path in payload.get("paths", []) if str(path).strip()]
                if isinstance(payload.get("paths"), list)
                else [],
                session_id=str(payload.get("session_id", "")).strip(),
                claim_paths=[str(path).strip() for path in payload.get("claim_paths", []) if str(path).strip()]
                if isinstance(payload.get("claim_paths"), list)
                else [],
                working_tree_scope=str(payload.get("working_tree_scope", "repo")).strip() or "repo",
                case=str(payload.get("case", "")).strip(),
                view=str(payload.get("view", "spec")).strip() or "spec",
            )
        )
    if command == "context":
        event_limit = max(1, int(payload.get("event_limit", 2) or 2))
        relation_limit = max(1, int(payload.get("relation_limit", 2) or 2))
        return dossier_compaction_runtime.compact_context_dossier_for_delivery(
            store.load_context_dossier(
                repo_root=repo_root,
                ref=str(payload.get("ref", "")).strip(),
                kind=str(payload.get("kind", "")).strip() or None,
                event_limit=event_limit,
                relation_limit=relation_limit,
            ),
            event_limit=event_limit,
            relation_limit_per_kind=relation_limit,
            delivery_limit=1,
        )
    if command == "impact":
        return store.build_impact_report(
            repo_root=repo_root,
            changed_paths=[str(path).strip() for path in payload.get("paths", []) if str(path).strip()]
            if isinstance(payload.get("paths"), list)
            else [],
            use_working_tree=bool(payload.get("use_working_tree")),
            working_tree_scope=str(payload.get("working_tree_scope", "repo")).strip() or "repo",
            session_id=str(payload.get("session_id", "")).strip(),
            claimed_paths=[str(token).strip() for token in payload.get("claim_paths", []) if str(token).strip()]
            if isinstance(payload.get("claim_paths"), list)
            else [],
            test_limit=max(1, int(payload.get("test_limit", 12) or 12)),
            intent=str(payload.get("intent", "")).strip(),
            delivery_profile=str(payload.get("delivery_profile", "full")).strip() or "full",
            family_hint=str(payload.get("family_hint", "")).strip(),
            workstream_hint=str(payload.get("workstream_hint", "")).strip(),
            validation_command_hints=[
                str(token).strip()
                for token in payload.get("validation_command_hints", [])
                if str(token).strip()
            ]
            if isinstance(payload.get("validation_command_hints"), list)
            else [],
            retain_hot_path_internal_context=bool(payload.get("retain_hot_path_internal_context")),
        )
    if command == "architecture":
        return store.build_architecture_audit(
            repo_root=repo_root,
            changed_paths=[str(path).strip() for path in payload.get("paths", []) if str(path).strip()]
            if isinstance(payload.get("paths"), list)
            else [],
            use_working_tree=bool(payload.get("use_working_tree")),
            working_tree_scope=str(payload.get("working_tree_scope", "repo")).strip() or "repo",
            session_id=str(payload.get("session_id", "")).strip(),
            claimed_paths=[str(token).strip() for token in payload.get("claim_paths", []) if str(token).strip()]
            if isinstance(payload.get("claim_paths"), list)
            else [],
            runtime_mode=str(payload.get("runtime_mode", "auto")).strip() or "auto",
            detail_level=str(payload.get("detail_level", "compact")).strip() or "compact",
        )
    if command == "governance-slice":
        return store.build_governance_slice(
            repo_root=repo_root,
            changed_paths=[str(path).strip() for path in payload.get("paths", []) if str(path).strip()]
            if isinstance(payload.get("paths"), list)
            else [],
            workstream=str(payload.get("workstream", "")).strip(),
            component=str(payload.get("component", "")).strip(),
            use_working_tree=bool(payload.get("use_working_tree")),
            working_tree_scope=str(payload.get("working_tree_scope", "repo")).strip() or "repo",
            session_id=str(payload.get("session_id", "")).strip(),
            claimed_paths=[str(token).strip() for token in payload.get("claim_paths", []) if str(token).strip()]
            if isinstance(payload.get("claim_paths"), list)
            else [],
            runtime_mode=str(payload.get("runtime_mode", "auto")).strip() or "auto",
            delivery_profile=str(payload.get("delivery_profile", "full")).strip() or "full",
            family_hint=str(payload.get("family_hint", "")).strip(),
            validation_command_hints=[
                str(token).strip()
                for token in payload.get("validation_command_hints", [])
                if str(token).strip()
            ]
            if isinstance(payload.get("validation_command_hints"), list)
            else [],
        )
    if command == "session-brief":
        return packet_session_runtime.build_session_brief(
            repo_root=repo_root,
            changed_paths=[str(path).strip() for path in payload.get("paths", []) if str(path).strip()]
            if isinstance(payload.get("paths"), list)
            else [],
            use_working_tree=bool(payload.get("use_working_tree")),
            working_tree_scope=str(payload.get("working_tree_scope", "session")).strip() or "session",
            session_id=str(payload.get("session_id", "")).strip(),
            workstream=str(payload.get("workstream", "")).strip(),
            intent=str(payload.get("intent", "")).strip(),
            generated_surfaces=[str(token).strip() for token in payload.get("surfaces", []) if str(token).strip()]
            if isinstance(payload.get("surfaces"), list)
            else [],
            visible_text=[str(token).strip() for token in payload.get("visible_text", []) if str(token).strip()]
            if isinstance(payload.get("visible_text"), list)
            else [],
            active_tab=str(payload.get("active_tab", "")).strip(),
            user_turn_id=str(payload.get("user_turn_id", "")).strip(),
            supersedes_turn_id=str(payload.get("supersedes_turn_id", "")).strip(),
            claim_mode=str(payload.get("claim_mode", "shared")).strip() or "shared",
            claimed_paths=[str(token).strip() for token in payload.get("claim_paths", []) if str(token).strip()]
            if isinstance(payload.get("claim_paths"), list)
            else [],
            lease_seconds=max(60, int(payload.get("lease_seconds", 15 * 60) or 15 * 60)),
            runtime_mode=str(payload.get("runtime_mode", "auto")).strip() or "auto",
            delivery_profile=str(payload.get("delivery_profile", "full")).strip() or "full",
            family_hint=str(payload.get("family_hint", "")).strip(),
            validation_command_hints=[
                str(token).strip()
                for token in payload.get("validation_command_hints", [])
                if str(token).strip()
            ]
            if isinstance(payload.get("validation_command_hints"), list)
            else [],
        )
    if command == "bootstrap-session":
        return packet_session_runtime.build_session_bootstrap(
            repo_root=repo_root,
            changed_paths=[str(path).strip() for path in payload.get("paths", []) if str(path).strip()]
            if isinstance(payload.get("paths"), list)
            else [],
            use_working_tree=bool(payload.get("use_working_tree")),
            working_tree_scope=str(payload.get("working_tree_scope", "session")).strip() or "session",
            session_id=str(payload.get("session_id", "")).strip(),
            workstream=str(payload.get("workstream", "")).strip(),
            intent=str(payload.get("intent", "")).strip(),
            generated_surfaces=[str(token).strip() for token in payload.get("surfaces", []) if str(token).strip()]
            if isinstance(payload.get("surfaces"), list)
            else [],
            visible_text=[str(token).strip() for token in payload.get("visible_text", []) if str(token).strip()]
            if isinstance(payload.get("visible_text"), list)
            else [],
            active_tab=str(payload.get("active_tab", "")).strip(),
            user_turn_id=str(payload.get("user_turn_id", "")).strip(),
            supersedes_turn_id=str(payload.get("supersedes_turn_id", "")).strip(),
            claim_mode=str(payload.get("claim_mode", "shared")).strip() or "shared",
            claimed_paths=[str(token).strip() for token in payload.get("claim_paths", []) if str(token).strip()]
            if isinstance(payload.get("claim_paths"), list)
            else [],
            lease_seconds=max(60, int(payload.get("lease_seconds", 15 * 60) or 15 * 60)),
            doc_limit=max(1, int(payload.get("doc_limit", 8) or 8)),
            command_limit=max(1, int(payload.get("command_limit", 10) or 10)),
            test_limit=max(1, int(payload.get("test_limit", 8) or 8)),
            runtime_mode=str(payload.get("runtime_mode", "auto")).strip() or "auto",
            delivery_profile=str(payload.get("delivery_profile", "full")).strip() or "full",
            family_hint=str(payload.get("family_hint", "")).strip(),
            validation_command_hints=[
                str(token).strip()
                for token in payload.get("validation_command_hints", [])
                if str(token).strip()
            ]
            if isinstance(payload.get("validation_command_hints"), list)
            else [],
        )
    if command == "benchmark":
        return odylith_benchmark_runner.run_benchmarks(
            repo_root=repo_root,
            benchmark_profile=str(payload.get("benchmark_profile", odylith_benchmark_runner.DEFAULT_BENCHMARK_PROFILE)).strip()
            or odylith_benchmark_runner.DEFAULT_BENCHMARK_PROFILE,
            modes=[str(token).strip() for token in payload.get("modes", []) if str(token).strip()]
            if isinstance(payload.get("modes"), list)
            else [],
            cache_profiles=[str(token).strip() for token in payload.get("cache_profiles", []) if str(token).strip()]
            if isinstance(payload.get("cache_profiles"), list)
            else [],
            case_ids=[str(token).strip() for token in payload.get("case_ids", []) if str(token).strip()]
            if isinstance(payload.get("case_ids"), list)
            else [],
            families=[str(token).strip() for token in payload.get("families", []) if str(token).strip()]
            if isinstance(payload.get("families"), list)
            else [],
            shard_count=max(1, int(payload.get("shard_count", 1) or 1)),
            shard_index=max(1, int(payload.get("shard_index", 1) or 1)),
            limit=max(0, int(payload.get("limit", 0) or 0)),
            write_report=bool(payload.get("write_report", True)),
        )
    raise ValueError(f"unsupported odylith context engine daemon command: {command}")


class _RuntimeUnixRequestServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, *, repo_root: Path, socket_path: Path, auth_token: str) -> None:
        self.repo_root = repo_root
        self.socket_path = socket_path
        self.auth_token = str(auth_token or "").strip()
        super().__init__(str(socket_path), _RuntimeRequestHandler)


class _RuntimeTcpRequestServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, *, repo_root: Path, host: str, port: int, auth_token: str) -> None:
        self.repo_root = repo_root
        self.auth_token = str(auth_token or "").strip()
        super().__init__((host, int(port)), _RuntimeRequestHandler)


class _RuntimeRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        try:
            raw = self.rfile.readline(_DAEMON_REQUEST_MAX_BYTES + 1)
            if len(raw) > _DAEMON_REQUEST_MAX_BYTES:
                raise ValueError("request payload too large")
            request = json.loads(raw.decode("utf-8")) if raw else {}
            if not isinstance(request, Mapping):
                raise ValueError("request payload must be a JSON object")
            command = str(request.get("command", "")).strip()
            payload = request.get("payload", {})
            if not isinstance(payload, Mapping):
                raise ValueError("request payload field must be a JSON object")
            expected_token = str(getattr(self.server, "auth_token", "")).strip()
            provided_token = str(request.get("auth_token", "")).strip()
            if expected_token and provided_token != expected_token:
                raise ValueError("invalid auth token")
            response = {
                "ok": True,
                "payload": _dispatch_daemon_command(
                    repo_root=self.server.repo_root,  # type: ignore[attr-defined]
                    command=command,
                    payload=payload,
                ),
            }
        except Exception as exc:  # pragma: no cover - exercised through client-facing tests
            response = {
                "ok": False,
                "error": str(exc),
            }
        with contextlib.suppress(BrokenPipeError, ConnectionResetError, OSError):
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))


class _RuntimeDaemonServer:
    def __init__(self, *, repo_root: Path, auth_token: str) -> None:
        self._repo_root = repo_root
        self._socket_path = store.socket_path(repo_root=repo_root)
        self._auth_token = str(auth_token or "").strip()
        self._server: socketserver.BaseServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        _record_daemon_client_activity(repo_root=self._repo_root)
        self._socket_path.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(FileNotFoundError):
            self._socket_path.unlink()
        try:
            self._server = _RuntimeUnixRequestServer(
                repo_root=self._repo_root,
                socket_path=self._socket_path,
                auth_token=self._auth_token,
            )
            _harden_private_runtime_artifact(self._socket_path)
        except OSError:
            try:
                tcp_server = _RuntimeTcpRequestServer(
                    repo_root=self._repo_root,
                    host="127.0.0.1",
                    port=0,
                    auth_token=self._auth_token,
                )
                host, port = tcp_server.server_address
                odylith_context_cache.write_json_if_changed(
                    repo_root=self._repo_root,
                    path=self._socket_path,
                    payload={
                        "transport": "tcp",
                        "host": str(host).strip() or "127.0.0.1",
                        "port": int(port or 0),
                        "pid": os.getpid(),
                    },
                    lock_key=str(self._socket_path),
                )
                _harden_private_runtime_artifact(self._socket_path)
                self._server = tcp_server
            except OSError:
                _INPROC_DAEMON_REGISTRY.add(_inproc_daemon_key(repo_root=self._repo_root))
                odylith_context_cache.write_json_if_changed(
                    repo_root=self._repo_root,
                    path=self._socket_path,
                    payload={
                        "transport": "inproc",
                        "repo_root": _inproc_daemon_key(repo_root=self._repo_root),
                        "pid": os.getpid(),
                    },
                    lock_key=str(self._socket_path),
                )
                _harden_private_runtime_artifact(self._socket_path)
                self._server = None
        if self._server is not None:
            self._thread = threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.25}, daemon=True)
            self._thread.start()

    def close(self) -> None:
        if self._server is not None:
            with contextlib.suppress(Exception):
                self._server.shutdown()
            with contextlib.suppress(Exception):
                self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        _INPROC_DAEMON_REGISTRY.discard(_inproc_daemon_key(repo_root=self._repo_root))
        _clear_daemon_client_activity(repo_root=self._repo_root)
        with contextlib.suppress(FileNotFoundError):
            self._socket_path.unlink()


def _normalize_repo_relative(repo_root: Path, candidate: str) -> str:
    raw = str(candidate or "").strip().replace("\\", "/")
    if not raw:
        return ""
    path = Path(raw)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(repo_root).as_posix()
        except ValueError:
            return path.resolve().as_posix()
    while raw.startswith("./"):
        raw = raw[2:]
    return Path(raw).as_posix().strip("/")


def _should_refresh_for_change(*, repo_root: Path, changed_path: str, watch_targets: Sequence[str]) -> bool:
    normalized = _normalize_repo_relative(repo_root, changed_path)
    if not normalized:
        return False
    for token in watch_targets:
        watch = _normalize_repo_relative(repo_root, token)
        if not watch:
            continue
        if normalized == watch or normalized.startswith(f"{watch}/") or watch.startswith(f"{normalized}/"):
            return True
    return False


def _watch_roots(repo_root: Path, watch_targets: Sequence[str]) -> tuple[Path, ...]:
    roots: dict[str, Path] = {}
    for token in watch_targets:
        normalized = _normalize_repo_relative(repo_root, token)
        if not normalized:
            continue
        top = normalized.split("/", 1)[0]
        candidate = (repo_root / top).resolve()
        if candidate.exists():
            roots[str(candidate)] = candidate
    if not roots:
        roots[str(repo_root)] = repo_root
    return tuple(roots[key] for key in sorted(roots))


class _PollingRuntimeWatcher:
    backend = "poll"

    def wait_for_change(self, *, stop_file: Path, poll_seconds: int) -> bool:
        deadline = time.monotonic() + max(1, int(poll_seconds))
        while time.monotonic() < deadline:
            if stop_file.exists():
                return False
            time.sleep(0.25)
        return not stop_file.exists()

    def close(self) -> None:
        return None


class _WatchdogRuntimeWatcher:
    backend = "watchdog"

    def __init__(self, *, repo_root: Path, watch_targets: Sequence[str]) -> None:
        from watchdog.events import FileSystemEventHandler  # type: ignore
        from watchdog.observers import Observer  # type: ignore

        self._repo_root = repo_root
        self._watch_targets = tuple(watch_targets)
        self._event = threading.Event()
        self._observer = Observer()

        watcher = self

        class _Handler(FileSystemEventHandler):
            def on_any_event(self, event: Any) -> None:
                for raw_path in (getattr(event, "src_path", ""), getattr(event, "dest_path", "")):
                    if _should_refresh_for_change(
                        repo_root=watcher._repo_root,
                        changed_path=str(raw_path or ""),
                        watch_targets=watcher._watch_targets,
                    ):
                        watcher._event.set()
                        return

        handler = _Handler()
        for root in _watch_roots(repo_root, watch_targets):
            self._observer.schedule(handler, str(root), recursive=True)
        self._observer.start()

    def wait_for_change(self, *, stop_file: Path, poll_seconds: int) -> bool:
        _ = poll_seconds
        while not stop_file.exists():
            if self._event.wait(timeout=0.5):
                self._event.clear()
                return True
        return False

    def close(self) -> None:
        self._observer.stop()
        self._observer.join(timeout=2)


class _WatchmanRuntimeWatcher:
    backend = "watchman"

    def __init__(self, *, repo_root: Path, watch_targets: Sequence[str]) -> None:
        self._repo_root = repo_root
        self._watch_targets = tuple(watch_targets)
        self._subscription = f"odylith-context-engine-{os.getpid()}"
        self._process = subprocess.Popen(
            ["watchman", "--server-encoding=json", "-j"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        if self._process.stdin is None or self._process.stdout is None:
            raise RuntimeError("watchman stdio unavailable")
        watch_project = self._request(["watch-project", str(repo_root)])
        self._watch_root = str(watch_project.get("watch", "")).strip() or str(repo_root)
        relative_root = str(watch_project.get("relative_path", "")).strip()
        subscribe_payload: dict[str, Any] = {"fields": ["name", "exists", "type"]}
        if relative_root:
            subscribe_payload["relative_root"] = relative_root
        self._request(["subscribe", self._watch_root, self._subscription, subscribe_payload])

    def _request(self, payload: list[Any]) -> Mapping[str, Any]:
        assert self._process.stdin is not None
        assert self._process.stdout is not None
        self._process.stdin.write(json.dumps(payload) + "\n")
        self._process.stdin.flush()
        while True:
            line = self._process.stdout.readline()
            if not line:
                raise RuntimeError("watchman closed the subscription stream")
            try:
                decoded = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, Mapping) and decoded.get("subscription"):
                continue
            if isinstance(decoded, Mapping):
                return decoded

    def wait_for_change(self, *, stop_file: Path, poll_seconds: int) -> bool:
        _ = poll_seconds
        assert self._process.stdout is not None
        while not stop_file.exists():
            ready, _, _ = select.select([self._process.stdout], [], [], 0.5)
            if not ready:
                continue
            line = self._process.stdout.readline()
            if not line:
                raise RuntimeError("watchman subscription ended unexpectedly")
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, Mapping) or str(payload.get("subscription", "")).strip() != self._subscription:
                continue
            files = payload.get("files", [])
            if not isinstance(files, list):
                continue
            for item in files:
                if isinstance(item, Mapping):
                    candidate = str(item.get("name", "")).strip()
                else:
                    candidate = str(item).strip()
                if _should_refresh_for_change(
                    repo_root=self._repo_root,
                    changed_path=candidate,
                    watch_targets=self._watch_targets,
                ):
                    return True
        return False

    def close(self) -> None:
        process = self._process
        with contextlib.suppress(Exception):
            if process.stdin is not None:
                process.stdin.write(json.dumps(["unsubscribe", self._watch_root, self._subscription]) + "\n")
                process.stdin.flush()
        with contextlib.suppress(Exception):
            if process.poll() is None:
                process.terminate()
        with contextlib.suppress(Exception):
            process.wait(timeout=2)
        if process.poll() is None:
            with contextlib.suppress(Exception):
                process.kill()
            with contextlib.suppress(Exception):
                process.wait(timeout=2)
        for stream in (process.stdin, process.stdout, process.stderr):
            with contextlib.suppress(Exception):
                if stream is not None:
                    stream.close()


class _GitFsmonitorRuntimeWatcher:
    backend = "git-fsmonitor"

    def __init__(self, *, repo_root: Path, watch_targets: Sequence[str], bootstrap: bool) -> None:
        self._repo_root = repo_root
        self._watch_targets = tuple(watch_targets)
        if bootstrap:
            result = store.bootstrap_git_fsmonitor(repo_root=repo_root)
            if not bool(result.get("active")):
                raise RuntimeError(str(result.get("detail", "")).strip() or "git fsmonitor bootstrap failed")
        elif not bool(store.git_fsmonitor_status(repo_root=repo_root).get("active")):
            raise RuntimeError("git fsmonitor is not active")
        self._last_changed_paths = tuple(governance.collect_git_changed_paths(repo_root=repo_root))

    def wait_for_change(self, *, stop_file: Path, poll_seconds: int) -> bool:
        deadline = time.monotonic() + max(1, int(poll_seconds))
        while time.monotonic() < deadline:
            if stop_file.exists():
                return False
            current_changed_paths = tuple(governance.collect_git_changed_paths(repo_root=self._repo_root))
            if current_changed_paths != self._last_changed_paths:
                changed_union = tuple(dict.fromkeys((*self._last_changed_paths, *current_changed_paths)))
                self._last_changed_paths = current_changed_paths
                if any(
                    _should_refresh_for_change(
                        repo_root=self._repo_root,
                        changed_path=changed_path,
                        watch_targets=self._watch_targets,
                    )
                    for changed_path in changed_union
                ):
                    return True
            time.sleep(0.25)
        return not stop_file.exists()

    def close(self) -> None:
        return None


def _build_runtime_watcher(*, repo_root: Path, backend: str) -> Any:
    watch_targets = store.watch_targets(repo_root=repo_root)
    requested = str(backend or "auto").strip().lower()
    backend_report = store.watcher_backend_report(repo_root=repo_root) if requested == "auto" else {}
    if requested == "auto":
        ordered = [store.preferred_watcher_backend(repo_root=repo_root), "watchman", "watchdog", "git-fsmonitor", "poll"]
    else:
        ordered = [requested]
    seen: set[str] = set()
    for candidate in ordered:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            if candidate == "watchman":
                return _WatchmanRuntimeWatcher(repo_root=repo_root, watch_targets=watch_targets)
            if candidate == "watchdog":
                return _WatchdogRuntimeWatcher(repo_root=repo_root, watch_targets=watch_targets)
            if candidate == "git-fsmonitor":
                bootstrap_git_fsmonitor = requested == "git-fsmonitor" or bool(backend_report.get("bootstrap_recommended"))
                return _GitFsmonitorRuntimeWatcher(
                    repo_root=repo_root,
                    watch_targets=watch_targets,
                    bootstrap=bootstrap_git_fsmonitor,
                )
            if candidate == "poll":
                return _PollingRuntimeWatcher()
        except Exception:
            if requested != "auto":
                raise
            continue
    return _PollingRuntimeWatcher()

def _run_serve(
    *,
    repo_root: Path,
    force: bool,
    interval_seconds: int,
    watcher_backend: str,
    scope: str,
    spawn_reason: str,
    idle_timeout_seconds: int,
) -> int:
    existing_pid = _read_pid(store.pid_path(repo_root=repo_root))
    if existing_pid and _pid_alive(existing_pid):
        print(f"odylith context engine serve already running with pid {existing_pid}")
        return 0
    stop_file = store.stop_path(repo_root=repo_root)
    if stop_file.exists():
        stop_file.unlink()
    _write_pid(repo_root=repo_root)
    _write_daemon_metadata(
        repo_root=repo_root,
        spawn_reason=spawn_reason,
        idle_timeout_seconds=max(0, int(idle_timeout_seconds)),
        auth_token=secrets.token_urlsafe(24),
    )
    daemon_server = _RuntimeDaemonServer(
        repo_root=repo_root,
        auth_token=str(_read_daemon_metadata(repo_root=repo_root).get("auth_token", "")).strip(),
    )
    daemon_server.start()
    watcher = _build_runtime_watcher(repo_root=repo_root, backend=watcher_backend)
    try:
        first = True
        while True:
            if stop_file.exists():
                break
            if _autospawn_daemon_idle_expired(
                repo_root=repo_root,
                spawn_reason=spawn_reason,
                idle_timeout_seconds=idle_timeout_seconds,
            ):
                break
            if first:
                summary = store.warm_projections(
                    repo_root=repo_root,
                    force=bool(force and first),
                    reason="serve",
                    scope=scope,
                )
                odylith_context_engine_daemon_wait_runtime.record_projection_fingerprint(
                    repo_root=repo_root,
                    projection_fingerprint=str(summary.get("projection_fingerprint", "")).strip(),
                )
                first = False
                continue
            if not watcher.wait_for_change(stop_file=stop_file, poll_seconds=max(1, int(interval_seconds))):
                continue
            if _autospawn_daemon_idle_expired(
                repo_root=repo_root,
                spawn_reason=spawn_reason,
                idle_timeout_seconds=idle_timeout_seconds,
            ):
                break
            summary = store.warm_projections(
                repo_root=repo_root,
                force=False,
                reason="serve",
                scope=scope,
            )
            odylith_context_engine_daemon_wait_runtime.record_projection_fingerprint(
                repo_root=repo_root,
                projection_fingerprint=str(summary.get("projection_fingerprint", "")).strip(),
            )
    except KeyboardInterrupt:
        return 130
    finally:
        with contextlib.suppress(Exception):
            watcher.close()
        with contextlib.suppress(Exception):
            daemon_server.close()
        _clear_pid(repo_root=repo_root)
        _clear_daemon_metadata(repo_root=repo_root)
        if stop_file.exists():
            stop_file.unlink()
    print("odylith context engine serve loop stopped")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    args = _parse_args(raw_argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    preferred_python = _preferred_odylith_python(repo_root=repo_root)
    if str(Path(preferred_python).resolve()) != str(Path(sys.executable).resolve()):
        return _run_workspace_python_handoff(
            repo_root=repo_root,
            python_path=preferred_python,
            argv=raw_argv,
        )
    client_mode = str(getattr(args, "client_mode", "auto")).strip().lower()
    command = str(args.command)
    if command == "warmup":
        if _should_try_daemon(client_mode=client_mode, repo_root=repo_root):
            payload = _daemon_request(
                repo_root=repo_root,
                command="warmup",
                payload={
                    "force": bool(args.force),
                    "reason": "warmup",
                    "scope": str(args.scope),
                },
                required=_client_mode_required(client_mode),
            )
            if payload is not None:
                print("odylith context engine warmup passed")
                print(f"- repo_root: {repo_root}")
                print(f"- updated_utc: {payload.get('updated_utc', '')}")
                print(f"- projection_fingerprint: {payload.get('projection_fingerprint', '')}")
                print(f"- projection_scope: {payload.get('projection_scope', '')}")
                print(f"- watcher_backend: {payload.get('watcher_backend', '')}")
                print(f"- updated_projections: {', '.join(payload.get('updated_projections', [])) or 'none'}")
                return 0
        return _run_warmup(repo_root=repo_root, force=bool(args.force), reason="warmup", scope=str(args.scope))
    if command == "serve":
        return _run_serve(
            repo_root=repo_root,
            force=bool(args.force),
            interval_seconds=max(1, int(args.interval_seconds)),
            watcher_backend=str(args.watcher_backend),
            scope=str(args.scope),
            spawn_reason=str(args.spawn_reason),
            idle_timeout_seconds=max(0, int(args.idle_timeout_seconds)),
        )
    if command == "query":
        if _should_try_daemon(client_mode=client_mode, repo_root=repo_root):
            payload = _daemon_request(
                repo_root=repo_root,
                command="query",
                payload={
                    "text": str(args.text),
                    "limit": max(1, int(args.limit)),
                    "kinds": [str(kind).strip() for kind in args.kind if str(kind).strip()],
                },
                required=_client_mode_required(client_mode),
            )
            if payload is not None:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return 0
        return _return_local_result_with_optional_autospawn(
            repo_root=repo_root,
            client_mode=client_mode,
            command=command,
            exit_code=_run_query(
                repo_root=repo_root,
                text=str(args.text),
                limit=max(1, int(args.limit)),
                kinds=[str(kind).strip() for kind in args.kind if str(kind).strip()],
            ),
        )
    if command == "surface-read":
        entity = str(getattr(args, "entity", ""))
        workstream = str(getattr(args, "workstream", ""))
        component = str(getattr(args, "component", ""))
        paths = [str(path).strip() for path in getattr(args, "path", []) if str(path).strip()]
        session_id = str(getattr(args, "session_id", ""))
        claim_paths = [str(path).strip() for path in getattr(args, "claim_path", []) if str(path).strip()]
        working_tree_scope = str(getattr(args, "working_tree_scope", "repo"))
        case = str(getattr(args, "case", ""))
        view = str(getattr(args, "view", ""))
        if _should_try_daemon(client_mode=client_mode, repo_root=repo_root):
            payload = _daemon_request(
                repo_root=repo_root,
                command="surface-read",
                payload={
                    "entity": entity,
                    "workstream": workstream,
                    "component": component,
                    "paths": paths,
                    "session_id": session_id,
                    "claim_paths": claim_paths,
                    "working_tree_scope": working_tree_scope,
                    "case": case,
                    "view": view,
                },
                required=_client_mode_required(client_mode),
            )
            if payload is not None:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return 0
        return _run_surface_read(
            repo_root=repo_root,
            entity=entity,
            workstream=workstream,
            component=component,
            paths=paths,
            session_id=session_id,
            claim_paths=claim_paths,
            working_tree_scope=working_tree_scope,
            case=case,
            view=view,
        )
    if command == "context":
        if _should_try_daemon(client_mode=client_mode, repo_root=repo_root):
            payload = _daemon_request(
                repo_root=repo_root,
                command="context",
                payload={
                    "ref": str(args.ref),
                    "kind": str(args.kind),
                    "event_limit": max(1, int(args.event_limit)),
                    "relation_limit": max(1, int(args.relation_limit)),
                },
                required=_client_mode_required(client_mode),
            )
            if payload is not None:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return 0
        return _return_local_result_with_optional_autospawn(
            repo_root=repo_root,
            client_mode=client_mode,
            command=command,
            exit_code=_run_context(
                repo_root=repo_root,
                ref=str(args.ref),
                kind=str(args.kind),
                event_limit=max(1, int(args.event_limit)),
                relation_limit=max(1, int(args.relation_limit)),
            ),
        )
    if command == "impact":
        if _should_try_daemon(client_mode=client_mode, repo_root=repo_root):
            payload = _daemon_request(
                repo_root=repo_root,
                command="impact",
                payload={
                    "paths": [str(path).strip() for path in args.paths if str(path).strip()],
                    "use_working_tree": bool(args.working_tree),
                    "working_tree_scope": str(args.working_tree_scope),
                    "session_id": str(args.session_id),
                    "claim_paths": [str(path).strip() for path in args.claim_path if str(path).strip()],
                    "test_limit": max(1, int(args.test_limit)),
                },
                required=_client_mode_required(client_mode),
            )
            if payload is not None:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return 0
        return _return_local_result_with_optional_autospawn(
            repo_root=repo_root,
            client_mode=client_mode,
            command=command,
            exit_code=_run_impact(
                repo_root=repo_root,
                paths=[str(path).strip() for path in args.paths if str(path).strip()],
                use_working_tree=bool(args.working_tree),
                working_tree_scope=str(args.working_tree_scope),
                session_id=str(args.session_id),
                claim_paths=[str(path).strip() for path in args.claim_path if str(path).strip()],
                test_limit=max(1, int(args.test_limit)),
            ),
        )
    if command == "architecture":
        if _should_try_daemon(client_mode=client_mode, repo_root=repo_root):
            payload = _daemon_request(
                repo_root=repo_root,
                command="architecture",
                payload={
                    "paths": [str(path).strip() for path in args.paths if str(path).strip()],
                    "use_working_tree": bool(args.working_tree),
                    "working_tree_scope": str(args.working_tree_scope),
                    "session_id": str(args.session_id),
                    "claim_paths": [str(path).strip() for path in args.claim_path if str(path).strip()],
                },
                required=_client_mode_required(client_mode),
            )
            if payload is not None:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return 0
        return _return_local_result_with_optional_autospawn(
            repo_root=repo_root,
            client_mode=client_mode,
            command=command,
            exit_code=_run_architecture(
                repo_root=repo_root,
                paths=[str(path).strip() for path in args.paths if str(path).strip()],
                use_working_tree=bool(args.working_tree),
                working_tree_scope=str(args.working_tree_scope),
                session_id=str(args.session_id),
                claim_paths=[str(path).strip() for path in args.claim_path if str(path).strip()],
            ),
        )
    if command == "governance-slice":
        if _should_try_daemon(client_mode=client_mode, repo_root=repo_root):
            payload = _daemon_request(
                repo_root=repo_root,
                command="governance-slice",
                payload={
                    "paths": [str(path).strip() for path in args.paths if str(path).strip()],
                    "workstream": str(args.workstream),
                    "component": str(args.component),
                    "use_working_tree": bool(args.working_tree),
                    "working_tree_scope": str(args.working_tree_scope),
                    "session_id": str(args.session_id),
                    "claim_paths": [str(path).strip() for path in args.claim_path if str(path).strip()],
                },
                required=_client_mode_required(client_mode),
            )
            if payload is not None:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return 0
        return _return_local_result_with_optional_autospawn(
            repo_root=repo_root,
            client_mode=client_mode,
            command=command,
            exit_code=_run_governance_slice(
                repo_root=repo_root,
                paths=[str(path).strip() for path in args.paths if str(path).strip()],
                workstream=str(args.workstream),
                component=str(args.component),
                use_working_tree=bool(args.working_tree),
                working_tree_scope=str(args.working_tree_scope),
                session_id=str(args.session_id),
                claim_paths=[str(path).strip() for path in args.claim_path if str(path).strip()],
            ),
        )
    if command == "session-brief":
        if _should_try_daemon(client_mode=client_mode, repo_root=repo_root):
            payload = _daemon_request(
                repo_root=repo_root,
                command="session-brief",
                payload={
                    "paths": [str(path).strip() for path in args.paths if str(path).strip()],
                    "use_working_tree": bool(args.working_tree),
                    "working_tree_scope": str(args.working_tree_scope),
                    "session_id": str(args.session_id),
                    "workstream": str(args.workstream),
                    "intent": str(args.intent),
                    "surfaces": [str(token).strip() for token in args.surface if str(token).strip()],
                    "visible_text": [str(token).strip() for token in args.visible_text if str(token).strip()],
                    "active_tab": str(args.active_tab),
                    "user_turn_id": str(args.user_turn_id),
                    "supersedes_turn_id": str(args.supersedes_turn_id),
                    "claim_mode": str(args.claim_mode),
                    "claim_paths": [str(token).strip() for token in args.claim_path if str(token).strip()],
                    "lease_seconds": max(60, int(args.lease_seconds)),
                },
                required=_client_mode_required(client_mode),
            )
            if payload is not None:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return 0
        return _return_local_result_with_optional_autospawn(
            repo_root=repo_root,
            client_mode=client_mode,
            command=command,
            exit_code=_run_session_brief(
                repo_root=repo_root,
                paths=[str(path).strip() for path in args.paths if str(path).strip()],
                use_working_tree=bool(args.working_tree),
                working_tree_scope=str(args.working_tree_scope),
                session_id=str(args.session_id),
                workstream=str(args.workstream),
                intent=str(args.intent),
                surfaces=[str(token).strip() for token in args.surface if str(token).strip()],
                visible_text=[str(token).strip() for token in args.visible_text if str(token).strip()],
                active_tab=str(args.active_tab),
                user_turn_id=str(args.user_turn_id),
                supersedes_turn_id=str(args.supersedes_turn_id),
                claim_mode=str(args.claim_mode),
                claim_paths=[str(token).strip() for token in args.claim_path if str(token).strip()],
                lease_seconds=max(60, int(args.lease_seconds)),
            ),
        )
    if command == "bootstrap-session":
        if _should_try_daemon(client_mode=client_mode, repo_root=repo_root):
            payload = _daemon_request(
                repo_root=repo_root,
                command="bootstrap-session",
                payload={
                    "paths": [str(path).strip() for path in args.paths if str(path).strip()],
                    "use_working_tree": bool(args.working_tree),
                    "working_tree_scope": str(args.working_tree_scope),
                    "session_id": str(args.session_id),
                    "workstream": str(args.workstream),
                    "intent": str(args.intent),
                    "surfaces": [str(token).strip() for token in args.surface if str(token).strip()],
                    "visible_text": [str(token).strip() for token in args.visible_text if str(token).strip()],
                    "active_tab": str(args.active_tab),
                    "user_turn_id": str(args.user_turn_id),
                    "supersedes_turn_id": str(args.supersedes_turn_id),
                    "claim_mode": str(args.claim_mode),
                    "claim_paths": [str(token).strip() for token in args.claim_path if str(token).strip()],
                    "lease_seconds": max(60, int(args.lease_seconds)),
                    "doc_limit": max(1, int(args.doc_limit)),
                    "command_limit": max(1, int(args.command_limit)),
                    "test_limit": max(1, int(args.test_limit)),
                },
                required=_client_mode_required(client_mode),
            )
            if payload is not None:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return 0
        return _return_local_result_with_optional_autospawn(
            repo_root=repo_root,
            client_mode=client_mode,
            command=command,
            exit_code=_run_bootstrap_session(
                repo_root=repo_root,
                paths=[str(path).strip() for path in args.paths if str(path).strip()],
                use_working_tree=bool(args.working_tree),
                working_tree_scope=str(args.working_tree_scope),
                session_id=str(args.session_id),
                workstream=str(args.workstream),
                intent=str(args.intent),
                surfaces=[str(token).strip() for token in args.surface if str(token).strip()],
                visible_text=[str(token).strip() for token in args.visible_text if str(token).strip()],
                active_tab=str(args.active_tab),
                user_turn_id=str(args.user_turn_id),
                supersedes_turn_id=str(args.supersedes_turn_id),
                claim_mode=str(args.claim_mode),
                claim_paths=[str(token).strip() for token in args.claim_path if str(token).strip()],
                lease_seconds=max(60, int(args.lease_seconds)),
                doc_limit=max(1, int(args.doc_limit)),
                command_limit=max(1, int(args.command_limit)),
                test_limit=max(1, int(args.test_limit)),
            ),
        )
    if command == "doctor":
        return _run_doctor(
            repo_root=repo_root,
            bootstrap_watcher=bool(args.bootstrap_watcher),
        )
    if command == "benchmark":
        return _run_benchmark(
            repo_root=repo_root,
            benchmark_profile=str(args.profile).strip() or odylith_benchmark_runner.DEFAULT_CLI_BENCHMARK_PROFILE,
            modes=[str(token).strip() for token in args.mode if str(token).strip()],
            cache_profiles=[str(token).strip() for token in args.cache_profile if str(token).strip()],
            case_ids=[str(token).strip() for token in args.case_id if str(token).strip()],
            families=[str(token).strip() for token in args.family if str(token).strip()],
            shard_count=max(1, int(args.shard_count)),
            shard_index=max(1, int(args.shard_index)),
            limit=max(0, int(args.limit)),
            write_report=not bool(args.no_write_report),
            json_output=bool(args.json),
        )
    if command == "status":
        # Status is diagnostic truth, not a candidate for thin-client lag.
        # Always read the local store directly so evaluation/optimization views
        # reflect the current corpus and recent bootstrap packets.
        return _run_status(repo_root=repo_root)
    if command == "memory-snapshot":
        # The memory snapshot is a local derived-state truth surface and should
        # not lag behind daemon-side caches.
        return _run_memory_snapshot(repo_root=repo_root)
    if command == "odylith-switch":
        return _run_odylith_switch(
            repo_root=repo_root,
            enable=bool(args.enable),
            disable=bool(args.disable),
            clear=bool(args.clear),
            note=str(args.note),
        )
    if command == "odylith-remote-sync":
        return _run_odylith_remote_sync(
            repo_root=repo_root,
            dry_run=bool(args.dry_run),
        )
    if command == "stop":
        return _run_stop(repo_root=repo_root)
    print(f"unsupported odylith context engine command: {command}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
