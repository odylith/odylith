"""Process helpers for release simulation scripts."""

from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path
import signal
import subprocess


def run_command_with_group_timeout(
    *,
    cwd: Path,
    env: Mapping[str, str],
    command: list[str],
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _terminate_process_group(process)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired as second_exc:
            _kill_process_group(process)
            stdout, stderr = process.communicate()
            stdout = _merge_timeout_streams(stdout, second_exc.stdout)
            stderr = _merge_timeout_streams(stderr, second_exc.stderr)
        stdout = _merge_timeout_streams(stdout, exc.stdout)
        stderr = _merge_timeout_streams(stderr, exc.stderr)
        timeout_note = f"command timed out after {timeout:.1f}s and process group was terminated"
        stderr = "\n".join(part for part in (str(stderr or "").rstrip(), timeout_note) if part)
        return subprocess.CompletedProcess(command, 124, stdout=stdout, stderr=stderr)
    return subprocess.CompletedProcess(command, process.returncode, stdout=stdout, stderr=stderr)


def _terminate_process_group(process: subprocess.Popen[str]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return


def _kill_process_group(process: subprocess.Popen[str]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return


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
