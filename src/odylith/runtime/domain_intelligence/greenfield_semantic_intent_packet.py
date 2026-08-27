"""Single-author, source-meaning Greenfield intent packets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    greenfield_operating_envelope_receipt,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    SEMANTIC_REASONING_CAPABILITY_PROFILE,
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
    semantic_intent_product_facts,
    semantic_intent_product_facts_sha256,
    semantic_intent_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_schema import (
    semantic_intent_output_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    resolved_semantic_source_refs,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_meaning import (
    SEMANTIC_SOURCE_MEANING_AUTHOR_RUN_VERSION,
    compile_semantic_source_meaning,
    require_semantic_source_meaning_graph,
    semantic_source_meaning_graph_schema,
    semantic_source_meaning_sha256,
)


MAX_SEMANTIC_INTENT_PACKET_BYTES = 1_000_000
_CAPABILITY_PROFILE = SEMANTIC_REASONING_CAPABILITY_PROFILE


@dataclass(frozen=True)
class VerifiedSemanticIntentPacket:
    """Validated one-call source meaning and deterministic projection."""

    semantic_intent: Mapping[str, Any]
    product_facts: Mapping[str, Any] | None
    source_meaning_graph: Mapping[str, Any]
    source_meaning_sha256: str
    resolved_source_refs: tuple[Mapping[str, Any], ...]
    author_run: Mapping[str, Any]
    evidence_sha256: str
    semantic_intent_sha256: str
    semantic_meaning_sha256: str


def semantic_source_meaning_author_run_schema() -> dict[str, Any]:
    """Return the exact single-call receipt sealed into the packet."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "version", "capability_profile", "run_id", "host_profile", "model",
            "reasoning_effort", "budget_seconds", "wall_ms", "usage",
            "graph_sha256", "model_call_count", "restart_count",
        ],
        "properties": {
            "version": {
                "type": "string",
                "enum": [SEMANTIC_SOURCE_MEANING_AUTHOR_RUN_VERSION],
            },
            "capability_profile": {
                "type": "string", "enum": [_CAPABILITY_PROFILE]
            },
            "run_id": {"type": "string", "minLength": 1, "maxLength": 200},
            "host_profile": {"type": "string", "enum": ["codex", "claude"]},
            "model": {"type": "string", "minLength": 1, "maxLength": 100},
            "reasoning_effort": {
                "type": "string", "enum": ["low", "medium", "high"]
            },
            "budget_seconds": {"type": "integer", "minimum": 1, "maximum": 54},
            "wall_ms": {"type": "integer", "minimum": 0, "maximum": 54000},
            "usage": {"type": "object"},
            "graph_sha256": {"type": "string", "minLength": 64, "maxLength": 64},
            "model_call_count": {"type": "integer", "enum": [1]},
            "restart_count": {"type": "integer", "enum": [0]},
        },
    }


def semantic_intent_packet_schema() -> dict[str, Any]:
    """Return the sole public host-to-Odylith packet schema."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "version", "evidence_sha256", "authoring_contract_sha256",
            "source_meaning_graph", "source_meaning_sha256", "author_run",
            "semantic_intent",
        ],
        "properties": {
            "version": {"type": "string", "enum": [SEMANTIC_INTENT_PACKET_VERSION]},
            "evidence_sha256": {"type": "string", "minLength": 64, "maxLength": 64},
            "authoring_contract_sha256": {
                "type": "string", "minLength": 64, "maxLength": 64
            },
            "source_meaning_graph": semantic_source_meaning_graph_schema(),
            "source_meaning_sha256": {
                "type": "string", "minLength": 64, "maxLength": 64
            },
            "author_run": semantic_source_meaning_author_run_schema(),
            "semantic_intent": semantic_intent_output_schema(
                clarification_source_ref_minimum=0
            ),
        },
    }


def load_semantic_intent_packet(
    path: Path | str,
    *,
    prompt: str,
    edit_evidence: str = "",
) -> VerifiedSemanticIntentPacket:
    """Read and verify an explicit packet without interpreting source prose."""

    packet_path = Path(path).expanduser().resolve()
    try:
        if packet_path.stat().st_size > MAX_SEMANTIC_INTENT_PACKET_BYTES:
            raise ValueError("Greenfield Semantic Intent packet exceeds its operating limit")
        raw = json.loads(packet_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RuntimeError(
            "environment/IO failure while reading Semantic Intent packet"
        ) from error
    return require_semantic_intent_packet(
        raw, prompt=prompt, edit_evidence=edit_evidence
    )


def require_semantic_intent_packet(
    value: Any,
    *,
    prompt: str,
    edit_evidence: str = "",
) -> VerifiedSemanticIntentPacket:
    """Verify graph bytes, run custody, citations, and deterministic projection."""

    packet = _mapping(value, "Greenfield Semantic Intent packet")
    expected_keys = {
        "version", "evidence_sha256", "authoring_contract_sha256",
        "source_meaning_graph", "source_meaning_sha256", "author_run",
        "semantic_intent",
    }
    if set(packet) != expected_keys:
        raise ValueError("Greenfield Semantic Intent packet is malformed")
    if packet.get("version") != SEMANTIC_INTENT_PACKET_VERSION:
        raise ValueError("Greenfield Semantic Intent packet uses an unsupported version")
    evidence_sources = {
        "operator_prompt": str(prompt or ""),
        "operator_edit": str(edit_evidence or ""),
    }
    evidence_sha256 = semantic_evidence_sha256(evidence_sources)
    if packet.get("evidence_sha256") != evidence_sha256:
        raise ValueError("Greenfield Semantic Intent packet does not match supplied evidence")
    contract_sha256 = semantic_intent_authoring_contract_sha256()
    if packet.get("authoring_contract_sha256") != contract_sha256:
        raise ValueError("Greenfield Semantic Intent packet changes its authoring contract")
    graph = require_semantic_source_meaning_graph(
        packet.get("source_meaning_graph"), evidence_sources=evidence_sources
    )
    graph_sha256 = semantic_source_meaning_sha256(graph)
    if packet.get("source_meaning_sha256") != graph_sha256:
        raise ValueError("Greenfield source-meaning graph hash mismatch")
    author_run = require_semantic_source_meaning_author_run(
        packet.get("author_run"), graph_sha256=graph_sha256
    )
    expected_intent = compile_semantic_source_meaning(
        graph, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
    )
    if packet.get("semantic_intent") != expected_intent:
        raise ValueError("Semantic Intent differs from deterministic source-meaning projection")
    semantic_intent = require_semantic_intent_ir(
        expected_intent,
        evidence_sources=evidence_sources,
        allow_empty_clarification_source_refs=False,
    )
    product_facts = (
        semantic_intent_product_facts(semantic_intent)
        if semantic_intent["status"] == "complete"
        else None
    )
    resolved = resolved_semantic_source_refs(
        {"source_meaning_graph": graph, "semantic_intent": semantic_intent},
        evidence_sources=evidence_sources,
    )
    return VerifiedSemanticIntentPacket(
        semantic_intent=semantic_intent,
        product_facts=product_facts,
        source_meaning_graph=graph,
        source_meaning_sha256=graph_sha256,
        resolved_source_refs=tuple(resolved),
        author_run=author_run,
        evidence_sha256=evidence_sha256,
        semantic_intent_sha256=semantic_intent_sha256(semantic_intent),
        semantic_meaning_sha256=semantic_intent_meaning_sha256(semantic_intent),
    )


def build_semantic_intent_packet(
    source_meaning_value: Any,
    *,
    prompt: str,
    author_run: Mapping[str, Any],
    edit_evidence: str = "",
) -> dict[str, Any]:
    """Build one packet from exact graph bytes and the sole model-call receipt."""

    evidence_sources = {
        "operator_prompt": str(prompt or ""),
        "operator_edit": str(edit_evidence or ""),
    }
    graph = require_semantic_source_meaning_graph(
        source_meaning_value, evidence_sources=evidence_sources
    )
    graph_sha256 = semantic_source_meaning_sha256(graph)
    run = require_semantic_source_meaning_author_run(
        author_run, graph_sha256=graph_sha256
    )
    packet = {
        "version": SEMANTIC_INTENT_PACKET_VERSION,
        "evidence_sha256": semantic_evidence_sha256(evidence_sources),
        "authoring_contract_sha256": semantic_intent_authoring_contract_sha256(),
        "source_meaning_graph": graph,
        "source_meaning_sha256": graph_sha256,
        "author_run": run,
        "semantic_intent": compile_semantic_source_meaning(
            graph, semantic_intent_ir_version=SEMANTIC_INTENT_IR_VERSION
        ),
    }
    require_semantic_intent_packet(
        packet, prompt=prompt, edit_evidence=edit_evidence
    )
    return packet


def build_semantic_clarification_packet(
    source_meaning_value: Any,
    *,
    prompt: str,
    author_run: Mapping[str, Any],
    edit_evidence: str = "",
) -> dict[str, Any]:
    """Build a packet only when the sole graph carries one material question."""

    packet = build_semantic_intent_packet(
        source_meaning_value,
        prompt=prompt,
        author_run=author_run,
        edit_evidence=edit_evidence,
    )
    if packet["semantic_intent"]["status"] != "clarification_required":
        raise ValueError("clarification packet requires one material question")
    return packet


def require_semantic_source_meaning_author_run(
    value: Any,
    *,
    graph_sha256: str,
) -> dict[str, Any]:
    """Validate one zero-retry frontier-author receipt."""

    row = _mapping(value, "Semantic source-meaning author run")
    keys = {
        "version", "capability_profile", "run_id", "host_profile", "model",
        "reasoning_effort", "budget_seconds", "wall_ms", "usage",
        "graph_sha256", "model_call_count", "restart_count",
    }
    if set(row) != keys:
        raise ValueError("Semantic source-meaning author run is malformed")
    if row.get("version") != SEMANTIC_SOURCE_MEANING_AUTHOR_RUN_VERSION:
        raise ValueError("Semantic source-meaning author run version is unsupported")
    if row.get("capability_profile") != _CAPABILITY_PROFILE:
        raise ValueError("Semantic source-meaning author lacks frontier capability")
    _text(row.get("run_id"), 200)
    if row.get("host_profile") not in {"codex", "claude"}:
        raise ValueError("Semantic source-meaning author host is unsupported")
    _text(row.get("model"), 100)
    if row.get("reasoning_effort") not in {"low", "medium", "high"}:
        raise ValueError("Semantic source-meaning reasoning effort is unsupported")
    budget = _integer(row.get("budget_seconds"), "author budget")
    wall_ms = _integer(row.get("wall_ms"), "author wall time")
    if budget < 1 or budget > 54 or wall_ms > budget * 1000:
        raise ValueError("Semantic source-meaning author exceeded its budget")
    if not isinstance(row.get("usage"), Mapping):
        raise ValueError("Semantic source-meaning author usage is malformed")
    if row.get("graph_sha256") != graph_sha256:
        raise ValueError("Semantic source-meaning author run does not bind graph bytes")
    if row.get("model_call_count") != 1 or row.get("restart_count") != 0:
        raise ValueError("Semantic source-meaning author run contains retry or cascade")
    return dict(row)


def semantic_intent_authority(
    verified: VerifiedSemanticIntentPacket,
    *,
    prompt: str,
    edit_evidence: str = "",
) -> dict[str, Any]:
    """Seal verified source meaning and its deterministic projection."""

    source_evidence = {
        "operator_prompt": str(prompt or ""),
        "operator_edit": str(edit_evidence or ""),
    }
    if semantic_evidence_sha256(source_evidence) != verified.evidence_sha256:
        raise ValueError("Greenfield authority does not match supplied evidence")
    if verified.semantic_intent.get("status") != "complete" or verified.product_facts is None:
        raise ValueError("clarification-bound source meaning cannot be sealed")
    from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
        PRODUCT_INTENT_AUTHORITY_VERSION,
        product_intent_authority_snapshot_hash,
        require_product_intent_authority_structure,
    )

    authority = {
        "version": PRODUCT_INTENT_AUTHORITY_VERSION,
        "origin": "verified_semantic_intent_packet",
        "decision": "confirmed_intent_accepted",
        "fact_authority": "semantic_source_meaning_graph",
        "markdown_authority": "ingest_only",
        "product_facts_sha256": semantic_intent_product_facts_sha256(
            verified.semantic_intent
        ),
        "source_format": "semantic_intent_packet",
        "materiality_status": "passed",
        "operating_envelope": greenfield_operating_envelope_receipt(
            facts=verified.product_facts,
            source_format="semantic_intent_packet",
            source_size_bytes=sum(
                len(value.encode("utf-8")) for value in source_evidence.values()
            ),
            source_document_count=1 + bool(edit_evidence),
        ),
        "semantic_intent_packet_version": SEMANTIC_INTENT_PACKET_VERSION,
        "semantic_intent_ir_version": SEMANTIC_INTENT_IR_VERSION,
        "semantic_intent_authoring_request_version": (
            SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION
        ),
        "semantic_intent_authoring_contract_sha256": (
            semantic_intent_authoring_contract_sha256()
        ),
        "semantic_source_meaning_graph": dict(verified.source_meaning_graph),
        "semantic_source_meaning_sha256": verified.source_meaning_sha256,
        "semantic_intent_author_run": dict(verified.author_run),
        # Citations are byte coordinates into the original sealed evidence.
        # Reassembling excerpts would create a different document and invalidate
        # otherwise exact Unicode, Markdown, and reordered-source custody.
        "evidence_sources": source_evidence,
        "evidence_sha256": verified.evidence_sha256,
        "accepted_evidence_sha256": verified.evidence_sha256,
        "semantic_intent": dict(verified.semantic_intent),
        "semantic_intent_sha256": verified.semantic_intent_sha256,
        "semantic_meaning_sha256": verified.semantic_meaning_sha256,
        "semantic_source_refs": [dict(row) for row in verified.resolved_source_refs],
    }
    authority["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(
        authority
    )
    require_product_intent_authority_structure(authority)
    return authority


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} is malformed")
    return value


def _text(value: Any, maximum: int) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > maximum:
        raise ValueError("Semantic source-meaning run text is malformed")
    return value


def _integer(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"Semantic {label} is invalid")
    return value


__all__ = [
    "MAX_SEMANTIC_INTENT_PACKET_BYTES",
    "SEMANTIC_INTENT_PACKET_VERSION",
    "VerifiedSemanticIntentPacket",
    "build_semantic_clarification_packet",
    "build_semantic_intent_packet",
    "load_semantic_intent_packet",
    "require_semantic_intent_packet",
    "require_semantic_source_meaning_author_run",
    "semantic_evidence_sha256",
    "semantic_intent_authority",
    "semantic_intent_packet_schema",
    "semantic_source_meaning_author_run_schema",
]
