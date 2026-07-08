"""Precompiled create transactions for confirmed greenfield writes."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import fields
from dataclasses import is_dataclass
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.governance import validate_backlog_contract as backlog_contract


PRODUCT_CREATE_TRANSACTION_VERSION = "odylith.greenfield.product_create_transaction.v1"
PRODUCT_CREATE_TRANSACTION_COMPILER = "odylith.greenfield.compile_transaction.v1"
PRODUCT_CREATE_TRANSACTION_COMMIT_POLICY = "hash_verified_commit_only"
_POST_CONFIRM_ALLOWED_OPERATIONS = (
    "verify_transaction_hash",
    "verify_compiler_provenance",
    "verify_repo_preconditions",
    "write_staged_governed_records",
    "validate_readback",
    "refresh_required_surfaces",
    "report_success",
)
_POST_CONFIRM_FORBIDDEN_OPERATIONS = (
    "product_interpretation",
    "artifact_generation",
    "semantic_repair",
    "markdown_parsing",
    "host_model_work",
    "quality_repair",
)
_VOLATILE_HASH_KEYS = {
    "elapsed_seconds",
    "whole_project_elapsed_seconds",
}


@dataclass(frozen=True)
class ProductCreateTransaction:
    """Validated package that post-confirm code may only verify and commit."""

    version: str
    release_selector: str
    proposal: Mapping[str, Any]
    validation_gate: Mapping[str, Any]
    prewrite_package: GreenfieldCompletionPackage
    backlog_result: Mapping[str, Any]
    quality_manifest: Mapping[str, Any]
    compiler_provenance: Mapping[str, Any]
    transaction_hash: str

    @property
    def verified(self) -> bool:
        return self.transaction_hash == product_create_transaction_hash(self)

    def summary(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "transaction_hash": self.transaction_hash,
            "verified": self.verified,
            "release_selector": self.release_selector,
            "quality_status": str(self.quality_manifest.get("status", "")).strip(),
            "validation_status": str(self.quality_manifest.get("validation_status", "")).strip(),
            "compiler": str(self.compiler_provenance.get("compiler", "")).strip(),
            "compiler_phase": str(self.compiler_provenance.get("phase", "")).strip(),
        }


def build_product_create_transaction(
    *,
    proposal: Mapping[str, Any],
    release_selector: str,
    validation_gate: Mapping[str, Any],
    prewrite_package: GreenfieldCompletionPackage,
    backlog_result: Mapping[str, Any],
    quality_manifest: Mapping[str, Any],
    repo_root: Path,
) -> ProductCreateTransaction:
    """Build a hash-bound transaction from an already validated prewrite package."""

    transaction = ProductCreateTransaction(
        version=PRODUCT_CREATE_TRANSACTION_VERSION,
        release_selector=str(release_selector or "").strip(),
        proposal=proposal,
        validation_gate=validation_gate,
        prewrite_package=prewrite_package,
        backlog_result=backlog_result,
        quality_manifest=quality_manifest,
        compiler_provenance=build_product_create_transaction_provenance(
            repo_root=repo_root,
            quality_manifest=quality_manifest,
        ),
        transaction_hash="",
    )
    return replace(transaction, transaction_hash=product_create_transaction_hash(transaction))


def require_product_create_transaction_verified(transaction: ProductCreateTransaction) -> None:
    """Fail closed when a commit request does not match the compiled package hash."""

    expected = product_create_transaction_hash(transaction)
    if transaction.transaction_hash != expected:
        raise ValueError(
            "ProductCreateTransaction hash mismatch; rebuild the transaction before committing governed records"
        )


def build_product_create_transaction_provenance(
    *,
    repo_root: Path,
    quality_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "compiler": PRODUCT_CREATE_TRANSACTION_COMPILER,
        "transaction_version": PRODUCT_CREATE_TRANSACTION_VERSION,
        "phase": "pre_confirm_compile",
        "commit_policy": PRODUCT_CREATE_TRANSACTION_COMMIT_POLICY,
        "repo_root_fingerprint": product_create_transaction_repo_fingerprint(repo_root),
        "quality_manifest_version": str(quality_manifest.get("version", "")).strip(),
        "quality_manifest_engine": str(quality_manifest.get("engine", "")).strip(),
        "post_confirm_allowed_operations": list(_POST_CONFIRM_ALLOWED_OPERATIONS),
        "post_confirm_forbidden_operations": list(_POST_CONFIRM_FORBIDDEN_OPERATIONS),
    }


def product_create_transaction_repo_fingerprint(repo_root: Path) -> str:
    root = Path(repo_root).expanduser().resolve()
    return hashlib.sha256(str(root).encode("utf-8")).hexdigest()


def require_product_create_transaction_compiler_provenance(
    transaction: ProductCreateTransaction,
    *,
    repo_root: Path,
) -> None:
    provenance = transaction.compiler_provenance if isinstance(transaction.compiler_provenance, Mapping) else {}
    expected = {
        "compiler": PRODUCT_CREATE_TRANSACTION_COMPILER,
        "transaction_version": PRODUCT_CREATE_TRANSACTION_VERSION,
        "phase": "pre_confirm_compile",
        "commit_policy": PRODUCT_CREATE_TRANSACTION_COMMIT_POLICY,
        "repo_root_fingerprint": product_create_transaction_repo_fingerprint(repo_root),
        "quality_manifest_version": str(transaction.quality_manifest.get("version", "")).strip(),
        "quality_manifest_engine": str(transaction.quality_manifest.get("engine", "")).strip(),
    }
    for key, expected_value in expected.items():
        if str(provenance.get(key, "")).strip() != expected_value:
            raise ValueError(
                "ProductCreateTransaction compiler provenance is not approved for this repo; "
                "rebuild the pre-confirm transaction before committing governed records"
            )
    if tuple(provenance.get("post_confirm_allowed_operations") or ()) != _POST_CONFIRM_ALLOWED_OPERATIONS:
        raise ValueError(
            "ProductCreateTransaction compiler provenance is missing the commit-only operation contract; "
            "rebuild the pre-confirm transaction before committing governed records"
        )
    if tuple(provenance.get("post_confirm_forbidden_operations") or ()) != _POST_CONFIRM_FORBIDDEN_OPERATIONS:
        raise ValueError(
            "ProductCreateTransaction compiler provenance is missing the post-confirm forbidden-operation contract; "
            "rebuild the pre-confirm transaction before committing governed records"
        )


def product_create_transaction_to_dict(transaction: ProductCreateTransaction) -> dict[str, Any]:
    """Return the persisted transaction payload that a commit-only create can trust."""

    payload = _transaction_hash_payload(transaction)
    payload["transaction_hash"] = str(transaction.transaction_hash or "").strip()
    return payload


def product_create_transaction_from_dict(payload: Mapping[str, Any]) -> ProductCreateTransaction:
    """Rehydrate and verify a serialized ProductCreateTransaction."""

    if not isinstance(payload, Mapping):
        raise ValueError("ProductCreateTransaction payload must be a JSON object")
    version = str(payload.get("version", "")).strip()
    if version != PRODUCT_CREATE_TRANSACTION_VERSION:
        raise ValueError(
            f"unsupported ProductCreateTransaction version {version!r}; expected {PRODUCT_CREATE_TRANSACTION_VERSION}"
        )
    transaction = ProductCreateTransaction(
        version=version,
        release_selector=str(payload.get("release_selector", "")).strip(),
        proposal=_mapping(payload.get("proposal")),
        validation_gate=_mapping(payload.get("validation_gate")),
        prewrite_package=_completion_package_from_payload(_mapping(payload.get("prewrite_package"))),
        backlog_result=_backlog_result_from_payload(_mapping(payload.get("backlog_result"))),
        quality_manifest=_mapping(payload.get("quality_manifest")),
        compiler_provenance=_mapping(payload.get("compiler_provenance")),
        transaction_hash=str(payload.get("transaction_hash", "")).strip(),
    )
    require_product_create_transaction_verified(transaction)
    return transaction


def product_create_transaction_hash(transaction: ProductCreateTransaction) -> str:
    payload = _transaction_hash_payload(transaction)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _transaction_hash_payload(transaction: ProductCreateTransaction) -> dict[str, Any]:
    return {
        "version": transaction.version,
        "release_selector": transaction.release_selector,
        "proposal": _json_ready(transaction.proposal),
        "validation_gate": _json_ready(transaction.validation_gate),
        "prewrite_package": _json_ready(transaction.prewrite_package),
        "backlog_result": _json_ready(transaction.backlog_result),
        "quality_manifest": _json_ready(transaction.quality_manifest),
        "compiler_provenance": _json_ready(transaction.compiler_provenance),
    }


def _json_ready(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_ready({field.name: getattr(value, field.name) for field in fields(value)})
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key in sorted(value, key=lambda item: str(item)):
            key_text = str(key)
            if key_text in _VOLATILE_HASH_KEYS:
                continue
            result[key_text] = _json_ready(value[key])
        return result
    if isinstance(value, set):
        return sorted(_json_ready(item) for item in value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_ready(item) for item in value]
    if hasattr(value, "as_dict") and callable(value.as_dict):
        return _json_ready(value.as_dict())
    if hasattr(value, "__dict__") and value.__class__.__module__.startswith("odylith."):
        return _json_ready(vars(value))
    return value


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _backlog_result_from_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    result = dict(payload)
    candidate_specs = result.get("_candidate_idea_specs")
    if isinstance(candidate_specs, Mapping):
        result["_candidate_idea_specs"] = {
            str(idea_id): _idea_spec_from_payload(spec)
            for idea_id, spec in candidate_specs.items()
            if isinstance(spec, Mapping)
        }
    return result


def _idea_spec_from_payload(payload: Mapping[str, Any]) -> backlog_contract.IdeaSpec:
    return backlog_contract.IdeaSpec(
        path=Path(str(payload.get("path", ""))),
        metadata={str(key): str(value) for key, value in _mapping(payload.get("metadata")).items()},
        sections={str(value) for value in _sequence(payload.get("sections"))},
        section_bodies={str(key): str(value) for key, value in _mapping(payload.get("section_bodies")).items()},
    )


def _sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else ()


def _completion_package_from_payload(payload: Mapping[str, Any]) -> GreenfieldCompletionPackage:
    allowed = {field.name for field in fields(GreenfieldCompletionPackage)}
    kwargs = {key: payload[key] for key in allowed if key in payload}
    for tuple_key in ("component_registry_preview", "atlas_diagram_ids", "release_workstream_ids"):
        if tuple_key in kwargs and isinstance(kwargs[tuple_key], list):
            kwargs[tuple_key] = tuple(kwargs[tuple_key])
    if isinstance(kwargs.get("traceability_plan"), Mapping):
        kwargs["traceability_plan"] = greenfield_traceability.traceability_plan_from_payload(
            kwargs["traceability_plan"]
        )
    return GreenfieldCompletionPackage(**kwargs)


__all__ = [
    "PRODUCT_CREATE_TRANSACTION_VERSION",
    "PRODUCT_CREATE_TRANSACTION_COMPILER",
    "ProductCreateTransaction",
    "build_product_create_transaction",
    "build_product_create_transaction_provenance",
    "product_create_transaction_from_dict",
    "product_create_transaction_hash",
    "product_create_transaction_repo_fingerprint",
    "product_create_transaction_to_dict",
    "require_product_create_transaction_compiler_provenance",
    "require_product_create_transaction_verified",
]
