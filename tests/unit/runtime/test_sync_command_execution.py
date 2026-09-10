"""Completion latency and lifecycle laws for governed sync subprocesses."""

import inspect
from pathlib import Path

import pytest

from odylith.runtime.governance import sync_command_execution as execution
from odylith.runtime.governance import sync_workstream_artifacts as sync


@pytest.mark.parametrize("returncode", [0, 7])
@pytest.mark.parametrize("heartbeat_label", ["", "radar"])
def test_completed_child_is_observed_without_polling_delay(
    tmp_path: Path, monkeypatch, returncode: int, heartbeat_label: str,
) -> None:
    now = 0.0
    waits = []

    def advance(seconds: float) -> None:
        nonlocal now
        now += seconds

    class Process:
        def poll(self):
            return returncode if now >= 0.03 else None

        def wait(self, timeout):
            waits.append(timeout)
            advance(0.03 - now)
            return returncode

        def terminate(self):
            pytest.fail("a completed child must not be terminated")

        def kill(self):
            pytest.fail("a completed child must not be killed")

    monkeypatch.setattr(execution.subprocess, "Popen", lambda *args, **kwargs: Process())
    monkeypatch.setattr(execution.time, "perf_counter", lambda: now)
    monkeypatch.setattr(execution.time, "sleep", advance)
    result = execution.run_command(
        repo_root=tmp_path, args=["renderer"], heartbeat_label=heartbeat_label,
        timeout_seconds=1,
    )

    assert result == returncode
    assert now == pytest.approx(0.03)
    assert waits == [0.5]


def test_sync_uses_the_command_owner_without_private_compatibility_shims() -> None:
    for retired in ("_run_command", "_active_odylith_import_roots", "_terminate_process", "_kill_process"):
        assert not hasattr(sync, retired)
    assert "sync_workstream_artifacts" not in inspect.getsource(execution)


@pytest.mark.parametrize("error_type", [OSError, ValueError])
def test_wait_does_not_swallow_non_timeout_errors(tmp_path: Path, monkeypatch, error_type) -> None:
    class Process:
        def poll(self):
            return None

        def wait(self, timeout):
            raise error_type("wait failure")

    monkeypatch.setattr(execution.subprocess, "Popen", lambda *args, **kwargs: Process())
    with pytest.raises(error_type, match="wait failure"):
        execution.run_command(repo_root=tmp_path, args=["renderer"], timeout_seconds=1)


@pytest.mark.parametrize("process_group", [False, True])
def test_running_child_keeps_heartbeat_and_timeout_kill_escalation(
    tmp_path: Path, monkeypatch, capsys, process_group: bool,
) -> None:
    if process_group and execution.os.name != "posix":
        pytest.skip("POSIX process-group signaling")
    now = 0.0
    signals = []
    waits = []

    class Process:
        pid = 4321 if process_group else 0
        killed = False

        def poll(self):
            return None

        def wait(self, timeout):
            nonlocal now
            waits.append(timeout)
            if self.killed:
                return -9
            now += timeout
            raise execution.subprocess.TimeoutExpired("renderer", timeout)

        def terminate(self):
            signals.append("terminate")

        def kill(self):
            signals.append("kill")
            self.killed = True

    process = Process()

    def signal_group(pid, signal):
        assert pid == process.pid
        signals.append(signal)
        if signal == execution.signal.SIGKILL:
            process.killed = True

    monkeypatch.setattr(execution.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(execution.time, "perf_counter", lambda: now)
    monkeypatch.setattr(execution, "HEARTBEAT_INTERVAL_SECONDS", 0.25)
    if process_group:
        monkeypatch.setattr(execution.os, "killpg", signal_group)
    result = execution.run_command(
        repo_root=tmp_path, args=["renderer"], heartbeat_label="radar", timeout_seconds=1,
    )

    assert result == 124
    assert waits == [0.5, 0.5, 5, 5]
    assert signals == (
        [execution.signal.SIGTERM, execution.signal.SIGKILL]
        if process_group else ["terminate", "kill"]
    )
    output = capsys.readouterr().out
    assert "heartbeat: radar still running" in output
    assert "timeout: radar exceeded 1s; terminating" in output


def test_run_command_absolutizes_pythonpath_for_cross_repo_sync(tmp_path: Path, monkeypatch) -> None:
    commands: dict[str, object] = {}

    def _fake_run(args, cwd, env, check):  # noqa: ANN001
        commands["args"] = list(args)
        commands["cwd"] = cwd
        commands["env"] = dict(env)
        commands["check"] = check

        class _Completed:
            returncode = 0

        return _Completed()

    monkeypatch.setenv("PYTHONPATH", "src")
    monkeypatch.setattr(execution.subprocess, "run", _fake_run)

    rc = execution.run_command(  # noqa: SLF001
        repo_root=tmp_path,
        args=("python", "-m", "odylith.runtime.governance.normalize_plan_risk_mitigation", "--repo-root", str(tmp_path)),
    )

    assert rc == 0
    assert commands["args"][0] == execution.sys.executable
    assert commands["cwd"] == str(tmp_path)
    assert commands["check"] is False
    assert commands["env"]["PYTHONPATH"] == str((Path.cwd() / "src").resolve())


def test_run_command_terminates_timed_out_child_process(tmp_path: Path, monkeypatch, capsys) -> None:
    class _FakeProcess:
        def __init__(self) -> None:
            self.terminated = False
            self.killed = False
            self.wait_calls: list[float | None] = []

        def poll(self) -> int | None:
            return None

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, timeout: float | None = None) -> int:
            self.wait_calls.append(timeout)
            if timeout == 0.5:
                raise execution.subprocess.TimeoutExpired("renderer", timeout)
            return 0

        def kill(self) -> None:
            self.killed = True

    process = _FakeProcess()
    perf_counter_values = iter([0.0, 0.0, 1.2])

    monkeypatch.setattr(execution.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(execution.time, "perf_counter", lambda: next(perf_counter_values))
    monkeypatch.setattr(execution.time, "sleep", lambda _seconds: None)

    rc = execution.run_command(  # noqa: SLF001
        repo_root=tmp_path,
        args=("python", "-m", "odylith.runtime.surfaces.render_backlog_ui"),
        heartbeat_label="radar",
        timeout_seconds=1.0,
    )
    output = capsys.readouterr().out

    assert rc == 124
    assert process.terminated is True
    assert process.killed is False
    assert process.wait_calls == [0.5, 5]
    assert "timeout: radar exceeded 1s; terminating" in output


def test_run_command_terminates_process_group_for_timed_out_child(tmp_path: Path, monkeypatch, capsys) -> None:
    class _FakeProcess:
        def __init__(self) -> None:
            self.pid = 4321
            self.terminated = False
            self.killed = False
            self.wait_calls: list[float | None] = []

        def poll(self) -> int | None:
            return None

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, timeout: float | None = None) -> int:
            self.wait_calls.append(timeout)
            if timeout == 0.5:
                raise execution.subprocess.TimeoutExpired("renderer", timeout)
            return 0

        def kill(self) -> None:
            self.killed = True

    process = _FakeProcess()
    perf_counter_values = iter([0.0, 0.0, 1.2])
    killed_groups: list[tuple[int, int]] = []

    monkeypatch.setattr(execution.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(execution.time, "perf_counter", lambda: next(perf_counter_values))
    monkeypatch.setattr(execution.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(execution.os, "killpg", lambda pid, sig: killed_groups.append((pid, int(sig))))

    rc = execution.run_command(  # noqa: SLF001
        repo_root=tmp_path,
        args=("python", "-m", "odylith.runtime.surfaces.render_backlog_ui"),
        heartbeat_label="radar",
        timeout_seconds=1.0,
    )
    output = capsys.readouterr().out

    assert rc == 124
    assert killed_groups == [(4321, int(execution.signal.SIGTERM))]
    assert process.terminated is False
    assert process.killed is False
    assert process.wait_calls == [0.5, 5]
    assert "timeout: radar exceeded 1s; terminating" in output
