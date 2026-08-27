"""Declarative shape and completeness contract for Greenfield semantic graphs."""

from __future__ import annotations

from typing import Any


SEMANTIC_FACT_KINDS = (
    "audience",
    "actor",
    "entity",
    "workflow_step",
    "state_object",
    "visible_output",
    "external_system",
    "internal_system",
    "component_responsibility",
    "product_boundary",
    "policy_boundary",
    "assumption",
)
SEMANTIC_RELATION_KINDS = (
    "owned_by",
    "input_entity",
    "target_entity",
    "creates",
    "produces",
    "output_of",
    "visible_to",
    "changes",
    "maintains",
    "state_of",
    "depends_on",
    "implements",
    "applies_to",
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
SEMANTIC_ATTRIBUTE_NAMES = (
    "action",
    "action_phrase",
    "object",
    "entity_id",
    "condition",
    "responsibility",
    "component_kind",
    "boundary",
    "outside_boundary",
    "proof",
    "risk",
    "release_scope",
    "audience_kind",
    "access_mode",
    "modalities",
    "statement",
    "stable_state",
)
SINGULAR_NARRATIVE_FIELDS = frozenset(
    {"product_story", "problem", "customer", "opportunity", "product_view", "proof_boundary"}
)
LIST_NARRATIVE_FIELDS = frozenset({"success_metric", "evidence_requirement"})
INTERNAL_SYSTEM_COMPONENT_KINDS = (
    "adapter",
    "interface",
    "library",
    "service",
    "worker",
)
INTERNAL_SYSTEM_RELEASE_SCOPES = (
    "first_path_required",
    "deferred",
)
FACT_REQUIRED_ATTRIBUTES = {
    "audience": ("audience_kind",),
    "workflow_step": ("action", "action_phrase"),
    "state_object": ("object", "entity_id"),
    "visible_output": ("entity_id",),
    "product_boundary": ("statement",),
    "policy_boundary": ("modalities", "statement"),
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
FACT_OWNER_KINDS = {
    kind: ("actor", "product", "system") if kind == "workflow_step" else ("none",)
    for kind in SEMANTIC_FACT_KINDS
}
FACT_SEMANTIC_ROLES = {
    "audience": "one explicit passive human or nonhuman recipient; never a workflow owner",
    "actor": "one explicit human role or participant; preserve each declared role separately",
    "entity": (
        "one canonical source-declared domain or observable entity; identity comes from its graph id, "
        "never from matching its label against workflow prose"
    ),
    "workflow_step": "one ordered source-entailable action with its real semantic owner kind",
    "state_object": (
        "one durable domain object with either no transition or one atomic "
        "transition object whose nullable endpoints preserve only source-declared states"
    ),
    "visible_output": "one source-entailable result that a consumer can observe",
    "external_system": "one explicit dependency or external boundary; never merge named dependencies",
    "internal_system": (
        "one source-explicit internal boundary; never synthesize a default system or restate the product"
    ),
    "component_responsibility": "one source-entailable responsibility boundary not owned by another fact",
    "product_boundary": (
        "one source-declared product scope, execution-location, deployment, or data-locality boundary; "
        "never a behavioral policy"
    ),
    "policy_boundary": (
        "one neutral source-grounded boundary preserving its complete statement and every explicit modality"
    ),
    "assumption": "a visible non-material interpretation needed to proceed",
}
COMPLETE_FACT_COUNTS = {
    "audience": {"minimum": 0, "maximum": 64},
    "actor": {"minimum": 0, "maximum": 64},
    "entity": {"minimum": 0, "maximum": 64},
    "workflow_step": {"minimum": 1},
    "state_object": {"minimum": 0, "maximum": 16},
    "visible_output": {"minimum": 1},
    "internal_system": {"minimum": 0, "maximum": 128},
}
RELATION_ENDPOINT_KINDS = {
    "owned_by": {"subject": ("workflow_step",), "object": ("actor",)},
    "input_entity": {"subject": ("workflow_step",), "object": ("entity",)},
    "target_entity": {"subject": ("workflow_step",), "object": ("entity",)},
    "creates": {"subject": ("workflow_step",), "object": ("entity",)},
    "produces": {"subject": ("workflow_step",), "object": ("visible_output",)},
    "output_of": {"subject": ("visible_output",), "object": ("entity",)},
    "visible_to": {
        "subject": ("visible_output",),
        "object": ("actor", "audience"),
    },
    "changes": {"subject": ("workflow_step",), "object": ("state_object",)},
    "maintains": {"subject": ("workflow_step",), "object": ("state_object",)},
    "state_of": {"subject": ("state_object",), "object": ("entity",)},
    "depends_on": {
        "subject": ("internal_system", "workflow_step"),
        "object": ("external_system", "internal_system"),
    },
    "implements": {
        "subject": ("internal_system",),
        "object": ("workflow_step", "state_object", "visible_output"),
    },
    "applies_to": {
        "subject": ("policy_boundary",),
        "object": ("workflow_step", "external_system", "internal_system"),
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
            "clarification_graph": (
                "preserve every settled source-cited fact, relation, and narrative; "
                "ask one question citing the exact source uncertainty and carry no accepted graph rows"
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
                **(
                    {
                        "attribute_value_contracts": {
                            "component_kind": list(INTERNAL_SYSTEM_COMPONENT_KINDS),
                            "release_scope": list(INTERNAL_SYSTEM_RELEASE_SCOPES),
                        },
                        "release_scope_semantics": {
                            "first_path_required": (
                                "the source explicitly places this boundary in the first release"
                            ),
                            "deferred": "excluded from the first release",
                            "implementation_role": (
                                "preserve only source-entailable relations; project delivery policy "
                                "outside the canonical Semantic Intent graph"
                            ),
                        },
                    }
                    if kind == "internal_system"
                    else {}
                ),
                "owner_kinds": (
                    list(FACT_OWNER_KINDS[kind])
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
            "visible_output_relations_exist_only_when_source_explicit": True,
            "source_entailable_output_recipients_use_visible_to_instead_of_workflow_ownership": True,
            "state_change_relations_exist_only_when_source_explicit": True,
            "workflow_entity_roles_are_typed_relations_to_canonical_entity_ids": True,
            "state_and_output_identity_are_bound_to_exactly_one_canonical_entity": True,
            "canonical_graph_custody": (
                "facts and relations preserve only source-entailable meaning; "
                "implementation policy is projected outside the canonical graph"
            ),
            "explicit_internal_systems_are_optional": True,
            "implementation_policy_is_not_a_semantic_fact_or_relation": True,
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
    "SEMANTIC_ATTRIBUTE_NAMES",
    "SEMANTIC_FACT_KINDS",
    "SEMANTIC_NARRATIVE_FIELDS",
    "SEMANTIC_RELATION_KINDS",
    "SINGULAR_NARRATIVE_FIELDS",
    "semantic_intent_authoring_contract",
]
