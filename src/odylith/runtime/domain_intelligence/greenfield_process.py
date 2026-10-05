"""Shared Greenfield process groups and independently enforced journey lifetime."""

from __future__ import annotations

from collections.abc import Callable
from collections.abc import Mapping
import contextlib
from contextvars import ContextVar
import math
import json
import hashlib
import secrets
import select
import socket
import threading
import sys
import os
from pathlib import Path
import signal
import subprocess
import time


_POPEN_TYPE = subprocess.Popen

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
        self.result = result
        self.command_kind = _command_kind(command)
        self.returncode = int(result.returncode)
        self.state = state
        self.termination_observation = getattr(result, "termination_observation", None)
        self.stdout = result.stdout
        self.stderr = result.stderr


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
    pass_fds: tuple[int, ...] = (),
    stdin_text: str | None = None,
    inherit_journey: bool = True,
) -> subprocess.CompletedProcess[str]:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("command timeout must be a positive finite number")
    owner = _ACTIVE_JOURNEY.get()
    command_env = dict(env)
    registration = _ACTIVE_REGISTRATION.get()
    if registration is not None and inherit_journey:
        command_env[_JOURNEY_CHANNEL_ENV] = str(registration.fileno())
        pass_fds = (*pass_fds, registration.fileno())
    else:
        command_env.pop(_JOURNEY_CHANNEL_ENV, None)
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=command_env,
        stdin=subprocess.PIPE if stdin_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        pass_fds=pass_fds,
    )
    if owner is not None:
        birth = _process_birth(process.pid)
        owner.send(json.dumps({"kind": "group", "pid": process.pid, "birth": birth}).encode())
        original_wait = process.wait
        def owned_wait(*args, **kwargs):
            # Capture same-group identities before communicate() reaps the leader.
            # A child closing its pipes must not lose custody after reparenting.
            # The parent has not reaped this child, so its PID cannot be reused;
            # Darwin's proc_pidinfo may already omit an exited zombie leader.
            if process.returncode is None:
                for pid, _ppid, pgid in _process_rows():
                    if pgid == process.pid:
                        owner.send(json.dumps({"kind": "group", "pid": pid, "birth": _process_birth(pid)}).encode())
            return original_wait(*args, **kwargs)
        process.wait = owned_wait
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
        exc.stdout, exc.stderr = _stdout, _stderr
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
        stdout, stderr = (process.communicate(timeout=timeout) if stdin_text is None
                          else process.communicate(input=stdin_text, timeout=timeout))
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
        exc.stdout, exc.stderr = _stdout, _stderr
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
    descendants = _descendant_groups(process.pid) if isinstance(process, _POPEN_TYPE) else set()
    for group in descendants:
        _signal_group(group, signal.SIGTERM)
    _terminate_process_group(process)
    try:
        stdout, stderr = process.communicate(timeout=5)
        for group in descendants:
            _signal_group(group, signal.SIGKILL)
        return stdout, stderr, "output_pipes_closed_after_sigterm"
    except subprocess.TimeoutExpired as second_exc:
        for group in descendants:
            _signal_group(group, signal.SIGKILL)
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
    _signal_group(process.pid, signal.SIGTERM)


def _kill_process_group(process: subprocess.Popen[str]) -> None:
    _signal_group(process.pid, signal.SIGKILL)


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


JOURNEY_CANCELLATION_GRACE_SECONDS = 2.0
JOURNEY_SUPERVISION_VERSION = "odylith.greenfield.journey-supervision.v1"
_JOURNEY_CHANNEL_ENV = "ODYLITH_GREENFIELD_JOURNEY_CHANNEL_FD"
_JOURNEY_MARKER = ".bounded-journey.v1.json"
_JOURNEY_COMPLETION = ".bounded-completion.v1.json"
_ACTIVE_JOURNEY: ContextVar[socket.socket | None] = ContextVar("greenfield_journey", default=None)
_ACTIVE_REGISTRATION: ContextVar[socket.socket | None] = ContextVar("greenfield_registration", default=None)
_REAL_MONOTONIC = time.monotonic


class JourneyCancelled(BaseException):
    """Unwind all Python work; the independent guardian also enforces native stalls."""


class JourneyDeliveryError(RuntimeError):
    """Completion may be accepted; an environment failure prevented delivery."""


def _signal_group(pid: int, sig: int) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(pid, sig)


def _finish_journey_pending(path: Path, *, journey_id: str, release: bool, marker_name: str = _JOURNEY_MARKER) -> bool:
    marker = path / marker_name
    try:
        if marker.is_symlink() or path.is_symlink() or json.loads(marker.read_text())["journey_id"] != journey_id:
            return False
        if release:
            # Only a delivered private receipt confers readiness. Stored state
            # is insufficient, including when every abort cleanup operation fails.
            return True
        elif marker_name == _JOURNEY_MARKER:
            # Canonical repo/hash denial survives removal of newly owned bytes.
            for name in ("product-create-transaction.v1.json", "product-create-transaction.v1.json.compiler-receipt.v1.json"):
                (path / name).unlink(missing_ok=True)
            marker.write_text(json.dumps({"journey_id": journey_id}), encoding="utf-8")
        else:
            import shutil
            shutil.rmtree(path)
        return True
    except (OSError, ValueError, KeyError, TypeError):
        # An unretired marker remains fail closed at the public resolver.
        return not release and not path.exists()


def _write_journey_marker(marker: Path, state: Mapping[str, object]) -> None:
    temporary = marker.with_name(marker.name + ".release")
    temporary.write_text(json.dumps(state), encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(marker)


def _write_journey_completion(path: Path, *, journey_id: str, finished: float, deadline: float) -> None:
    marker = json.loads((path / _JOURNEY_MARKER).read_text())
    _write_journey_marker(path / _JOURNEY_COMPLETION, {
        "version": "odylith.greenfield.journey-completion.v2", "status": "completion_attempt",
        "journey_id": journey_id, "transaction_hash": path.name,
        "completion_digest": marker["completion_digest"],
        "record_started_at": finished, "deadline": deadline,
    })


def _journey_guardian(channel: socket.socket, *, parent: int, expires: float,
                      journey_id: str, grace: float, registration: socket.socket | None = None) -> None:
    pending: set[Path] = set()
    accepted = False
    nonce = secrets.token_hex(32)  # Fresh exec RAM only, never sent to descendants.
    digest = hashlib.sha256(nonce.encode("ascii")).hexdigest()
    channels = [channel] if registration is None else [channel, registration]
    try:
        channel.send(b'{"ready":true}')
        roots: dict[int, str] = {}
        groups: set[int] = set()
        workspaces: set[Path] = set()
        done = False
        aborted = False
        while _REAL_MONOTONIC() < expires:
            readable, _, _ = select.select(channels, [], [], max(0.0, expires - _REAL_MONOTONIC()))
            if not readable:
                break
            incoming = readable[0]
            packet = incoming.recv(65536)
            if not packet:
                break
            message = json.loads(packet)
            if message["kind"] == "group":
                roots[int(message["pid"])] = message["birth"]
            elif message["kind"] in {"pending", "workspace"}:
                path = Path(message["path"])
                (pending if message["kind"] == "pending" else workspaces).add(path)
                response = {"journey_id": journey_id}
                if message["kind"] == "pending":
                    response.update(version=JOURNEY_SUPERVISION_VERSION, completion_digest=digest)
                incoming.send(json.dumps(response).encode())
            elif message["kind"] == "settle" and incoming is channel:
                done = True
                break
            elif message["kind"] == "abort" and incoming is channel:
                aborted = True
                break
        # Kernel birth identity prevents a completed child's reused PID or group
        # from conferring ownership over an unrelated process.
        groups = _owned_journey_groups(roots)
        for pid in groups:
            if pid in _current_owned_groups(roots):
                _signal_group(pid, signal.SIGTERM)
        if not done and not aborted:
            with contextlib.suppress(ProcessLookupError):
                os.kill(parent, signal.SIGALRM)
        end = (min(expires, _REAL_MONOTONIC()+0.05) if done else _REAL_MONOTONIC()+min(grace,0.05) if aborted else expires+grace)
        while _REAL_MONOTONIC() < end:
            readable, _, _ = select.select(channels, [], [], max(0.0, end - _REAL_MONOTONIC()))
            if readable:
                incoming = readable[0]
                packet = incoming.recv(65536)
                if packet:
                    message = json.loads(packet)
                    if message["kind"] == "group":
                        roots[int(message["pid"])] = message["birth"]
                        groups.update(_owned_journey_groups(roots))
                    elif message["kind"] in {"pending", "workspace"}:
                        (pending if message["kind"] == "pending" else workspaces).add(Path(message["path"]))
                    elif message["kind"] == "abort" and incoming is channel:
                        aborted = True
                        break
        for pid in _owned_journey_groups(roots):
            if pid in _current_owned_groups(roots):
                _signal_group(pid, signal.SIGKILL)
        if not done and not aborted:
            with contextlib.suppress(ProcessLookupError):
                os.kill(parent, signal.SIGKILL)
        for path in workspaces:
            _finish_journey_pending(path, journey_id=journey_id, release=False, marker_name=".bounded-workspace.v1.json")
        # The supported journey authors one candidate and seals at most one PCT.
        within = done and len(pending) <= 1 and _REAL_MONOTONIC() < expires
        if done:
            channel.send(json.dumps({"settled": within}).encode())
            if within:
                readable, _, _ = select.select([channel], [], [], max(0.0,expires-_REAL_MONOTONIC()))
                if readable:
                    message = json.loads(channel.recv(65536))
                    expires = min(expires, float(message.get("release_deadline", expires)))
                    within = message["kind"] == "release" and _REAL_MONOTONIC() < expires
                    aborted = message["kind"] == "abort"
                else:
                    within = False
                    with contextlib.suppress(ProcessLookupError):
                        os.kill(parent,signal.SIGALRM)
                    readable, _, _ = select.select([channel],[],[],max(0.0,expires+grace-_REAL_MONOTONIC()))
                    if readable:
                        aborted = json.loads(channel.recv(65536))["kind"] == "abort"
                    if not aborted:
                        with contextlib.suppress(ProcessLookupError):
                            os.kill(parent,signal.SIGKILL)
        for path in pending:
            if not _finish_journey_pending(path, journey_id=journey_id, release=within):
                within = False
        within = within and _REAL_MONOTONIC() < expires
        finished = _REAL_MONOTONIC()
        within = within and finished < expires
        if within and pending:
            path = next(iter(pending))
            _write_journey_completion(path, journey_id=journey_id, finished=finished, deadline=expires)
            finished = _REAL_MONOTONIC()
            within = finished < expires
        if not within:
            for path in pending:
                _finish_journey_pending(path, journey_id=journey_id, release=False)
        if done or aborted:
            outcome = {"completed": within, "publication_finished": finished}
            if within and pending:
                outcome["completion_receipt"] = {"version": "odylith.greenfield.completion-receipt.v1",
                    "journey_id": journey_id, "transaction_hash": next(iter(pending)).name, "nonce": nonce}
            # Irrevocable RAM acceptance precedes the first disclosure attempt.
            # Later channel errors are delivery unknown, never rollback authority.
            accepted = within
            channel.send(json.dumps(outcome).encode())
    except BaseException:
        if not accepted:
            with contextlib.suppress(OSError):
                channel.send(b'{"completed":false}')
        raise
    finally:
        if not accepted:
            for path in pending:
                _finish_journey_pending(path, journey_id=journey_id, release=False)


@contextlib.contextmanager
def supervise_greenfield_journey(*, seconds: float, started_at: float | None = None,
                                on_settled: Callable[[], float | None] | None = None,
                                on_published: Callable[[float], None] | None = None,
                                completion_receipt_sink: dict | None = None):
    """Own a POSIX guardian through settlement and actual pending publication.

    The guardian is an independent process, not a Python-only alarm. It stops
    owned child groups and a runner stuck in native work at deadline + 2 seconds.
    No receipt, environment duration, or detached CLI invocation supplies this
    capability. Guardian retirement and final preview presentation follow the
    measured interval.
    """
    if os.name != "posix" or threading.current_thread() is not threading.main_thread():
        raise RuntimeError("bounded Greenfield transport requires a POSIX main process")
    if _ACTIVE_JOURNEY.get() is not None:
        raise RuntimeError("a bounded Greenfield journey cannot nest or replenish")
    started = _REAL_MONOTONIC() if started_at is None else started_at
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    duration = min(seconds, previous_timer[0]) if previous_timer[0] > 0 else seconds
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("journey duration must be positive and finite")
    parent_channel, child_channel = socket.socketpair(type=socket.SOCK_DGRAM)
    child_registration, guardian_registration = socket.socketpair(type=socket.SOCK_DGRAM)
    journey_id = secrets.token_hex(32)
    def expired(_signum, _frame):
        raise JourneyCancelled("Greenfield whole journey deadline expired")
    signal.signal(signal.SIGALRM, expired)
    try:
        guardian_process = subprocess.Popen(
            [sys.executable, "-m", __name__, "--guardian", str(child_channel.fileno()),
             str(os.getpid()), str(started+duration), journey_id, str(JOURNEY_CANCELLATION_GRACE_SECONDS),
             str(guardian_registration.fileno())],
            pass_fds=(child_channel.fileno(), guardian_registration.fileno()), start_new_session=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except BaseException:
        parent_channel.close()
        child_channel.close()
        child_registration.close()
        guardian_registration.close()
        _restore_journey_alarm(previous_handler, previous_timer, started)
        raise
    guardian = guardian_process.pid
    child_channel.close()
    guardian_registration.close()
    token = _ACTIVE_JOURNEY.set(parent_channel)
    registration_token = _ACTIVE_REGISTRATION.set(child_registration)
    completed = False
    requested = False
    outcome_known = False
    try:
        parent_channel.settimeout(min(1.0, duration))
        if json.loads(parent_channel.recv(65536)).get("ready") is not True:
            raise RuntimeError("Greenfield guardian did not acquire live custody")
        if completion_receipt_sink is not None:
            completion_receipt_sink.clear()
        yield {"version": JOURNEY_SUPERVISION_VERSION, "guardian_pid": guardian,
               "cancellation_grace_seconds": JOURNEY_CANCELLATION_GRACE_SECONDS}
        parent_channel.send(b'{"kind":"settle"}')
        parent_channel.settimeout(max(0.001, started + duration - _REAL_MONOTONIC()))
        if json.loads(parent_channel.recv(65536)).get("settled") is not True:
            raise JourneyCancelled("Greenfield guarded settlement exceeded its deadline")
        publication_started = _REAL_MONOTONIC()
        remaining = on_settled() if on_settled is not None else None
        if _REAL_MONOTONIC() >= started + duration:
            raise JourneyCancelled("Greenfield guarded completion exceeded its deadline")
        release = {"kind": "release"}
        if remaining is not None:
            if not math.isfinite(remaining) or remaining <= 0:
                raise JourneyCancelled("Greenfield publication has no proposal budget remaining")
            release["release_deadline"] = min(started + duration, publication_started + remaining)
        requested = True
        parent_channel.send(json.dumps(release).encode())
        completion = json.loads(parent_channel.recv(65536))
        outcome_known = type(completion.get("completed")) is bool
        completed = completion.get("completed") is True
        if not completed:
            raise JourneyCancelled("Greenfield guarded publication was not released")
        if completion_receipt_sink is not None:
            completion_receipt_sink.update(completion.get("completion_receipt", {}))
        if on_published is not None:
            on_published(completion["publication_finished"])
    except BaseException as exc:
        if completed or (requested and not outcome_known):
            raise JourneyDeliveryError("Greenfield completion may be accepted; receipt delivery is unknown") from exc
        raise
    finally:
        _ACTIVE_JOURNEY.reset(token)
        _ACTIVE_REGISTRATION.reset(registration_token)
        cleanup_until = _REAL_MONOTONIC() + JOURNEY_CANCELLATION_GRACE_SECONDS
        if not completed:
            with contextlib.suppress(OSError):
                parent_channel.send(b'{"kind":"abort"}')
                parent_channel.settimeout(max(0.001,cleanup_until-_REAL_MONOTONIC()))
                parent_channel.recv(65536)
        parent_channel.close()
        child_registration.close()
        primary_error = sys.exception()
        try:
            guardian_process.wait(timeout=max(0.001,cleanup_until-_REAL_MONOTONIC()))
        except subprocess.TimeoutExpired:
            _signal_group(guardian, signal.SIGKILL)
            with contextlib.suppress(subprocess.TimeoutExpired):
                guardian_process.wait(timeout=0.25)
        except OSError as exc:
            if primary_error is None:
                raise JourneyDeliveryError("Greenfield completion was accepted; guardian retirement delivery is unknown") from exc
        finally:
            _restore_journey_alarm(previous_handler, previous_timer, started)


def _restore_journey_alarm(handler, timer, started):
    signal.setitimer(signal.ITIMER_REAL, 0)
    signal.signal(signal.SIGALRM, handler)
    if timer[0] > 0:
        signal.setitimer(signal.ITIMER_REAL, max(0.000001, timer[0]-(_REAL_MONOTONIC()-started)),timer[1])


def register_bounded_workspace(path: Path) -> None:
    """Let the same guardian clean its exact ephemeral directory after cancellation."""
    owner = _ACTIVE_JOURNEY.get()
    if owner is None:
        raise RuntimeError("Greenfield workspace has no live parent")
    owner.send(json.dumps({"kind":"workspace", "path":str(path)}).encode())
    response = json.loads(owner.recv(65536))
    marker = path / ".bounded-workspace.v1.json"
    marker.write_text(json.dumps(response),encoding="utf-8")
    marker.chmod(0o600)


def register_bounded_pending_transaction(path: Path) -> dict[str, str] | None:
    """Require an actual connected guardian before quarantining a new pending seal."""
    fd = os.environ.get(_JOURNEY_CHANNEL_ENV)
    if fd is None:
        return None
    channel = socket.socket(fileno=os.dup(int(fd)))
    try:
        channel.send(json.dumps({"kind": "pending", "path": str(path)}).encode())
        channel.settimeout(1.0)
        response = json.loads(channel.recv(65536))
        return response
    finally:
        channel.close()


def _process_rows() -> list[tuple[int, int, int]]:
    """Read bounded numeric topology for the groups this journey owns."""
    try:
        result = subprocess.run(["ps", "-axo", "pid=,ppid=,pgid="], capture_output=True,
                                text=True, timeout=0.25, check=True)
        return [tuple(map(int, row.split())) for row in result.stdout.splitlines()]
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


def _descendant_groups(parent: int) -> set[int]:
    rows = _process_rows()
    owned = {parent}
    groups: set[int] = set()
    while True:
        children = [(pid, pgid) for pid, ppid, pgid in rows if ppid in owned and pid not in owned]
        if not children:
            return groups
        owned.update(pid for pid, _ in children)
        groups.update(pgid for _, pgid in children if pgid != os.getpgrp())



def _process_birth(pid: int) -> str | None:
    """Read stable kernel launch identity on the declared Linux/macOS envelope."""
    try:
        if sys.platform.startswith("linux"):
            return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
        if sys.platform == "darwin":
            import ctypes
            # Darwin sys/proc_info.h: PROC_PIDTBSDINFO=3, proc_bsdinfo=136
            # bytes, with uint64 start_tvsec/start_tvusec as its final fields.
            buffer = ctypes.create_string_buffer(136)
            libproc = ctypes.CDLL("/usr/lib/libproc.dylib")
            if libproc.proc_pidinfo(pid, 3, 0, buffer, 136) == 136:
                return buffer.raw[-16:].hex()
    except (OSError, ValueError, IndexError):
        pass
    return None


def _current_owned_groups(roots: Mapping[int, str]) -> set[int]:
    groups: set[int] = set()
    for pid, birth in list(roots.items()):
        if birth is not None and _process_birth(pid) == birth:
            with contextlib.suppress(ProcessLookupError):
                groups.add(os.getpgid(pid))
    groups.discard(os.getpgrp())
    return groups


def _owned_journey_groups(roots: dict[int, str]) -> set[int]:
    # Retain stable member identities before TERM can orphan descendants. Numeric
    # PGID alone never grants a later signal when its original members are gone.
    groups = _current_owned_groups(roots)
    for pid, birth in list(roots.items()):
        if birth is not None and _process_birth(pid) == birth:
            groups.update(_descendant_groups(pid))
    for pid, _ppid, pgid in _process_rows():
        if pgid in groups:
            birth = _process_birth(pid)
            if birth is not None:
                roots[pid] = birth
    return _current_owned_groups(roots)

if __name__ == "__main__":
    if len(sys.argv) != 8 or sys.argv[1] != "--guardian":
        raise SystemExit("This module is the owned Greenfield guardian transport")
    channel = socket.socket(fileno=int(sys.argv[2]))
    registration = socket.socket(fileno=int(sys.argv[7]))
    try:
        _journey_guardian(channel, parent=int(sys.argv[3]), expires=float(sys.argv[4]),
                          journey_id=sys.argv[5], grace=float(sys.argv[6]), registration=registration)
    finally:
        channel.close()
        registration.close()
