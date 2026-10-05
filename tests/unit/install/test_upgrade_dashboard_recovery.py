"""An exact failed-upgrade completion may resume without replaying installation."""

import hashlib
import json
from datetime import UTC, datetime
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



def _selected_atlas_upgrade(root, monkeypatch, *, predecessor_applied=True):
    from odylith.install import atlas_surface_migration as atlas, migration_runtime, runtime, state
    from tests.unit.install.test_atlas_surface_migration import _seed_atlas_catalog, _patch_mermaid_render

    root.mkdir(parents=True, exist_ok=True)
    catalog = _seed_atlas_catalog(root)
    _patch_mermaid_render(monkeypatch)
    source = root / "odylith/atlas/source/migration-fixture.mmd"
    source.chmod(0o640)
    note = root / "notes/operator.md"
    note.parent.mkdir()
    note.write_bytes(b"Operator-owned UTF-8 truth: preserve \xc3\xa9\r\n")
    note.chmod(0o600)
    target_runtime = root / ".odylith/runtime/versions/0.1.15"
    target_runtime.mkdir(parents=True)
    (root / ".odylith/runtime/current").symlink_to("versions/0.1.15")
    state.write_install_state(repo_root=root, payload={"active_version": "0.1.15", "detached": False})
    monkeypatch.setattr(runtime, "current_runtime_root", lambda **_: target_runtime)
    verification = {"wheel_sha256": "synthetic-target-wheel"}
    monkeypatch.setattr(runtime, "runtime_verification_evidence", lambda _: verification)
    monkeypatch.setattr(recovery, "__file__", str(target_runtime / "lib/odylith/install/upgrade_dashboard_recovery.py"))
    monkeypatch.setattr(atlas, "__file__", str(target_runtime / "lib/odylith/install/atlas_surface_migration.py"))
    monkeypatch.setattr(atlas.diagram_freshness, "__file__", str(target_runtime / "lib/odylith/runtime/common/diagram_freshness.py"))
    inspection = atlas.inspect_atlas_surface_migration(repo_root=root, previous_version="0.1.14", target_version="0.1.15")
    decision = migration_runtime.MigrationDecision(
        migration_id=atlas.MIGRATION_ID, state="selected", reason="target render is stale",
        ledger_path=inspection.ledger_path, planned_paths=inspection.planned_paths,
        rollback_scope="generated renders only", validation_commands=(), evidence=inspection.as_dict(),
    )
    scenario = migration_runtime.RepoMigrationScenario(
        scenario="release_marked_migration_required", reasons=("migration_required=true",),
        state={"repo_role": "consumer_repo", "runtime_root": str(target_runtime)},
    )
    fields = {"previous_version": "0.1.14", "target_version": "0.1.15", "repo_schema_version": 1,
              "scenario": scenario.as_dict(), "selected": [decision.as_dict()], "blocked": [], "skipped": []}
    fingerprint = migration_runtime._fingerprint_plan_payload({"repo_root": str(root), **fields})
    plan = migration_runtime.MigrationPlan(
        repo_root=root, previous_version="0.1.14", target_version="0.1.15", repo_schema_version=1,
        scenario=scenario, selected=(decision,), skipped=(), blocked=(),
        release_manifest_migration_required=True, no_op=False, plan_fingerprint=fingerprint,
    )
    result = migration_runtime.MigrationResult(
        migration_id=atlas.MIGRATION_ID, state="applied" if predecessor_applied else "selected",
        reason="predecessor observation" if predecessor_applied else "target completion pending",
        written_paths=(), removed_paths=(), ledger_path=inspection.ledger_path,
        verification_result={"status": "passed" if predecessor_applied else "pending"},
    )
    link = migration_runtime.append_migration_ledger_snapshot(repo_root=root, plan=plan, results=(result,))
    event = {"operation": "upgrade", "status": "activated", "active_version": "0.1.15",
             "previous_version": "0.1.14", "verification": verification,
             "migration_plan": {**plan.as_dict(), "transaction_ledger": link},
             "migration_results": [result.as_dict()], "recorded_utc": datetime.now(UTC).isoformat()}
    state.append_install_ledger(repo_root=root, payload=event)
    return atlas, catalog, target_runtime, event


def _authored_bytes_and_modes(root):
    return {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mode & 0o777)
            for p in (root / "odylith/atlas/source/migration-fixture.mmd", root / "notes/operator.md")}


@pytest.mark.parametrize("predecessor_applied", [True, False])
def test_selected_atlas_completion_uses_target_theme_and_preserves_authored_sources(
    tmp_path, monkeypatch, predecessor_applied,
):
    atlas, catalog, _, event = _selected_atlas_upgrade(tmp_path, monkeypatch, predecessor_applied=predecessor_applied)
    before = _authored_bytes_and_modes(tmp_path)
    payload = json.loads(catalog.read_text())
    payload["diagrams"][0]["render_source_fingerprint"] = "retired-predecessor-theme"
    catalog.write_text(json.dumps(payload) + "\n")
    with repository_lock.greenfield_repository_lock(tmp_path) as fd:
        recovery.complete_selected_render_migrations(repo_root=tmp_path, repository_lock_fd=fd)
    after = json.loads(catalog.read_text())
    expected = atlas.diagram_freshness.ContentFingerprintCache().mermaid_render_fingerprint(
        tmp_path / after["diagrams"][0]["source_mmd"],
    )
    assert after["diagrams"][0]["render_source_fingerprint"] == expected
    assert expected != "retired-predecessor-theme"
    assert atlas.inspect_atlas_surface_migration(repo_root=tmp_path, previous_version="0.1.14", target_version="0.1.15").verification_passed
    assert _authored_bytes_and_modes(tmp_path) == before
    for key in payload["diagrams"][0]:
        if key not in {"render_source_fingerprint", "reviewed_watch_fingerprints", "last_reviewed_utc"}:
            assert after["diagrams"][0][key] == payload["diagrams"][0][key]
    assert json.loads((tmp_path / ".odylith/install-ledger.v1.jsonl").read_text().splitlines()[-1]) == event
    assert json.loads((tmp_path / event["migration_plan"]["transaction_ledger"]).read_text())["results"] == event["migration_results"]


@pytest.mark.parametrize("tamper", ["loaded-old", "old-producer", "old-inspector", "target", "verification", "link", "plan", "results", "transaction"])
def test_selected_target_completion_refuses_wrong_owner_or_ledger_link_before_render(tmp_path, monkeypatch, tamper):
    from odylith.install import state
    atlas, _, _, event = _selected_atlas_upgrade(tmp_path, monkeypatch)
    if tamper == "loaded-old":
        monkeypatch.setattr(recovery, "__file__", str(tmp_path / ".odylith/runtime/versions/0.1.14/upgrade_dashboard_recovery.py"))
    elif tamper == "old-producer":
        monkeypatch.setattr(atlas, "__file__", str(tmp_path / ".odylith/runtime/versions/0.1.14/atlas_surface_migration.py"))
    elif tamper == "old-inspector":
        monkeypatch.setattr(atlas.diagram_freshness, "__file__", str(tmp_path / ".odylith/runtime/versions/0.1.14/diagram_freshness.py"))
    elif tamper == "target":
        event["active_version"] = "0.1.14"
    elif tamper == "verification":
        event["verification"] = {"wheel_sha256": "another-wheel"}
    elif tamper == "link":
        event["migration_plan"]["transaction_ledger"] = "../outside.json"
    elif tamper == "plan":
        event["migration_plan"]["selected"][0]["reason"] = "another plan"
    elif tamper == "results":
        event["migration_results"][0]["verification_result"] = {"status": "another-result"}
    else:
        transaction = tmp_path / event["migration_plan"]["transaction_ledger"]
        payload = json.loads(transaction.read_text())
        payload["plan"]["target_version"] = "0.1.14"
        transaction.write_text(json.dumps(payload))
    (state.install_ledger_path(repo_root=tmp_path)).write_text(json.dumps(event) + "\n")
    monkeypatch.setattr(atlas, "migrate_atlas_surface_polish", lambda **_: pytest.fail("invalid completion rendered"))
    before = _authored_bytes_and_modes(tmp_path)
    with repository_lock.greenfield_repository_lock(tmp_path) as fd:
        with pytest.raises(recovery.UpgradeDashboardRecoveryError, match="freshness was not certified"):
            recovery.complete_selected_render_migrations(repo_root=tmp_path, repository_lock_fd=fd)
    assert _authored_bytes_and_modes(tmp_path) == before


def test_target_completion_rechecks_current_fingerprint_after_passed_producer(tmp_path, monkeypatch):
    atlas, catalog, _, _ = _selected_atlas_upgrade(tmp_path, monkeypatch)
    producer = atlas.migrate_atlas_surface_polish
    def stale_after_render(**arguments):
        result = producer(**arguments)
        assert result.verification_result["status"] == "passed"
        data = json.loads(catalog.read_text())
        data["diagrams"][0]["render_source_fingerprint"] = "predecessor-fingerprint"
        catalog.write_text(json.dumps(data) + "\n")
        return result
    monkeypatch.setattr(atlas, "migrate_atlas_surface_polish", stale_after_render)
    before = _authored_bytes_and_modes(tmp_path)
    with repository_lock.greenfield_repository_lock(tmp_path) as fd:
        with pytest.raises(recovery.UpgradeDashboardRecoveryError):
            recovery.complete_selected_render_migrations(repo_root=tmp_path, repository_lock_fd=fd)
    assert _authored_bytes_and_modes(tmp_path) == before


@pytest.mark.parametrize("scope", ["absent", "unselected", "unrelated-operation", "completed"])
def test_ordinary_dashboard_has_no_selected_atlas_scan_or_mutation(tmp_path, monkeypatch, scope):
    from odylith.install import state
    atlas, _, _, event = _selected_atlas_upgrade(tmp_path, monkeypatch)
    ledger = state.install_ledger_path(repo_root=tmp_path)
    if scope == "absent":
        ledger.unlink()
    elif scope == "unselected":
        event["migration_plan"]["selected"] = []
        ledger.write_text(json.dumps(event) + "\n")
    elif scope == "unrelated-operation":
        event["operation"] = "feature-pack"
        ledger.write_text(json.dumps(event) + "\n")
    else:
        logs = tmp_path / ".odylith/runtime/logs"
        logs.mkdir()
        (logs / "upgrade-20990101T000000Z.json").write_text(json.dumps({
            "plan_fingerprint": event["migration_plan"]["plan_fingerprint"],
            "finished_at": datetime.now(UTC).isoformat(), "dashboard_refresh": {"success": True},
        }))
    monkeypatch.setattr(atlas, "inspect_atlas_surface_migration", lambda **_: pytest.fail("ordinary refresh inspected Atlas"))
    monkeypatch.setattr(atlas, "migrate_atlas_surface_polish", lambda **_: pytest.fail("ordinary refresh rendered Atlas"))
    before = _authored_bytes_and_modes(tmp_path)
    with repository_lock.greenfield_repository_lock(tmp_path) as fd:
        recovery.complete_selected_render_migrations(repo_root=tmp_path, repository_lock_fd=fd)
    assert _authored_bytes_and_modes(tmp_path) == before


def test_legacy_dashboard_command_cannot_bypass_failed_upgrade_generation_admission(tmp_path, monkeypatch, capsys):
    sim, _, _ = _failed_upgrade(tmp_path, monkeypatch, capsys)
    before = _observed(sim)
    monkeypatch.setattr(recovery, "complete_selected_render_migrations", lambda **_: pytest.fail("legacy command bypassed admission"))
    assert cli.main(["dashboard", "refresh", "--repo-root", str(sim.repo_root),
                     "--surfaces", "tooling_shell,radar,compass"]) != 0
    assert _observed(sim) == before



def test_selected_completion_failed_renderer_never_certifies_freshness(tmp_path, monkeypatch):
    atlas, _, _, _ = _selected_atlas_upgrade(tmp_path, monkeypatch)
    def readonly_destination(**_):
        raise PermissionError("read-only generated destination")
    monkeypatch.setattr(atlas, "migrate_atlas_surface_polish", readonly_destination)
    before = _authored_bytes_and_modes(tmp_path)
    with repository_lock.greenfield_repository_lock(tmp_path) as fd:
        with pytest.raises(recovery.UpgradeDashboardRecoveryError) as refusal:
            recovery.complete_selected_render_migrations(repo_root=tmp_path, repository_lock_fd=fd)
    assert isinstance(refusal.value.__cause__, PermissionError)
    assert _authored_bytes_and_modes(tmp_path) == before


def test_selected_completion_requires_real_repository_lease(tmp_path, monkeypatch):
    atlas, _, _, _ = _selected_atlas_upgrade(tmp_path, monkeypatch)
    monkeypatch.setattr(atlas, "migrate_atlas_surface_polish", lambda **_: pytest.fail("unadmitted render"))
    with (tmp_path / "notes/operator.md").open("rb") as wrong:
        with pytest.raises(recovery.UpgradeDashboardRecoveryError):
            recovery.complete_selected_render_migrations(repo_root=tmp_path, repository_lock_fd=wrong.fileno())


def test_failed_selected_completion_requires_explicit_force_under_existing_lease(tmp_path, monkeypatch):
    atlas, _, _, event = _selected_atlas_upgrade(tmp_path, monkeypatch)
    logs = tmp_path / ".odylith/runtime/logs"
    logs.mkdir()
    report = {"plan_fingerprint": event["migration_plan"]["plan_fingerprint"],
              "finished_at": datetime.now(UTC).isoformat(), "dashboard_refresh": {"success": False}}
    (logs / "upgrade-20990101T000000Z.json").write_text(json.dumps(report))
    with repository_lock.greenfield_repository_lock(tmp_path) as fd:
        with pytest.raises(recovery.UpgradeDashboardRecoveryError):
            recovery.complete_selected_render_migrations(repo_root=tmp_path, repository_lock_fd=fd)
        assert not atlas.inspect_atlas_surface_migration(repo_root=tmp_path, previous_version="0.1.14", target_version="0.1.15").verification_passed
        recovery.complete_selected_render_migrations(repo_root=tmp_path, repository_lock_fd=fd, force=True)
    assert atlas.inspect_atlas_surface_migration(repo_root=tmp_path, previous_version="0.1.14", target_version="0.1.15").verification_passed
    assert json.loads((logs / "upgrade-20990101T000000Z.json").read_text()) == report
