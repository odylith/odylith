"""Bound foreground hook work and own the subprocess groups it creates."""

from __future__ import annotations

from contextlib import contextmanager, nullcontext, suppress
from contextvars import ContextVar
from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
from typing import Iterator


class HookBudgetExpired(BaseException):
    """Unwind to the hook boundary without being swallowed by fail-soft engines."""


@dataclass(frozen=True)
class _Deadline:
    expires_at: float

    def remaining(self) -> float:
        remaining = self.expires_at - time.monotonic()
        if remaining <= 0:
            raise HookBudgetExpired
        return remaining

    @contextmanager
    def suspend_alarm(self) -> Iterator[None]:
        # communicate owns the command timeout. The alarm must not interrupt
        # launch, timeout handling, or entry into owned-process cleanup.
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        try:
            yield
        finally:
            remaining = self.expires_at - time.monotonic()
            if remaining > 0:
                signal.setitimer(signal.ITIMER_REAL, remaining)


_ACTIVE_DEADLINE: ContextVar[_Deadline | None] = ContextVar("hook_deadline", default=None)
_TERMINATION_GRACE_SECONDS = 0.2
_REAP_TIMEOUT_SECONDS = 0.5
_FOREGROUND_GROUP_ENV = "ODYLITH_HOOK_OWNS_FOREGROUND_GROUP"


def in_hook_owned_foreground_group() -> bool:
    """Identify inherited foreground lifetime ownership, never runtime trust."""
    return os.name == "posix" and os.environ.get(_FOREGROUND_GROUP_ENV) == "1"


@contextmanager
def hook_budget(*, seconds: float) -> Iterator[None]:
    """Apply one foreground POSIX budget, preserving any caller alarm deadline."""
    if (
        os.name != "posix"
        or not hasattr(signal, "setitimer")
        or threading.current_thread() is not threading.main_thread()
    ):
        raise HookBudgetExpired
    started = time.monotonic()
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    duration = min(seconds, previous_timer[0]) if previous_timer[0] > 0 else seconds
    if duration <= 0:
        raise HookBudgetExpired
    deadline = _Deadline(started + duration)

    def expire(_signum: int, _frame: object) -> None:
        raise HookBudgetExpired

    token = _ACTIVE_DEADLINE.set(deadline)
    try:
        signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, deadline.remaining())
        yield
        deadline.remaining()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        _ACTIVE_DEADLINE.reset(token)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer[0] > 0:
            remaining = max(0.000001, previous_timer[0] - (time.monotonic() - started))
            signal.setitimer(signal.ITIMER_REAL, remaining, previous_timer[1])


def _signal_owned_group(process: subprocess.Popen[str], sig: int) -> bool:
    # start_new_session makes the original PID our PGID. Do not resolve it via
    # a live leader: the leader may exit while its children keep running.
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        return False
    return True


def _finish_owned_process(process: subprocess.Popen[str]) -> None:
    grace_until = time.monotonic() + _TERMINATION_GRACE_SECONDS
    group_signalled = False
    try:
        if os.name == "posix":
            group_signalled = _signal_owned_group(process, signal.SIGTERM)
        elif process.poll() is None:
            process.terminate()
        with suppress(subprocess.TimeoutExpired):
            process.wait(timeout=_TERMINATION_GRACE_SECONDS)
        if group_signalled:
            # Leader exit must not preempt a child's asynchronous cleanup.
            remaining = grace_until - time.monotonic()
            if remaining > 0:
                time.sleep(remaining)
    finally:
        if os.name == "posix":
            _signal_owned_group(process, signal.SIGKILL)
        elif process.poll() is None:
            process.kill()
        try:
            process.wait(timeout=_REAP_TIMEOUT_SECONDS)
        finally:
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()


def run_hook_command(
    *, command: list[str], cwd: Path, timeout: float,
) -> subprocess.CompletedProcess[str] | None:
    """Fail soft for command errors, but never consume whole-hook cancellation."""
    deadline = _ACTIVE_DEADLINE.get()
    if deadline is not None:
        timeout = min(timeout, deadline.remaining())
    env = os.environ.copy()
    env.pop(_FOREGROUND_GROUP_ENV, None)
    if deadline is not None:
        env[_FOREGROUND_GROUP_ENV] = "1"
    process: subprocess.Popen[str] | None = None
    try:
        with deadline.suspend_alarm() if deadline is not None else nullcontext():
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(cwd),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    start_new_session=os.name == "posix",
                )
                if deadline is not None:
                    timeout = min(timeout, deadline.remaining())
                stdout, stderr = process.communicate(timeout=timeout)
                return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
            finally:
                if process is not None:
                    _finish_owned_process(process)
                if deadline is not None:
                    deadline.remaining()
    except (OSError, subprocess.SubprocessError):
        if deadline is not None:
            deadline.remaining()
        return None
