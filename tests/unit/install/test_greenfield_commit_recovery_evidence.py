"""Recovery custody and narrow mutation retraction fail-closed controls."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import greenfield_commit_recovery_evidence as evidence
import greenfield_matrix_release_artifacts as artifacts


@pytest.mark.parametrize("outcome", ("success", "failure", "timeout"))
def test_proposal_custody_keeps_native_descriptor_and_raw_streams(tmp_path: Path, outcome: str) -> None:
    case = evidence.begin_proposal(output_dir=tmp_path / "evidence", temp_parent=tmp_path / "fixtures")
    captured = {}

    def runner(**arguments):
        captured.update(arguments)
        descriptor = int(arguments["env"]["ODYLITH_GREENFIELD_MODEL_PROOF_FD"])
        assert arguments["pass_fds"] == (descriptor,)
        os.write(descriptor, b'{"native":"observation"}\n')
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(arguments["command"], 150, output=b"partial\xff", stderr=b"timeout")
        return SimpleNamespace(returncode=0 if outcome == "success" else 2, stdout="raw stdout", stderr="raw stderr")

    args = dict(evidence=case, runner=runner, env={"PATH": "/usr/bin"}, command=["odylith", "greenfield", "propose"])
    if outcome == "timeout":
        with pytest.raises(subprocess.TimeoutExpired):
            evidence.run_proposal(**args)
        assert (case.staging_root / "commands/propose.stdout").read_bytes() == b"partial\xff"
        assert json.loads((case.staging_root / "commands/propose-error.json").read_text())["exception"] == "TimeoutExpired"
    else:
        result = evidence.run_proposal(**args)
        assert result.returncode == (0 if outcome == "success" else 2)
        assert (case.staging_root / "commands/propose.stdout").read_text() == "raw stdout"
        assert (case.staging_root / "commands/propose.stderr").read_text() == "raw stderr"
    assert (case.staging_root / "semantic/model-authoring-observation.v1.json").read_bytes() == b'{"native":"observation"}\n'
    with pytest.raises(OSError):
        os.fstat(captured["pass_fds"][0])


@pytest.mark.parametrize("mutation", ("none", "bytes", "mode", "inode", "symlink", "fifo"))
def test_retraction_only_accepts_exact_owned_file(tmp_path: Path, mutation: str) -> None:
    selected = tmp_path / "selected"
    original = b"exact post-crash bytes\x00\xff"
    injected = b"run-owned mutation"
    selected.write_bytes(original)
    original_stat = selected.stat()
    selected.write_bytes(injected)
    if mutation == "bytes":
        selected.write_bytes(b"another operator's work")
    elif mutation == "mode":
        selected.chmod(0o600 if original_stat.st_mode & 0o777 != 0o600 else 0o644)
    elif mutation == "inode":
        selected.rename(tmp_path / "previous-inode")
        selected.write_bytes(injected)
    elif mutation in {"symlink", "fifo"}:
        selected.rename(tmp_path / "previous-inode")
        if mutation == "symlink":
            selected.symlink_to(tmp_path / "previous-inode")
        else:
            os.mkfifo(selected)
    arguments = dict(path=selected, original_bytes=original, original_stat=original_stat, operator_bytes=injected)
    if mutation != "none":
        with pytest.raises(RuntimeError, match="symlink|regular file|identity or mode|unexpected mutation"):
            evidence.retract_injected_mutation(**arguments)
        if mutation in {"inode", "symlink"}:
            assert (tmp_path / "previous-inode").read_bytes() == injected
    else:
        evidence.retract_injected_mutation(**arguments)
        restored = selected.stat()
        assert selected.read_bytes() == original
        assert (restored.st_ino, restored.st_mode, restored.st_mtime_ns) == (
            original_stat.st_ino, original_stat.st_mode, original_stat.st_mtime_ns,
        )


@pytest.mark.parametrize("failure", ("none", "fsync", "tamper"))
def test_conflict_evidence_binds_snapshot_structure_before_retraction(tmp_path: Path, monkeypatch, failure: str) -> None:
    repo = tmp_path / "fixtures/repo"
    journal = repo / "journal"
    (journal / "snapshot/empty").mkdir(parents=True)
    (journal / "snapshot/data").write_bytes(b"snapshot\x00\xff")
    (journal / "state.v1.json").write_text('{"state":"projecting"}')
    selected = repo / "index.html"
    selected.write_bytes(b"original carrier")
    original_stat = selected.stat()
    selected.write_bytes(b"injection")
    proposal = evidence.begin_proposal(output_dir=tmp_path / "evidence", temp_parent=tmp_path / "fixtures")
    artifacts.record_retained_case_text(proposal, "commands/propose.stdout", "sealed")
    artifacts.record_retained_case_json(proposal, "semantic/transaction.json", {"transaction_hash": "a" * 64})
    evidence.finish_proposal(evidence=proposal, repo_root=repo, status="passed", issues=[])
    if failure == "fsync":
        monkeypatch.setattr(artifacts, "_fsync_tree", lambda _root: (_ for _ in ()).throw(OSError("fsync rejected")))
    arguments = dict(proposal=proposal, repo_root=repo, journal_root=journal, selected_path=selected,
        original_bytes=b"original carrier", original_stat=original_stat, operator_bytes=b"injection",
        result=SimpleNamespace(stdout='{"conflict":true}', stderr="raw stderr"),
        facts={"transaction_hash": "a" * 64}, binding={"transaction_hash": "a" * 64}, run_id="b" * 64)
    if failure == "fsync":
        with pytest.raises(OSError, match="fsync rejected"):
            evidence.seal_conflict(**arguments)
        staging = next(path for path in proposal.final_root.parent.iterdir() if path.name.endswith(".staging"))
        assert (staging / "recovery/pre-injection.bin").read_bytes() == b"original carrier"
    else:
        receipt, inventory = evidence.seal_conflict(**arguments)
        assert "snapshot/empty" in inventory
        assert inventory["snapshot/data"]["byte_count"] == 10
        assert inventory["snapshot/data"]["mode"] == (journal / "snapshot/data").stat().st_mode
        assert not evidence.retained_conflict_issues(receipt, expected_binding=arguments["binding"], run_id="b" * 64)
        assert evidence.retained_conflict_issues(receipt, run_id="c" * 64)
        assert evidence.retained_conflict_issues(receipt, expected_binding={"transaction_hash": "d" * 64})
        retained = proposal.final_root.parent / "operator-conflict/recovery/journal/snapshot/data"
        assert retained.read_bytes() == b"snapshot\x00\xff"
        if failure == "tamper":
            retained.write_bytes(b"changed")
            assert evidence.retained_conflict_issues(receipt)
    assert selected.read_bytes() == b"injection"
    assert (journal / "snapshot/data").read_bytes() == b"snapshot\x00\xff"


def test_journal_inventory_rejects_symlink_and_includes_empty_directories(tmp_path: Path) -> None:
    journal = tmp_path / "journal"
    (journal / "empty").mkdir(parents=True)
    assert set(evidence.journal_inventory(journal)) == {".", "empty"}
    (journal / "escape").symlink_to(tmp_path)
    with pytest.raises(RuntimeError, match="unsafe journal entry"):
        evidence.journal_inventory(journal)


def test_injection_rejects_replaced_path_before_writing(tmp_path: Path, monkeypatch) -> None:
    selected = tmp_path / "selected"
    selected.write_bytes(b"original")
    actual_replace = evidence._replace_selected_bytes

    def race(descriptor, path, payload, original_stat):
        path.rename(tmp_path / "old-inode")
        path.write_bytes(b"new operator truth")
        actual_replace(descriptor, path, payload, original_stat)

    monkeypatch.setattr(evidence, "_replace_selected_bytes", race)
    with pytest.raises(RuntimeError, match="identity or mode changed"):
        evidence.inject_operator_mutation(path=selected, operator_bytes=b"injected")
    assert selected.read_bytes() == b"new operator truth"
    assert (tmp_path / "old-inode").read_bytes() == b"original"


def test_interrupted_wrapper_preserves_fixture_even_without_nonterminal_journal(tmp_path: Path, monkeypatch) -> None:
    from tests.unit.install.test_greenfield_commit_recovery_proof import _module
    module = _module()
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "install.sh").write_text("install stub")
    server = SimpleNamespace(shutdown=lambda: None, server_close=lambda: None)
    monkeypatch.setattr(module, "_serve_directory", lambda _path: (server, "http://127.0.0.1"))
    monkeypatch.setattr(module, "_installed_release_env", lambda **_kwargs: {})
    def interrupted_seed(**kwargs):
        (kwargs["run_root"] / "required-diagnostic").write_bytes(b"retain me")
        raise KeyboardInterrupt()
    monkeypatch.setattr(module, "_prepare_recovery_seed", interrupted_seed)
    with pytest.raises(KeyboardInterrupt):
        module.run_installed_commit_recovery_proof(
            dist_dir=dist, version="0.1.15", temp_parent=tmp_path / "fixtures",
            evidence_output_dir=tmp_path / "evidence",
            recovery_case=module.GreenfieldMatrixCase(name="case", prompt="Create a product.", required_terms=()),
        )
    retained = tuple((tmp_path / "fixtures").glob("*/required-diagnostic"))
    assert len(retained) == 1 and retained[0].read_bytes() == b"retain me"


def test_matrix_rejects_missing_recovery_evidence_before_product_execution(monkeypatch) -> None:
    from tests.unit.install.test_greenfield_preconfirm_matrix_proof_scope import _module
    module = _module()
    monkeypatch.setattr(module, "run_matrix", lambda **_kwargs: pytest.fail("must reject before execution"))
    with pytest.raises(RuntimeError, match="commit recovery proof requires --evidence-output-dir"):
        module.main(["--dist-dir", "/unused", "--include-commit-recovery-proof", "--json"])
