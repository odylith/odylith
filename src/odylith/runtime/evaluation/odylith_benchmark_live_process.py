"""Execution control helpers for live Odylith benchmark runs."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Mapping, Sequence


_DISABLED_TIMEOUT_TOKENS = frozenset({"0", "off", "none", "disabled", "disable", "infinite", "inf", "unbounded"})
_PROCESS_GROUP_TERMINATION_GRACE_SECONDS = 0.2
_PROCESS_CAPTURE_POLL_SECONDS = 0.05
_DEFAULT_LIVE_TIMEOUT_SECONDS = 1200.0
_MIN_TIMEOUT_SECONDS = 30.0
_MISSING = object()


def _default_live_timeout_policy(scenario: Mapping[str, Any] | None) -> tuple[float | None, str]:
    scenario_timeout_seconds = _scenario_live_timeout_seconds(scenario)
    if scenario_timeout_seconds is not None:
        return scenario_timeout_seconds, "scenario_timeout"
    return _DEFAULT_LIVE_TIMEOUT_SECONDS, "default_live_timeout"


def _timeout_override(raw: Any) -> float | None | object:
    token = str(raw or "").strip().lower()
    if not token:
        return _MISSING
    if token in _DISABLED_TIMEOUT_TOKENS:
        return None
    with contextlib.suppress(ValueError):
        return max(0.0, float(token))
    return _MISSING


def _scenario_live_timeout_seconds(scenario: Mapping[str, Any] | None) -> float | None:
    if not isinstance(scenario, Mapping):
        return None
    with contextlib.suppress(TypeError, ValueError):
        budget = float(scenario.get("live_timeout_seconds") or 0.0)
        if budget > 0.0:
            return max(_MIN_TIMEOUT_SECONDS, budget)
    return None


def _resolved_live_timeout_budget(
    *,
    scenario: Mapping[str, Any] | None,
    environ: Mapping[str, str] | None = None,
) -> tuple[float | None, str]:
    env = dict(os.environ if environ is None else environ)
    env_override = _timeout_override(env.get("ODYLITH_BENCHMARK_CODEX_TIMEOUT_SECONDS", ""))
    if env_override is None:
        return None, "env_disabled"
    if env_override is not _MISSING:
        return max(_MIN_TIMEOUT_SECONDS, float(env_override)), "env_override"
    return _default_live_timeout_policy(scenario)


def _validator_timeout_seconds(*, environ: Mapping[str, str] | None = None) -> float | None:
    env = dict(os.environ if environ is None else environ)
    env_override = _timeout_override(env.get("ODYLITH_BENCHMARK_VALIDATOR_TIMEOUT_SECONDS", ""))
    if env_override is None:
        return None
    if env_override is not _MISSING:
        return max(15.0, float(env_override))
    return None


def _terminate_process_group(process: subprocess.Popen[str], *, sig: int) -> None:
    if process.poll() is not None:
        return
    with contextlib.suppress(OSError, ProcessLookupError):
        os.killpg(os.getpgid(process.pid), sig)


def _drain_stream(
    stream: Any | None,
    *,
    sink: list[str],
    errors: list[BaseException],
) -> None:
    if stream is None:
        return
    try:
        chunk = stream.read()
        if chunk:
            sink.append(str(chunk))
    except BaseException as exc:  # pragma: no cover - defensive capture
        errors.append(exc)
    finally:
        with contextlib.suppress(OSError, ValueError):
            stream.close()


def _feed_stdin(
    stream: Any | None,
    *,
    payload: str | None,
    errors: list[BaseException],
) -> None:
    if stream is None:
        return
    try:
        if payload:
            stream.write(payload)
            stream.flush()
    except BrokenPipeError:
        return
    except BaseException as exc:  # pragma: no cover - defensive capture
        errors.append(exc)
    finally:
        with contextlib.suppress(OSError, ValueError):
            stream.close()


def _join_capture_threads(threads: Sequence[threading.Thread]) -> None:
    for thread in threads:
        if thread.is_alive():
            thread.join(timeout=1.0)


def _run_subprocess_capture(
    *,
    command: Sequence[str],
    cwd: Path,
    env: Mapping[str, str] | None = None,
    input_text: str | None = None,
    timeout_seconds: float | None = None,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        list(command),
        cwd=str(cwd),
        env=dict(os.environ if env is None else env),
        stdin=subprocess.PIPE if input_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    reader_errors: list[BaseException] = []
    stdin_errors: list[BaseException] = []
    stdout_thread = threading.Thread(
        target=_drain_stream,
        args=(process.stdout,),
        kwargs={"sink": stdout_chunks, "errors": reader_errors},
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_drain_stream,
        args=(process.stderr,),
        kwargs={"sink": stderr_chunks, "errors": reader_errors},
        daemon=True,
    )
    stdin_thread = threading.Thread(
        target=_feed_stdin,
        args=(process.stdin,),
        kwargs={"payload": input_text, "errors": stdin_errors},
        daemon=True,
    )
    threads = (stdout_thread, stderr_thread, stdin_thread)
    for thread in threads:
        thread.start()
    deadline = None
    if timeout_seconds is not None:
        deadline = time.monotonic() + max(0.0, float(timeout_seconds))
    try:
        timed_out = False
        while process.poll() is None:
            if deadline is not None and time.monotonic() >= deadline:
                timed_out = True
                _terminate_process_group(process, sig=signal.SIGTERM)
                try:
                    process.wait(timeout=_PROCESS_GROUP_TERMINATION_GRACE_SECONDS)
                except subprocess.TimeoutExpired:
                    _terminate_process_group(process, sig=signal.SIGKILL)
                    process.wait()
                break
            time.sleep(_PROCESS_CAPTURE_POLL_SECONDS)
        if not timed_out:
            process.wait()
        _join_capture_threads(threads)
        if reader_errors:
            raise reader_errors[0]
        if stdin_errors:
            raise stdin_errors[0]
        stdout = "".join(stdout_chunks)
        stderr = "".join(stderr_chunks)
        if timed_out:
            raise subprocess.TimeoutExpired(
                cmd=list(command),
                timeout=0.0 if timeout_seconds is None else float(timeout_seconds),
                output=stdout,
                stderr=stderr,
            )
        return subprocess.CompletedProcess(
            args=list(command),
            returncode=int(process.returncode or 0),
            stdout=stdout,
            stderr=stderr,
        )
    except subprocess.TimeoutExpired as exc:
        _join_capture_threads(threads)
        exc.stdout = "".join(stdout_chunks)
        exc.stderr = "".join(stderr_chunks)
        raise
    except BaseException:
        _terminate_process_group(process, sig=signal.SIGTERM)
        try:
            process.wait(timeout=_PROCESS_GROUP_TERMINATION_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            _terminate_process_group(process, sig=signal.SIGKILL)
            with contextlib.suppress(OSError, subprocess.SubprocessError):
                process.wait(timeout=_PROCESS_GROUP_TERMINATION_GRACE_SECONDS)
        _join_capture_threads(threads)
        raise
