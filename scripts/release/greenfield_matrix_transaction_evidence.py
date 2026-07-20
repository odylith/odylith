"""Capture the sealed pre-confirm transaction that an installed matrix case commits."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import time
from types import SimpleNamespace
from typing import Any


DRY_RUN_RECEIPT_VERSION = "odylith.greenfield.matrix.dry-run-receipt.v1"


@dataclass(frozen=True)
class CompiledCreateExecution:
    """The commit result and immutable transaction facts captured before that commit."""

    create: Any
    create_seconds: float
    dry_run_receipt: Mapping[str, Any]


def commit_precompiled_transaction(
    *,
    repo_root: Path,
    proposed: Any,
    invoke_create: Callable[[Sequence[str]], Any],
) -> CompiledCreateExecution:
    """Validate a proposed transaction receipt before invoking commit-only create."""

    try:
        proposal_returncode = int(getattr(proposed, "returncode", 1))
    except (TypeError, ValueError):
        proposal_returncode = 1
    if proposal_returncode != 0:
        return CompiledCreateExecution(proposed, 0.0, _receipt(status="proposal_failed"))
    proposed_payload = _json_mapping(getattr(proposed, "stdout", ""))
    proposal_mode = str(proposed_payload.get("mode") or "").strip()
    if proposal_mode == "clarification_required":
        return CompiledCreateExecution(
            SimpleNamespace(
                returncode=2,
                stdout=getattr(proposed, "stdout", ""),
                stderr="greenfield proposal requires a material clarification before compiling a transaction",
            ),
            0.0,
            _receipt(status="clarification_required", proposal_mode=proposal_mode),
        )
    summary = _mapping(proposed_payload.get("product_create_transaction"))
    transaction_hash = str(summary.get("transaction_hash") or "").strip()
    transaction_file = str(proposed_payload.get("transaction_file") or "").strip()
    if proposal_mode != "product_create_transaction" or not transaction_hash or not transaction_file:
        return CompiledCreateExecution(
            _error_result("greenfield propose did not return a ProductCreateTransaction hash and transaction file"),
            0.0,
            _receipt(status="proposal_contract_failed", proposal_mode=proposal_mode),
        )
    receipt, issues = _sealed_dry_run_receipt(
        repo_root=repo_root,
        transaction_file=transaction_file,
        transaction_hash=transaction_hash,
        proposal_mode=proposal_mode,
    )
    if issues:
        return CompiledCreateExecution(
            _error_result("greenfield propose returned an invalid pre-confirm transaction: " + "; ".join(issues)),
            0.0,
            receipt,
        )
    started = time.perf_counter()
    create = invoke_create(
        (
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
        )
    )
    return CompiledCreateExecution(create, round(time.perf_counter() - started, 3), receipt)


def dry_run_commit_issues(*, receipt: Mapping[str, Any], create_payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Require the successful create readback to match the receipt captured before confirmation."""

    if str(receipt.get("status") or "") != "compiled":
        return ("pre-confirm dry-run receipt was not compiled before commit",)
    expected = str(receipt.get("transaction_hash") or "").strip()
    if not _is_sha256(expected):
        return ("pre-confirm dry-run receipt is missing a valid transaction hash",)
    manifest = _mapping(create_payload.get("commit_manifest"))
    write_transaction = _mapping(manifest.get("write_transaction"))
    manifest_transaction = _mapping(manifest.get("product_create_transaction"))
    observed = (
        str(write_transaction.get("product_create_transaction_hash") or "").strip(),
        str(manifest_transaction.get("transaction_hash") or "").strip(),
    )
    issues = [
        "commit readback does not match the pre-confirm transaction hash"
        for value in observed
        if value != expected
    ]
    return tuple(dict.fromkeys(issues))


def _sealed_dry_run_receipt(
    *,
    repo_root: Path,
    transaction_file: str,
    transaction_hash: str,
    proposal_mode: str,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    receipt = _receipt(
        status="invalid",
        proposal_mode=proposal_mode,
        transaction_file=transaction_file,
        transaction_hash=transaction_hash,
    )
    transaction_path, path_issue = _repo_path(repo_root, transaction_file)
    if path_issue:
        return receipt, (path_issue,)
    compiler_receipt_path = transaction_path.with_name(transaction_path.name + ".compiler-receipt.v1.json")
    try:
        transaction_bytes = transaction_path.read_bytes()
        compiler_receipt_bytes = compiler_receipt_path.read_bytes()
    except OSError as error:
        return receipt, (f"pre-confirm transaction receipt is unavailable: {error}",)
    transaction = _json_mapping(transaction_bytes)
    compiler_receipt = _json_mapping(compiler_receipt_bytes)
    transaction_file_sha256 = hashlib.sha256(transaction_bytes).hexdigest()
    compiler_receipt_sha256 = hashlib.sha256(compiler_receipt_bytes).hexdigest()
    quality_manifest = _mapping(transaction.get("quality_manifest"))
    receipt.update(
        {
            "transaction_file": str(transaction_path.relative_to(Path(repo_root).resolve())),
            "transaction_file_sha256": transaction_file_sha256,
            "compiler_receipt_file": str(compiler_receipt_path.relative_to(Path(repo_root).resolve())),
            "compiler_receipt_sha256": compiler_receipt_sha256,
            "compiler_receipt_transaction_hash": str(compiler_receipt.get("transaction_hash") or "").strip(),
            "preconfirm_quality_status": str(quality_manifest.get("status") or "").strip(),
            "preconfirm_validation_status": str(quality_manifest.get("validation_status") or "").strip(),
        }
    )
    issues: list[str] = []
    if str(transaction.get("transaction_hash") or "").strip() != transaction_hash:
        issues.append("transaction file hash does not match the propose response")
    if str(compiler_receipt.get("transaction_hash") or "").strip() != transaction_hash:
        issues.append("compiler receipt hash does not match the propose response")
    if str(compiler_receipt.get("transaction_file_sha256") or "").strip() != transaction_file_sha256:
        issues.append("compiler receipt file digest does not match the transaction bytes")
    if receipt["preconfirm_quality_status"] != "passed":
        issues.append("pre-confirm transaction quality is not passed")
    if receipt["preconfirm_validation_status"] != "passed":
        issues.append("pre-confirm transaction validation is not passed")
    if issues:
        return receipt, tuple(issues)
    receipt["status"] = "compiled"
    return receipt, ()


def _receipt(*, status: str, **values: Any) -> dict[str, Any]:
    return {"version": DRY_RUN_RECEIPT_VERSION, "status": status, **values}


def _repo_path(repo_root: Path, token: str) -> tuple[Path, str]:
    root = Path(repo_root).resolve()
    candidate = (root / token).resolve() if not Path(token).is_absolute() else Path(token).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return candidate, "pre-confirm transaction path escapes the case repository"
    return candidate, ""


def _error_result(message: str) -> SimpleNamespace:
    return SimpleNamespace(
        returncode=2,
        stdout=json.dumps({"mode": "error", "error": message}, sort_keys=True),
        stderr="",
    )


def _json_mapping(value: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(value.decode("utf-8") if isinstance(value, bytes) else str(value or ""))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return _mapping(parsed)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


__all__ = [
    "DRY_RUN_RECEIPT_VERSION",
    "CompiledCreateExecution",
    "commit_precompiled_transaction",
    "dry_run_commit_issues",
]
