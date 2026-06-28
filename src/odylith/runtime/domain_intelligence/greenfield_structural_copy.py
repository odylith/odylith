"""Shared structural-field boundary for greenfield generated-copy checks."""

from __future__ import annotations


STRUCTURAL_COPY_KEYS = frozenset(
    {
        "category",
        "component",
        "component_id",
        "components",
        "created",
        "date",
        "diagrams",
        "href",
        "id",
        "kind",
        "origin",
        "owner",
        "path",
        "paths",
        "product_layer",
        "qualification",
        "release",
        "schema_version",
        "semantic_axis",
        "slug",
        "slugs",
        "source",
        "sources",
        "status",
        "uri",
        "url",
        "version",
        "workstreams",
    }
)
STRUCTURAL_COPY_KEY_SUFFIXES = (
    "_id",
    "_ids",
    "_path",
    "_paths",
    "_slug",
    "_slugs",
    "_uri",
    "_uris",
    "_url",
    "_urls",
    "_version",
)


def structural_copy_value(*, key: str, value: str) -> bool:
    """Return whether a value is machine custody rather than public prose."""

    field = str(key or "").strip().casefold()
    if field in STRUCTURAL_COPY_KEYS or field.endswith(STRUCTURAL_COPY_KEY_SUFFIXES):
        return True
    text = str(value or "").strip()
    if not text:
        return False
    return bool(("://" in text or "/" in text) and not any(char.isspace() for char in text))


__all__ = ["STRUCTURAL_COPY_KEYS", "STRUCTURAL_COPY_KEY_SUFFIXES", "structural_copy_value"]
