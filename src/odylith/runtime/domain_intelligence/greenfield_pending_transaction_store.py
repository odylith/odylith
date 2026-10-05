"""Immutable transaction-addressed storage for pending Greenfield decisions."""

from __future__ import annotations

import re
import json
import hashlib
import secrets
import os
from pathlib import Path
import shutil
import tempfile
from typing import TYPE_CHECKING

from odylith.install.fs import fsync_directory
from odylith.runtime.domain_intelligence import greenfield_commit_transaction

if TYPE_CHECKING:
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
        ProductCreateTransaction,
    )


PENDING_TRANSACTION_FILENAME = "product-create-transaction.v1.json"
GREENFIELD_RUNTIME_ROOT = ".odylith/runtime/greenfield"
GREENFIELD_PENDING_TRANSACTION_ROOT = f"{GREENFIELD_RUNTIME_ROOT}/pending"
_DIGEST = re.compile(r"[0-9a-f]{64}")


def pending_transaction_directory(repo_root: Path, transaction_hash: str) -> Path:
    digest = _require_digest(transaction_hash)
    return (
        Path(repo_root).expanduser().resolve()
        / GREENFIELD_PENDING_TRANSACTION_ROOT
        / digest
    )


def pending_transaction_path(repo_root: Path, transaction_hash: str) -> Path:
    return pending_transaction_directory(repo_root, transaction_hash) / PENDING_TRANSACTION_FILENAME


def stage_pending_transaction(
    *,
    repo_root: Path,
    transaction: ProductCreateTransaction,
    completion_receipt: Path | str | None = None,
) -> Path:
    """Publish one immutable pending package with atomic directory visibility."""

    root = Path(repo_root).expanduser().resolve()
    digest = _require_digest(transaction.transaction_hash)
    parent = pending_transaction_directory(root, digest).parent
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
        raise RuntimeError("Greenfield pending transaction store is unsafe")
    parent.mkdir(parents=True, exist_ok=True)
    fsync_directory(parent.parent)
    target = parent / digest
    if target.exists() or target.is_symlink():
        return resolve_pending_transaction(repo_root=root, transaction_hash=digest, completion_receipt=completion_receipt)
    from odylith.runtime.domain_intelligence import greenfield_create_transaction

    from odylith.runtime.domain_intelligence.greenfield_process import register_bounded_pending_transaction
    journey_marker = register_bounded_pending_transaction(target)
    temporary = Path(tempfile.mkdtemp(prefix=f".stage-{digest[:12]}-", dir=parent))
    try:
        path = temporary / PENDING_TRANSACTION_FILENAME
        greenfield_create_transaction.write_compiled_product_create_transaction_file(path, transaction)
        if journey_marker is not None:
            import json
            (temporary / ".bounded-journey.v1.json").write_text(json.dumps(journey_marker), encoding="utf-8")
        fsync_directory(temporary)
        temporary.replace(target)
        fsync_directory(parent)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return _resolve_pending_transaction(repo_root=root, transaction_hash=digest)


def resolve_pending_transaction(*, repo_root: Path, transaction_hash: str,
                                completion_receipt: Path | str | None = None) -> Path:
    """Resolve and verify the exact pending package named by a user decision."""

    directory = pending_transaction_directory(repo_root, transaction_hash)
    require_pending_transaction_released(directory / PENDING_TRANSACTION_FILENAME, repo_root=repo_root,
                                        transaction_hash=transaction_hash, completion_receipt=completion_receipt)
    return _resolve_pending_transaction(repo_root=repo_root, transaction_hash=transaction_hash)


def resolve_pending_transaction_directory(*, repo_root: Path, transaction_hash: str) -> Path:
    """Locate exact pending ownership for rejection without granting readiness."""
    directory = pending_transaction_directory(repo_root, transaction_hash)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Greenfield pending package is missing or unsafe")
    return directory


def require_pending_transaction_released(path: Path, *, repo_root: Path, transaction_hash: str,
                                        completion_receipt: Path | str | None = None) -> None:
    """Require explicit delivered custody proof at the canonical repository/hash."""
    canonical = pending_transaction_directory(repo_root, transaction_hash)
    for directory in dict.fromkeys((canonical, Path(path).parent)):
        marker = directory / ".bounded-journey.v1.json"
        if not (marker.exists() or marker.is_symlink()):
            continue  # Standalone source-custody transactions retain their contract.
        try:
            state = json.loads(marker.read_text())
            completion_path = directory / ".bounded-completion.v1.json"
            completion = json.loads(completion_path.read_text())
            receipt_path = Path(completion_receipt or "").expanduser()
            if not receipt_path.is_absolute():
                receipt_path = Path(repo_root) / receipt_path
            receipt = json.loads(receipt_path.read_text())
            released = (not marker.is_symlink() and not completion_path.is_symlink()
                and not receipt_path.is_symlink() and set(state) == {
                    "version", "journey_id", "completion_digest"}
                and state["version"] == "odylith.greenfield.journey-supervision.v1"
                and _DIGEST.fullmatch(state["journey_id"]) is not None
                and _DIGEST.fullmatch(state["completion_digest"]) is not None
                and set(receipt) == {"version", "journey_id", "transaction_hash", "nonce"}
                and receipt["version"] == "odylith.greenfield.completion-receipt.v1"
                and receipt["journey_id"] == state["journey_id"]
                and receipt["transaction_hash"] == transaction_hash
                and _DIGEST.fullmatch(receipt["nonce"]) is not None
                and secrets.compare_digest(hashlib.sha256(receipt["nonce"].encode("ascii")).hexdigest(),
                                           state["completion_digest"])
                and set(completion) == {"version", "status", "journey_id", "transaction_hash",
                                       "completion_digest", "record_started_at", "deadline"}
                and completion["version"] == "odylith.greenfield.journey-completion.v2"
                and completion["status"] == "completion_attempt"
                and completion["transaction_hash"] == transaction_hash
                and all(completion[key] == state[key] for key in ("journey_id", "completion_digest")))
        except (OSError, ValueError, TypeError, KeyError):
            released = False
        if not released:
            raise ValueError("Greenfield bounded journey has not released this pending package; supply its delivered --completion-receipt")


def write_completion_receipt_delivery(*, repo_root: Path, receipt: dict) -> Path:
    """Persist the guardian's delivered receipt outside the measured journey."""
    digest = _require_digest(receipt["transaction_hash"])
    journey = _require_digest(receipt["journey_id"])
    directory = Path(repo_root).resolve() / GREENFIELD_RUNTIME_ROOT / "completion-receipts" / digest
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (journey + ".json")
    with open(path, "x", encoding="utf-8", opener=lambda file, flags: os.open(file, flags, 0o600)) as stream:
        json.dump(receipt, stream, sort_keys=True)
    return path


def _resolve_pending_transaction(*, repo_root: Path, transaction_hash: str) -> Path:
    root = Path(repo_root).expanduser().resolve()
    digest = _require_digest(transaction_hash)
    directory = pending_transaction_directory(root, digest)
    path = directory / PENDING_TRANSACTION_FILENAME
    receipt = path.with_name(path.name + ".compiler-receipt.v1.json")
    if directory.is_symlink() or not directory.is_dir() or path.is_symlink() or receipt.is_symlink():
        raise ValueError("Greenfield pending transaction is missing or unsafe")
    transaction = greenfield_commit_transaction.load_sealed_product_create_commit(
        path,
        repo_root=root,
    )
    if transaction.transaction_hash != digest:
        raise ValueError("Greenfield pending transaction does not match its decision hash")
    return path


def discard_pending_transaction(*, repo_root: Path, transaction_hash: str) -> None:
    """Atomically remove one exact pending package after a terminal rejection."""

    digest = _require_digest(transaction_hash)
    directory = pending_transaction_directory(repo_root, digest)
    if directory.is_symlink():
        raise ValueError("Greenfield pending transaction directory must not be a symlink")
    if not directory.exists():
        raise ValueError("Greenfield pending transaction does not exist")
    marker = directory / ".bounded-journey.v1.json"
    if marker.exists() or marker.is_symlink():
        from odylith.runtime.domain_intelligence.greenfield_process import _write_journey_marker
        # Retire authority before bytes; canonical hash denial survives copying.
        _write_journey_marker(marker, {"rejected": True})
        for name in (PENDING_TRANSACTION_FILENAME, PENDING_TRANSACTION_FILENAME + ".compiler-receipt.v1.json"):
            (directory / name).unlink(missing_ok=True)
        return
    parent = directory.parent
    retired = parent / f".discard-{digest}"
    if retired.exists() or retired.is_symlink():
        raise RuntimeError("Greenfield pending transaction discard path is occupied")
    directory.replace(retired)
    fsync_directory(parent)
    shutil.rmtree(retired)
    fsync_directory(parent)


def _require_digest(value: object) -> str:
    token = str(value or "").strip()
    if not _DIGEST.fullmatch(token):
        raise ValueError("Greenfield pending transaction hash must be a SHA-256 value")
    return token


__all__ = [
    "GREENFIELD_PENDING_TRANSACTION_ROOT",
    "GREENFIELD_RUNTIME_ROOT",
    "PENDING_TRANSACTION_FILENAME",
    "discard_pending_transaction",
    "pending_transaction_directory",
    "pending_transaction_path",
    "resolve_pending_transaction",
    "stage_pending_transaction",
]
