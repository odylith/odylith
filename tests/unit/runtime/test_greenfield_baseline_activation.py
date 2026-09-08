"""Complete first publication and narrowly recoverable working-shell activation."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from odylith import cli
from odylith.install.bootstrap_assets import customer_shell_index_placeholder_source
from odylith.runtime.domain_intelligence import greenfield_create_baseline as baseline
from odylith.runtime.domain_intelligence import greenfield_generation_state as state
from odylith.runtime.domain_intelligence import greenfield_generation_store as store
from odylith.runtime.domain_intelligence import greenfield_repository_lock as lock
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as kernel
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal


def _complete(root: Path) -> bytes:
    for relative in cli._FIRST_RUN_SURFACE_OUTPUTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"<!doctype html><title>{relative}</title>\n".encode())
    (root / "odylith/index.html").chmod(0o640)
    (root / "odylith/tooling-payload.v1.js").write_bytes(b"window.payload = {};\n")
    return (root / "odylith/index.html").read_bytes()


def _activate(root: Path):
    return baseline.activate_completed_greenfield_baseline(
        repo_root=root, required_surface_outputs=cli._FIRST_RUN_SURFACE_OUTPUTS,
    )


def test_complete_activation_preserves_raw_baseline_and_is_idempotent(tmp_path, monkeypatch):
    raw = _complete(tmp_path)
    before = kernel.greenfield_managed_fingerprints(tmp_path)
    publication = _activate(tmp_path)
    pinned = store.pin_active_greenfield_generation(tmp_path)
    assert publication == state.read_active_publication(tmp_path)
    assert (pinned.repository_root / "odylith/index.html").read_bytes() == raw
    assert (tmp_path / "odylith/tooling-shell.html").read_bytes() == raw
    assert (tmp_path / "odylith/tooling-shell.html").stat().st_mode & 0o777 == 0o640
    assert kernel.greenfield_managed_fingerprints(tmp_path) == before
    assert not (tmp_path / ".odylith/runtime/greenfield/active-generation.v1.json").exists()
    expected = kernel.compile_greenfield_repository_write_set(
        source_root=pinned.repository_root, staged_root=pinned.repository_root,
    )
    assert expected["active_generation_precondition"] == state.no_active_generation_identity()
    assert expected["write_set_hash"] == pinned.write_set_hash
    assert expected["write_count"] == expected["delete_count"] == 0
    monkeypatch.setattr(state, "compile_greenfield_publication_entry", lambda **_: pytest.fail("recompiled P"))
    assert _activate(tmp_path) == publication


@pytest.mark.parametrize("defect", ("missing", "empty", "placeholder", "symlink"))
def test_incomplete_surfaces_cannot_become_a_baseline(tmp_path, defect):
    raw = _complete(tmp_path)
    target = tmp_path / "odylith/registry/registry.html"
    if defect == "missing":
        target.unlink()
    elif defect == "empty":
        target.write_bytes(b"")
    elif defect == "placeholder":
        (tmp_path / "odylith/index.html").write_text(customer_shell_index_placeholder_source(repo_root=tmp_path))
    else:
        target.unlink()
        target.symlink_to(tmp_path / "odylith/radar/radar.html")
    with pytest.raises((ValueError, RuntimeError), match="complete|placeholder|symlink"):
        _activate(tmp_path)
    assert state.read_active_publication(tmp_path) is None
    assert not (tmp_path / "odylith/tooling-shell.html").exists()
    assert not (tmp_path / ".odylith/runtime/greenfield/generations").exists()
    if defect != "placeholder":
        assert (tmp_path / "odylith/index.html").read_bytes() == raw


def test_interruption_before_publication_preserves_raw_shell_and_can_resume(tmp_path, monkeypatch):
    raw = _complete(tmp_path)
    publish = store.publish_greenfield_generation
    monkeypatch.setattr(store, "publish_greenfield_generation", lambda **_: (_ for _ in ()).throw(OSError("before P")))
    with pytest.raises(OSError, match="before P"):
        _activate(tmp_path)
    assert state.read_active_publication(tmp_path) is None
    assert (tmp_path / "odylith/index.html").read_bytes() == raw
    assert not (tmp_path / "odylith/tooling-shell.html").exists()
    monkeypatch.setattr(store, "publish_greenfield_generation", publish)
    assert _activate(tmp_path) == state.read_active_publication(tmp_path)


def _interrupt_after_publication(root, monkeypatch):
    raw = _complete(root)
    write = baseline.atomic_write_bytes
    monkeypatch.setattr(baseline, "atomic_write_bytes", lambda *_, **__: (_ for _ in ()).throw(OSError("after P")))
    with pytest.raises(OSError, match="after P"):
        _activate(root)
    monkeypatch.setattr(baseline, "atomic_write_bytes", write)
    return raw, (root / "odylith/index.html").read_bytes()


def test_interruption_after_publication_restores_only_exact_missing_shell(tmp_path, monkeypatch):
    raw, publication = _interrupt_after_publication(tmp_path, monkeypatch)
    assert not (tmp_path / "odylith/tooling-shell.html").exists()
    pinned = store.pin_active_greenfield_generation(tmp_path)
    assert (pinned.repository_root / "odylith/index.html").read_bytes() == raw
    _activate(tmp_path)
    assert (tmp_path / "odylith/index.html").read_bytes() == publication
    assert (tmp_path / "odylith/tooling-shell.html").read_bytes() == raw
    assert kernel.greenfield_managed_fingerprints(tmp_path) == pinned.manifest["after_fingerprints"]


@pytest.mark.parametrize("defect", ("other-working-file", "existing-shell", "immutable-file"))
def test_interrupted_activation_preserves_drift_and_fails_closed(tmp_path, monkeypatch, defect):
    _, publication = _interrupt_after_publication(tmp_path, monkeypatch)
    working = tmp_path / "odylith/tooling-shell.html"
    if defect == "other-working-file":
        target = tmp_path / "odylith/radar/radar.html"
    elif defect == "existing-shell":
        target = working
    else:
        target = store.pin_active_greenfield_generation(tmp_path).repository_root / "odylith/index.html"
    target.write_bytes(b"unexplained change\n")
    with pytest.raises(RuntimeError, match="differ|drift"):
        _activate(tmp_path)
    assert target.read_bytes() == b"unexplained change\n"
    assert (tmp_path / "odylith/index.html").read_bytes() == publication
    assert working.exists() is (defect == "existing-shell")


def test_activation_recovers_journals_under_lock_before_baseline_capture(tmp_path, monkeypatch):
    _complete(tmp_path)
    observations = []

    def recover(*, repo_root):
        with pytest.raises(lock.GreenfieldRepositoryBusyError):
            with lock.greenfield_repository_lock(repo_root):
                pytest.fail("activation did not own lock")
        observations.append(state.read_active_publication(repo_root))
        (repo_root / "odylith/radar/radar.html").write_bytes(b"recovered baseline\n")

    monkeypatch.setattr(GreenfieldCommitJournal, "recover_pending_journals", recover)
    _activate(tmp_path)
    pinned = store.pin_active_greenfield_generation(tmp_path)
    assert observations == [None]
    assert (pinned.repository_root / "odylith/radar/radar.html").read_bytes() == b"recovered baseline\n"


@pytest.mark.parametrize("initially_complete", (False, True))
def test_bootstrap_activates_only_after_successful_render(tmp_path, monkeypatch, initially_complete):
    if initially_complete:
        _complete(tmp_path)
    calls = []

    def render(**_):
        assert state.read_active_publication(tmp_path) is None
        with pytest.raises(lock.GreenfieldRepositoryBusyError):
            with lock.greenfield_repository_lock(tmp_path):
                pytest.fail("bootstrap render did not inherit CLI writer lock")
        calls.append("render")
        _complete(tmp_path)
        return 0

    monkeypatch.setattr(cli, "_sync_workstream_artifacts", lambda: SimpleNamespace(refresh_dashboard_surfaces=render))
    monkeypatch.setattr(cli, "_run_first_run_full_sync", render)
    monkeypatch.setattr(cli, "_cmd_install", lambda args: cli._bootstrap_first_run_surfaces(repo_root=Path(args.repo_root)))
    assert cli.main(["install", "--repo-root", str(tmp_path), "--no-open"]) == 0
    assert calls == ["render"]
    assert state.read_active_publication(tmp_path) is not None


@pytest.mark.parametrize("render_result", (0, 1))
def test_bootstrap_partial_or_failed_render_does_not_activate(tmp_path, monkeypatch, render_result):
    monkeypatch.setattr(cli, "_sync_workstream_artifacts", lambda: SimpleNamespace())
    monkeypatch.setattr(cli, "_run_first_run_full_sync", lambda **_: render_result)
    with lock.greenfield_repository_lock(tmp_path):
        assert cli._bootstrap_first_run_surfaces(repo_root=tmp_path) != 0
    assert state.read_active_publication(tmp_path) is None


def test_protected_bootstrap_leaves_publication_to_outer_writer(tmp_path, monkeypatch):
    _complete(tmp_path)
    publication = _activate(tmp_path)
    monkeypatch.setattr(cli, "_sync_workstream_artifacts", lambda: SimpleNamespace(refresh_dashboard_surfaces=lambda **_: 0))
    monkeypatch.setattr(baseline, "activate_completed_greenfield_baseline", lambda **_: pytest.fail("nested activation"))
    with lock.greenfield_repository_lock(tmp_path):
        assert cli._bootstrap_first_run_surfaces(repo_root=tmp_path) == 0
    assert state.read_active_publication(tmp_path) == publication


@pytest.mark.parametrize("root_option,repair_option", (("--repo-root", "--repair"), ("--repo-ro", "--repa")))
def test_validated_doctor_repair_restores_interrupted_activation_before_dispatch(tmp_path, monkeypatch, root_option, repair_option):
    raw, publication = _interrupt_after_publication(tmp_path, monkeypatch)
    observations = []

    def doctor(**arguments):
        observations.append(arguments)
        assert (tmp_path / "odylith/tooling-shell.html").read_bytes() == raw
        store.require_greenfield_working_generation(tmp_path)
        with pytest.raises(lock.GreenfieldRepositoryBusyError):
            with lock.greenfield_repository_lock(tmp_path):
                pytest.fail("doctor is not inside writer admission")
        return True, "Synthetic install-owner readback passed."

    monkeypatch.setattr(cli, "doctor_bundle", doctor)
    monkeypatch.setattr(cli, "version_status", lambda **_: None)
    assert cli.main(["doctor", root_option, str(tmp_path), repair_option]) == 0
    assert len(observations) == 1 and observations[0]["repair"] is True
    assert (tmp_path / "odylith/index.html").read_bytes() == publication


@pytest.mark.parametrize("arguments", (("--repair", "--unknown"), ("--repair=invalid",), ("--repair", "extra"), ("--rep",)))
def test_invalid_doctor_arguments_cannot_recover_or_dispatch(tmp_path, monkeypatch, arguments):
    _, publication = _interrupt_after_publication(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "doctor_bundle", lambda **_: pytest.fail("invalid doctor dispatched"))
    monkeypatch.setattr(GreenfieldCommitJournal, "recover_pending_journals", lambda **_: pytest.fail("invalid doctor recovered journals"))
    with pytest.raises(SystemExit) as failure:
        cli.main(["doctor", "--repo-root", str(tmp_path), *arguments])
    assert failure.value.code == 2
    assert not (tmp_path / "odylith/tooling-shell.html").exists()
    assert (tmp_path / "odylith/index.html").read_bytes() == publication


@pytest.mark.parametrize("defect", ("other-file", "working-shell", "symlink", "missing-immutable-surface"))
def test_doctor_repair_does_not_admit_arbitrary_drift(tmp_path, monkeypatch, defect):
    _, publication = _interrupt_after_publication(tmp_path, monkeypatch)
    working = tmp_path / "odylith/tooling-shell.html"
    if defect == "other-file":
        (tmp_path / "odylith/radar/radar.html").write_bytes(b"operator change\n")
    elif defect == "working-shell":
        working.write_bytes(b"operator change\n")
    elif defect == "symlink":
        working.symlink_to(tmp_path / "odylith/radar/radar.html")
    else:
        (store.pin_active_greenfield_generation(tmp_path).repository_root / "odylith/registry/registry.html").unlink()
    monkeypatch.setattr(cli, "doctor_bundle", lambda **_: pytest.fail("unsafe doctor dispatched"))
    assert cli.main(["doctor", "--repo-root", str(tmp_path), "--repair"]) == 1
    assert (tmp_path / "odylith/index.html").read_bytes() == publication
    assert working.exists() is (defect in {"working-shell", "symlink"})


def test_doctor_without_repair_never_restores_the_working_shell(tmp_path, monkeypatch):
    _, publication = _interrupt_after_publication(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "doctor_bundle", lambda **_: (True, "Read-only synthetic check."))
    monkeypatch.setattr(cli, "version_status", lambda **_: None)
    assert cli.main(["doctor", "--repo-root", str(tmp_path)]) == 0
    assert not (tmp_path / "odylith/tooling-shell.html").exists()
    assert (tmp_path / "odylith/index.html").read_bytes() == publication


def test_doctor_reset_without_repair_is_rejected_without_recovery(tmp_path, monkeypatch):
    _, publication = _interrupt_after_publication(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "doctor_bundle", lambda **_: pytest.fail("invalid reset dispatched"))
    monkeypatch.setattr(GreenfieldCommitJournal, "recover_pending_journals", lambda **_: pytest.fail("invalid reset recovered"))
    assert cli.main(["doctor", "--repo-root", str(tmp_path), "--reset-local-state"]) == 2
    assert not (tmp_path / "odylith/tooling-shell.html").exists()
    assert (tmp_path / "odylith/index.html").read_bytes() == publication


def test_doctor_repair_cannot_enter_a_competing_writer(tmp_path, monkeypatch):
    _, publication = _interrupt_after_publication(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "doctor_bundle", lambda **_: pytest.fail("busy doctor dispatched"))
    with lock.greenfield_repository_lock(tmp_path):
        assert cli.main(["doctor", "--repo-root", str(tmp_path), "--repair"]) == 75
    assert not (tmp_path / "odylith/tooling-shell.html").exists()
    assert (tmp_path / "odylith/index.html").read_bytes() == publication


def test_doctor_recovery_does_not_activate_an_unpublished_root(tmp_path, monkeypatch):
    raw = _complete(tmp_path)
    monkeypatch.setattr(cli, "doctor_bundle", lambda **_: (True, "Synthetic install-owner check."))
    monkeypatch.setattr(cli, "version_status", lambda **_: None)
    assert cli.main(["doctor", "--repo-root", str(tmp_path), "--repair"]) == 0
    assert state.read_active_publication(tmp_path) is None
    assert (tmp_path / "odylith/index.html").read_bytes() == raw
    assert not (tmp_path / "odylith/tooling-shell.html").exists()


def test_first_install_publishes_writes_made_after_bootstrap_activation(tmp_path, monkeypatch):
    baseline_generation = []

    def render(**_):
        _complete(tmp_path)
        return 0

    def install(args):
        assert cli._bootstrap_first_run_surfaces(repo_root=Path(args.repo_root)) == 0
        baseline_generation.append(store.pin_active_greenfield_generation(tmp_path))
        (tmp_path / "odylith/registry/registry.html").write_bytes(b"Complete final install view\n")
        return 0

    monkeypatch.setattr(cli, "_sync_workstream_artifacts", lambda: SimpleNamespace())
    monkeypatch.setattr(cli, "_run_first_run_full_sync", render)
    monkeypatch.setattr(cli, "_cmd_install", install)
    assert cli.main(["install", "--repo-root", str(tmp_path), "--no-open"]) == 0
    final = store.require_greenfield_working_generation(tmp_path)
    assert final.write_set_hash != baseline_generation[0].write_set_hash
    assert (final.repository_root / "odylith/registry/registry.html").read_bytes() == b"Complete final install view\n"
    assert (baseline_generation[0].repository_root / "odylith/registry/registry.html").read_bytes() != b"Complete final install view\n"


def _dashboard_renderer(monkeypatch, render):
    monkeypatch.setattr(cli, "_sync_workstream_artifacts", lambda: SimpleNamespace(
        normalize_dashboard_surfaces=lambda values: tuple(values[0].split(",")),
        refresh_dashboard_surfaces=render,
    ))


def test_dashboard_refresh_activates_complete_baseline_inside_writer_lock(tmp_path, monkeypatch):
    def render(**kwargs):
        with pytest.raises(lock.GreenfieldRepositoryBusyError):
            with lock.greenfield_repository_lock(tmp_path):
                pytest.fail("dashboard completion lost writer ownership")
        _complete(tmp_path)
        return kwargs.get("on_completed", lambda: 0)()

    _dashboard_renderer(monkeypatch, render)
    assert cli.main(["dashboard", "refresh", "--repo-root", str(tmp_path), "--force"]) == 0
    store.require_greenfield_working_generation(tmp_path)


@pytest.mark.parametrize("defect", ("missing", "empty", "placeholder", "failed", "queued", "dry-run"))
def test_dashboard_cannot_activate_incomplete_or_unfinished_refresh(tmp_path, monkeypatch, capsys, defect):
    _complete(tmp_path)
    target = tmp_path / "odylith/registry/registry.html"
    if defect == "missing":
        target.unlink()
    elif defect == "empty":
        target.write_bytes(b"")
    elif defect == "placeholder":
        (tmp_path / "odylith/index.html").write_text(customer_shell_index_placeholder_source(repo_root=tmp_path))

    def render(**kwargs):
        if defect == "failed":
            return 2
        if defect in {"queued", "dry-run"}:
            return 0
        return kwargs.get("on_completed", lambda: 0)()

    _dashboard_renderer(monkeypatch, render)
    args = ["dashboard", "refresh", "--repo-root", str(tmp_path)]
    if defect == "dry-run":
        args.append("--dry-run")
    rc = cli.main(args)
    assert state.read_active_publication(tmp_path) is None
    if defect not in {"queued", "dry-run"}:
        assert rc != 0
    if defect in {"empty", "placeholder"}:
        assert "baseline activation" in capsys.readouterr().err


def test_dashboard_active_generation_uses_outer_successor_not_baseline_readmission(tmp_path, monkeypatch):
    _complete(tmp_path)
    previous = _activate(tmp_path)
    monkeypatch.setattr(baseline, "activate_completed_greenfield_baseline_locked", lambda **_: pytest.fail("re-admitted in-flight working writes"))

    def render(**kwargs):
        (tmp_path / "odylith/registry/registry.html").write_bytes(b"Updated registry view\n")
        return kwargs.get("on_completed", lambda: 0)()

    _dashboard_renderer(monkeypatch, render)
    assert cli.main(["dashboard", "refresh", "--repo-root", str(tmp_path)]) == 0
    current = store.require_greenfield_working_generation(tmp_path)
    assert state.read_active_publication(tmp_path) != previous
    assert (current.repository_root / "odylith/registry/registry.html").read_bytes() == b"Updated registry view\n"


def test_dashboard_activation_failure_is_not_success(tmp_path, monkeypatch, capsys):
    _complete(tmp_path)

    def fail(**_):
        raise OSError("activation write failed")

    monkeypatch.setattr(baseline, "activate_completed_greenfield_baseline_locked", fail)
    _dashboard_renderer(monkeypatch, lambda **kwargs: kwargs.get("on_completed", lambda: 0)())
    assert cli.main(["dashboard", "refresh", "--repo-root", str(tmp_path)]) == 1
    assert "activation write failed" in capsys.readouterr().err
    assert state.read_active_publication(tmp_path) is None
