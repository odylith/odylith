"""Typed provider schema and outcome contract for node-owned source meaning."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    semantic_evidence_block_schema,
    semantic_source_ref_schema,
)


SEMANTIC_SOURCE_MEANING_GRAPH_VERSION = (
    "odylith.greenfield.semantic-source-meaning-graph.v16"
)
SEMANTIC_SOURCE_MEANING_CONTRACT_VERSION = (
    "odylith.greenfield.semantic-source-meaning-contract.v22"
)

SOURCE_MEANING_COLLECTIONS = (
    "audiences",
    "actors",
    "entities",
    "workflow",
    "dependencies",
    "product_boundaries",
    "policy_boundaries",
    "non_material_gaps",
    "provenance_only",
)
SOURCE_MEANING_MODALITIES = ("permitted", "prohibited", "required", "limited")
SOURCE_MEANING_AUDIENCE_KINDS = ("explicit_human", "explicit_nonhuman")
SOURCE_MEANING_ENTITY_EFFECT_KINDS = (
    "input",
    "target",
    "created",
    "changed",
    "stable",
    "visible_result",
)


def semantic_source_meaning_graph_schema(
    *, source_ref_schema: Mapping[str, Any] | None = None,
    _provider_effect_slots: bool = False,
) -> dict[str, Any]:
    """Return the exact graph schema accepted at the semantic boundary."""

    source_ref = dict(source_ref_schema or semantic_source_ref_schema())
    refs = _array(source_ref, minimum=1, maximum=8)
    actor_recipient = _object(
        {
            "kind": {"type": "string", "enum": ["actor"]},
            "index": {"type": "integer", "minimum": 0, "maximum": 63},
            "source_refs": refs,
        }
    )
    audience_recipient = _object(
        {
            "kind": {"type": "string", "enum": ["audience"]},
            "index": {"type": "integer", "minimum": 0, "maximum": 63},
            "source_refs": refs,
        }
    )
    indexed_effect = {
        "entity_index": {"type": "integer", "minimum": 0, "maximum": 63},
        "source_refs": refs,
    }
    entity_effect = {
        "anyOf": [
            _object(
                ({
                    "kind": {"type": "string", "enum": [kind]},
                    **indexed_effect,
                })
            )
            for kind in ("input", "target")
        ]
        + [
            _object(
                {
                    "kind": {"type": "string", "enum": ["created"]},
                    **indexed_effect,
                    "edge_source_refs": refs,
                }
            ),
            _object(
                {
                    "kind": {"type": "string", "enum": ["changed"]},
                    **indexed_effect,
                    "from_state": _text_schema(200),
                    "to_state": _text_schema(200),
                    "edge_source_refs": refs,
                }
            ),
            _object(
                {
                    "kind": {"type": "string", "enum": ["stable"]},
                    **indexed_effect,
                    "stable_state": _text_schema(200),
                    "edge_source_refs": refs,
                }
            ),
            _object(
                {
                    "kind": {"type": "string", "enum": ["visible_result"]},
                    **indexed_effect,
                    "visible_to": _array(
                        {"anyOf": [actor_recipient, audience_recipient]}, maximum=64
                    ),
                    "edge_source_refs": refs,
                }
            ),
        ]
    }
    effect_payloads = {
        "input": _object({"source_refs": refs}),
        "target": _object({"source_refs": refs}),
        "created": _object(
            {"source_refs": refs, "edge_source_refs": refs}
        ),
        "changed": _object(
            {
                "source_refs": refs,
                "from_state": _text_schema(200),
                "to_state": _text_schema(200),
                "edge_source_refs": refs,
            }
        ),
        "stable": _object(
            {
                "source_refs": refs,
                "stable_state": _text_schema(200),
                "edge_source_refs": refs,
            }
        ),
        "visible_result": _object(
            {
                "source_refs": refs,
                "visible_to": _array(
                    {"anyOf": [actor_recipient, audience_recipient]}, maximum=64
                ),
                "edge_source_refs": refs,
            }
        ),
    }
    entity_effect_slots = _array(
        _object(
            {
                "entity_index": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 63,
                },
                **{
                    kind: _nullable(payload)
                    for kind, payload in effect_payloads.items()
                },
            }
        ),
        maximum=64,
    )
    workflow_effects_key = (
        "entity_effect_slots" if _provider_effect_slots else "entity_effects"
    )
    workflow_effects = (
        entity_effect_slots
        if _provider_effect_slots
        else _array(entity_effect, maximum=64)
    )
    policy_boundary = {
        "anyOf": [
            _object(
                {
                    "modalities": _array(
                        {"type": "string", "enum": list(SOURCE_MEANING_MODALITIES)},
                        minimum=1,
                        maximum=4,
                    ),
                    "statement": _text_schema(500),
                    "source_refs": refs,
                }
            ),
            _object(
                {
                    "modalities": _array(
                        {"type": "string", "enum": list(SOURCE_MEANING_MODALITIES)},
                        minimum=1,
                        maximum=4,
                    ),
                    "statement": _text_schema(500),
                    "source_refs": refs,
                    "applies_to_dependency_index": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 63,
                    },
                    "attachment_source_refs": refs,
                }
            ),
        ]
    }
    return _object(
        {
            "version": {
                "type": "string",
                "enum": [SEMANTIC_SOURCE_MEANING_GRAPH_VERSION],
            },
            "presentation": {
                "anyOf": [
                    _object(
                        {
                            "title": _text_schema(200),
                            "status": {
                                "type": "string",
                                "enum": ["source_declared"],
                            },
                            "source_refs": refs,
                        }
                    ),
                    _object(
                        {
                            "title": _text_schema(200),
                            "status": {
                                "type": "string",
                                "enum": ["working_assumption"],
                            },
                            "source_refs": _array(source_ref, maximum=0),
                        }
                    ),
                ]
            },
            "audiences": _array(
                _object(
                    {
                        "kind": {
                            "type": "string",
                            "enum": list(SOURCE_MEANING_AUDIENCE_KINDS),
                        },
                        "label": _text_schema(200),
                        "source_refs": refs,
                    }
                ),
                maximum=64,
            ),
            "actors": _array(
                _object(
                    {
                        "canonical_label": _text_schema(200),
                        "source_refs": refs,
                    }
                ),
                maximum=64,
            ),
            "entities": _array(
                _object(
                    {
                        "label": _text_schema(300),
                        "source_refs": refs,
                    }
                ),
                maximum=64,
            ),
            "workflow": _array(
                _object(
                    {
                        "action": _text_schema(200),
                        workflow_effects_key: workflow_effects,
                        "owner_actor_index": {
                            "anyOf": [
                                {"type": "integer", "minimum": 0, "maximum": 63},
                                {"type": "null"},
                            ]
                        },
                        "source_refs": refs,
                    }
                ),
                minimum=1,
                maximum=64,
            ),
            "dependencies": _array(
                _object(
                    {
                        "label": _text_schema(300),
                        "access_mode": {
                            "type": "string",
                            "enum": ["read", "read_only", "unspecified"],
                        },
                        "source_refs": refs,
                    }
                ),
                maximum=64,
            ),
            "product_boundaries": _array(
                _object(
                    {
                        "statement": _text_schema(500),
                        "source_refs": refs,
                    }
                ),
                maximum=32,
            ),
            "policy_boundaries": _array(policy_boundary, maximum=32),
            "non_material_gaps": _array(
                _object({"statement": _text_schema(500), "source_refs": refs}),
                maximum=32,
            ),
            "provenance_only": _array(
                _object({"statement": _text_schema(500), "source_refs": refs}),
                maximum=32,
            ),
            "clarification": {
                "anyOf": [
                    _object(
                        {
                            "required": {"type": "boolean", "enum": [False]},
                            "question": {"type": "string", "enum": [""]},
                            "source_refs": _array(source_ref, maximum=0),
                        }
                    ),
                    _object(
                        {
                            "required": {"type": "boolean", "enum": [True]},
                            "question": _text_schema(600),
                            "source_refs": refs,
                        }
                    ),
                ]
            },
        }
    )


def semantic_source_meaning_provider_schema(
    evidence_catalog: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Return the provider schema using opaque exact-evidence handles."""

    return semantic_source_meaning_graph_schema(
        source_ref_schema=semantic_evidence_block_schema(evidence_catalog),
        _provider_effect_slots=True,
    )


def semantic_source_meaning_contract(
    evidence_catalog: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return canonical semantic ownership without a prompt-rule cascade."""

    contract: dict[str, Any] = {
        "version": SEMANTIC_SOURCE_MEANING_CONTRACT_VERSION,
        "objective": (
            "Author complete source-grounded product meaning as one typed graph. Preserve "
            "the whole source; do not infer meaning with keyword, token, or example matching."
        ),
        "semantic_ownership": {
            "audience_and_actors": (
                "Actors are explicit human roles or participants. canonical_label preserves the "
                "most specific source-declared role name; later shorthand or pronouns may resolve "
                "ownership through indexes but never replace or shorten that canonical identity. "
                "Owner indexes identify which "
                "actors own workflow; unowned source-declared roles remain source facts but never "
                "gain first-path responsibility. Audiences contains only separately explicit "
                "passive human or nonhuman recipients; never duplicate an actor. A human label mentioned only "
                "as the target of permitted, limited, required, or prohibited behavior is neither "
                "an actor nor an audience; actor citations must establish a product role, explicit "
                "participation, or workflow ownership. Runtime derives "
                "first-path participants from actor-owned workflow. If no actor "
                "owns the first path and no explicit audience exists, ask which role uses the "
                "product and owns or directs its first path. Resolve ordinary-language ownership "
                "continuity over the complete source: a subjectless continuation keeps the last "
                "explicit human owner only when the source meaning makes that continuation "
                "unambiguous. Ask about genuine ownership conflict; do not erase entailed ownership."
            ),
            "workflow_and_effects": (
                "Each workflow row is one ordered in-product action. Its action is the complete "
                "source-faithful human-readable action statement. Define each durable or observable "
                "thing once in the root entities table. entity_effect_slots has one row for each "
                "touched root entity, ordered by entity index. Each slot has one nullable field for "
                "each exact relationship between that action and the entity: input, target, created, "
                "changed, stable, or visible_result. Put every relationship for that entity in its "
                "one slot; never repeat an entity slot. Runtime binds those fields directly; it never "
                "reparses action text. The product container named only "
                "by the operator's build request belongs to presentation, not entities; include it "
                "as an entity only when the source separately uses it in an in-product action, "
                "state, or result. created records source-declared "
                "creation of a domain object or intermediate artifact without promoting it to a "
                "visible result. It never creates a dependency, policy, or observable result. "
                "A visible_result already means produced, so never add a parallel created effect. Nest each "
                "state change and observable output under the exact step that causes it. Parent action refs "
                "and child edge refs jointly establish the causal relation; each change and output "
                "references its canonical root entity. Dependency reads, "
                "policy behavior, terminal human observation, state persistence, and presentation "
                "choices are not workflow. Use a stable effect only when the source explicitly says "
                "an object remains in one state during that exact workflow action; stable_state is "
                "only the state value, without a verb or sentence punctuation. A global prohibition "
                "is policy, not a stable effect. Transition endpoints are not stable effects."
            ),
            "success": (
                "A produced output is a source-declared observable artifact or human-visible "
                "confirmation. Creating an intermediate object does not make it an observable "
                "result unless the source separately establishes that role; use created for that "
                "intermediate object and visible_result only for the visible result. When the source "
                "separately names multiple visible results, preserve each as its own produced "
                "entity; combine them only when the source declares one combined result. A transition, "
                "persistence statement, placement, or surface alone is not success. If no "
                "observable output exists, ask one focused result question. A visible_to recipient "
                "is optional and requires its own exact citation establishing that recipient edge; "
                "do not infer a viewer from an actor or output citation."
            ),
            "boundaries": (
                "Dependencies are external sources or systems declared as used, required, or "
                "available to the first path, including any source with a declared access mode "
                "or boundary. access_mode is the sole owner of generic read or read-only dependency "
                "access; do not duplicate it as policy. A restriction that merely names a class does not create a dependency. "
                "A class that the source permits naming but explicitly forbids accessing is a "
                "product or policy boundary, never a dependency. "
                "Product boundaries preserve source-declared product scope, execution location, "
                "deployment limits, and data locality without converting them into behavioral policy. "
                "Policy boundaries preserve source modality without inventing subtypes or relations. "
                "When a distinct boundary applies to one dependency, use its optional dependency "
                "attachment once rather than duplicating it inside the dependency. "
                "A thing mentioned only as a policy target is not a product entity; policy citations "
                "alone never create an entity, state, dependency, or workflow binding. "
                "Product form or identity is neither boundary class. Optional or unspecified "
                "presentation and ordering belong only in non_material_gaps."
            ),
            "presentation_and_provenance": (
                "Presentation is not product meaning. Use source_declared only when exact source "
                "refs declare the product title. Otherwise author one concise consumer-facing "
                "working_assumption title with no source refs. Do not copy a heading when it names "
                "the evidence document rather than the product. Retired, discarded, obsolete, superseded, or "
                "commentary-only evidence appears only in provenance_only and nowhere in product truth. "
                "A trial, test, brainstorm, scratch, or candidate name/label/phrase that the source "
                "explicitly excludes is likewise provenance-only; its exclusion is not a product policy."
            ),
            "clarification": (
                "Ask exactly one focused question only for a material conflict or missing owner, "
                "first path, observable result, boundary, dependency, proof, or safety fact. Cite the "
                "exact source bytes that establish the uncertainty. For an ownership conflict, ask directly which role owns the action "
                "and leave that owner unset; never ask whether role labels are the same."
            ),
        },
        "hard_laws": [
            "Every fact and relationship is semantically entailed by its exact citations.",
            "Do not invent or retype users, facts, causal edges, dependencies, or authority.",
            "Do not duplicate one proposition across incompatible semantic fields.",
        ],
    }
    if evidence_catalog is not None:
        contract["evidence"] = {
            key: {"quote": str(row["quote"]), "source_id": str(row["source_id"])}
            for key, row in evidence_catalog.items()
        }
    return contract


def _object(properties: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": dict(properties),
    }


def _array(
    items: Mapping[str, Any], *, minimum: int = 0, maximum: int | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "array", "minItems": minimum, "items": dict(items)}
    if maximum is not None:
        result["maxItems"] = maximum
    return result


def _nullable(schema: Mapping[str, Any]) -> dict[str, Any]:
    return {"anyOf": [{"type": "null"}, dict(schema)]}


def _text_schema(maximum: int) -> dict[str, Any]:
    return {"type": "string", "minLength": 1, "maxLength": maximum}


__all__ = [
    "SEMANTIC_SOURCE_MEANING_CONTRACT_VERSION",
    "SEMANTIC_SOURCE_MEANING_GRAPH_VERSION",
    "SOURCE_MEANING_AUDIENCE_KINDS",
    "SOURCE_MEANING_COLLECTIONS",
    "SOURCE_MEANING_ENTITY_EFFECT_KINDS",
    "SOURCE_MEANING_MODALITIES",
    "semantic_source_meaning_contract",
    "semantic_source_meaning_graph_schema",
    "semantic_source_meaning_provider_schema",
]
