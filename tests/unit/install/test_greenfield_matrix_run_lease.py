from __future__ import annotations

import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _module():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    spec = importlib.util.spec_from_file_location(
        "greenfield_matrix_run_lease_test",
        SCRIPTS_ROOT / "greenfield_matrix_run_lease.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_lease_owns_a_private_namespace_and_releases_its_output_lock(tmp_path: Path) -> None:
    module = _module()
    output_path = tmp_path / "proof.json"

    lease = module.acquire_matrix_run_lease(temp_parent=tmp_path, output_path=output_path)

    assert lease.temp_namespace.parent == tmp_path
    assert lease.temp_namespace.is_dir()
    assert lease.lock_path is not None and lease.lock_path.is_file()
    assert json.loads(lease.lock_path.read_text(encoding="utf-8")) == {
        "pid": os.getpid(),
        "run_id": lease.run_id,
        "state": "active",
    }
    assert lease.to_dict()["output_path"] == str(output_path)

    lease.release()

    assert not lease.temp_namespace.exists()
    assert lease.lock_path is not None and not lease.lock_path.exists()


def test_lease_rejects_concurrent_output_ownership_and_cleans_the_loser_namespace(tmp_path: Path) -> None:
    module = _module()
    output_path = tmp_path / "proof.json"
    first = module.acquire_matrix_run_lease(temp_parent=tmp_path, output_path=output_path)

    with pytest.raises(RuntimeError, match="already owned"):
        module.acquire_matrix_run_lease(temp_parent=tmp_path, output_path=output_path)

    assert [path.name for path in tmp_path.iterdir() if path.name.startswith("odylith-greenfield-proof-run-")] == [
        first.temp_namespace.name
    ]
    first.release()


def test_lease_blocks_a_dead_pid_bound_output_lock_until_explicit_recovery(tmp_path: Path) -> None:
    module = _module()
    output_path = tmp_path / "proof.json"
    lock_path = tmp_path / ".proof.json.lock"
    lock_path.write_text(
        '{"pid": 99999999, "run_id": "abandoned", "state": "active"}\n',
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="blocked by an incomplete prior run"):
        module.acquire_matrix_run_lease(temp_parent=tmp_path, output_path=output_path)

    assert json.loads(lock_path.read_text(encoding="utf-8"))["run_id"] == "abandoned"


def test_lease_preserves_an_unrecognized_output_lock(tmp_path: Path) -> None:
    module = _module()
    output_path = tmp_path / "proof.json"
    lock_path = tmp_path / ".proof.json.lock"
    lock_path.write_text("legacy-lock-without-pid\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="already owned"):
        module.acquire_matrix_run_lease(temp_parent=tmp_path, output_path=output_path)

    assert lock_path.read_text(encoding="utf-8") == "legacy-lock-without-pid\n"


def test_successful_release_closes_the_lock_before_removing_its_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    output_path = tmp_path / "proof.json"
    lease = module.acquire_matrix_run_lease(temp_parent=tmp_path, output_path=output_path)
    assert lease.lock_path is not None
    original_close = module._unlock_and_close
    observed: dict[str, bool] = {}

    def record_then_close(descriptor: int | None) -> None:
        observed["lock_path_exists_at_close"] = lease.lock_path is not None and lease.lock_path.exists()
        original_close(descriptor)

    monkeypatch.setattr(module, "_unlock_and_close", record_then_close)

    lease.release()

    assert observed == {"lock_path_exists_at_close": True}
    assert not lease.lock_path.exists()


def test_successful_release_surfaces_lock_removal_failure_and_keeps_the_lease_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    output_path = tmp_path / "proof.json"
    lease = module.acquire_matrix_run_lease(temp_parent=tmp_path, output_path=output_path)
    assert lease.lock_path is not None
    original_unlink = Path.unlink

    def reject_lock_removal(path: Path, *args: object, **kwargs: object) -> None:
        if path == lease.lock_path:
            raise OSError("injected lock removal failure")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", reject_lock_removal)
    with pytest.raises(OSError, match="injected lock removal failure"):
        lease.release()
    monkeypatch.undo()

    assert not lease.temp_namespace.exists()
    assert lease.lock_path.exists()
    with pytest.raises(RuntimeError, match="already owned"):
        module.acquire_matrix_run_lease(temp_parent=tmp_path, output_path=output_path)
    lease.lock_path.unlink()


def test_cleanup_failure_keeps_the_output_lease_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    output_path = tmp_path / "proof.json"
    lease = module.acquire_matrix_run_lease(temp_parent=tmp_path, output_path=output_path)
    assert lease.lock_path is not None

    monkeypatch.setattr(module, "_cleanup_smoke_temp_root", lambda _: None)
    with pytest.raises(RuntimeError, match="was not removed"):
        lease.release()
    monkeypatch.undo()

    assert lease.temp_namespace.exists()
    assert lease.lock_path.exists()
    with pytest.raises(RuntimeError, match="blocked by unresolved cleanup failure"):
        module.acquire_matrix_run_lease(temp_parent=tmp_path, output_path=output_path)

    shutil.rmtree(lease.temp_namespace)
    lease.lock_path.unlink()


def test_cleanup_failure_blocks_a_new_process_from_reclaiming_the_output_lease(tmp_path: Path) -> None:
    module = _module()
    output_path = tmp_path / "proof.json"
    child_program = f"""
from pathlib import Path
import greenfield_matrix_run_lease as lease_module
lease_module._cleanup_smoke_temp_root = lambda _: None
lease = lease_module.acquire_matrix_run_lease(
    temp_parent=Path({str(tmp_path)!r}),
    output_path=Path({str(output_path)!r}),
)
try:
    lease.release()
except RuntimeError:
    raise SystemExit(9)
raise SystemExit(0)
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SCRIPTS_ROOT)

    result = subprocess.run(
        [sys.executable, "-c", child_program],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 9, result.stderr
    with pytest.raises(RuntimeError, match="blocked by unresolved cleanup failure"):
        module.acquire_matrix_run_lease(temp_parent=tmp_path, output_path=output_path)

    for namespace in tmp_path.glob("odylith-greenfield-proof-run-*"):
        shutil.rmtree(namespace)
    (tmp_path / ".proof.json.lock").unlink()


def test_hard_killed_lease_blocks_a_new_process_from_reclaiming_the_output_lease(tmp_path: Path) -> None:
    module = _module()
    output_path = tmp_path / "proof.json"
    child_program = f"""
import os
import signal
from pathlib import Path
import greenfield_matrix_run_lease as lease_module
lease = lease_module.acquire_matrix_run_lease(
    temp_parent=Path({str(tmp_path)!r}),
    output_path=Path({str(output_path)!r}),
)
os.kill(os.getpid(), signal.SIGKILL)
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SCRIPTS_ROOT)

    result = subprocess.run(
        [sys.executable, "-c", child_program],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == -signal.SIGKILL
    with pytest.raises(RuntimeError, match="blocked by an incomplete prior run"):
        module.acquire_matrix_run_lease(temp_parent=tmp_path, output_path=output_path)

    for namespace in tmp_path.glob("odylith-greenfield-proof-run-*"):
        shutil.rmtree(namespace)
    (tmp_path / ".proof.json.lock").unlink()


def test_payload_writer_replaces_complete_json_atomically(tmp_path: Path) -> None:
    module = _module()
    output_path = tmp_path / "proof.json"
    output_path.write_text('{"old": true}\n', encoding="utf-8")

    module.write_matrix_payload(output_path=output_path, payload={"status": "passed"})

    assert json.loads(output_path.read_text(encoding="utf-8")) == {"status": "passed"}
    assert not list(tmp_path.glob(".proof.json.*.tmp"))
