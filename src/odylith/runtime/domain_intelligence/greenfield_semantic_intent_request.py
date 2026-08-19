"""Deterministic host authoring contract for Greenfield Semantic Intent."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    semantic_evidence_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    semantic_intent_authoring_contract,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION,
    semantic_intent_authoring_contract_sha256,
    semantic_intent_authoring_protocol,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    semantic_intent_packet_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    semantic_materiality_assessment_schema,
    semantic_materiality_critic_schema,
)


SEMANTIC_INTENT_PACKET_DIRECTORY = Path(
    ".odylith/runtime/greenfield/semantic-intent"
)
_EDIT_SEPARATOR = "\n\n--- next operator correction ---\n\n"


def semantic_intent_authoring_request(
    *,
    prompt: str,
    edit_evidence: str = "",
    supersedes_transaction_hash: str = "",
) -> dict[str, Any]:
    """Return exact evidence and one machine-readable graph-authoring contract."""

    evidence_sources = {
        "operator_prompt": str(prompt or ""),
        "operator_edit": str(edit_evidence or ""),
    }
    evidence_sha256 = semantic_evidence_sha256(evidence_sources)
    packet_path = SEMANTIC_INTENT_PACKET_DIRECTORY / f"{evidence_sha256}.json"
    schema = semantic_intent_packet_schema()
    authoring_contract_sha256 = semantic_intent_authoring_contract_sha256()
    return {
        "version": SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION,
        "authoring_contract_sha256": authoring_contract_sha256,
        "materiality_owner": "independent_frontier_host_model",
        "semantic_owner": "distinct_frontier_host_model",
        "verification_owner": "odylith_deterministic_contract",
        "evidence_sources": evidence_sources,
        "evidence_sha256": evidence_sha256,
        "supersedes_transaction_hash": str(supersedes_transaction_hash or ""),
        "packet_destination": packet_path.as_posix(),
        "packet_header": {
            "version": schema["properties"]["version"]["enum"][0],
            "evidence_sha256": evidence_sha256,
            "authoring_contract_sha256": authoring_contract_sha256,
        },
        "materiality_gate": {
            "order": "before_graph_authoring",
            "evidence_sources": evidence_sources,
            "candidate_access": "forbidden",
            "source_candidates": (
                "required; an independent critic locks exact evidence spans only and has no semantic authority"
            ),
            "workflow_candidate_adjudication": (
                "one graph author must decide every span, author the complete source graph, and bind every source claim before deterministic verification"
            ),
            "assessment_schema": semantic_materiality_assessment_schema(),
            "critic_run_schema": semantic_materiality_critic_schema(),
            "structured_output": "exact_schema_constrained_when_available",
            "schema_failure_action": "block_or_start_fresh_independent_author_run",
        },
        "packet_schema": schema,
        "packet_structured_output": "exact_schema_constrained_when_available",
        "semantic_contract": semantic_intent_authoring_contract(),
        "authoring_protocol": semantic_intent_authoring_protocol(),
        "next_invocation": {
            "command": "odylith greenfield propose",
            "arguments": [
                "--repo-root",
                ".",
                "--prompt",
                evidence_sources["operator_prompt"],
                *(
                    ["--edit", evidence_sources["operator_edit"]]
                    if evidence_sources["operator_edit"]
                    else []
                ),
                "--semantic-intent-file",
                packet_path.as_posix(),
            ],
        },
    }


def semantic_intent_revision_request(
    *,
    repo_root: Path,
    transaction_hash: str,
    correction: str,
) -> dict[str, Any]:
    """Rebind one EDIT to sealed evidence without reinterpreting the old package."""

    from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
        load_compiled_product_create_transaction_file,
    )

    correction_text = str(correction or "")
    if not correction_text.strip():
        raise ValueError("Greenfield Semantic Intent revision requires correction evidence")
    path = greenfield_pending_transaction_store.resolve_pending_transaction(
        repo_root=Path(repo_root),
        transaction_hash=transaction_hash,
    )
    transaction = load_compiled_product_create_transaction_file(path)
    authority = transaction.intent_authority
    evidence = authority.get("evidence_sources") if isinstance(authority, Mapping) else None
    if not isinstance(evidence, Mapping):
        raise ValueError("pending Greenfield transaction lacks sealed evidence sources")
    prompt = evidence.get("operator_prompt")
    prior_edit = evidence.get("operator_edit")
    if not isinstance(prompt, str) or not isinstance(prior_edit, str):
        raise ValueError("pending Greenfield transaction has malformed sealed evidence sources")
    cumulative_edit = (
        f"{prior_edit}{_EDIT_SEPARATOR}{correction_text}"
        if prior_edit
        else correction_text
    )
    request = semantic_intent_authoring_request(
        prompt=prompt,
        edit_evidence=cumulative_edit,
        supersedes_transaction_hash=transaction_hash,
    )
    request["prior_semantic_intent"] = (
        dict(authority["semantic_intent"])
        if isinstance(authority.get("semantic_intent"), Mapping)
        else None
    )
    request["revision_evidence"] = {
        "prior_operator_edit": prior_edit,
        "new_operator_correction": correction_text,
        "canonical_separator": _EDIT_SEPARATOR,
    }
    return request


__all__ = [
    "SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION",
    "SEMANTIC_INTENT_PACKET_DIRECTORY",
    "semantic_intent_authoring_request",
    "semantic_intent_revision_request",
]
