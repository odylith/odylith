"""Installed crash-recovery proof for sealed Greenfield create transactions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import signal
from typing import Any
import uuid

from greenfield_process import run_command_with_group_timeout as _run
from greenfield_preconfirm_matrix_cases import default_cases
from local_release_smoke import _cleanup_smoke_temp_root
from local_release_smoke import _local_release_env
from local_release_smoke import _serve_directory


COMMAND_TIMEOUT_SECONDS = 300
PROOF_SCOPE = "real_installed_additive_write_sigkill_recovery_conflict_same_hash_retry_and_fsync_rollback"
_GOVERNED_ROOTS = ("odylith", "src/odylith/bundle/assets/odylith")
_SIGKILL_FAULT = """
import os
import signal
import sys

from odylith import cli
from odylith.runtime.domain_intelligence import greenfield_repository_write_set

original = greenfield_repository_write_set.atomic_write_bytes


def crash_after_first_sealed_write(*args, **kwargs):
    result = original(*args, **kwargs)
    os.kill(os.getpid(), signal.SIGKILL)
    return result


greenfield_repository_write_set.atomic_write_bytes = crash_after_first_sealed_write
raise SystemExit(cli.main(sys.argv[1:]))
"""
_FSYNC_FAILURE_FAULT = """
import sys

from odylith import cli
from odylith.runtime.domain_intelligence import greenfield_repository_write_set


def fail_after_first_sealed_write(*_args, **_kwargs):
    raise OSError("injected installed Greenfield fsync failure")


greenfield_repository_write_set.fsync_file = fail_after_first_sealed_write
raise SystemExit(cli.main(sys.argv[1:]))
"""


@dataclass(frozen=True)
class GreenfieldInstalledCommitRecoveryProof:
    """Evidence returned by the installed crash-recovery release proof."""

    status: str
    issues: tuple[str, ...]
    sigkill_returncode: int | None = None
    recovery_returncode: int | None = None
    same_hash_retry_returncode: int | None = None
    fsync_failure_returncode: int | None = None
    fsync_retry_returncode: int | None = None
    fsync_same_hash_retry_returncode: int | None = None
    operator_conflict_returncode: int | None = None
    journal_state_after_crash: str = ""
    journal_state_after_recovery: str = ""
    fsync_journal_state_after_failure: str = ""
    fsync_journal_state_after_retry: str = ""
    fsync_failure_kind: str = ""
    operator_conflict_failure_kind: str = ""
    operator_conflict_rollback_status: str = ""
    operator_conflict_journal_state: str = ""
    governed_write_observed_after_crash: bool = False
    operator_mutation_preserved: bool = False
    operator_conflict_snapshot_retained: bool = False
    operator_conflict_recovery_path_bound: bool = False
    installed_runtime_module_path: str = ""
    installed_runtime_version: str = ""

    @property
    def passed(self) -> bool:
        return self.status == "passed" and not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "scope": PROOF_SCOPE,
            "issues": list(self.issues),
            "sigkill_returncode": self.sigkill_returncode,
            "recovery_returncode": self.recovery_returncode,
            "same_hash_retry_returncode": self.same_hash_retry_returncode,
            "fsync_failure_returncode": self.fsync_failure_returncode,
            "fsync_retry_returncode": self.fsync_retry_returncode,
            "fsync_same_hash_retry_returncode": self.fsync_same_hash_retry_returncode,
            "operator_conflict_returncode": self.operator_conflict_returncode,
            "journal_state_after_crash": self.journal_state_after_crash,
            "journal_state_after_recovery": self.journal_state_after_recovery,
            "fsync_journal_state_after_failure": self.fsync_journal_state_after_failure,
            "fsync_journal_state_after_retry": self.fsync_journal_state_after_retry,
            "fsync_failure_kind": self.fsync_failure_kind,
            "operator_conflict_failure_kind": self.operator_conflict_failure_kind,
            "operator_conflict_rollback_status": self.operator_conflict_rollback_status,
            "operator_conflict_journal_state": self.operator_conflict_journal_state,
            "governed_write_observed_after_crash": self.governed_write_observed_after_crash,
            "operator_mutation_preserved": self.operator_mutation_preserved,
            "operator_conflict_snapshot_retained": self.operator_conflict_snapshot_retained,
            "operator_conflict_recovery_path_bound": self.operator_conflict_recovery_path_bound,
            "installed_runtime_module_path": self.installed_runtime_module_path,
            "installed_runtime_version": self.installed_runtime_version,
        }


def run_installed_commit_recovery_proof(
    *,
    dist_dir: Path,
    version: str,
    temp_parent: Path,
) -> GreenfieldInstalledCommitRecoveryProof:
    """Prove installed hard-crash recovery, exact retry, and fsync rollback."""

    run_root = Path(temp_parent).expanduser().resolve() / f"odylith-greenfield-commit-recovery-{uuid.uuid4().hex}"
    server = None
    issues: list[str] = []
    facts: dict[str, Any] = {}
    try:
        release_dir = Path(dist_dir).expanduser().resolve()
        install_script = release_dir / "install.sh"
        if not install_script.is_file():
            raise RuntimeError(f"missing local release install script: {install_script}")
        run_root.mkdir(parents=True, exist_ok=False)
        server, base_url = _serve_directory(release_dir)
        env = _installed_release_env(base_url=base_url, version=version)
        facts.update(
            _run_sigkill_recovery_phase(
                run_root=run_root,
                install_script=install_script,
                env=env,
                version=version,
            )
        )
        facts.update(
            _run_operator_conflict_recovery_phase(
                run_root=run_root,
                install_script=install_script,
                env=env,
            )
        )
        facts.update(_run_fsync_rollback_phase(run_root=run_root, install_script=install_script, env=env))
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        issues.append(str(exc))
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        try:
            _cleanup_smoke_temp_root(run_root)
        except OSError as exc:
            issues.append(f"installed commit recovery proof cleanup failed: {exc}")
        if run_root.exists() or run_root.is_symlink():
            issues.append(f"installed commit recovery proof left a temporary root: {run_root}")
    if not issues:
        issues.extend(_missing_required_evidence(facts))
    return GreenfieldInstalledCommitRecoveryProof(
        status="passed" if not issues else "failed",
        issues=tuple(issues),
        sigkill_returncode=facts.get("sigkill_returncode"),
        recovery_returncode=facts.get("recovery_returncode"),
        same_hash_retry_returncode=facts.get("same_hash_retry_returncode"),
        fsync_failure_returncode=facts.get("fsync_failure_returncode"),
        fsync_retry_returncode=facts.get("fsync_retry_returncode"),
        fsync_same_hash_retry_returncode=facts.get("fsync_same_hash_retry_returncode"),
        operator_conflict_returncode=facts.get("operator_conflict_returncode"),
        journal_state_after_crash=str(facts.get("journal_state_after_crash") or ""),
        journal_state_after_recovery=str(facts.get("journal_state_after_recovery") or ""),
        fsync_journal_state_after_failure=str(facts.get("fsync_journal_state_after_failure") or ""),
        fsync_journal_state_after_retry=str(facts.get("fsync_journal_state_after_retry") or ""),
        fsync_failure_kind=str(facts.get("fsync_failure_kind") or ""),
        operator_conflict_failure_kind=str(facts.get("operator_conflict_failure_kind") or ""),
        operator_conflict_rollback_status=str(facts.get("operator_conflict_rollback_status") or ""),
        operator_conflict_journal_state=str(facts.get("operator_conflict_journal_state") or ""),
        governed_write_observed_after_crash=bool(facts.get("governed_write_observed_after_crash")),
        operator_mutation_preserved=bool(facts.get("operator_mutation_preserved")),
        operator_conflict_snapshot_retained=bool(facts.get("operator_conflict_snapshot_retained")),
        operator_conflict_recovery_path_bound=bool(facts.get("operator_conflict_recovery_path_bound")),
        installed_runtime_module_path=str(facts.get("installed_runtime_module_path") or ""),
        installed_runtime_version=str(facts.get("installed_runtime_version") or ""),
    )


def _missing_required_evidence(facts: Mapping[str, Any]) -> list[str]:
    """Keep a partial proof record from being published as a successful proof."""

    missing: list[str] = []
    required_values = {
        "journal_state_after_crash": "applying",
        "journal_state_after_recovery": "committed",
        "fsync_journal_state_after_failure": "rolled_back",
        "fsync_journal_state_after_retry": "committed",
        "fsync_failure_kind": "post_confirm_commit_environment_or_io_failure",
        "operator_conflict_failure_kind": "post_confirm_commit_recovery_conflict",
        "operator_conflict_rollback_status": "not_started",
        "operator_conflict_journal_state": "applying",
    }
    for key, expected in required_values.items():
        if str(facts.get(key) or "") != expected:
            missing.append(f"installed recovery proof did not record required {key}={expected}")
    for key in (
        "sigkill_returncode",
        "recovery_returncode",
        "same_hash_retry_returncode",
        "fsync_failure_returncode",
        "fsync_retry_returncode",
        "fsync_same_hash_retry_returncode",
        "operator_conflict_returncode",
    ):
        if not isinstance(facts.get(key), int):
            missing.append(f"installed recovery proof did not record required {key}")
    if facts.get("governed_write_observed_after_crash") is not True:
        missing.append("installed recovery proof did not observe a partial governed write before recovery")
    if facts.get("operator_mutation_preserved") is not True:
        missing.append("installed recovery proof did not preserve the concurrent operator mutation")
    if facts.get("operator_conflict_snapshot_retained") is not True:
        missing.append("installed recovery proof did not retain the conflict recovery snapshot")
    if facts.get("operator_conflict_recovery_path_bound") is not True:
        missing.append("installed recovery proof did not report the retained conflict recovery path")
    for key in ("installed_runtime_module_path", "installed_runtime_version"):
        if not str(facts.get(key) or "").strip():
            missing.append(f"installed recovery proof did not record required {key}")
    return missing


def _run_sigkill_recovery_phase(
    *,
    run_root: Path,
    install_script: Path,
    env: Mapping[str, str],
    version: str,
) -> dict[str, Any]:
    repo_root = run_root / "sigkill-same-hash"
    _install_repo(repo_root=repo_root, install_script=install_script, env=env)
    runtime_identity = _installed_runtime_identity(repo_root=repo_root, env=env, version=version)
    transaction_file, transaction_hash, write_set_hash = _compile_transaction(repo_root=repo_root, env=env)
    before = _governed_fingerprint(repo_root)
    command = _create_command(transaction_file=transaction_file, transaction_hash=transaction_hash)
    crashed = _run_faulted_create(repo_root=repo_root, env=env, command=command, fault_script=_SIGKILL_FAULT)
    if crashed.returncode != -signal.SIGKILL:
        raise RuntimeError(
            "installed create did not terminate with SIGKILL after its first sealed write: "
            + _command_detail(crashed)
        )
    after_crash = _governed_fingerprint(repo_root)
    if not after_crash or after_crash == before:
        raise RuntimeError("SIGKILL proof did not observe a partial sealed governed write before recovery")
    journal = _journal_state(repo_root=repo_root, transaction_hash=transaction_hash)
    if journal.get("state") != "applying":
        raise RuntimeError("SIGKILL proof did not leave the installed commit journal in applying state")
    recovered = _run(cwd=repo_root, env=dict(env), command=command, timeout=COMMAND_TIMEOUT_SECONDS)
    recovery_payload = _require_success_payload(recovered, label="installed SIGKILL recovery create")
    _require_receipt_identity(
        recovery_payload,
        transaction_hash=transaction_hash,
        write_set_hash=write_set_hash,
    )
    after_recovery = _governed_fingerprint(repo_root)
    if not after_recovery or after_recovery == before:
        raise RuntimeError("installed SIGKILL recovery did not materialize the sealed governed package")
    completed_journal = _journal_state(repo_root=repo_root, transaction_hash=transaction_hash)
    if completed_journal.get("state") != "committed":
        raise RuntimeError("installed SIGKILL recovery did not produce a committed durable receipt")
    journal_root = _journal_root(repo_root, transaction_hash)
    if (journal_root / "snapshot").exists() or (journal_root / "staging").exists():
        raise RuntimeError("installed SIGKILL recovery retained rollback artifacts after durable commit")
    retried = _run(cwd=repo_root, env=dict(env), command=command, timeout=COMMAND_TIMEOUT_SECONDS)
    retry_payload = _require_success_payload(retried, label="installed same-hash retry")
    _require_receipt_identity(
        retry_payload,
        transaction_hash=transaction_hash,
        write_set_hash=write_set_hash,
    )
    if retry_payload != recovery_payload:
        raise RuntimeError("installed same-hash retry did not return the durable commit receipt")
    if _governed_fingerprint(repo_root) != after_recovery:
        raise RuntimeError("installed same-hash retry rewrote the committed governed package")
    return {
        "sigkill_returncode": crashed.returncode,
        "recovery_returncode": recovered.returncode,
        "same_hash_retry_returncode": retried.returncode,
        "journal_state_after_crash": str(journal.get("state") or ""),
        "journal_state_after_recovery": str(completed_journal.get("state") or ""),
        "governed_write_observed_after_crash": True,
        **runtime_identity,
    }


def _run_operator_conflict_recovery_phase(
    *,
    run_root: Path,
    install_script: Path,
    env: Mapping[str, str],
) -> dict[str, Any]:
    """Prove recovery preserves a later operator mutation instead of restoring over it."""

    repo_root = run_root / "operator-conflict"
    _install_repo(repo_root=repo_root, install_script=install_script, env=env)
    transaction_file, transaction_hash, _write_set_hash = _compile_transaction(repo_root=repo_root, env=env)
    before = _governed_fingerprint(repo_root)
    command = _create_command(transaction_file=transaction_file, transaction_hash=transaction_hash)
    crashed = _run_faulted_create(repo_root=repo_root, env=env, command=command, fault_script=_SIGKILL_FAULT)
    if crashed.returncode != -signal.SIGKILL:
        raise RuntimeError(
            "installed conflict proof did not terminate with SIGKILL after its first sealed write: "
            + _command_detail(crashed)
        )
    partial_write = _interrupted_governed_write_path(
        repo_root=repo_root,
        before=before,
        after=_governed_fingerprint(repo_root),
    )
    operator_bytes = b"operator mutation retained by installed recovery proof\n"
    partial_write.write_bytes(operator_bytes)
    conflicted = _run(cwd=repo_root, env=dict(env), command=command, timeout=COMMAND_TIMEOUT_SECONDS)
    conflict_payload = _require_error_payload(conflicted, label="installed operator-conflict recovery create")
    commit_failure = _mapping(conflict_payload.get("commit_failure"))
    failure_kind = str(commit_failure.get("failure_kind") or "")
    if failure_kind != "post_confirm_commit_recovery_conflict":
        raise RuntimeError(
            "installed conflict recovery reported unexpected failure kind: "
            f"{failure_kind or 'missing'}"
        )
    rollback_status = str(commit_failure.get("rollback_status") or "")
    if rollback_status != "not_started":
        raise RuntimeError(
            "installed conflict recovery reported unexpected rollback status: "
            f"{rollback_status or 'missing'}"
        )
    journal = _journal_state(repo_root=repo_root, transaction_hash=transaction_hash)
    if journal.get("state") != "applying":
        raise RuntimeError("installed conflict recovery changed the interrupted journal state")
    journal_root = _journal_root(repo_root, transaction_hash)
    recovery_path = Path(str(commit_failure.get("recovery_path") or "")).expanduser()
    if not recovery_path.is_absolute():
        recovery_path = repo_root / recovery_path
    if recovery_path.resolve(strict=False) != journal_root.resolve():
        raise RuntimeError("installed conflict recovery did not report its retained journal path")
    if not (journal_root / "snapshot").is_dir():
        raise RuntimeError("installed conflict recovery discarded the retained rollback snapshot")
    if partial_write.read_bytes() != operator_bytes:
        raise RuntimeError("installed conflict recovery overwrote the later operator mutation")
    return {
        "operator_conflict_returncode": conflicted.returncode,
        "operator_conflict_failure_kind": failure_kind,
        "operator_conflict_rollback_status": rollback_status,
        "operator_conflict_journal_state": str(journal.get("state") or ""),
        "operator_mutation_preserved": True,
        "operator_conflict_snapshot_retained": True,
        "operator_conflict_recovery_path_bound": True,
    }


def _run_fsync_rollback_phase(*, run_root: Path, install_script: Path, env: Mapping[str, str]) -> dict[str, Any]:
    repo_root = run_root / "fsync-rollback"
    _install_repo(repo_root=repo_root, install_script=install_script, env=env)
    transaction_file, transaction_hash, write_set_hash = _compile_transaction(repo_root=repo_root, env=env)
    before = _governed_fingerprint(repo_root)
    command = _create_command(transaction_file=transaction_file, transaction_hash=transaction_hash)
    failed = _run_faulted_create(repo_root=repo_root, env=env, command=command, fault_script=_FSYNC_FAILURE_FAULT)
    failure_payload = _require_error_payload(failed, label="installed fsync rollback create")
    commit_failure = _mapping(failure_payload.get("commit_failure"))
    failure_kind = str(commit_failure.get("failure_kind") or "")
    if failure_kind != "post_confirm_commit_environment_or_io_failure":
        raise RuntimeError(f"installed fsync failure reported unexpected failure kind: {failure_kind or 'missing'}")
    if str(commit_failure.get("rollback_status") or "") != "rolled_back":
        raise RuntimeError("installed fsync failure did not report a completed rollback")
    if _governed_fingerprint(repo_root) != before:
        raise RuntimeError("installed fsync failure left partial governed writes after rollback")
    failed_journal = _journal_state(repo_root=repo_root, transaction_hash=transaction_hash)
    if failed_journal.get("state") != "rolled_back":
        raise RuntimeError("installed fsync failure did not persist a rolled_back journal state")
    journal_root = _journal_root(repo_root, transaction_hash)
    if (journal_root / "snapshot").exists() or (journal_root / "staging").exists():
        raise RuntimeError("installed fsync failure retained rollback artifacts after cleanup")
    retried = _run(cwd=repo_root, env=dict(env), command=command, timeout=COMMAND_TIMEOUT_SECONDS)
    retry_payload = _require_success_payload(retried, label="installed fsync rollback retry")
    _require_receipt_identity(
        retry_payload,
        transaction_hash=transaction_hash,
        write_set_hash=write_set_hash,
    )
    after_retry = _governed_fingerprint(repo_root)
    if not after_retry:
        raise RuntimeError("installed fsync rollback retry did not materialize the sealed governed package")
    completed_journal = _journal_state(repo_root=repo_root, transaction_hash=transaction_hash)
    if completed_journal.get("state") != "committed":
        raise RuntimeError("installed fsync rollback retry did not produce a committed durable receipt")
    if (journal_root / "snapshot").exists() or (journal_root / "staging").exists():
        raise RuntimeError("installed fsync rollback retry retained rollback artifacts after durable commit")
    same_hash_retry = _run(cwd=repo_root, env=dict(env), command=command, timeout=COMMAND_TIMEOUT_SECONDS)
    same_hash_payload = _require_success_payload(same_hash_retry, label="installed fsync same-hash retry")
    _require_receipt_identity(
        same_hash_payload,
        transaction_hash=transaction_hash,
        write_set_hash=write_set_hash,
    )
    if same_hash_payload != retry_payload:
        raise RuntimeError("installed fsync same-hash retry did not return the durable commit receipt")
    if _governed_fingerprint(repo_root) != after_retry:
        raise RuntimeError("installed fsync same-hash retry rewrote the committed governed package")
    return {
        "fsync_failure_returncode": failed.returncode,
        "fsync_retry_returncode": retried.returncode,
        "fsync_same_hash_retry_returncode": same_hash_retry.returncode,
        "fsync_journal_state_after_failure": str(failed_journal.get("state") or ""),
        "fsync_journal_state_after_retry": str(completed_journal.get("state") or ""),
        "fsync_failure_kind": failure_kind,
    }


def _install_repo(*, repo_root: Path, install_script: Path, env: Mapping[str, str]) -> None:
    repo_root.mkdir(parents=True, exist_ok=False)
    initialized = _run(cwd=repo_root, env=dict(env), command=["git", "init"], timeout=60)
    _require_success(initialized, label="installed commit recovery git init")
    installed = _run(
        cwd=repo_root,
        env=dict(env),
        command=["bash", str(install_script)],
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    _require_success(installed, label="installed commit recovery install")


def _compile_transaction(*, repo_root: Path, env: Mapping[str, str]) -> tuple[str, str, str]:
    proposed = _run(
        cwd=repo_root,
        env=dict(env),
        command=[
            "./.odylith/bin/odylith",
            "greenfield",
            "propose",
            "--repo-root",
            ".",
            "--prompt",
            _proof_prompt(),
            "--format",
            "json",
        ],
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    payload = _require_success_payload(proposed, label="installed commit recovery propose")
    transaction = _mapping(payload.get("product_create_transaction"))
    transaction_hash = str(transaction.get("transaction_hash") or "").strip()
    transaction_file = str(payload.get("transaction_file") or "").strip()
    if not transaction_hash or not transaction_file:
        raise RuntimeError("installed greenfield propose did not return a sealed transaction file and hash")
    transaction_path = Path(transaction_file).expanduser()
    if not transaction_path.is_absolute():
        transaction_path = repo_root / transaction_path
    sealed_transaction = _json_mapping(
        transaction_path.read_text(encoding="utf-8"),
        label="installed compiled Greenfield transaction",
    )
    sealed_hash = str(sealed_transaction.get("transaction_hash") or "").strip()
    sealed_package = _mapping(sealed_transaction.get("prewrite_package"))
    sealed_write_set = _mapping(sealed_package.get("repository_write_set"))
    write_set_hash = str(sealed_write_set.get("write_set_hash") or "").strip()
    if sealed_hash != transaction_hash or not write_set_hash:
        raise RuntimeError("installed greenfield propose returned an inconsistent sealed transaction identity")
    return transaction_file, transaction_hash, write_set_hash


def _run_faulted_create(*, repo_root: Path, env: Mapping[str, str], command: list[str], fault_script: str):
    runtime_python = repo_root / ".odylith" / "runtime" / "current" / "bin" / "python"
    if not runtime_python.is_file():
        raise RuntimeError(f"installed runtime Python is missing: {runtime_python}")
    isolated_env = dict(env)
    isolated_env.pop("PYTHONPATH", None)
    return _run(
        cwd=repo_root,
        env=isolated_env,
        command=[str(runtime_python), "-I", "-c", fault_script, *command[1:]],
        timeout=COMMAND_TIMEOUT_SECONDS,
    )


def _installed_release_env(*, base_url: str, version: str) -> dict[str, str]:
    """Keep every installed proof command independent from the maintainer source tree."""

    env = _local_release_env(base_url=base_url, version=version)
    env.pop("PYTHONPATH", None)
    return env


def _installed_runtime_identity(*, repo_root: Path, env: Mapping[str, str], version: str) -> dict[str, str]:
    """Verify that the proof imports Odylith from the freshly installed runtime."""

    runtime_python = repo_root / ".odylith" / "runtime" / "current" / "bin" / "python"
    identity = _run(
        cwd=repo_root,
        env=dict(env),
        command=[
            str(runtime_python),
            "-I",
            "-c",
            "import json, odylith; print(json.dumps({'module_path': odylith.__file__, 'version': getattr(odylith, '__version__', '')}))",
        ],
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    payload = _require_success_payload(identity, label="installed runtime identity")
    module_path = Path(str(payload.get("module_path") or "")).expanduser().resolve()
    runtime_root = (repo_root / ".odylith" / "runtime").resolve()
    try:
        module_path.relative_to(runtime_root)
    except ValueError as exc:
        raise RuntimeError(f"installed runtime imported Odylith outside its managed runtime: {module_path}") from exc
    installed_version = str(payload.get("version") or "").strip()
    if installed_version and installed_version != version:
        raise RuntimeError(
            f"installed runtime version mismatch: expected {version}, received {installed_version}"
        )
    return {
        "installed_runtime_module_path": str(module_path),
        "installed_runtime_version": installed_version,
    }


def _proof_prompt() -> str:
    """Reuse an approved high-variance case without duplicating product-language fixtures."""

    return default_cases()[0].prompt


def _create_command(*, transaction_file: str, transaction_hash: str) -> list[str]:
    return [
        "./.odylith/bin/odylith",
        "greenfield",
        "create",
        "--repo-root",
        ".",
        "--transaction-file",
        transaction_file,
        "--transaction-hash",
        transaction_hash,
        "--confirm",
        "--json",
    ]


def _journal_root(repo_root: Path, transaction_hash: str) -> Path:
    return repo_root / ".odylith" / "runtime" / "greenfield" / "create-journal" / transaction_hash


def _journal_state(*, repo_root: Path, transaction_hash: str) -> Mapping[str, Any]:
    state_path = _journal_root(repo_root, transaction_hash) / "state.v1.json"
    if not state_path.is_file():
        raise RuntimeError("installed create did not persist a recovery journal state")
    return _json_mapping(state_path.read_text(encoding="utf-8"), label="installed create journal state")


def _governed_fingerprint(repo_root: Path) -> dict[str, str]:
    root = Path(repo_root).expanduser().resolve()
    result: dict[str, str] = {}
    for relative_root in _GOVERNED_ROOTS:
        candidate = root / relative_root
        if candidate.is_symlink():
            raise RuntimeError(f"installed recovery proof found a governed symlink: {candidate}")
        if candidate.is_file():
            result[relative_root] = _file_fingerprint(candidate)
            continue
        if not candidate.is_dir():
            continue
        for file_path in sorted(path for path in candidate.rglob("*") if path.is_file()):
            if file_path.is_symlink():
                raise RuntimeError(f"installed recovery proof found a governed symlink: {file_path}")
            relative_path = file_path.relative_to(root).as_posix()
            result[relative_path] = _file_fingerprint(file_path)
    return result


def _interrupted_governed_write_path(
    *,
    repo_root: Path,
    before: Mapping[str, str],
    after: Mapping[str, str],
) -> Path:
    """Return a governed file proven to have changed in the interrupted write."""

    root = Path(repo_root).expanduser().resolve()
    changed_paths = sorted(path for path, fingerprint in after.items() if before.get(path) != fingerprint)
    if not changed_paths:
        raise RuntimeError("installed conflict proof did not observe a governed write after interruption")
    path = root / changed_paths[0]
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"installed conflict proof selected an unsafe governed file: {path}")
    return path


def _file_fingerprint(path: Path) -> str:
    stat_result = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"{stat_result.st_mode:o}:{stat_result.st_mtime_ns}:{digest}"


def _require_success(result: Any, *, label: str) -> None:
    if result.returncode != 0:
        raise RuntimeError(f"{label} failed: {_command_detail(result)}")


def _require_success_payload(result: Any, *, label: str) -> Mapping[str, Any]:
    _require_success(result, label=label)
    return _json_mapping(result.stdout, label=label)


def _require_error_payload(result: Any, *, label: str) -> Mapping[str, Any]:
    if result.returncode == 0:
        raise RuntimeError(f"{label} unexpectedly succeeded")
    payload = _json_mapping(result.stdout, label=label)
    if str(payload.get("mode") or "") != "error":
        raise RuntimeError(f"{label} did not return a commit error payload")
    return payload


def _require_receipt_identity(
    payload: Mapping[str, Any],
    *,
    transaction_hash: str,
    write_set_hash: str,
) -> None:
    transaction = _mapping(payload.get("product_create_transaction"))
    manifest = _mapping(payload.get("commit_manifest"))
    write_transaction = _mapping(manifest.get("write_transaction"))
    if str(transaction.get("transaction_hash") or "") != transaction_hash:
        raise RuntimeError("installed create receipt does not identify the requested transaction hash")
    if str(write_transaction.get("product_create_transaction_hash") or "") != transaction_hash:
        raise RuntimeError("installed create manifest does not identify the requested transaction hash")
    if str(write_transaction.get("repository_write_set_hash") or "") != write_set_hash:
        raise RuntimeError("installed create manifest does not identify the sealed repository write set")


def _json_mapping(value: str, *, label: str) -> Mapping[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} did not return JSON: {value[-600:]!r}") from exc
    if not isinstance(parsed, Mapping):
        raise RuntimeError(f"{label} did not return a JSON object")
    return parsed


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _command_detail(result: Any) -> str:
    stdout = str(getattr(result, "stdout", "") or "").strip()
    stderr = str(getattr(result, "stderr", "") or "").strip()
    output = "\n".join(part for part in (stdout, stderr) if part)
    return f"returncode={result.returncode}; output={output[-1000:]!r}"


__all__ = [
    "GreenfieldInstalledCommitRecoveryProof",
    "PROOF_SCOPE",
    "run_installed_commit_recovery_proof",
]
