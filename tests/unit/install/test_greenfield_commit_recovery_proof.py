from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _module():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    spec = importlib.util.spec_from_file_location(
        "greenfield_commit_recovery_proof_test",
        SCRIPTS_ROOT / "greenfield_commit_recovery_proof.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_faulted_create_uses_the_installed_runtime_without_source_path(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    runtime_python = tmp_path / ".odylith/runtime/current/bin/python"
    runtime_python.parent.mkdir(parents=True)
    runtime_python.touch()
    captured: dict[str, object] = {}

    def fake_run(**kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return SimpleNamespace(returncode=-9, stdout="", stderr="")

    monkeypatch.setattr(module, "_run", fake_run)
    result = module._run_faulted_create(
        repo_root=tmp_path,
        env={"PYTHONPATH": "/must-not-be-used", "PATH": "/usr/bin"},
        command=["./.odylith/bin/odylith", "greenfield", "create", "--confirm", "--json"],
        fault_script=module._SIGKILL_FAULT,  # noqa: SLF001
    )

    assert result.returncode == -9
    assert captured["command"][:5] == [
        str(runtime_python),
        "-I",
        "-c",
        module._SIGKILL_FAULT,  # noqa: SLF001
        "greenfield",
    ]
    assert "PYTHONPATH" not in captured["env"]


def test_installed_release_env_removes_maintainer_source_path(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(
        module,
        "_local_release_env",
        lambda **_kwargs: {"PYTHONPATH": "/maintainer/src", "ODYLITH_VERSION": "0.1.15"},
    )

    env = module._installed_release_env(base_url="http://127.0.0.1:8123", version="0.1.15")

    assert env == {"ODYLITH_VERSION": "0.1.15"}


def test_runtime_identity_requires_the_managed_installed_runtime(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    module_path = tmp_path / ".odylith/runtime/versions/0.1.15/lib/odylith/__init__.py"
    module_path.parent.mkdir(parents=True)
    module_path.touch()
    runtime_python = tmp_path / ".odylith/runtime/current/bin/python"
    runtime_python.parent.mkdir(parents=True)
    runtime_python.touch()
    monkeypatch.setattr(
        module,
        "_run",
        lambda **_kwargs: SimpleNamespace(
            returncode=0,
            stdout=f'{{"module_path": "{module_path}", "version": "0.1.15"}}',
            stderr="",
        ),
    )

    identity = module._installed_runtime_identity(  # noqa: SLF001
        repo_root=tmp_path,
        env={"PATH": "/usr/bin"},
        version="0.1.15",
    )

    assert identity == {
        "installed_runtime_module_path": str(module_path),
        "installed_runtime_version": "0.1.15",
    }


def test_runtime_identity_rejects_a_maintainer_source_import(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    runtime_python = tmp_path / ".odylith/runtime/current/bin/python"
    runtime_python.parent.mkdir(parents=True)
    runtime_python.touch()
    monkeypatch.setattr(
        module,
        "_run",
        lambda **_kwargs: SimpleNamespace(
            returncode=0,
            stdout='{"module_path": "/maintainer/src/odylith/__init__.py", "version": "0.1.15"}',
            stderr="",
        ),
    )

    try:
        module._installed_runtime_identity(  # noqa: SLF001
            repo_root=tmp_path,
            env={"PATH": "/usr/bin"},
            version="0.1.15",
        )
    except RuntimeError as exc:
        assert "outside its managed runtime" in str(exc)
    else:
        raise AssertionError("maintainer source import should fail installed-proof identity validation")


def test_receipt_identity_rejects_a_stale_or_unbound_success_payload() -> None:
    module = _module()
    payload = {
        "product_create_transaction": {"transaction_hash": "a" * 64},
        "commit_manifest": {
            "write_transaction": {
                "product_create_transaction_hash": "a" * 64,
                "repository_write_set_hash": "b" * 64,
            }
        },
    }

    module._require_receipt_identity(  # noqa: SLF001
        payload,
        transaction_hash="a" * 64,
        write_set_hash="b" * 64,
    )
    payload["commit_manifest"]["write_transaction"]["repository_write_set_hash"] = "c" * 64
    try:
        module._require_receipt_identity(  # noqa: SLF001
            payload,
            transaction_hash="a" * 64,
            write_set_hash="b" * 64,
        )
    except RuntimeError as exc:
        assert "sealed repository write set" in str(exc)
    else:
        raise AssertionError("receipt identity mismatch should fail the installed proof")


def test_recovery_proof_payload_is_a_falsifiable_release_record() -> None:
    module = _module()
    proof = module.GreenfieldInstalledCommitRecoveryProof(
        status="passed",
        issues=(),
        sigkill_returncode=-9,
        recovery_returncode=0,
        same_hash_retry_returncode=0,
        fsync_failure_returncode=2,
        fsync_retry_returncode=0,
        fsync_same_hash_retry_returncode=0,
        operator_conflict_returncode=2,
        journal_state_after_crash="applying",
        journal_state_after_recovery="committed",
        fsync_journal_state_after_failure="rolled_back",
        fsync_journal_state_after_retry="committed",
        fsync_failure_kind="post_confirm_commit_environment_or_io_failure",
        operator_conflict_failure_kind="post_confirm_commit_recovery_conflict",
        operator_conflict_rollback_status="not_started",
        operator_conflict_journal_state="applying",
        governed_write_observed_after_crash=True,
        operator_mutation_preserved=True,
        operator_conflict_snapshot_retained=True,
        operator_conflict_recovery_path_bound=True,
        installed_runtime_module_path="/tmp/repo/.odylith/runtime/versions/0.1.15/lib/odylith/__init__.py",
        installed_runtime_version="0.1.15",
    )

    assert proof.passed
    assert proof.to_dict() == {
        "status": "passed",
        "scope": "real_installed_additive_write_sigkill_recovery_conflict_same_hash_retry_and_fsync_rollback",
        "issues": [],
        "sigkill_returncode": -9,
        "recovery_returncode": 0,
        "same_hash_retry_returncode": 0,
        "fsync_failure_returncode": 2,
        "fsync_retry_returncode": 0,
        "fsync_same_hash_retry_returncode": 0,
        "operator_conflict_returncode": 2,
        "journal_state_after_crash": "applying",
        "journal_state_after_recovery": "committed",
        "fsync_journal_state_after_failure": "rolled_back",
        "fsync_journal_state_after_retry": "committed",
        "fsync_failure_kind": "post_confirm_commit_environment_or_io_failure",
        "operator_conflict_failure_kind": "post_confirm_commit_recovery_conflict",
        "operator_conflict_rollback_status": "not_started",
        "operator_conflict_journal_state": "applying",
        "governed_write_observed_after_crash": True,
        "operator_mutation_preserved": True,
        "operator_conflict_snapshot_retained": True,
        "operator_conflict_recovery_path_bound": True,
        "installed_runtime_module_path": "/tmp/repo/.odylith/runtime/versions/0.1.15/lib/odylith/__init__.py",
        "installed_runtime_version": "0.1.15",
    }


def test_recovery_proof_rejects_a_success_record_missing_required_observations() -> None:
    module = _module()

    issues = module._missing_required_evidence(  # noqa: SLF001
        {
            "sigkill_returncode": -9,
            "recovery_returncode": 0,
            "same_hash_retry_returncode": 0,
            "fsync_failure_returncode": 2,
            "fsync_retry_returncode": 0,
            "journal_state_after_crash": "applying",
            "journal_state_after_recovery": "committed",
            "fsync_journal_state_after_failure": "rolled_back",
            "fsync_failure_kind": "post_confirm_commit_environment_or_io_failure",
        }
    )

    assert "installed recovery proof did not observe a partial governed write before recovery" in issues
    assert "installed recovery proof did not record required fsync_same_hash_retry_returncode" in issues
    assert "installed recovery proof did not record required operator_conflict_returncode" in issues
    assert "installed recovery proof did not preserve the concurrent operator mutation" in issues
    assert "installed recovery proof did not retain the conflict recovery snapshot" in issues
    assert "installed recovery proof did not report the retained conflict recovery path" in issues
    assert "installed recovery proof did not record required installed_runtime_module_path" in issues


def test_installed_conflict_phase_preserves_operator_mutation_and_snapshot(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    repo_root = tmp_path / "operator-conflict"
    partial_write = repo_root / "odylith/radar/source/partial.md"
    transaction_hash = "a" * 64
    journal_root = module._journal_root(repo_root, transaction_hash)  # noqa: SLF001
    (journal_root / "snapshot").mkdir(parents=True)

    monkeypatch.setattr(module, "_install_repo", lambda **_kwargs: repo_root.mkdir(exist_ok=True))
    monkeypatch.setattr(
        module,
        "_compile_transaction",
        lambda **_kwargs: (".odylith/runtime/greenfield/product-create-transaction.v1.json", transaction_hash, "b" * 64),
    )

    def fake_faulted_create(**_kwargs):  # noqa: ANN001
        partial_write.parent.mkdir(parents=True, exist_ok=True)
        partial_write.write_text("sealed write before interruption\\n", encoding="utf-8")
        return SimpleNamespace(returncode=-9, stdout="", stderr="")

    monkeypatch.setattr(module, "_run_faulted_create", fake_faulted_create)
    monkeypatch.setattr(
        module,
        "_run",
        lambda **_kwargs: SimpleNamespace(
            returncode=2,
            stdout=(
                '{"mode":"error","commit_failure":{"failure_kind":"post_confirm_commit_recovery_conflict",'
                '"rollback_status":"not_started","recovery_path":"'
                + str(journal_root)
                + '"}}'
            ),
            stderr="",
        ),
    )
    monkeypatch.setattr(module, "_journal_state", lambda **_kwargs: {"state": "applying"})

    facts = module._run_operator_conflict_recovery_phase(  # noqa: SLF001
        run_root=tmp_path,
        install_script=tmp_path / "install.sh",
        env={"PATH": "/usr/bin"},
    )

    assert facts == {
        "operator_conflict_returncode": 2,
        "operator_conflict_failure_kind": "post_confirm_commit_recovery_conflict",
        "operator_conflict_rollback_status": "not_started",
        "operator_conflict_journal_state": "applying",
        "operator_mutation_preserved": True,
        "operator_conflict_snapshot_retained": True,
        "operator_conflict_recovery_path_bound": True,
    }
    assert partial_write.read_bytes() == b"operator mutation retained by installed recovery proof\n"


def test_interrupted_write_selector_ignores_unchanged_governed_files(tmp_path: Path) -> None:
    module = _module()
    unchanged = tmp_path / "odylith/radar/source/unchanged.md"
    changed = tmp_path / "odylith/radar/source/changed.md"
    unchanged.parent.mkdir(parents=True)
    unchanged.write_text("operator-owned before and after\n", encoding="utf-8")
    changed.write_text("sealed write after interruption\n", encoding="utf-8")

    selected = module._interrupted_governed_write_path(  # noqa: SLF001
        repo_root=tmp_path,
        before={
            "odylith/radar/source/unchanged.md": "same",
            "odylith/radar/source/changed.md": "before",
        },
        after={
            "odylith/radar/source/unchanged.md": "same",
            "odylith/radar/source/changed.md": "after",
        },
    )

    assert selected == changed
