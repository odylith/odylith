"""Versioned host-model authoring contract for Greenfield Semantic Intent."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    semantic_intent_authoring_contract,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_IR_VERSION,
    SEMANTIC_INTENT_PACKET_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_schema import (
    semantic_intent_output_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    semantic_intent_author_schema,
    semantic_materiality_assessment_schema,
    semantic_materiality_critic_schema,
)


SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION = (
    "odylith.greenfield.semantic-intent-authoring-request.v3"
)
SEMANTIC_INTENT_MANDATORY_CHALLENGES = (
    "unsupported_addition",
    "supported_fact_omission",
    "ownership_mismatch",
    "cardinality_violation",
    "polarity_reversal",
    "wrong_relation_endpoint",
    "weak_component_differentiation",
    "evidence_status_misclassification",
    "semantic_kind_conflation",
    "explicit_axis_cardinality_loss",
    "partial_clarification_custody",
    "consumer_copy_specificity",
    "cross_surface_utility",
)


def semantic_intent_authoring_protocol() -> dict[str, Any]:
    """Return the mechanism-neutral outcome and challenge contract."""

    return {
        "mechanism_status": "provisional",
        "mechanism_selection": "pending_development_evidence",
        "materiality_gate": {
            "order": "before_graph_authoring",
            "evidence_scope": "prompt_only",
            "critic_context": "independent",
            "decision": "authorize_graph_or_request_one_focused_clarification",
            "candidate_access": "forbidden",
        },
        "structured_output_contract": {
            "assessment_mode": "exact_schema_constrained_when_available",
            "packet_mode": "exact_schema_constrained_when_available",
            "schema_failure_action": "block_or_start_fresh_independent_author_run",
            "forbidden_action": "validation_error_driven_field_repair",
        },
        "component_boundary_custody": {
            "source_fact": (
                "allowed only when source evidence explicitly names the exact component "
                "responsibility or boundary"
            ),
            "bounded_interpretation": (
                "required for inferred decomposition needed to implement typed facts; "
                "each inferred boundary must remain specific and differentiated"
            ),
            "runtime_detection": "forbidden",
        },
        "semantic_kind_disambiguation": {
            "operational_constraint": (
                "limits how an accepted capability, access path, or execution behavior may operate"
            ),
            "non_goal": "excludes an entire capability or outcome from product scope",
            "decision_basis": "relationship_to_accepted_behavior_not_tokens_or_grammar",
            "duplication": "one statement must never populate both semantic kinds",
            "challenge": "semantic_kind_conflation",
            "runtime_detection": "forbidden",
        },
        "outcome_requirements": [
            "produce one complete source-cited typed graph",
            "preserve supported meaning without adding unsupported product semantics",
            "emit clarification_required for unresolved material disagreement",
            (
                "when clarification is required, preserve every settled source-cited "
                "fact, relation, and narrative and omit only meaning that depends on "
                "the unresolved canonical field"
            ),
            (
                "treat superseded, discarded, retired, deleted, or evidence-noise labels "
                "as excluded interpretation evidence, never as product facts, non-goals, "
                "components, or relations"
            ),
            (
                "keep every explicit actor and dependency as its own typed fact, distinguish "
                "operational constraints from excluded product capabilities, and bind each "
                "state change and visible output to the exact source-entailable workflow step"
            ),
            (
                "write consumer narratives with the specific project, actor, action, object, "
                "state, and output supported by evidence; never substitute generic phrases "
                "such as stated path, requested workflow, or named operator"
            ),
            "make each governed surface concise, reviewable, and useful for its distinct job",
        ],
        "required_axes": [
            "identity",
            "ordered_actions",
            "visible_outcomes",
            "dependencies_and_access_direction",
            "constraints",
            "non_goals",
            "component_boundaries",
            "proof",
        ],
        "optional_axes": [
            "actors_and_ownership",
            "state_objects_and_transitions",
        ],
        "empty_axis_rule": (
            "emit an empty actor or state-object collection when evidence does not "
            "support that axis; never synthesize a placeholder fact"
        ),
        "mandatory_challenges": list(SEMANTIC_INTENT_MANDATORY_CHALLENGES),
        "challenge_requirement": (
            "all mandatory challenges must pass against the supplied evidence and "
            "semantic contract; no authoring sequence is prescribed"
        ),
        "material_disagreement_action": "clarification_required",
        "replacement_discipline": {
            "status": "evidence_led",
            "triggers": [
                "recurring_failure_across_independent_examples",
                "cross_surface_regression",
                "fixture_dependence",
                "complexity_or_latency_growth_without_product_gain",
                "downstream_reinterpretation_of_canonical_meaning",
            ],
            "action": "compare_bounded_alternatives_and_remove_the_losing_mechanism",
        },
        "forbidden_mechanisms": [
            "regex_or_token_semantic_inference",
            "legacy_prose_recomposition",
            "validation_error_driven_packet_repair",
            "silent_candidate_merge",
            "post_candidate_materiality_assessment",
        ],
    }


def semantic_intent_authoring_contract_payload() -> dict[str, Any]:
    """Return the exact prompt-independent contract sealed with accepted intent."""

    return {
        "version": SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION,
        "semantic_intent_ir_version": SEMANTIC_INTENT_IR_VERSION,
        "semantic_intent_packet_version": SEMANTIC_INTENT_PACKET_VERSION,
        "semantic_intent_schema": semantic_intent_output_schema(),
        "materiality_assessment_schema": semantic_materiality_assessment_schema(),
        "materiality_critic_schema": semantic_materiality_critic_schema(),
        "semantic_intent_author_schema": semantic_intent_author_schema(),
        "semantic_contract": semantic_intent_authoring_contract(),
        "authoring_protocol": semantic_intent_authoring_protocol(),
    }


def semantic_intent_authoring_contract_sha256() -> str:
    """Hash the canonical host-authoring contract without prompt evidence."""

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
