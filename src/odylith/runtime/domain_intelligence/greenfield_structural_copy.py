"""Shared structural-field boundary for greenfield generated-copy checks."""

from __future__ import annotations


STRUCTURAL_COPY_KEYS = frozenset(
    {
        "accepted_project",
        "category",
        "anchor",
        "anchors",
        "artifact",
        "artifacts",
        "backlog_index",
        "catalog",
        "checksum",
        "component",
        "component_focus",
        "component_id",
        "component_ids",
        "component_sequence",
        "components",
        "created",
        "date",
        "diagram",
        "diagram_id",
        "diagram_ids",
        "diagrams",
        "fingerprint",
        "fingerprints",
        "hash",
        "href",
        "id",
        "ids",
        "key",
        "kind",
        "origin",
        "owner",
        "path",
        "path_prefixes",
        "paths",
        "product_layer",
        "project_brief",
        "qualification",
        "release",
        "release_id",
        "release_selector",
        "repo_name",
        "repo_root",
        "registry_path",
        "route",
        "schema_version",
        "selector",
        "semantic_axis",
        "sha",
        "slug",
        "slugs",
        "source",
        "source_mmd",
        "source_path",
        "source_png",
        "source_svg",
        "sources",
        "spec_path",
        "spec_ref",
        "status",
        "stream",
        "target_path",
        "uri",
        "url",
        "validation_gate",
        "version",
        "workstream",
        "workstreams",
    }
)
STRUCTURAL_COPY_KEY_SUFFIXES = (
    "_id",
    "_ids",
    "_path",
    "_paths",
    "_fingerprint",
    "_fingerprints",
    "_hash",
    "_href",
    "_slug",
    "_slugs",
    "_route",
    "_sha",
    "_uri",
    "_uris",
    "_url",
    "_urls",
    "_version",
    "_selector",
)


def structural_copy_value(*, key: str, value: str) -> bool:
    """Return whether a value is machine custody rather than public prose."""

    field = str(key or "").strip().casefold()
    if field in STRUCTURAL_COPY_KEYS or field.endswith(STRUCTURAL_COPY_KEY_SUFFIXES):
        return True
    text = str(value or "").strip()
    if not text:
        return False
    return bool("://" in text and not any(char.isspace() for char in text))


__all__ = ["STRUCTURAL_COPY_KEYS", "STRUCTURAL_COPY_KEY_SUFFIXES", "structural_copy_value"]
