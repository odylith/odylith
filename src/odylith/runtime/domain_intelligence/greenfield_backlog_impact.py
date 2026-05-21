"""Derive product-facing Radar impact metadata for greenfield workstreams."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_experience import row_text_tuple
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


_INTERNAL_SURFACE_TOKENS = frozenset(
    {
        "app",
        "apps",
        "application",
        "applications",
        "atlas",
        "backlog",
        "casebook",
        "component-registry",
        "governance",
        "governed-records",
        "odylith",
        "project-records",
        "radar",
        "registry",
        "release-plan",
        "surface",
        "surfaces",
    }
)


def derive_greenfield_impacted_parts(row: Mapping[str, Any], proposal: Mapping[str, Any]) -> str:
    """Return product boundary labels for Radar ``impacted_parts`` metadata."""

    explicit = _clean_impact_values(_impact_values(row.get("impacted_parts")))
    if explicit:
        return _join_labels(explicit)

    component_rows = _component_rows(proposal)
    lookup = _component_lookup(component_rows)
    labels: list[str] = []
    for key in ("component_focus", "related_components", "component_ids", "components"):
        labels.extend(_labels_for_references(row_text_tuple(row, key), lookup=lookup))
    if not labels:
        labels.extend(_labels_for_workstream(row=row, components=component_rows))
    if not labels and _is_first_backlog_row(row=row, proposal=proposal):
        labels.extend(_component_label(component) for component in component_rows)
    if not labels:
        labels.append(_title_boundary_label(row.get("title")))
    return _join_labels(labels) or "Accepted first-path product boundary"


def _component_rows(proposal: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    return tuple(row for row in proposal.get("components", []) if isinstance(row, Mapping))


def _component_lookup(components: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    lookup: dict[str, Mapping[str, Any]] = {}
    for component in components:
        for key in ("component_id", "id", "label", "name", "slug"):
            token = slugify(str(component.get(key) or ""))
            if token:
                lookup.setdefault(token, component)
    return lookup


def _labels_for_references(
    values: Sequence[str],
    *,
    lookup: Mapping[str, Mapping[str, Any]],
) -> tuple[str, ...]:
    labels: list[str] = []
    for value in values:
        text = _readable_label(value)
        if not text:
            continue
        component = lookup.get(slugify(text))
        labels.append(_component_label(component) if component else text)
    return unique_text(label for label in labels if label)


def _labels_for_workstream(
    *,
    row: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    title = slugify(str(row.get("title") or ""))
    if not title:
        return ()
    labels: list[str] = []
    for component in components:
        workstream_titles = row_text_tuple(
            component,
            "workstream_titles",
            "workstreams",
            "related_workstream_titles",
        )
        if any(slugify(value) == title for value in workstream_titles):
            labels.append(_component_label(component))
    return unique_text(label for label in labels if label)


def _component_label(component: Mapping[str, Any]) -> str:
    for key in ("label", "name", "component_id", "id", "slug"):
        text = _readable_label(component.get(key))
        if text:
            return text
    return ""


def _is_first_backlog_row(*, row: Mapping[str, Any], proposal: Mapping[str, Any]) -> bool:
    rows = [item for item in proposal.get("backlog", []) if isinstance(item, Mapping)]
    if not rows:
        return False
    title = slugify(str(row.get("title") or ""))
    first_title = slugify(str(rows[0].get("title") or ""))
    return bool(title and title == first_title)


def _title_boundary_label(value: Any) -> str:
    text = _readable_label(value)
    text = re.sub(r"^(Govern|Define|Build|Create|Implement)\s+", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\s+boundary$", " boundary", text, flags=re.IGNORECASE).strip()
    return _readable_label(text)


def _impact_values(value: Any) -> tuple[str, ...]:
    if isinstance(value, Mapping):
        return tuple(part for nested in value.values() for part in _impact_values(nested))
    if isinstance(value, str):
        return tuple(part.strip() for part in re.split(r"[,;\n|]+", value) if part.strip())
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return tuple(part for nested in value for part in _impact_values(nested))
    text = str(value or "").strip()
    return (text,) if text else ()


def _clean_impact_values(values: Sequence[str]) -> tuple[str, ...]:
    return unique_text(label for value in values if (label := _readable_label(value)))


def _readable_label(value: Any) -> str:
    text = " ".join(str(value or "").replace("_", " ").split()).strip(" ,.;:")
    if not text:
        return ""
    if slugify(text) in _INTERNAL_SURFACE_TOKENS:
        return ""
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", text):
        text = " ".join(part[:1].upper() + part[1:] for part in text.split("-") if part)
    return text


def _join_labels(values: Sequence[str]) -> str:
    return ", ".join(unique_text(_clean_impact_values(values)))
