"""Precompiled create transactions for confirmed greenfield writes."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import is_dataclass
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage


PRODUCT_CREATE_TRANSACTION_VERSION = "odylith.greenfield.product_create_transaction.v1"
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
        }


def build_product_create_transaction(
    *,
    proposal: Mapping[str, Any],
    release_selector: str,
    validation_gate: Mapping[str, Any],
    prewrite_package: GreenfieldCompletionPackage,
    backlog_result: Mapping[str, Any],
    quality_manifest: Mapping[str, Any],
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
    }


def _json_ready(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_ready(asdict(value))
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


__all__ = [
    "PRODUCT_CREATE_TRANSACTION_VERSION",
    "ProductCreateTransaction",
    "build_product_create_transaction",
    "product_create_transaction_hash",
    "require_product_create_transaction_verified",
]
