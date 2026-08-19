"""Shared JSON-schema primitives for Greenfield semantic authoring contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any


def object_schema(
    required: Sequence[str], properties: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(required),
        "properties": dict(properties),
    }


def array_schema(
    item: Mapping[str, Any], *, minimum: int = 0, maximum: int = 64
) -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": minimum,
        "maxItems": maximum,
        "items": dict(item),
    }


def string_schema(maximum: int) -> dict[str, Any]:
    return {"type": "string", "minLength": 1, "maxLength": maximum}


def inline_local_refs(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Inline one schema's local definitions before embedding it in another schema."""

    root = deepcopy(dict(schema))
    definitions = dict(root.pop("$defs", {}))

    def expand(value: Any) -> Any:
        if isinstance(value, Mapping):
            if set(value) == {"$ref"}:
                prefix = "#/$defs/"
                reference = str(value["$ref"])
                if not reference.startswith(prefix) or reference[len(prefix):] not in definitions:
                    raise ValueError("Semantic authoring schema has an unsupported reference")
                return expand(deepcopy(definitions[reference[len(prefix):]]))
            return {key: expand(item) for key, item in value.items()}
        if isinstance(value, list):
            return [expand(item) for item in value]
        return value

    return expand(root)


__all__ = ["array_schema", "inline_local_refs", "object_schema", "string_schema"]
