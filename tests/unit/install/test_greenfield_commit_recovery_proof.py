from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
import shutil
from types import SimpleNamespace

from odylith.runtime.domain_intelligence import greenfield_generation_store
from odylith.runtime.domain_intelligence import greenfield_repository_write_set


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


def _receipt_payload(*, transaction_hash: str, product_facts_hash: str, write_set_hash: str) -> dict[str, object]:
    return {
        "product_create_transaction": {
            "transaction_hash": transaction_hash,
            "product_facts_sha256": product_facts_hash,
        },
        "commit_manifest": {
            "product_create_transaction": {"product_facts_sha256": product_facts_hash},
            "write_transaction": {
                "product_create_transaction_hash": transaction_hash,
                "product_facts_sha256": product_facts_hash,
                "repository_write_set_hash": write_set_hash,
            },
        },
    }


def _generation_observation(
    *,
    transaction_hash: str = "a" * 64,
    write_set_hash: str = "b" * 64,
    active: bool = False,
    generation_present: bool = False,
    readback_status: str = "",
) -> dict[str, object]:
    manifest = "e" * 64 if generation_present else ""
    return {
        "active_identity": {
            "status": "active" if active else "none",
            "transaction_hash": transaction_hash if active else "",
            "write_set_hash": write_set_hash if active else "",
            "generation_manifest_sha256": manifest if active else "",
        },
        "active_pin_status": "active" if active else "none",
        "active_pin_transaction_hash": transaction_hash if active else "",
        "transaction_generation_status": "present" if generation_present else "missing",
        "transaction_generation_manifest_sha256": manifest,
        "transaction_generation_write_set_hash": write_set_hash if generation_present else "",
        "transaction_generation_readback_status": readback_status or ("passed" if generation_present else "missing"),
    }


def test_generation_observation_rejects_manifest_only_published_proof() -> None:
    module = _module()
    invalid = _generation_observation(
        active=True,
        generation_present=True,
        readback_status="invalid",
    )
    facts = {
        "sigkill_generation_observations": {
            "before": _generation_observation(),
            "after_crash": _generation_observation(generation_present=True),
            "after_recovery": invalid,
        },
        "operator_conflict_generation_observations": {
            "before": _generation_observation(),
            "after_conflict": _generation_observation(),
        },
        "fsync_generation_observations": {
            "before": _generation_observation(),
            "after_failure": _generation_observation(),
            "after_retry": _generation_observation(active=True, generation_present=True),
        },
    }

    assert "installed SIGKILL recovery published generation failed sealed after-image readback" in module._generation_observation_issues(facts)  # noqa: SLF001


def test_installed_generation_observation_rejects_tampered_after_image(tmp_path: Path) -> None:
    module = _module()
    repo = tmp_path / "repo"
    stage = tmp_path / "stage"
    source_file = repo / "odylith/index.html"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("before\n", encoding="utf-8")
    shutil.copytree(repo / "odylith", stage / "odylith")
    (stage / "odylith/index.html").write_text("after\n", encoding="utf-8")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=repo,
        staged_root=stage,
    )
    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        transaction_hash="a" * 64,
        write_set=write_set,
    )
    transaction_file = repo / "transaction.json"
    transaction_file.write_text(
        json.dumps({"prewrite_package": {"repository_write_set": write_set}}),
        encoding="utf-8",
    )
    (generation.repository_root / "odylith/index.html").write_text("tampered\n", encoding="utf-8")

    observed = subprocess.run(
        [
            sys.executable,
            "-c",
            module._GENERATION_OBSERVATION_SCRIPT,  # noqa: SLF001
            "a" * 64,
            str(transaction_file),
        ],
        cwd=repo,
        env={
            **os.environ,
            "PYTHONPATH": str(REPO_ROOT / "src"),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(observed.stdout)

    assert payload["transaction_generation_status"] == "invalid"
    assert payload["transaction_generation_readback_status"] == "invalid"


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

    assert "PYTHONPATH" not in env
    assert env["ODYLITH_VERSION"] == "0.1.15"
    assert env["ODYLITH_GREENFIELD_MODEL_PROFILE"] == module.STANDARD_PROFILE_ID
    assert env["ODYLITH_REASONING_PROVIDER"] == "codex-cli"


def test_recovery_phases_reuse_one_sealed_transaction(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    seed_root = tmp_path / "seed"
    seed_version_root = seed_root / ".odylith/runtime/versions/0.1.15"
    seed_version_root.mkdir(parents=True)
    seed_current = seed_root / ".odylith/runtime/current"
    seed_current.symlink_to(seed_version_root, target_is_directory=True)
    transaction_path = seed_root / ".odylith/runtime/greenfield/pending/hash/product-create-transaction.v1.json"
    transaction_path.parent.mkdir(parents=True)
    transaction_path.write_text("{}\n", encoding="utf-8")
    seed = module._RecoverySeed(  # noqa: SLF001
        repo_root=seed_root,
        transaction=module._CompiledRecoveryTransaction(  # noqa: SLF001
            transaction_file=str(transaction_path),
            transaction_hash="a" * 64,
            product_facts_hash="c" * 64,
            write_set_hash="b" * 64,
            intent_authority={},
        ),
    )
    monkeypatch.setattr(
        module,
        "_install_repo",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("seeded phase must not reinstall")),
    )
    monkeypatch.setattr(
        module,
        "_compile_transaction",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("seeded phase must not re-author")),
    )

    repo_root, transaction = module._phase_repo_and_transaction(  # noqa: SLF001
        run_root=tmp_path,
        phase_name="phase",
        install_script=tmp_path / "install.sh",
        env={"PATH": "/usr/bin"},
        case=module.GreenfieldMatrixCase(
            name="bound recovery case",
            prompt="Create the exact recovery-bound product.",
            required_terms=("recovery",),
        ),
        seed=seed,
    )

    assert (repo_root / transaction.transaction_file).read_text(encoding="utf-8") == "{}\n"
    assert transaction.product_facts_hash == "c" * 64
    cloned_current = repo_root / ".odylith/runtime/current"
    assert cloned_current.is_symlink()
    assert cloned_current.readlink() == Path("versions/0.1.15")
    assert cloned_current.resolve() == repo_root / ".odylith/runtime/versions/0.1.15"


def test_recovery_seed_clone_rejects_runtime_outside_managed_versions(tmp_path: Path) -> None:
    module = _module()
    seed_root = tmp_path / "seed"
    outside_runtime = tmp_path / "outside-runtime"
    outside_runtime.mkdir()
    seed_current = seed_root / ".odylith/runtime/current"
    seed_current.parent.mkdir(parents=True)
    seed_current.symlink_to(outside_runtime, target_is_directory=True)

    try:
        module._clone_recovery_seed_repo(seed_repo=seed_root, repo_root=tmp_path / "phase")  # noqa: SLF001
    except RuntimeError as exc:
        assert str(exc) == "installed recovery seed active runtime is outside its managed versions"
    else:
        raise AssertionError("external recovery runtime must fail closed")
    assert not (tmp_path / "phase").exists()


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
    payload = _receipt_payload(
        transaction_hash="a" * 64,
        product_facts_hash="c" * 64,
        write_set_hash="b" * 64,
    )

    observed = module._require_receipt_identity(  # noqa: SLF001
        payload,
        transaction_hash="a" * 64,
        product_facts_hash="c" * 64,
        write_set_hash="b" * 64,
    )
    assert observed == "c" * 64
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


def test_journal_receipt_identity_requires_a_bound_durable_receipt() -> None:
    module = _module()
    journal = {
        "transaction_hash": "a" * 64,
        "repository_write_set_hash": "b" * 64,
        "commit_result": _receipt_payload(
            transaction_hash="a" * 64,
            product_facts_hash="c" * 64,
            write_set_hash="b" * 64,
        ),
    }

    observed = module._require_journal_receipt_identity(  # noqa: SLF001
        journal,
        transaction_hash="a" * 64,
        product_facts_hash="c" * 64,
        write_set_hash="b" * 64,
    )

    assert observed == "c" * 64
    journal.pop("commit_result")
    try:
        module._require_journal_receipt_identity(  # noqa: SLF001
            journal,
            transaction_hash="a" * 64,
            product_facts_hash="c" * 64,
            write_set_hash="b" * 64,
        )
    except RuntimeError as exc:
        assert "did not retain its sealed commit receipt" in str(exc)
    else:
        raise AssertionError("journal receipt identity should fail without the durable commit receipt")


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
        journal_state_after_crash="projecting",
        journal_state_after_recovery="closed",
        fsync_journal_state_after_failure="aborted",
        fsync_journal_state_after_retry="closed",
        fsync_failure_kind="post_confirm_commit_environment_or_io_failure",
        operator_conflict_failure_kind="post_confirm_commit_recovery_conflict",
        operator_conflict_rollback_status="not_started",
        operator_conflict_journal_state="projecting",
        governed_write_observed_after_crash=True,
        operator_mutation_preserved=True,
        operator_conflict_snapshot_retained=True,
        operator_conflict_recovery_path_bound=True,
        installed_runtime_module_path="/tmp/repo/.odylith/runtime/versions/0.1.15/lib/odylith/__init__.py",
        installed_runtime_version="0.1.15",
        product_facts_sha256="c" * 64,
        product_facts_hashes_by_phase={
            "sigkill": "c" * 64,
            "operator_conflict": "c" * 64,
            "fsync": "c" * 64,
        },
        product_facts_hash_sources_by_phase={
            "sigkill": "success_receipt",
            "operator_conflict": "projecting_journal_commit_receipt",
            "fsync": "retry_success_receipt",
        },
        sigkill_generation_observations={
            "before": _generation_observation(),
            "after_crash": _generation_observation(generation_present=True),
            "after_recovery": _generation_observation(active=True, generation_present=True),
        },
        operator_conflict_generation_observations={
            "before": _generation_observation(),
            "after_crash": _generation_observation(generation_present=True),
            "after_conflict": _generation_observation(generation_present=True),
        },
        fsync_generation_observations={
            "before": _generation_observation(),
            "after_failure": _generation_observation(),
            "after_retry": _generation_observation(active=True, generation_present=True),
        },
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
        "journal_state_after_crash": "projecting",
        "journal_state_after_recovery": "closed",
        "fsync_journal_state_after_failure": "aborted",
        "fsync_journal_state_after_retry": "closed",
        "fsync_failure_kind": "post_confirm_commit_environment_or_io_failure",
        "operator_conflict_failure_kind": "post_confirm_commit_recovery_conflict",
        "operator_conflict_rollback_status": "not_started",
        "operator_conflict_journal_state": "projecting",
        "governed_write_observed_after_crash": True,
        "operator_mutation_preserved": True,
        "operator_conflict_snapshot_retained": True,
        "operator_conflict_recovery_path_bound": True,
        "installed_runtime_module_path": "/tmp/repo/.odylith/runtime/versions/0.1.15/lib/odylith/__init__.py",
        "installed_runtime_version": "0.1.15",
        "product_facts_sha256": "c" * 64,
        "product_facts_hashes_by_phase": {
            "sigkill": "c" * 64,
            "operator_conflict": "c" * 64,
            "fsync": "c" * 64,
        },
        "product_facts_hash_sources_by_phase": {
            "sigkill": "success_receipt",
            "operator_conflict": "projecting_journal_commit_receipt",
            "fsync": "retry_success_receipt",
        },
        "sigkill_generation_observations": {
            "before": _generation_observation(),
            "after_crash": _generation_observation(generation_present=True),
            "after_recovery": _generation_observation(active=True, generation_present=True),
        },
        "operator_conflict_generation_observations": {
            "before": _generation_observation(),
            "after_crash": _generation_observation(generation_present=True),
            "after_conflict": _generation_observation(generation_present=True),
        },
        "fsync_generation_observations": {
            "before": _generation_observation(),
            "after_failure": _generation_observation(),
            "after_retry": _generation_observation(active=True, generation_present=True),
        },
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
            "journal_state_after_crash": "projecting",
            "journal_state_after_recovery": "closed",
            "fsync_journal_state_after_failure": "aborted",
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
    monkeypatch.setattr(
        module,
        "_prepare_recovery_seed",
        lambda **_kwargs: module._RecoverySeed(  # noqa: SLF001
            repo_root=tmp_path / "seed",
            transaction=module._CompiledRecoveryTransaction(  # noqa: SLF001
                transaction_file=".odylith/runtime/greenfield/product-create-transaction.v1.json",
                transaction_hash="a" * 64,
                product_facts_hash="c" * 64,
                write_set_hash="b" * 64,
                intent_authority={},
            ),
        ),
    )

    def sigkill_phase(**kwargs):  # noqa: ANN001
        captured_cases.append(kwargs["case"])
        return {
            "sigkill_returncode": -9,
            "recovery_returncode": 0,
                "same_hash_retry_returncode": 0,
                "journal_state_after_crash": "projecting",
                "journal_state_after_recovery": "closed",
                "governed_write_observed_after_crash": True,
                "installed_runtime_module_path": "/tmp/managed/odylith/__init__.py",
                "installed_runtime_version": "0.1.15",
                "product_facts_sha256": "c" * 64,
                "product_facts_hash_source": "success_receipt",
                "sigkill_generation_observations": {
                    "before": _generation_observation(),
                    "after_crash": _generation_observation(generation_present=True),
                    "after_recovery": _generation_observation(active=True, generation_present=True),
                },
        }

    def conflict_phase(**kwargs):  # noqa: ANN001
        captured_cases.append(kwargs["case"])
        return {
            "operator_conflict_returncode": 2,
            "operator_conflict_failure_kind": "post_confirm_commit_recovery_conflict",
            "operator_conflict_rollback_status": "not_started",
            "operator_conflict_journal_state": "projecting",
            "operator_mutation_preserved": True,
            "operator_conflict_snapshot_retained": True,
            "operator_conflict_recovery_path_bound": True,
            "product_facts_sha256": "c" * 64,
            "product_facts_hash_source": "projecting_journal_commit_receipt",
            "operator_conflict_generation_observations": {
                "before": _generation_observation(),
                "after_crash": _generation_observation(generation_present=True),
                "after_conflict": _generation_observation(generation_present=True),
            },
        }

    def fsync_phase(**kwargs):  # noqa: ANN001
        captured_cases.append(kwargs["case"])
        return {
            "fsync_failure_returncode": 2,
                "fsync_retry_returncode": 0,
                "fsync_same_hash_retry_returncode": 0,
                "fsync_journal_state_after_failure": "aborted",
                "fsync_journal_state_after_retry": "closed",
                "fsync_failure_kind": "post_confirm_commit_environment_or_io_failure",
                "product_facts_sha256": "c" * 64,
                "product_facts_hash_source": "retry_success_receipt",
                "fsync_generation_observations": {
                    "before": _generation_observation(),
                    "after_failure": _generation_observation(),
                    "after_retry": _generation_observation(active=True, generation_present=True),
                },
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
    assert proof.product_facts_hashes_by_phase == {
        "sigkill": "c" * 64,
        "operator_conflict": "c" * 64,
        "fsync": "c" * 64,
    }
    assert proof.product_facts_hash_sources_by_phase == {
        "sigkill": "success_receipt",
        "operator_conflict": "projecting_journal_commit_receipt",
        "fsync": "retry_success_receipt",
    }
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

    def mismatched_conflict_phase(**kwargs):  # noqa: ANN001
        facts = conflict_phase(**kwargs)
        facts["product_facts_sha256"] = "d" * 64
        return facts

    monkeypatch.setattr(module, "_run_fsync_rollback_phase", fsync_phase)
    monkeypatch.setattr(module, "_run_operator_conflict_recovery_phase", mismatched_conflict_phase)

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
    monkeypatch.setattr(
        module,
        "_journal_state",
        lambda **_kwargs: {
            "state": "projecting",
            "generation_manifest_sha256": "e" * 64,
        },
    )
    conflict_observations = iter(
        (
            _generation_observation(),
            _generation_observation(generation_present=True),
            _generation_observation(generation_present=True),
        )
    )
    monkeypatch.setattr(
        module,
        "_installed_generation_observation",
        lambda **_kwargs: next(conflict_observations),
    )
    captured_receipt: dict[str, object] = {}

    def observed_journal_receipt(_journal, **kwargs):  # noqa: ANN001
        captured_receipt.update(kwargs)
        return "d" * 64

    monkeypatch.setattr(module, "_require_journal_receipt_identity", observed_journal_receipt)

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
        "operator_conflict_journal_state": "projecting",
        "operator_mutation_preserved": True,
        "operator_conflict_snapshot_retained": True,
        "operator_conflict_recovery_path_bound": True,
        "operator_conflict_generation_observations": {
            "before": _generation_observation(),
            "after_crash": _generation_observation(generation_present=True),
            "after_conflict": _generation_observation(generation_present=True),
        },
        "product_facts_sha256": "d" * 64,
        "product_facts_hash_source": "projecting_journal_commit_receipt",
    }
    assert captured_receipt["product_facts_hash"] == "c" * 64
    assert partial_write.read_bytes() == b"operator mutation retained by installed recovery proof\n"


def test_sigkill_phase_reports_the_observed_success_receipt_hash(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    repo_root = tmp_path / "sigkill"
    compiled = module._CompiledRecoveryTransaction(  # noqa: SLF001
        transaction_file=".odylith/runtime/greenfield/product-create-transaction.v1.json",
        transaction_hash="a" * 64,
        product_facts_hash="c" * 64,
        write_set_hash="b" * 64,
        intent_authority={},
    )
    monkeypatch.setattr(module, "_install_repo", lambda **_kwargs: repo_root.mkdir(exist_ok=True))
    monkeypatch.setattr(module, "_installed_runtime_identity", lambda **_kwargs: {})
    monkeypatch.setattr(module, "_compile_transaction", lambda **_kwargs: compiled)
    fingerprints = iter(({"before": "1"}, {"partial": "1"}, {"after": "1"}, {"after": "1"}))
    monkeypatch.setattr(module, "_governed_fingerprint", lambda _root: next(fingerprints))
    monkeypatch.setattr(
        module,
        "_run_faulted_create",
        lambda **_kwargs: SimpleNamespace(returncode=-9, stdout="", stderr=""),
    )
    journal_states = iter(
        (
            {"state": "projecting", "generation_manifest_sha256": "e" * 64},
            {"state": "closed"},
        )
    )
    monkeypatch.setattr(module, "_journal_state", lambda **_kwargs: next(journal_states))
    sigkill_observations = iter(
        (
            _generation_observation(),
            _generation_observation(generation_present=True),
            _generation_observation(active=True, generation_present=True),
        )
    )
    monkeypatch.setattr(
        module,
        "_installed_generation_observation",
        lambda **_kwargs: next(sigkill_observations),
    )
    monkeypatch.setattr(
        module,
        "_run",
        lambda **_kwargs: SimpleNamespace(returncode=0, stdout="{}", stderr=""),
    )
    observed_receipts: list[dict[str, object]] = []

    def observed_receipt(_payload, **kwargs):  # noqa: ANN001
        observed_receipts.append(kwargs)
        return "d" * 64

    monkeypatch.setattr(module, "_require_receipt_identity", observed_receipt)

    facts = module._run_sigkill_recovery_phase(  # noqa: SLF001
        run_root=tmp_path,
        install_script=tmp_path / "install.sh",
        env={"PATH": "/usr/bin"},
        version="0.1.15",
        case=module.GreenfieldMatrixCase(
            name="bound recovery case",
            prompt="Create the exact recovery-bound product.",
            required_terms=("recovery",),
        ),
    )

    assert facts["product_facts_sha256"] == "d" * 64
    assert facts["product_facts_hash_source"] == "success_receipt"
    assert [call["product_facts_hash"] for call in observed_receipts] == ["c" * 64, "c" * 64]


def test_fsync_phase_reports_the_observed_retry_receipt_hash(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    repo_root = tmp_path / "fsync-rollback"
    compiled = module._CompiledRecoveryTransaction(  # noqa: SLF001
        transaction_file=".odylith/runtime/greenfield/product-create-transaction.v1.json",
        transaction_hash="a" * 64,
        product_facts_hash="c" * 64,
        write_set_hash="b" * 64,
        intent_authority={},
    )
    monkeypatch.setattr(module, "_install_repo", lambda **_kwargs: repo_root.mkdir(exist_ok=True))
    monkeypatch.setattr(module, "_compile_transaction", lambda **_kwargs: compiled)
    fingerprints = iter(({"before": "1"}, {"before": "1"}, {"after": "1"}, {"after": "1"}))
    monkeypatch.setattr(module, "_governed_fingerprint", lambda _root: next(fingerprints))
    monkeypatch.setattr(
        module,
        "_run_faulted_create",
        lambda **_kwargs: SimpleNamespace(
            returncode=2,
            stdout=(
                '{"mode":"error","commit_failure":{"failure_kind":"post_confirm_commit_environment_or_io_failure",'
                '"rollback_status":"rolled_back"}}'
            ),
            stderr="",
        ),
    )
    journal_states = iter(({"state": "aborted"}, {"state": "closed"}))
    monkeypatch.setattr(module, "_journal_state", lambda **_kwargs: next(journal_states))
    fsync_observations = iter(
        (
            _generation_observation(),
            _generation_observation(),
            _generation_observation(active=True, generation_present=True),
        )
    )
    monkeypatch.setattr(
        module,
        "_installed_generation_observation",
        lambda **_kwargs: next(fsync_observations),
    )
    monkeypatch.setattr(
        module,
        "_run",
        lambda **_kwargs: SimpleNamespace(returncode=0, stdout="{}", stderr=""),
    )
    observed_receipts: list[dict[str, object]] = []

    def observed_receipt(_payload, **kwargs):  # noqa: ANN001
        observed_receipts.append(kwargs)
        return "d" * 64

    monkeypatch.setattr(module, "_require_receipt_identity", observed_receipt)

    facts = module._run_fsync_rollback_phase(  # noqa: SLF001
        run_root=tmp_path,
        install_script=tmp_path / "install.sh",
        env={"PATH": "/usr/bin"},
        case=module.GreenfieldMatrixCase(
            name="bound recovery case",
            prompt="Create the exact recovery-bound product.",
            required_terms=("recovery",),
        ),
    )

    assert facts["product_facts_sha256"] == "d" * 64
    assert facts["product_facts_hash_source"] == "retry_success_receipt"
    assert [call["product_facts_hash"] for call in observed_receipts] == ["c" * 64, "c" * 64]


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
