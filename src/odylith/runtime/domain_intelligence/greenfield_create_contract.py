"""Shared wire-contract constants for Greenfield create transactions."""

from __future__ import annotations


PRODUCT_CREATE_TRANSACTION_VERSION = "odylith.greenfield.product_create_transaction.v1"
PRODUCT_CREATE_TRANSACTION_COMPILER = "odylith.greenfield.compile_transaction.v1"
PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION = "odylith.greenfield.compiler_identity.v3"
PRODUCT_CREATE_TRANSACTION_COMMIT_POLICY = "compiler_receipt_hash_verified_commit_only"
PRODUCT_CREATE_TRANSACTION_RECEIPT_VERSION = "odylith.greenfield.compiler_receipt.v1"


__all__ = [
    "PRODUCT_CREATE_TRANSACTION_COMMIT_POLICY",
    "PRODUCT_CREATE_TRANSACTION_COMPILER",
    "PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION",
    "PRODUCT_CREATE_TRANSACTION_RECEIPT_VERSION",
    "PRODUCT_CREATE_TRANSACTION_VERSION",
]
