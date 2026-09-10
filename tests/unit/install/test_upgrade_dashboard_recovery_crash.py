"""SIGKILL recovery cuts use the real CLI/manager/publication with simulated rendering."""

import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import signal
import stat
import traceback

import pytest

from odylith import cli
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_repository_lock as repository_lock
from tests.unit.install.test_upgrade_dashboard_recovery import (
    RADAR, _failed_upgrade, _observed, _receipt, _successful_dashboard_renderer,
)


pytestmark = pytest.mark.skipif(not hasattr(os, "fork"), reason="SIGKILL lease proof requires POSIX fork")
_INTERRUPTED_OUTPUT = b"retry interrupted after writing incomplete dashboard bytes\n"


def _recovery_tree_state(root):
    """Include runtime evidence and empty directories, without following simulator symlinks."""
    observed = {}
    for path in (root, *sorted(root.rglob("*"))):
        metadata = path.lstat()
        content = None
        if stat.S_ISLNK(metadata.st_mode):
            content = str(path.readlink())
        elif stat.S_ISREG(metadata.st_mode):
            content = hashlib.sha256(path.read_bytes()).hexdigest()
        observed[str(path.relative_to(root))] = (metadata.st_mode, metadata.st_mtime_ns, content)
    return observed


def _kill_retry_at_barrier(sim, retry, monkeypatch, capsys, *, phase):
    root = sim.repo_root
    receipt = _receipt(root)
    old_receipt = receipt.read_bytes()
    old_publication = (root / "odylith/index.html").read_bytes()
    receiver, sender = multiprocessing.get_context("fork").Pipe(duplex=False)

    def retry_process():
        receiver.close()

        def reached():
            sender.send({"phase": phase, "pid": os.getpid()})
            while True:
                signal.pause()

        try:
            os.chdir(root)
            if phase == "partial-output":
                def interrupted_renderer(**arguments):
                    assert Path(arguments["repo_root"]).resolve() == root
                    assert arguments["force"] is True and arguments["repository_lock_fd"] is not None
                    (root / RADAR).write_bytes(_INTERRUPTED_OUTPUT)
                    reached()

                monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", interrupted_renderer)
            else:
                calls = _successful_dashboard_renderer(sim, monkeypatch)
                original_unlink = Path.unlink

                def before_receipt_removal(path, *args, **kwargs):
                    if path == receipt:
                        assert calls == ["complete-retry"]
                        assert receipt.read_bytes() == old_receipt
                        assert (root / "odylith/index.html").read_bytes() != old_publication
                        generations.require_greenfield_working_generation(root)
                        reached()
                    return original_unlink(path, *args, **kwargs)

                monkeypatch.setattr(Path, "unlink", before_receipt_removal)
            sender.send({"unexpected_return": cli.main(retry)})
        except BaseException:
            sender.send({"unexpected_error": traceback.format_exc()})
        finally:
            sender.close()

    process = multiprocessing.get_context("fork").Process(target=retry_process, daemon=True)
    process.start()
    sender.close()
    try:
        assert receiver.poll(20), "retry did not reach its exact interruption barrier"
        reached = receiver.recv()
        assert reached == {"phase": phase, "pid": process.pid}, reached
        blocked_state = _recovery_tree_state(root)
        capsys.readouterr()
        assert cli.main(retry) == 75
        output = capsys.readouterr()
        assert "BUSY_NO_WRITE" in output.err
        assert _recovery_tree_state(root) == blocked_state
        assert process.is_alive()
        process.kill()
        process.join(timeout=5)
        assert not process.is_alive() and process.exitcode == -signal.SIGKILL
        assert _recovery_tree_state(root) == blocked_state
        with repository_lock.greenfield_repository_lock(root):
            pass
        assert _recovery_tree_state(root) == blocked_state
        return {**reached, "exitcode": process.exitcode, "competing_cli_returncode": 75,
                "reaped": True, "writer_lock_reacquired": True}
    finally:
        if process.is_alive():
            process.kill()
            process.join(timeout=5)
        assert not process.is_alive(), "owned retry process survived cleanup"
        process.close()
        receiver.close()


def _assert_retry_refuses_without_writes(sim, retry, monkeypatch, capsys):
    calls = _successful_dashboard_renderer(sim, monkeypatch)
    before = _recovery_tree_state(sim.repo_root)
    capsys.readouterr()
    assert cli.main(retry) == 1
    output = capsys.readouterr()
    assert "RECOVERY_REQUIRED" in output.err
    assert calls == []
    assert _recovery_tree_state(sim.repo_root) == before


def test_killed_retry_before_receipt_renewal_refuses_changed_partial_output(
    tmp_path, monkeypatch, capsys, record_property,
):
    sim, retry, failed = _failed_upgrade(tmp_path, monkeypatch, capsys)
    root = sim.repo_root
    monkeypatch.chdir(root)
    receipt_before = _receipt(root).read_bytes()
    publication_before = (root / "odylith/index.html").read_bytes()
    predecessor = generations.pin_active_greenfield_generation(root)
    terminal = _kill_retry_at_barrier(sim, retry, monkeypatch, capsys, phase="partial-output")
    record_property("owned_process", json.dumps(terminal, sort_keys=True))
    record_property("retained_repository", str(root))

    assert (root / RADAR).read_bytes() == _INTERRUPTED_OUTPUT
    assert _receipt(root).read_bytes() == receipt_before
    assert (root / "odylith/index.html").read_bytes() == publication_before
    after = _observed(sim)
    assert after["files"] == failed["files"]
    assert after["active_runtime"] == after["pin"] == "1.2.4"
    assert after["working"] != failed["working"]
    assert generations.pin_active_greenfield_generation(root).write_set_hash == predecessor.write_set_hash

    _assert_retry_refuses_without_writes(sim, retry, monkeypatch, capsys)
    assert _receipt(root).read_bytes() == receipt_before
    assert (root / "odylith/index.html").read_bytes() == publication_before
    assert (root / RADAR).read_bytes() == _INTERRUPTED_OUTPUT


@pytest.mark.parametrize("later_change", ("owned-tree", "old-publication"))
def test_killed_retry_after_publication_keeps_valid_successor_but_no_stale_authority(
    tmp_path, monkeypatch, capsys, record_property, later_change,
):
    sim, retry, failed = _failed_upgrade(tmp_path, monkeypatch, capsys)
    root = sim.repo_root
    monkeypatch.chdir(root)
    receipt_before = _receipt(root).read_bytes()
    publication_before = (root / "odylith/index.html").read_bytes()
    terminal = _kill_retry_at_barrier(sim, retry, monkeypatch, capsys, phase="published-before-receipt-removal")
    record_property("owned_process", json.dumps(terminal, sort_keys=True))
    record_property("retained_repository", str(root))

    successor_entry = (root / "odylith/index.html").read_bytes()
    assert successor_entry != publication_before
    assert _receipt(root).read_bytes() == receipt_before
    successor = generations.require_greenfield_working_generation(root)
    rendered = (root / RADAR).read_bytes()
    assert rendered == b"<!doctype html><title>Complete refreshed Radar</title>\n"
    assert (successor.repository_root / RADAR).read_bytes() == rendered
    assert _observed(sim)["files"] == failed["files"]
    assert sim.active_runtime_name() == sim.pin().odylith_version == "1.2.4"
    record_property("successor_write_set_hash", successor.write_set_hash)

    if later_change == "owned-tree":
        (root / RADAR).write_bytes(b"Later operator edit must not acquire stale upgrade authority.\n")
    else:
        (root / "odylith/index.html").write_bytes(publication_before)
    _assert_retry_refuses_without_writes(sim, retry, monkeypatch, capsys)
    assert _receipt(root).read_bytes() == receipt_before
    assert (root / "odylith/index.html").read_bytes() == (
        successor_entry if later_change == "owned-tree" else publication_before
    )
    retained = generations.pin_greenfield_generation(repo_root=root, write_set_hash=successor.write_set_hash)
    assert retained.manifest_sha256 == successor.manifest_sha256
    assert (retained.repository_root / RADAR).read_bytes() == rendered
