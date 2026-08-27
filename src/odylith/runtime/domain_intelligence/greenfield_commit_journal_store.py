"""Descriptor-relative persistence primitives for Greenfield commit journals."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_transaction_path_boundary


def record_hash(record: Mapping[str, Any]) -> str:
    canonical = json.dumps(dict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_record(repo_root: Path, journal_token: str, record: Mapping[str, Any]) -> None:
    greenfield_transaction_path_boundary.atomic_write_bytes(
        repo_root,
        f"{journal_token}/state.v1.json",
        (
            json.dumps(
                dict(record),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8"),
    )


def is_empty_prewrite_orphan(repo_root: Path, journal_token: str) -> bool:
    try:
        if greenfield_transaction_path_boundary.path_kind(repo_root, journal_token) != "directory":
            return False
        if greenfield_transaction_path_boundary.path_kind(
            repo_root,
            f"{journal_token}/state.v1.json",
        ) != "missing":
            return False
        return not greenfield_transaction_path_boundary.list_directory(repo_root, journal_token)
    except (OSError, ValueError):
        return False


def quarantine_legacy_journal(
    repo_root: Path,
    journal_token: str,
    *,
    journal_parent_token: str,
) -> None:
    manual_root = f"{journal_parent_token}/manual-recovery"
    kind = greenfield_transaction_path_boundary.path_kind(repo_root, manual_root)
    if kind == "missing":
        greenfield_transaction_path_boundary.ensure_directory(repo_root, manual_root)
    elif kind != "directory":
        raise ValueError("greenfield commit journal manual-recovery directory is unsafe")
    destination = f"{manual_root}/{Path(journal_token).name}"
    if greenfield_transaction_path_boundary.path_kind(repo_root, destination) != "missing":
        raise ValueError("greenfield commit journal legacy recovery entry already exists")
    greenfield_transaction_path_boundary.rename_directory(
        repo_root,
        journal_token,
        destination,
    )


def discard_committed_artifacts(repo_root: Path, journal_token: str) -> None:
    for name in ("snapshot", "staging"):
        target = f"{journal_token}/{name}"
        kind = greenfield_transaction_path_boundary.path_kind(repo_root, target)
        if kind == "missing":
            continue
        if kind != "directory":
            raise ValueError("greenfield committed journal artifact is not a safe directory")
        greenfield_transaction_path_boundary.remove_tree(repo_root, target)


__all__ = [
    "discard_committed_artifacts",
    "is_empty_prewrite_orphan",
    "quarantine_legacy_journal",
    "record_hash",
    "write_record",
]
