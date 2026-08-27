"""Shared wire-contract constants for Greenfield create transactions."""

from __future__ import annotations

PRODUCT_CREATE_TRANSACTION_VERSION = "odylith.greenfield.product_create_transaction.v2"
PRODUCT_CREATE_TRANSACTION_COMPILER = "odylith.greenfield.compile_transaction.v2"
PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION = "odylith.greenfield.compiler_identity.v33"
PRODUCT_CREATE_TRANSACTION_COMMIT_POLICY = "compiler_receipt_hash_verified_commit_only"
PRODUCT_CREATE_TRANSACTION_RECEIPT_VERSION = "odylith.greenfield.compiler_receipt.v1"
PRODUCT_CREATE_TRANSACTION_ACCEPTED_INTENT_AUTHORITY_VERSION = "odylith.product-intent-authority.v40"
PRODUCT_CREATE_TRANSACTION_FIELDS = (
    "version",
    "release_selector",
    "validation_gate",
    "prewrite_package",
    "intent_authority",
    "quality_manifest",
    "compiler_provenance",
    "commit_summary",
    "transaction_hash",
)
POST_CONFIRM_ALLOWED_OPERATIONS = (
    "verify_transaction_hash",
    "verify_compiler_receipt",
    "verify_post_confirm_runtime_identity",
    "verify_sealed_write_set",
    "verify_repo_preconditions",
    "apply_preconfirm_refreshed_sealed_bytes",
    "write_sealed_repository_bytes",
    "validate_readback",
    "report_success",
)
POST_CONFIRM_FORBIDDEN_OPERATIONS = (
    "product_interpretation",
    "artifact_generation",
    "semantic_repair",
    "markdown_parsing",
    "host_model_work",
    "quality_repair",
    "live_post_confirm_refresh",
)


def is_sha256_digest(value: object) -> bool:
    """Return whether ``value`` is one canonical lowercase SHA-256 token."""

    token = str(value or "").strip()
    return len(token) == 64 and all(character in "0123456789abcdef" for character in token)


__all__ = [
    "PRODUCT_CREATE_TRANSACTION_COMMIT_POLICY",
    "PRODUCT_CREATE_TRANSACTION_COMPILER",
    "PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION",
    "PRODUCT_CREATE_TRANSACTION_FIELDS",
    "PRODUCT_CREATE_TRANSACTION_RECEIPT_VERSION",
    "PRODUCT_CREATE_TRANSACTION_ACCEPTED_INTENT_AUTHORITY_VERSION",
    "PRODUCT_CREATE_TRANSACTION_VERSION",
    "POST_CONFIRM_ALLOWED_OPERATIONS",
    "POST_CONFIRM_FORBIDDEN_OPERATIONS",
    "is_sha256_digest",
]
