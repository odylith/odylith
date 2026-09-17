"""Durable raw evidence and admission checks for installed recovery proof."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any

from greenfield_commit_recovery_generation import generation_observation_issues
from greenfield_matrix_release_artifacts import is_sha256
from greenfield_matrix_release_artifacts import (
    RetainedEvidenceCase, begin_retained_case_evidence, finalize_retained_case_evidence,
    prepare_retained_evidence_output_dir, record_retained_case_bytes,
    record_retained_case_json, record_retained_case_text, retained_case_evidence_fd,
    retained_evidence_manifest_issues, sha256_file, write_retained_evidence_manifest,
)


def begin_proposal(*, output_dir: Path, temp_parent: Path) -> RetainedEvidenceCase:
    root = prepare_retained_evidence_output_dir(output_dir=output_dir, temp_parent=temp_parent)
    return begin_retained_case_evidence(evidence_root=root, case_id="proposal")


def run_proposal(*, evidence: RetainedEvidenceCase | None, runner: Any, **arguments: Any) -> Any:
    capture = retained_case_evidence_fd(evidence, "semantic/model-authoring-observation.v1.json") if evidence else nullcontext(None)
    try:
        with capture as descriptor:
            if descriptor is not None:
                arguments["env"] = dict(arguments["env"], ODYLITH_GREENFIELD_MODEL_PROOF_FD=str(descriptor))
                arguments["pass_fds"] = (descriptor,)
            result = runner(**arguments)
    except BaseException as exc:
        if evidence is not None:
            record_retained_case_json(evidence, "commands/propose-error.json", {
                "command": arguments["command"], "exception": type(exc).__name__, "message": str(exc),
            })
            for name in ("stdout", "stderr"):
                value = getattr(exc, name, None)
                if value is not None:
                    record_retained_case_bytes(evidence, f"commands/propose.{name}",
                        value if isinstance(value, bytes) else str(value).encode("utf-8"))
        raise
    if evidence is not None:
        record_retained_case_text(evidence, "commands/propose.stdout", result.stdout)
        record_retained_case_text(evidence, "commands/propose.stderr", result.stderr)
        record_retained_case_json(evidence, "commands/propose.json", {
            "command": arguments["command"], "returncode": result.returncode,
        })
    return result


def finish_proposal(*, evidence: RetainedEvidenceCase, repo_root: Path, status: str, issues: list[str], run_id: str = "") -> None:
    finalize_retained_case_evidence(
        case=evidence, repo_root=repo_root,
        result_payload={"status": status, "issues": issues},
    )
    if status != "passed":
        write_retained_evidence_manifest(root=evidence.final_root.parent, expected_case_ids=("proposal",), run_id=run_id)


def journal_inventory(journal_root: Path) -> dict[str, dict[str, Any]]:
    """Bind directories and regular bytes without following recovery symlinks."""
    inventory: dict[str, dict[str, Any]] = {}
    for ancestor in (journal_root, *journal_root.parents):
        if ancestor.is_symlink():
            raise RuntimeError("recovery evidence crosses a symlink")
    for path in (journal_root, *sorted(journal_root.rglob("*"))):
        info = path.lstat()
        row: dict[str, Any] = {"mode": info.st_mode, "mtime_ns": info.st_mtime_ns}
        if stat.S_ISREG(info.st_mode):
            row.update(sha256=sha256_file(path), byte_count=info.st_size)
        elif not stat.S_ISDIR(info.st_mode):
            raise RuntimeError("recovery evidence contains an unsafe journal entry")
        inventory[path.relative_to(journal_root).as_posix()] = row
    return inventory


def seal_conflict(
    *, proposal: RetainedEvidenceCase, repo_root: Path, journal_root: Path,
    selected_path: Path, original_bytes: bytes, original_stat: os.stat_result,
    operator_bytes: bytes, result: Any, facts: Mapping[str, Any], binding: Mapping[str, Any], run_id: str = "",
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    """Persist and validate conflict evidence before the harness retracts its mutation."""
    case = begin_retained_case_evidence(evidence_root=proposal.final_root.parent, case_id="operator-conflict")
    inventory = journal_inventory(journal_root)
    for relative, row in inventory.items():
        if "sha256" in row:
            payload = (journal_root / relative).read_bytes()
            if hashlib.sha256(payload).hexdigest() != row["sha256"]:
                raise RuntimeError("recovery journal changed while retaining evidence")
            record_retained_case_bytes(case, "recovery/journal/" + relative, payload)
    record_retained_case_json(case, "semantic/conflict-observation.json", {
        **facts, "journal_inventory": inventory,
        "selected_path": selected_path.relative_to(repo_root).as_posix(),
        "original_mode": original_stat.st_mode, "original_mtime_ns": original_stat.st_mtime_ns,
    })
    record_retained_case_json(case, "semantic/conflict-binding.json", dict(binding))
    record_retained_case_bytes(case, "recovery/pre-injection.bin", original_bytes)
    record_retained_case_bytes(case, "recovery/injected.bin", operator_bytes)
    record_retained_case_text(case, "commands/conflict.stdout", result.stdout)
    record_retained_case_text(case, "commands/conflict.stderr", result.stderr)
    finalize_retained_case_evidence(case=case, repo_root=repo_root, result_payload={"status": "passed"})
    manifest = write_retained_evidence_manifest(
        root=proposal.final_root.parent, expected_case_ids=("proposal", "operator-conflict"), run_id=run_id,
    )
    receipt = {"manifest": str(manifest), "sha256": sha256_file(manifest), "run_id": run_id}
    issues = retained_conflict_issues(receipt, expected_binding=binding, run_id=run_id)
    if issues:
        raise RuntimeError("conflict evidence failed custody: " + "; ".join(issues))
    return receipt, inventory


def retained_conflict_issues(
    receipt: Mapping[str, Any], *, expected_binding: Mapping[str, Any] | None = None, run_id: str = "",
) -> list[str]:
    manifest = Path(str(receipt.get("manifest") or ""))
    issues = list(retained_evidence_manifest_issues(
        manifest, expected_case_ids=("proposal", "operator-conflict"), require_passed_cases=True, expected_run_id=run_id,
    ))
    if not issues and receipt.get("sha256") != sha256_file(manifest):
        issues.append("recovery evidence manifest digest changed")
    if not issues and expected_binding is not None:
        binding_path = manifest.parent / "operator-conflict/semantic/conflict-binding.json"
        try:
            if json.loads(binding_path.read_text(encoding="utf-8")) != dict(expected_binding):
                issues.append("recovery evidence belongs to a different transaction or case")
        except (OSError, ValueError):
            issues.append("recovery evidence is missing its conflict binding")
    return issues


def _open_selected_file(path: Path) -> int:
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink():
            raise RuntimeError("conflict mutation crosses a symlink")
    if not stat.S_ISREG(path.lstat().st_mode):
        raise RuntimeError("conflict mutation requires a regular file")
    return os.open(path, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)


def _replace_selected_bytes(descriptor: int, path: Path, payload: bytes, expected_stat: os.stat_result) -> None:
    current = path.lstat()
    if (current.st_dev, current.st_ino, current.st_mode) != (
        expected_stat.st_dev, expected_stat.st_ino, expected_stat.st_mode,
    ):
        raise RuntimeError("conflict mutation file identity or mode changed")
    os.lseek(descriptor, 0, os.SEEK_SET)
    with os.fdopen(os.dup(descriptor), "wb") as stream:
        stream.write(payload)
        stream.truncate()
        stream.flush()
    os.utime(descriptor, ns=(expected_stat.st_atime_ns, expected_stat.st_mtime_ns))
    os.fsync(descriptor)
    os.lseek(descriptor, 0, os.SEEK_SET)
    with os.fdopen(os.dup(descriptor), "rb") as stream:
        observed = stream.read()
    current = os.fstat(descriptor)
    if observed != payload or (current.st_ino, current.st_mode, current.st_mtime_ns) != (
        expected_stat.st_ino, expected_stat.st_mode, expected_stat.st_mtime_ns,
    ) or path.lstat().st_ino != current.st_ino:
        raise RuntimeError("conflict mutation failed exact byte and metadata readback")


def inject_operator_mutation(*, path: Path, operator_bytes: bytes) -> tuple[bytes, os.stat_result]:
    """Capture and inject through one descriptor, never through a reopened path."""
    descriptor = _open_selected_file(path)
    try:
        original_stat = os.fstat(descriptor)
        if not stat.S_ISREG(original_stat.st_mode):
            raise RuntimeError("conflict injection requires a regular file")
        with os.fdopen(os.dup(descriptor), "rb") as stream:
            original_bytes = stream.read()
        current = os.fstat(descriptor)
        if (current.st_dev, current.st_ino, current.st_mode, current.st_size, current.st_mtime_ns) != (
            original_stat.st_dev, original_stat.st_ino, original_stat.st_mode, original_stat.st_size, original_stat.st_mtime_ns,
        ) or original_bytes == operator_bytes:
            raise RuntimeError("conflict injection source changed or marker is not distinct")
        _replace_selected_bytes(descriptor, path, operator_bytes, original_stat)
        return original_bytes, original_stat
    finally:
        os.close(descriptor)


def retract_injected_mutation(
    *, path: Path, original_bytes: bytes, original_stat: os.stat_result, operator_bytes: bytes,
) -> None:
    """Retract only the harness's exact mutation; never change recovery bookkeeping."""
    descriptor = _open_selected_file(path)
    try:
        current = os.fstat(descriptor)
        if (current.st_dev, current.st_ino, current.st_mode) != (
            original_stat.st_dev, original_stat.st_ino, original_stat.st_mode,
        ) or not stat.S_ISREG(current.st_mode):
            raise RuntimeError("conflict restoration file identity or mode changed")
        if os.read(descriptor, len(operator_bytes) + 1) != operator_bytes:
            raise RuntimeError("conflict restoration found an unexpected mutation")
        _replace_selected_bytes(descriptor, path, original_bytes, original_stat)
    finally:
        os.close(descriptor)


def as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def missing_required_evidence(facts: Mapping[str, Any], *, run_id: str = "") -> list[str]:
    """Keep a partial proof record from being published as a successful proof."""

    missing: list[str] = []
    resolution = as_mapping(facts.get("operator_conflict_resolution"))
    for key in ("recovery_returncode", "retry_returncode"):
        if type(resolution.get(key)) is not int or resolution[key] != 0:
            missing.append(f"installed conflict settlement did not prove {key}=0")
    if resolution.get("journal_state") != "closed" or resolution.get("same_hash_retry_unchanged") is not True:
        missing.append("installed conflict settlement did not prove closed idempotent recovery")
    binding = as_mapping(resolution.get("binding"))
    case = as_mapping(facts.get("recovery_case"))
    for key, expected in {
        "transaction_hash": facts.get("transaction_hash"),
        "repository_write_set_hash": facts.get("repository_write_set_hash"),
        "product_facts_sha256": facts.get("product_facts_sha256"),
        "case_id": case.get("id"), "prompt_sha256": case.get("prompt_sha256"),
    }.items():
        if not expected or binding.get(key) != expected:
            missing.append(f"installed conflict evidence did not bind {key}")
    missing.extend(retained_conflict_issues(as_mapping(resolution.get("evidence")), expected_binding=binding, run_id=run_id))
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
    phase_hashes = as_mapping(facts.get("product_facts_hashes_by_phase"))
    phase_sources = as_mapping(facts.get("product_facts_hash_sources_by_phase"))
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
    missing.extend(generation_observation_issues(facts))
    recovery_case = as_mapping(facts.get("recovery_case"))
    for key in ("id", "prompt_sha256"):
        if not str(recovery_case.get(key) or "").strip():
            missing.append(f"installed recovery proof did not record required recovery_case.{key}")
    binding_scope = str(recovery_case.get("binding_scope") or "")
    if binding_scope not in {"campaign-case-v1", "release-confirmed-intent-v1"}:
        missing.append("installed recovery proof did not record a recognized recovery_case.binding_scope")
    if binding_scope == "release-confirmed-intent-v1":
        for key in ("confirmed_intent_sha256",):
            if not str(recovery_case.get(key) or "").strip():
                missing.append(f"installed recovery proof did not record required recovery_case.{key}")
        provenance = as_mapping(recovery_case.get("provenance"))
        for key in (
            "corpus_tier",
            "source_id",
            "source_family",
            "source_artifact_sha256",
            "source_excerpt_sha256",
            "derived_prompt_sha256",
        ):
            if not str(provenance.get(key) or "").strip():
                missing.append(f"installed recovery proof did not record required recovery_case.provenance.{key}")
        if provenance.get("derived_prompt_sha256") != recovery_case.get("prompt_sha256"):
            missing.append("installed recovery proof did not retain a recovery_case prompt hash bound to provenance")
        audit_binding = as_mapping(recovery_case.get("release_audit_binding"))
        audit_request_sha256 = str(audit_binding.get("audit_request_sha256") or "")
        if not is_sha256(audit_request_sha256):
            missing.append("installed recovery proof did not retain a valid release audit request hash")
        if audit_binding.get("confirmed_intent_sha256") != recovery_case.get("confirmed_intent_sha256"):
            missing.append("installed recovery proof did not retain a release audit binding for the confirmed intent")
    return missing
