from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path

import pytest

from odylith.runtime.common import compass_log_continuation as continuation
from odylith.runtime.common import log_compass_timeline_event as log
from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary as boundary
from odylith.runtime.domain_intelligence import greenfield_repository_lock as leases
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as write_sets
from odylith.runtime.governance import compass_dashboard_refresh_inputs as inputs
from odylith.runtime.governance import sync_workstream_artifacts as sync
from odylith.runtime.surfaces import compass_refresh_runtime as refresh
from tests.unit.runtime.test_greenfield_managed_mutation_boundary import _active_repository


EVENT = b'{"kind": "statement", "summary": "One durable event", "ts_iso": "2026-09-10T12:00:00+00:00"}\n'


@pytest.fixture
def active(tmp_path, monkeypatch):
    # Rendering is replaced at its existing public boundary. No provider,
    # daemon, installed consumer, or live workspace is used by this fixture.
    monkeypatch.setattr(continuation, "_runtime_identity", lambda root: {"code": "frozen"})
    repository = _active_repository(tmp_path)
    monkeypatch.chdir(repository[0])
    return repository


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _terminal(repo, *, status="passed"):
    path = repo / continuation._REQUEST_PATH
    previous = json.loads(path.read_text()).get("request_id", "request") if path.exists() else "request"
    state = refresh._base_state(request_id=previous + "-next", requested_profile="shell-safe",
                                requested_runtime_mode="standalone", status="queued")
    state = refresh._finalize_state(state, status=status, rc=0 if status == "passed" else 1, terminal_reason="")
    refresh._write_state(repo_root=repo, payload=state)


def _success(repo, **kwargs):
    _terminal(repo)
    state = refresh._load_state(repo_root=repo)
    if callback := kwargs.get("on_results"):
        callback([{"surface": "compass", "status": "passed", "rc": 0, "action_results": [
            {"request_id": state["request_id"], "state": state, "coalesced": False, "status": "passed", "rc": 0},
        ]}])
    return 0


def _receipt(repo):
    return json.loads((repo / continuation.RECEIPT_PATH).read_text())


def _run(repo, *, complete=False):
    tokens = ["compass", "log", "--repo-root", str(repo)]
    if complete:
        tokens.append("--complete")

    def operation(descriptor):
        if complete:
            return log.main(tokens[2:], repository_lock_fd=descriptor)
        admitted = continuation.prepare_append(repo_root=repo, event=EVENT, repository_lock_fd=descriptor)
        continuation.append_prepared(admitted)
        try:
            return admitted.render()
        except RuntimeError:
            return 1

    return boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo, command_tokens=tokens, operation=operation,
    )


def _failed(repo, monkeypatch):
    def render(**kwargs):
        _write(repo / "odylith/compass/runtime/current.v1.json", b'{"partial": true}\n')
        raise RuntimeError("synthetic handled failure")

    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", render)
    assert _run(repo) == 1
    assert _receipt(repo)["phase"] == "failed"


def _no_render(**kwargs):
    pytest.fail("no refresh may run across a rejected continuation")


def test_completion_is_a_payload_free_public_invocation():
    args = log._parse_args(["--repo-root", ".", "--complete"])
    assert args.complete is True


@pytest.mark.parametrize("extra", [
    ["--summary", "must not append"], ["--kind", "decision"],
    ["--stream", "odylith/compass/runtime/agent-stream.v1.jsonl"],
    ["--complete"], ["--receipt", "untrusted.json"],
])
def test_completion_rejects_every_append_or_receipt_override(extra):
    with pytest.raises(SystemExit):
        log._parse_args(["--complete", *extra])


@pytest.mark.parametrize("failure", ["nonzero", "exception"])
def test_handled_failure_retries_once_without_reappending(active, monkeypatch, failure):
    repo, original = active
    calls = []

    def render(**kwargs):
        calls.append(True)
        _write(repo / "odylith/compass/runtime/current.v1.json", b'{"progress": 1}\n')
        if len(calls) < 3:
            if failure == "exception":
                raise ValueError("synthetic render exception")
            return 7
        _write(repo / "odylith/tooling-shell.html", b'<!doctype html><title>Completed</title>\n')
        return _success(repo, **kwargs)

    # Exercise the public surface policy adapter without its rendering/provider
    # implementation; completion owns its command-specific nonzero advice.
    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", render)
    if failure == "exception":
        with pytest.raises(ValueError, match="synthetic render exception"):
            _run(repo)
        with pytest.raises(ValueError, match="synthetic render exception"):
            _run(repo, complete=True)
    else:
        assert _run(repo) == 1
        assert _run(repo, complete=True) == 1
    assert _receipt(repo)["phase"] == "failed"
    assert generations.pin_active_greenfield_generation(repo).write_set_hash == original.write_set_hash
    assert (repo / continuation.STREAM_PATH).read_bytes() == EVENT
    assert _run(repo, complete=True) == 0
    current = generations.require_greenfield_working_generation(repo)
    assert current.write_set_hash != original.write_set_hash
    assert (current.repository_root / continuation.STREAM_PATH).read_bytes() == EVENT
    assert not (repo / continuation.RECEIPT_PATH).exists()
    assert len(calls) == 3
    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", _no_render)
    with pytest.raises(continuation.CompassLogContinuationError, match="receipt"):
        _run(repo, complete=True)


@pytest.mark.parametrize("mutation", ["stream_bytes", "stream_mode", "authored_bytes", "authored_mode", "derived", "runtime", "publication", "repo_inode", "foreign_active"])
def test_changed_anchors_refuse_before_render(active, monkeypatch, mutation):
    repo, _ = active
    _failed(repo, monkeypatch)
    receipt_before = (repo / continuation.RECEIPT_PATH).read_bytes()
    if mutation == "stream_bytes":
        _write(repo / continuation.STREAM_PATH, EVENT + b'{}\n')
    elif mutation == "stream_mode":
        (repo / continuation.STREAM_PATH).chmod(0o644)
    elif mutation == "authored_bytes":
        _write(repo / "odylith/radar/source/keep.md", b"foreign authored content\n")
    elif mutation == "authored_mode":
        (repo / "odylith/radar/source/keep.md").chmod(0o600)
    elif mutation == "derived":
        _write(repo / "odylith/compass/runtime/current.v1.json", b"unrecorded\n")
    elif mutation == "runtime":
        monkeypatch.setattr(continuation, "_runtime_identity", lambda root: {"code": "changed"})
    elif mutation == "publication":
        prior = publication.active_generation_identity(repo)
        monkeypatch.setattr(publication, "active_generation_identity", lambda root: {**prior, "publication_sha256": "0" * 64})
    elif mutation == "repo_inode":
        anchor = continuation._anchors(repo)
        monkeypatch.setattr(continuation, "_anchors", lambda root: {**anchor, "repository": [str(repo), 0, 0]})
    else:
        _write(repo / continuation._REQUEST_PATH, b'{"status": "running", "pid": 987654}\n')
    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", _no_render)
    with pytest.raises(continuation.CompassLogContinuationError):
        _run(repo, complete=True)
    assert (repo / continuation.RECEIPT_PATH).read_bytes() == receipt_before


@pytest.mark.parametrize("terminal", ["foreign_passed", "still_running", "authored_write", "interrupt"])
def test_unrecordable_render_stays_closed(active, monkeypatch, terminal):
    repo, original = active

    def render(**kwargs):
        _write(repo / "odylith/compass/runtime/current.v1.json", b"partial\n")
        if terminal == "authored_write":
            _write(repo / "odylith/radar/source/keep.md", b"must not adopt\n")
        elif terminal == "interrupt":
            raise KeyboardInterrupt("synthetic interruption")
        else:
            status = "passed" if terminal == "foreign_passed" else "running"
            _terminal(repo, status=status)
        raise RuntimeError("render returned without acceptable custody")

    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", render)
    if terminal == "interrupt":
        with pytest.raises(KeyboardInterrupt):
            _run(repo)
    else:
        assert _run(repo) == 1
    assert _receipt(repo)["phase"] == "rendering"
    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", _no_render)
    with pytest.raises(continuation.CompassLogContinuationError):
        _run(repo, complete=True)
    assert (repo / continuation.STREAM_PATH).read_bytes() == EVENT
    assert generations.pin_active_greenfield_generation(repo).write_set_hash == original.write_set_hash


@pytest.mark.parametrize("append_state", ["absent", "partial", "complete", "complete_with_unrecorded_render"])
def test_prepared_phase_recovers_only_exact_complete_append(active, monkeypatch, append_state):
    repo, _ = active
    with leases.greenfield_repository_lock(repo) as descriptor:
        continuation.prepare_append(repo_root=repo, event=EVENT, repository_lock_fd=descriptor)
        if append_state != "absent":
            _write(repo / continuation.STREAM_PATH, EVENT if append_state.startswith("complete") else EVENT[:-1])
            (repo / continuation.STREAM_PATH).chmod(0o600)
        if append_state == "complete_with_unrecorded_render":
            _write(repo / "odylith/compass/runtime/current.v1.json", b"unrecorded\n")
    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", lambda **kwargs: _success(repo, **kwargs))
    if append_state == "complete":
        assert _run(repo, complete=True) == 0
        assert (repo / continuation.STREAM_PATH).read_bytes() == EVENT
    else:
        with pytest.raises(continuation.CompassLogContinuationError):
            _run(repo, complete=True)
        assert _receipt(repo)["phase"] == "prepared"


@pytest.mark.parametrize("mutation", ["stream", "authored", "runtime", "request"])
def test_preappend_change_never_writes_event(active, monkeypatch, mutation):
    repo, _ = active
    with leases.greenfield_repository_lock(repo) as descriptor:
        admitted = continuation.prepare_append(repo_root=repo, event=EVENT, repository_lock_fd=descriptor)
        if mutation == "stream":
            _write(repo / continuation.STREAM_PATH, b"foreign\n")
        elif mutation == "authored":
            _write(repo / "odylith/radar/source/keep.md", b"changed\n")
        elif mutation == "runtime":
            monkeypatch.setattr(continuation, "_runtime_identity", lambda root: {"code": "changed"})
        else:
            _write(repo / continuation._REQUEST_PATH, b'{"status": "running"}\n')
        with pytest.raises(continuation.CompassLogContinuationError):
            continuation.append_prepared(admitted)
    stream = repo / continuation.STREAM_PATH
    assert not stream.exists() or EVENT not in stream.read_bytes()
    assert _receipt(repo)["phase"] == "prepared"


@pytest.mark.parametrize("failure_point", ["materialize", "publish_before", "publish_after", "retire"])
def test_completed_render_survives_seal_publication_and_cleanup_failures(active, monkeypatch, failure_point):
    repo, original = active
    render_calls = []
    def render(**kwargs):
        render_calls.append(True)
        return _success(repo, **kwargs)

    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", render)
    if failure_point == "materialize":
        target, name = generations, "materialize_immutable_greenfield_generation"
    elif failure_point.startswith("publish"):
        target, name = generations, "publish_greenfield_generation"
    else:
        target, name = Path, "unlink"
    real = getattr(target, name)

    def fail(*args, **kwargs):
        if failure_point == "retire" and args[0] != repo / continuation.RECEIPT_PATH:
            return real(*args, **kwargs)
        if failure_point == "publish_after":
            real(*args, **kwargs)
        raise OSError("synthetic publication or cleanup failure")

    monkeypatch.setattr(target, name, fail)
    with pytest.raises(OSError):
        _run(repo)
    assert _receipt(repo)["phase"] == ("rendered" if failure_point == "materialize" else "sealed")
    if failure_point in {"publish_after", "retire"}:
        assert generations.pin_active_greenfield_generation(repo).write_set_hash != original.write_set_hash
    else:
        assert generations.pin_active_greenfield_generation(repo).write_set_hash == original.write_set_hash
    monkeypatch.setattr(target, name, real)
    assert _run(repo, complete=True) == 0
    assert render_calls == [True]
    assert (repo / continuation.STREAM_PATH).read_bytes() == EVENT
    assert not (repo / continuation.RECEIPT_PATH).exists()


def test_receiptless_historical_failure_is_never_adopted(active, monkeypatch):
    repo, _ = active
    _write(repo / continuation.STREAM_PATH, EVENT)
    _write(repo / "odylith/compass/runtime/current.v1.json", b"historical failure\n")
    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", _no_render)
    with pytest.raises(continuation.CompassLogContinuationError, match="receipt"):
        _run(repo, complete=True)
    with pytest.raises(generations.GreenfieldWorkingGenerationDriftError):
        _run(repo)
    assert (repo / continuation.STREAM_PATH).read_bytes() == EVENT
    assert not (repo / continuation.RECEIPT_PATH).exists()


def test_directory_fsync_failure_after_retirement_cannot_reappend(active, monkeypatch):
    repo, _ = active
    receipt = repo / continuation.RECEIPT_PATH
    real = continuation.fsync_directory

    def fail_after_unlink(path):
        if path == receipt.parent and not receipt.exists():
            raise OSError("synthetic post-unlink directory fsync failure")
        return real(path)

    monkeypatch.setattr(continuation, "fsync_directory", fail_after_unlink)
    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", lambda **kwargs: _success(repo, **kwargs))
    with pytest.raises(OSError, match="post-unlink"):
        _run(repo)
    assert not receipt.exists()
    current = generations.require_greenfield_working_generation(repo)
    assert (current.repository_root / continuation.STREAM_PATH).read_bytes() == EVENT
    with pytest.raises(continuation.CompassLogContinuationError, match="receipt"):
        _run(repo, complete=True)
    assert (repo / continuation.STREAM_PATH).read_bytes() == EVENT


@pytest.mark.parametrize("field,value", [("publication", None), ("event", []), ("before_stream", {}), ("after_stream", "wrong"), ("working", {}), ("anchors", []), ("successor", {})])
def test_malformed_receipt_is_a_closed_refusal(active, monkeypatch, field, value):
    repo, _ = active
    _failed(repo, monkeypatch)
    receipt = _receipt(repo)
    receipt[field] = value
    _write(repo / continuation.RECEIPT_PATH, (json.dumps(receipt, sort_keys=True) + "\n").encode())
    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", _no_render)
    with pytest.raises(continuation.CompassLogContinuationError):
        _run(repo, complete=True)


def test_cli_hands_off_lock_and_completion_never_prepares_another_event(active, monkeypatch, capsys):
    from odylith import cli

    repo, _ = active
    prepared = []
    real_prepare = log.prepare_event

    def prepare(**kwargs):
        prepared.append(True)
        return real_prepare(**kwargs)

    monkeypatch.setattr(log, "prepare_event", prepare)
    monkeypatch.setattr(log.component_registry, "build_component_index", lambda **kwargs: ({}, {}, []))
    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", lambda **kwargs: 7)
    assert cli.main(["compass", "log", "--repo-root", str(repo), "--kind", "statement",
                     "--summary", "  One   durable event ", "--ts-iso", "2026-09-10T12:00:00+00:00"]) == 1
    data = (repo / continuation.STREAM_PATH).read_bytes()
    assert json.loads(data)["summary"] == "One durable event"
    output = capsys.readouterr().out
    assert "compass log --repo-root . --complete" in output
    assert "compass refresh --repo-root . --wait" not in output
    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", lambda **kwargs: _success(repo, **kwargs))
    assert cli.main(["compass", "log", "--repo-root", str(repo), "--complete"]) == 0
    assert (repo / continuation.STREAM_PATH).read_bytes() == data
    assert prepared == [True]
    assert not (repo / continuation.RECEIPT_PATH).exists()


@pytest.mark.parametrize("extra", [["--kind", "statement"], ["--repo-root", "."], ["--complete"], ["--receipt", "file.json"]])
def test_cli_invalid_completion_is_refused_before_dispatch(active, monkeypatch, extra):
    from odylith import cli

    repo, _ = active
    monkeypatch.setattr(log, "main", _no_render)
    monkeypatch.setattr(leases, "greenfield_repository_lock", lambda *args: pytest.fail("invalid completion cannot acquire a lock"))
    assert cli.main(["compass", "log", "--repo-root", str(repo), "--complete", *extra]) == 1
    assert not (repo / continuation.STREAM_PATH).exists()
    assert not (repo / continuation.RECEIPT_PATH).exists()


def test_custom_stream_keeps_append_api_but_never_receives_completion_authority(active, monkeypatch):
    repo, _ = active
    custom = repo / "odylith/compass/runtime/custom.jsonl"
    monkeypatch.setattr(log.component_registry, "build_component_index", lambda **kwargs: ({}, {}, []))
    with leases.greenfield_repository_lock(repo) as descriptor:
        payload = log.append_event(repo_root=repo, stream_path=custom, repository_lock_fd=descriptor,
                                   kind="update", summary="  Ready  ", workstream_values=[],
                                   artifact_values=[], component_values=[])
    assert payload["kind"] == "statement"
    assert payload["summary"] == "Ready"
    assert json.loads(custom.read_text()) == payload
    assert not (repo / continuation.RECEIPT_PATH).exists()
    assert not (repo / continuation.STREAM_PATH).exists()


@pytest.mark.parametrize("request_bytes", [b'{"status": "running"}', b'{"status": "passed"}', b'not-json'])
def test_unknown_or_active_request_cannot_admit_an_append(active, monkeypatch, request_bytes):
    repo, _ = active
    # Publish the preexisting request through the ordinary test writer so this
    # control reaches log admission rather than generic working-drift refusal.
    boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo, command_tokens=["compass", "refresh"],
        operation=lambda fd: (_write(repo / continuation._REQUEST_PATH, request_bytes) or 0),
    )
    with pytest.raises(continuation.CompassLogContinuationError, match="request"):
        _run(repo)
    assert not (repo / continuation.STREAM_PATH).exists()
    assert not (repo / continuation.RECEIPT_PATH).exists()


@pytest.mark.parametrize("terminal", ["missing", "unchanged", "failed"])
def test_zero_return_without_own_passed_request_is_not_publishable(active, monkeypatch, terminal):
    repo, _ = active
    if terminal == "unchanged":
        boundary.run_with_greenfield_managed_mutation_boundary(
            repo_root=repo, command_tokens=["compass", "refresh"],
            operation=lambda fd: (_terminal(repo) or 0),
        )

    def render(**kwargs):
        if terminal == "failed":
            _terminal(repo, status="failed")
        return 0

    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", render)
    assert _run(repo) == 1
    assert _receipt(repo)["phase"] == "rendering"
    with pytest.raises(continuation.CompassLogContinuationError):
        _run(repo, complete=True)


def test_append_receipt_and_stream_are_durable_before_appended_phase(active, monkeypatch):
    repo, _ = active
    synced = []
    real_fsync = os.fsync

    def fsync(descriptor):
        actual = os.fstat(descriptor)
        stream = repo / continuation.STREAM_PATH
        if stream.exists() and actual.st_ino == stream.stat().st_ino:
            assert _receipt(repo)["phase"] == "prepared"
            assert stream.read_bytes() == EVENT
            synced.append("stream")
        return real_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", fsync)
    with leases.greenfield_repository_lock(repo) as descriptor:
        admitted = continuation.prepare_append(repo_root=repo, event=EVENT, repository_lock_fd=descriptor)
        assert _receipt(repo)["phase"] == "prepared"
        assert not (repo / continuation.STREAM_PATH).exists()
        continuation.append_prepared(admitted)
        assert _receipt(repo)["phase"] == "appended"
        with pytest.raises(continuation.CompassLogContinuationError, match="already attempted"):
            continuation.append_prepared(admitted)
    assert synced == ["stream"]


def test_lost_lease_never_appends(active):
    repo, _ = active
    with leases.greenfield_repository_lock(repo) as descriptor:
        admitted = continuation.prepare_append(repo_root=repo, event=EVENT, repository_lock_fd=descriptor)
    with pytest.raises(continuation.CompassLogContinuationError, match="lease"):
        continuation.append_prepared(admitted)
    assert not (repo / continuation.STREAM_PATH).exists()


def test_existing_stream_prefix_and_mode_are_preserved(active, monkeypatch):
    repo, _ = active
    prefix = b'{"kind":"statement","summary":"Earlier event"}\n'

    def original_stream(fd):
        _write(repo / continuation.STREAM_PATH, prefix)
        (repo / continuation.STREAM_PATH).chmod(0o640)
        return 0

    boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo, command_tokens=["ordinary-test-writer"], operation=original_stream,
    )
    _failed(repo, monkeypatch)
    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", lambda **kwargs: _success(repo, **kwargs))
    assert _run(repo, complete=True) == 0
    stream = repo / continuation.STREAM_PATH
    assert stream.read_bytes() == prefix + EVENT
    assert stream.stat().st_mode & 0o777 == 0o640


def test_actual_owned_output_inventory_is_admitted_as_derived_not_authored(active, monkeypatch):
    repo, pinned = active
    outputs = continuation._derived_paths(pinned.repository_root)
    assert "odylith/index.html" in outputs
    assert "odylith/compass/compass-runtime-truth.v1.js" in outputs
    assert len(outputs) > 20
    layout = write_sets.greenfield_repository_layout(repo)

    def render(**kwargs):
        for token in outputs - {continuation._REQUEST_PATH}:
            _write(layout.target_path(token), b"owned generated output\n")
        _write(repo / "odylith/compass/runtime/history/2026-09-10.v1.json", b"owned daily history\n")
        return _success(repo, **kwargs)

    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", render)
    assert _run(repo) == 0
    assert (repo / "odylith/radar/source/keep.md").read_bytes() == b"reviewed\n"
    assert (repo / continuation.STREAM_PATH).read_bytes() == EVENT
    generations.require_greenfield_working_generation(repo)


@pytest.mark.parametrize("mutation", ["package_bytes", "package_mode", "new_code", "interpreter", "activation_mode", "verification", "selection", "bundle_template"])
def test_runtime_identity_binds_loaded_code_interpreter_selection_and_install(tmp_path, monkeypatch, mutation):
    repo = tmp_path / "repo"
    package = tmp_path / "installed/odylith"
    code = package / "__init__.py"
    executable = repo / ".odylith/runtime/versions/v1/bin/python"
    install = repo / ".odylith/install.json"
    verification = executable.parent.parent / "runtime-verification.v1.json"
    _write(code, b"# frozen package\n")
    _write(package / "bundle/assets/odylith/frontend.js", b"frozen template\n")
    _write(executable, b"frozen interpreter\n")
    _write(install, b'{}\n')
    _write(verification, b'{}\n')
    current = repo / ".odylith/runtime/current"
    current.symlink_to("versions/v1")
    monkeypatch.setattr(continuation.odylith, "__file__", str(code))
    monkeypatch.setattr(continuation.sys, "executable", str(executable))
    before = continuation._runtime_identity(repo)
    if mutation == "package_bytes":
        code.write_bytes(b"# changed package\n")
    elif mutation == "package_mode":
        code.chmod(0o600)
    elif mutation == "new_code":
        _write(package / "new_module.py", b"# changed\n")
    elif mutation == "interpreter":
        executable.write_bytes(b"changed interpreter\n")
    elif mutation == "activation_mode":
        install.chmod(0o600)
    elif mutation == "verification":
        verification.write_bytes(b'{"changed": true}\n')
    elif mutation == "selection":
        current.unlink()
        current.symlink_to("versions/../versions/v1")
    else:
        (package / "bundle/assets/odylith/frontend.js").write_bytes(b"changed template\n")
    assert continuation._runtime_identity(repo) != before


def _actual_engine(repo, monkeypatch, render):
    def prerequisites(fd):
        _write(repo / "odylith/casebook/bugs/INDEX.md", b"# Bugs\n")
        _write(repo / "odylith/radar/traceability-graph.v1.json", b"{}\n")
        return 0

    boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo, command_tokens=["synthetic-fixture-setup"], operation=prerequisites,
    )
    # Keep the real action/capture, foreground executor, finalizer, state writer,
    # and generation owners. Only expensive rendering is replaced.
    monkeypatch.setattr(refresh, "_render_request", render)
    monkeypatch.setattr(refresh, "_record_failed_live_payload", lambda **kwargs: None)


def test_actual_engine_terminal_success_publishes(active, monkeypatch, capfd):
    repo, _ = active
    _actual_engine(repo, monkeypatch, lambda **kwargs: None)
    result = _run(repo)
    state = refresh._load_state(repo_root=repo)
    assert state["status"] == "passed" and state["pid"] == 0
    assert result == 0
    assert not (repo / continuation.RECEIPT_PATH).exists()
    assert (generations.require_greenfield_working_generation(repo).repository_root / continuation.STREAM_PATH).read_bytes() == EVENT
    output = capfd.readouterr()
    assert output.out == output.err == ""


def test_actual_engine_failure_can_complete_without_append(active, monkeypatch):
    repo, _ = active
    attempts = []

    def render(**kwargs):
        attempts.append(True)
        _write(repo / "odylith/compass/runtime/current.v1.json", b"owned progress\n")
        if len(attempts) == 1:
            raise ValueError("synthetic renderer failure")

    _actual_engine(repo, monkeypatch, render)
    assert _run(repo) == 1
    state = refresh._load_state(repo_root=repo)
    assert state["status"] == "failed" and state["pid"] == 0
    assert _receipt(repo)["phase"] == "failed"
    assert _run(repo, complete=True) == 0
    assert attempts == [True, True]
    assert (repo / continuation.STREAM_PATH).read_bytes() == EVENT


def _finish_existing_wait(repo, monkeypatch, calls):
    # Only replace waiting time; use the actual finalizer and state writer.
    def finish(**kwargs):
        calls.append(kwargs)
        state = refresh._load_state(repo_root=repo)
        terminal = refresh._finalize_state(state, status="passed", rc=0, terminal_reason="")
        terminal = refresh._write_state(repo_root=repo, payload=terminal)
        return {"request_id": state["request_id"], "state": terminal,
                "coalesced": False, "rc": 0, "status": "passed"}

    monkeypatch.setattr(refresh, "_wait_for_terminal", finish)


def _running_request(repo, *, profile="shell-safe", mode="auto"):
    state = refresh._base_state(request_id="existing-request", requested_profile=profile,
                                requested_runtime_mode=mode, status="running")
    refresh._write_state(repo_root=repo, payload={**state, "pid": os.getpid()})


def test_actual_wait_branch_marks_existing_request_coalesced(tmp_path, monkeypatch):
    _running_request(tmp_path)
    calls = []
    _finish_existing_wait(tmp_path, monkeypatch, calls)
    monkeypatch.setattr(refresh, "_run_foreground_request", _no_render)
    result = refresh.run_refresh(repo_root=tmp_path, requested_profile="shell-safe", requested_runtime_mode="auto",
                                 wait=True, status_only=False, emit_output=False, skip_settlement=True)
    assert calls == [{"repo_root": tmp_path, "request_id": "existing-request", "settle_standup_maintenance": True}]
    assert result["coalesced"] is True
    assert result["state"]["pid"] == 0
    assert result["request_id"] == result["state"]["request_id"] == "existing-request"


def test_actual_new_foreground_request_is_not_coalesced(tmp_path, monkeypatch):
    monkeypatch.setattr(refresh, "_render_request", lambda **kwargs: None)
    result = refresh.run_refresh(repo_root=tmp_path, requested_profile="shell-safe", requested_runtime_mode="auto",
                                 wait=True, status_only=False, emit_output=False, skip_settlement=True)
    assert result["coalesced"] is False
    assert result["state"]["pid"] == 0
    assert result["request_id"] == result["state"]["request_id"]
    assert result["state"] == refresh._load_state(repo_root=tmp_path)


def test_actual_waited_foreign_request_cannot_complete_log(active, monkeypatch):
    repo, original = active
    _actual_engine(repo, monkeypatch, _no_render)
    original = generations.pin_active_greenfield_generation(repo)
    calls = []
    _finish_existing_wait(repo, monkeypatch, calls)
    real = refresh.run_refresh

    def race(**kwargs):
        _running_request(repo, profile=kwargs["requested_profile"], mode=kwargs["requested_runtime_mode"])
        return real(**kwargs)

    monkeypatch.setattr(refresh, "run_refresh", race)
    assert _run(repo) == 1
    assert len(calls) == 1
    assert _receipt(repo)["phase"] == "rendering"
    assert generations.pin_active_greenfield_generation(repo).write_set_hash == original.write_set_hash
    assert (repo / continuation.STREAM_PATH).read_bytes() == EVENT
    with pytest.raises(continuation.CompassLogContinuationError):
        _run(repo, complete=True)


@pytest.mark.parametrize("moment", ["during_render", "after_foreground"])
def test_actual_same_process_request_replacement_stays_closed(active, monkeypatch, moment):
    repo, original = active
    originating = []

    def render(**kwargs):
        originating.append(kwargs["request_id"])
        if moment == "during_render":
            _terminal(repo)

    _actual_engine(repo, monkeypatch, render)
    original = generations.pin_active_greenfield_generation(repo)
    real = refresh._run_foreground_request

    def replace_after(**kwargs):
        result = real(**kwargs)
        _terminal(repo)
        return result

    if moment == "after_foreground":
        monkeypatch.setattr(refresh, "_run_foreground_request", replace_after)
    assert _run(repo) == 1
    state = refresh._load_state(repo_root=repo)
    assert state["request_id"] != originating[0] and state["pid"] == 0
    assert _receipt(repo)["phase"] == "rendering"
    assert generations.pin_active_greenfield_generation(repo).write_set_hash == original.write_set_hash
    with pytest.raises(continuation.CompassLogContinuationError):
        _run(repo, complete=True)
    assert (repo / continuation.STREAM_PATH).read_bytes() == EVENT


@pytest.mark.parametrize("coalesced", [True, 0, None, "false", "missing"])
def test_actual_terminal_needs_explicit_false_coalesced_evidence(active, monkeypatch, coalesced):
    repo, _ = active
    _actual_engine(repo, monkeypatch, lambda **kwargs: None)
    real = refresh._run_foreground_request

    def changed_result(**kwargs):
        result = real(**kwargs)
        if coalesced == "missing":
            result.pop("coalesced")
        else:
            result["coalesced"] = coalesced
        return result

    monkeypatch.setattr(refresh, "_run_foreground_request", changed_result)
    assert _run(repo) == 1
    assert refresh._load_state(repo_root=repo)["status"] == "passed"
    assert _receipt(repo)["phase"] == "rendering"


def test_actual_mode_resolution_failure_can_complete(active, monkeypatch):
    repo, _ = active
    attempts = []
    _actual_engine(repo, monkeypatch, lambda **kwargs: attempts.append(True))
    real = refresh._resolve_runtime_mode

    def unavailable(**kwargs):
        raise refresh.CompassRefreshError("synthetic mode unavailable")

    monkeypatch.setattr(refresh, "_resolve_runtime_mode", unavailable)
    assert _run(repo) == 1
    state = refresh._load_state(repo_root=repo)
    assert state["pid"] == 0 and state["terminal_reason"] == "mode_resolution_failed"
    assert _receipt(repo)["phase"] == "failed"
    assert attempts == []
    monkeypatch.setattr(refresh, "_resolve_runtime_mode", real)
    assert _run(repo, complete=True) == 0
    assert attempts == [True]
    assert (repo / continuation.STREAM_PATH).read_bytes() == EVENT


@pytest.mark.parametrize("failure", ["nonzero", "exception", "oserror"])
@pytest.mark.parametrize("replace_request", [False, True])
def test_pre_request_failure_requires_unchanged_prior_request(active, monkeypatch, failure, replace_request):
    repo, _ = active
    _actual_engine(repo, monkeypatch, lambda **kwargs: None)
    boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo, command_tokens=["synthetic-prior-request"], operation=lambda fd: (_terminal(repo) or 0),
    )
    before = refresh._load_state(repo_root=repo)
    calls = []
    real = inputs.ensure_compass_dashboard_inputs

    def unavailable(**kwargs):
        calls.append(True)
        if replace_request:
            _terminal(repo)
        if failure == "exception":
            raise ValueError("synthetic pre-request failure")
        if failure == "oserror":
            raise OSError("synthetic pre-request failure")
        return {"rc": 7, "status": "failed", "detail": "synthetic prerequisite failure"}

    monkeypatch.setattr(inputs, "ensure_compass_dashboard_inputs", unavailable)
    if failure != "nonzero" and not replace_request:
        with pytest.raises((ValueError, OSError), match="pre-request"):
            _run(repo)
    else:
        assert _run(repo) == 1
    assert calls == [True]
    assert _receipt(repo)["phase"] == ("rendering" if replace_request else "failed")
    if replace_request:
        with pytest.raises(continuation.CompassLogContinuationError):
            _run(repo, complete=True)
    else:
        assert refresh._load_state(repo_root=repo) == before
        monkeypatch.setattr(inputs, "ensure_compass_dashboard_inputs", real)
        assert _run(repo, complete=True) == 0
    assert (repo / continuation.STREAM_PATH).read_bytes() == EVENT


def test_delivered_actual_result_is_snapshotted_before_later_mutation(active, monkeypatch):
    repo, _ = active
    _actual_engine(repo, monkeypatch, lambda **kwargs: None)
    real = continuation.owned_surface_refresh.raise_for_failed_refresh

    def observe(**kwargs):
        callback = kwargs["on_results"]

        def mutate_after_delivery(results):
            callback(results)
            results[0]["action_results"][0]["state"]["request_id"] = "mutated-after-delivery"

        return real(**{**kwargs, "on_results": mutate_after_delivery})

    monkeypatch.setattr(continuation.owned_surface_refresh, "raise_for_failed_refresh", observe)
    assert _run(repo) == 0
    assert refresh._load_state(repo_root=repo)["request_id"] != "mutated-after-delivery"


def test_capture_cleanup_after_actual_pass_completes_without_reentering_real_cache(active, monkeypatch):
    repo, original = active
    attempts = []

    def render(**kwargs):
        attempts.append(True)
        _write(repo / "odylith/compass/compass.html", b"<!doctype html><title>Rendered Compass</title>\n")

    _actual_engine(repo, monkeypatch, render)
    real_capture = continuation.owned_surface_refresh.tempfile.TemporaryFile
    original = generations.pin_active_greenfield_generation(repo)

    @contextmanager
    def failed_cleanup(**kwargs):
        with real_capture(**kwargs) as captured:
            yield captured
        raise OSError("synthetic capture cleanup failure")

    monkeypatch.setattr(continuation.owned_surface_refresh.tempfile, "TemporaryFile", failed_cleanup)
    with pytest.raises(OSError, match="capture cleanup"):
        _run(repo)
    assert attempts == [True]
    assert refresh._load_state(repo_root=repo)["status"] == "passed"
    assert _receipt(repo)["phase"] == "rendered"
    assert generations.pin_active_greenfield_generation(repo).write_set_hash == original.write_set_hash
    reusable, details = sync.surface_refresh_fingerprint_dag.can_reuse_surface_refresh(
        repo_root=repo, surface="compass", atlas_sync=False,
        outputs=sync.sync_generated_outputs.surface_render_outputs("compass", repo_root=repo),
    )
    assert reusable, details
    monkeypatch.setattr(continuation.owned_surface_refresh.tempfile, "TemporaryFile", real_capture)
    monkeypatch.setattr(continuation.owned_surface_refresh, "refresh_owned_surfaces", _no_render)
    monkeypatch.setattr(sync.surface_refresh_fingerprint_dag, "can_reuse_surface_refresh", _no_render)
    result = _run(repo, complete=True)
    assert attempts == [True]
    assert (repo / continuation.STREAM_PATH).read_bytes() == EVENT
    assert result == 0
    assert not (repo / continuation.RECEIPT_PATH).exists()
    generations.require_greenfield_working_generation(repo)


@pytest.mark.parametrize("field,value", [("rc", None), ("rc", "0"), ("rc", False), ("status", "failed")])
def test_partial_delivered_surface_result_stays_closed_even_after_pass(active, monkeypatch, field, value):
    repo, _ = active
    _actual_engine(repo, monkeypatch, lambda **kwargs: None)
    real = continuation.owned_surface_refresh.raise_for_failed_refresh

    def observe(**kwargs):
        callback = kwargs["on_results"]

        def partial_result(results):
            results[0][field] = value
            callback(results)
            raise OSError("synthetic cleanup after partial result")

        return real(**{**kwargs, "on_results": partial_result})

    monkeypatch.setattr(continuation.owned_surface_refresh, "raise_for_failed_refresh", observe)
    assert _run(repo) == 1
    assert refresh._load_state(repo_root=repo)["status"] == "passed"
    assert _receipt(repo)["phase"] == "rendering"
    with pytest.raises(continuation.CompassLogContinuationError):
        _run(repo, complete=True)


def test_actual_post_render_failure_without_delivered_result_stays_closed(active, monkeypatch):
    repo, _ = active
    attempts = []
    _actual_engine(repo, monkeypatch, lambda **kwargs: attempts.append(True))

    def fail_recording_surface(**kwargs):
        raise OSError("synthetic post-render fingerprint failure")

    monkeypatch.setattr(sync.surface_refresh_fingerprint_dag, "record_surface_refresh", fail_recording_surface)
    assert _run(repo) == 1
    assert refresh._load_state(repo_root=repo)["status"] == "passed"
    assert attempts == [True]
    assert _receipt(repo)["phase"] == "rendering"
    with pytest.raises(continuation.CompassLogContinuationError):
        _run(repo, complete=True)
    assert attempts == [True]
    assert (repo / continuation.STREAM_PATH).read_bytes() == EVENT


def test_cached_surface_without_executed_request_cannot_claim_completion(active, monkeypatch):
    repo, _ = active
    attempts = []
    _actual_engine(repo, monkeypatch, lambda **kwargs: attempts.append(True))
    with monkeypatch.context() as failure_patch:
        _failed(repo, failure_patch)
    monkeypatch.setattr(refresh, "_render_request", _no_render)
    monkeypatch.setattr(sync.surface_refresh_fingerprint_dag, "can_reuse_surface_refresh",
                        lambda **kwargs: (True, {"synthetic_existing_fingerprint": True}))
    assert _run(repo, complete=True) == 1
    assert _receipt(repo)["phase"] == "rendering"
    assert attempts == []
    assert (repo / continuation.STREAM_PATH).read_bytes() == EVENT
