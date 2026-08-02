"""Immutable generation materialization and pointer-pinned Greenfield reads."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any

from odylith.install.fs import atomic_write_text
from odylith.install.fs import fsync_directory
from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_repository_write_set


GREENFIELD_GENERATION_MANIFEST_VERSION = "odylith.greenfield.immutable-generation.v1"
_DIGEST = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class PinnedGreenfieldGeneration:
    transaction_hash: str
    write_set_hash: str
    generation_root: Path
    repository_root: Path
    manifest_sha256: str
    manifest: Mapping[str, Any]


def generation_root(repo_root: Path, transaction_hash: str) -> Path:
    transaction = _require_digest(transaction_hash, label="transaction hash")
    return (
        Path(repo_root).expanduser().resolve()
        / ".odylith/runtime/greenfield/generations"
        / transaction
    )


def materialize_immutable_greenfield_generation(
    *,
    repo_root: Path,
    transaction_hash: str,
    write_set: object,
) -> PinnedGreenfieldGeneration:
    """Materialize one transaction-addressed generation from sealed after-image bytes."""

    root = Path(repo_root).expanduser().resolve()
    transaction = _require_digest(transaction_hash, label="transaction hash")
    payload = greenfield_repository_write_set.require_compiled_greenfield_repository_write_set(write_set)
    parent = generation_root(root, transaction).parent
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
        raise RuntimeError("Greenfield generation store is unsafe")
    parent.mkdir(parents=True, exist_ok=True)
    fsync_directory(parent.parent)
    target = parent / transaction
    if target.exists() or target.is_symlink():
        return pin_greenfield_generation(
            repo_root=root,
            transaction_hash=transaction,
            expected_write_set=payload,
        )
    temporary = Path(tempfile.mkdtemp(prefix=f".prepare-{transaction[:12]}-", dir=parent))
    try:
        repository = temporary / "repository"
        materialized = greenfield_repository_write_set.materialize_compiled_greenfield_after_image(
            destination_root=repository,
            write_set=payload,
            temporary_directory=temporary / ".writes",
        )
        writes_tmp = temporary / ".writes"
        if writes_tmp.exists():
            shutil.rmtree(writes_tmp)
        manifest = _generation_manifest(
            transaction_hash=transaction,
            write_set=payload,
            materialized=materialized,
        )
        atomic_write_text(
            temporary / "generation-manifest.v1.json",
            _canonical_manifest_bytes(manifest).decode("utf-8"),
        )
        fsync_directory(temporary)
        temporary.replace(target)
        fsync_directory(parent)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return pin_greenfield_generation(
        repo_root=root,
        transaction_hash=transaction,
        expected_write_set=payload,
    )


def publish_greenfield_generation(
    *,
    repo_root: Path,
    generation: PinnedGreenfieldGeneration,
    expected_active_identity: Mapping[str, Any],
) -> dict[str, Any]:
    pinned = pin_greenfield_generation(
        repo_root=repo_root,
        transaction_hash=generation.transaction_hash,
    )
    return greenfield_generation_state.publish_active_generation_state(
        repo_root=repo_root,
        expected_identity=expected_active_identity,
        transaction_hash=pinned.transaction_hash,
        write_set_hash=pinned.write_set_hash,
        generation_manifest_sha256=pinned.manifest_sha256,
    )


def pin_active_greenfield_generation(repo_root: Path) -> PinnedGreenfieldGeneration:
    """Resolve the active-state record once and pin that exact immutable generation."""

    root = Path(repo_root).expanduser().resolve()
    state = greenfield_generation_state.read_active_generation_state(root)
    if state is None or str(state.get("status") or "") != greenfield_generation_state.ACTIVE:
        raise RuntimeError("Greenfield has no active immutable generation")
    pinned = pin_greenfield_generation(
        repo_root=root,
        transaction_hash=str(state["transaction_hash"]),
    )
    if pinned.write_set_hash != str(state["write_set_hash"]):
        raise RuntimeError("Greenfield active generation write-set binding is invalid")
    if pinned.manifest_sha256 != str(state["generation_manifest_sha256"]):
        raise RuntimeError("Greenfield active generation manifest binding is invalid")
    return pinned


def pin_greenfield_generation(
    *,
    repo_root: Path,
    transaction_hash: str,
    expected_write_set: object | None = None,
) -> PinnedGreenfieldGeneration:
    root = Path(repo_root).expanduser().resolve()
    transaction = _require_digest(transaction_hash, label="transaction hash")
    target = generation_root(root, transaction)
    manifest_path = target / "generation-manifest.v1.json"
    repository = target / "repository"
    if target.is_symlink() or not target.is_dir() or manifest_path.is_symlink() or not manifest_path.is_file():
        raise RuntimeError("Greenfield immutable generation is missing or unsafe")
    if repository.is_symlink() or not repository.is_dir():
        raise RuntimeError("Greenfield immutable generation repository is missing or unsafe")
    try:
        raw = manifest_path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Greenfield immutable generation manifest is unreadable") from exc
    if not isinstance(payload, Mapping) or raw != _canonical_manifest_bytes(payload):
        raise RuntimeError("Greenfield immutable generation manifest bytes are not canonical")
    manifest = dict(payload)
    _require_generation_manifest(manifest, transaction_hash=transaction)
    if expected_write_set is not None:
        write_set = greenfield_repository_write_set.require_compiled_greenfield_repository_write_set(
            expected_write_set
        )
        if str(write_set["write_set_hash"]) != str(manifest["write_set_hash"]):
            raise RuntimeError("Greenfield immutable generation does not match the sealed transaction")
        greenfield_repository_write_set.require_greenfield_repository_after_state(
            repo_root=repository,
            write_set=write_set,
        )
    return PinnedGreenfieldGeneration(
        transaction_hash=transaction,
        write_set_hash=str(manifest["write_set_hash"]),
        generation_root=target,
        repository_root=repository,
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
        manifest=manifest,
    )


def discard_unpublished_greenfield_generation(*, repo_root: Path, transaction_hash: str) -> None:
    root = Path(repo_root).expanduser().resolve()
    transaction = _require_digest(transaction_hash, label="transaction hash")
    state = greenfield_generation_state.read_active_generation_state(root)
    if state is not None and str(state.get("transaction_hash") or "") == transaction:
        return
    target = generation_root(root, transaction)
    if target.is_symlink():
        raise RuntimeError("Greenfield immutable generation path is unsafe")
    if target.is_dir():
        shutil.rmtree(target)
        fsync_directory(target.parent)


def _generation_manifest(
    *,
    transaction_hash: str,
    write_set: Mapping[str, Any],
    materialized: Mapping[str, Any],
) -> dict[str, Any]:
    after_image = write_set["after_image"]
    return {
        "version": GREENFIELD_GENERATION_MANIFEST_VERSION,
        "transaction_hash": transaction_hash,
        "write_set_hash": str(write_set["write_set_hash"]),
        "after_fingerprints": dict(write_set["after_fingerprints"]),
        "directory_count": int(after_image["directory_count"]),
        "file_count": int(after_image["file_count"]),
        "byte_count": int(after_image["byte_count"]),
        "materialization_status": str(materialized.get("status") or ""),
    }


def _require_generation_manifest(manifest: Mapping[str, Any], *, transaction_hash: str) -> None:
    if str(manifest.get("version") or "") != GREENFIELD_GENERATION_MANIFEST_VERSION:
        raise RuntimeError("Greenfield immutable generation manifest version is unsupported")
    if str(manifest.get("transaction_hash") or "") != transaction_hash:
        raise RuntimeError("Greenfield immutable generation transaction binding is invalid")
    _require_digest(manifest.get("write_set_hash"), label="write-set hash")
    if str(manifest.get("materialization_status") or "") != "passed":
        raise RuntimeError("Greenfield immutable generation was not fully materialized")
    for key in ("directory_count", "file_count", "byte_count"):
        if not isinstance(manifest.get(key), int) or int(manifest[key]) < 0:
            raise RuntimeError("Greenfield immutable generation manifest counts are invalid")
    fingerprints = manifest.get("after_fingerprints")
    if not isinstance(fingerprints, Mapping) or set(fingerprints) != set(
        greenfield_repository_write_set.GREENFIELD_REPOSITORY_WRITE_PATHS
    ):
        raise RuntimeError("Greenfield immutable generation fingerprints are incomplete")
    if any(not _DIGEST.fullmatch(str(value or "")) for value in fingerprints.values()):
        raise RuntimeError("Greenfield immutable generation fingerprints are invalid")


def _canonical_manifest_bytes(manifest: Mapping[str, Any]) -> bytes:
    return (json.dumps(dict(manifest), indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def _require_digest(value: Any, *, label: str) -> str:
    token = str(value or "").strip()
    if not _DIGEST.fullmatch(token):
        raise ValueError(f"Greenfield {label} must be a SHA-256 value")
    return token


__all__ = [
    "GREENFIELD_GENERATION_MANIFEST_VERSION",
    "PinnedGreenfieldGeneration",
    "discard_unpublished_greenfield_generation",
    "generation_root",
    "materialize_immutable_greenfield_generation",
    "pin_active_greenfield_generation",
    "pin_greenfield_generation",
    "publish_greenfield_generation",
]
