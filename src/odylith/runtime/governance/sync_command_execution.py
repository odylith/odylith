"""Run governed sync subprocesses with completion-aware waiting and owned cleanup."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any, Sequence

from odylith.runtime.surfaces import host_hook_execution


HEARTBEAT_INTERVAL_SECONDS = 10.0


def run_command(
    *,
    repo_root: Path,
    args: Sequence[str],
    heartbeat_label: str = "",
    timeout_seconds: float | None = None,
    pass_fds: tuple[int, ...] = (),
) -> int:
    env = os.environ.copy()
    cwd = Path.cwd()
    # Cross-repository renders must import the invoking Odylith runtime.
    pythonpath_tokens = [str(Path(__file__).resolve().parents[3])]
    raw_pythonpath = str(env.get("PYTHONPATH", "")).strip()
    if raw_pythonpath:
        for token in raw_pythonpath.split(os.pathsep):
            normalized = str((cwd / token).resolve()) if token and not Path(token).is_absolute() else token
            if normalized and normalized not in pythonpath_tokens:
                pythonpath_tokens.append(normalized)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_tokens)
    tokens = [str(token) for token in args]
    if tokens and tokens[0] == "python":
        tokens[0] = sys.executable
    if heartbeat_label or timeout_seconds is not None:
        started_at = time.perf_counter()
        last_heartbeat = started_at
        popen_kwargs: dict[str, Any] = {
            "cwd": str(repo_root),
            "env": env,
        }
        if os.name == "posix" and not host_hook_execution.in_hook_owned_foreground_group():
            popen_kwargs["start_new_session"] = True
        if pass_fds:
            popen_kwargs["pass_fds"] = pass_fds
        process = subprocess.Popen(tokens, **popen_kwargs)
        while True:
            rc = process.poll()
            if rc is not None:
                return int(rc)
            now = time.perf_counter()
            if timeout_seconds is not None and now - started_at >= float(timeout_seconds):
                print(
                    f"- timeout: {heartbeat_label or 'command'} exceeded "
                    f"{int(float(timeout_seconds))}s; terminating"
                )
                _terminate_process(process)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    _kill_process(process)
                    process.wait(timeout=5)
                return 124
            if now - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                print(f"- heartbeat: {heartbeat_label} still running ({int(now - started_at)}s)")
                last_heartbeat = now
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=0.5)
    completed = subprocess.run(
        tokens,
        cwd=str(repo_root),
        env=env,
        check=False,
        **({"pass_fds": pass_fds} if pass_fds else {}),
    )
    return int(completed.returncode)


def _terminate_process(process: subprocess.Popen[Any]) -> None:
    process_pid = int(getattr(process, "pid", 0) or 0)
    if os.name == "posix" and process_pid > 0:
        try:
            os.killpg(process_pid, signal.SIGTERM)
            return
        except (OSError, ProcessLookupError):
            pass
    process.terminate()


def _kill_process(process: subprocess.Popen[Any]) -> None:
    process_pid = int(getattr(process, "pid", 0) or 0)
    if os.name == "posix" and process_pid > 0:
        try:
            os.killpg(process_pid, signal.SIGKILL)
            return
        except (OSError, ProcessLookupError):
            pass
    process.kill()
