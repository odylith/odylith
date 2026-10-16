"""Target-runtime dashboard transport, parent activation, and failed-upgrade publication."""

import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from odylith import cli
from odylith.runtime.domain_intelligence import greenfield_generation_state as state
from odylith.runtime.domain_intelligence import greenfield_generation_store as store
from odylith.runtime.domain_intelligence.greenfield_repository_lock import (
    GreenfieldRepositoryBusyError,
    greenfield_repository_lock,
)
from tests.unit.runtime.greenfield_baseline_fixtures import activate_greenfield_baseline_fixture


@pytest.fixture
def rendered_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for relative in cli._FIRST_RUN_SURFACE_OUTPUTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"<!doctype html><title>{relative}</title>\n", encoding="utf-8")
    assert state.read_active_publication(root) is None
    return root


@pytest.fixture
def renderer(monkeypatch):
    def prepare(root: Path, descriptor: int, *, returncode=0, stdout="dashboard refresh completed\n", stderr=""):
        launcher = root / ".odylith/bin/odylith"
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text("#!/bin/sh\n", encoding="utf-8")
        calls: list[object] = []

        def run(command, **kwargs):
            assert os.path.samestat(os.fstat(descriptor), (root / ".odylith/runtime/greenfield/create.lock").stat())
            with pytest.raises(GreenfieldRepositoryBusyError):
                with greenfield_repository_lock(root):
                    pytest.fail("renderer must inherit the active writer lock")
            assert command == [
                str(launcher.resolve()), "_upgrade-dashboard-render", "--repo-root", str(root),
                "--lock-fd", str(descriptor),
            ]
            assert kwargs == {
                "cwd": str(root), "check": False, "capture_output": True, "text": True,
                "pass_fds": (descriptor,),
            }
            calls.append(command)
            return subprocess.CompletedProcess(command, returncode, stdout, stderr)

        monkeypatch.setattr(cli.upgrade_dashboard.subprocess, "run", run)
        return calls

    return prepare


def test_refresh_dashboard_after_upgrade_reenters_through_fresh_launcher(rendered_repo, renderer, capsys) -> None:
    details = {}
    with greenfield_repository_lock(rendered_repo) as descriptor:
        calls = renderer(rendered_repo, descriptor)
        refreshed, message = cli._refresh_dashboard_after_upgrade(
            repo_root=rendered_repo, repository_lock_fd=descriptor, details=details,
        )
    output = capsys.readouterr()
    assert refreshed is True
    assert len(calls) == 1
    assert message == "Dashboard refreshed. Open `odylith/index.html` to see what landed in this release."
    assert "Refreshing Odylith dashboard surfaces so the local shell reflects the new release." in output.out
    assert "dashboard refresh completed" in output.out
    assert details["surfaces"] == ["tooling_shell", "radar", "compass", "registry", "casebook", "atlas"]
    store.require_greenfield_working_generation(rendered_repo)


def test_refresh_dashboard_after_upgrade_compact_hides_launcher_refresh_plan(rendered_repo, renderer, capsys) -> None:
    with greenfield_repository_lock(rendered_repo) as descriptor:
        calls = renderer(rendered_repo, descriptor, stdout="dashboard refresh plan\n- stage_timing.complete: 0.1s\ndashboard refresh completed\n")
        refreshed, message = cli._refresh_dashboard_after_upgrade(
            repo_root=rendered_repo, repository_lock_fd=descriptor, compact_output=True,
        )
    output = capsys.readouterr()
    assert refreshed is True
    assert len(calls) == 1
    assert message == "Dashboard refreshed. Open `odylith/index.html` to see what landed in this release."
    assert "draw   Refreshing dashboard." in output.out
    assert "dashboard refresh plan" not in output.out
    assert "stage_timing" not in output.out
    store.require_greenfield_working_generation(rendered_repo)


def test_refresh_dashboard_after_upgrade_returns_failure_when_launcher_refresh_fails(rendered_repo, renderer, capsys) -> None:
    with greenfield_repository_lock(rendered_repo) as descriptor:
        calls = renderer(rendered_repo, descriptor, returncode=2, stdout="dashboard refresh completed\n- outcome: failed\n", stderr="compass failed\n")
        refreshed, message = cli._refresh_dashboard_after_upgrade(
            repo_root=rendered_repo, repository_lock_fd=descriptor,
        )
    output = capsys.readouterr()
    assert refreshed is False
    assert len(calls) == 1
    assert message == "Odylith upgrade succeeded, but dashboard refresh failed. Retry with `./.odylith/bin/odylith dashboard refresh --repo-root . --force`."
    assert "dashboard refresh completed" in output.out
    assert "compass failed" in output.err
    assert state.read_active_publication(rendered_repo) is None


def test_refresh_dashboard_after_upgrade_falls_back_to_in_process_refresh_when_launcher_is_missing(
    monkeypatch, rendered_repo, capsys,
) -> None:
    calls: list[object] = []
    details = {}
    with greenfield_repository_lock(rendered_repo) as descriptor:
        def refresh(**kwargs):
            assert kwargs == {
                "repo_root": rendered_repo, "surfaces": ("tooling_shell", "radar", "compass", "registry", "casebook", "atlas"),
                "runtime_mode": "auto", "atlas_sync": False, "force": True,
                "repository_lock_fd": descriptor, "on_completed": kwargs["on_completed"],
            }
            assert os.fstat(kwargs["repository_lock_fd"])
            with pytest.raises(GreenfieldRepositoryBusyError):
                with greenfield_repository_lock(rendered_repo):
                    pytest.fail("fallback must retain the admitted writer lock")
            calls.append(kwargs)
            return kwargs["on_completed"]()

        monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", refresh)
        monkeypatch.setattr(cli.upgrade_dashboard, "run_dashboard_renderer", lambda **kwargs: pytest.fail("should use in-process fallback"))
        refreshed, message = cli._refresh_dashboard_after_upgrade(
            repo_root=rendered_repo, repository_lock_fd=descriptor, details=details,
        )
    output = capsys.readouterr()
    assert refreshed is True
    assert len(calls) == 1
    assert details["surfaces"] == ["tooling_shell", "radar", "compass", "registry", "casebook", "atlas"]
    assert message == "Dashboard refreshed. Open `odylith/index.html` to see what landed in this release."
    assert "Refreshing Odylith dashboard surfaces so the local shell reflects the new release." in output.out
    store.require_greenfield_working_generation(rendered_repo)


@pytest.mark.parametrize("json_output", [False, True])
def test_upgrade_failed_dashboard_does_not_publish_partial_working_output(
    monkeypatch, rendered_repo, capsys, json_output: bool,
) -> None:
    import json

    root = rendered_repo
    activate_greenfield_baseline_fixture(root)
    entry_before = (root / "odylith/index.html").read_bytes()
    generation_before = store.require_greenfield_working_generation(root)
    published_radar = (generation_before.repository_root / "odylith/radar/radar.html").read_bytes()
    launcher = root / ".odylith/bin/odylith"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(cli, "plan_upgrade_lifecycle", lambda **kwargs: SimpleNamespace(
        command="upgrade", headline="preview", steps=(), dirty_overlap=(), notes=(),
    ))
    monkeypatch.setattr(cli, "upgrade_install", lambda **kwargs: SimpleNamespace(
        active_version="1.2.4", launcher_path=launcher, pin_changed=False, pinned_version="1.2.4",
        previous_version="1.2.3", repo_role="consumer_repo", followed_latest=False,
        release_tag="v1.2.4", release_body="", release_highlights=(), release_published_at="", release_url="",
    ))

    def fail_render(*, repo_root: Path, repository_lock_fd: int):
        assert repo_root == root and os.fstat(repository_lock_fd)
        with pytest.raises(GreenfieldRepositoryBusyError):
            with greenfield_repository_lock(root):
                pytest.fail("partial renderer must run under the actual writer lock")
        (root / "odylith/radar/radar.html").write_text("partial new dashboard\n", encoding="utf-8")
        return subprocess.CompletedProcess([str(launcher)], 2, "dashboard incomplete\n", "compass failed\n")

    monkeypatch.setattr(cli.upgrade_dashboard, "run_dashboard_renderer", fail_render)
    rc = cli.main(["upgrade", "--repo-root", str(root), "--to", "1.2.4", *(["--json"] if json_output else [])])
    output = capsys.readouterr()
    assert rc != 0
    assert (root / "odylith/index.html").read_bytes() == entry_before
    assert store.pin_active_greenfield_generation(root).write_set_hash == generation_before.write_set_hash
    assert (generation_before.repository_root / "odylith/radar/radar.html").read_bytes() == published_radar
    assert (root / "odylith/radar/radar.html").read_text(encoding="utf-8") == "partial new dashboard\n"
    with pytest.raises(RuntimeError, match="managed files differ"):
        store.require_greenfield_working_generation(root)
    if json_output:
        payload = json.loads(output.out)
        assert payload["status"] == "failed"
        assert payload["final_state"]["active_version"] == "1.2.4"
        assert payload["dashboard_refresh"]["success"] is False
        assert next(phase for phase in payload["phases"] if phase["name"] == "dashboard_refresh")["status"] == "failed"
    else:
        assert "Dashboard ready" not in output.out
        assert "dashboard refresh failed" in output.out



def _legacy_dashboard_args(root, descriptor, **changes):
    return SimpleNamespace(**{
        "repo_root": root, "surfaces": "tooling_shell,radar,compass", "runtime_mode": "auto",
        "atlas_sync": False, "dry_run": False, "verbose": False, "force": False,
        "repository_lock_fd": descriptor, **changes,
    })


@pytest.mark.parametrize("surfaces", ["tooling_shell,radar,compass", "", "tooling_shell,radar,compass,registry,casebook,atlas"])
def test_published_predecessor_public_refresh_completes_selected_target_before_fresh(monkeypatch, rendered_repo, surfaces):
    order = []
    def complete(*, repo_root, repository_lock_fd, force):
        assert repo_root == rendered_repo and force is False
        assert os.path.samestat(os.fstat(repository_lock_fd), (repo_root / ".odylith/runtime/greenfield/create.lock").stat())
        order.append("target-migration-verified")
        return True
    def refresh(**arguments):
        assert order == ["target-migration-verified"]
        assert arguments["surfaces"] == ["tooling_shell", "radar", "compass", "registry", "casebook", "atlas"]
        order.append("dashboard-refresh")
        return 0
    monkeypatch.setattr(cli.upgrade_dashboard_recovery, "complete_selected_render_migrations", complete)
    monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", refresh)
    with greenfield_repository_lock(rendered_repo) as descriptor:
        assert cli._cmd_dashboard_refresh(_legacy_dashboard_args(rendered_repo, descriptor, surfaces=surfaces)) == 0
    assert order == ["target-migration-verified", "dashboard-refresh"]


@pytest.mark.parametrize("surfaces", ["tooling_shell,radar,compass", "", None])
def test_ordinary_legacy_scope_stays_narrow_after_completion(monkeypatch, rendered_repo, surfaces):
    monkeypatch.setattr(cli.upgrade_dashboard_recovery, "complete_selected_render_migrations", lambda **_: False)
    calls = []
    monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", lambda **args: calls.append(args) or 0)
    with greenfield_repository_lock(rendered_repo) as descriptor:
        assert cli._cmd_dashboard_refresh(_legacy_dashboard_args(rendered_repo, descriptor, surfaces=surfaces)) == 0
    assert len(calls) == 1
    assert calls[0]["surfaces"] == ["tooling_shell", "radar", "compass"]
    assert cli._DEFAULT_DASHBOARD_REFRESH_SURFACES_CSV == "tooling_shell,radar,compass"


@pytest.mark.parametrize("options", [
    {"dry_run": True}, {"atlas_sync": True}, {"runtime_mode": "standalone"}, {"surfaces": "radar"},
    {"surfaces": "", "dry_run": True}, {"surfaces": "", "runtime_mode": "standalone"},
])
def test_other_dashboard_refresh_scope_does_not_dispatch_selected_migration(monkeypatch, rendered_repo, options):
    monkeypatch.setattr(cli.upgrade_dashboard_recovery, "complete_selected_render_migrations", lambda **_: pytest.fail("unrequested migration"))
    def refresh(**arguments):
        assert arguments["surfaces"] == (["radar"] if options.get("surfaces") == "radar" else ["tooling_shell", "radar", "compass"])
        return 0
    monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", refresh)
    with greenfield_repository_lock(rendered_repo) as descriptor:
        assert cli._cmd_dashboard_refresh(_legacy_dashboard_args(rendered_repo, descriptor, **options)) == 0


def test_selected_target_failure_stops_legacy_dashboard_before_refresh_or_activation(monkeypatch, rendered_repo):
    activate_greenfield_baseline_fixture(rendered_repo)
    before = (rendered_repo / "odylith/index.html").read_bytes()
    def refused(**_):
        raise cli.upgrade_dashboard_recovery.UpgradeDashboardRecoveryError("target migration failed")
    monkeypatch.setattr(cli.upgrade_dashboard_recovery, "complete_selected_render_migrations", refused)
    monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", lambda **_: pytest.fail("failed target dispatched dashboard"))
    monkeypatch.setattr(cli.dashboard_refresh_contract, "activate_initial_dashboard_baseline", lambda **_: pytest.fail("failed target activated"))
    assert cli.main(["dashboard", "refresh", "--repo-root", str(rendered_repo),
                     "--surfaces", "tooling_shell,radar,compass"]) == 1
    assert (rendered_repo / "odylith/index.html").read_bytes() == before


def test_target_worker_completes_selected_migration_under_inherited_lease(monkeypatch, rendered_repo):
    from odylith.runtime.governance import sync_workstream_artifacts
    order = []
    def complete(*, repo_root, repository_lock_fd):
        assert repo_root == rendered_repo
        assert os.path.samestat(os.fstat(repository_lock_fd), (repo_root / ".odylith/runtime/greenfield/create.lock").stat())
        order.append("target-migration-verified")
    def refresh(**arguments):
        assert order == ["target-migration-verified"]
        assert arguments["repository_lock_fd"] is not None
        assert arguments["surfaces"] == ("tooling_shell", "radar", "compass", "registry", "casebook", "atlas")
        order.append("dashboard-refresh")
        return 0
    monkeypatch.setattr(cli.upgrade_dashboard_recovery, "complete_selected_render_migrations", complete)
    monkeypatch.setattr(sync_workstream_artifacts, "refresh_dashboard_surfaces", refresh)
    with greenfield_repository_lock(rendered_repo) as descriptor:
        worker_fd = os.dup(descriptor)
        assert cli.upgrade_dashboard.worker_main(["--repo-root", str(rendered_repo), "--lock-fd", str(worker_fd)]) == 0
    assert order == ["target-migration-verified", "dashboard-refresh"]
    assert state.read_active_publication(rendered_repo) is None


def test_target_worker_render_refusal_has_no_dashboard_dispatch(monkeypatch, rendered_repo, capsys):
    def refused(**_):
        raise cli.upgrade_dashboard_recovery.UpgradeDashboardRecoveryError("target migration failed")
    monkeypatch.setattr(cli.upgrade_dashboard_recovery, "complete_selected_render_migrations", refused)
    monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", lambda **_: pytest.fail("refused worker dispatched dashboard"))
    with greenfield_repository_lock(rendered_repo) as descriptor:
        worker_fd = os.dup(descriptor)
        assert cli.upgrade_dashboard.worker_main(["--repo-root", str(rendered_repo), "--lock-fd", str(worker_fd)]) == 1
    assert "target migration failed" in capsys.readouterr().err
    assert state.read_active_publication(rendered_repo) is None
