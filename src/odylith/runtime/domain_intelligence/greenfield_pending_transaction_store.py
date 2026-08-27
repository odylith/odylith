"""Immutable transaction-addressed storage for pending Greenfield decisions."""

from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_create_transaction
from odylith.runtime.domain_intelligence import greenfield_transaction_path_boundary
from odylith.runtime.domain_intelligence.greenfield_create_contract import is_sha256_digest


PENDING_TRANSACTION_FILENAME = "product-create-transaction.v1.json"
_PENDING_ROOT = ".odylith/runtime/greenfield/pending"


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
    greenfield_transaction_path_boundary.ensure_directory(root, _PENDING_ROOT)
    target_token = f"{_PENDING_ROOT}/{digest}"
    target = root / target_token
    target_kind = greenfield_transaction_path_boundary.path_kind(root, target_token)
    if target_kind != "missing":
        if target_kind != "directory":
            raise RuntimeError("Greenfield pending transaction address is unsafe")
        path = resolve_pending_transaction(repo_root=root, transaction_hash=digest)
        existing = greenfield_create_transaction.load_compiled_product_create_transaction_file(
            path,
            repo_root=root,
        )
        if existing.transaction_hash != digest:
            raise RuntimeError("Greenfield pending transaction address is occupied by different bytes")
        return path
    temporary_token = greenfield_transaction_path_boundary.make_temporary_directory(
        root,
        _PENDING_ROOT,
        prefix=f".stage-{digest[:12]}-",
    )
    temporary = root / temporary_token
    try:
        path = temporary / PENDING_TRANSACTION_FILENAME
        greenfield_create_transaction.write_compiled_product_create_transaction_file(
            path,
            transaction,
            repo_root=root,
        )
        greenfield_transaction_path_boundary.rename_directory(root, temporary_token, target_token)
    except BaseException:
        try:
            if greenfield_transaction_path_boundary.path_kind(root, temporary_token) == "directory":
                greenfield_transaction_path_boundary.remove_tree(root, temporary_token)
        except (OSError, greenfield_transaction_path_boundary.GreenfieldTransactionPathError):
            pass
        raise
    return resolve_pending_transaction(repo_root=root, transaction_hash=digest)


def resolve_pending_transaction(*, repo_root: Path, transaction_hash: str) -> Path:
    """Resolve and verify the exact pending package named by a user decision."""

    digest = _require_digest(transaction_hash)
    directory = pending_transaction_directory(repo_root, digest)
    path = directory / PENDING_TRANSACTION_FILENAME
    root = Path(repo_root).expanduser().resolve()
    if greenfield_transaction_path_boundary.path_kind(root, directory) != "directory":
        raise ValueError("Greenfield pending transaction is missing or unsafe")
    transaction = greenfield_create_transaction.load_compiled_product_create_transaction_file(
        path,
        repo_root=root,
    )
    if transaction.transaction_hash != digest:
        raise ValueError("Greenfield pending transaction does not match its decision hash")
    return path


def discard_pending_transaction(*, repo_root: Path, transaction_hash: str) -> None:
    """Atomically remove one exact pending package after a terminal rejection."""

    digest = _require_digest(transaction_hash)
    root = Path(repo_root).expanduser().resolve()
    directory = pending_transaction_directory(repo_root, digest)
    if greenfield_transaction_path_boundary.path_kind(root, directory) != "directory":
        raise ValueError("Greenfield pending transaction does not exist")
    greenfield_transaction_path_boundary.scan_tree(root, directory, require_present=True)
    parent = directory.parent
    retired = parent / f".discard-{digest}"
    if greenfield_transaction_path_boundary.path_kind(root, retired) != "missing":
        raise RuntimeError("Greenfield pending transaction discard path is occupied")
    greenfield_transaction_path_boundary.rename_directory(root, directory, retired)
    greenfield_transaction_path_boundary.remove_tree(root, retired)


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
