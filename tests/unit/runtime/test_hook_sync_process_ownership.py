from __future__ import annotations

from contextlib import suppress
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from odylith.runtime.surfaces import host_dirty_checkpoint, host_hook_execution


pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX foreground process group contract")
_SOURCE_ROOT = Path(host_hook_execution.__file__).resolve().parents[3]


def _write_sync_fixture(tmp_path: Path, *, step_timeout: float = 30, inherited_capture: bool = True) -> Path:
    (tmp_path / "grandchild.py").write_text(
        "import json,os,signal,time\nfrom pathlib import Path\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "Path('grandchild.json').write_text(json.dumps({'pid': os.getpid(), 'pgid': os.getpgrp()}))\n"
        "time.sleep(30)\n",
    )
    (tmp_path / "renderer.py").write_text(
        "import json,os,subprocess,sys,time\nfrom pathlib import Path\n"
        "Path('renderer.json').write_text(json.dumps({'pid': os.getpid(), 'pgid': os.getpgrp()}))\n"
        "subprocess.Popen([sys.executable, 'grandchild.py']"
        + ("" if inherited_capture else ", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL")
        + ")\n"
        "while not Path('grandchild.json').exists(): time.sleep(0.005)\n"
        "time.sleep(30)\n",
    )
    sync = tmp_path / "sync.py"
    sync.write_text(
        "import json,os,sys\nfrom pathlib import Path\n"
        f"sys.path.insert(0, {str(_SOURCE_ROOT)!r})\n"
        "from odylith.runtime.governance import sync_workstream_artifacts as sync\n"
        "Path('sync.json').write_text(json.dumps({'pid': os.getpid(), 'pgid': os.getpgrp()}))\n"
        "rc = sync._run_command(repo_root=Path.cwd(), args=[sys.executable, 'renderer.py'], "
        f"heartbeat_label='controlled-render', timeout_seconds={step_timeout!r})\n"
        "Path('step-result').write_text(str(rc))\n"
        "raise SystemExit(rc)\n",
    )
    return sync


def _fixture_processes(tmp_path: Path) -> list[dict[str, int]]:
    return [json.loads((tmp_path / name).read_text()) for name in ("sync.json", "renderer.json", "grandchild.json")]


def _running(pid: int) -> bool:
    result = subprocess.run(["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True, timeout=1)
    return bool(result.stdout.strip()) and not result.stdout.lstrip().startswith("Z")


def _assert_stopped(processes: list[dict[str, int]]) -> None:
    deadline = time.monotonic() + 1
    while any(_running(row["pid"]) for row in processes) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not any(_running(row["pid"]) for row in processes)


def _cleanup_fixture_processes(tmp_path: Path) -> None:
    for name in ("sync.json", "renderer.json", "grandchild.json"):
        if (tmp_path / name).exists():
            pid = json.loads((tmp_path / name).read_text())["pid"]
            assert pid != os.getpid()
            if _running(pid):
                with suppress(ProcessLookupError):
                    os.kill(pid, signal.SIGKILL)


def test_stop_expiry_owns_real_sync_renderer_and_grandchild(tmp_path: Path) -> None:
    sync = _write_sync_fixture(tmp_path)
    sibling = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)
    try:
        with pytest.raises(host_hook_execution.HookBudgetExpired):
            with host_hook_execution.hook_budget(seconds=1.5):
                host_hook_execution.run_hook_command(command=[sys.executable, str(sync)], cwd=tmp_path, timeout=20)
        processes = _fixture_processes(tmp_path)
        assert {row["pgid"] for row in processes} == {processes[0]["pid"]}
        _assert_stopped(processes)
        assert sibling.poll() is None
    finally:
        _cleanup_fixture_processes(tmp_path)
        sibling.kill()
        sibling.wait(timeout=1)


def test_manual_sync_keeps_its_separate_renderer_group(tmp_path: Path) -> None:
    sync = _write_sync_fixture(tmp_path)
    try:
        assert host_hook_execution.run_hook_command(command=[sys.executable, str(sync)], cwd=tmp_path, timeout=1.5) is None
        processes = _fixture_processes(tmp_path)
        assert processes[1]["pgid"] == processes[1]["pid"]
        assert processes[1]["pgid"] != processes[0]["pgid"]
        assert processes[2]["pgid"] == processes[1]["pgid"]
    finally:
        _cleanup_fixture_processes(tmp_path)


@pytest.mark.parametrize("inherited_capture", [True, False])
def test_short_sync_step_failure_is_cleaned_by_outer_hook_owner(tmp_path: Path, inherited_capture: bool) -> None:
    sync = _write_sync_fixture(tmp_path, step_timeout=0.2, inherited_capture=inherited_capture)
    try:
        if inherited_capture:
            with pytest.raises(host_hook_execution.HookBudgetExpired):
                with host_hook_execution.hook_budget(seconds=2):
                    host_hook_execution.run_hook_command(command=[sys.executable, str(sync)], cwd=tmp_path, timeout=20)
        else:
            with host_hook_execution.hook_budget(seconds=2):
                result = host_hook_execution.run_hook_command(command=[sys.executable, str(sync)], cwd=tmp_path, timeout=20)
            assert result is not None and result.returncode == 124
        assert (tmp_path / "step-result").read_text() == "124"
        processes = _fixture_processes(tmp_path)
        assert len({row["pgid"] for row in processes}) == 1
        _assert_stopped(processes)
    finally:
        _cleanup_fixture_processes(tmp_path)


def test_exact_controlled_stop_command_finishes_inside_native_timeout(tmp_path: Path) -> None:
    _write_sync_fixture(tmp_path)
    launcher = tmp_path / ".odylith/bin/odylith"
    launcher.parent.mkdir(parents=True)
    launcher.write_text(
        f"#!{sys.executable}\n"
        "import runpy,sys\nfrom pathlib import Path\n"
        f"sys.path.insert(0, {str(_SOURCE_ROOT)!r})\n"
        "if sys.argv[1:3] == ['codex', 'stop-summary']:\n"
        "    from odylith.runtime.surfaces.codex_host_stop_summary import main\n"
        "    raise SystemExit(main(sys.argv[3:]))\n"
        "if sys.argv[1] == 'sync':\n"
        "    runpy.run_path('sync.py', run_name='__main__')\n",
    )
    launcher.chmod(0o755)
    event_id = host_dirty_checkpoint.record_dirty_event(
        repo_root=tmp_path, host_family="codex", session_id="command-proof", source="test",
        governed_paths=["odylith/casebook/bugs/example.md"],
    )
    command = [str(launcher), "codex", "stop-summary", "--repo-root", str(tmp_path)]
    started = time.monotonic()
    process = subprocess.Popen(
        command, cwd=tmp_path, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(
            input=json.dumps({"session_id": "command-proof", "last_assistant_message": "Completed the requested changes."}),
            timeout=20,
        )
        elapsed = time.monotonic() - started
        assert process.returncode == 0, stderr
        assert 14 <= elapsed < 20
        payload = json.loads(stdout)
        assert "queued" in payload["systemMessage"]
        assert "decision" not in payload
        assert [row["id"] for row in host_dirty_checkpoint.read_dirty_events(repo_root=tmp_path)] == [event_id]
        processes = _fixture_processes(tmp_path)
        assert len({row["pgid"] for row in processes}) == 1
        _assert_stopped(processes)
        print(f"Controlled exact hook command: {command!r}; elapsed={elapsed:.3f}s; returncode=0")
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=1)
        _cleanup_fixture_processes(tmp_path)
