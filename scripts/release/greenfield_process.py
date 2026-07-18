"""Process helpers for release simulation scripts."""

from __future__ import annotations

from collections.abc import Callable
from collections.abc import Mapping
import contextlib
import math
import os
from pathlib import Path
import signal
import subprocess


class GroupTimeoutCompletedProcess(subprocess.CompletedProcess[str]):
    """Completed process with the observable result of timeout cleanup."""

    def __init__(
        self,
        args: list[str],
        returncode: int,
        *,
        stdout: str,
        stderr: str,
        termination_observation: str,
    ) -> None:
        super().__init__(args, returncode, stdout=stdout, stderr=stderr)
        self.termination_observation = termination_observation


def run_command_with_group_timeout(
    *,
    cwd: Path,
    env: Mapping[str, str],
    command: list[str],
    timeout: float,
    on_started: Callable[[int, int], None] | None = None,
) -> subprocess.CompletedProcess[str]:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("command timeout must be a positive finite number")
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    if on_started is not None:
        try:
            on_started(process.pid, process.pid)
        except BaseException:
            _stop_process_group(process)
            raise
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, termination_observation = _stop_process_group(process)
        stdout = _merge_timeout_streams(stdout, exc.stdout)
        stderr = _merge_timeout_streams(stderr, exc.stderr)
        timeout_note = f"command timed out after {timeout:.1f}s and process group was terminated"
        if termination_observation == "output_pipes_still_open_after_sigkill":
            timeout_note += "; output pipes remained open after SIGKILL, so escaped descendant cleanup is unverified"
        stderr = "\n".join(part for part in (str(stderr or "").rstrip(), timeout_note) if part)
        return GroupTimeoutCompletedProcess(
            command,
            124,
            stdout=stdout,
            stderr=stderr,
            termination_observation=termination_observation,
        )
    except BaseException:
        _stop_process_group(process)
        raise
    return subprocess.CompletedProcess(command, process.returncode, stdout=stdout, stderr=stderr)


def _stop_process_group(process: subprocess.Popen[str]) -> tuple[str, str, str]:
    _terminate_process_group(process)
    try:
        stdout, stderr = process.communicate(timeout=5)
        return stdout, stderr, "output_pipes_closed_after_sigterm"
    except subprocess.TimeoutExpired as second_exc:
        _kill_process_group(process)
        try:
            stdout, stderr = process.communicate(timeout=1)
            return stdout, stderr, "output_pipes_closed_after_sigkill"
        except subprocess.TimeoutExpired as third_exc:
            _close_output_pipes(process)
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=1)
            return (
                _merge_timeout_streams(third_exc.stdout, second_exc.stdout),
                _merge_timeout_streams(third_exc.stderr, second_exc.stderr),
                "output_pipes_still_open_after_sigkill",
            )


def _terminate_process_group(process: subprocess.Popen[str]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return


def _kill_process_group(process: subprocess.Popen[str]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        return


def _close_output_pipes(process: subprocess.Popen[str]) -> None:
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            with contextlib.suppress(OSError, ValueError):
                stream.close()


def _merge_timeout_streams(primary: str | bytes | None, fallback: str | bytes | None) -> str:
    primary_text = _decode_stream(primary)
    fallback_text = _decode_stream(fallback)
    if fallback_text and fallback_text not in primary_text:
        return "\n".join(part for part in (primary_text.rstrip(), fallback_text) if part)
    return primary_text


def _decode_stream(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value or "")
