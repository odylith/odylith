"""Parser-free v28 source-meaning authority and sealed-byte checks."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import hmac
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    require_supported_greenfield_operating_envelope,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION,
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_IR_VERSION,
    SEMANTIC_INTENT_PACKET_VERSION,
    require_semantic_intent_ir,
    semantic_evidence_sha256,
    semantic_intent_meaning_sha256,
    semantic_intent_product_facts_sha256,
    semantic_intent_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    resolved_semantic_source_refs,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_meaning import (
    compile_semantic_source_meaning,
    require_semantic_source_meaning_graph,
    semantic_source_meaning_sha256,
)


PRODUCT_INTENT_AUTHORITY_KEY = "product_intent_authority"
PRODUCT_INTENT_AUTHORITY_VERSION = "odylith.product-intent-authority.v40"
_SEMANTIC_AUTHORITY_FIELDS = frozenset(
    {
        "version", "origin", "decision", "fact_authority", "markdown_authority",
        "product_facts_sha256", "source_format", "materiality_status",
        "operating_envelope",
        "semantic_intent_packet_version", "semantic_intent_ir_version",
        "semantic_intent_authoring_request_version",
        "semantic_intent_authoring_contract_sha256",
        "semantic_source_meaning_graph", "semantic_source_meaning_sha256",
        "semantic_intent_author_run", "evidence_sources", "evidence_sha256",
        "accepted_evidence_sha256", "semantic_intent", "semantic_intent_sha256",
        "semantic_meaning_sha256", "semantic_source_refs",
        "authority_snapshot_sha256",
    }
)


def require_sealed_product_intent_authority_bytes(
    authority: Mapping[str, Any],
    *,
    authority_bytes: bytes,
    preconfirm_provenance_bytes: bytes,
) -> None:
    """Verify compiler-sealed authority bytes without inspecting prose meaning."""

    if not isinstance(authority, Mapping):
        raise ValueError("ProductCreateTransaction is missing sealed Product Intent authority")
    canonical = _canonical_json_bytes(authority)
    if not hmac.compare_digest(authority_bytes, canonical):
        raise ValueError("sealed Product Intent authority bytes are not canonical")
    if not hmac.compare_digest(authority_bytes, preconfirm_provenance_bytes):
        raise ValueError("sealed Product Intent authority differs from pre-confirm provenance")
    require_product_intent_authority_structure(authority)


def require_product_intent_authority_structure(authority: Mapping[str, Any]) -> None:
    """Verify the sole supported source-meaning authority."""

    if not isinstance(authority, Mapping):
        raise ValueError("ProductCreateTransaction sealed Product Intent authority is malformed")
    if authority.get("version") != PRODUCT_INTENT_AUTHORITY_VERSION:
        raise ValueError(
            "ProductCreateTransaction sealed Product Intent authority uses an unsupported version; "
            "rebuild the proposal before confirmation"
        )
    if set(authority) != _SEMANTIC_AUTHORITY_FIELDS:
        raise ValueError("ProductCreateTransaction sealed Semantic Intent authority is malformed")
    expected = {
        "version": PRODUCT_INTENT_AUTHORITY_VERSION,
        "origin": "verified_semantic_intent_packet",
        "decision": "confirmed_intent_accepted",
        "fact_authority": "semantic_source_meaning_graph",
        "markdown_authority": "ingest_only",
        "source_format": "semantic_intent_packet",
        "materiality_status": "passed",
        "semantic_intent_packet_version": SEMANTIC_INTENT_PACKET_VERSION,
        "semantic_intent_ir_version": SEMANTIC_INTENT_IR_VERSION,
        "semantic_intent_authoring_request_version": (
            SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION
        ),
        "semantic_intent_authoring_contract_sha256": (
            semantic_intent_authoring_contract_sha256()
        ),
    }
    if any(authority.get(key) != value for key, value in expected.items()):
        raise ValueError("ProductCreateTransaction sealed Semantic Intent authority is invalid")
    evidence_sources = authority.get("evidence_sources")
    if not isinstance(evidence_sources, Mapping) or set(evidence_sources) != {
        "operator_prompt", "operator_edit",
    }:
        raise ValueError("sealed Semantic Intent evidence is malformed")
    prompt = evidence_sources.get("operator_prompt")
    edit = evidence_sources.get("operator_edit")
    if not isinstance(prompt, str) or not prompt or not isinstance(edit, str):
        raise ValueError("sealed Semantic Intent evidence is malformed")
    if not _is_sha256(authority.get("evidence_sha256")):
        raise ValueError("sealed Semantic Intent source hash is malformed")
    if not _matches_sha256(
        authority.get("accepted_evidence_sha256"),
        semantic_evidence_sha256(evidence_sources),
    ):
        raise ValueError("sealed accepted Semantic Intent evidence hash mismatch")
    graph = require_semantic_source_meaning_graph(
        authority.get("semantic_source_meaning_graph"),
        evidence_sources=evidence_sources,
    )
    graph_sha256 = semantic_source_meaning_sha256(graph)
    if not _matches_sha256(
        authority.get("semantic_source_meaning_sha256"), graph_sha256
    ):
        raise ValueError("sealed source-meaning graph hash mismatch")
    from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
        require_semantic_source_meaning_author_run,
    )

    run = require_semantic_source_meaning_author_run(
        authority.get("semantic_intent_author_run"), graph_sha256=graph_sha256
    )
    if authority.get("semantic_intent_author_run") != run:
        raise ValueError("sealed source-meaning author run is noncanonical")
    expected_intent = compile_semantic_source_meaning(
        graph, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
    )
    if authority.get("semantic_intent") != expected_intent:
        raise ValueError("sealed Semantic Intent differs from source meaning")
    semantic_intent = require_semantic_intent_ir(
        expected_intent, evidence_sources=evidence_sources
    )
    if semantic_intent.get("status") != "complete":
        raise ValueError("sealed Semantic Intent is clarification-bound")
    hashes = {
        "semantic_intent_sha256": semantic_intent_sha256(semantic_intent),
        "semantic_meaning_sha256": semantic_intent_meaning_sha256(semantic_intent),
        "product_facts_sha256": semantic_intent_product_facts_sha256(semantic_intent),
    }
    for key, expected_hash in hashes.items():
        if not _matches_sha256(authority.get(key), expected_hash):
            raise ValueError(f"sealed Semantic Intent {key} mismatch")
    expected_refs = resolved_semantic_source_refs(
        {"source_meaning_graph": graph, "semantic_intent": semantic_intent},
        evidence_sources=evidence_sources,
    )
    if authority.get("semantic_source_refs") != expected_refs:
        raise ValueError("sealed Semantic Intent source custody mismatch")
    _require_operating_envelope(authority.get("operating_envelope"))
    if not _matches_sha256(
        authority.get("authority_snapshot_sha256"),
        product_intent_authority_snapshot_hash(authority),
    ):
        raise ValueError("sealed Product Intent authority snapshot hash mismatch")


def _require_operating_envelope(value: Any) -> None:
    try:
        require_supported_greenfield_operating_envelope(value)
    except ValueError as error:
        raise ValueError("sealed Product Intent authority has an invalid operating envelope") from error


def product_intent_authority_snapshot_hash(authority: Mapping[str, Any]) -> str:
    """Hash every authority field except the hash itself."""

    payload = {
        key: authority.get(key)
        for key in sorted(_SEMANTIC_AUTHORITY_FIELDS - {"authority_snapshot_sha256"})
    }
    return _sha256_json(payload)


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("ascii")


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


__all__ = [
    "PRODUCT_INTENT_AUTHORITY_KEY",
    "PRODUCT_INTENT_AUTHORITY_VERSION",
    "product_intent_authority_snapshot_hash",
    "require_product_intent_authority_structure",
    "require_sealed_product_intent_authority_bytes",
]
