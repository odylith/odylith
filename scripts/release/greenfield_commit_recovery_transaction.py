"""Prepare one sealed transaction shared by every installed recovery phase."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    combined_prompt_evidence_source,
)

import greenfield_commit_recovery_evidence as recovery_evidence
from greenfield_commit_recovery_evidence import as_mapping
from greenfield_matrix_host_candidate import HostCandidateFlow
from greenfield_matrix_host_candidate import post_receipt_runtime_env
from greenfield_matrix_host_candidate import resolve_trusted_codex_executable
from greenfield_matrix_host_candidate import run_host_candidate_flow
from greenfield_matrix_release_artifacts import is_sha256
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from greenfield_process import run_command_with_group_timeout as _run


COMMAND_TIMEOUT_SECONDS = 300


@dataclass(frozen=True)
class RecoveryTransaction:
    """Sealed transaction identity and the authority that bound its input evidence."""

    transaction_file: str
    transaction_hash: str
    product_facts_hash: str
    write_set_hash: str
    intent_authority: Mapping[str, Any]


@dataclass(frozen=True)
class RecoverySeed:
    """One installed baseline and one sealed transaction reused by every fault phase."""

    repo_root: Path
    transaction: RecoveryTransaction


def prepare_recovery_seed(
    *,
    run_root: Path,
    install_script: Path,
    env: Mapping[str, str],
    case: GreenfieldMatrixCase,
    evidence: recovery_evidence.RetainedEvidenceCase | None = None,
    host_candidate_argv: Sequence[str] = (),
) -> RecoverySeed:
    """Install and compile once so every recovery phase exercises identical sealed bytes."""

    repo_root = run_root / "sealed-transaction-seed"
    _install_repo(repo_root=repo_root, install_script=install_script, env=env)
    transaction = compile_transaction(
        repo_root=repo_root,
        env=env,
        case=case,
        evidence=evidence,
        host_candidate_argv=host_candidate_argv,
    )
    return RecoverySeed(repo_root=repo_root, transaction=transaction)


def phase_repo_and_transaction(
    *,
    run_root: Path,
    phase_name: str,
    install_script: Path,
    env: Mapping[str, str],
    case: GreenfieldMatrixCase,
    seed: RecoverySeed | None,
) -> tuple[Path, RecoveryTransaction]:
    """Materialize a phase-local repository bound to the campaign transaction."""

    repo_root = run_root / phase_name
    if seed is None:
        _install_repo(repo_root=repo_root, install_script=install_script, env=env)
        return repo_root, compile_transaction(repo_root=repo_root, env=env, case=case)
    clone_recovery_seed_repo(seed_repo=seed.repo_root, repo_root=repo_root)
    return repo_root, _transaction_for_phase(seed=seed)


def clone_recovery_seed_repo(*, seed_repo: Path, repo_root: Path) -> None:
    """Copy one installed seed while keeping its managed runtime phase-local."""

    seed_runtime_root = seed_repo / ".odylith/runtime"
    seed_versions_root = seed_runtime_root / "versions"
    seed_current = seed_runtime_root / "current"
    if not seed_current.is_symlink():
        raise RuntimeError("installed recovery seed does not have an active runtime symlink")
    try:
        active_relative = seed_current.resolve(strict=True).relative_to(
            seed_versions_root.resolve(strict=True)
        )
    except (OSError, ValueError) as exc:
        raise RuntimeError(
            "installed recovery seed active runtime is outside its managed versions"
        ) from exc
    if len(active_relative.parts) != 1:
        raise RuntimeError("installed recovery seed active runtime is not one managed version")

    shutil.copytree(seed_repo, repo_root, symlinks=True)
    cloned_current = repo_root / ".odylith/runtime/current"
    cloned_current.unlink()
    cloned_current.symlink_to(Path("versions") / active_relative, target_is_directory=True)


def compile_transaction(
    *,
    repo_root: Path,
    env: Mapping[str, str],
    case: GreenfieldMatrixCase,
    evidence: recovery_evidence.RetainedEvidenceCase | None = None,
    host_candidate_argv: Sequence[str] = (),
) -> RecoveryTransaction:
    """Author and verify the single transaction consumed by the recovery campaign."""

    command = [
        "./.odylith/bin/odylith",
        "greenfield",
        "propose",
        "--repo-root",
        ".",
        "--prompt",
        case.prompt,
        "--format",
        "json",
    ]
    confirmed_intent = str(case.confirmed_intent_markdown or "").strip()
    if confirmed_intent:
        command.extend(["--edit", confirmed_intent])
    if not host_candidate_argv:
        raise RuntimeError(
            "installed recovery proof requires the one-authority host candidate argv"
        )

    def invoke_installed(installed_command: Sequence[str], timeout: float) -> Any:
        return _run(
            cwd=repo_root,
            env=dict(env),
            command=list(installed_command),
            timeout=timeout,
        )

    def invoke_propose(candidate_path: Path, gate_path: Path, timeout: float) -> Any:
        candidate_command = [
            *command,
            "--candidate-file", str(candidate_path),
            "--gate-file", str(gate_path),
        ]
        return recovery_evidence.run_proposal(
            evidence=evidence,
            runner=_run,
            cwd=repo_root,
            env=post_receipt_runtime_env(env),
            command=candidate_command,
            timeout=timeout,
        )

    observe = None
    retain_candidate_bytes = None
    if evidence is not None:
        observe = lambda payload: recovery_evidence.record_retained_case_json(
            evidence,
            "semantic/host-authoring-observation.v1.json",
            dict(payload),
        )
        retain_candidate_bytes = lambda value: recovery_evidence.record_retained_case_bytes(
            evidence,
            "semantic/host-candidate.raw.v1.json",
            value,
        )
    proposed = run_host_candidate_flow(
        HostCandidateFlow(
            repo_root=repo_root,
            temp_parent=repo_root.parent,
            host_argv=tuple(str(value) for value in host_candidate_argv),
            prompt=case.prompt,
            edit_evidence=confirmed_intent,
            timeout=COMMAND_TIMEOUT_SECONDS,
            env=env,
            trusted_codex_executable=resolve_trusted_codex_executable(environ=env),
            expected_model=str(env.get("ODYLITH_REASONING_MODEL") or ""),
            expected_reasoning_effort=str(
                env.get("ODYLITH_REASONING_CODEX_REASONING_EFFORT") or ""
            ),
            invoke_installed=invoke_installed,
            invoke_propose=invoke_propose,
            observe=observe,
            retain_candidate_bytes=retain_candidate_bytes,
        )
    )
    payload = require_success_payload(proposed, label="installed commit recovery propose")
    transaction = as_mapping(payload.get("product_create_transaction"))
    transaction_hash = str(transaction.get("transaction_hash") or "").strip()
    transaction_file = str(payload.get("transaction_file") or "").strip()
    if not transaction_hash or not transaction_file:
        raise RuntimeError(
            "installed greenfield propose did not return a sealed transaction file and hash"
        )
    transaction_path = Path(transaction_file).expanduser()
    if not transaction_path.is_absolute():
        transaction_path = repo_root / transaction_path
    sealed_transaction = json_mapping(
        transaction_path.read_text(encoding="utf-8"),
        label="installed compiled Greenfield transaction",
    )
    sealed_hash = str(sealed_transaction.get("transaction_hash") or "").strip()
    sealed_package = as_mapping(sealed_transaction.get("prewrite_package"))
    sealed_write_set = as_mapping(sealed_package.get("repository_write_set"))
    write_set_hash = str(sealed_write_set.get("write_set_hash") or "").strip()
    intent_authority = as_mapping(sealed_transaction.get("intent_authority"))
    product_facts_hash = str(intent_authority.get("product_facts_sha256") or "").strip()
    if sealed_hash != transaction_hash or not write_set_hash or not is_sha256(product_facts_hash):
        raise RuntimeError(
            "installed greenfield propose returned an inconsistent sealed transaction identity"
        )
    if str(transaction.get("product_facts_sha256") or "").strip() != product_facts_hash:
        raise RuntimeError(
            "installed greenfield propose did not return the sealed Product Intent facts hash"
        )
    _require_case_evidence_bound_to_transaction(case=case, intent_authority=intent_authority)
    if evidence is not None:
        recovery_evidence.record_retained_case_bytes(
            evidence,
            "semantic/product-create-transaction.v1.json",
            transaction_path.read_bytes(),
        )
    return RecoveryTransaction(
        transaction_file=transaction_file,
        transaction_hash=transaction_hash,
        product_facts_hash=product_facts_hash,
        write_set_hash=write_set_hash,
        intent_authority=intent_authority,
    )


def require_success_payload(result: Any, *, label: str) -> Mapping[str, Any]:
    """Require a successful command and decode its JSON object payload."""

    if result.returncode != 0:
        raise RuntimeError(f"{label} failed: {command_detail(result)}")
    return json_mapping(result.stdout, label=label)


def json_mapping(value: str, *, label: str) -> Mapping[str, Any]:
    """Decode one command payload while preserving the release proof error contract."""

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} did not return JSON: {value[-600:]!r}") from exc
    if not isinstance(parsed, Mapping):
        raise RuntimeError(f"{label} did not return a JSON object")
    return parsed


def command_detail(result: Any) -> str:
    """Format bounded command failure output for recovery proof diagnostics."""

    stdout = str(getattr(result, "stdout", "") or "").strip()
    stderr = str(getattr(result, "stderr", "") or "").strip()
    output = "\n".join(part for part in (stdout, stderr) if part)
    return f"returncode={result.returncode}; output={output[-1000:]!r}"


def _install_repo(*, repo_root: Path, install_script: Path, env: Mapping[str, str]) -> None:
    repo_root.mkdir(parents=True, exist_ok=False)
    initialized = _run(cwd=repo_root, env=dict(env), command=["git", "init"], timeout=60)
    if initialized.returncode != 0:
        raise RuntimeError(
            "installed commit recovery git init failed: " + command_detail(initialized)
        )
    installed = _run(
        cwd=repo_root,
        env=dict(env),
        command=["bash", str(install_script)],
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    if installed.returncode != 0:
        raise RuntimeError(
            "installed commit recovery install failed: " + command_detail(installed)
        )


def _transaction_for_phase(*, seed: RecoverySeed) -> RecoveryTransaction:
    transaction = seed.transaction
    transaction_path = Path(transaction.transaction_file).expanduser()
    if transaction_path.is_absolute():
        try:
            transaction_file = str(
                transaction_path.resolve().relative_to(seed.repo_root.resolve())
            )
        except ValueError as exc:
            raise RuntimeError(
                "installed recovery transaction file is outside its sealed seed repo"
            ) from exc
    else:
        transaction_file = str(transaction_path)
    return RecoveryTransaction(
        transaction_file=transaction_file,
        transaction_hash=transaction.transaction_hash,
        product_facts_hash=transaction.product_facts_hash,
        write_set_hash=transaction.write_set_hash,
        intent_authority=transaction.intent_authority,
    )


def _require_case_evidence_bound_to_transaction(
    *,
    case: GreenfieldMatrixCase,
    intent_authority: Mapping[str, Any],
) -> None:
    confirmed_intent = str(case.confirmed_intent_markdown or "").strip()
    expected_source_format = (
        "operator_prompt_with_edit_evidence" if confirmed_intent else "operator_prompt"
    )
    if str(intent_authority.get("source_format") or "").strip() != expected_source_format:
        raise RuntimeError(
            "installed greenfield transaction authority did not record the expected input format"
        )
    expected_evidence = combined_prompt_evidence_source(
        prompt=case.prompt,
        edit_evidence=confirmed_intent,
    )
    expected_hash = hashlib.sha256(expected_evidence.encode("utf-8")).hexdigest()
    if str(intent_authority.get("markdown_source_sha256") or "").strip() != expected_hash:
        raise RuntimeError(
            "installed greenfield transaction authority did not bind the exact prompt and edit evidence"
        )
