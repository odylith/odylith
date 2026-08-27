"""Read-only state comparison for interrupted Greenfield transaction recovery."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_transaction_path_boundary


def snapshot_tree(
    repo_root: Path,
    tree_token: str,
    *,
    owner: str,
    required: bool,
    missing_marker: str = "",
) -> tuple[dict[str, tuple[bytes, int]], set[str]]:
    """Capture one recovery owner through the transaction no-follow boundary."""

    if missing_marker and greenfield_transaction_path_boundary.path_kind(
        repo_root,
        missing_marker,
    ) != "missing":
        if (
            not required
            or greenfield_transaction_path_boundary.path_kind(repo_root, tree_token)
            != "missing"
            or greenfield_transaction_path_boundary.read_bytes(repo_root, missing_marker)
            != b"missing\n"
        ):
            raise ValueError("greenfield commit snapshot has an invalid missing-path marker")
        return {}, set()
    entries = greenfield_transaction_path_boundary.scan_tree(repo_root, tree_token)
    if not entries:
        if required:
            raise ValueError("greenfield commit recovery snapshot is missing a protected path")
        return {}, set()
    files: dict[str, tuple[bytes, int]] = {}
    directories: set[str] = set()
    tree_parts = Path(tree_token).parts
    for entry in entries:
        suffix = Path(*Path(entry.path).parts[len(tree_parts) :]).as_posix()
        token = owner if suffix == "." else f"{owner}/{suffix}"
        if entry.kind == "file":
            files[token] = (entry.data, entry.mode)
        else:
            directories.add(token)
    return files, directories


def safe_interrupted_tree(
    *,
    owner: str,
    before_files: Mapping[str, tuple[bytes, int]],
    before_directories: set[str],
    current_files: Mapping[str, tuple[bytes, int]],
    current_directories: set[str],
    writes: Mapping[str, tuple[bytes, int]],
    deletes: set[str],
    created_directories: set[str],
    deleted_directories: set[str],
) -> bool:
    """Accept only exact before/after states within one sealed recovery owner."""

    def owned(token: str) -> bool:
        return token == owner or token.startswith(owner + "/")

    expected_writes = {path: state for path, state in writes.items() if owned(path)}
    expected_deletes = {path for path in deletes if owned(path)}
    expected_created_directories = {path for path in created_directories if owned(path)}
    expected_deleted_directories = {path for path in deleted_directories if owned(path)}
    allowed_files = set(before_files) | set(expected_writes)
    if set(current_files) - allowed_files:
        return False
    for path in allowed_files:
        before = before_files.get(path)
        current = current_files.get(path)
        after = expected_writes.get(path)
        if path in expected_deletes:
            if current not in {before, None}:
                return False
        elif current not in {before, after}:
            return False
    allowed_directories = before_directories | expected_created_directories
    if not current_directories <= allowed_directories:
        return False
    return all(
        path in current_directories
        for path in before_directories - expected_deleted_directories
    )


__all__ = ["safe_interrupted_tree", "snapshot_tree"]
