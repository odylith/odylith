"""Provider-compatible structured-output schema for Greenfield Semantic Intent."""

from __future__ import annotations

from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    FACT_OWNER_KINDS,
    INTERNAL_SYSTEM_COMPONENT_KINDS,
    INTERNAL_SYSTEM_RELEASE_SCOPES,
    SEMANTIC_ATTRIBUTE_NAMES,
    SEMANTIC_CLARIFICATION_FIELDS,
    SEMANTIC_FACT_KINDS,
    SEMANTIC_NARRATIVE_FIELDS,
    SEMANTIC_RELATION_KINDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_IR_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    semantic_source_ref_schema,
)


_SYSTEM_ATTRIBUTE_NAMES = frozenset({"component_kind", "release_scope"})


def semantic_intent_output_schema(
    *, source_ref_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the exact schema accepted by the structured-output provider lane."""

    source_ref = source_ref_schema or semantic_source_ref_schema()
    source_refs = _source_refs(source_ref, minimum=1)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "version",
            "status",
            "clarification",
            "facts",
            "relations",
            "narratives",
        ],
        "properties": {
            "version": {"type": "string", "enum": [SEMANTIC_INTENT_IR_VERSION]},
            "status": {
                "type": "string",
                "enum": ["complete", "clarification_required"],
            },
            "clarification": _clarification_schema(source_ref),
            "facts": {
                "type": "array",
                "maxItems": 128,
                "items": {
                    "anyOf": [
                        _fact_schema(kind=kind, source_refs=source_refs)
                        for kind in SEMANTIC_FACT_KINDS
                    ]
                },
            },
            "relations": {
                "type": "array",
                "maxItems": 256,
                "items": _relation_schema(source_refs),
            },
            "narratives": {
                "type": "array",
                "maxItems": 64,
                "items": _narrative_schema(source_refs),
            },
        },
    }


def _clarification_schema(source_ref: dict[str, Any]) -> dict[str, Any]:
    return {
        "anyOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["question", "fields", "source_refs"],
                "properties": {
                    "question": {"type": "string", "enum": [""]},
                    "fields": {
                        "type": "array",
                        "maxItems": 0,
                        "items": _clarification_field(),
                    },
                    "source_refs": _source_refs(source_ref, maximum=0),
                },
            },
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["question", "fields", "source_refs"],
                "properties": {
                    "question": {"type": "string", "minLength": 1, "maxLength": 600},
                    "fields": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 3,
                        "items": _clarification_field(),
                    },
                    "source_refs": _source_refs(source_ref, minimum=1),
                },
            },
        ]
    }


def _clarification_field() -> dict[str, Any]:
    return {"type": "string", "enum": list(SEMANTIC_CLARIFICATION_FIELDS)}


def _fact_schema(*, kind: str, source_refs: dict[str, Any]) -> dict[str, Any]:
    required = [
        "fact_id",
        "kind",
        "label",
        "statement",
        "order",
        "owner_kind",
        "custody",
        "attributes",
        "source_refs",
    ]
    if kind == "state_object":
        required.append("transition")
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": {
            "fact_id": {"type": "string", "minLength": 1, "maxLength": 100},
            "kind": {"type": "string", "enum": [kind]},
            "label": {"type": "string", "minLength": 1, "maxLength": 300},
            "statement": {"type": "string", "minLength": 1, "maxLength": 1600},
            "order": {"type": "integer", "minimum": 0},
            "owner_kind": {"type": "string", "enum": list(FACT_OWNER_KINDS[kind])},
            "custody": {
                "type": "string",
                "enum": ["source_fact", "bounded_interpretation", "visible_assumption"],
            },
            "attributes": {
                "type": "array",
                "maxItems": 12,
                "items": {"anyOf": _attribute_variants(kind)},
            },
            **(
                {"transition": _state_transition_schema()}
                if kind == "state_object"
                else {}
            ),
            "source_refs": source_refs,
        },
    }


def _attribute_variants(kind: str) -> list[dict[str, Any]]:
    generic_names = set(SEMANTIC_ATTRIBUTE_NAMES) - _SYSTEM_ATTRIBUTE_NAMES
    variants = [_attribute_schema(names=sorted(generic_names))]
    if kind == "internal_system":
        variants.extend(
            [
                _attribute_schema(
                    names=["component_kind"], values=INTERNAL_SYSTEM_COMPONENT_KINDS
                ),
                _attribute_schema(
                    names=["release_scope"], values=INTERNAL_SYSTEM_RELEASE_SCOPES
                ),
            ]
        )
    return variants


def _state_transition_schema() -> dict[str, Any]:
    value = {"type": "string", "minLength": 1, "maxLength": 800}
    return {
        "anyOf": [
            {"type": "null"},
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["from_state", "to_state"],
                "properties": {
                    "from_state": dict(value),
                    "to_state": dict(value),
                },
            },
        ]
    }


def _attribute_schema(
    *, names: list[str], values: tuple[str, ...] | None = None
) -> dict[str, Any]:
    value_schema: dict[str, Any] = (
        {"type": "string", "enum": list(values)}
        if values is not None
        else {"type": "string", "minLength": 1, "maxLength": 800}
    )
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["name", "value"],
        "properties": {
            "name": {"type": "string", "enum": names},
            "value": value_schema,
        },
    }


def _relation_schema(source_refs: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "relation_id",
            "kind",
            "subject_id",
            "object_id",
            "order",
            "source_refs",
        ],
        "properties": {
            "relation_id": {"type": "string", "minLength": 1, "maxLength": 100},
            "kind": {"type": "string", "enum": list(SEMANTIC_RELATION_KINDS)},
            "subject_id": {"type": "string", "minLength": 1, "maxLength": 100},
            "object_id": {"type": "string", "minLength": 1, "maxLength": 100},
            "order": {"type": "integer", "minimum": 0},
            "source_refs": source_refs,
        },
    }


def _narrative_schema(source_refs: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["field", "order", "text", "fact_ids", "source_refs"],
        "properties": {
            "field": {"type": "string", "enum": list(SEMANTIC_NARRATIVE_FIELDS)},
            "order": {"type": "integer", "minimum": 0},
            "text": {"type": "string", "minLength": 1, "maxLength": 1600},
            "fact_ids": {
                "type": "array",
                "minItems": 1,
                "maxItems": 32,
                "items": {"type": "string", "minLength": 1, "maxLength": 100},
            },
            "source_refs": source_refs,
        },
    }


def _source_refs(
    source_ref: dict[str, Any], *, minimum: int | None = None, maximum: int = 8
) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "array",
        "maxItems": maximum,
        "items": source_ref,
    }
    if minimum is not None:
        schema["minItems"] = minimum
    return schema


__all__ = ["semantic_intent_output_schema"]
