"""Host-authored, deterministically verified Greenfield Semantic Intent packets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_IR_VERSION,
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
    resolve_semantic_source_ref,
    resolved_semantic_source_refs,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
    ATOMIC_SOURCE_ADJUDICATION_VERSION,
    atomic_source_adjudication_schema,
    select_atomic_source_claims,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_author_output import (
    require_semantic_graph_author_output,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_extension import (
    assemble_semantic_intent_from_extension,
    bind_semantic_graph_extension_source_refs,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_claims import (
    SEMANTIC_SOURCE_CLAIMS_VERSION,
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
    source_candidate_adjudication: Mapping[str, Any]
    source_claims: Mapping[str, Any]
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
            "source_candidate_adjudication",
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
            "source_candidate_adjudication": (
                atomic_source_adjudication_schema()
            ),
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
        "source_candidate_adjudication",
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
    source_candidates = materiality_assessment["source_candidates"]
    settled_fields = {
        str(row["field"]): row for row in materiality_assessment["fields"]
    }
    source_candidate_adjudication, source_claims = select_atomic_source_claims(
        source_candidates,
        value.get("source_candidate_adjudication"),
        evidence_sources=evidence_sources,
        settled_fields=settled_fields,
    )
    semantic_intent = require_semantic_intent_ir(
        value.get("semantic_intent"),
        evidence_sources=evidence_sources,
        source_claims=source_claims,
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
        source_candidate_adjudication=source_candidate_adjudication,
        source_claims=source_claims,
        critic_run=critic_run,
        author_run=author_run,
        evidence_sha256=evidence_sha256,
        semantic_intent_sha256=semantic_intent_sha256(semantic_intent),
        semantic_meaning_sha256=semantic_intent_meaning_sha256(semantic_intent),
    )


def build_semantic_intent_packet(
    materiality_assessment_value: Any,
    graph_author_output_value: Any,
    *,
    prompt: str,
    critic_run_id: str,
    author_run_id: str,
    critic_host_profile: str,
    edit_evidence: str = "",
) -> dict[str, Any]:
    """Assemble and verify one production packet from the two typed host outputs."""

    evidence_sources = {
        "operator_prompt": str(prompt or ""),
        "operator_edit": str(edit_evidence or ""),
    }
    evidence_sha256 = semantic_evidence_sha256(evidence_sources)
    contract_sha256 = semantic_intent_authoring_contract_sha256()
    assessment = require_semantic_materiality_assessment(
        materiality_assessment_value,
        evidence_sources=evidence_sources,
        evidence_sha256=evidence_sha256,
        authoring_contract_sha256=contract_sha256,
    )
    author_output = require_semantic_graph_author_output(graph_author_output_value)
    settled_fields = {str(row["field"]): row for row in assessment["fields"]}
    adjudication, source_claims = select_atomic_source_claims(
        assessment["source_candidates"],
        author_output["source_candidate_adjudication"],
        evidence_sources=evidence_sources,
        settled_fields=settled_fields,
    )
    extension = bind_semantic_graph_extension_source_refs(
        author_output["semantic_extension"],
        assessment=assessment,
        evidence_sources=evidence_sources,
    )
    semantic_intent = assemble_semantic_intent_from_extension(
        extension,
        assessment=assessment,
        source_claims=source_claims,
    )
    packet = {
        "version": SEMANTIC_INTENT_PACKET_VERSION,
        "evidence_sha256": evidence_sha256,
        "authoring_contract_sha256": contract_sha256,
        "materiality_assessment": assessment,
        "materiality_assessment_sha256": semantic_materiality_assessment_sha256(
            assessment
        ),
        "source_candidate_adjudication": adjudication,
        "critic_run": {
            "capability_profile": "frontier_semantic_reasoning",
            "critic_run_id": str(critic_run_id),
            "host_profile": str(critic_host_profile),
            "independent_context": True,
        },
        "author_run": {
            "capability_profile": "frontier_semantic_reasoning",
            "author_run_id": str(author_run_id),
        },
        "semantic_intent": semantic_intent,
    }
    require_semantic_intent_packet(
        packet,
        prompt=prompt,
        edit_evidence=edit_evidence,
    )
    return packet


def build_semantic_clarification_packet(
    materiality_assessment_value: Any,
    *,
    prompt: str,
    critic_run_id: str,
    author_run_id: str,
    critic_host_profile: str,
    edit_evidence: str = "",
) -> dict[str, Any]:
    """Seal one independently challenged material question without graph claims."""

    evidence_sources = {
        "operator_prompt": str(prompt or ""),
        "operator_edit": str(edit_evidence or ""),
    }
    evidence_sha256 = semantic_evidence_sha256(evidence_sources)
    contract_sha256 = semantic_intent_authoring_contract_sha256()
    assessment = require_semantic_materiality_assessment(
        materiality_assessment_value,
        evidence_sources=evidence_sources,
        evidence_sha256=evidence_sha256,
        authoring_contract_sha256=contract_sha256,
    )
    if assessment["decision"] != "clarification_required":
        raise ValueError("clarification packet requires one material question")
    clarification = assessment["clarification"]
    packet = {
        "version": SEMANTIC_INTENT_PACKET_VERSION,
        "evidence_sha256": evidence_sha256,
        "authoring_contract_sha256": contract_sha256,
        "materiality_assessment": assessment,
        "materiality_assessment_sha256": semantic_materiality_assessment_sha256(
            assessment
        ),
        "source_candidate_adjudication": {
            "version": ATOMIC_SOURCE_ADJUDICATION_VERSION,
            "candidate_decisions": [
                {
                    "candidate_id": row["candidate_id"],
                    "decision": "reject_noise",
                    "fact_ids": [],
                    "relation_ids": [],
                }
                for row in assessment["source_candidates"]["candidates"]
            ],
            "source_claims": {
                "version": SEMANTIC_SOURCE_CLAIMS_VERSION,
                "facts": [],
                "relations": [],
            },
        },
        "critic_run": {
            "capability_profile": "frontier_semantic_reasoning",
            "critic_run_id": str(critic_run_id),
            "host_profile": str(critic_host_profile),
            "independent_context": True,
        },
        "author_run": {
            "capability_profile": "frontier_semantic_reasoning",
            "author_run_id": str(author_run_id),
        },
        "semantic_intent": {
            "version": SEMANTIC_INTENT_IR_VERSION,
            "status": "clarification_required",
            "clarification": {
                "question": clarification["question"],
                "fields": [clarification["field"]],
                "source_refs": list(clarification["source_refs"]),
            },
            "facts": [],
            "relations": [],
            "narratives": [],
        },
    }
    require_semantic_intent_packet(
        packet,
        prompt=prompt,
        edit_evidence=edit_evidence,
    )
    return packet


def semantic_intent_authority(
    verified: VerifiedSemanticIntentPacket,
    *,
    prompt: str,
    edit_evidence: str = "",
) -> dict[str, Any]:
    """Seal one verified graph as the sole Product Intent authority."""

    source_evidence = {
        "operator_prompt": str(prompt or ""),
        "operator_edit": str(edit_evidence or ""),
    }
    if semantic_evidence_sha256(source_evidence) != verified.evidence_sha256:
        raise ValueError("Greenfield Semantic Intent authority does not match the supplied evidence")
    if verified.semantic_intent.get("status") != "complete" or verified.product_facts is None:
        raise ValueError("clarification-bound Semantic Intent cannot be sealed as product authority")
    from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
        PRODUCT_INTENT_AUTHORITY_VERSION,
        product_intent_authority_snapshot_hash,
        require_product_intent_authority_structure,
    )

    evidence_sources = accepted_semantic_evidence_sources(
        verified,
        source_evidence=source_evidence,
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
            source_size_bytes=sum(len(value.encode("utf-8")) for value in source_evidence.values()),
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
        "semantic_source_candidate_adjudication": dict(
            verified.source_candidate_adjudication
        ),
        "semantic_materiality_critic_run": dict(verified.critic_run),
        "semantic_intent_author_run": dict(verified.author_run),
        "evidence_sources": evidence_sources,
        "evidence_sha256": verified.evidence_sha256,
        "accepted_evidence_sha256": semantic_evidence_sha256(evidence_sources),
        "semantic_intent": dict(verified.semantic_intent),
        "semantic_intent_sha256": verified.semantic_intent_sha256,
        "semantic_meaning_sha256": verified.semantic_meaning_sha256,
        "semantic_source_refs": [
            dict(row)
            for row in resolved_semantic_source_refs(
                verified.semantic_intent,
                evidence_sources=evidence_sources,
            )
        ],
    }
    authority["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(authority)
    require_product_intent_authority_structure(authority)
    return authority


def accepted_semantic_evidence_sources(
    verified: VerifiedSemanticIntentPacket,
    *,
    source_evidence: Mapping[str, str],
) -> dict[str, str]:
    refs = _source_ref_rows(
        {
            "assessment": verified.materiality_assessment,
            "source_adjudication": verified.source_candidate_adjudication,
            "semantic_intent": verified.semantic_intent,
        }
    )
    by_source: dict[str, dict[str, int]] = {
        "operator_prompt": {},
        "operator_edit": {},
    }
    positions: dict[tuple[str, str], int] = {}
    for ref in refs:
        resolved = resolve_semantic_source_ref(ref, evidence_sources=source_evidence)
        source_id = str(resolved["source_id"])
        quote = str(ref["quote"])
        occurrence = int(ref["occurrence"])
        by_source[source_id][quote] = max(by_source[source_id].get(quote, 0), occurrence)
        positions[(source_id, quote)] = min(
            positions.get((source_id, quote), int(resolved["char_start"])),
            int(resolved["char_start"]),
        )
    accepted = {
        source_id: "\n".join(
            quote
            for quote, occurrence in sorted(
                quotes.items(), key=lambda item: positions[(source_id, item[0])]
            )
            for _ in range(occurrence)
        )
        for source_id, quotes in by_source.items()
    }
    for ref in refs:
        resolve_semantic_source_ref(ref, evidence_sources=accepted)
    if not accepted["operator_prompt"]:
        raise ValueError("Greenfield Semantic Intent authority has no accepted prompt evidence")
    return accepted


def _source_ref_rows(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if isinstance(value, Mapping):
        if (
            isinstance(value.get("source_id"), str)
            and isinstance(value.get("quote"), str)
            and isinstance(value.get("occurrence"), int)
        ):
            result.append(
                {
                    "source_id": value["source_id"],
                    "quote": value["quote"],
                    "occurrence": value["occurrence"],
                }
            )
        else:
            for nested in value.values():
                result.extend(_source_ref_rows(nested))
    elif isinstance(value, list):
        for nested in value:
            result.extend(_source_ref_rows(nested))
    unique: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in result:
        unique[(row["source_id"], row["quote"], row["occurrence"])] = row
    return list(unique.values())


__all__ = [
    "MAX_SEMANTIC_INTENT_PACKET_BYTES",
    "SEMANTIC_INTENT_PACKET_VERSION",
    "VerifiedSemanticIntentPacket",
    "accepted_semantic_evidence_sources",
    "build_semantic_clarification_packet",
    "build_semantic_intent_packet",
    "load_semantic_intent_packet",
    "require_semantic_intent_packet",
    "semantic_intent_authority",
    "semantic_evidence_sha256",
    "semantic_intent_packet_schema",
]
