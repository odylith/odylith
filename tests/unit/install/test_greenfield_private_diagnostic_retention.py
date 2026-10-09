"""Private returned-stream custody under the existing prepare deadline and refusal laws."""
from __future__ import annotations

from argparse import Namespace
import errno
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

import pytest

from odylith.runtime.domain_intelligence import greenfield_host_flow as host
from odylith.runtime.domain_intelligence import greenfield_prepare_cli as prepare
from odylith.runtime.domain_intelligence.greenfield_authority_gate import greenfield_authority_gate_contract
from odylith.runtime.domain_intelligence.greenfield_process import (
    CommandLifecycleObserverError, GroupTimeoutCompletedProcess,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_compact import expand_compact_source_duty_ledger
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import preflight_greenfield_source_duty_ledger
from tests.unit.install.test_greenfield_matrix_host_candidate import _flow


def _prepare_fixture(tmp_path, monkeypatch, *, diagnostic=True, failure=None, clock=None):
    raw = "Original request ∆\r\n"
    source = "First Complete Path: A reviewer creates a reviewable plan. Reference: Notes are background only.\r\n∆"
    flow, original_host, installed_calls, host_calls, proposals, repo = _flow(
        tmp_path, candidate={"result": {"status": "authored"}},
        contract={"request": {"evidence": source}, "authority_gate": greenfield_authority_gate_contract(
            prompt=raw, edit_evidence="", evidence_source=source,
        )},
    )
    destination = tmp_path / "private-diagnostic"
    args = Namespace(repo_root=str(repo), prompt=raw, edit=None, edit_evidence=None,
        transaction_hash=None, completion_receipt="", release="",
        diagnostic_evidence_dir=str(destination) if diagnostic else "")
    emitted, captured = {}, []

    def invoke(**kwargs):
        command = list(kwargs["command"])
        stage = command[command.index("greenfield") + 1]
        if stage == "candidate-contract":
            stage = "contract"
        if stage == "propose":
            result = flow.invoke_propose(*[Path(command[command.index(flag) + 1])
                for flag in ("--candidate-file", "--gate-file", "--ledger-file")], kwargs["timeout"])
            stage = "proposal"
        else:
            if stage == "source-ledger-check" and "--decision-file" not in command:
                stage = "source-ledger-preflight"
            if stage == "source-ledger-preflight" and failure == "atomic":
                ledger = json.loads(Path(command[command.index("--ledger-file") + 1]).read_bytes())
                with pytest.raises(ValueError) as refused:
                    preflight_greenfield_source_duty_ledger(
                        expand_compact_source_duty_ledger(ledger, evidence_text=source), evidence_text=source)
                result = subprocess.CompletedProcess(command, 2, json.dumps({"mode": "error", "error": str(refused.value)}), "")
            else:
                result = flow.invoke_installed(command, kwargs["timeout"])
        if stage == failure:
            result = subprocess.CompletedProcess(command, 2,
                stdout=' \n{"mode":"error","error":"controlled refusal"}\n',
                stderr="returned private checker ∆\r\n")
        else:
            result.stderr = "private returned " + stage + " ∆\r\n"
        emitted[stage] = result
        if clock is not None and stage == failure:
            clock[0] = 660.0
        return result

    def invoke_host(command, **kwargs):
        result = original_host(command, **kwargs)
        result.stderr = "private model stream ∆\r\n"
        stage = {"authority-gate-schema.json": "authority-gate",
                 "source-ledger-schema.json": "source-ledger",
                 "source-duty-decision-schema.json": "source-duty-verifier"}.get(
                     Path(command[command.index("--output-schema") + 1]).name, "candidate")
        if stage == "source-ledger" and failure == "atomic":
            ledger = json.loads(result.stdout)
            ledger["first_path_actions"][0]["actor_ref"] = ledger["first_path_actions"][0]["event_ref"]
            result.stdout = json.dumps(ledger, ensure_ascii=False) + "\n"
        emitted[stage] = result
        return result

    original_flow = prepare.run_host_candidate_flow
    def run(value):
        captured.append(value)
        return original_flow(value)
    monkeypatch.setattr(prepare, "resolve_trusted_codex_executable", lambda **_: flow.trusted_codex_executable)
    monkeypatch.setattr(prepare, "run_command_with_group_timeout", invoke)
    monkeypatch.setattr(prepare, "run_host_candidate_flow", run)
    monkeypatch.setattr(host, "_invoke_host", invoke_host)
    return args, destination, emitted, captured, installed_calls, host_calls, proposals, repo


def _index(directory):
    return json.loads((directory / "artifact-index.json").read_bytes())


def test_option_absent_keeps_callbacks_and_output_clean(tmp_path, monkeypatch):
    args, directory, _, captured, _, hosts, proposals, repo = _prepare_fixture(
        tmp_path, monkeypatch, diagnostic=False)
    payload, observation = prepare.prepare_request(args)
    assert payload == {"mode": "product_create_transaction"}
    assert observation["status"] == "passed" and len(hosts) == 4 and len(proposals) == 1
    assert captured[0].retain_diagnostic_bytes is None and captured[0].observe is None
    assert captured[0].retain_host_stderr_bytes is None
    assert not directory.exists() and list(repo.iterdir()) == []


def test_private_custody_binds_actual_stdin_schema_and_returned_utf8(tmp_path, monkeypatch):
    args, directory, emitted, _, _, hosts, proposals, repo = _prepare_fixture(tmp_path, monkeypatch)
    payload, observation = prepare.prepare_request(args)
    assert payload == {"mode": "product_create_transaction"} and observation["status"] == "passed"
    assert len(hosts) == 4 and len(proposals) == 1 and list(repo.iterdir()) == []
    assert (directory / "operator-request.exact.txt").read_bytes() == args.prompt.encode()
    assert (directory / "correction.exact.txt").read_bytes() == b""
    assert (directory / "compiler-source.exact.txt").read_bytes() != args.prompt.encode()
    assert (directory / "compiler-source.exact.txt").read_bytes().endswith("\r\n∆".encode())
    for stage, result in emitted.items():
        for stream in ("stdout", "stderr"):
            assert (directory / (stage + "." + stream)).read_bytes() == getattr(result, stream).encode()
    for stage, position, schema_name in (
        ("authority-gate", 0, "authority-gate-schema.json"),
        ("source-ledger", 1, "source-ledger-schema.json"),
        ("source-duty-verifier", 2, "source-duty-decision-schema.json"),
        ("candidate", 3, "candidate-schema.json"),
    ):
        assert (directory / (stage + ".stdin.json")).read_bytes() == hosts[position][1].encode()
        schema = json.loads((directory / schema_name).read_bytes())
        stdin = json.loads(hosts[position][1])
        expected_schema = {
            0: json.loads(emitted["contract"].stdout)["authority_gate"]["response_schema"],
            1: json.loads(emitted["contract"].stdout)["source_ledger"]["source_ledger_schema"],
            2: json.loads(hosts[2][1])["decision_set_schema"],
            3: json.loads(emitted["contract"].stdout)["candidate_schema"],
        }
        assert schema == expected_schema[position]
        if position == 1:
            assert "source_ledger_schema" not in stdin["source_ledger"]
            assert hashlib.sha256((directory / schema_name).read_bytes()).hexdigest() == observation["source_ledger_schema_sha256"]
    index = _index(directory)
    assert index["authority"] == "none" and index["status"] == "retained_through_returned_stage"
    assert "not pipe octets" in index["representation"]
    assert index["journey_completion"] == "not certified by this index"
    for name, entry in index["artifacts"].items():
        body = (directory / name).read_bytes()
        assert entry == {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in directory.iterdir())
    assert "private model stream" not in json.dumps(observation)


@pytest.mark.parametrize("kind", ["relative", "existing-dir", "existing-file", "symlink", "inside", "parent-symlink"])
def test_invalid_destination_refuses_before_flow_and_preserves_previous_bytes(tmp_path, monkeypatch, kind):
    args, directory, _, captured, installed, hosts, _, repo = _prepare_fixture(tmp_path, monkeypatch)
    if kind == "relative":
        args.diagnostic_evidence_dir = "private-diagnostic"
    elif kind == "existing-dir":
        directory.mkdir(); (directory / "old").write_bytes(b"old evidence")
    elif kind == "existing-file":
        directory.write_bytes(b"old evidence")
    elif kind == "symlink":
        directory.symlink_to(tmp_path / "missing")
    elif kind == "inside":
        args.diagnostic_evidence_dir = str(repo / "private")
    else:
        linked = tmp_path / "linked"; linked.symlink_to(repo, target_is_directory=True)
        args.diagnostic_evidence_dir = str(linked / "private")
    with pytest.raises(ValueError, match="new absolute directory outside"):
        prepare.prepare_request(args)
    assert captured == installed == hosts == []
    if kind == "existing-dir":
        assert (directory / "old").read_bytes() == b"old evidence"
    elif kind == "existing-file":
        assert directory.read_bytes() == b"old evidence"
    assert not (repo / "private").exists()


@pytest.mark.parametrize("stage,passes", [("source-ledger-preflight", 2), ("source-ledger-check", 3)])
def test_denial_retains_both_returned_streams_before_cleanup_without_candidate(tmp_path, monkeypatch, stage, passes):
    args, directory, emitted, _, _, hosts, proposals, repo = _prepare_fixture(
        tmp_path, monkeypatch, failure=stage)
    with pytest.raises(host.HostCandidateFlowError) as refused:
        prepare.prepare_request(args)
    assert len(hosts) == passes and proposals == [] and list(repo.iterdir()) == []
    assert refused.value.observation["candidate_host_invocations"] == 0
    assert refused.value.observation["host_workspace_cleaned"] is True
    for stream in ("stdout", "stderr"):
        assert (directory / (stage + "." + stream)).read_bytes() == getattr(emitted[stage], stream).encode()
    assert not (directory / "candidate.stdout").exists()
    assert _index(directory)["authority"] == "none"
    if passes == 3:
        assert (directory / "source-duty-verifier.stdin.json").read_bytes() == hosts[2][1].encode()
        assert (directory / "source-duty-verifier.stdout").read_bytes() == emitted["source-duty-verifier"].stdout.encode()


@pytest.mark.parametrize("stage,passes", [("source-ledger-preflight", 2), ("source-ledger-check", 3)])
def test_late_installed_return_keeps_streams_then_refuses_under_original_clock(tmp_path, monkeypatch, stage, passes):
    clock = [0.0]
    args, directory, emitted, _, _, hosts, proposals, _ = _prepare_fixture(
        tmp_path, monkeypatch, failure=stage, clock=clock)
    monkeypatch.setattr(host.time, "monotonic", lambda: clock[0])
    with pytest.raises(host.HostCandidateFlowError) as refused:
        prepare.prepare_request(args)
    observation = refused.value.observation
    assert observation["whole_journey_deadline_status"] == "expired"
    assert observation["whole_journey_seconds"] == 660.0 and observation["status"] == "failed"
    assert observation["candidate_host_invocations"] == 0 and len(hosts) == passes and proposals == []
    for stream in ("stdout", "stderr"):
        assert (directory / (stage + "." + stream)).read_bytes() == getattr(emitted[stage], stream).encode()


@pytest.mark.parametrize("artifact,passes", [
    ("operator-request.exact.txt", 0), ("source-ledger.stdin.json", 1),
    ("source-ledger.stdout", 2), ("source-ledger-preflight.stderr", 2),
    ("source-duty-verifier.stdout", 3), ("source-ledger-check.stdout", 3),
])
def test_artifact_creation_failure_is_incomplete_and_stops_next_model(tmp_path, monkeypatch, artifact, passes):
    args, directory, _, _, _, hosts, proposals, _ = _prepare_fixture(tmp_path, monkeypatch)
    original_open = os.open
    def fail(path, flags, *rest, **kwargs):
        if str(path) == artifact:
            raise OSError(errno.ENOSPC, "controlled retention failure")
        return original_open(path, flags, *rest, **kwargs)
    monkeypatch.setattr(prepare.os, "open", fail)
    with pytest.raises(host.HostCandidateFlowError) as refused:
        prepare.prepare_request(args)
    assert refused.value.observation["status"] == "failed"
    assert refused.value.observation["candidate_host_invocations"] == 0
    assert len(hosts) == passes and proposals == []
    index = _index(directory)
    assert index["status"] == "incomplete"
    assert index["retention_failures"] == [{"artifact": artifact, "error_type": "OSError"}]
    assert artifact not in index["artifacts"]


def test_partial_file_failure_is_not_overwritten_or_indexed_as_complete(tmp_path, monkeypatch):
    repo = tmp_path / "consumer"; repo.mkdir()
    directory = tmp_path / "private"
    retain, observe = prepare._diagnostic_retention(str(directory), repo_root=repo)
    assert not directory.exists()
    original_fdopen = os.fdopen
    class Partial:
        def __init__(self, stream): self.stream = stream
        def __enter__(self): return self
        def __exit__(self, *args): return self.stream.__exit__(*args)
        def write(self, data):
            self.stream.write(data[:2])
            raise OSError(errno.ENOSPC, "controlled partial write")
    monkeypatch.setattr(prepare.os, "fdopen", lambda fd, *args, **kwargs: Partial(original_fdopen(fd, *args, **kwargs)))
    with pytest.raises(OSError): retain("source-ledger.stdout", b"abcdef")
    assert (directory / "source-ledger.stdout").read_bytes() == b"ab"
    monkeypatch.setattr(prepare.os, "fdopen", original_fdopen)
    observe({"status": "failed"})
    index = _index(directory)
    assert index["status"] == "incomplete" and "source-ledger.stdout" not in index["artifacts"]
    assert (directory / "source-ledger.stdout").read_bytes() == b"ab"


@pytest.mark.parametrize("boundary", ["artifact-fsync", "index-create", "directory-fsync"])
def test_fsync_or_index_error_prevents_successful_flow(tmp_path, monkeypatch, boundary):
    args, directory, _, _, _, hosts, proposals, _ = _prepare_fixture(tmp_path, monkeypatch)
    original_fsync, original_open = os.fsync, os.open
    def fail_fsync(fd):
        if (boundary == "artifact-fsync" or
                boundary == "directory-fsync" and stat.S_ISDIR(os.fstat(fd).st_mode)):
            raise OSError(errno.EIO, "controlled diagnostic fsync failure")
        return original_fsync(fd)
    def fail_open(path, flags, *rest, **kwargs):
        if boundary == "index-create" and str(path) == "artifact-index.json":
            raise OSError(errno.ENOSPC, "controlled index failure")
        return original_open(path, flags, *rest, **kwargs)
    monkeypatch.setattr(prepare.os, "fsync", fail_fsync)
    monkeypatch.setattr(prepare.os, "open", fail_open)
    with pytest.raises(host.HostCandidateFlowError) as refused:
        prepare.prepare_request(args)
    assert refused.value.observation["status"] == "failed"
    if boundary == "artifact-fsync":
        assert hosts == [] and proposals == [] and not (directory / "artifact-index.json").exists()
    else:
        assert len(hosts) == 4 and len(proposals) == 1
        assert refused.value.observation["observer_error"] == "OSError"
        assert refused.value.observation["host_workspace_cleaned"] is True
        if boundary == "index-create": assert not (directory / "artifact-index.json").exists()
        else: assert _index(directory)["journey_completion"] == "not certified by this index"


def test_timeout_and_lifecycle_error_results_are_retained_without_parsing(tmp_path, monkeypatch):
    args, directory, _, _, installed, hosts, proposals, _ = _prepare_fixture(tmp_path, monkeypatch)
    def timeout(**kwargs):
        result = GroupTimeoutCompletedProcess(kwargs["command"], 124,
            stdout="private timeout output ∆\r\n", stderr="partial stderr\ntermination note",
            termination_observation="output_pipes_closed_after_sigterm")
        raise CommandLifecycleObserverError(command=kwargs["command"], result=result, state="timed_out")
    monkeypatch.setattr(prepare, "run_command_with_group_timeout", timeout)
    with pytest.raises(CommandLifecycleObserverError):
        prepare.prepare_request(args)
    assert (directory / "contract.stdout").read_bytes() == "private timeout output ∆\r\n".encode()
    assert (directory / "contract.stderr").read_bytes() == b"partial stderr\ntermination note"
    assert installed == hosts == proposals == []
    assert _index(directory)["authority"] == "none"


@pytest.mark.parametrize("after_first_artifact", [False, True])
def test_parent_retargeting_cannot_write_in_consumer(tmp_path, after_first_artifact):
    repo = tmp_path / "consumer"; repo.mkdir()
    parent = tmp_path / "validated-parent"; parent.mkdir()
    retain, _observe = prepare._diagnostic_retention(str(parent / "private"), repo_root=repo)
    if after_first_artifact:
        retain("operator-request.exact.txt", b"first private input")
    original = tmp_path / "original-parent"
    parent.rename(original)
    parent.symlink_to(repo, target_is_directory=True)
    with pytest.raises((OSError, ValueError)):
        retain("source-ledger.stdout", b"must never enter consumer")
    assert list(repo.iterdir()) == []
    assert not (original / "private" / "source-ledger.stdout").exists()
    if after_first_artifact:
        assert (original / "private" / "operator-request.exact.txt").read_bytes() == b"first private input"
        with pytest.raises((OSError, ValueError)):
            _observe({"status": "failed"})


def test_replaced_destination_is_not_followed_by_descriptor_writer(tmp_path):
    repo = tmp_path / "consumer"; repo.mkdir()
    directory = tmp_path / "private"
    retain, _observe = prepare._diagnostic_retention(str(directory), repo_root=repo)
    retain("operator-request.exact.txt", b"first")
    original = tmp_path / "original-evidence"
    directory.rename(original)
    directory.symlink_to(repo, target_is_directory=True)
    with pytest.raises(ValueError, match="destination changed"):
        retain("source-ledger.stdout", b"must never enter consumer")
    assert list(repo.iterdir()) == []
    assert (original / "operator-request.exact.txt").read_bytes() == b"first"
    with pytest.raises(ValueError):
        _observe({"status": "failed"})


def test_actual_atomic_actor_refusal_keeps_raw_inventory_without_verifier_or_candidate(tmp_path, monkeypatch):
    args, directory, emitted, _, _, hosts, proposals, repo = _prepare_fixture(
        tmp_path, monkeypatch, failure="atomic")
    with pytest.raises(host.HostCandidateFlowError) as refused:
        prepare.prepare_request(args)
    assert refused.value.observation["stage"] == "source-ledger-preflight"
    assert refused.value.observation["source_duty_verifier_host_invocations"] == 0
    assert refused.value.observation["candidate_host_invocations"] == 0
    assert len(hosts) == 2 and proposals == [] and list(repo.iterdir()) == []
    assert (directory / "source-ledger.stdout").read_bytes() == emitted["source-ledger"].stdout.encode()
    assert "actor" in json.loads((directory / "source-ledger-preflight.stdout").read_bytes())["error"]


def test_supported_option_keeps_private_model_payload_out_of_normal_error_output(tmp_path, monkeypatch, capsys):
    args, directory, _, _, _, hosts, proposals, _ = _prepare_fixture(tmp_path, monkeypatch)
    private = "unparsed private model payload ∆\r\n"
    def refuse(command, **kwargs):
        return subprocess.CompletedProcess(command, 2, private, "private provider stderr\r\n")
    monkeypatch.setattr(host, "_invoke_host", refuse)
    assert prepare.main(["--repo-root", args.repo_root, "--prompt", args.prompt,
                         "--diagnostic-evidence-dir", str(directory), "--format", "json"]) == 2
    printed = capsys.readouterr().out
    assert "private model payload" not in printed and "private provider stderr" not in printed
    assert json.loads(printed)["mode"] == "error"
    assert (directory / "authority-gate.stdout").read_bytes() == private.encode()
    assert (directory / "authority-gate.stderr").read_bytes() == b"private provider stderr\r\n"
    assert hosts == [] and proposals == []


def test_parent_retarget_during_lazy_mkdir_uses_pinned_descriptor_and_fails_closed(tmp_path, monkeypatch):
    repo = tmp_path / "consumer"; repo.mkdir()
    parent = tmp_path / "parent"; parent.mkdir()
    original = tmp_path / "original-parent"
    retain, observe = prepare._diagnostic_retention(str(parent / "private"), repo_root=repo)
    original_mkdir = os.mkdir
    def retarget(path, *args, **kwargs):
        if path == "private":
            parent.rename(original)
            parent.symlink_to(repo, target_is_directory=True)
        return original_mkdir(path, *args, **kwargs)
    monkeypatch.setattr(prepare.os, "mkdir", retarget)
    with pytest.raises(ValueError, match="parent changed"):
        retain("operator-request.exact.txt", b"must not enter consumer")
    assert list(repo.iterdir()) == []
    assert list((original / "private").iterdir()) == []
    with pytest.raises(OSError): observe({"status": "failed"})


def test_observed_leaf_substitution_refuses_old_evidence_before_any_dispatch(tmp_path, monkeypatch):
    args, directory, _, captured, installed, hosts, proposals, repo = _prepare_fixture(tmp_path, monkeypatch)
    previous = tmp_path / "previous-attempt"; previous.mkdir(mode=0o750)
    (previous / "old-marker").write_bytes(b"preserve previous evidence")
    previous_mode = stat.S_IMODE(previous.stat().st_mode)
    orphan = tmp_path / "created-orphan"
    original_open = os.open
    opened = []
    def substitute(path, flags, *rest, **kwargs):
        if path == directory.name and flags & os.O_DIRECTORY and not opened:
            directory.rename(orphan)
            previous.rename(directory)
            fd = original_open(path, flags, *rest, **kwargs)
            opened.append(fd)
            return fd
        return original_open(path, flags, *rest, **kwargs)
    monkeypatch.setattr(prepare.os, "open", substitute)
    with pytest.raises(host.HostCandidateFlowError) as refused:
        prepare.prepare_request(args)
    assert installed == hosts == proposals == [] and list(repo.iterdir()) == []
    assert refused.value.observation["status"] == "failed"
    assert refused.value.observation["candidate_host_invocations"] == 0
    assert captured[0].completion_receipt_sink == {}
    assert list(orphan.iterdir()) == []
    assert [p.name for p in directory.iterdir()] == ["old-marker"]
    assert (directory / "old-marker").read_bytes() == b"preserve previous evidence"
    assert stat.S_IMODE(directory.stat().st_mode) == previous_mode
    with pytest.raises(OSError) as closed:
        os.fstat(opened[0])
    assert closed.value.errno == errno.EBADF


@pytest.mark.parametrize("artifact,passes", [("operator-request.exact.txt", 0), ("source-ledger.stdout", 2)])
@pytest.mark.parametrize("boundary", ["artifact-open", "artifact-fsync"])
def test_external_reparent_detected_after_write_stops_later_dispatch_and_receipt(
        tmp_path, monkeypatch, artifact, passes, boundary):
    args, directory, emitted, captured, installed, hosts, proposals, repo = _prepare_fixture(tmp_path, monkeypatch)
    moved = repo / "externally-moved-private"
    original_open, original_fsync = os.open, os.fsync
    def reparent_open(path, flags, *rest, **kwargs):
        if boundary == "artifact-open" and path == artifact:
            directory.rename(moved)
        return original_open(path, flags, *rest, **kwargs)
    def reparent_fsync(fd):
        original_fsync(fd)
        named = directory / artifact
        if boundary == "artifact-fsync" and named.exists():
            pinned, current = os.fstat(fd), named.stat()
            if (pinned.st_dev, pinned.st_ino) == (current.st_dev, current.st_ino):
                directory.rename(moved)
    monkeypatch.setattr(prepare.os, "open", reparent_open)
    monkeypatch.setattr(prepare.os, "fsync", reparent_fsync)
    with pytest.raises(host.HostCandidateFlowError) as refused:
        prepare.prepare_request(args)
    observation = refused.value.observation
    assert observation["status"] == "failed" and observation["host_workspace_cleaned"] is True
    assert observation["source_duty_verifier_host_invocations"] == 0
    assert observation["candidate_host_invocations"] == observation["proposal_command_invocations"] == 0
    assert len(hosts) == passes and proposals == [] and captured[0].completion_receipt_sink == {}
    if passes == 0:
        assert installed == []
        expected = args.prompt.encode()
    else:
        assert "source-ledger-preflight" not in emitted
        expected = emitted["source-ledger"].stdout.encode()
    # External renames can move the pinned inode into the consumer before detection.
    assert (moved / artifact).read_bytes() == expected
    assert list(repo.iterdir()) == [moved] and not directory.exists()
    assert not (moved / "artifact-index.json").exists()
    assert not (moved / "candidate.stdout").exists()


def test_external_reparent_after_final_directory_fsync_prevents_receipt_delivery(tmp_path, monkeypatch):
    args, directory, _, captured, _, hosts, proposals, repo = _prepare_fixture(tmp_path, monkeypatch)
    moved = repo / "externally-moved-private"
    original_fsync = os.fsync
    def reparent(fd):
        original_fsync(fd)
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            directory.rename(moved)
    monkeypatch.setattr(prepare.os, "fsync", reparent)
    with pytest.raises(host.HostCandidateFlowError) as refused:
        prepare.prepare_request(args)
    assert len(hosts) == 4 and len(proposals) == 1
    assert refused.value.observation["status"] == "failed"
    assert refused.value.observation["observer_error"] == "FileNotFoundError"
    assert captured[0].completion_receipt_sink == {} and list(repo.iterdir()) == [moved]
    assert _index(moved)["journey_completion"] == "not certified by this index"


def test_oversized_model_stderr_preserves_existing_bound_and_marks_evidence_incomplete(tmp_path, monkeypatch):
    args, directory, _, _, _, hosts, proposals, _ = _prepare_fixture(tmp_path, monkeypatch)
    stderr = "x" * (256 * 1024 + 1)
    monkeypatch.setattr(host, "_invoke_host", lambda command, **kwargs:
        subprocess.CompletedProcess(command, 124, "private partial stdout", stderr))
    with pytest.raises(host.HostCandidateFlowError) as refused:
        prepare.prepare_request(args)
    proof = refused.value.observation["host_command_diagnostic"]
    assert proof["stderr_retention_status"] == "rejected_over_bound"
    assert proof["stderr_sha256"] == hashlib.sha256(stderr.encode()).hexdigest()
    assert (directory / "authority-gate.stdout").read_bytes() == b"private partial stdout"
    assert not (directory / "authority-gate.stderr").exists()
    assert _index(directory)["status"] == "incomplete" and hosts == [] and proposals == []


@pytest.mark.parametrize("diagnostic", [False, True])
def test_text_refusal_is_concise_and_diagnostic_option_shows_only_destination(tmp_path, monkeypatch, capsys, diagnostic):
    raw_detail = '{"mode":"error","error":"decision_set_schema parser says malformed source refs"}'
    observation = {"stage": "source-ledger-check", "detail": raw_detail,
                   "candidate_host_invocations": 0, "proposal_command_invocations": 0}
    def refused(_args):
        raise host.HostCandidateFlowError("controlled refusal", observation=observation)
    monkeypatch.setattr(prepare, "prepare_request", refused)
    argv = ["--repo-root", str(tmp_path), "--prompt", "Declared controlled request"]
    destination = tmp_path / "private"
    if diagnostic: argv.extend(["--diagnostic-evidence-dir", str(destination)])
    assert prepare.main(argv) == 2
    text = capsys.readouterr().out
    assert text.startswith("Greenfield preparation stopped during source inventory verification before publication.\n")
    assert "decision_set_schema" not in text and "parser" not in text and raw_detail not in text
    assert "Checker detail" not in text
    assert observation["detail"] == raw_detail and not destination.exists()
    if diagnostic:
        assert str(destination) in text and "non-authoritative" in text
    else:
        assert len(text.splitlines()) == 1
