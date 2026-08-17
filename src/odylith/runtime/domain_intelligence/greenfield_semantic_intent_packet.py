"""Host-authored, deterministically verified Greenfield Semantic Intent packets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_PACKET_VERSION,
    require_semantic_intent_ir,
    semantic_evidence_sha256,
    semantic_intent_meaning_sha256,
    semantic_intent_product_facts,
    semantic_intent_product_facts_sha256,
    semantic_intent_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_schema import (
    semantic_intent_output_schema,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    greenfield_operating_envelope_receipt,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION,
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    require_materiality_intent_alignment,
    require_semantic_materiality_assessment,
    require_semantic_reasoning_runs,
    semantic_intent_author_schema,
    semantic_materiality_assessment_schema,
    semantic_materiality_assessment_sha256,
    semantic_materiality_critic_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    resolved_semantic_source_refs,
)


MAX_SEMANTIC_INTENT_PACKET_BYTES = 1_000_000


@dataclass(frozen=True)
class VerifiedSemanticIntentPacket:
    """Validated prompt-only decision and host interpretation."""

    semantic_intent: Mapping[str, Any]
    product_facts: Mapping[str, Any] | None
    resolved_source_refs: tuple[Mapping[str, Any], ...]
    materiality_assessment: Mapping[str, Any]
    materiality_assessment_sha256: str
    critic_run: Mapping[str, Any]
    author_run: Mapping[str, Any]
    evidence_sha256: str
    semantic_intent_sha256: str
    semantic_meaning_sha256: str


def semantic_intent_packet_schema() -> dict[str, Any]:
    """Return the public host-to-Odylith packet schema."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "version",
            "evidence_sha256",
            "authoring_contract_sha256",
            "materiality_assessment",
            "materiality_assessment_sha256",
            "critic_run",
            "author_run",
            "semantic_intent",
        ],
        "properties": {
            "version": {"type": "string", "enum": [SEMANTIC_INTENT_PACKET_VERSION]},
            "evidence_sha256": {"type": "string", "minLength": 64, "maxLength": 64},
            "authoring_contract_sha256": {
                "type": "string",
                "minLength": 64,
                "maxLength": 64,
            },
            "materiality_assessment": semantic_materiality_assessment_schema(),
            "materiality_assessment_sha256": {
                "type": "string",
                "minLength": 64,
                "maxLength": 64,
            },
            "critic_run": semantic_materiality_critic_schema(),
            "author_run": semantic_intent_author_schema(),
            "semantic_intent": semantic_intent_output_schema(),
        },
    }


def load_semantic_intent_packet(
    path: Path | str,
    *,
    prompt: str,
    edit_evidence: str = "",
) -> VerifiedSemanticIntentPacket:
    """Read and verify an explicit host packet; never infer from its prose."""

    packet_path = Path(path).expanduser().resolve()
    try:
        if packet_path.stat().st_size > MAX_SEMANTIC_INTENT_PACKET_BYTES:
            raise ValueError("Greenfield Semantic Intent packet exceeds its operating limit")
        raw = json.loads(packet_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError("environment/IO failure while reading Semantic Intent packet") from exc
    return require_semantic_intent_packet(
        raw,
        prompt=prompt,
        edit_evidence=edit_evidence,
    )


def require_semantic_intent_packet(
    value: Any,
    *,
    prompt: str,
    edit_evidence: str = "",
) -> VerifiedSemanticIntentPacket:
    """Verify packet bytes, citations, graph integrity, and product projection."""

    if not isinstance(value, Mapping) or set(value) != {
        "version",
        "evidence_sha256",
        "authoring_contract_sha256",
        "materiality_assessment",
        "materiality_assessment_sha256",
        "critic_run",
        "author_run",
        "semantic_intent",
    }:
        raise ValueError("Greenfield Semantic Intent packet is malformed")
    if value.get("version") != SEMANTIC_INTENT_PACKET_VERSION:
        raise ValueError("Greenfield Semantic Intent packet uses an unsupported version")
    evidence_sources = {
        "operator_prompt": str(prompt or ""),
        "operator_edit": str(edit_evidence or ""),
    }
    evidence_sha256 = semantic_evidence_sha256(evidence_sources)
    if value.get("evidence_sha256") != evidence_sha256:
        raise ValueError("Greenfield Semantic Intent packet does not match the supplied evidence")
    authoring_contract_sha256 = semantic_intent_authoring_contract_sha256()
    if value.get("authoring_contract_sha256") != authoring_contract_sha256:
        raise ValueError("Greenfield Semantic Intent packet uses a different authoring contract")
    materiality_assessment = require_semantic_materiality_assessment(
        value.get("materiality_assessment"),
        evidence_sources=evidence_sources,
        evidence_sha256=evidence_sha256,
        authoring_contract_sha256=authoring_contract_sha256,
    )
    materiality_sha256 = semantic_materiality_assessment_sha256(materiality_assessment)
    if value.get("materiality_assessment_sha256") != materiality_sha256:
        raise ValueError("Greenfield Semantic Intent packet materiality hash mismatch")
    critic_run, author_run = require_semantic_reasoning_runs(
        value.get("critic_run"),
        value.get("author_run"),
    )
    semantic_intent = require_semantic_intent_ir(
        value.get("semantic_intent"),
        evidence_sources=evidence_sources,
    )
    require_materiality_intent_alignment(materiality_assessment, semantic_intent)
    product_facts = (
        semantic_intent_product_facts(semantic_intent)
        if semantic_intent.get("status") == "complete"
        else None
    )
    return VerifiedSemanticIntentPacket(
        semantic_intent=semantic_intent,
        product_facts=product_facts,
        resolved_source_refs=tuple(
            resolved_semantic_source_refs(
                semantic_intent,
                evidence_sources=evidence_sources,
            )
        ),
        materiality_assessment=materiality_assessment,
        materiality_assessment_sha256=materiality_sha256,
        critic_run=critic_run,
        author_run=author_run,
        evidence_sha256=evidence_sha256,
        semantic_intent_sha256=semantic_intent_sha256(semantic_intent),
        semantic_meaning_sha256=semantic_intent_meaning_sha256(semantic_intent),
    )


def semantic_intent_authority(
    verified: VerifiedSemanticIntentPacket,
    *,
    prompt: str,
    edit_evidence: str = "",
) -> dict[str, Any]:
    """Seal one verified graph as the sole Product Intent authority."""

    evidence_sources = {
        "operator_prompt": str(prompt or ""),
        "operator_edit": str(edit_evidence or ""),
    }
    if semantic_evidence_sha256(evidence_sources) != verified.evidence_sha256:
        raise ValueError("Greenfield Semantic Intent authority does not match the supplied evidence")
    if verified.semantic_intent.get("status") != "complete" or verified.product_facts is None:
        raise ValueError("clarification-bound Semantic Intent cannot be sealed as product authority")
    from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
        PRODUCT_INTENT_AUTHORITY_VERSION,
        product_intent_authority_snapshot_hash,
        require_product_intent_authority_structure,
    )

    authority = {
        "version": PRODUCT_INTENT_AUTHORITY_VERSION,
        "origin": "verified_semantic_intent_packet",
        "decision": "confirmed_intent_accepted",
        "fact_authority": "semantic_intent",
        "markdown_authority": "ingest_only",
        "product_facts_sha256": semantic_intent_product_facts_sha256(verified.semantic_intent),
        "source_format": "semantic_intent_packet",
        "materiality_status": "passed",
        "blocked_material_fields": [],
        "operating_envelope": greenfield_operating_envelope_receipt(
            facts=verified.product_facts,
            source_format="semantic_intent_packet",
            source_size_bytes=sum(len(value.encode("utf-8")) for value in evidence_sources.values()),
            source_document_count=1 + bool(edit_evidence),
        ),
        "semantic_intent_packet_version": SEMANTIC_INTENT_PACKET_VERSION,
        "semantic_intent_ir_version": str(verified.semantic_intent.get("version") or ""),
        "semantic_intent_authoring_request_version": (
            SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION
        ),
        "semantic_intent_authoring_contract_sha256": (
            semantic_intent_authoring_contract_sha256()
        ),
        "semantic_materiality_assessment": dict(verified.materiality_assessment),
        "semantic_materiality_assessment_sha256": (
            verified.materiality_assessment_sha256
        ),
        "semantic_materiality_critic_run": dict(verified.critic_run),
        "semantic_intent_author_run": dict(verified.author_run),
        "evidence_sources": evidence_sources,
        "evidence_sha256": verified.evidence_sha256,
        "semantic_intent": dict(verified.semantic_intent),
        "semantic_intent_sha256": verified.semantic_intent_sha256,
        "semantic_meaning_sha256": verified.semantic_meaning_sha256,
        "semantic_source_refs": [dict(row) for row in verified.resolved_source_refs],
    }
    authority["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(authority)
    require_product_intent_authority_structure(authority)
    return authority
__all__ = [
    "MAX_SEMANTIC_INTENT_PACKET_BYTES",
    "SEMANTIC_INTENT_PACKET_VERSION",
    "VerifiedSemanticIntentPacket",
    "load_semantic_intent_packet",
    "require_semantic_intent_packet",
    "semantic_intent_authority",
    "semantic_evidence_sha256",
    "semantic_intent_packet_schema",
]
