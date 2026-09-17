"""Installed crash-recovery proof for sealed Greenfield create transactions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import shutil
import signal
from typing import Any
import uuid

from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    combined_prompt_evidence_source,
)
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal
from odylith.runtime.surfaces.compass_standup_brief_maintenance_worker import maintenance_worker_pids

import greenfield_commit_recovery_evidence as recovery_evidence
from greenfield_commit_recovery_evidence import as_mapping

from greenfield_process import run_command_with_group_timeout as _run
from greenfield_commit_recovery_cases import RECOVERY_CASE_SCOPE
from greenfield_commit_recovery_cases import recovery_case_evidence
from greenfield_commit_recovery_cases import select_recovery_case
from greenfield_commit_recovery_generation import FSYNC_FAILURE_FAULT as _FSYNC_FAILURE_FAULT
from greenfield_commit_recovery_generation import GENERATION_OBSERVATION_SCRIPT as _GENERATION_OBSERVATION_SCRIPT
from greenfield_commit_recovery_generation import SIGKILL_FAULT as _SIGKILL_FAULT
from greenfield_commit_recovery_generation import generation_observation_issues as _generation_observation_issues
from greenfield_commit_recovery_generation import require_aborted_generation_boundary as _require_aborted_generation_boundary
from greenfield_commit_recovery_generation import require_journal_generation_binding as _require_journal_generation_binding
from greenfield_commit_recovery_generation import (
    require_prepublication_generation_boundary as _require_prepublication_generation_boundary,
)
from greenfield_commit_recovery_generation import (
    require_published_generation_boundary as _require_published_generation_boundary,
)
from greenfield_matrix_release_artifacts import is_sha256
from greenfield_model_profiles import STANDARD_PROFILE_ID
from greenfield_model_profiles import model_profile_environment
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from local_release_smoke import _cleanup_smoke_temp_root
from local_release_smoke import _local_release_env
from local_release_smoke import _serve_directory


COMMAND_TIMEOUT_SECONDS = 300
PROOF_SCOPE = "real_installed_additive_write_sigkill_recovery_conflict_same_hash_retry_and_fsync_rollback"
_GOVERNED_ROOTS = ("odylith", "src/odylith/bundle/assets/odylith")


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
    product_facts_sha256: str = ""
    product_facts_hashes_by_phase: Mapping[str, str] = field(default_factory=dict)
    product_facts_hash_sources_by_phase: Mapping[str, str] = field(default_factory=dict)
    sigkill_generation_observations: Mapping[str, Any] = field(default_factory=dict)
    operator_conflict_generation_observations: Mapping[str, Any] = field(default_factory=dict)
    fsync_generation_observations: Mapping[str, Any] = field(default_factory=dict)
    recovery_case: Mapping[str, Any] = field(default_factory=dict)
    retained_recovery_roots: Mapping[str, str] = field(default_factory=dict)
    operator_conflict_resolution: Mapping[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == "passed" and not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "scope": PROOF_SCOPE,
            "recovery_case_scope": RECOVERY_CASE_SCOPE,
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
            "product_facts_sha256": self.product_facts_sha256,
            "product_facts_hashes_by_phase": dict(self.product_facts_hashes_by_phase),
            "product_facts_hash_sources_by_phase": dict(self.product_facts_hash_sources_by_phase),
            "sigkill_generation_observations": dict(self.sigkill_generation_observations),
            "operator_conflict_generation_observations": dict(self.operator_conflict_generation_observations),
            "fsync_generation_observations": dict(self.fsync_generation_observations),
            "recovery_case": dict(self.recovery_case),
            "retained_recovery_roots": dict(self.retained_recovery_roots),
            "operator_conflict_resolution": dict(self.operator_conflict_resolution),
        }


@dataclass(frozen=True)
class _CompiledRecoveryTransaction:
    """Sealed transaction identity and the authority that bound its input evidence."""

    transaction_file: str
    transaction_hash: str
    product_facts_hash: str
    write_set_hash: str
    intent_authority: Mapping[str, Any]


@dataclass(frozen=True)
class _RecoverySeed:
    """One installed baseline and one sealed transaction reused by every fault phase."""

    repo_root: Path
    transaction: _CompiledRecoveryTransaction


def run_installed_commit_recovery_proof(
    *,
    dist_dir: Path,
    version: str,
    temp_parent: Path,
    recovery_case: GreenfieldMatrixCase,
    evidence_output_dir: Path | None = None,
    retained_evidence_run_id: str = "",
    require_release_binding: bool = False,
    release_audit_binding: Mapping[str, Any] | None = None,
) -> GreenfieldInstalledCommitRecoveryProof:
    """Prove installed recovery against one deterministic campaign case."""

    run_root = Path(temp_parent).expanduser().resolve() / f"odylith-greenfield-commit-recovery-{uuid.uuid4().hex}"
    server = None
    issues: list[str] = []
    facts: dict[str, Any] = {}
    proposal_evidence = None
    proposal_sealed = False
    try:
        case_binding = recovery_case_evidence(
            recovery_case,
            require_release_binding=require_release_binding,
            release_audit_binding=release_audit_binding,
        )
        facts["recovery_case"] = case_binding
        if evidence_output_dir is None:
            raise RuntimeError("installed recovery proof requires an external evidence output directory")
        if retained_evidence_run_id and not is_sha256(retained_evidence_run_id):
            raise RuntimeError("installed recovery proof run identity is invalid")
        proposal_evidence = recovery_evidence.begin_proposal(output_dir=evidence_output_dir, temp_parent=temp_parent)
        release_dir = Path(dist_dir).expanduser().resolve()
        install_script = release_dir / "install.sh"
        if not install_script.is_file():
            raise RuntimeError(f"missing local release install script: {install_script}")
        run_root.mkdir(parents=True, exist_ok=False)
        server, base_url = _serve_directory(release_dir)
        env = _installed_release_env(base_url=base_url, version=version)
        seed = _prepare_recovery_seed(
            run_root=run_root,
            install_script=install_script,
            env=env,
            case=recovery_case,
            evidence=proposal_evidence,
        )
        recovery_evidence.finish_proposal(evidence=proposal_evidence, repo_root=seed.repo_root, status="passed", issues=[], run_id=retained_evidence_run_id)
        proposal_sealed = True
        sigkill_facts = _run_sigkill_recovery_phase(
            run_root=run_root,
            install_script=install_script,
            env=env,
            version=version,
            case=recovery_case,
            seed=seed,
        )
        facts.update(sigkill_facts)
        operator_conflict_facts = _run_operator_conflict_recovery_phase(
            run_root=run_root,
            install_script=install_script,
            env=env,
            case=recovery_case,
            seed=seed,
            evidence=proposal_evidence,
            run_id=retained_evidence_run_id,
        )
        facts.update(operator_conflict_facts)
        fsync_facts = _run_fsync_rollback_phase(
            run_root=run_root,
            install_script=install_script,
            env=env,
            case=recovery_case,
            seed=seed,
        )
        facts.update(fsync_facts)
        product_facts_hashes_by_phase = {
            "sigkill": str(sigkill_facts.get("product_facts_sha256") or ""),
            "operator_conflict": str(operator_conflict_facts.get("product_facts_sha256") or ""),
            "fsync": str(fsync_facts.get("product_facts_sha256") or ""),
        }
        product_facts_hash_sources_by_phase = {
            "sigkill": str(sigkill_facts.get("product_facts_hash_source") or ""),
            "operator_conflict": str(operator_conflict_facts.get("product_facts_hash_source") or ""),
            "fsync": str(fsync_facts.get("product_facts_hash_source") or ""),
        }
        product_facts_sha256 = product_facts_hashes_by_phase["sigkill"]
        if not is_sha256(product_facts_sha256) or any(
            phase_hash != product_facts_sha256 for phase_hash in product_facts_hashes_by_phase.values()
        ):
            raise RuntimeError("installed recovery phases did not retain the same sealed Product Intent facts hash")
        facts["product_facts_sha256"] = product_facts_sha256
        facts["product_facts_hashes_by_phase"] = product_facts_hashes_by_phase
        facts["product_facts_hash_sources_by_phase"] = product_facts_hash_sources_by_phase
        issues.extend(recovery_evidence.missing_required_evidence(facts, run_id=retained_evidence_run_id))
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        issues.append(str(exc))
    except BaseException as exc:
        issues.append(f"installed recovery proof interrupted: {type(exc).__name__}")
        raise
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if proposal_evidence is not None and not proposal_sealed:
            try:
                recovery_evidence.finish_proposal(evidence=proposal_evidence, repo_root=run_root, status="failed", issues=issues, run_id=retained_evidence_run_id)
            except (OSError, RuntimeError) as exc:
                issues.append(f"recovery proposal evidence retention failed: {exc}")
        try:
            facts["retained_recovery_roots"] = (
                {str(run_root): "failed proof; preserve fixtures for diagnosis"} if issues and run_root.exists()
                else _cleanup_recovery_run_root(run_root)
            )
            if facts["retained_recovery_roots"] and not issues:
                issues.append("installed recovery fixtures are not eligible for cleanup")
        except OSError as exc:
            issues.append(f"installed commit recovery proof cleanup failed: {exc}")
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
        product_facts_sha256=str(facts.get("product_facts_sha256") or ""),
        product_facts_hashes_by_phase=as_mapping(facts.get("product_facts_hashes_by_phase")),
        product_facts_hash_sources_by_phase=as_mapping(facts.get("product_facts_hash_sources_by_phase")),
        sigkill_generation_observations=as_mapping(facts.get("sigkill_generation_observations")),
        operator_conflict_generation_observations=as_mapping(
            facts.get("operator_conflict_generation_observations")
        ),
        fsync_generation_observations=as_mapping(facts.get("fsync_generation_observations")),
        recovery_case=as_mapping(facts.get("recovery_case")),
        retained_recovery_roots=as_mapping(facts.get("retained_recovery_roots")),
        operator_conflict_resolution=as_mapping(facts.get("operator_conflict_resolution")),
    )


def _cleanup_recovery_run_root(run_root: Path) -> dict[str, str]:
    """Remove settled fixtures, retaining conflict journals and unverifiable workers."""
    if run_root.is_symlink():
        raise OSError(f"unsafe recovery run root: {run_root}")
    if not run_root.exists():
        return {}
    retained: dict[str, str] = {}
    for repo in run_root.iterdir():
        try:
            if repo.is_symlink() or not repo.is_dir():
                raise RuntimeError("unsafe recovery fixture path")
            GreenfieldCommitJournal.require_settled_journals(repo_root=repo)
            if maintenance_worker_pids(repo_root=repo) != []:
                raise RuntimeError("recovery fixture has active or unverified workers")
        except (OSError, RuntimeError) as exc:
            retained[str(repo)] = str(exc)
            continue
        _cleanup_smoke_temp_root(repo)
        if repo.exists() or repo.is_symlink():
            raise OSError(f"terminal recovery fixture survived cleanup: {repo}")
    if not retained:
        _cleanup_smoke_temp_root(run_root)
        if run_root.exists() or run_root.is_symlink():
            raise OSError(f"terminal recovery root survived cleanup: {run_root}")
    return retained



def _run_sigkill_recovery_phase(
    *,
    run_root: Path,
    install_script: Path,
    env: Mapping[str, str],
    version: str,
    case: GreenfieldMatrixCase,
    seed: _RecoverySeed | None = None,
) -> dict[str, Any]:
    repo_root, compiled = _phase_repo_and_transaction(
        run_root=run_root,
        phase_name="sigkill-same-hash",
        install_script=install_script,
        env=env,
        case=case,
        seed=seed,
    )
    runtime_identity = _installed_runtime_identity(repo_root=repo_root, env=env, version=version)
    before = _governed_fingerprint(repo_root)
    generation_before = _installed_generation_observation(
        repo_root=repo_root,
        env=env,
        transaction_hash=compiled.transaction_hash,
        transaction_file=compiled.transaction_file,
    )
    command = _create_command(
        transaction_file=compiled.transaction_file,
        transaction_hash=compiled.transaction_hash,
    )
    crashed = _run_faulted_create(repo_root=repo_root, env=env, command=command, fault_script=_SIGKILL_FAULT)
    if crashed.returncode != -signal.SIGKILL:
        raise RuntimeError(
            "installed create did not terminate with SIGKILL after its first sealed write: "
            + _command_detail(crashed)
        )
    after_crash = _governed_fingerprint(repo_root)
    if not after_crash or after_crash == before:
        raise RuntimeError("SIGKILL proof did not observe a partial sealed governed write before recovery")
    generation_after_crash = _installed_generation_observation(
        repo_root=repo_root,
        env=env,
        transaction_hash=compiled.transaction_hash,
        transaction_file=compiled.transaction_file,
    )
    _require_prepublication_generation_boundary(
        before=generation_before,
        after=generation_after_crash,
        write_set_hash=compiled.write_set_hash,
        label="SIGKILL",
    )
    journal = _journal_state(repo_root=repo_root, transaction_hash=compiled.transaction_hash)
    if journal.get("state") != "projecting":
        raise RuntimeError("SIGKILL proof did not leave the installed commit journal in projecting state")
    _require_journal_generation_binding(journal=journal, observation=generation_after_crash)
    recovered = _run(cwd=repo_root, env=dict(env), command=command, timeout=COMMAND_TIMEOUT_SECONDS)
    recovery_payload = _require_success_payload(recovered, label="installed SIGKILL recovery create")
    recovered_product_facts_hash = _require_receipt_identity(
        recovery_payload,
        transaction_hash=compiled.transaction_hash,
        product_facts_hash=compiled.product_facts_hash,
        write_set_hash=compiled.write_set_hash,
    )
    after_recovery = _governed_fingerprint(repo_root)
    if not after_recovery or after_recovery == before:
        raise RuntimeError("installed SIGKILL recovery did not materialize the sealed governed package")
    completed_journal = _journal_state(repo_root=repo_root, transaction_hash=compiled.transaction_hash)
    if completed_journal.get("state") != "closed":
        raise RuntimeError("installed SIGKILL recovery did not produce a closed durable receipt")
    generation_after_recovery = _installed_generation_observation(
        repo_root=repo_root,
        env=env,
        transaction_hash=compiled.transaction_hash,
        transaction_file=compiled.transaction_file,
    )
    _require_published_generation_boundary(
        observation=generation_after_recovery,
        transaction_hash=compiled.transaction_hash,
        write_set_hash=compiled.write_set_hash,
        label="SIGKILL recovery",
    )
    journal_root = _journal_root(repo_root, compiled.transaction_hash)
    if any(path.exists() or path.is_symlink() for path in (journal_root / "snapshot", journal_root / "staging")):
        raise RuntimeError("installed SIGKILL recovery retained rollback artifacts after durable commit")
    retried = _run(cwd=repo_root, env=dict(env), command=command, timeout=COMMAND_TIMEOUT_SECONDS)
    retry_payload = _require_success_payload(retried, label="installed same-hash retry")
    retry_product_facts_hash = _require_receipt_identity(
        retry_payload,
        transaction_hash=compiled.transaction_hash,
        product_facts_hash=compiled.product_facts_hash,
        write_set_hash=compiled.write_set_hash,
    )
    if retry_product_facts_hash != recovered_product_facts_hash:
        raise RuntimeError("installed same-hash retry did not retain the recovery receipt Product Intent facts hash")
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
        "sigkill_generation_observations": {
            "before": generation_before,
            "after_crash": generation_after_crash,
            "after_recovery": generation_after_recovery,
        },
        "product_facts_sha256": recovered_product_facts_hash,
        "product_facts_hash_source": "success_receipt",
        **runtime_identity,
    }


def _run_operator_conflict_recovery_phase(
    *,
    run_root: Path,
    install_script: Path,
    env: Mapping[str, str],
    case: GreenfieldMatrixCase,
    evidence: recovery_evidence.RetainedEvidenceCase,
    run_id: str = "",
    seed: _RecoverySeed | None = None,
) -> dict[str, Any]:
    """Prove recovery preserves a later operator mutation instead of restoring over it."""

    repo_root, compiled = _phase_repo_and_transaction(
        run_root=run_root,
        phase_name="operator-conflict",
        install_script=install_script,
        env=env,
        case=case,
        seed=seed,
    )
    before = _governed_fingerprint(repo_root)
    generation_before = _installed_generation_observation(
        repo_root=repo_root,
        env=env,
        transaction_hash=compiled.transaction_hash,
        transaction_file=compiled.transaction_file,
    )
    command = _create_command(
        transaction_file=compiled.transaction_file,
        transaction_hash=compiled.transaction_hash,
    )
    crashed = _run_faulted_create(repo_root=repo_root, env=env, command=command, fault_script=_SIGKILL_FAULT)
    if crashed.returncode != -signal.SIGKILL:
        raise RuntimeError(
            "installed conflict proof did not terminate with SIGKILL after its first sealed write: "
            + _command_detail(crashed)
        )
    generation_after_crash = _installed_generation_observation(
        repo_root=repo_root,
        env=env,
        transaction_hash=compiled.transaction_hash,
        transaction_file=compiled.transaction_file,
    )
    _require_prepublication_generation_boundary(
        before=generation_before,
        after=generation_after_crash,
        write_set_hash=compiled.write_set_hash,
        label="operator-conflict SIGKILL",
    )
    partial_write = _interrupted_governed_write_path(
        repo_root=repo_root,
        before=before,
        after=_governed_fingerprint(repo_root),
    )
    post_crash_fingerprint = _governed_fingerprint(repo_root, include_directories=True)
    if maintenance_worker_pids(repo_root=repo_root) != []:
        raise RuntimeError("conflict injection has active or unverified workers")
    operator_bytes = f"operator mutation {uuid.uuid4().hex} retained by installed recovery proof\n".encode()
    original_bytes, original_stat = recovery_evidence.inject_operator_mutation(path=partial_write, operator_bytes=operator_bytes)
    operator_fingerprint = _governed_fingerprint(repo_root, include_directories=True)
    conflicted = _run(cwd=repo_root, env=dict(env), command=command, timeout=COMMAND_TIMEOUT_SECONDS)
    if _governed_fingerprint(repo_root, include_directories=True) != operator_fingerprint:
        raise RuntimeError("installed conflict recovery changed the governed tree")
    conflict_payload = _require_error_payload(conflicted, label="installed operator-conflict recovery create")
    commit_failure = as_mapping(conflict_payload.get("commit_failure"))
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
    journal = _journal_state(repo_root=repo_root, transaction_hash=compiled.transaction_hash)
    if journal.get("state") != "projecting":
        raise RuntimeError("installed conflict recovery changed the interrupted journal state")
    _require_journal_generation_binding(journal=journal, observation=generation_after_crash)
    conflict_product_facts_hash = _require_journal_receipt_identity(
        journal,
        transaction_hash=compiled.transaction_hash,
        product_facts_hash=compiled.product_facts_hash,
        write_set_hash=compiled.write_set_hash,
    )
    journal_root = _journal_root(repo_root, compiled.transaction_hash)
    recovery_path = Path(str(commit_failure.get("recovery_path") or "")).expanduser()
    if not recovery_path.is_absolute():
        recovery_path = repo_root / recovery_path
    if recovery_path.resolve(strict=False) != journal_root.resolve():
        raise RuntimeError("installed conflict recovery did not report its retained journal path")
    if not (journal_root / "snapshot").is_dir():
        raise RuntimeError("installed conflict recovery discarded the retained rollback snapshot")
    if partial_write.read_bytes() != operator_bytes:
        raise RuntimeError("installed conflict recovery overwrote the later operator mutation")
    generation_after_conflict = _installed_generation_observation(
        repo_root=repo_root,
        env=env,
        transaction_hash=compiled.transaction_hash,
        transaction_file=compiled.transaction_file,
    )
    if generation_after_conflict != generation_after_crash:
        raise RuntimeError("installed conflict recovery changed generation or pointer state")
    facts = {
        "operator_conflict_returncode": conflicted.returncode,
        "operator_conflict_failure_kind": failure_kind,
        "operator_conflict_rollback_status": rollback_status,
        "operator_conflict_journal_state": str(journal.get("state") or ""),
        "operator_mutation_preserved": True,
        "operator_conflict_snapshot_retained": True,
        "operator_conflict_recovery_path_bound": True,
        "operator_conflict_generation_observations": {
            "before": generation_before,
            "after_crash": generation_after_crash,
            "after_conflict": generation_after_conflict,
        },
        "product_facts_sha256": conflict_product_facts_hash,
        "product_facts_hash_source": "projecting_journal_commit_receipt",
        "transaction_hash": compiled.transaction_hash,
        "repository_write_set_hash": compiled.write_set_hash,
    }
    binding = {
        "transaction_hash": compiled.transaction_hash, "repository_write_set_hash": compiled.write_set_hash,
        "product_facts_sha256": compiled.product_facts_hash, "case_id": recovery_case_evidence(case)["id"],
        "prompt_sha256": hashlib.sha256(case.prompt.encode("utf-8")).hexdigest(),
        "command": command, "returncode": conflicted.returncode,
    }
    retained, inventory = recovery_evidence.seal_conflict(
        proposal=evidence, repo_root=repo_root, journal_root=journal_root,
        selected_path=partial_write, original_bytes=original_bytes, original_stat=original_stat,
        operator_bytes=operator_bytes, result=conflicted, facts=facts, binding=binding, run_id=run_id,
    )
    if (maintenance_worker_pids(repo_root=repo_root) != []
        or _governed_fingerprint(repo_root, include_directories=True) != operator_fingerprint
        or recovery_evidence.journal_inventory(journal_root) != inventory):
        raise RuntimeError("conflict evidence drifted or workers are active; fixture preserved")
    if _installed_generation_observation(repo_root=repo_root, env=env,
        transaction_hash=compiled.transaction_hash, transaction_file=compiled.transaction_file) != generation_after_conflict:
        raise RuntimeError("conflict generation drifted after evidence sealing; fixture preserved")
    recovery_evidence.retract_injected_mutation(
        path=partial_write, original_bytes=original_bytes, original_stat=original_stat, operator_bytes=operator_bytes,
    )
    if (_governed_fingerprint(repo_root, include_directories=True) != post_crash_fingerprint
        or recovery_evidence.journal_inventory(journal_root) != inventory):
        raise RuntimeError("conflict retraction did not restore only the injected mutation")
    recovered = _run(cwd=repo_root, env=dict(env), command=command, timeout=COMMAND_TIMEOUT_SECONDS)
    receipt = _require_success_payload(recovered, label="installed conflict settlement")
    _require_receipt_identity(receipt, transaction_hash=compiled.transaction_hash,
        product_facts_hash=compiled.product_facts_hash, write_set_hash=compiled.write_set_hash)
    completed = _journal_state(repo_root=repo_root, transaction_hash=compiled.transaction_hash)
    if completed.get("state") != "closed" or any(
        path.exists() or path.is_symlink() for path in (journal_root / "snapshot", journal_root / "staging")
    ):
        raise RuntimeError("installed conflict settlement did not close and retire rollback artifacts")
    published = _installed_generation_observation(repo_root=repo_root, env=env,
        transaction_hash=compiled.transaction_hash, transaction_file=compiled.transaction_file)
    _require_published_generation_boundary(observation=published, transaction_hash=compiled.transaction_hash,
        write_set_hash=compiled.write_set_hash, label="operator-conflict settlement")
    settled_fingerprint = _governed_fingerprint(repo_root, include_directories=True)
    settled_journal_inventory = recovery_evidence.journal_inventory(journal_root)
    retry = _run(cwd=repo_root, env=dict(env), command=command, timeout=COMMAND_TIMEOUT_SECONDS)
    if (_require_success_payload(retry, label="installed conflict same-hash retry") != receipt
        or _governed_fingerprint(repo_root, include_directories=True) != settled_fingerprint):
        raise RuntimeError("installed conflict same-hash retry changed the receipt or governed tree")
    if (recovery_evidence.journal_inventory(journal_root) != settled_journal_inventory
        or _installed_generation_observation(repo_root=repo_root, env=env,
            transaction_hash=compiled.transaction_hash, transaction_file=compiled.transaction_file) != published):
        raise RuntimeError("installed conflict same-hash retry changed journal or generation state")
    facts["operator_conflict_resolution"] = {
        "evidence": retained, "recovery_returncode": recovered.returncode, "retry_returncode": retry.returncode,
        "journal_state": completed["state"], "same_hash_retry_unchanged": True,
        "generation": published, "receipt": receipt, "binding": binding,
    }
    return facts


def _run_fsync_rollback_phase(
    *,
    run_root: Path,
    install_script: Path,
    env: Mapping[str, str],
    case: GreenfieldMatrixCase,
    seed: _RecoverySeed | None = None,
) -> dict[str, Any]:
    repo_root, compiled = _phase_repo_and_transaction(
        run_root=run_root,
        phase_name="fsync-rollback",
        install_script=install_script,
        env=env,
        case=case,
        seed=seed,
    )
    before = _governed_fingerprint(repo_root)
    generation_before = _installed_generation_observation(
        repo_root=repo_root,
        env=env,
        transaction_hash=compiled.transaction_hash,
        transaction_file=compiled.transaction_file,
    )
    command = _create_command(
        transaction_file=compiled.transaction_file,
        transaction_hash=compiled.transaction_hash,
    )
    failed = _run_faulted_create(repo_root=repo_root, env=env, command=command, fault_script=_FSYNC_FAILURE_FAULT)
    failure_payload = _require_error_payload(failed, label="installed fsync rollback create")
    commit_failure = as_mapping(failure_payload.get("commit_failure"))
    failure_kind = str(commit_failure.get("failure_kind") or "")
    if failure_kind != "post_confirm_commit_environment_or_io_failure":
        raise RuntimeError(f"installed fsync failure reported unexpected failure kind: {failure_kind or 'missing'}")
    if str(commit_failure.get("rollback_status") or "") != "rolled_back":
        raise RuntimeError("installed fsync failure did not report a completed rollback")
    if _governed_fingerprint(repo_root) != before:
        raise RuntimeError("installed fsync failure left partial governed writes after rollback")
    failed_journal = _journal_state(repo_root=repo_root, transaction_hash=compiled.transaction_hash)
    if failed_journal.get("state") != "aborted":
        raise RuntimeError("installed fsync failure did not persist an aborted journal state")
    generation_after_failure = _installed_generation_observation(
        repo_root=repo_root,
        env=env,
        transaction_hash=compiled.transaction_hash,
        transaction_file=compiled.transaction_file,
    )
    _require_aborted_generation_boundary(
        before=generation_before,
        after=generation_after_failure,
        label="fsync rollback",
    )
    journal_root = _journal_root(repo_root, compiled.transaction_hash)
    if any(path.exists() or path.is_symlink() for path in (journal_root / "snapshot", journal_root / "staging")):
        raise RuntimeError("installed fsync failure retained rollback artifacts after cleanup")
    retried = _run(cwd=repo_root, env=dict(env), command=command, timeout=COMMAND_TIMEOUT_SECONDS)
    retry_payload = _require_success_payload(retried, label="installed fsync rollback retry")
    retry_product_facts_hash = _require_receipt_identity(
        retry_payload,
        transaction_hash=compiled.transaction_hash,
        product_facts_hash=compiled.product_facts_hash,
        write_set_hash=compiled.write_set_hash,
    )
    after_retry = _governed_fingerprint(repo_root)
    if not after_retry:
        raise RuntimeError("installed fsync rollback retry did not materialize the sealed governed package")
    completed_journal = _journal_state(repo_root=repo_root, transaction_hash=compiled.transaction_hash)
    if completed_journal.get("state") != "closed":
        raise RuntimeError("installed fsync rollback retry did not produce a closed durable receipt")
    generation_after_retry = _installed_generation_observation(
        repo_root=repo_root,
        env=env,
        transaction_hash=compiled.transaction_hash,
        transaction_file=compiled.transaction_file,
    )
    _require_published_generation_boundary(
        observation=generation_after_retry,
        transaction_hash=compiled.transaction_hash,
        write_set_hash=compiled.write_set_hash,
        label="fsync retry",
    )
    if any(path.exists() or path.is_symlink() for path in (journal_root / "snapshot", journal_root / "staging")):
        raise RuntimeError("installed fsync rollback retry retained rollback artifacts after durable commit")
    same_hash_retry = _run(cwd=repo_root, env=dict(env), command=command, timeout=COMMAND_TIMEOUT_SECONDS)
    same_hash_payload = _require_success_payload(same_hash_retry, label="installed fsync same-hash retry")
    same_hash_product_facts_hash = _require_receipt_identity(
        same_hash_payload,
        transaction_hash=compiled.transaction_hash,
        product_facts_hash=compiled.product_facts_hash,
        write_set_hash=compiled.write_set_hash,
    )
    if same_hash_product_facts_hash != retry_product_facts_hash:
        raise RuntimeError("installed fsync same-hash retry did not retain the retry receipt Product Intent facts hash")
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
        "fsync_generation_observations": {
            "before": generation_before,
            "after_failure": generation_after_failure,
            "after_retry": generation_after_retry,
        },
        "product_facts_sha256": retry_product_facts_hash,
        "product_facts_hash_source": "retry_success_receipt",
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


def _prepare_recovery_seed(
    *,
    run_root: Path,
    install_script: Path,
    env: Mapping[str, str],
    case: GreenfieldMatrixCase,
    evidence: recovery_evidence.RetainedEvidenceCase | None = None,
) -> _RecoverySeed:
    """Compile once so recovery phases exercise identical sealed bytes."""

    repo_root = run_root / "sealed-transaction-seed"
    _install_repo(repo_root=repo_root, install_script=install_script, env=env)
    transaction = _compile_transaction(repo_root=repo_root, env=env, case=case, evidence=evidence)
    return _RecoverySeed(repo_root=repo_root, transaction=transaction)


def _phase_repo_and_transaction(
    *,
    run_root: Path,
    phase_name: str,
    install_script: Path,
    env: Mapping[str, str],
    case: GreenfieldMatrixCase,
    seed: _RecoverySeed | None,
) -> tuple[Path, _CompiledRecoveryTransaction]:
    repo_root = run_root / phase_name
    if seed is None:
        _install_repo(repo_root=repo_root, install_script=install_script, env=env)
        return repo_root, _compile_transaction(repo_root=repo_root, env=env, case=case)
    _clone_recovery_seed_repo(seed_repo=seed.repo_root, repo_root=repo_root)
    return repo_root, _transaction_for_phase(seed=seed)


def _clone_recovery_seed_repo(*, seed_repo: Path, repo_root: Path) -> None:
    """Copy one installed seed while keeping its managed runtime phase-local."""

    seed_runtime_root = seed_repo / ".odylith/runtime"
    seed_versions_root = seed_runtime_root / "versions"
    seed_current = seed_runtime_root / "current"
    if not seed_current.is_symlink():
        raise RuntimeError("installed recovery seed does not have an active runtime symlink")
    try:
        active_relative = seed_current.resolve(strict=True).relative_to(seed_versions_root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise RuntimeError("installed recovery seed active runtime is outside its managed versions") from exc
    if len(active_relative.parts) != 1:
        raise RuntimeError("installed recovery seed active runtime is not one managed version")

    shutil.copytree(seed_repo, repo_root, symlinks=True)
    cloned_runtime_root = repo_root / ".odylith/runtime"
    cloned_current = cloned_runtime_root / "current"
    cloned_current.unlink()
    cloned_current.symlink_to(Path("versions") / active_relative, target_is_directory=True)


def _transaction_for_phase(*, seed: _RecoverySeed) -> _CompiledRecoveryTransaction:
    transaction = seed.transaction
    transaction_path = Path(transaction.transaction_file).expanduser()
    if transaction_path.is_absolute():
        try:
            transaction_file = str(transaction_path.resolve().relative_to(seed.repo_root.resolve()))
        except ValueError as exc:
            raise RuntimeError("installed recovery transaction file is outside its sealed seed repo") from exc
    else:
        transaction_file = str(transaction_path)
    return _CompiledRecoveryTransaction(
        transaction_file=transaction_file,
        transaction_hash=transaction.transaction_hash,
        product_facts_hash=transaction.product_facts_hash,
        write_set_hash=transaction.write_set_hash,
        intent_authority=transaction.intent_authority,
    )


def _compile_transaction(
    *,
    repo_root: Path,
    env: Mapping[str, str],
    case: GreenfieldMatrixCase,
    evidence: recovery_evidence.RetainedEvidenceCase | None = None,
) -> _CompiledRecoveryTransaction:
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
    proposed = recovery_evidence.run_proposal(
        evidence=evidence, runner=_run,
        cwd=repo_root,
        env=dict(env),
        command=command,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    payload = _require_success_payload(proposed, label="installed commit recovery propose")
    transaction = as_mapping(payload.get("product_create_transaction"))
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
    sealed_package = as_mapping(sealed_transaction.get("prewrite_package"))
    sealed_write_set = as_mapping(sealed_package.get("repository_write_set"))
    write_set_hash = str(sealed_write_set.get("write_set_hash") or "").strip()
    intent_authority = as_mapping(sealed_transaction.get("intent_authority"))
    product_facts_hash = str(intent_authority.get("product_facts_sha256") or "").strip()
    if sealed_hash != transaction_hash or not write_set_hash or not is_sha256(product_facts_hash):
        raise RuntimeError("installed greenfield propose returned an inconsistent sealed transaction identity")
    if str(transaction.get("product_facts_sha256") or "").strip() != product_facts_hash:
        raise RuntimeError("installed greenfield propose did not return the sealed Product Intent facts hash")
    _require_case_evidence_bound_to_transaction(case=case, intent_authority=intent_authority)
    if evidence is not None:
        recovery_evidence.record_retained_case_bytes(evidence, "semantic/product-create-transaction.v1.json", transaction_path.read_bytes())
    return _CompiledRecoveryTransaction(
        transaction_file=transaction_file,
        transaction_hash=transaction_hash,
        product_facts_hash=product_facts_hash,
        write_set_hash=write_set_hash,
        intent_authority=intent_authority,
    )


def _require_case_evidence_bound_to_transaction(
    *,
    case: GreenfieldMatrixCase,
    intent_authority: Mapping[str, Any],
) -> None:
    """Prove the sealed transaction authority contains the exact recovery inputs."""

    confirmed_intent = str(case.confirmed_intent_markdown or "").strip()
    expected_source_format = "operator_prompt_with_edit_evidence" if confirmed_intent else "operator_prompt"
    if str(intent_authority.get("source_format") or "").strip() != expected_source_format:
        raise RuntimeError("installed greenfield transaction authority did not record the expected input format")
    expected_evidence = combined_prompt_evidence_source(
        prompt=case.prompt,
        edit_evidence=confirmed_intent,
    )
    expected_hash = hashlib.sha256(expected_evidence.encode("utf-8")).hexdigest()
    if str(intent_authority.get("markdown_source_sha256") or "").strip() != expected_hash:
        raise RuntimeError("installed greenfield transaction authority did not bind the exact prompt and edit evidence")


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

    env = model_profile_environment(
        STANDARD_PROFILE_ID,
        _local_release_env(base_url=base_url, version=version),
    )
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


def _installed_generation_observation(
    *,
    repo_root: Path,
    env: Mapping[str, str],
    transaction_hash: str,
    transaction_file: str,
) -> Mapping[str, Any]:
    """Observe the installed pointer, canonical pin, and transaction generation together."""

    runtime_python = repo_root / ".odylith" / "runtime" / "current" / "bin" / "python"
    observed = _run(
        cwd=repo_root,
        env=dict(env),
        command=[
            str(runtime_python),
            "-I",
            "-c",
            _GENERATION_OBSERVATION_SCRIPT,
            transaction_hash,
            transaction_file,
        ],
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    return _require_success_payload(observed, label="installed generation observation")


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


def _governed_fingerprint(repo_root: Path, *, include_directories: bool = False) -> dict[str, str]:
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
        if include_directories:
            result[relative_root + "/"] = "directory"
        for file_path in sorted(candidate.rglob("*")):
            if file_path.is_symlink():
                raise RuntimeError(f"installed recovery proof found a governed symlink: {file_path}")
            relative_path = file_path.relative_to(root).as_posix()
            if file_path.is_dir():
                if include_directories:
                    result[relative_path + "/"] = "directory"
            elif file_path.is_file():
                result[relative_path] = _file_fingerprint(file_path)
            else:
                raise RuntimeError(f"installed recovery proof found an unsafe governed entry: {file_path}")
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
    product_facts_hash: str,
    write_set_hash: str,
) -> str:
    observed_product_facts_hash = _receipt_product_facts_hash(
        payload,
        transaction_hash=transaction_hash,
        write_set_hash=write_set_hash,
    )
    if observed_product_facts_hash != product_facts_hash:
        raise RuntimeError("installed create receipt does not identify the sealed Product Intent facts hash")
    return observed_product_facts_hash


def _require_journal_receipt_identity(
    journal: Mapping[str, Any],
    *,
    transaction_hash: str,
    product_facts_hash: str,
    write_set_hash: str,
) -> str:
    if str(journal.get("transaction_hash") or "") != transaction_hash:
        raise RuntimeError("installed conflict recovery journal does not identify the requested transaction hash")
    if str(journal.get("repository_write_set_hash") or "") != write_set_hash:
        raise RuntimeError("installed conflict recovery journal does not identify the sealed repository write set")
    commit_result = as_mapping(journal.get("commit_result"))
    if not commit_result:
        raise RuntimeError("installed conflict recovery journal did not retain its sealed commit receipt")
    return _require_receipt_identity(
        commit_result,
        transaction_hash=transaction_hash,
        product_facts_hash=product_facts_hash,
        write_set_hash=write_set_hash,
    )


def _receipt_product_facts_hash(
    payload: Mapping[str, Any],
    *,
    transaction_hash: str,
    write_set_hash: str,
) -> str:
    transaction = as_mapping(payload.get("product_create_transaction"))
    manifest = as_mapping(payload.get("commit_manifest"))
    manifest_transaction = as_mapping(manifest.get("product_create_transaction"))
    write_transaction = as_mapping(manifest.get("write_transaction"))
    observed_product_facts_hash = str(transaction.get("product_facts_sha256") or "")
    if str(transaction.get("transaction_hash") or "") != transaction_hash:
        raise RuntimeError("installed create receipt does not identify the requested transaction hash")
    if not is_sha256(observed_product_facts_hash):
        raise RuntimeError("installed create receipt does not identify a valid sealed Product Intent facts hash")
    if str(manifest_transaction.get("product_facts_sha256") or "") != observed_product_facts_hash:
        raise RuntimeError("installed create manifest does not identify the sealed Product Intent facts hash")
    if str(write_transaction.get("product_create_transaction_hash") or "") != transaction_hash:
        raise RuntimeError("installed create manifest does not identify the requested transaction hash")
    if str(write_transaction.get("product_facts_sha256") or "") != observed_product_facts_hash:
        raise RuntimeError("installed create manifest does not identify the sealed Product Intent facts hash")
    if str(write_transaction.get("repository_write_set_hash") or "") != write_set_hash:
        raise RuntimeError("installed create manifest does not identify the sealed repository write set")
    return observed_product_facts_hash


def _json_mapping(value: str, *, label: str) -> Mapping[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} did not return JSON: {value[-600:]!r}") from exc
    if not isinstance(parsed, Mapping):
        raise RuntimeError(f"{label} did not return a JSON object")
    return parsed


def _command_detail(result: Any) -> str:
    stdout = str(getattr(result, "stdout", "") or "").strip()
    stderr = str(getattr(result, "stderr", "") or "").strip()
    output = "\n".join(part for part in (stdout, stderr) if part)
    return f"returncode={result.returncode}; output={output[-1000:]!r}"
