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
from odylith.runtime.domain_intelligence.greenfield_create_contract import (
    PRODUCT_CREATE_TRANSACTION_COMPILER,
)
from odylith.runtime.domain_intelligence.greenfield_create_contract import (
    PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_create_contract import (
    PRODUCT_CREATE_TRANSACTION_RECEIPT_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_create_contract import PRODUCT_CREATE_TRANSACTION_VERSION
from odylith.runtime.domain_intelligence.greenfield_create_contract import POST_CONFIRM_ALLOWED_OPERATIONS
from odylith.runtime.domain_intelligence.greenfield_create_contract import POST_CONFIRM_FORBIDDEN_OPERATIONS
from odylith.runtime.domain_intelligence import greenfield_repository_write_set


_POSTCONFIRM_RUNTIME_SOURCE_FILES = (
    "__init__.py",
    "cli.py",
    "install/fs.py",
    "runtime/common/derivation_provenance.py",
    "runtime/domain_intelligence/greenfield_commit_journal.py",
    "runtime/domain_intelligence/greenfield_commit_transaction.py",
    "runtime/domain_intelligence/greenfield_create_cli.py",
    "runtime/domain_intelligence/greenfield_compiled_write.py",
    "runtime/domain_intelligence/greenfield_create_commit.py",
    "runtime/domain_intelligence/greenfield_create_contract.py",
    "runtime/domain_intelligence/greenfield_create_lifecycle.py",
    "runtime/domain_intelligence/greenfield_generation_state.py",
    "runtime/domain_intelligence/greenfield_generation_store.py",
    "runtime/domain_intelligence/greenfield_create_manifest.py",
    "runtime/domain_intelligence/greenfield_post_confirm_handoff.py",
    "runtime/domain_intelligence/greenfield_pending_transaction_store.py",
    "runtime/domain_intelligence/greenfield_proposals_cli.py",
    "runtime/domain_intelligence/greenfield_repository_lock.py",
    "runtime/domain_intelligence/greenfield_repository_write_set.py",
    "runtime/domain_intelligence/greenfield_transaction.py",
    "runtime/surfaces/greenfield_host_confirmation.py",
)
_VOLATILE_HASH_KEYS = frozenset({"elapsed_seconds", "whole_project_elapsed_seconds"})
_SEALED_COMMIT_ATTESTATION = object()


@dataclass(frozen=True)
class SealedGreenfieldCommitPackage:
    """The only compiled package fields post-confirm code may consume."""

    _repository_write_set_json: str
    _commit_result_preview_json: str
    _surface_refresh_preview_json: str

    @property
    def repository_write_set(self) -> Mapping[str, Any]:
        return _sealed_mapping_copy(self._repository_write_set_json)

    @property
    def commit_result_preview(self) -> Mapping[str, Any]:
        return _sealed_mapping_copy(self._commit_result_preview_json)

    @property
    def surface_refresh_preview(self) -> Mapping[str, Any]:
        return _sealed_mapping_copy(self._surface_refresh_preview_json)


@dataclass(frozen=True)
class SealedProductCreateCommit:
    """Hash-verified transaction projection for commit-only execution."""

    version: str
    release_selector: str
    _commit_manifest_preview_json: str
    _transaction_summary_json: str
    transaction_hash: str
    transaction_file: Path
    prewrite_package: SealedGreenfieldCommitPackage
    _attestation: object | None = None

    @property
    def verified(self) -> bool:
        return self._attestation is _SEALED_COMMIT_ATTESTATION

    @property
    def commit_manifest_preview(self) -> Mapping[str, Any]:
        """Return opaque pre-confirm evidence for the final commit report."""

        return _sealed_mapping_copy(self._commit_manifest_preview_json)

    def summary(self) -> dict[str, Any]:
        report = _sealed_mapping_copy(self._transaction_summary_json)
        write_set = self.prewrite_package.repository_write_set
        return {
            "version": self.version,
            "transaction_hash": self.transaction_hash,
            "verified": self.verified,
            "release_selector": self.release_selector,
            "quality_status": str(report.get("quality_status", "")).strip(),
            "validation_status": str(report.get("validation_status", "")).strip(),
            "compiler": str(report.get("compiler", "")).strip(),
            "compiler_phase": str(report.get("compiler_phase", "")).strip(),
            "product_facts_sha256": str(report.get("product_facts_sha256", "")).strip(),
            "intent_authority_version": str(report.get("intent_authority_version", "")).strip(),
            "surface_refresh_preview": dict(self.prewrite_package.surface_refresh_preview),
            "repository_write_set_hash": str(write_set.get("write_set_hash", "")).strip(),
            "repository_write_count": int(write_set.get("write_count", 0) or 0),
            "repository_delete_count": int(write_set.get("delete_count", 0) or 0),
            "repository_directory_delete_count": int(write_set.get("directory_delete_count", 0) or 0),
        }


def load_sealed_product_create_commit(
    path: Path,
    *,
    repo_root: Path | None = None,
) -> SealedProductCreateCommit:
    """Load only the sealed fields required by the post-confirm writer."""

    target = Path(path).expanduser()
    receipt_path = target.with_name(target.name + ".compiler-receipt.v1.json")
    if target.is_symlink() or receipt_path.is_symlink():
        raise ValueError("ProductCreateTransaction file and compiler receipt must not be symlinks")
    try:
        payload_bytes = target.read_bytes()
        receipt_bytes = receipt_path.read_bytes()
        receipt_payload = json.loads(receipt_bytes.decode("utf-8"))
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
    expected_receipt_fields = {
        "version",
        "transaction_hash",
        "transaction_file_sha256",
        "post_confirm_runtime_identity",
    }
    if set(receipt_payload) != expected_receipt_fields or receipt_bytes != canonical_product_create_transaction_receipt_bytes(
        receipt_payload
    ):
        raise ValueError("ProductCreateTransaction compiler receipt bytes are not canonical")
    if str(receipt_payload.get("version", "")).strip() != PRODUCT_CREATE_TRANSACTION_RECEIPT_VERSION:
        raise ValueError("ProductCreateTransaction compiler receipt has an unsupported version")
    if hashlib.sha256(payload_bytes).hexdigest() != str(receipt_payload.get("transaction_file_sha256", "")).strip():
        raise ValueError("ProductCreateTransaction file does not match its pre-confirm compiler receipt")
    runtime_identity = receipt_payload.get("post_confirm_runtime_identity")
    if not isinstance(runtime_identity, Mapping) or dict(runtime_identity) != build_product_create_transaction_compiler_identity():
        raise ValueError(
            "ProductCreateTransaction post-confirm runtime changed after pre-confirm compilation; "
            "rebuild the transaction before committing governed records"
        )
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
    commit_manifest_preview = payload.get("quality_manifest")
    transaction_summary = payload.get("commit_summary")
    if (
        not isinstance(write_set, Mapping)
        or not isinstance(commit_preview, Mapping)
        or not isinstance(commit_manifest_preview, Mapping)
        or not isinstance(transaction_summary, Mapping)
    ):
        raise ValueError("ProductCreateTransaction is missing its sealed commit package")
    compiler_provenance = payload.get("compiler_provenance")
    if not isinstance(compiler_provenance, Mapping):
        raise ValueError("ProductCreateTransaction is missing compiler provenance")
    if repo_root is not None:
        require_product_create_transaction_compiler_provenance_payload(
            compiler_provenance,
            quality_manifest=commit_manifest_preview,
            repo_root=repo_root,
        )
    sealed = SealedProductCreateCommit(
        version=PRODUCT_CREATE_TRANSACTION_VERSION,
        release_selector=str(payload.get("release_selector", "")).strip(),
        _commit_manifest_preview_json=_sealed_mapping_json(commit_manifest_preview),
        _transaction_summary_json=_sealed_mapping_json(transaction_summary),
        transaction_hash=transaction_hash,
        transaction_file=target.resolve(),
        prewrite_package=SealedGreenfieldCommitPackage(
            _repository_write_set_json=_sealed_mapping_json(write_set),
            _commit_result_preview_json=_sealed_mapping_json(commit_preview),
            _surface_refresh_preview_json=_sealed_mapping_json(surface_preview),
        ),
        _attestation=_SEALED_COMMIT_ATTESTATION,
    )
    require_sealed_commit_transaction(sealed)
    return sealed


def require_sealed_commit_transaction(transaction: Any) -> None:
    """Require only the execution envelope needed after confirmation.

    Product interpretation, custody, and quality were settled before the user
    saw CONFIRM. The commit path keeps their reporting bytes opaque and checks
    only the executable write protocol.
    """

    if not bool(getattr(transaction, "verified", False)):
        raise ValueError(
            "ProductCreateTransaction was not accepted by the pre-confirm compiler; compile the transaction before committing governed records"
        )
    package = getattr(transaction, "prewrite_package", None)
    write_set = getattr(package, "repository_write_set", None)
    greenfield_repository_write_set.require_compiled_greenfield_repository_write_set(write_set)


def require_product_create_transaction_compiler_provenance_payload(
    provenance: Mapping[str, Any],
    *,
    quality_manifest: Mapping[str, Any],
    repo_root: Path,
) -> None:
    """Validate compiler provenance before the transaction enters the write boundary."""

    root = Path(repo_root).expanduser().resolve()
    expected = {
        "compiler": PRODUCT_CREATE_TRANSACTION_COMPILER,
        "transaction_version": PRODUCT_CREATE_TRANSACTION_VERSION,
        "phase": "pre_confirm_compile",
        "commit_policy": PRODUCT_CREATE_TRANSACTION_COMMIT_POLICY,
        "repo_root_fingerprint": hashlib.sha256(str(root).encode("utf-8")).hexdigest(),
        "quality_manifest_version": str(quality_manifest.get("version", "")).strip(),
        "quality_manifest_engine": str(quality_manifest.get("engine", "")).strip(),
    }
    for key, expected_value in expected.items():
        if str(provenance.get(key, "")).strip() != expected_value:
            raise ValueError(
                "ProductCreateTransaction compiler provenance was invalidated by a runtime or repository-context change; "
                "no Product Intent was rejected and no governed records were written. "
                "Rebuild the pre-confirm transaction before committing."
            )
    identity = provenance.get("compiler_identity") if isinstance(provenance.get("compiler_identity"), Mapping) else {}
    expected_identity = build_product_create_transaction_compiler_identity()
    for key, expected_value in expected_identity.items():
        if identity.get(key) != expected_value:
            raise ValueError(
                "ProductCreateTransaction compiler identity was invalidated by a runtime or compiler change; "
                "no Product Intent or compiled artifact failed, and no governed records were written. "
                "Rebuild the pre-confirm transaction before committing."
            )
    if tuple(provenance.get("post_confirm_allowed_operations") or ()) != POST_CONFIRM_ALLOWED_OPERATIONS:
        raise ValueError(
            "ProductCreateTransaction was invalidated because the commit-only runtime contract changed; "
            "no Product Intent was rejected and no governed records were written. "
            "Rebuild the pre-confirm transaction before committing."
        )
    if tuple(provenance.get("post_confirm_forbidden_operations") or ()) != POST_CONFIRM_FORBIDDEN_OPERATIONS:
        raise ValueError(
            "ProductCreateTransaction was invalidated because the commit-only runtime contract changed; "
            "no Product Intent was rejected and no governed records were written. "
            "Rebuild the pre-confirm transaction before committing."
        )


def build_product_create_transaction_compiler_identity() -> dict[str, Any]:
    source_root = Path(__file__).resolve().parents[2]
    paths = tuple(source_root / name for name in _POSTCONFIRM_RUNTIME_SOURCE_FILES)
    return {
        "version": PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION,
        "odylith_version": __version__,
        "source_files_sha256": derivation_provenance.fingerprint_source_files(paths),
        "source_file_count": len(paths),
    }


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
        "commit_summary",
    )
    canonical = json.dumps(
        {field: _json_ready(payload.get(field)) for field in fields},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def canonical_product_create_transaction_receipt_bytes(receipt: Mapping[str, Any]) -> bytes:
    """Return the one accepted serialized form for a compiler receipt."""

    return (json.dumps(dict(receipt), indent=2, sort_keys=True) + "\n").encode("utf-8")


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


def _sealed_mapping_json(value: Any) -> str:
    if not isinstance(value, Mapping):
        raise ValueError("ProductCreateTransaction sealed package contains an invalid mapping")
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _sealed_mapping_copy(payload: str) -> Mapping[str, Any]:
    value = json.loads(payload)
    if not isinstance(value, Mapping):
        raise RuntimeError("ProductCreateTransaction sealed package integrity was invalidated in memory")
    return dict(value)


__all__ = [
    "SealedGreenfieldCommitPackage",
    "SealedProductCreateCommit",
    "build_product_create_transaction_compiler_identity",
    "canonical_product_create_transaction_receipt_bytes",
    "load_sealed_product_create_commit",
    "require_product_create_transaction_compiler_provenance_payload",
    "require_sealed_commit_transaction",
]
