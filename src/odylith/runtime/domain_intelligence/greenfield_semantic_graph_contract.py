"""Declarative shape and completeness contract for Greenfield semantic graphs."""

from __future__ import annotations

from typing import Any


SEMANTIC_FACT_KINDS = (
    "identity",
    "actor",
    "workflow_step",
    "state_object",
    "visible_output",
    "external_system",
    "internal_system",
    "component_responsibility",
    "operational_constraint",
    "non_goal",
    "assumption",
    "ambiguity",
)
SEMANTIC_RELATION_KINDS = (
    "owned_by",
    "produces",
    "changes",
    "depends_on",
    "implements",
    "constrained_by",
    "excludes",
)
SEMANTIC_NARRATIVE_FIELDS = (
    "product_story",
    "problem",
    "customer",
    "opportunity",
    "product_view",
    "proof_boundary",
    "success_metric",
    "evidence_requirement",
)
SEMANTIC_CLARIFICATION_FIELDS = (
    "identity",
    "role",
    "first_path",
    "state_object",
    "visible_result",
    "dependency",
    "constraint",
    "non_goal",
    "component_boundary",
)
SINGULAR_NARRATIVE_FIELDS = frozenset(
    {"product_story", "problem", "customer", "opportunity", "product_view", "proof_boundary"}
)
LIST_NARRATIVE_FIELDS = frozenset({"success_metric", "evidence_requirement"})
FACT_REQUIRED_ATTRIBUTES = {
    "identity": ("source_title",),
    "actor": ("responsibility",),
    "workflow_step": ("action", "action_phrase"),
    "state_object": ("object",),
    "internal_system": (
        "responsibility",
        "component_kind",
        "boundary",
        "outside_boundary",
        "proof",
        "risk",
        "release_scope",
    ),
}
FACT_SEMANTIC_ROLES = {
    "identity": "the source-backed product identity, excluding discarded or superseded labels",
    "actor": "one explicit human role or participant; preserve each declared role separately",
    "workflow_step": "one ordered source-entailable action with its real semantic owner kind",
    "state_object": "one durable domain object and at most one explicit transition pair",
    "visible_output": "one source-entailable result that a consumer can observe",
    "external_system": "one explicit dependency or external boundary; never merge named dependencies",
    "internal_system": (
        "one specific implementation responsibility needed for typed workflow, state, or output facts; "
        "never a generic interface, local capability, or restatement of the whole product"
    ),
    "component_responsibility": "one source-entailable responsibility boundary not owned by another fact",
    "operational_constraint": (
        "a rule limiting how an accepted capability, access path, or execution behavior may operate; "
        "classify by its relationship to accepted behavior, regardless of grammatical form"
    ),
    "non_goal": (
        "an entire capability or outcome excluded from product scope; classify by its relationship "
        "to accepted behavior, regardless of grammatical form, and never duplicate it as a constraint"
    ),
    "assumption": "a visible non-material interpretation needed to proceed",
    "ambiguity": "an unresolved material meaning that requires clarification",
}
COMPLETE_FACT_COUNTS = {
    "identity": {"minimum": 1, "maximum": 1},
    "actor": {"minimum": 0, "maximum": 64},
    "workflow_step": {"minimum": 1},
    "state_object": {"minimum": 0, "maximum": 16},
    "visible_output": {"minimum": 1},
    "internal_system": {"minimum": 1, "maximum": 128},
}
RELATION_ENDPOINT_KINDS = {
    "owned_by": {"subject": ("workflow_step",), "object": ("actor",)},
    "produces": {"subject": ("workflow_step",), "object": ("visible_output",)},
    "changes": {"subject": ("workflow_step",), "object": ("state_object",)},
    "depends_on": {
        "subject": ("identity", "internal_system", "workflow_step"),
        "object": ("external_system", "internal_system"),
    },
    "implements": {
        "subject": ("internal_system",),
        "object": ("workflow_step", "state_object", "visible_output"),
    },
    "constrained_by": {
        "subject": ("identity", "internal_system", "workflow_step"),
        "object": ("operational_constraint",),
    },
    "excludes": {
        "subject": ("identity", "internal_system", "workflow_step"),
        "object": ("non_goal",),
    },
}


def semantic_intent_authoring_contract() -> dict[str, Any]:
    """Expose every non-schema invariant enforced before Product Intent sealing."""

    return {
        "status_contract": {
            "propose_accepts": "complete",
            "clarification_required_action": (
                "ask one focused question, bind the answer as operator_edit evidence, "
                "then author a new complete packet"
            ),
            "clarification_fields": list(SEMANTIC_CLARIFICATION_FIELDS),
            "clarification_graph": (
                "preserve every settled source-cited fact, relation, and narrative; "
                "omit only meaning that depends on the unresolved field"
            ),
        },
        "source_citation_contract": {
            "match": "exact evidence bytes",
            "source_ids": ["operator_prompt", "operator_edit"],
            "occurrence_is_one_based": True,
            "every_fact_relation_and_narrative_requires_source_refs": True,
        },
        "fact_contracts": {
            kind: {
                "semantic_role": FACT_SEMANTIC_ROLES[kind],
                "required_attributes": list(FACT_REQUIRED_ATTRIBUTES.get(kind, ())),
                "owner_kinds": (
                    ["actor", "product", "system"]
                    if kind == "workflow_step"
                    else ["none"]
                ),
                **COMPLETE_FACT_COUNTS.get(kind, {}),
            }
            for kind in SEMANTIC_FACT_KINDS
        },
        "relation_contracts": {
            kind: {
                "subject_kinds": list(contract["subject"]),
                "object_kinds": list(contract["object"]),
            }
            for kind, contract in RELATION_ENDPOINT_KINDS.items()
        },
        "narrative_contracts": {
            field: {
                "minimum": 1,
                **({"maximum": 1} if field in SINGULAR_NARRATIVE_FIELDS else {}),
            }
            for field in SEMANTIC_NARRATIVE_FIELDS
        },
        "complete_graph_contract": {
            "minimum_success_metrics": 2,
            "empty_actor_and_state_axes_must_not_be_synthesized": True,
            "every_actor_owned_step_has_exactly_one_owned_by_relation": True,
            "product_and_system_steps_have_no_owned_by_relation": True,
            "every_visible_output_has_a_typed_produces_relation": True,
            "every_state_object_has_a_typed_changes_relation": True,
            "minimum_first_path_required_internal_systems": 1,
            "implementation_coverage_release_scopes": [
                "first_path_required",
                "supporting",
            ],
            "every_workflow_step_state_object_and_visible_output_is_implemented_by_an_active_system": True,
            "maximum_transition_pairs_per_state_object": 1,
            "multiple_transitions_for_one_state_object": "clarification_required",
        },
        "ordering_contract": (
            "order is zero-based and contiguous within each fact kind, relation kind, "
            "and narrative field"
        ),
    }


__all__ = [
    "COMPLETE_FACT_COUNTS",
    "FACT_REQUIRED_ATTRIBUTES",
    "FACT_SEMANTIC_ROLES",
    "LIST_NARRATIVE_FIELDS",
    "RELATION_ENDPOINT_KINDS",
    "SEMANTIC_FACT_KINDS",
    "SEMANTIC_CLARIFICATION_FIELDS",
    "SEMANTIC_NARRATIVE_FIELDS",
    "SEMANTIC_RELATION_KINDS",
    "SINGULAR_NARRATIVE_FIELDS",
    "semantic_intent_authoring_contract",
]
