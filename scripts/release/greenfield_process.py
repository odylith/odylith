"""Process helpers for release simulation scripts."""

from __future__ import annotations

from collections.abc import Callable
from collections.abc import Mapping
import contextlib
from contextvars import ContextVar
import math
import os
from pathlib import Path
import signal
import subprocess
import time


CommandLifecycleObserver = Callable[[Mapping[str, object]], None]
_COMMAND_LIFECYCLE_OBSERVER: ContextVar[CommandLifecycleObserver | None] = ContextVar(
    "greenfield_command_lifecycle_observer",
    default=None,
)


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


class CommandLifecycleObserverError(RuntimeError):
    """Telemetry failed after a command reached a terminal outcome."""

    def __init__(self, *, command: list[str], result: subprocess.CompletedProcess[str], state: str) -> None:
        super().__init__("command lifecycle telemetry failed after terminal command outcome")
        self.command_kind = _command_kind(command)
        self.returncode = int(result.returncode)
        self.state = state


@contextlib.contextmanager
def command_lifecycle_observer(observer: CommandLifecycleObserver | None):
    """Scope redacted process lifecycle evidence to the current execution flow."""

    token = _COMMAND_LIFECYCLE_OBSERVER.set(observer)
    try:
        yield
    finally:
        _COMMAND_LIFECYCLE_OBSERVER.reset(token)


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
    started_at = time.monotonic()
    observer = _COMMAND_LIFECYCLE_OBSERVER.get()
    try:
        _notify_lifecycle_observer(
            observer,
            _command_lifecycle_event(
                state="started",
                command=command,
                pid=process.pid,
                timeout=timeout,
            ),
        )
        if on_started is not None:
            on_started(process.pid, process.pid)
    except BaseException as exc:
        _stdout, _stderr, termination_observation = _stop_process_group(process)
        _notify_interrupted_lifecycle(
            observer,
            command,
            process,
            timeout,
            started_at,
            exc,
            termination_observation,
        )
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
        result = GroupTimeoutCompletedProcess(
            command,
            124,
            stdout=stdout,
            stderr=stderr,
            termination_observation=termination_observation,
        )
        _notify_terminal_lifecycle(observer, command, result, started_at, state="timed_out")
        return result
    except BaseException as exc:
        _stdout, _stderr, termination_observation = _stop_process_group(process)
        _notify_interrupted_lifecycle(
            observer,
            command,
            process,
            timeout,
            started_at,
            exc,
            termination_observation,
        )
        raise
    result = subprocess.CompletedProcess(command, process.returncode, stdout=stdout, stderr=stderr)
    _notify_terminal_lifecycle(observer, command, result, started_at, state="completed")
    return result


def _command_lifecycle_event(
    *,
    state: str,
    command: list[str],
    pid: int,
    timeout: float,
) -> dict[str, object]:
    return {
        "state": state,
        "pid": int(pid),
        "pgid": int(pid),
        **_redacted_command_shape(command),
        "timeout_seconds": round(float(timeout), 3),
    }


def _redacted_command_shape(command: list[str]) -> dict[str, object]:
    return {
        "command_kind": _command_kind(command),
        "argument_count": len(command),
        "option_count": sum(1 for argument in command[1:] if argument.startswith("--")),
    }


def _command_kind(command: list[str]) -> str:
    executable_name = Path(str(command[0] if command else "")).name.lower()
    if executable_name.startswith(("python", "pypy")):
        return "python"
    if executable_name in {"bash", "sh", "zsh"}:
        return "shell"
    if executable_name == "git":
        return "git"
    if executable_name == "odylith":
        return "odylith"
    return "other"


def _terminal_lifecycle_event(
    command: list[str],
    result: subprocess.CompletedProcess[str],
    started_at: float,
    *,
    state: str,
) -> dict[str, object]:
    event = {
        "state": state,
        **_redacted_command_shape(command),
        "returncode": int(result.returncode),
        "elapsed_seconds": round(time.monotonic() - started_at, 3),
        "stdout_bytes": _stream_byte_count(result.stdout),
        "stderr_bytes": _stream_byte_count(result.stderr),
    }
    termination_observation = getattr(result, "termination_observation", None)
    if termination_observation is not None:
        event["termination_observation"] = str(termination_observation)
    return event


def _notify_terminal_lifecycle(
    observer: CommandLifecycleObserver | None,
    command: list[str],
    result: subprocess.CompletedProcess[str],
    started_at: float,
    *,
    state: str,
) -> None:
    try:
        _notify_lifecycle_observer(
            observer,
            _terminal_lifecycle_event(command, result, started_at, state=state),
        )
    except Exception as observer_error:
        raise CommandLifecycleObserverError(command=command, result=result, state=state) from observer_error


def _notify_interrupted_lifecycle(
    observer: CommandLifecycleObserver | None,
    command: list[str],
    process: subprocess.Popen[str],
    timeout: float,
    started_at: float,
    exc: BaseException,
    termination_observation: str,
) -> None:
    event = _command_lifecycle_event(
        state="interrupted",
        command=command,
        pid=process.pid,
        timeout=timeout,
    )
    event.update(
        {
            "elapsed_seconds": round(time.monotonic() - started_at, 3),
            "exception_type": type(exc).__name__,
            "termination_observation": termination_observation,
        }
    )
    try:
        _notify_lifecycle_observer(observer, event)
    except Exception as observer_error:
        exc.add_note(
            "command lifecycle telemetry failed after process cleanup: "
            f"{type(observer_error).__name__}: {observer_error}"
        )


def _notify_lifecycle_observer(observer: CommandLifecycleObserver | None, event: Mapping[str, object]) -> None:
    if observer is not None:
        observer(event)


def _stream_byte_count(value: str | bytes | None) -> int:
    return len(value) if isinstance(value, bytes) else len(str(value or "").encode("utf-8"))


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
