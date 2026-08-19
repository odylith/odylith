#!/usr/bin/env python3
"""Compile independent semantic and deterministic host-parity evidence."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
import os
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_commit_transaction
from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store
from odylith.runtime.surfaces import greenfield_host_confirmation
from scripts.release.greenfield_semantic_release_support import (
    canonical_sha256,
    exclusive_json,
    json_mapping,
    mapped_rows,
    mapping,
    require_sha256,
    unique_index,
)


HOST_PARITY_WORK_VERSION = "odylith.greenfield.host-parity-work.v1"
HOST_PARITY_REPORT_VERSION = "odylith.greenfield.host-parity-report.v1"
HOST_CALLBACK_PROOF_VERSION = "odylith.greenfield.host-callback-parity.v1"
HOST_PARITY_REHEARSAL_VERSION = "odylith.greenfield.host-parity-rehearsal.v1"
SUPPORTED_HOSTS = ("codex", "claude")
_OUTCOMES = frozenset({"commit", "clarify"})


def compile_host_parity_report(
    semantic_work: Mapping[str, Any],
    callback_proof: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate independent same-case semantics and one shared commit callback."""

    work = dict(semantic_work)
    expected_work_fields = {
        "version",
        "assignment_manifest_sha256",
        "authoring_contract_sha256",
        "evaluation_contract_sha256",
        "required_case_ids",
        "cases",
    }
    if set(work) != expected_work_fields:
        raise RuntimeError("host-parity work fields do not match the versioned contract")
    if work.get("version") != HOST_PARITY_WORK_VERSION:
        raise RuntimeError("host-parity work uses an unsupported version")
    assignment_manifest_sha256 = require_sha256(
        work.get("assignment_manifest_sha256"), "host-parity assignment manifest"
    )
    authoring_contract_sha256 = require_sha256(
        work.get("authoring_contract_sha256"), "host-parity authoring contract"
    )
    evaluation_contract_sha256 = require_sha256(
        work.get("evaluation_contract_sha256"), "host-parity evaluation contract"
    )
    required_case_ids = _unique_text_rows(work.get("required_case_ids"), "required host-parity case IDs")
    cases = mapped_rows(work.get("cases"), "host-parity cases")
    case_index = unique_index(cases, "case_id", "host-parity case")
    if tuple(case_index) != required_case_ids:
        raise RuntimeError("host-parity cases do not match the frozen required case order")

    summaries: list[dict[str, Any]] = []
    outcome_counts = {outcome: 0 for outcome in sorted(_OUTCOMES)}
    seen_execution_nonces: set[str] = set()
    for case_id in required_case_ids:
        summary = _require_semantic_case(
            case_index[case_id],
            case_id=case_id,
            seen_execution_nonces=seen_execution_nonces,
        )
        summaries.append(summary)
        outcome_counts[summary["outcome"]] += 1

    callback = require_callback_parity_proof(callback_proof)
    return {
        "version": HOST_PARITY_REPORT_VERSION,
        "status": "passed",
        "passed": True,
        "assignment_manifest_sha256": assignment_manifest_sha256,
        "authoring_contract_sha256": authoring_contract_sha256,
        "evaluation_contract_sha256": evaluation_contract_sha256,
        "semantic_work_sha256": canonical_sha256(work),
        "semantic_parity": {
            "status": "passed",
            "case_count": len(summaries),
            "commit_count": outcome_counts["commit"],
            "clarify_count": outcome_counts["clarify"],
            "cases": summaries,
        },
        "callback_parity": callback,
    }


def run_callback_parity(
    *,
    repo_root: Path | str,
    transaction_hash: str,
) -> dict[str, Any]:
    """Commit one disposable transaction through both exact host callbacks."""

    root = Path(repo_root).expanduser().resolve()
    digest = require_sha256(transaction_hash, "host-parity transaction hash")
    _require_rehearsal_marker(root, digest)
    transaction_path = greenfield_pending_transaction_store.resolve_pending_transaction(
        repo_root=root,
        transaction_hash=digest,
    )
    sealed = greenfield_commit_transaction.load_sealed_product_create_commit(
        transaction_path,
        repo_root=root,
    )
    write_set_hash = require_sha256(
        sealed.prewrite_package.repository_write_set.get("write_set_hash"),
        "host-parity write-set hash",
    )

    previous_no_browser = os.environ.get("ODYLITH_NO_BROWSER")
    os.environ["ODYLITH_NO_BROWSER"] = "1"
    try:
        codex = _confirm_as_host(root, "codex", digest)
        codex_receipt_sha256 = _closed_receipt_sha256(root, digest)
        claude = _confirm_as_host(root, "claude", digest)
        claude_receipt_sha256 = _closed_receipt_sha256(root, digest)
    finally:
        if previous_no_browser is None:
            os.environ.pop("ODYLITH_NO_BROWSER", None)
        else:
            os.environ["ODYLITH_NO_BROWSER"] = previous_no_browser

    proof = {
        "version": HOST_CALLBACK_PROOF_VERSION,
        "callback_version": greenfield_host_confirmation.HOST_CONFIRMATION_CALLBACK_VERSION,
        "transaction_hash": digest,
        "write_set_hash": write_set_hash,
        "codex": {
            "status": codex["status"],
            "decision_sha256": canonical_sha256(codex),
            "receipt_sha256": codex_receipt_sha256,
        },
        "claude": {
            "status": claude["status"],
            "decision_sha256": canonical_sha256(claude),
            "receipt_sha256": claude_receipt_sha256,
        },
    }
    return require_callback_parity_proof(proof)


def require_callback_parity_proof(value: Mapping[str, Any]) -> dict[str, Any]:
    proof = dict(value)
    expected_fields = {
        "version",
        "callback_version",
        "transaction_hash",
        "write_set_hash",
        "codex",
        "claude",
    }
    if set(proof) != expected_fields:
        raise RuntimeError("host callback proof fields do not match the versioned contract")
    if proof.get("version") != HOST_CALLBACK_PROOF_VERSION:
        raise RuntimeError("host callback proof uses an unsupported version")
    if proof.get("callback_version") != greenfield_host_confirmation.HOST_CONFIRMATION_CALLBACK_VERSION:
        raise RuntimeError("host callback proof uses an unsupported callback contract")
    transaction_hash = require_sha256(proof.get("transaction_hash"), "host callback transaction hash")
    write_set_hash = require_sha256(proof.get("write_set_hash"), "host callback write-set hash")
    host_rows: dict[str, dict[str, Any]] = {}
    for host in SUPPORTED_HOSTS:
        row = mapping(proof.get(host), f"{host} callback proof")
        if set(row) != {"status", "decision_sha256", "receipt_sha256"}:
            raise RuntimeError(f"{host} callback proof fields do not match the versioned contract")
        if row.get("status") != "CLOSED":
            raise RuntimeError(f"{host} callback did not close the sealed transaction")
        host_rows[host] = {
            "status": "CLOSED",
            "decision_sha256": require_sha256(row.get("decision_sha256"), f"{host} decision"),
            "receipt_sha256": require_sha256(row.get("receipt_sha256"), f"{host} receipt"),
        }
    if host_rows["codex"] != host_rows["claude"]:
        raise RuntimeError("Codex and Claude callback evidence differs for the same sealed transaction")
    return {
        "version": HOST_CALLBACK_PROOF_VERSION,
        "status": "passed",
        "passed": True,
        "callback_version": greenfield_host_confirmation.HOST_CONFIRMATION_CALLBACK_VERSION,
        "transaction_hash": transaction_hash,
        "write_set_hash": write_set_hash,
        "hosts": host_rows,
    }


def _require_semantic_case(
    value: Mapping[str, Any],
    *,
    case_id: str,
    seen_execution_nonces: set[str],
) -> dict[str, Any]:
    row = dict(value)
    expected_fields = {
        "case_id",
        "prompt_sha256",
        "assignment_sha256",
        "codex",
        "claude",
        "independent_adjudication",
    }
    if set(row) != expected_fields or row.get("case_id") != case_id:
        raise RuntimeError(f"host-parity case {case_id} fields or identity are invalid")
    prompt_sha256 = require_sha256(row.get("prompt_sha256"), f"host-parity case {case_id} prompt")
    assignment_sha256 = require_sha256(
        row.get("assignment_sha256"), f"host-parity case {case_id} assignment"
    )
    host_rows = {
        host: _require_host_candidate(row.get(host), host=host, case_id=case_id)
        for host in SUPPORTED_HOSTS
    }
    if host_rows["codex"]["outcome"] != host_rows["claude"]["outcome"]:
        raise RuntimeError(f"host-parity case {case_id} has different material outcomes")
    adjudication = _require_adjudication(
        row.get("independent_adjudication"),
        case_id=case_id,
        seen_execution_nonces=seen_execution_nonces,
    )
    return {
        "case_id": case_id,
        "prompt_sha256": prompt_sha256,
        "assignment_sha256": assignment_sha256,
        "outcome": host_rows["codex"]["outcome"],
        "codex_candidate_sha256": host_rows["codex"]["candidate_sha256"],
        "claude_candidate_sha256": host_rows["claude"]["candidate_sha256"],
        "adjudication_sha256": adjudication["adjudication_sha256"],
        "meaning_equivalent": True,
        "consumer_utility_equivalent": True,
        "material_decision_equivalent": True,
    }


def _require_host_candidate(value: Any, *, host: str, case_id: str) -> dict[str, str]:
    row = mapping(value, f"host-parity case {case_id} {host} candidate")
    expected_fields = {
        "host_profile",
        "outcome",
        "candidate_sha256",
        "mechanism_evidence_sha256",
        "semantic_artifact_sha256",
    }
    if set(row) != expected_fields or row.get("host_profile") != host:
        raise RuntimeError(f"host-parity case {case_id} {host} candidate identity is invalid")
    outcome = str(row.get("outcome") or "")
    if outcome not in _OUTCOMES:
        raise RuntimeError(f"host-parity case {case_id} {host} outcome is invalid")
    return {
        "outcome": outcome,
        "candidate_sha256": require_sha256(row.get("candidate_sha256"), f"{case_id} {host} candidate"),
        "mechanism_evidence_sha256": require_sha256(
            row.get("mechanism_evidence_sha256"), f"{case_id} {host} mechanism evidence"
        ),
        "semantic_artifact_sha256": require_sha256(
            row.get("semantic_artifact_sha256"), f"{case_id} {host} semantic artifact"
        ),
    }


def _require_adjudication(
    value: Any,
    *,
    case_id: str,
    seen_execution_nonces: set[str],
) -> dict[str, str]:
    row = mapping(value, f"host-parity case {case_id} adjudication")
    expected_fields = {
        "review_a_sha256",
        "review_b_sha256",
        "adjudication_sha256",
        "review_a_run_nonce",
        "review_b_run_nonce",
        "adjudicator_run_nonce",
        "meaning_equivalent",
        "consumer_utility_equivalent",
        "material_decision_equivalent",
        "unresolved_p0_count",
        "unresolved_p1_count",
    }
    if set(row) != expected_fields:
        raise RuntimeError(f"host-parity case {case_id} adjudication fields are invalid")
    for field in (
        "meaning_equivalent",
        "consumer_utility_equivalent",
        "material_decision_equivalent",
    ):
        if row.get(field) is not True:
            raise RuntimeError(f"host-parity case {case_id} failed {field}")
    for field in ("unresolved_p0_count", "unresolved_p1_count"):
        if type(row.get(field)) is not int or row[field] != 0:
            raise RuntimeError(f"host-parity case {case_id} has unresolved priority findings")
    for field in ("review_a_run_nonce", "review_b_run_nonce", "adjudicator_run_nonce"):
        nonce = str(row.get(field) or "").strip()
        if not nonce or len(nonce) > 200 or nonce in seen_execution_nonces:
            raise RuntimeError(f"host-parity case {case_id} has reused or invalid independent-run evidence")
        seen_execution_nonces.add(nonce)
    return {
        field: require_sha256(row.get(field), f"host-parity case {case_id} {field}")
        for field in ("review_a_sha256", "review_b_sha256", "adjudication_sha256")
    }


def _confirm_as_host(root: Path, host: str, transaction_hash: str) -> dict[str, Any]:
    decision = greenfield_host_confirmation.maybe_handle_greenfield_decision(
        repo_root=root,
        host_family=host,
        prompt=f"CONFIRM {transaction_hash}",
    )
    if not isinstance(decision, Mapping):
        raise RuntimeError(f"{host} did not route the exact confirmation command")
    return dict(decision)


def _closed_receipt_sha256(root: Path, transaction_hash: str) -> str:
    state = json_mapping(
        root / ".odylith/runtime/greenfield/create-journal" / transaction_hash / "state.v1.json",
        "closed host-parity journal",
    )
    if state.get("state") != "closed" or state.get("lifecycle_state") not in {None, "", "CLOSED"}:
        raise RuntimeError("host-parity transaction did not reach the closed journal state")
    commit_result = state.get("commit_result")
    if not isinstance(commit_result, Mapping):
        raise RuntimeError("host-parity closed journal lacks the kernel commit receipt")
    return canonical_sha256(commit_result)


def _require_rehearsal_marker(root: Path, transaction_hash: str) -> None:
    marker = json_mapping(root / ".odylith-host-parity-rehearsal.v1.json", "host-parity rehearsal marker")
    if marker != {
        "version": HOST_PARITY_REHEARSAL_VERSION,
        "transaction_hash": transaction_hash,
    }:
        raise RuntimeError("host-parity callback proof requires an exact disposable-repository marker")


def _unique_text_rows(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise RuntimeError(f"{label} must be a list")
    rows = tuple(str(row or "").strip() for row in value)
    if not rows or any(not row or len(row) > 200 for row in rows) or len(set(rows)) != len(rows):
        raise RuntimeError(f"{label} must contain unique non-empty values")
    return rows


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semantic-work", type=Path, required=True)
    parser.add_argument("--callback-repo-root", type=Path, required=True)
    parser.add_argument("--transaction-hash", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    semantic_work = json_mapping(args.semantic_work, "host-parity semantic work")
    callback_proof = run_callback_parity(
        repo_root=args.callback_repo_root,
        transaction_hash=args.transaction_hash,
    )
    report = compile_host_parity_report(semantic_work, callback_proof)
    exclusive_json(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "HOST_CALLBACK_PROOF_VERSION",
    "HOST_PARITY_REPORT_VERSION",
    "HOST_PARITY_REHEARSAL_VERSION",
    "HOST_PARITY_WORK_VERSION",
    "compile_host_parity_report",
    "main",
    "require_callback_parity_proof",
    "run_callback_parity",
]
