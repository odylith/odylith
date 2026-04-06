"""Execution control helpers for live Odylith benchmark runs."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence


_DISABLED_TIMEOUT_TOKENS = frozenset({"0", "off", "none", "disabled", "disable", "infinite", "inf", "unbounded"})
_PROCESS_GROUP_TERMINATION_GRACE_SECONDS = 0.2
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
    try:
        stdout, stderr = process.communicate(input=input_text, timeout=timeout_seconds)
        return subprocess.CompletedProcess(
            args=list(command),
            returncode=int(process.returncode or 0),
            stdout=stdout,
            stderr=stderr,
        )
    except subprocess.TimeoutExpired as exc:
        _terminate_process_group(process, sig=signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=_PROCESS_GROUP_TERMINATION_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            _terminate_process_group(process, sig=signal.SIGKILL)
            stdout, stderr = process.communicate()
        exc.stdout = stdout
        exc.stderr = stderr
        raise
    except BaseException:
        _terminate_process_group(process, sig=signal.SIGTERM)
        try:
            process.wait(timeout=_PROCESS_GROUP_TERMINATION_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            _terminate_process_group(process, sig=signal.SIGKILL)
            with contextlib.suppress(OSError, subprocess.SubprocessError):
                process.wait(timeout=_PROCESS_GROUP_TERMINATION_GRACE_SECONDS)
        raise
