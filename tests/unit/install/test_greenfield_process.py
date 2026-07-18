from __future__ import annotations

import contextlib
import importlib.util
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _module():
    return _load_module(SCRIPTS_ROOT / "greenfield_process.py", "greenfield_process")


def test_run_command_with_group_timeout_terminates_process_group(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    popen_kwargs: dict[str, object] = {}
    killed: list[tuple[int, int]] = []

    class FakeProcess:
        pid = 4242
        returncode = -15

        def __init__(self) -> None:
            self.calls = 0

        def communicate(self, timeout=None):  # noqa: ANN001
            self.calls += 1
            if self.calls == 1:
                raise module.subprocess.TimeoutExpired(
                    ["bash", "install.sh"],
                    timeout,
                    output="partial stdout",
                    stderr="partial stderr",
                )
            return "final stdout", "final stderr"

    fake_process = FakeProcess()

    def fake_popen(*_args, **kwargs):  # noqa: ANN001
        popen_kwargs.update(kwargs)
        return fake_process

    monkeypatch.setattr(module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(module.os, "killpg", lambda pid, sig: killed.append((pid, sig)))

    result = module.run_command_with_group_timeout(
        cwd=tmp_path,
        env={},
        command=["bash", "install.sh"],
        timeout=0.01,
        on_started=lambda _pid, _pgid: None,
    )

    assert result.returncode == 124
    assert popen_kwargs["start_new_session"] is True
    assert killed == [(4242, module.signal.SIGTERM)]
    assert "partial stdout" in result.stdout
    assert "partial stderr" in result.stderr
    assert "process group was terminated" in result.stderr


def test_run_command_with_group_timeout_reaps_child_when_start_callback_fails(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    killed: list[tuple[int, int]] = []

    class FakeProcess:
        pid = 4242
        returncode = -15

        def communicate(self, timeout=None):  # noqa: ANN001
            return "", ""

    monkeypatch.setattr(module.subprocess, "Popen", lambda *_args, **_kwargs: FakeProcess())
    monkeypatch.setattr(module.os, "killpg", lambda pid, sig: killed.append((pid, sig)))

    with pytest.raises(RuntimeError, match="telemetry unavailable"):
        module.run_command_with_group_timeout(
            cwd=tmp_path,
            env={},
            command=["bash", "install.sh"],
            timeout=0.01,
            on_started=lambda _pid, _pgid: (_ for _ in ()).throw(RuntimeError("telemetry unavailable")),
        )

    assert killed == [(4242, module.signal.SIGTERM)]


def test_run_command_with_group_timeout_reaps_child_when_start_callback_is_interrupted(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    killed: list[tuple[int, int]] = []

    class FakeProcess:
        pid = 4242

        def communicate(self, timeout=None):  # noqa: ANN001
            return "", ""

    monkeypatch.setattr(module.subprocess, "Popen", lambda *_args, **_kwargs: FakeProcess())
    monkeypatch.setattr(module.os, "killpg", lambda pid, sig: killed.append((pid, sig)))

    with pytest.raises(KeyboardInterrupt):
        module.run_command_with_group_timeout(
            cwd=tmp_path,
            env={},
            command=["bash", "install.sh"],
            timeout=1,
            on_started=lambda _pid, _pgid: (_ for _ in ()).throw(KeyboardInterrupt),
        )

    assert killed == [(4242, module.signal.SIGTERM)]


def test_run_command_with_group_timeout_reaps_child_when_communicate_is_interrupted(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    killed: list[tuple[int, int]] = []

    class FakeProcess:
        pid = 4242

        def communicate(self, timeout=None):  # noqa: ANN001
            if timeout == 5:
                return "", ""
            raise KeyboardInterrupt

    monkeypatch.setattr(module.subprocess, "Popen", lambda *_args, **_kwargs: FakeProcess())
    monkeypatch.setattr(module.os, "killpg", lambda pid, sig: killed.append((pid, sig)))

    with pytest.raises(KeyboardInterrupt):
        module.run_command_with_group_timeout(cwd=tmp_path, env={}, command=["bash", "install.sh"], timeout=1)

    assert killed == [(4242, module.signal.SIGTERM)]


def test_run_command_with_group_timeout_reaps_real_child_when_runner_receives_sigint(tmp_path: Path) -> None:
    child_pid_path = tmp_path / "child.pid"
    runner_script = tmp_path / "interrupted_runner.py"
    runner_script.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "sys.path.insert(0, " + repr(str(SCRIPTS_ROOT)) + ")\n"
        "from greenfield_process import run_command_with_group_timeout\n"
        "def record(pid, _pgid):\n"
        "    Path(sys.argv[1]).write_text(str(pid), encoding='utf-8')\n"
        "run_command_with_group_timeout(\n"
        "    cwd=Path.cwd(),\n"
        "    env={},\n"
        "    command=[sys.executable, '-c', 'import time; time.sleep(30)'],\n"
        "    timeout=30,\n"
        "    on_started=record,\n"
        ")\n",
        encoding="utf-8",
    )
    runner = subprocess.Popen(
        [sys.executable, str(runner_script), str(child_pid_path)],
        cwd=str(tmp_path),
        start_new_session=True,
    )
    child_pid: int | None = None
    try:
        deadline = time.monotonic() + 5
        while not child_pid_path.is_file() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert child_pid_path.is_file()
        child_pid = int(child_pid_path.read_text(encoding="utf-8"))

        os.kill(runner.pid, signal.SIGINT)
        assert runner.wait(timeout=5) != 0

        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.02)
        else:
            raise AssertionError(f"interrupted runner left installer process {child_pid} alive")
    finally:
        if runner.poll() is None:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(runner.pid, signal.SIGKILL)
        if child_pid is not None:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(child_pid, signal.SIGKILL)


@pytest.mark.parametrize("timeout", (0, -1, float("inf"), float("nan")))
def test_run_command_with_group_timeout_rejects_non_positive_or_non_finite_timeout(monkeypatch, tmp_path: Path, timeout: float) -> None:
    module = _module()
    monkeypatch.setattr(module.subprocess, "Popen", pytest.fail)

    with pytest.raises(ValueError, match="positive finite"):
        module.run_command_with_group_timeout(cwd=tmp_path, env={}, command=["bash", "install.sh"], timeout=timeout)


def test_run_command_with_group_timeout_returns_when_detached_descendant_holds_output_pipes(tmp_path: Path) -> None:
    module = _module()
    child_pid_path = tmp_path / "detached-child.pid"
    script = tmp_path / "spawn_detached_child.py"
    script.write_text(
        "from pathlib import Path\n"
        "import os\n"
        "import subprocess\n"
        "import sys\n"
        "import time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import os, time; os.setsid(); time.sleep(30)'])\n"
        "Path(os.environ['CHILD_PID_PATH']).write_text(str(child.pid), encoding='utf-8')\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["CHILD_PID_PATH"] = str(child_pid_path)
    started = time.monotonic()
    result = module.run_command_with_group_timeout(
        cwd=tmp_path,
        env=environment,
        command=[sys.executable, str(script)],
        timeout=0.1,
    )

    try:
        assert result.returncode == 124
        assert time.monotonic() - started < 8
        assert "process group was terminated" in result.stderr
        assert "escaped descendant cleanup is unverified" in result.stderr
        assert result.termination_observation == "output_pipes_still_open_after_sigkill"
        assert child_pid_path.is_file()
        os.kill(int(child_pid_path.read_text(encoding="utf-8")), 0)
    finally:
        if child_pid_path.is_file():
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(int(child_pid_path.read_text(encoding="utf-8")), signal.SIGKILL)
