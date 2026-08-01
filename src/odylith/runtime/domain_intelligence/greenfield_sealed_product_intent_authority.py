"""Shared parser-free Product Intent authority contract and sealed-byte checks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import hmac
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    require_supported_greenfield_operating_envelope,
)


PRODUCT_INTENT_AUTHORITY_KEY = "product_intent_authority"
PRODUCT_INTENT_AUTHORITY_VERSION = "odylith.product-intent-authority.v3"
PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION = "odylith.product-intent-envelope.v3"
PRODUCT_INTENT_LEDGER_VERSION = "odylith.product-intent-custody-ledger.v2"
MATERIAL_FACT_KEYS = (
    "product_story",
    "state_object",
    "first_path",
    "proof_boundary",
    "human_actors",
)
TYPED_SOURCE_FORMATS = frozenset(
    {
        "compiled_proposal_intent",
        "in_memory_confirmed_intent",
        "legacy_json",
        "typed_envelope_json",
    }
)
# Compatibility export for callers that still use the older name. Raw operator
# prompts are evidence, never structured product truth.
STRUCTURED_SOURCE_FORMATS = TYPED_SOURCE_FORMATS


def require_sealed_product_intent_authority_bytes(
    authority: Mapping[str, Any],
    *,
    authority_bytes: bytes,
    preconfirm_provenance_bytes: bytes,
) -> None:
    """Verify the compiler-sealed authority without parsing or normalizing source evidence."""

    if not isinstance(authority, Mapping):
        raise ValueError("ProductCreateTransaction is missing sealed Product Intent authority")
    canonical_authority_bytes = _canonical_json_bytes(authority)
    if not hmac.compare_digest(authority_bytes, canonical_authority_bytes):
        raise ValueError("ProductCreateTransaction sealed Product Intent authority bytes are not canonical")
    if not hmac.compare_digest(authority_bytes, preconfirm_provenance_bytes):
        raise ValueError(
            "ProductCreateTransaction sealed Product Intent authority does not match its pre-confirm provenance bytes"
        )

    require_product_intent_authority_structure(authority)


def require_product_intent_authority_structure(authority: Mapping[str, Any]) -> None:
    """Verify canonical Product Intent authority fields without inspecting source prose."""

    if not isinstance(authority, Mapping):
        raise ValueError("ProductCreateTransaction sealed Product Intent authority is malformed")
    _require_exact_authority_fields(authority)
    _require_operating_envelope(authority.get("operating_envelope"))
    material_fields = authority.get("material_fields")
    if not isinstance(material_fields, Mapping):
        raise ValueError("ProductCreateTransaction sealed Product Intent authority is malformed")
    _require_material_custody(authority, material_fields)

    expected_material_custody_sha256 = product_intent_material_custody_hash(material_fields)
    if not _matches_sha256(authority.get("material_custody_sha256"), expected_material_custody_sha256):
        raise ValueError("ProductCreateTransaction sealed Product Intent authority custody hash mismatch")
    expected_snapshot_sha256 = product_intent_authority_snapshot_hash(authority)
    if not _matches_sha256(authority.get("authority_snapshot_sha256"), expected_snapshot_sha256):
        raise ValueError("ProductCreateTransaction sealed Product Intent authority snapshot hash mismatch")


def _require_exact_authority_fields(authority: Mapping[str, Any]) -> None:
    expected = {
        "version": PRODUCT_INTENT_AUTHORITY_VERSION,
        "origin": "verified_typed_envelope",
        "envelope_schema_version": PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION,
        "ledger_version": PRODUCT_INTENT_LEDGER_VERSION,
        "decision": "confirmed_intent_accepted",
        "fact_authority": "product_facts",
        "markdown_authority": "ingest_only",
    }
    if any(authority.get(key) != value for key, value in expected.items()):
        raise ValueError("ProductCreateTransaction sealed Product Intent authority is invalid")
    for key in (
        "structured_intent_path",
        "markdown_source_path",
        "product_facts_sha256",
        "markdown_source_sha256",
        "source_format",
    ):
        if not _is_nonempty_string(authority.get(key)):
            raise ValueError("ProductCreateTransaction sealed Product Intent authority is missing required custody")
    for key in ("product_facts_sha256", "markdown_source_sha256"):
        if not _is_sha256(authority.get(key)):
            raise ValueError("ProductCreateTransaction sealed Product Intent authority custody hash mismatch")
    if authority.get("materiality_status") != "passed":
        raise ValueError("ProductCreateTransaction sealed Product Intent authority did not pass materiality")
    blocked_fields = authority.get("blocked_material_fields")
    if not isinstance(blocked_fields, list) or blocked_fields:
        raise ValueError("ProductCreateTransaction sealed Product Intent authority still has blocked material fields")


def _require_operating_envelope(value: Any) -> None:
    try:
        require_supported_greenfield_operating_envelope(value)
    except ValueError as error:
        raise ValueError(
            "ProductCreateTransaction sealed Product Intent authority has an invalid operating envelope"
        ) from error


def _require_material_custody(authority: Mapping[str, Any], material_fields: Mapping[str, Any]) -> None:
    for key in MATERIAL_FACT_KEYS:
        field = material_fields.get(key)
        if not isinstance(field, Mapping):
            raise ValueError("ProductCreateTransaction sealed Product Intent authority has unresolved material custody")
        state = field.get("custody_state")
        relationship = field.get("entailment_relationship")
        if state not in {"accepted_fact", "bounded_interpretation"}:
            raise ValueError("ProductCreateTransaction sealed Product Intent authority has unresolved material custody")
        if not _is_nonempty_string_sequence(field.get("source_span_ids")):
            raise ValueError("ProductCreateTransaction sealed Product Intent authority is missing material source custody")
        if not _valid_span_refs(field.get("source_span_refs"), field.get("source_span_ids")):
            raise ValueError("ProductCreateTransaction sealed Product Intent authority has invalid material source spans")
        if state == "accepted_fact":
            if relationship not in {"direct_product_claim", "normalized_product_claim"}:
                raise ValueError("ProductCreateTransaction sealed Product Intent authority has invalid fact entailment")
            if not _is_nonempty_string_sequence(field.get("product_claim_span_ids")):
                raise ValueError(
                    "ProductCreateTransaction sealed Product Intent authority is missing material product-claim custody"
                )
        elif relationship != "bounded_interpretation_of":
            raise ValueError("ProductCreateTransaction sealed Product Intent authority has invalid interpretation custody")


def _authority_snapshot_payload(authority: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "version": authority.get("version"),
        "origin": authority.get("origin"),
        "structured_intent_path": authority.get("structured_intent_path"),
        "markdown_source_path": authority.get("markdown_source_path"),
        "envelope_schema_version": authority.get("envelope_schema_version"),
        "ledger_version": authority.get("ledger_version"),
        "decision": authority.get("decision"),
        "fact_authority": authority.get("fact_authority"),
        "markdown_authority": authority.get("markdown_authority"),
        "product_facts_sha256": authority.get("product_facts_sha256"),
        "markdown_source_sha256": authority.get("markdown_source_sha256"),
        "source_format": authority.get("source_format"),
        "materiality_status": authority.get("materiality_status"),
        "blocked_material_fields": authority.get("blocked_material_fields"),
        "clarification_policy": authority.get("clarification_policy"),
        "operating_envelope": authority.get("operating_envelope"),
        "material_fields": authority.get("material_fields"),
        "material_custody_sha256": authority.get("material_custody_sha256"),
    }


def product_intent_authority_snapshot_hash(authority: Mapping[str, Any]) -> str:
    """Return the stable hash over authority fields, excluding the hash itself."""

    return _sha256_json(_authority_snapshot_payload(authority))


def product_intent_material_custody_hash(material_fields: Mapping[str, Any]) -> str:
    """Return the stable hash over the bounded material-custody fields."""

    return _sha256_json({key: material_fields.get(key) for key in MATERIAL_FACT_KEYS})


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _matches_sha256(value: Any, expected: str) -> bool:
    return _is_sha256(value) and hmac.compare_digest(value, expected)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _is_nonempty_string_sequence(value: Any) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray))
        and bool(value)
        and all(_is_nonempty_string(item) for item in value)
    )


def _valid_span_refs(value: Any, span_ids: Any) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)) or not value:
        return False
    expected_ids = list(span_ids) if _is_nonempty_string_sequence(span_ids) else []
    actual_ids: list[str] = []
    for row in value:
        if not isinstance(row, Mapping):
            return False
        span_id = row.get("span_id")
        digest = row.get("text_sha256")
        if not _is_nonempty_string(span_id) or not _is_sha256(digest):
            return False
        actual_ids.append(span_id)
    return actual_ids == expected_ids


__all__ = [
    "MATERIAL_FACT_KEYS",
    "PRODUCT_INTENT_AUTHORITY_KEY",
    "PRODUCT_INTENT_AUTHORITY_VERSION",
    "PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION",
    "PRODUCT_INTENT_LEDGER_VERSION",
    "STRUCTURED_SOURCE_FORMATS",
    "TYPED_SOURCE_FORMATS",
    "product_intent_authority_snapshot_hash",
    "product_intent_material_custody_hash",
    "require_product_intent_authority_structure",
    "require_sealed_product_intent_authority_bytes",
]
