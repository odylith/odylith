"""Installed crash-recovery proof for sealed Greenfield create transactions."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import shutil
import signal
import sys
from typing import Any
import uuid

from greenfield_process import run_command_with_group_timeout as _run
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
from local_release_smoke import _cleanup_smoke_temp_root
from local_release_smoke import _local_release_env
from local_release_smoke import _serve_directory


COMMAND_TIMEOUT_SECONDS = 300
PROOF_SCOPE = "real_installed_additive_write_sigkill_recovery_conflict_same_hash_retry_and_fsync_rollback"
RECOVERY_CASE_SCOPE = "semantic-intent-v3-release-fixture"
_GOVERNED_ROOTS = ("odylith", "src/odylith/bundle/assets/odylith")
_DEFAULT_SEMANTIC_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "greenfield-semantic-smoke.v4.json"


@dataclass(frozen=True)
class SemanticRecoveryCase:
    """One source-controlled graph packet used only to exercise transaction laws."""

    case_id: str
    prompt: str
    packet: Mapping[str, Any]


def load_semantic_recovery_case(
    fixture_path: Path = _DEFAULT_SEMANTIC_FIXTURE,
) -> SemanticRecoveryCase:
    """Load the same graph packet used by the installed release smoke."""

    path = Path(fixture_path).expanduser().resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"installed recovery semantic fixture is unreadable: {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise RuntimeError("installed recovery semantic fixture must be a JSON object")
    case_id = str(payload.get("case_id") or "").strip()
    prompt = str(payload.get("prompt") or "").strip()
    packet = payload.get("packet")
    if not case_id or not prompt or not isinstance(packet, Mapping):
        raise RuntimeError("installed recovery semantic fixture is incomplete")
    if packet.get("version") != "odylith.greenfield.semantic-intent-packet.v4":
        raise RuntimeError("installed recovery semantic fixture must use Semantic Intent packet v3")
    semantic_intent = packet.get("semantic_intent")
    if not isinstance(semantic_intent, Mapping) or semantic_intent.get("status") != "complete":
        raise RuntimeError("installed recovery semantic fixture must contain a complete Semantic Intent graph")
    return SemanticRecoveryCase(case_id=case_id, prompt=prompt, packet=dict(packet))


def semantic_recovery_case_evidence(case: SemanticRecoveryCase) -> dict[str, str]:
    semantic_intent = _mapping(case.packet.get("semantic_intent"))
    return {
        "id": case.case_id,
        "binding_scope": RECOVERY_CASE_SCOPE,
        "prompt_sha256": hashlib.sha256(case.prompt.encode("utf-8")).hexdigest(),
        "evidence_sha256": str(case.packet.get("evidence_sha256") or ""),
        "semantic_intent_sha256": hashlib.sha256(
            json.dumps(semantic_intent, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")
        ).hexdigest(),
    }


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
        }


@dataclass(frozen=True)
class _CompiledRecoveryTransaction:
    """Sealed transaction identity and the authority that bound its input evidence."""

    transaction_file: str
    transaction_hash: str
    product_facts_hash: str
    write_set_hash: str
    intent_authority: Mapping[str, Any]


def run_installed_commit_recovery_proof(
    *,
    dist_dir: Path,
    version: str,
    temp_parent: Path,
    recovery_case: SemanticRecoveryCase | None = None,
) -> GreenfieldInstalledCommitRecoveryProof:
    """Prove installed recovery against one validated Semantic Intent packet."""

    run_root = Path(temp_parent).expanduser().resolve() / f"odylith-greenfield-commit-recovery-{uuid.uuid4().hex}"
    server = None
    issues: list[str] = []
    facts: dict[str, Any] = {}
    try:
        selected_case = recovery_case or load_semantic_recovery_case()
        facts["recovery_case"] = semantic_recovery_case_evidence(selected_case)
        release_dir = Path(dist_dir).expanduser().resolve()
        install_script = release_dir / "install.sh"
        if not install_script.is_file():
            raise RuntimeError(f"missing local release install script: {install_script}")
        run_root.mkdir(parents=True, exist_ok=False)
        server, base_url = _serve_directory(release_dir)
        env = _installed_release_env(base_url=base_url, version=version)
        sigkill_facts = _run_sigkill_recovery_phase(
            run_root=run_root,
            install_script=install_script,
            env=env,
            version=version,
            case=selected_case,
        )
        facts.update(sigkill_facts)
        operator_conflict_facts = _run_operator_conflict_recovery_phase(
            run_root=run_root,
            install_script=install_script,
            env=env,
            case=selected_case,
        )
        facts.update(operator_conflict_facts)
        fsync_facts = _run_fsync_rollback_phase(
            run_root=run_root,
            install_script=install_script,
            env=env,
            case=selected_case,
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
        product_facts_sha256=str(facts.get("product_facts_sha256") or ""),
        product_facts_hashes_by_phase=_mapping(facts.get("product_facts_hashes_by_phase")),
        product_facts_hash_sources_by_phase=_mapping(facts.get("product_facts_hash_sources_by_phase")),
        sigkill_generation_observations=_mapping(facts.get("sigkill_generation_observations")),
        operator_conflict_generation_observations=_mapping(
            facts.get("operator_conflict_generation_observations")
        ),
        fsync_generation_observations=_mapping(facts.get("fsync_generation_observations")),
        recovery_case=_mapping(facts.get("recovery_case")),
    )


def _missing_required_evidence(facts: Mapping[str, Any]) -> list[str]:
    """Keep a partial proof record from being published as a successful proof."""

    missing: list[str] = []
    required_values = {
        "journal_state_after_crash": "projecting",
        "journal_state_after_recovery": "closed",
        "fsync_journal_state_after_failure": "aborted",
        "fsync_journal_state_after_retry": "closed",
        "fsync_failure_kind": "post_confirm_commit_environment_or_io_failure",
        "operator_conflict_failure_kind": "post_confirm_commit_recovery_conflict",
        "operator_conflict_rollback_status": "not_started",
        "operator_conflict_journal_state": "projecting",
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
    if not is_sha256(facts.get("product_facts_sha256")):
        missing.append("installed recovery proof did not record a valid Product Intent facts hash")
    phase_hashes = _mapping(facts.get("product_facts_hashes_by_phase"))
    phase_sources = _mapping(facts.get("product_facts_hash_sources_by_phase"))
    required_phase_sources = {
        "sigkill": "success_receipt",
        "operator_conflict": "projecting_journal_commit_receipt",
        "fsync": "retry_success_receipt",
    }
    for phase, required_source in required_phase_sources.items():
        if phase_hashes.get(phase) != facts.get("product_facts_sha256"):
            missing.append(f"installed recovery proof did not retain the sealed Product Intent facts hash for {phase}")
        if phase_sources.get(phase) != required_source:
            missing.append(f"installed recovery proof did not record the observed Product Intent facts source for {phase}")
    missing.extend(_generation_observation_issues(facts))
    recovery_case = _mapping(facts.get("recovery_case"))
    for key in ("id", "prompt_sha256"):
        if not str(recovery_case.get(key) or "").strip():
            missing.append(f"installed recovery proof did not record required recovery_case.{key}")
    if recovery_case.get("binding_scope") != RECOVERY_CASE_SCOPE:
        missing.append("installed recovery proof did not bind the Semantic Intent release fixture")
    for key in ("evidence_sha256", "semantic_intent_sha256"):
        if not is_sha256(recovery_case.get(key)):
            missing.append(f"installed recovery proof did not record required recovery_case.{key}")
    return missing


def _run_sigkill_recovery_phase(
    *,
    run_root: Path,
    install_script: Path,
    env: Mapping[str, str],
    version: str,
    case: SemanticRecoveryCase,
) -> dict[str, Any]:
    repo_root = run_root / "sigkill-same-hash"
    _install_repo(repo_root=repo_root, install_script=install_script, env=env)
    runtime_identity = _installed_runtime_identity(repo_root=repo_root, env=env, version=version)
    compiled = _compile_transaction(
        repo_root=repo_root,
        env=env,
        case=case,
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
    if (journal_root / "snapshot").exists() or (journal_root / "staging").exists():
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
    case: SemanticRecoveryCase,
) -> dict[str, Any]:
    """Prove recovery preserves a later operator mutation instead of restoring over it."""

    repo_root = run_root / "operator-conflict"
    _install_repo(repo_root=repo_root, install_script=install_script, env=env)
    compiled = _compile_transaction(
        repo_root=repo_root,
        env=env,
        case=case,
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
    return {
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
    }


def _run_fsync_rollback_phase(
    *,
    run_root: Path,
    install_script: Path,
    env: Mapping[str, str],
    case: SemanticRecoveryCase,
) -> dict[str, Any]:
    repo_root = run_root / "fsync-rollback"
    _install_repo(repo_root=repo_root, install_script=install_script, env=env)
    compiled = _compile_transaction(
        repo_root=repo_root,
        env=env,
        case=case,
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
    commit_failure = _mapping(failure_payload.get("commit_failure"))
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
    if (journal_root / "snapshot").exists() or (journal_root / "staging").exists():
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
    if (journal_root / "snapshot").exists() or (journal_root / "staging").exists():
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


def _compile_transaction(
    *,
    repo_root: Path,
    env: Mapping[str, str],
    case: SemanticRecoveryCase,
) -> _CompiledRecoveryTransaction:
    semantic_intent_path = repo_root / "semantic-intent-recovery.v3.json"
    semantic_intent_path.write_text(
        json.dumps(case.packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    command = [
        "./.odylith/bin/odylith",
        "greenfield",
        "propose",
        "--repo-root",
        ".",
        "--prompt",
        case.prompt,
        "--semantic-intent-file",
        str(semantic_intent_path),
        "--format",
        "json",
    ]
    proposed = _run(
        cwd=repo_root,
        env=dict(env),
        command=command,
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
    intent_authority = _mapping(sealed_transaction.get("intent_authority"))
    product_facts_hash = str(intent_authority.get("product_facts_sha256") or "").strip()
    if sealed_hash != transaction_hash or not write_set_hash or not is_sha256(product_facts_hash):
        raise RuntimeError("installed greenfield propose returned an inconsistent sealed transaction identity")
    if str(transaction.get("product_facts_sha256") or "").strip() != product_facts_hash:
        raise RuntimeError("installed greenfield propose did not return the sealed Product Intent facts hash")
    _require_case_evidence_bound_to_transaction(case=case, intent_authority=intent_authority)
    return _CompiledRecoveryTransaction(
        transaction_file=transaction_file,
        transaction_hash=transaction_hash,
        product_facts_hash=product_facts_hash,
        write_set_hash=write_set_hash,
        intent_authority=intent_authority,
    )


def _require_case_evidence_bound_to_transaction(
    *,
    case: SemanticRecoveryCase,
    intent_authority: Mapping[str, Any],
) -> None:
    """Prove the sealed v8 authority contains the exact assessed graph packet."""

    expected = {
        "version": "odylith.product-intent-authority.v10",
        "origin": "verified_semantic_intent_packet",
        "source_format": "semantic_intent_packet",
        "evidence_sha256": str(case.packet.get("evidence_sha256") or ""),
        "semantic_intent_packet_version": "odylith.greenfield.semantic-intent-packet.v4",
        "semantic_intent_ir_version": "odylith.greenfield.semantic-intent-ir.v3",
        "semantic_intent_authoring_request_version": (
            "odylith.greenfield.semantic-intent-authoring-request.v8"
        ),
        "semantic_intent_authoring_contract_sha256": str(
            case.packet.get("authoring_contract_sha256") or ""
        ),
        "semantic_materiality_assessment": case.packet.get("materiality_assessment"),
        "semantic_materiality_assessment_sha256": str(
            case.packet.get("materiality_assessment_sha256") or ""
        ),
        "semantic_materiality_critic_run": case.packet.get("critic_run"),
        "semantic_intent_author_run": case.packet.get("author_run"),
    }
    if any(intent_authority.get(key) != value for key, value in expected.items()):
        raise RuntimeError(
            "installed Greenfield transaction authority did not bind the v3 assessed Semantic Intent packet"
        )
    if intent_authority.get("semantic_intent") != case.packet.get("semantic_intent"):
        raise RuntimeError("installed Greenfield transaction authority changed the Semantic Intent graph")
    evidence_sources = _mapping(intent_authority.get("evidence_sources"))
    if evidence_sources != {"operator_prompt": case.prompt, "operator_edit": ""}:
        raise RuntimeError("installed Greenfield transaction authority changed the operator evidence")


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
    commit_result = _mapping(journal.get("commit_result"))
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
    transaction = _mapping(payload.get("product_create_transaction"))
    manifest = _mapping(payload.get("commit_manifest"))
    manifest_transaction = _mapping(manifest.get("product_create_transaction"))
    write_transaction = _mapping(manifest.get("write_transaction"))
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


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.casefold()
        and all(character in "0123456789abcdef" for character in value)
    )


def _command_detail(result: Any) -> str:
    stdout = str(getattr(result, "stdout", "") or "").strip()
    stderr = str(getattr(result, "stderr", "") or "").strip()
    output = "\n".join(part for part in (stdout, stderr) if part)
    return f"returncode={result.returncode}; output={output[-1000:]!r}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--temp-parent", type=Path, required=True)
    parser.add_argument("--semantic-fixture", type=Path, default=_DEFAULT_SEMANTIC_FIXTURE)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args(argv)
    try:
        case = load_semantic_recovery_case(args.semantic_fixture)
        proof = run_installed_commit_recovery_proof(
            dist_dir=args.dist_dir,
            version=args.version,
            temp_parent=args.temp_parent,
            recovery_case=case,
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"installed Greenfield transaction recovery proof failed: {exc}", file=sys.stderr)
        return 1
    payload = proof.to_dict()
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output_json is not None:
        output_path = args.output_json.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if proof.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
