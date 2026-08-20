"""Versioned host-model authoring contract for Greenfield Semantic Intent."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    semantic_intent_authoring_contract,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_extension_contract import (
    semantic_graph_extension_contract,
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
from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
    atomic_source_adjudication_schema,
    atomic_source_custody_contract,
)


SEMANTIC_INTENT_AUTHORING_REQUEST_VERSION = (
    "odylith.greenfield.semantic-intent-authoring-request.v18"
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
            "source_candidate_authority": (
                "the critic identifies exact evidence spans only; it may not assign semantic "
                "kinds, canonical fields, ownership, relations, or product identity"
            ),
            "decision": "authorize_graph_or_request_one_focused_clarification",
            "graph_candidate_access": "exact_evidence_spans_only",
            "graph_author_binding": (
                "the critic-validated exact-byte citation catalog, decision, clarification, "
                "and atomic evidence spans are provider-locked before graph authoring; one graph "
                "author assigns all semantic kinds, fields, ownership, relations, identity, bounded "
                "architecture edges, and presentation, then binds every source claim to those spans"
            ),
        },
        "materiality_field_semantics": {
            "identity": (
                "the functional product or tool being created, not necessarily a proper name; "
                "when the product function and boundary are settled, a missing name is a "
                "nonmaterial bounded assumption; discarded or historical labels are not identity"
            ),
            "role": (
                "the target user or accountable human or organizational participant; an empty "
                "actor graph is settled only when evidence entails product or system ownership "
                "without a human-facing interaction; a source statement that directly names an "
                "actor performing a first-path action settles that role unless the source also "
                "supplies conflicting ownership evidence"
            ),
            "first_path": (
                "the complete ordered usable path from its accepted input or selection through "
                "the action that makes the visible result available"
            ),
            "state_object": (
                "a durable domain object and its supported transition; a destination or collection "
                "name alone does not establish a separate state object"
            ),
            "visible_result": (
                "an artifact, status, decision, notification, summary, receipt, or evidence that "
                "a consumer can observe after the path; a mutation, destination, collection "
                "membership, or completed action alone is not a visible result"
            ),
            "dependency": (
                "a named system, data source, repository resource, or service required by the path"
            ),
            "constraint": "a safety or operating limit on accepted behavior or access",
            "non_goal": "a capability or outcome explicitly excluded from product scope",
            "component_boundary": (
                "a distinct implementation responsibility or external boundary justified by typed "
                "facts; optional architecture depth is not a material product question"
            ),
        },
        "materiality_decision_rules": [
            (
                "authorize when functional identity, target role or source-entailable actorless "
                "ownership, complete first path, and observable visible result are settled; a "
                "missing proper name alone is not a material question"
            ),
            (
                "clarify identity only when competing product interpretations materially change "
                "the product boundary, first path, or visible result; otherwise author a concise "
                "functional identity as bounded interpretation and keep the assumption visible"
            ),
            (
                "treat an explicit actor performing a first-path action as settled role evidence; "
                "do not replace that actor with a hypothetical automated product or system unless "
                "the source provides contradictory ownership evidence"
            ),
            (
                "when a named first-path actor operates on an input already described as selected, "
                "reviewed, prepared, or otherwise ready, treat that input condition as an upstream "
                "precondition rather than a missing first-path role; ask about role only when the "
                "requested first-path action itself lacks an accountable participant"
            ),
            (
                "require every clarification alternative to be independently supported by source "
                "evidence and materially distinct; never create a question from an unsupported "
                "alternative"
            ),
            (
                "do not use an internal transition, destination, lane membership, or successful "
                "mutation as evidence of a visible result unless the source makes it observable"
            ),
            (
                "when evidence describes a human-facing interaction but omits who performs or "
                "receives it, mark role materially unresolved"
            ),
            (
                "when product or system ownership is explicit and no human-facing interaction is "
                "required, role may be source-entailable without an actor fact"
            ),
            (
                "ask exactly one question for the highest-impact unresolved canonical field and "
                "preserve all settled meaning"
            ),
            (
                "when clarification is required, clarification owns the omitted field, its exact "
                "source references, and one focused question without an inferred option list; "
                "fields contains only the other eight settled canonical fields"
            ),
        ],
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
            (
                "decide every locked evidence span exactly once and bind every source-owned fact "
                "and relation to at least one retained exact span"
            ),
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
        "conditionally_optional_axes": {
            "actors_and_ownership": (
                "empty only for source-entailable product or system ownership without a "
                "human-facing interaction"
            ),
            "state_objects_and_transitions": (
                "empty when evidence does not declare durable state; a transition is one "
                "atomic from_state/to_state object or null, never independent attributes"
            ),
        },
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
            "critic_authored_semantic_kind_field_ownership_relation_or_identity",
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
        "source_candidate_adjudication_schema": (
            atomic_source_adjudication_schema()
        ),
        "source_candidate_adjudication_contract": (
            atomic_source_custody_contract()
        ),
        "semantic_graph_extension_contract": semantic_graph_extension_contract(),
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
