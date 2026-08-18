"""Present typed and legacy Atlas catalog entries without mixing their authorities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from odylith.runtime.surfaces import display_text


SEMANTIC_PROJECTION_ORIGIN = "verified_semantic_intent_graph"
_DIAGRAM_BOX_FIELDS = ("label", "role", "description")


@dataclass(frozen=True)
class CatalogEntryPresentation:
    """Validated presentation inputs for one Atlas catalog entry."""

    semantic_projection: bool
    catalog_diagram_boxes: tuple[Any, ...]


def presentation_text(value: Any) -> str:
    """Return operator-visible text with inline Markdown emphasis removed."""

    return display_text.strip_inline_markdown_emphasis(value)


def catalog_entry_presentation(
    item: Mapping[str, Any],
    *,
    context: str,
    errors: list[str],
) -> CatalogEntryPresentation:
    """Validate the entry's diagram-box contract at its declared authority boundary."""

    semantic_projection = item.get("projection_origin") == SEMANTIC_PROJECTION_ORIGIN
    if semantic_projection:
        boxes = _semantic_diagram_boxes(item.get("diagram_boxes"), context=context, errors=errors)
    else:
        from odylith.runtime.surfaces import atlas_box_explanations

        boxes = atlas_box_explanations.normalize_catalog_diagram_boxes(
            raw_boxes=item.get("diagram_boxes", []),
            context=context,
            errors=errors,
        )
    return CatalogEntryPresentation(
        semantic_projection=semantic_projection,
        catalog_diagram_boxes=tuple(boxes),
    )


def component_description(
    presentation: CatalogEntryPresentation,
    *,
    name: str,
    description: Any,
) -> str:
    """Preserve typed semantic descriptions and sanitize only legacy inferred copy."""

    description_text = presentation_text(description)
    if presentation.semantic_projection:
        return description_text

    from odylith.runtime.surfaces import atlas_box_explanations

    return atlas_box_explanations.clean_component_description(
        name=name,
        description=description_text,
    )


def diagram_presentation(
    presentation: CatalogEntryPresentation,
    *,
    components: Sequence[Mapping[str, Any]],
    title: str,
    kind: str,
    summary: str,
    read_guide: str,
    source_text: str,
) -> tuple[list[dict[str, Any]], str, str]:
    """Render entry copy without reinterpreting graph-native semantic projections."""

    if presentation.semantic_projection:
        return _display_rows(presentation.catalog_diagram_boxes), summary, read_guide

    from odylith.runtime.surfaces import atlas_box_explanations
    from odylith.runtime.surfaces import atlas_diagram_intelligence

    boxes = atlas_box_explanations.merge_diagram_box_explanations(
        source_text=source_text,
        catalog_boxes=presentation.catalog_diagram_boxes,
        component_rows=components,
        diagram_title=title,
        diagram_summary=summary,
    )
    narrative = atlas_diagram_intelligence.build_diagram_narrative(
        title=title,
        kind=kind,
        summary=summary,
        read_guide=read_guide,
        source_text=source_text,
    )
    return (
        _display_rows(boxes),
        presentation_text(narrative.summary),
        presentation_text(narrative.read_guide),
    )


def _semantic_diagram_boxes(
    value: Any,
    *,
    context: str,
    errors: list[str],
) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        errors.append(f"{context}: verified semantic `diagram_boxes` must be a non-empty list")
        return []
    boxes: list[dict[str, str]] = []
    for index, row in enumerate(value):
        if not isinstance(row, Mapping) or set(row) != set(_DIAGRAM_BOX_FIELDS):
            errors.append(f"{context}: diagram_boxes[{index}] must contain label, role, and description")
            continue
        box = {key: presentation_text(row.get(key, "")) for key in _DIAGRAM_BOX_FIELDS}
        if not all(box.values()):
            errors.append(f"{context}: diagram_boxes[{index}] contains an empty field")
            continue
        boxes.append(box)
    return boxes


def _display_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **dict(row),
            **{field: presentation_text(row.get(field, "")) for field in _DIAGRAM_BOX_FIELDS if field in row},
        }
        for row in rows
        if isinstance(row, Mapping)
    ]


__all__ = [
    "CatalogEntryPresentation",
    "catalog_entry_presentation",
    "component_description",
    "diagram_presentation",
    "presentation_text",
]
