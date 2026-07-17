"""Minimal sealed transaction loader for the post-confirm create path."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from odylith import __version__
from odylith.runtime.common import derivation_provenance
from odylith.runtime.domain_intelligence.greenfield_create_contract import (
    PRODUCT_CREATE_TRANSACTION_COMMIT_POLICY,
)
from odylith.runtime.domain_intelligence.greenfield_create_contract import PRODUCT_CREATE_TRANSACTION_COMPILER
from odylith.runtime.domain_intelligence.greenfield_create_contract import (
    PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_create_contract import (
    PRODUCT_CREATE_TRANSACTION_RECEIPT_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_create_contract import PRODUCT_CREATE_TRANSACTION_VERSION


_POSTCONFIRM_RUNTIME_SOURCE_FILES = (
    "__init__.py",
    "install/fs.py",
    "runtime/common/derivation_provenance.py",
    "runtime/domain_intelligence/greenfield_commit_journal.py",
    "runtime/domain_intelligence/greenfield_commit_transaction.py",
    "runtime/domain_intelligence/greenfield_compiled_write.py",
    "runtime/domain_intelligence/greenfield_create_commit.py",
    "runtime/domain_intelligence/greenfield_create_contract.py",
    "runtime/domain_intelligence/greenfield_create_manifest.py",
    "runtime/domain_intelligence/greenfield_repository_write_set.py",
    "runtime/domain_intelligence/greenfield_transaction.py",
)
_VOLATILE_HASH_KEYS = frozenset({"elapsed_seconds", "whole_project_elapsed_seconds"})
_SEALED_COMMIT_ATTESTATION = object()


@dataclass(frozen=True)
class SealedGreenfieldCommitPackage:
    """The only compiled package fields post-confirm code may consume."""

    repository_write_set: Mapping[str, Any]
    commit_result_preview: Mapping[str, Any]
    surface_refresh_preview: Mapping[str, Any]


@dataclass(frozen=True)
class SealedProductCreateCommit:
    """Hash-verified transaction projection for commit-only execution."""

    version: str
    release_selector: str
    intent_authority: Mapping[str, Any]
    quality_manifest: Mapping[str, Any]
    compiler_provenance: Mapping[str, Any]
    transaction_hash: str
    prewrite_package: SealedGreenfieldCommitPackage
    _attestation: object | None = None

    @property
    def verified(self) -> bool:
        return self._attestation is _SEALED_COMMIT_ATTESTATION

    def summary(self) -> dict[str, Any]:
        write_set = self.prewrite_package.repository_write_set
        return {
            "version": self.version,
            "transaction_hash": self.transaction_hash,
            "verified": self.verified,
            "release_selector": self.release_selector,
            "quality_status": str(self.quality_manifest.get("status", "")).strip(),
            "validation_status": str(self.quality_manifest.get("validation_status", "")).strip(),
            "compiler": str(self.compiler_provenance.get("compiler", "")).strip(),
            "compiler_phase": str(self.compiler_provenance.get("phase", "")).strip(),
            "product_facts_sha256": str(self.intent_authority.get("product_facts_sha256", "")).strip(),
            "intent_authority_version": str(self.intent_authority.get("version", "")).strip(),
            "surface_refresh_preview": dict(self.prewrite_package.surface_refresh_preview),
            "repository_write_set_hash": str(write_set.get("write_set_hash", "")).strip(),
            "repository_write_count": int(write_set.get("write_count", 0) or 0),
            "repository_delete_count": int(write_set.get("delete_count", 0) or 0),
            "repository_directory_delete_count": int(write_set.get("directory_delete_count", 0) or 0),
        }


def load_sealed_product_create_commit(path: Path) -> SealedProductCreateCommit:
    """Load only the sealed fields required by the post-confirm writer."""

    target = Path(path).expanduser()
    receipt_path = target.with_name(target.name + ".compiler-receipt.v1.json")
    if target.is_symlink() or receipt_path.is_symlink():
        raise ValueError("ProductCreateTransaction file and compiler receipt must not be symlinks")
    try:
        payload_bytes = target.read_bytes()
        receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        payload = json.loads(payload_bytes.decode("utf-8"))
    except FileNotFoundError as error:
        raise ValueError(
            "ProductCreateTransaction is missing its pre-confirm compiler receipt; rebuild it with greenfield propose"
        ) from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(
            "ProductCreateTransaction or compiler receipt is malformed; no Product Intent was rejected and no governed records were written. "
            "Rebuild the pre-confirm transaction before committing."
        ) from error
    except OSError as error:
        raise RuntimeError(
            "environment/IO failure while reading the pre-confirm ProductCreateTransaction; no governed records were written"
        ) from error
    if not isinstance(payload, Mapping) or not isinstance(receipt_payload, Mapping):
        raise ValueError("ProductCreateTransaction and compiler receipt must be JSON objects")
    if str(receipt_payload.get("version", "")).strip() != PRODUCT_CREATE_TRANSACTION_RECEIPT_VERSION:
        raise ValueError("ProductCreateTransaction compiler receipt has an unsupported version")
    if hashlib.sha256(payload_bytes).hexdigest() != str(receipt_payload.get("transaction_file_sha256", "")).strip():
        raise ValueError("ProductCreateTransaction file does not match its pre-confirm compiler receipt")
    transaction_hash = str(payload.get("transaction_hash", "")).strip()
    if not transaction_hash or transaction_hash != _payload_hash(payload):
        raise ValueError("ProductCreateTransaction hash mismatch; rebuild the transaction before committing governed records")
    if str(receipt_payload.get("transaction_hash", "")).strip() != transaction_hash:
        raise ValueError("ProductCreateTransaction hash does not match its pre-confirm compiler receipt")
    if str(payload.get("version", "")).strip() != PRODUCT_CREATE_TRANSACTION_VERSION:
        raise ValueError("ProductCreateTransaction has an unsupported version")
    package = payload.get("prewrite_package")
    if not isinstance(package, Mapping):
        raise ValueError("ProductCreateTransaction is missing its sealed prewrite package")
    write_set = package.get("repository_write_set")
    commit_preview = package.get("commit_result_preview")
    surface_preview = package.get("surface_refresh_preview")
    if not isinstance(write_set, Mapping) or not isinstance(commit_preview, Mapping):
        raise ValueError("ProductCreateTransaction is missing its sealed commit package")
    return SealedProductCreateCommit(
        version=PRODUCT_CREATE_TRANSACTION_VERSION,
        release_selector=str(payload.get("release_selector", "")).strip(),
        intent_authority=_mapping(payload.get("intent_authority")),
        quality_manifest=_mapping(payload.get("quality_manifest")),
        compiler_provenance=_mapping(payload.get("compiler_provenance")),
        transaction_hash=transaction_hash,
        prewrite_package=SealedGreenfieldCommitPackage(
            repository_write_set=_mapping(write_set),
            commit_result_preview=_mapping(commit_preview),
            surface_refresh_preview=_mapping(surface_preview),
        ),
        _attestation=_SEALED_COMMIT_ATTESTATION,
    )


def require_sealed_commit_transaction(transaction: Any) -> None:
    if not bool(getattr(transaction, "verified", False)):
        raise ValueError(
            "ProductCreateTransaction was not accepted by the pre-confirm compiler; compile the transaction before committing governed records"
        )
    authority = getattr(transaction, "intent_authority", None)
    if not isinstance(authority, Mapping) or not str(authority.get("authority_snapshot_sha256", "")).strip():
        raise ValueError("ProductCreateTransaction is missing sealed Product Intent authority")


def build_product_create_transaction_compiler_identity() -> dict[str, Any]:
    source_root = Path(__file__).resolve().parents[2]
    paths = tuple(source_root / name for name in _POSTCONFIRM_RUNTIME_SOURCE_FILES)
    return {
        "version": PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION,
        "odylith_version": __version__,
        "source_files_sha256": derivation_provenance.fingerprint_source_files(paths),
        "source_file_count": len(paths),
    }


def require_sealed_commit_provenance(transaction: Any, *, repo_root: Path) -> None:
    provenance = getattr(transaction, "compiler_provenance", None)
    manifest = getattr(transaction, "quality_manifest", None)
    if not isinstance(provenance, Mapping) or not isinstance(manifest, Mapping):
        raise ValueError("ProductCreateTransaction compiler provenance is invalid")
    expected = {
        "compiler": PRODUCT_CREATE_TRANSACTION_COMPILER,
        "transaction_version": PRODUCT_CREATE_TRANSACTION_VERSION,
        "phase": "pre_confirm_compile",
        "commit_policy": PRODUCT_CREATE_TRANSACTION_COMMIT_POLICY,
        "repo_root_fingerprint": hashlib.sha256(str(Path(repo_root).expanduser().resolve()).encode("utf-8")).hexdigest(),
        "quality_manifest_version": str(manifest.get("version", "")).strip(),
        "quality_manifest_engine": str(manifest.get("engine", "")).strip(),
    }
    for key, value in expected.items():
        if str(provenance.get(key, "")).strip() != value:
            raise ValueError(_stale_runtime_message())
    identity = provenance.get("compiler_identity")
    if not isinstance(identity, Mapping) or dict(identity) != build_product_create_transaction_compiler_identity():
        raise ValueError(_stale_runtime_message())


def _payload_hash(payload: Mapping[str, Any]) -> str:
    fields = (
        "version",
        "release_selector",
        "proposal",
        "validation_gate",
        "prewrite_package",
        "backlog_result",
        "intent_authority",
        "quality_manifest",
        "compiler_provenance",
    )
    canonical = json.dumps(
        {field: _json_ready(payload.get(field)) for field in fields},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _json_ready(item)
            for key, item in sorted(value.items(), key=lambda row: str(row[0]))
            if str(key) not in _VOLATILE_HASH_KEYS
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_ready(item) for item in value]
    return value


def _mapping(value: Any) -> Mapping[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _stale_runtime_message() -> str:
    return (
        "ProductCreateTransaction compiler identity was invalidated by a runtime or repository-context change; "
        "no Product Intent was rejected and no governed records were written. Rebuild the pre-confirm transaction before committing."
    )


__all__ = [
    "SealedGreenfieldCommitPackage",
    "SealedProductCreateCommit",
    "build_product_create_transaction_compiler_identity",
    "load_sealed_product_create_commit",
    "require_sealed_commit_provenance",
    "require_sealed_commit_transaction",
]
