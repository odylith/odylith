"""Shared wire-contract constants for Greenfield create transactions."""

from __future__ import annotations


PRODUCT_CREATE_TRANSACTION_VERSION = "odylith.greenfield.product_create_transaction.v1"
PRODUCT_CREATE_TRANSACTION_COMPILER = "odylith.greenfield.compile_transaction.v1"
PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION = "odylith.greenfield.compiler_identity.v4"
PRODUCT_CREATE_TRANSACTION_COMMIT_POLICY = "compiler_receipt_hash_verified_commit_only"
PRODUCT_CREATE_TRANSACTION_RECEIPT_VERSION = "odylith.greenfield.compiler_receipt.v1"
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


__all__ = [
    "PRODUCT_CREATE_TRANSACTION_COMMIT_POLICY",
    "PRODUCT_CREATE_TRANSACTION_COMPILER",
    "PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION",
    "PRODUCT_CREATE_TRANSACTION_RECEIPT_VERSION",
    "PRODUCT_CREATE_TRANSACTION_VERSION",
    "POST_CONFIRM_ALLOWED_OPERATIONS",
    "POST_CONFIRM_FORBIDDEN_OPERATIONS",
]
