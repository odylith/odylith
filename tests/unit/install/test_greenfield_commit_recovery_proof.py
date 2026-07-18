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
        journal_state_after_crash="applying",
        journal_state_after_recovery="committed",
        fsync_journal_state_after_failure="rolled_back",
        fsync_journal_state_after_retry="committed",
        fsync_failure_kind="post_confirm_commit_environment_or_io_failure",
        governed_write_observed_after_crash=True,
        installed_runtime_module_path="/tmp/repo/.odylith/runtime/versions/0.1.15/lib/odylith/__init__.py",
        installed_runtime_version="0.1.15",
    )

    assert proof.passed
    assert proof.to_dict() == {
        "status": "passed",
        "scope": "real_installed_additive_write_sigkill_same_hash_retry_and_fsync_rollback",
        "issues": [],
        "sigkill_returncode": -9,
        "recovery_returncode": 0,
        "same_hash_retry_returncode": 0,
        "fsync_failure_returncode": 2,
        "fsync_retry_returncode": 0,
        "fsync_same_hash_retry_returncode": 0,
        "journal_state_after_crash": "applying",
        "journal_state_after_recovery": "committed",
        "fsync_journal_state_after_failure": "rolled_back",
        "fsync_journal_state_after_retry": "committed",
        "fsync_failure_kind": "post_confirm_commit_environment_or_io_failure",
        "governed_write_observed_after_crash": True,
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
    assert "installed recovery proof did not record required installed_runtime_module_path" in issues
