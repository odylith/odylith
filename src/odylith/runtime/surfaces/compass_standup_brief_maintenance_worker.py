"""Own detached Compass worker identity and atomic maintenance-request custody."""

from __future__ import annotations

import datetime as dt
import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any, Iterator, Mapping

from odylith.common.json_objects import load_json_object as _load_json
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.surfaces import compass_refresh_contract
from odylith.runtime.surfaces import compass_standup_brief_narrator

REQUEST_VERSION = "v1"
STATE_VERSION = "v1"
_REQUEST_PATH = ".odylith/compass/standup-brief-maintenance-request.v1.json"
_STATE_PATH = ".odylith/compass/standup-brief-maintenance-state.v1.json"
_BACKGROUND_DISABLE_ENV = "ODYLITH_COMPASS_STANDUP_BACKGROUND_DISABLE"
_BACKGROUND_TEST_ALLOW_ENV = "ODYLITH_COMPASS_STANDUP_BACKGROUND_ALLOW_IN_TESTS"
_WORKER_MODULE = "odylith.runtime.surfaces.compass_standup_brief_maintenance"
_MAX_PROCESS_ARGS_BYTES = 1024 * 1024
_WORKER_EPOCH_RELATIVE_PATHS = (
    "surfaces/compass_standup_brief_maintenance.py",
    "surfaces/compass_standup_brief_maintenance_worker.py",
    "surfaces/compass_standup_brief_runtime_patch.py",
    "domain_intelligence/greenfield_managed_mutation_boundary.py",
    "domain_intelligence/greenfield_repository_lock.py",
    "domain_intelligence/greenfield_repository_write_set.py",
    "domain_intelligence/greenfield_commit_journal.py",
    "domain_intelligence/greenfield_generation_state.py",
    "domain_intelligence/greenfield_generation_store.py",
    "../install/upgrade_dashboard_recovery.py",
    "surfaces/compass_standup_brief_batch.py",
    "surfaces/compass_standup_brief_provider_contract.py",
    "surfaces/compass_standup_brief_narrator.py",
    "surfaces/compass_standup_brief_status.py",
    "surfaces/compass_standup_brief_substrate.py",
)


def maintenance_request_path(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / _REQUEST_PATH).resolve()


def maintenance_state_path(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / _STATE_PATH).resolve()


def now_utc_iso() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(*, repo_root: Path, path: Path, payload: Mapping[str, Any]) -> None:
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=path,
        content=json.dumps(payload, indent=2) + "\n",
        lock_key=str(path),
    )


def load_state(*, repo_root: Path) -> dict[str, Any]:
    state = _load_json(maintenance_state_path(repo_root=repo_root))
    entries = state.get("entries")
    return {
        "version": STATE_VERSION,
        "active_pid": int(state.get("active_pid", 0) or 0),
        "last_run_utc": str(state.get("last_run_utc", "")).strip(),
        "worker_epoch": str(state.get("worker_epoch", "")).strip(),
        "worker_python_bin": str(state.get("worker_python_bin", "")).strip(),
        "entries": dict(entries) if isinstance(entries, Mapping) else {},
    }


def write_state(*, repo_root: Path, state: Mapping[str, Any]) -> None:
    write_json(
        repo_root=repo_root,
        path=maintenance_state_path(repo_root=repo_root),
        payload={
            "version": STATE_VERSION,
            "active_pid": int(state.get("active_pid", 0) or 0),
            "last_run_utc": str(state.get("last_run_utc", "")).strip(),
            "worker_epoch": str(state.get("worker_epoch", "")).strip(),
            "worker_python_bin": str(state.get("worker_python_bin", "")).strip(),
            "entries": dict(state.get("entries", {})) if isinstance(state.get("entries"), Mapping) else {},
        },
    )


def pid_alive(pid: int) -> bool:
    if int(pid) <= 0:
        return False
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def worker_python_bin() -> str:
    return str(Path(sys.executable).resolve()) if str(sys.executable).strip() else "python3"


def worker_env() -> dict[str, str]:
    env = dict(os.environ)
    raw_pythonpath = str(env.get("PYTHONPATH", "")).strip()
    if raw_pythonpath:
        cwd = Path.cwd()
        tokens = []
        for raw_token in raw_pythonpath.split(os.pathsep):
            token = str(raw_token).strip()
            if not token:
                continue
            path = Path(token)
            tokens.append(str(path if path.is_absolute() else (cwd / path).resolve()))
        env["PYTHONPATH"] = os.pathsep.join(tokens)
    return env


def current_worker_epoch() -> str:
    root = Path(__file__).resolve().parents[1]
    return odylith_context_cache.fingerprint_payload(
        {
            "state_version": STATE_VERSION,
            "request_version": REQUEST_VERSION,
            "standup_brief_schema_version": compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            "paths": {
                relative_path: odylith_context_cache.path_signature(root / relative_path)
                for relative_path in _WORKER_EPOCH_RELATIVE_PATHS
            },
        }
    )


def worker_matches_current(*, state: Mapping[str, Any], python_bin: str) -> bool:
    return (
        str(state.get("worker_epoch", "")).strip() == current_worker_epoch()
        and str(state.get("worker_python_bin", "")).strip() == str(python_bin).strip()
    )


def _macos_process_argv(pid: int) -> tuple[str, ...] | None:
    # KERN_PROCARGS2: argc, executable path, NUL padding, argv, then environment.
    # Only argc strings are decoded; the trailing native buffer is never returned.
    query = ctypes.CDLL(None, use_errno=True).sysctl
    query.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_uint, ctypes.c_void_p,
                     ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p, ctypes.c_size_t]
    query.restype = ctypes.c_int
    mib = (ctypes.c_int * 3)(1, 49, pid)  # CTL_KERN, KERN_PROCARGS2
    size = ctypes.c_size_t()
    if query(mib, 3, None, ctypes.byref(size), None, 0) != 0:
        return None
    if not ctypes.sizeof(ctypes.c_int) < size.value <= _MAX_PROCESS_ARGS_BYTES:
        return None
    buffer = ctypes.create_string_buffer(size.value)
    if query(mib, 3, buffer, ctypes.byref(size), None, 0) != 0 or size.value > len(buffer):
        return None
    raw = buffer.raw[:size.value]
    header = ctypes.sizeof(ctypes.c_int)
    if len(raw) <= header:
        return None
    argc = int.from_bytes(raw[:header], sys.byteorder, signed=True)
    if not 0 < argc <= 4096 or argc > len(raw) - header:
        return None
    end = raw.find(b"\0", header)
    if end <= header:
        return None
    cursor = end + 1
    while cursor < len(raw) and raw[cursor] == 0:
        cursor += 1
    arguments = []
    for _ in range(argc):
        end = raw.find(b"\0", cursor)
        if end < 0:
            return None
        arguments.append(os.fsdecode(raw[cursor:end]))
        cursor = end + 1
    return tuple(arguments)


def _native_process_argv(pid: int) -> tuple[str, ...] | None:
    if not 0 < int(pid) < 2**31:
        return None
    try:
        if sys.platform == "darwin":
            return _macos_process_argv(int(pid))
        if sys.platform.startswith("linux"):
            with Path(f"/proc/{int(pid)}/cmdline").open("rb") as stream:
                raw = stream.read(_MAX_PROCESS_ARGS_BYTES + 1)
            if not raw or len(raw) > _MAX_PROCESS_ARGS_BYTES or not raw.endswith(b"\0"):
                return None
            return tuple(os.fsdecode(argument) for argument in raw[:-1].split(b"\0"))
    except (OSError, AttributeError, ValueError):
        return None
    return None


def _matches_worker_argv(argv: tuple[str, ...] | None, *, repo_root: Path, previous_python_bin: str = "") -> bool:
    if not isinstance(argv, tuple) or len(argv) not in {5, 6}:
        return False
    interpreters = {worker_python_bin(), str(sys.executable), str(previous_python_bin)}
    return (
        bool(argv[0]) and Path(argv[0]).is_absolute() and argv[0] in interpreters
        and argv[1:5] == ("-m", _WORKER_MODULE, "--repo-root", str(Path(repo_root).resolve()))
        and (len(argv) == 5 or argv[5] == "--emit-output")
    )


def terminate_worker(pid: int, *, repo_root: Path, previous_python_bin: str = "") -> bool:
    """Stop only a reverified actor; replacement waits for observed termination."""
    if not pid_alive(pid):
        return True
    if not _matches_worker_argv(
        _native_process_argv(pid), repo_root=repo_root, previous_python_bin=previous_python_bin,
    ):
        return not pid_alive(pid)
    try:
        os.kill(int(pid), signal.SIGTERM)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        if not pid_alive(pid):
            return True
        time.sleep(0.05)
    return not pid_alive(pid)


def maintenance_worker_pids(*, repo_root: Path, previous_python_bin: str = "") -> list[int] | None:
    try:
        completed = subprocess.run(  # noqa: S603
            ["ps", "-ww", "-ax", "-o", "pid=,command="],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    pids: list[int] = []
    for raw_line in str(completed.stdout or "").splitlines():
        line = str(raw_line).strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            return None
        pid_token, command = parts
        try:
            pid = int(pid_token)
        except ValueError:
            return None
        if pid <= 0 or _WORKER_MODULE not in command:
            continue
        argv = _native_process_argv(pid)
        if argv is None:
            return None
        if _matches_worker_argv(argv, repo_root=repo_root, previous_python_bin=previous_python_bin):
            pids.append(pid)
    return sorted(set(pids))


def candidate_key(*, window_key: str, scope_id: str = "") -> str:
    return f"global:{window_key}" if not str(scope_id).strip() else f"scoped:{window_key}:{str(scope_id).strip()}"


def maybe_spawn_background(*, repo_root: Path) -> int:
    if not compass_refresh_contract.background_maintenance_allowed(repo_root=repo_root):
        return 0
    if str(os.environ.get(_BACKGROUND_DISABLE_ENV, "")).strip() == "1":
        return 0
    if str(os.environ.get("PYTEST_CURRENT_TEST", "")).strip() and str(os.environ.get(_BACKGROUND_TEST_ALLOW_ENV, "")).strip() != "1":
        return 0
    repo_root = Path(repo_root).resolve()
    request_file = maintenance_request_path(repo_root=repo_root)
    request_payload = _load_json(request_file)
    if not request_has_entries(request_payload):
        return 0
    state = load_state(repo_root=repo_root)
    active_pid = int(state.get("active_pid", 0) or 0)
    python_bin = worker_python_bin()
    previous_python_bin = str(state.get("worker_python_bin", ""))
    inventory = maintenance_worker_pids(repo_root=repo_root, previous_python_bin=previous_python_bin)
    if inventory is None:
        return 0
    live_worker_pids = [
        pid for pid in inventory if int(pid) != int(os.getpid())
    ]
    if active_pid not in live_worker_pids and pid_alive(active_pid):
        return 0
    if active_pid in live_worker_pids and worker_matches_current(state=state, python_bin=python_bin):
        for pid in live_worker_pids:
            if pid != active_pid:
                terminate_worker(pid, repo_root=repo_root, previous_python_bin=previous_python_bin)
        return active_pid
    for pid in live_worker_pids:
        if not terminate_worker(pid, repo_root=repo_root, previous_python_bin=previous_python_bin):
            return 0
    state["active_pid"] = 0
    worker = subprocess.Popen(  # noqa: S603
        [
            python_bin,
            "-m",
            "odylith.runtime.surfaces.compass_standup_brief_maintenance",
            "--repo-root",
            str(repo_root),
        ],
        cwd=str(repo_root),
        env=worker_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    state["active_pid"] = int(worker.pid or 0)
    state["worker_epoch"] = current_worker_epoch()
    state["worker_python_bin"] = python_bin
    write_state(repo_root=repo_root, state=state)
    return int(worker.pid or 0)


def request_has_entries(payload: Mapping[str, Any] | None) -> bool:
    return isinstance(payload, Mapping) and next(request_entries(payload), None) is not None


def request_entries(request: Mapping[str, Any]) -> Iterator[tuple[str, str, Mapping[str, Any]]]:
    def valid(entry: Any) -> bool:
        return (
            isinstance(entry, Mapping) and bool(str(entry.get("fingerprint", "")).strip())
            and isinstance(entry.get("fact_packet"), Mapping) and bool(entry["fact_packet"])
        )

    global_entries = request.get("global") if isinstance(request.get("global"), Mapping) else {}
    scoped_entries = request.get("scoped") if isinstance(request.get("scoped"), Mapping) else {}
    for window, entry in global_entries.items():
        if valid(entry):
            yield str(window).strip(), "", entry
    for window, entries in scoped_entries.items():
        if not isinstance(entries, Mapping):
            continue
        for scope, entry in entries.items():
            if valid(entry):
                yield str(window).strip(), str(scope).strip(), entry


def pending_request_payload(
    *,
    request: Mapping[str, Any],
    state_entries: Mapping[str, Any],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "version": str(request.get("version", REQUEST_VERSION)).strip() or REQUEST_VERSION,
        "generated_utc": str(request.get("generated_utc", "")).strip(),
        "runtime_input_fingerprint": str(request.get("runtime_input_fingerprint", "")).strip(),
        "global": {},
        "scoped": {},
    }

    global_requests = request.get("global") if isinstance(request.get("global"), Mapping) else {}
    for window_key, entry in global_requests.items():
        if not isinstance(entry, Mapping) or not str(entry.get("fingerprint", "")).strip():
            continue
        key = candidate_key(window_key=str(window_key).strip())
        state_entry = state_entries.get(key) if isinstance(state_entries.get(key), Mapping) else {}
        if str(state_entry.get("fingerprint", "")).strip() != str(entry.get("fingerprint", "")).strip():
            payload["global"][str(window_key).strip()] = dict(entry)
            continue
        if str(state_entry.get("status", "")).strip().lower() in {"ready", "skipped"}:
            continue
        payload["global"][str(window_key).strip()] = dict(entry)

    scoped_requests = request.get("scoped") if isinstance(request.get("scoped"), Mapping) else {}
    for window_key, entries in scoped_requests.items():
        if not isinstance(entries, Mapping):
            continue
        retained_window: dict[str, Any] = {}
        for scope_id, entry in entries.items():
            if not isinstance(entry, Mapping) or not str(entry.get("fingerprint", "")).strip():
                continue
            scope_token = str(scope_id).strip()
            key = candidate_key(window_key=str(window_key).strip(), scope_id=scope_token)
            state_entry = state_entries.get(key) if isinstance(state_entries.get(key), Mapping) else {}
            if str(state_entry.get("fingerprint", "")).strip() != str(entry.get("fingerprint", "")).strip():
                retained_window[scope_token] = dict(entry)
                continue
            if str(state_entry.get("status", "")).strip().lower() in {"ready", "skipped"}:
                continue
            retained_window[scope_token] = dict(entry)
        if retained_window:
            payload["scoped"][str(window_key).strip()] = retained_window
    return payload


def pending_request_delay_seconds(
    *,
    request: Mapping[str, Any],
    state_entries: Mapping[str, Any],
    current_provider_name: str = "",
) -> float | None:
    if not request_has_entries(request):
        return None
    now = dt.datetime.now(tz=dt.timezone.utc)
    min_delay: float | None = None

    def _consider_entry(*, key: str, entry: Mapping[str, Any]) -> None:
        nonlocal min_delay
        state_entry = state_entries.get(key) if isinstance(state_entries.get(key), Mapping) else {}
        if str(state_entry.get("fingerprint", "")).strip() != str(entry.get("fingerprint", "")).strip():
            min_delay = 0.0
            return
        prior_provider = str(state_entry.get("provider_name", "")).strip().lower()
        if prior_provider and current_provider_name and prior_provider != current_provider_name.lower():
            min_delay = 0.0
            return
        if str(state_entry.get("status", "")).strip().lower() in {"ready", "skipped"}:
            return
        next_retry_dt = compass_standup_brief_narrator._parse_iso_datetime(  # noqa: SLF001
            str(state_entry.get("next_retry_utc", "")).strip()
        )
        if next_retry_dt is None:
            min_delay = 0.0
            return
        delay_seconds = max(0.0, (next_retry_dt - now).total_seconds())
        if min_delay is None or delay_seconds < min_delay:
            min_delay = delay_seconds

    global_requests = request.get("global") if isinstance(request.get("global"), Mapping) else {}
    for window_key, entry in global_requests.items():
        if not isinstance(entry, Mapping) or not str(entry.get("fingerprint", "")).strip():
            continue
        _consider_entry(key=candidate_key(window_key=str(window_key).strip()), entry=entry)
        if min_delay == 0.0:
            return 0.0

    scoped_requests = request.get("scoped") if isinstance(request.get("scoped"), Mapping) else {}
    for window_key, entries in scoped_requests.items():
        if not isinstance(entries, Mapping):
            continue
        for scope_id, entry in entries.items():
            if not isinstance(entry, Mapping) or not str(entry.get("fingerprint", "")).strip():
                continue
            _consider_entry(
                key=candidate_key(window_key=str(window_key).strip(), scope_id=str(scope_id).strip()),
                entry=entry,
            )
            if min_delay == 0.0:
                return 0.0
    return min_delay



# This value describes the code imported by this process, never a later disk edit.
LOADED_WORKER_EPOCH = current_worker_epoch()


def replace_request(*, repo_root: Path, payload: Mapping[str, Any]) -> None:
    with odylith_context_cache.advisory_lock(repo_root=repo_root, key="compass-maintenance-request-custody"):
        path = maintenance_request_path(repo_root=repo_root)
        if request_has_entries(payload):
            write_json(repo_root=repo_root, path=path, payload=payload)
        else:
            path.unlink(missing_ok=True)


def stamp_request(*, repo_root: Path, runtime_input_fingerprint: str) -> None:
    if not str(runtime_input_fingerprint).strip():
        return
    with odylith_context_cache.advisory_lock(repo_root=repo_root, key="compass-maintenance-request-custody"):
        path = maintenance_request_path(repo_root=repo_root)
        payload = _load_json(path)
        if request_has_entries(payload):
            payload["runtime_input_fingerprint"] = str(runtime_input_fingerprint).strip()
            write_json(repo_root=repo_root, path=path, payload=payload)


def finish_request(
    *, repo_root: Path, request: Mapping[str, Any], pending: Mapping[str, Any]
) -> dict[str, Any]:
    """Only consume the exact request that was processed; a foreground replacement wins."""
    with odylith_context_cache.advisory_lock(repo_root=repo_root, key="compass-maintenance-request-custody"):
        path = maintenance_request_path(repo_root=repo_root)
        latest = _load_json(path)
        if latest != request:
            return latest
        if request_has_entries(pending):
            write_json(repo_root=repo_root, path=path, payload=pending)
            return dict(pending)
        path.unlink(missing_ok=True)
        return {}
