from __future__ import annotations

import importlib.util
import json
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
        "product_create_transaction": {
            "transaction_hash": "a" * 64,
            "product_facts_sha256": "c" * 64,
        },
        "commit_manifest": {
            "product_create_transaction": {"product_facts_sha256": "c" * 64},
            "write_transaction": {
                "product_create_transaction_hash": "a" * 64,
                "product_facts_sha256": "c" * 64,
                "repository_write_set_hash": "b" * 64,
            }
        },
    }

    module._require_receipt_identity(  # noqa: SLF001
        payload,
        transaction_hash="a" * 64,
        product_facts_hash="c" * 64,
        write_set_hash="b" * 64,
    )
    payload["product_create_transaction"]["product_facts_sha256"] = "d" * 64
    try:
        module._require_receipt_identity(  # noqa: SLF001
            payload,
            transaction_hash="a" * 64,
            product_facts_hash="c" * 64,
            write_set_hash="b" * 64,
        )
    except RuntimeError as exc:
        assert "sealed Product Intent facts hash" in str(exc)
    else:
        raise AssertionError("receipt identity mismatch should fail the installed proof")
    payload["product_create_transaction"]["product_facts_sha256"] = "c" * 64
    payload["commit_manifest"]["product_create_transaction"]["product_facts_sha256"] = "d" * 64
    try:
        module._require_receipt_identity(  # noqa: SLF001
            payload,
            transaction_hash="a" * 64,
            product_facts_hash="c" * 64,
            write_set_hash="b" * 64,
        )
    except RuntimeError as exc:
        assert "sealed Product Intent facts hash" in str(exc)
    else:
        raise AssertionError("manifest Product Intent facts mismatch should fail the installed proof")
    payload["commit_manifest"]["product_create_transaction"]["product_facts_sha256"] = "c" * 64
    payload["commit_manifest"]["write_transaction"]["product_facts_sha256"] = "d" * 64
    try:
        module._require_receipt_identity(  # noqa: SLF001
            payload,
            transaction_hash="a" * 64,
            product_facts_hash="c" * 64,
            write_set_hash="b" * 64,
        )
    except RuntimeError as exc:
        assert "sealed Product Intent facts hash" in str(exc)
    else:
        raise AssertionError("write transaction Product Intent facts mismatch should fail the installed proof")


def test_compile_transaction_uses_the_exact_case_prompt_and_confirmed_intent(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    transaction_file = ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    transaction_path = tmp_path / transaction_file
    transaction_path.parent.mkdir(parents=True)
    transaction_path.write_text(
        json.dumps(
            {
                "transaction_hash": "a" * 64,
                "intent_authority": {
                    "source_format": "operator_prompt_with_edit_evidence",
                    "product_facts_sha256": "c" * 64,
                    "markdown_source_sha256": module.hashlib.sha256(
                        module.combined_prompt_evidence_source(
                            prompt="Create the exact recovery-bound product.",
                            edit_evidence="# Confirmed Recovery Intent\n\n## State\nA durable record.",
                        ).encode("utf-8")
                    ).hexdigest(),
                },
                "prewrite_package": {"repository_write_set": {"write_set_hash": "b" * 64}},
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        module,
        "_run",
        lambda **kwargs: captured.update(kwargs)
        or SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "product_create_transaction": {
                        "transaction_hash": "a" * 64,
                        "product_facts_sha256": "c" * 64,
                    },
                    "transaction_file": transaction_file,
                }
            ),
            stderr="",
        ),
    )
    case = module.GreenfieldMatrixCase(
        name="bound recovery case",
        prompt="Create the exact recovery-bound product.",
        required_terms=("recovery",),
        confirmed_intent_markdown="# Confirmed Recovery Intent\n\n## State\nA durable record.",
    )

    compiled = module._compile_transaction(  # noqa: SLF001
        repo_root=tmp_path,
        env={"PATH": "/usr/bin"},
        case=case,
    )
    assert compiled.transaction_hash == "a" * 64
    assert compiled.product_facts_hash == "c" * 64
    command = captured["command"]
    assert command[command.index("--prompt") + 1] == case.prompt
    assert command[command.index("--edit") + 1] == case.confirmed_intent_markdown


def test_compile_transaction_rejects_an_authority_that_does_not_bind_edit_evidence(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    transaction_file = ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    transaction_path = tmp_path / transaction_file
    transaction_path.parent.mkdir(parents=True)
    transaction_path.write_text(
        json.dumps(
            {
                "transaction_hash": "a" * 64,
                "intent_authority": {
                    "source_format": "operator_prompt_with_edit_evidence",
                    "product_facts_sha256": "c" * 64,
                    "markdown_source_sha256": "f" * 64,
                },
                "prewrite_package": {"repository_write_set": {"write_set_hash": "b" * 64}},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        module,
        "_run",
        lambda **_kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "product_create_transaction": {
                        "transaction_hash": "a" * 64,
                        "product_facts_sha256": "c" * 64,
                    },
                    "transaction_file": transaction_file,
                }
            ),
            stderr="",
        ),
    )
    case = module.GreenfieldMatrixCase(
        name="bound recovery case",
        prompt="Create the exact recovery-bound product.",
        required_terms=("recovery",),
        confirmed_intent_markdown="# Confirmed Recovery Intent\n\n## State\nA durable record.",
    )

    try:
        module._compile_transaction(repo_root=tmp_path, env={"PATH": "/usr/bin"}, case=case)  # noqa: SLF001
    except RuntimeError as exc:
        assert "did not bind the exact prompt and edit evidence" in str(exc)
    else:
        raise AssertionError("unbound edit evidence should fail installed recovery compilation")


def test_recovery_proof_payload_is_a_falsifiable_release_record() -> None:
    module = _module()
    case = module.GreenfieldMatrixCase(
        name="bound recovery case",
        prompt="Create the exact recovery-bound product.",
        required_terms=("recovery",),
        case_id="release-bound-recovery",
    )
    recovery_case = module.recovery_case_evidence(case)
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
        product_facts_sha256="c" * 64,
        recovery_case=recovery_case,
    )

    assert proof.passed
    assert proof.to_dict() == {
        "status": "passed",
        "scope": "real_installed_additive_write_sigkill_recovery_conflict_same_hash_retry_and_fsync_rollback",
        "recovery_case_scope": "one_selected_campaign_case_all_recovery_phases",
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
        "product_facts_sha256": "c" * 64,
        "recovery_case": recovery_case,
    }


def test_recovery_proof_requires_a_persisted_product_intent_facts_hash() -> None:
    module = _module()

    issues = module._missing_required_evidence({})  # noqa: SLF001

    assert "installed recovery proof did not record a valid Product Intent facts hash" in issues


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
    assert "installed recovery proof did not record required recovery_case.id" in issues


def test_recovery_proof_passes_the_same_case_to_every_recovery_phase(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    install_script = dist_dir / "install.sh"
    install_script.parent.mkdir()
    install_script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    case = module.GreenfieldMatrixCase(
        name="bound recovery case",
        prompt="Create the exact recovery-bound product.",
        required_terms=("recovery",),
        case_id="campaign-recovery-case",
    )
    captured_cases: list[object] = []

    class _Server:
        def shutdown(self) -> None:
            return None

        def server_close(self) -> None:
            return None

    monkeypatch.setattr(module, "_serve_directory", lambda _path: (_Server(), "http://127.0.0.1:8123"))
    monkeypatch.setattr(module, "_installed_release_env", lambda **_kwargs: {"PATH": "/usr/bin"})

    def sigkill_phase(**kwargs):  # noqa: ANN001
        captured_cases.append(kwargs["case"])
        return {
            "sigkill_returncode": -9,
            "recovery_returncode": 0,
                "same_hash_retry_returncode": 0,
                "journal_state_after_crash": "applying",
                "journal_state_after_recovery": "committed",
                "governed_write_observed_after_crash": True,
                "installed_runtime_module_path": "/tmp/managed/odylith/__init__.py",
                "installed_runtime_version": "0.1.15",
                "product_facts_sha256": "c" * 64,
        }

    def conflict_phase(**kwargs):  # noqa: ANN001
        captured_cases.append(kwargs["case"])
        return {
            "operator_conflict_returncode": 2,
            "operator_conflict_failure_kind": "post_confirm_commit_recovery_conflict",
            "operator_conflict_rollback_status": "not_started",
            "operator_conflict_journal_state": "applying",
            "operator_mutation_preserved": True,
            "operator_conflict_snapshot_retained": True,
            "operator_conflict_recovery_path_bound": True,
        }

    def fsync_phase(**kwargs):  # noqa: ANN001
        captured_cases.append(kwargs["case"])
        return {
            "fsync_failure_returncode": 2,
                "fsync_retry_returncode": 0,
                "fsync_same_hash_retry_returncode": 0,
                "fsync_journal_state_after_failure": "rolled_back",
                "fsync_journal_state_after_retry": "committed",
                "fsync_failure_kind": "post_confirm_commit_environment_or_io_failure",
                "product_facts_sha256": "c" * 64,
            }

    monkeypatch.setattr(module, "_run_sigkill_recovery_phase", sigkill_phase)
    monkeypatch.setattr(module, "_run_operator_conflict_recovery_phase", conflict_phase)
    monkeypatch.setattr(module, "_run_fsync_rollback_phase", fsync_phase)

    proof = module.run_installed_commit_recovery_proof(
        dist_dir=dist_dir,
        version="0.1.15",
        temp_parent=tmp_path,
        recovery_case=case,
    )

    assert proof.passed
    assert proof.product_facts_sha256 == "c" * 64
    assert captured_cases == [case, case, case]

    def mismatched_fsync_phase(**kwargs):  # noqa: ANN001
        facts = fsync_phase(**kwargs)
        facts["product_facts_sha256"] = "d" * 64
        return facts

    monkeypatch.setattr(module, "_run_fsync_rollback_phase", mismatched_fsync_phase)

    mismatch = module.run_installed_commit_recovery_proof(
        dist_dir=dist_dir,
        version="0.1.15",
        temp_parent=tmp_path,
        recovery_case=case,
    )

    assert not mismatch.passed
    assert "installed recovery phases did not retain the same sealed Product Intent facts hash" in mismatch.issues
    assert all(captured is case for captured in captured_cases)
    assert proof.recovery_case["id"] == case.case_id
    assert proof.recovery_case["binding_scope"] == "campaign-case-v1"


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
        lambda **_kwargs: module._CompiledRecoveryTransaction(  # noqa: SLF001
            transaction_file=".odylith/runtime/greenfield/product-create-transaction.v1.json",
            transaction_hash=transaction_hash,
            product_facts_hash="c" * 64,
            write_set_hash="b" * 64,
            intent_authority={},
        ),
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
        case=module.GreenfieldMatrixCase(
            name="bound recovery case",
            prompt="Create the exact recovery-bound product.",
            required_terms=("recovery",),
        ),
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
