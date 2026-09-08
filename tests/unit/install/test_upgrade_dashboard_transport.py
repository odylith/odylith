"""Real process/descriptor transport controls, not installed-wheel renderer proof."""

from contextlib import suppress
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
import time

import pytest

from odylith.install import upgrade_dashboard
from odylith.runtime.domain_intelligence import greenfield_generation_state as publications
from odylith.runtime.domain_intelligence import greenfield_repository_lock as locks
from odylith.runtime.governance import sync_workstream_artifacts as sync
from tests.unit.runtime.greenfield_baseline_fixtures import activate_greenfield_baseline_fixture


_SOURCE_ROOT = Path(__file__).resolve().parents[3] / "src"
_LEAF_DRIVER = r'''
import json, os, sys
from pathlib import Path
root, fd = Path(sys.argv[1]), int(sys.argv[2])
(root / "leaf-observation.json").write_text(json.dumps({"pid": os.getpid(), "lock_inode": os.fstat(fd).st_ino}))
(root / "leaf-ready").touch()
with (root / "worker-gate").open("rb") as gate:
    assert gate.read(1) == b"x"
(root / "odylith/radar/radar.html").write_text("<!doctype html><title>Leaf renderer output</title>\n")
os.close(fd)
(root / "leaf-finished").touch()
'''
_TARGET_DRIVER = r'''
import json, os, sys
from pathlib import Path
sys.path.insert(0, SOURCE_ROOT)
from odylith import cli
from odylith.runtime.governance import sync_workstream_artifacts as sync

root = Path(sys.argv[sys.argv.index("--repo-root") + 1])
config = json.loads((root / "transport-config.json").read_text())

def target_renderer(**kwargs):
    fd = kwargs["repository_lock_fd"]
    observed = {
        "marker": "target-renderer-executed", "pid": os.getpid(),
        "argv": sys.argv[1:], "fd": fd,
        "repo_root": str(kwargs["repo_root"]),
        "surfaces": list(kwargs["surfaces"]),
        "runtime_mode": kwargs["runtime_mode"],
        "atlas_sync": kwargs["atlas_sync"], "force": kwargs["force"],
        "completion_result": kwargs["on_completed"](),
        "lock_inode": os.fstat(fd).st_ino,
    }
    extra = config.get("unrelated_fd")
    observed["unrelated_inherited"] = False
    if extra is not None:
        try:
            info = os.fstat(extra)
            observed["unrelated_inherited"] = (info.st_dev, info.st_ino) == tuple(config["unrelated_identity"])
        except OSError:
            pass
    (root / "target-observation.json").write_text(json.dumps(observed))
    (root / "worker-ready").touch()
    if config.get("leaf"):
        return sync._run_command(
            repo_root=root,
            args=[sys.executable, "-B", "-c", LEAF_SOURCE, str(root), str(fd)],
            pass_fds=(fd,),
            timeout_seconds=30 if config["leaf"] == "popen" else None,
        )
    if config["blocked"]:
        with (root / "worker-gate").open("rb") as gate:
            assert gate.read(1) == b"x"
    output = root / "odylith/radar/radar.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("<!doctype html><title>Target renderer output</title>\n")
    if config["result"] == "exception":
        raise OSError("target-renderer-exception")
    if not config["blocked"]:
        print("target renderer stdout")
        print("target renderer stderr", file=sys.stderr)
    (root / "worker-finished").touch()
    return config["result"]

sync.refresh_dashboard_surfaces = target_renderer
raise SystemExit(cli.main(sys.argv[1:]))
'''
_PARENT_DRIVER = r'''
import json, sys, threading, time
from pathlib import Path
sys.path.insert(0, SOURCE_ROOT)
from odylith.install.upgrade_dashboard import run_dashboard_renderer
from odylith.runtime.domain_intelligence.greenfield_repository_lock import greenfield_repository_lock
root, mode = Path(sys.argv[1]), sys.argv[2]
result = []
def render(fd):
    result.append(run_dashboard_renderer(repo_root=root, repository_lock_fd=fd))
with greenfield_repository_lock(root) as fd:
    if mode == "close":
        worker = threading.Thread(target=render, args=(fd,))
        worker.start()
        deadline = time.monotonic() + 10
        while not (root / "worker-ready").exists():
            if time.monotonic() > deadline:
                raise RuntimeError("worker did not reach controlled render")
            time.sleep(.01)
    else:
        render(fd)
(root / "parent-closed").touch()
if mode == "close":
    worker.join(timeout=10)
    assert not worker.is_alive()
assert len(result) == 1 and result[0].returncode == 0, result
'''
_CONTENDER = r'''
import sys
from pathlib import Path
sys.path.insert(0, SOURCE_ROOT)
from odylith.runtime.domain_intelligence.greenfield_repository_lock import greenfield_repository_lock, GreenfieldRepositoryBusyError
try:
    with greenfield_repository_lock(Path(sys.argv[1])):
        pass
except GreenfieldRepositoryBusyError:
    raise SystemExit(75)
'''


@pytest.fixture(name="tmp_path")
def _owned_transport_root():
    with tempfile.TemporaryDirectory(prefix="odylith-upgrade-transport-") as root:
        yield Path(root).resolve()


def _script(source):
    return source.replace("SOURCE_ROOT", repr(str(_SOURCE_ROOT))).replace("LEAF_SOURCE", repr(_LEAF_DRIVER))


def _prepare_target(root, *, activated=False, result=0, blocked=False):
    if activated:
        activate_greenfield_baseline_fixture(root)
    else:
        shell = root / "odylith/index.html"
        shell.parent.mkdir(parents=True, exist_ok=True)
        shell.write_text("<!doctype html><title>Legacy live shell</title>\n")
    (root / "transport-config.json").write_text(json.dumps({"result": result, "blocked": blocked}))
    driver = root / "target-driver.py"
    driver.write_text(_script(_TARGET_DRIVER))
    launcher = root / ".odylith/bin/odylith"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} -B {shlex.quote(str(driver))} \"$@\"\n")
    launcher.chmod(0o755)
    if blocked:
        os.mkfifo(root / "worker-gate")


def _contender(root):
    completed = subprocess.run(
        [sys.executable, "-B", "-c", _script(_CONTENDER), str(root)],
        capture_output=True, text=True, timeout=10, check=False,
    )
    assert completed.stderr == "", completed.stderr
    return completed.returncode


def _wait_for(path, parent=None):
    deadline = time.monotonic() + 10
    while not path.exists():
        if parent is not None and parent.poll() is not None:
            stdout, stderr = parent.communicate(timeout=2)
            pytest.fail(f"parent ended before {path.name}: {parent.returncode}; {stdout}; {stderr}")
        assert time.monotonic() < deadline, f"Timed out waiting for {path}"
        time.sleep(.01)


def _wait_for_process_death(pid):
    # Orphaned worker descendants cannot be reaped by this test process.
    deadline = time.monotonic() + 10
    while True:
        observed = subprocess.run(
            ["ps", "-p", str(pid), "-o", "stat="],
            capture_output=True, text=True, timeout=2, check=False,
        )
        assert observed.returncode in {0, 1} and not observed.stderr, observed
        state = observed.stdout.strip()
        if not state or state.startswith("Z"):
            return
        assert time.monotonic() < deadline, f"Owned process {pid} remains live: {state}"
        time.sleep(.01)


def _release_worker(root):
    deadline = time.monotonic() + 5
    while True:
        try:
            descriptor = os.open(root / "worker-gate", os.O_WRONLY | os.O_NONBLOCK)
            break
        except OSError:
            assert time.monotonic() < deadline, "Worker did not open its controlled gate"
            time.sleep(.01)
    try:
        os.write(descriptor, b"x")
    finally:
        os.close(descriptor)


@pytest.mark.parametrize("activated", (False, True))
@pytest.mark.parametrize("result", (0, 2, "exception"))
def test_real_target_launcher_renders_without_publication_and_preserves_parent_lock(tmp_path, activated, result):
    _prepare_target(tmp_path, activated=activated, result=result)
    entry = tmp_path / "odylith/index.html"
    before_entry = entry.read_bytes()
    before_publication = publications.read_active_publication(tmp_path)
    unrelated = (tmp_path / "unrelated-descriptor").open("a+b")
    try:
        os.set_inheritable(unrelated.fileno(), True)
        identity = os.fstat(unrelated.fileno())
        config = json.loads((tmp_path / "transport-config.json").read_text())
        config.update(unrelated_fd=unrelated.fileno(), unrelated_identity=[identity.st_dev, identity.st_ino])
        (tmp_path / "transport-config.json").write_text(json.dumps(config))
        with locks.greenfield_repository_lock(tmp_path) as descriptor:
            completed = upgrade_dashboard.run_dashboard_renderer(repo_root=tmp_path, repository_lock_fd=descriptor)
            assert completed.returncode == (1 if result == "exception" else result), completed.stderr
            observation = json.loads((tmp_path / "target-observation.json").read_text())
            assert observation == {
                "marker": "target-renderer-executed", "pid": observation["pid"],
                "argv": ["_upgrade-dashboard-render", "--repo-root", str(tmp_path), "--lock-fd", str(descriptor)],
                "fd": descriptor, "repo_root": str(tmp_path),
                "surfaces": ["tooling_shell", "radar", "compass"],
                "runtime_mode": "auto", "atlas_sync": False, "force": True,
                "completion_result": 0, "lock_inode": os.fstat(descriptor).st_ino,
                "unrelated_inherited": False,
            }
            assert observation["pid"] != os.getpid()
            assert entry.read_bytes() == before_entry
            assert publications.read_active_publication(tmp_path) == before_publication
            assert _contender(tmp_path) == 75
        assert _contender(tmp_path) == 0
        if result == "exception":
            assert "target-renderer-exception" in completed.stderr
        else:
            assert completed.stdout == "target renderer stdout\n"
            assert completed.stderr == "target renderer stderr\n"
    finally:
        unrelated.close()


@pytest.mark.parametrize("mode", ("kill", "close"))
@pytest.mark.parametrize("activated", (False, True))
def test_render_child_keeps_real_lock_after_parent_death_or_close(tmp_path, mode, activated):
    _prepare_target(tmp_path, activated=activated, blocked=True)
    entry = tmp_path / "odylith/index.html"
    before_entry = entry.read_bytes()
    before_publication = publications.read_active_publication(tmp_path)
    parent = subprocess.Popen(
        [sys.executable, "-B", "-c", _script(_PARENT_DRIVER), str(tmp_path), mode],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
    )
    try:
        _wait_for(tmp_path / "worker-ready", parent)
        assert _contender(tmp_path) == 75
        if mode == "kill":
            parent.kill()
            assert parent.wait(timeout=5) == -signal.SIGKILL
        else:
            _wait_for(tmp_path / "parent-closed", parent)
        assert _contender(tmp_path) == 75
        assert entry.read_bytes() == before_entry
        _release_worker(tmp_path)
        _wait_for(tmp_path / "worker-finished")
        deadline = time.monotonic() + 10
        while _contender(tmp_path) == 75:
            assert time.monotonic() < deadline, "Worker retained lock after completion"
        stdout, stderr = parent.communicate(timeout=5)
        assert stdout == stderr == ""
        assert parent.returncode == (-signal.SIGKILL if mode == "kill" else 0)
        worker_pid = json.loads((tmp_path / "target-observation.json").read_text())["pid"]
        _wait_for_process_death(worker_pid)
        assert publications.read_active_publication(tmp_path) == before_publication
        assert entry.read_bytes() == before_entry
    finally:
        with suppress(ProcessLookupError):
            os.killpg(parent.pid, signal.SIGKILL)
        parent.wait(timeout=5)
        if parent.stdout:
            parent.stdout.close()
        if parent.stderr:
            parent.stderr.close()


@pytest.mark.parametrize("execution", ("run", "popen"))
@pytest.mark.parametrize("activated", (False, True))
def test_production_render_leaf_keeps_lock_after_parent_and_worker_death(tmp_path, execution, activated):
    _prepare_target(tmp_path, activated=activated, blocked=True)
    (tmp_path / "odylith/radar").mkdir(parents=True, exist_ok=True)
    config = json.loads((tmp_path / "transport-config.json").read_text())
    config["leaf"] = execution
    (tmp_path / "transport-config.json").write_text(json.dumps(config))
    entry = tmp_path / "odylith/index.html"
    before_entry = entry.read_bytes()
    before_publication = publications.read_active_publication(tmp_path)
    parent = subprocess.Popen(
        [sys.executable, "-B", "-c", _script(_PARENT_DRIVER), str(tmp_path), "kill"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
    )
    leaf_pid = None
    try:
        _wait_for(tmp_path / "leaf-ready", parent)
        worker = json.loads((tmp_path / "target-observation.json").read_text())
        leaf = json.loads((tmp_path / "leaf-observation.json").read_text())
        leaf_pid = leaf["pid"]
        assert leaf_pid != worker["pid"] != parent.pid
        assert leaf["lock_inode"] == worker["lock_inode"]
        assert _contender(tmp_path) == 75
        parent.kill()
        assert parent.wait(timeout=5) == -signal.SIGKILL
        os.kill(worker["pid"], signal.SIGKILL)
        _wait_for_process_death(worker["pid"])
        assert _contender(tmp_path) == 75
        assert entry.read_bytes() == before_entry
        _release_worker(tmp_path)
        _wait_for(tmp_path / "leaf-finished")
        deadline = time.monotonic() + 10
        while _contender(tmp_path) == 75:
            assert time.monotonic() < deadline, "Leaf retained lock after controlled completion"
        stdout, stderr = parent.communicate(timeout=5)
        assert stdout == stderr == ""
        _wait_for_process_death(leaf_pid)
        assert publications.read_active_publication(tmp_path) == before_publication
        assert entry.read_bytes() == before_entry
        assert "Leaf renderer output" in (tmp_path / "odylith/radar/radar.html").read_text()
    finally:
        if leaf_pid is not None:
            with suppress(ProcessLookupError):
                os.kill(leaf_pid, signal.SIGKILL)
        with suppress(ProcessLookupError):
            os.killpg(parent.pid, signal.SIGKILL)
        parent.wait(timeout=5)
        if parent.stdout:
            parent.stdout.close()
        if parent.stderr:
            parent.stderr.close()


@pytest.mark.parametrize("invalid", ("closed", "pipe", "wrong_repo", "read_only", "replaced", "symlink"))
def test_worker_refuses_invalid_descriptors_before_renderer(tmp_path, monkeypatch, invalid):
    monkeypatch.setattr(sync, "refresh_dashboard_surfaces", lambda **_: pytest.fail("invalid descriptor reached renderer"))
    root = tmp_path / "repo"
    lock_path = root / ".odylith/runtime/greenfield/create.lock"
    lock_path.parent.mkdir(parents=True)
    lock_path.touch()
    descriptor = os.open(lock_path, os.O_RDWR)
    extra = None
    try:
        if invalid == "closed":
            os.close(descriptor)
            descriptor = -1
        elif invalid == "pipe":
            os.close(descriptor)
            extra, descriptor = os.pipe()
        elif invalid == "wrong_repo":
            os.close(descriptor)
            descriptor = os.open(tmp_path / "another-lock", os.O_RDWR | os.O_CREAT, 0o600)
        elif invalid == "read_only":
            os.close(descriptor)
            descriptor = os.open(lock_path, os.O_RDONLY)
        elif invalid == "replaced":
            lock_path.rename(lock_path.with_suffix(".old"))
            lock_path.touch()
        elif invalid == "symlink":
            lock_path.rename(lock_path.with_suffix(".old"))
            lock_path.symlink_to(lock_path.with_suffix(".old"))
        assert upgrade_dashboard.worker_main(["--repo-root", str(root), "--lock-fd", str(descriptor)]) == 1
    finally:
        for candidate in (descriptor, extra):
            if candidate is not None:
                with suppress(OSError):
                    os.close(candidate)


def test_independently_opened_descriptor_cannot_borrow_another_description_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(sync, "refresh_dashboard_surfaces", lambda **_: pytest.fail("competing descriptor reached renderer"))
    with locks.greenfield_repository_lock(tmp_path):
        fresh = os.open(tmp_path / ".odylith/runtime/greenfield/create.lock", os.O_RDWR)
        try:
            assert upgrade_dashboard.worker_main(["--repo-root", str(tmp_path), "--lock-fd", str(fresh)]) == 75
            assert _contender(tmp_path) == 75
        finally:
            with suppress(OSError):
                os.close(fresh)


def test_borrowed_context_closes_only_its_descriptor(tmp_path):
    with locks.greenfield_repository_lock(tmp_path) as descriptor:
        borrowed = os.dup(descriptor)
        with locks.inherited_greenfield_repository_lock(tmp_path, borrowed) as received:
            assert received == borrowed
        with pytest.raises(OSError):
            os.fstat(borrowed)
        os.fstat(descriptor)
        assert _contender(tmp_path) == 75
    assert _contender(tmp_path) == 0


@pytest.mark.parametrize("flag", ("--skip-admission", "--command", "--module"))
def test_worker_does_not_accept_generic_dispatch_or_admission_bypass(tmp_path, flag):
    with pytest.raises(SystemExit) as outcome:
        upgrade_dashboard.worker_main(["--repo-root", str(tmp_path), "--lock-fd", "-1", flag, "anything"])
    assert outcome.value.code == 2
