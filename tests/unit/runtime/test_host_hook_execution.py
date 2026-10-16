from __future__ import annotations

from contextlib import contextmanager, suppress
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import pytest

from odylith.runtime.surfaces import claude_host_shared, codex_host_shared, host_hook_execution


pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX native hook ownership contract")


def _is_running(pid: int) -> bool:
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True, timeout=1,
    )
    return bool(result.stdout.strip()) and not result.stdout.lstrip().startswith("Z")


def _assert_processes_stopped(pids: list[int]) -> None:
    deadline = time.monotonic() + 1
    while any(_is_running(pid) for pid in pids) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not any(_is_running(pid) for pid in pids)


@pytest.mark.parametrize("exit_early", [False, True])
@pytest.mark.parametrize("scoped", [False, True])
def test_expired_command_stops_owned_children_even_after_leader_exit(
    tmp_path: Path, exit_early: bool, scoped: bool,
) -> None:
    grandchild = (
        "import os,signal,time; from pathlib import Path; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "Path('grandchild.pid').write_text(str(os.getpid())); time.sleep(30)"
    )
    child = (
        "import os,signal,subprocess,sys,time; from pathlib import Path; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "Path('child.pid').write_text(str(os.getpid())); "
        f"subprocess.Popen([sys.executable, '-c', {grandchild!r}]); time.sleep(30)"
    )
    parent = (
        "import os,subprocess,sys,time; from pathlib import Path\n"
        "Path('parent.pid').write_text(str(os.getpid()))\n"
        f"subprocess.Popen([sys.executable, '-c', {child!r}])\n"
        "while not Path('grandchild.pid').exists(): time.sleep(0.005)\n"
        + ("sys.exit(0)\n" if exit_early else "time.sleep(30)\n")
    )
    command = [sys.executable, "-c", parent]
    started = time.monotonic()
    try:
        if scoped:
            with pytest.raises(host_hook_execution.HookBudgetExpired):
                with host_hook_execution.hook_budget(seconds=0.4):
                    host_hook_execution.run_hook_command(command=command, cwd=tmp_path, timeout=20)
        else:
            assert host_hook_execution.run_hook_command(command=command, cwd=tmp_path, timeout=0.4) is None
        assert time.monotonic() - started < 2
        pids = [int((tmp_path / name).read_text()) for name in ("parent.pid", "child.pid", "grandchild.pid")]
        _assert_processes_stopped(pids)
    finally:
        if (tmp_path / "parent.pid").exists():
            with suppress(ProcessLookupError):
                os.killpg(int((tmp_path / "parent.pid").read_text()), signal.SIGKILL)


def test_success_does_not_leave_descendants_with_closed_capture_streams(tmp_path: Path) -> None:
    child = (
        "import os,signal,time; from pathlib import Path; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "Path('child.pid').write_text(str(os.getpid())); time.sleep(30)"
    )
    parent = (
        "import os,subprocess,sys,time; from pathlib import Path\n"
        "Path('parent.pid').write_text(str(os.getpid()))\n"
        f"subprocess.Popen([sys.executable, '-c', {child!r}], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
        "while not Path('child.pid').exists(): time.sleep(0.005)\n"
        "print('complete')\n"
    )
    try:
        result = host_hook_execution.run_hook_command(command=[sys.executable, "-c", parent], cwd=tmp_path, timeout=2)
        assert result is not None and result.returncode == 0 and result.stdout == "complete\n"
        _assert_processes_stopped([int((tmp_path / "child.pid").read_text())])
    finally:
        if (tmp_path / "parent.pid").exists():
            with suppress(ProcessLookupError):
                os.killpg(int((tmp_path / "parent.pid").read_text()), signal.SIGKILL)


@pytest.mark.parametrize("host", [codex_host_shared, claude_host_shared])
def test_both_host_adapters_use_owned_runner(host, monkeypatch, tmp_path: Path) -> None:
    launcher = tmp_path / ".odylith/bin/odylith"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("fixture launcher\n")
    calls = []
    monkeypatch.setattr(host_hook_execution, "run_hook_command", lambda **kwargs: calls.append(kwargs))
    host.run_odylith(project_dir=tmp_path, args=["sync"], timeout=180)
    assert calls == [{"command": [str(launcher), "sync"], "cwd": tmp_path, "timeout": 180}]


def test_budget_preserves_handler_timer_and_elapsed_deadline() -> None:
    original_handler = signal.getsignal(signal.SIGALRM)
    original_timer = signal.getitimer(signal.ITIMER_REAL)

    def prior_handler(_signum, _frame):
        raise AssertionError("Prior timer should not fire")

    try:
        signal.signal(signal.SIGALRM, prior_handler)
        signal.setitimer(signal.ITIMER_REAL, 2, 3)
        with host_hook_execution.hook_budget(seconds=1):
            time.sleep(0.05)
        remaining, interval = signal.getitimer(signal.ITIMER_REAL)
        assert 1.5 < remaining < 1.98
        assert interval == 3
        assert signal.getsignal(signal.SIGALRM) is prior_handler
        assert host_hook_execution._ACTIVE_DEADLINE.get() is None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, original_handler)
        signal.setitimer(signal.ITIMER_REAL, *original_timer)


def test_expired_budget_restores_state_and_is_not_an_ordinary_exception() -> None:
    previous_handler = signal.getsignal(signal.SIGALRM)
    with pytest.raises(host_hook_execution.HookBudgetExpired):
        with host_hook_execution.hook_budget(seconds=0.03):
            try:
                time.sleep(1)
            except Exception:
                pytest.fail("Engine fail-soft handling swallowed hook cancellation")
    assert signal.getsignal(signal.SIGALRM) is previous_handler
    assert signal.getitimer(signal.ITIMER_REAL) == (0, 0)
    assert host_hook_execution._ACTIVE_DEADLINE.get() is None


def test_unsupported_thread_defers_before_work() -> None:
    calls = []

    def worker():
        try:
            with host_hook_execution.hook_budget(seconds=1):
                calls.append("work")
        except host_hook_execution.HookBudgetExpired:
            calls.append("deferred")

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=1)
    assert not thread.is_alive()
    assert calls == ["deferred"]


def test_missing_command_fails_soft(tmp_path: Path) -> None:
    assert host_hook_execution.run_hook_command(command=[str(tmp_path / "absent")], cwd=tmp_path, timeout=1) is None


def test_deadline_cannot_skip_cleanup_when_command_timeout_wins(monkeypatch, tmp_path: Path) -> None:
    processes = []
    launch = subprocess.Popen
    suspend_alarm = host_hook_execution._Deadline.suspend_alarm

    def tracked_launch(*args, **kwargs):
        process = launch(*args, **kwargs)
        processes.append(process)
        return process

    @contextmanager
    def scheduled_suspend(deadline):
        # Model descheduling after communicate times out but before a separate
        # cleanup scope can disarm the asynchronous whole-hook alarm.
        if processes:
            time.sleep(max(0, deadline.expires_at - time.monotonic()) + 0.02)
        with suspend_alarm(deadline):
            yield

    monkeypatch.setattr(host_hook_execution.subprocess, "Popen", tracked_launch)
    monkeypatch.setattr(host_hook_execution._Deadline, "suspend_alarm", scheduled_suspend)
    try:
        with suppress(host_hook_execution.HookBudgetExpired):
            with host_hook_execution.hook_budget(seconds=0.5):
                host_hook_execution.run_hook_command(
                    command=[sys.executable, "-c", "import time; time.sleep(30)"],
                    cwd=tmp_path,
                    timeout=0.15,
                )
        assert len(processes) == 1
        assert processes[0].poll() is not None, "Whole-hook alarm skipped owned-process cleanup"
    finally:
        for process in processes:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=1)


def test_start_sync_and_log_share_one_monotonic_deadline(monkeypatch, tmp_path: Path) -> None:
    now = [100.0]
    timeouts = []

    class Command:
        returncode = 0

        def communicate(self, *, timeout):
            timeouts.append(timeout)
            now[0] += 2
            return "", ""

    monkeypatch.setattr(host_hook_execution.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(host_hook_execution.subprocess, "Popen", lambda *args, **kwargs: Command())
    monkeypatch.setattr(host_hook_execution, "_finish_owned_process", lambda process: None)
    with host_hook_execution.hook_budget(seconds=14):
        for phase, timeout in (("start", 20), ("sync", 180), ("compass", 20)):
            assert host_hook_execution.run_hook_command(command=[phase], cwd=tmp_path, timeout=timeout) is not None
    assert timeouts == [14, 12, 10]


def test_foreground_marker_is_child_local_and_not_forwarded_to_unowned_sessions(monkeypatch, tmp_path: Path) -> None:
    environments = []

    class Command:
        returncode = 0

        def communicate(self, *, timeout):
            return "", ""

    def launch(*args, **kwargs):
        environments.append(kwargs["env"])
        return Command()

    marker = host_hook_execution._FOREGROUND_GROUP_ENV
    monkeypatch.delenv(marker, raising=False)
    monkeypatch.setattr(host_hook_execution.subprocess, "Popen", launch)
    monkeypatch.setattr(host_hook_execution, "_finish_owned_process", lambda process: None)
    with host_hook_execution.hook_budget(seconds=1):
        host_hook_execution.run_hook_command(command=["start"], cwd=tmp_path, timeout=20)
    assert marker not in os.environ
    assert environments[0][marker] == "1"
    monkeypatch.setenv(marker, "1")
    host_hook_execution.run_hook_command(command=["sync"], cwd=tmp_path, timeout=180)
    assert marker not in environments[1]
    assert os.environ[marker] == "1"


def test_cleanup_error_cannot_swallow_expired_whole_hook_budget(monkeypatch, tmp_path: Path) -> None:
    now = [100.0]

    class Command:
        returncode = 0

        def communicate(self, *, timeout):
            return "", ""

    def cleanup(process):
        now[0] += 20
        raise OSError("cleanup failed after budget expiry")

    monkeypatch.setattr(host_hook_execution.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(host_hook_execution.subprocess, "Popen", lambda *args, **kwargs: Command())
    monkeypatch.setattr(host_hook_execution, "_finish_owned_process", cleanup)
    with pytest.raises(host_hook_execution.HookBudgetExpired):
        with host_hook_execution.hook_budget(seconds=14):
            host_hook_execution.run_hook_command(command=["sync"], cwd=tmp_path, timeout=180)


def test_group_grace_allows_child_cleanup_after_leader_exits(tmp_path: Path) -> None:
    grandchild = (
        "import os,time; from pathlib import Path; "
        "Path('grandchild.pid').write_text(str(os.getpid())); time.sleep(30)"
    )
    child = (
        "import os,signal,subprocess,sys,threading,time\nfrom pathlib import Path\n"
        f"grandchild = subprocess.Popen([sys.executable, '-c', {grandchild!r}], start_new_session=True)\n"
        "def cleanup():\n"
        "    time.sleep(0.05)\n"
        "    grandchild.terminate()\n"
        "    grandchild.wait(timeout=1)\n"
        "    Path('cleanup-complete').write_text('done')\n"
        "    os._exit(0)\n"
        "signal.signal(signal.SIGTERM, lambda *_: threading.Thread(target=cleanup).start())\n"
        "Path('child.pid').write_text(str(os.getpid()))\n"
        "time.sleep(30)\n"
    )
    parent = (
        "import os,subprocess,sys,time\nfrom pathlib import Path\n"
        "Path('parent.pid').write_text(str(os.getpid()))\n"
        f"subprocess.Popen([sys.executable, '-c', {child!r}])\n"
        "while not Path('grandchild.pid').exists(): time.sleep(0.005)\n"
        "time.sleep(30)\n"
    )
    sibling = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)
    started = time.monotonic()
    try:
        with pytest.raises(host_hook_execution.HookBudgetExpired):
            with host_hook_execution.hook_budget(seconds=0.4):
                host_hook_execution.run_hook_command(command=[sys.executable, "-c", parent], cwd=tmp_path, timeout=20)
        assert time.monotonic() - started < 1.5
        assert (tmp_path / "cleanup-complete").read_text() == "done"
        pids = [int((tmp_path / name).read_text()) for name in ("parent.pid", "child.pid", "grandchild.pid")]
        _assert_processes_stopped(pids)
        assert sibling.poll() is None
    finally:
        for name in ("parent.pid", "child.pid", "grandchild.pid"):
            path = tmp_path / name
            if path.exists() and _is_running(int(path.read_text())):
                with suppress(ProcessLookupError):
                    os.kill(int(path.read_text()), signal.SIGKILL)
        sibling.kill()
        sibling.wait(timeout=1)
