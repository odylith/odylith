"""An exact failed-upgrade completion may resume without replaying installation."""

import hashlib
from pathlib import Path
import shlex
import shutil
import subprocess

import pytest

from odylith import cli
from odylith.install import manager
from odylith.install import upgrade_dashboard_recovery as recovery
from odylith.install.state import version_pin_path
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as write_set
from odylith.runtime.domain_intelligence import greenfield_repository_lock as repository_lock
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal
from tests.integration.install.simulator import InstallLifecycleSimulator
from tests.integration.install.test_manager import _write_runtime_bundle_assets


ASSET_PATHS = (
    "odylith/agents-guidelines/UPGRADE_AND_RECOVERY.md",
    "odylith/skills/odylith-show-me/SKILL.md",
    ".agents/skills/odylith-show-me/SKILL.md",
    ".claude/skills/odylith-show-me/SKILL.md",
)
OPERATOR_PATHS = ("odylith/radar/source/operator-note.md", "notes/operator-note.md")
RADAR = "odylith/radar/radar.html"


def _installed(tmp_path, monkeypatch):
    sim = InstallLifecycleSimulator(tmp_path=tmp_path, monkeypatch=monkeypatch)
    sim.register_release("1.2.4")
    stage_runtime = manager.install_release_runtime

    def stage_with_versioned_assets(**arguments):
        staged = stage_runtime(**arguments)
        _write_runtime_bundle_assets(staged.root, marker=f"managed-assets-{staged.version}")
        return staged

    monkeypatch.setattr(manager, "install_release_runtime", stage_with_versioned_assets)
    for relative in OPERATOR_PATHS:
        path = sim.repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"Operator-owned intent: preserve these exact bytes.\n")
    assert sim.install("1.2.3") == 0
    generations.require_greenfield_working_generation(sim.repo_root)
    return sim


def _observed(sim):
    root = sim.repo_root
    paths = (*OPERATOR_PATHS, *ASSET_PATHS, "odylith/runtime/source/product-version.v1.json", ".odylith/bin/odylith")
    return {
        "active_runtime": sim.active_runtime_name(),
        "pin": sim.pin().odylith_version,
        "publication_sha256": hashlib.sha256((root / "odylith/index.html").read_bytes()).hexdigest(),
        "working": write_set.greenfield_managed_fingerprints(root),
        "files": {relative: hashlib.sha256((root / relative).read_bytes()).hexdigest() for relative in paths},
    }


def _failed_upgrade(tmp_path, monkeypatch, capsys):
    sim = _installed(tmp_path, monkeypatch)
    root = sim.repo_root
    before = _observed(sim)
    capsys.readouterr()
    render_calls = []

    def failed_render(*, repo_root, repository_lock_fd):
        assert repo_root == root and repository_lock_fd is not None
        assert sim.active_runtime_name() == sim.pin().odylith_version == "1.2.4"
        render_calls.append("failed-upgrade")
        (root / RADAR).write_bytes(b"partial new dashboard\n")
        return subprocess.CompletedProcess(["fixture-renderer"], 2, "dashboard incomplete\n", "compass failed\n")

    monkeypatch.setattr(cli.upgrade_dashboard, "run_dashboard_renderer", failed_render)
    assert sim.upgrade_to("1.2.4", write_pin=True) != 0
    output = capsys.readouterr()
    after = _observed(sim)
    assert render_calls == ["failed-upgrade"]
    assert after["active_runtime"] == after["pin"] == "1.2.4"
    assert before["publication_sha256"] == after["publication_sha256"]
    assert before["working"] != after["working"]
    for relative in OPERATOR_PATHS:
        assert before["files"][relative] == after["files"][relative]
    for relative in ASSET_PATHS:
        assert (root / relative).read_bytes() == b"managed-assets-1.2.4\n"
    assert (root / RADAR).read_bytes() == b"partial new dashboard\n"
    emitted = output.out.split("Retry with `", 1)[1].split("`", 1)[0]
    tokens = shlex.split(emitted)
    assert tokens == ["./.odylith/bin/odylith", "dashboard", "refresh", "--repo-root", ".", "--force"]
    return sim, tokens[1:], after


def _successful_dashboard_renderer(sim, monkeypatch):
    calls = []

    def refresh(**arguments):
        assert Path(arguments["repo_root"]).resolve() == sim.repo_root
        assert arguments["force"] is True
        assert arguments["repository_lock_fd"] is not None
        calls.append("complete-retry")
        (sim.repo_root / RADAR).write_bytes(b"<!doctype html><title>Complete refreshed Radar</title>\n")
        completed = arguments.get("on_completed")
        return completed() if completed is not None else 0

    monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", refresh)
    return calls


def test_failed_upgrade_advertised_retry_keeps_target_and_publishes_complete_successor(
    tmp_path, monkeypatch, capsys,
):
    sim, retry, failed = _failed_upgrade(tmp_path, monkeypatch, capsys)
    calls = _successful_dashboard_renderer(sim, monkeypatch)
    monkeypatch.chdir(sim.repo_root)
    result = cli.main(retry)
    output = capsys.readouterr()
    after = _observed(sim)
    assert result == 0, (output.out, output.err)
    assert calls == ["complete-retry"]
    assert after["active_runtime"] == after["pin"] == "1.2.4"
    assert after["publication_sha256"] != failed["publication_sha256"]
    assert after["files"] == failed["files"]
    pinned = generations.require_greenfield_working_generation(sim.repo_root)
    assert (pinned.repository_root / RADAR).read_bytes() == (sim.repo_root / RADAR).read_bytes()


@pytest.mark.parametrize("changed_path", (OPERATOR_PATHS[0], "odylith/runtime/source/product-version.v1.json", ".odylith/bin/odylith"))
def test_failed_upgrade_retry_refuses_changed_source_pin_or_launcher(
    tmp_path, monkeypatch, capsys, changed_path,
):
    sim, retry, failed = _failed_upgrade(tmp_path, monkeypatch, capsys)
    changed = sim.repo_root / changed_path
    if changed == version_pin_path(repo_root=sim.repo_root):
        sim.write_pin("1.2.5")
    else:
        changed.write_bytes(changed.read_bytes() + b"\nOperator edit after failed upgrade.\n")
    expected = changed.read_bytes()
    before_retry = _observed(sim)
    calls = _successful_dashboard_renderer(sim, monkeypatch)
    monkeypatch.chdir(sim.repo_root)
    result = cli.main(retry)
    output = capsys.readouterr()
    assert result != 0, (output.out, output.err)
    assert calls == []
    assert changed.read_bytes() == expected
    assert _observed(sim) == before_retry
    assert _observed(sim)["publication_sha256"] == failed["publication_sha256"]


def test_ordinary_force_refresh_cannot_admit_partial_tree_without_failed_upgrade(
    tmp_path, monkeypatch, capsys,
):
    sim = _installed(tmp_path, monkeypatch)
    assert sim.upgrade_to("1.2.4", write_pin=True) == 0
    generations.require_greenfield_working_generation(sim.repo_root)
    (sim.repo_root / RADAR).write_bytes(b"partial new dashboard\n")
    before = _observed(sim)
    calls = _successful_dashboard_renderer(sim, monkeypatch)
    capsys.readouterr()
    monkeypatch.chdir(sim.repo_root)
    result = cli.main(["dashboard", "refresh", "--repo-root", ".", "--force"])
    output = capsys.readouterr()
    assert result != 0, (output.out, output.err)
    assert calls == []
    assert _observed(sim) == before


def _receipt(root):
    return root / recovery._RECEIPT


def _journal_bytes(root):
    parent = root / ".odylith/runtime/greenfield/create-journal"
    return {str(path.relative_to(parent)): path.read_bytes()
            for path in parent.rglob("*") if path.is_file()}


def test_failed_retry_renews_only_completion_then_success_keeps_target(
    tmp_path, monkeypatch, capsys,
):
    sim, retry, failed = _failed_upgrade(tmp_path, monkeypatch, capsys)
    receipt = _receipt(sim.repo_root)
    first_receipt = receipt.read_bytes()
    calls = []

    def fail_again(**arguments):
        assert arguments["repository_lock_fd"] is not None
        calls.append("failed-retry")
        (sim.repo_root / RADAR).write_bytes(b"second incomplete dashboard\n")
        return 2

    monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", fail_again)
    monkeypatch.chdir(sim.repo_root)
    assert cli.main(retry) != 0
    after_failure = _observed(sim)
    assert calls == ["failed-retry"]
    assert after_failure["publication_sha256"] == failed["publication_sha256"]
    assert after_failure["active_runtime"] == after_failure["pin"] == "1.2.4"
    assert after_failure["files"] == failed["files"]
    assert receipt.read_bytes() != first_receipt

    completed = _successful_dashboard_renderer(sim, monkeypatch)
    assert cli.main(retry) == 0
    assert completed == ["complete-retry"]
    after_success = _observed(sim)
    assert after_success["files"] == failed["files"]
    assert after_success["active_runtime"] == after_success["pin"] == "1.2.4"
    assert after_success["publication_sha256"] != failed["publication_sha256"]
    generations.require_greenfield_working_generation(sim.repo_root)
    assert not receipt.exists()


@pytest.mark.parametrize("changed_anchor", ("pin", "launcher", "runtime"))
@pytest.mark.parametrize("render_result", (0, 2))
def test_activation_change_during_retry_never_publishes_or_renews_authority(
    tmp_path, monkeypatch, capsys, changed_anchor, render_result,
):
    sim, retry, failed = _failed_upgrade(tmp_path, monkeypatch, capsys)
    root = sim.repo_root
    receipt_before = _receipt(root).read_bytes()
    calls = []
    after_render = []

    def change_activation(**arguments):
        assert arguments["repository_lock_fd"] is not None
        calls.append("changed-activation")
        (root / RADAR).write_bytes(b"<!doctype html><title>Retry output</title>\n")
        if changed_anchor == "pin":
            sim.write_pin("1.2.5")
        elif changed_anchor == "launcher":
            launcher = root / ".odylith/bin/odylith"
            launcher.write_bytes(launcher.read_bytes() + b"\n# Operator replaced the launcher during retry.\n")
        else:
            current = root / ".odylith/runtime/current"
            current.unlink()
            current.symlink_to(root / ".odylith/runtime/versions/1.2.3")
        after_render.append(_observed(sim))
        return render_result

    monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", change_activation)
    monkeypatch.chdir(root)
    result = cli.main(retry)
    output = capsys.readouterr()
    assert result != 0, (output.out, output.err)
    assert calls == ["changed-activation"]
    assert _observed(sim) == after_render[0]
    assert _observed(sim)["publication_sha256"] == failed["publication_sha256"]
    assert _receipt(root).read_bytes() == receipt_before
    for relative in OPERATOR_PATHS:
        assert _observed(sim)["files"][relative] == failed["files"][relative]


@pytest.mark.parametrize("receipt_state", ("missing", "corrupt"))
def test_missing_or_corrupt_receipt_cannot_render_or_mutate_journals(
    tmp_path, monkeypatch, capsys, receipt_state,
):
    sim, retry, _ = _failed_upgrade(tmp_path, monkeypatch, capsys)
    receipt = _receipt(sim.repo_root)
    if receipt_state == "missing":
        receipt.unlink()
    else:
        receipt.write_bytes(b"corrupt incomplete recovery receipt\n")
    receipt_before = receipt.read_bytes() if receipt.exists() else None
    before = _observed(sim)
    journals = _journal_bytes(sim.repo_root)
    calls = _successful_dashboard_renderer(sim, monkeypatch)
    monkeypatch.chdir(sim.repo_root)
    assert cli.main(retry) != 0
    assert calls == []
    assert _observed(sim) == before
    assert _journal_bytes(sim.repo_root) == journals
    assert (receipt.read_bytes() if receipt.exists() else None) == receipt_before


def test_copied_repository_cannot_reuse_original_upgrade_receipt(tmp_path, monkeypatch, capsys):
    sim, retry, _ = _failed_upgrade(tmp_path, monkeypatch, capsys)
    copied = tmp_path / "copied-repository"
    shutil.copytree(sim.repo_root, copied, symlinks=True)
    receipt_before = _receipt(copied).read_bytes()
    publication_before = (copied / "odylith/index.html").read_bytes()
    working_before = write_set.greenfield_managed_fingerprints(copied)
    journals = _journal_bytes(copied)
    original_before = _observed(sim)
    calls = _successful_dashboard_renderer(sim, monkeypatch)
    monkeypatch.chdir(copied)
    assert cli.main(retry) != 0
    assert calls == []
    assert _receipt(copied).read_bytes() == receipt_before
    assert (copied / "odylith/index.html").read_bytes() == publication_before
    assert write_set.greenfield_managed_fingerprints(copied) == working_before
    assert _journal_bytes(copied) == journals
    assert _observed(sim) == original_before


def test_pending_greenfield_journal_blocks_retry_without_recovery(tmp_path, monkeypatch, capsys):
    sim, retry, _ = _failed_upgrade(tmp_path, monkeypatch, capsys)
    root = sim.repo_root
    compiled = write_set.compile_greenfield_repository_write_set(source_root=root, staged_root=root)
    journal = GreenfieldCommitJournal(repo_root=root, transaction_hash="b" * 64, write_set=compiled)
    with repository_lock.greenfield_repository_lock(root):
        journal.prepare()
    journals = _journal_bytes(root)
    assert journals
    before = _observed(sim)
    receipt_before = _receipt(root).read_bytes()
    calls = _successful_dashboard_renderer(sim, monkeypatch)
    monkeypatch.setattr(GreenfieldCommitJournal, "recover_pending_journals", lambda **_: pytest.fail("retry recovered another transaction"))
    monkeypatch.chdir(root)
    try:
        result = cli.main(retry)
    finally:
        assert calls == []
        assert _journal_bytes(root) == journals
        assert _receipt(root).read_bytes() == receipt_before
        assert _observed(sim) == before
    assert result != 0


@pytest.mark.parametrize("arguments", (
    ("dashboard", "refresh", "--force", "--surfaces", "radar"),
    ("dashboard", "refresh", "--force", "--dry-run"),
    ("dashboard", "refresh", "--force", "--force"),
    ("dashboard", "refresh"),
    ("sync", "--force"),
))
def test_upgrade_receipt_cannot_authorize_another_command(tmp_path, monkeypatch, capsys, arguments):
    sim, _, _ = _failed_upgrade(tmp_path, monkeypatch, capsys)
    before = _observed(sim)
    receipt_before = _receipt(sim.repo_root).read_bytes()
    journals = _journal_bytes(sim.repo_root)
    monkeypatch.setattr(cli, "_dispatch_main", lambda *_, **__: pytest.fail("unsupported continuation dispatched"))
    monkeypatch.chdir(sim.repo_root)
    assert cli.main([*arguments, "--repo-root", "."]) != 0
    assert _observed(sim) == before
    assert _receipt(sim.repo_root).read_bytes() == receipt_before
    assert _journal_bytes(sim.repo_root) == journals
