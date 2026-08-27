"""Versioned Greenfield semantic-authority contract."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_IR_VERSION,
    SEMANTIC_INTENT_PACKET_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_meaning import (
    SEMANTIC_SOURCE_MEANING_AUTHOR_RUN_VERSION,
    semantic_source_meaning_contract,
    semantic_source_meaning_graph_schema,
)


SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION = (
    "odylith.greenfield.semantic-intent-authoring-request.v45"
)
SEMANTIC_INTENT_MANDATORY_CHALLENGES = (
    "unsupported_addition",
    "supported_fact_omission",
    "ownership_mismatch",
    "polarity_reversal",
    "dependency_as_workflow",
    "output_as_workflow",
    "policy_entity_promotion",
    "discarded_evidence_promotion",
    "material_question_quality",
    "consumer_copy_specificity",
    "cross_surface_utility",
)


def semantic_intent_authoring_protocol() -> dict[str, Any]:
    """Return the active semantic topology and fixed outcome laws."""

    return {
        "mechanism_status": "selected_by_disclosed_development_evidence",
        "mechanism": "holistic_tagged_entity_effect_source_meaning",
        "model_calls": 1,
        "parallel_model_calls": 0,
        "maximum_author_seconds": 54,
        "retries": 0,
        "critics": 0,
        "selectors": 0,
        "merges": 0,
        "repairs": 0,
        "source_authority": (
            "one unchanged typed source-meaning graph; deterministic code validates "
            "exact citations and projects implementation artifacts without reinterpreting prose"
        ),
        "clarification": (
            "one grounded question with exact source citations when material product "
            "meaning is unsettled; no field taxonomy or routing label"
        ),
        "mandatory_challenges": list(SEMANTIC_INTENT_MANDATORY_CHALLENGES),
        "forbidden_mechanisms": [
            "regex_or_token_semantic_inference",
            "fuzzy_or_vocabulary_semantic_inference",
            "candidate_repair_or_merge",
            "serial_critic_or_selector_cascade",
            "downstream_prose_reinterpretation",
            "post_confirm_semantic_work",
        ],
        "latency_laws": {
            "standard": "strictly_less_than_60_seconds",
            "rescue": "cumulative_at_most_90_seconds",
            "explicit_deep": "operator_or_ci_only_at_most_120_seconds",
        },
    }


def semantic_intent_authoring_contract_payload() -> dict[str, Any]:
    """Return the exact prompt-independent contract sealed with intent."""

    return {
        "version": SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION,
        "semantic_intent_ir_version": SEMANTIC_INTENT_IR_VERSION,
        "semantic_intent_packet_version": SEMANTIC_INTENT_PACKET_VERSION,
        "source_meaning_graph_schema": semantic_source_meaning_graph_schema(),
        "source_meaning_contract": semantic_source_meaning_contract(),
        "author_run_version": SEMANTIC_SOURCE_MEANING_AUTHOR_RUN_VERSION,
        "authoring_protocol": semantic_intent_authoring_protocol(),
    }


def semantic_intent_authoring_contract_sha256() -> str:
    """Hash the complete mechanism and source-meaning contract."""

    encoded = json.dumps(
        semantic_intent_authoring_contract_payload(),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION",
    "SEMANTIC_INTENT_MANDATORY_CHALLENGES",
    "semantic_intent_authoring_contract_payload",
    "semantic_intent_authoring_contract_sha256",
    "semantic_intent_authoring_protocol",
]
