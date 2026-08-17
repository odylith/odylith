"""Pinned host execution profiles and measured runtime receipts for Greenfield."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


HOST_RUNTIME_RECEIPT_VERSION = "odylith.greenfield.host-runtime-receipt.v1"
TOKEN_MEASUREMENT_BASES = ("provider_usage_receipt", "host_runtime_usage_receipt")


def require_host_runtime_receipt(value: Any, *, host_profile: str) -> dict[str, Any]:
    """Validate the exact executable identity observed for one model call."""

    if not isinstance(value, Mapping):
        raise RuntimeError("host runtime receipt must be a JSON object")
    row = dict(value)
    expected_keys = {
        "version",
        "host_profile",
        "runtime_name",
        "runtime_version",
        "runtime_binary_sha256",
    }
    if set(row) != expected_keys:
        raise RuntimeError("host runtime receipt fields do not match the versioned contract")
    if row.get("version") != HOST_RUNTIME_RECEIPT_VERSION:
        raise RuntimeError("host runtime receipt uses an unsupported version")
    if row.get("host_profile") != host_profile:
        raise RuntimeError("host runtime receipt does not match its assigned host")
    expected_runtime = {"codex": "codex-cli", "claude": "claude-code"}[host_profile]
    if row.get("runtime_name") != expected_runtime:
        raise RuntimeError("host runtime receipt names the wrong executable family")
    runtime_version = _bounded_text(row.get("runtime_version"), "host runtime version", 200)
    runtime_sha256 = _sha256(row.get("runtime_binary_sha256"), "host runtime binary")
    return {
        "version": HOST_RUNTIME_RECEIPT_VERSION,
        "host_profile": host_profile,
        "runtime_name": expected_runtime,
        "runtime_version": runtime_version,
        "runtime_binary_sha256": runtime_sha256,
    }


def require_token_usage(value: Any, *, stage: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{stage} token usage must be a JSON object")
    row = dict(value)
    expected = {"input_tokens", "output_tokens", "total_tokens", "measurement_basis"}
    if set(row) != expected:
        raise RuntimeError(f"{stage} token usage fields do not match the versioned contract")
    input_tokens = positive_integer(row.get("input_tokens"), f"{stage} input tokens")
    output_tokens = positive_integer(row.get("output_tokens"), f"{stage} output tokens")
    total_tokens = positive_integer(row.get("total_tokens"), f"{stage} total tokens")
    if total_tokens != input_tokens + output_tokens:
        raise RuntimeError(f"{stage} token total does not match its measured parts")
    basis = row.get("measurement_basis")
    if basis not in TOKEN_MEASUREMENT_BASES:
        raise RuntimeError(f"{stage} token measurement basis is unsupported")
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "measurement_basis": basis,
    }


def positive_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RuntimeError(f"{label} must be a positive integer")
    return value


def _bounded_text(value: Any, label: str, maximum: int) -> str:
    result = str(value or "").strip()
    if not result or len(result) > maximum:
        raise RuntimeError(f"{label} must be bounded non-empty text")
    return result


def _sha256(value: Any, label: str) -> str:
    result = _bounded_text(value, label, 64)
    if len(result) != 64 or any(character not in "0123456789abcdef" for character in result):
        raise RuntimeError(f"{label} must be a lowercase SHA-256 digest")
    return result


__all__ = [
    "HOST_RUNTIME_RECEIPT_VERSION",
    "TOKEN_MEASUREMENT_BASES",
    "positive_integer",
    "require_host_runtime_receipt",
    "require_token_usage",
]
