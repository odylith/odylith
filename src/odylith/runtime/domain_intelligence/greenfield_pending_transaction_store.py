"""Immutable transaction-addressed storage for pending Greenfield decisions."""

from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

from odylith.install.fs import fsync_directory
from odylith.runtime.domain_intelligence import greenfield_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_contract import is_sha256_digest


PENDING_TRANSACTION_FILENAME = "product-create-transaction.v1.json"


def pending_transaction_directory(repo_root: Path, transaction_hash: str) -> Path:
    digest = _require_digest(transaction_hash)
    return (
        Path(repo_root).expanduser().resolve()
        / ".odylith/runtime/greenfield/pending"
        / digest
    )


def pending_transaction_path(repo_root: Path, transaction_hash: str) -> Path:
    return pending_transaction_directory(repo_root, transaction_hash) / PENDING_TRANSACTION_FILENAME


def stage_pending_transaction(
    *,
    repo_root: Path,
    transaction: greenfield_create_transaction.ProductCreateTransaction,
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
        path = resolve_pending_transaction(repo_root=root, transaction_hash=digest)
        existing = greenfield_create_transaction.load_compiled_product_create_transaction_file(path)
        if existing.transaction_hash != digest:
            raise RuntimeError("Greenfield pending transaction address is occupied by different bytes")
        return path
    temporary = Path(tempfile.mkdtemp(prefix=f".stage-{digest[:12]}-", dir=parent))
    try:
        path = temporary / PENDING_TRANSACTION_FILENAME
        greenfield_create_transaction.write_compiled_product_create_transaction_file(path, transaction)
        fsync_directory(temporary)
        temporary.replace(target)
        fsync_directory(parent)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return resolve_pending_transaction(repo_root=root, transaction_hash=digest)


def resolve_pending_transaction(*, repo_root: Path, transaction_hash: str) -> Path:
    """Resolve and verify the exact pending package named by a user decision."""

    digest = _require_digest(transaction_hash)
    directory = pending_transaction_directory(repo_root, digest)
    path = directory / PENDING_TRANSACTION_FILENAME
    receipt = greenfield_create_transaction.product_create_transaction_receipt_path(path)
    if directory.is_symlink() or not directory.is_dir() or path.is_symlink() or receipt.is_symlink():
        raise ValueError("Greenfield pending transaction is missing or unsafe")
    transaction = greenfield_create_transaction.load_compiled_product_create_transaction_file(path)
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
    if not is_sha256_digest(token):
        raise ValueError("Greenfield pending transaction hash must be a SHA-256 value")
    return token


__all__ = [
    "PENDING_TRANSACTION_FILENAME",
    "discard_pending_transaction",
    "pending_transaction_directory",
    "pending_transaction_path",
    "resolve_pending_transaction",
    "stage_pending_transaction",
]
