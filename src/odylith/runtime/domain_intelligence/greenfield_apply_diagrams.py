"""Diagram previews and id allocation for confirmed greenfield prewrite gates."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.proposal_validation import validated_mermaid_source


def allocated_diagram_ids(
    repo_root: Path,
    count: int,
    rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[str]:
    """Allocate stable diagram ids while preserving existing catalog slug ids."""

    slug_ids = _catalog_diagram_ids_by_slug(repo_root)
    if rows is None:
        rows = ()
    first = int(_next_diagram_id(repo_root).split("-", 1)[1])
    next_number = first
    used = set(slug_ids.values())
    allocated: list[str] = []
    for index in range(max(0, count)):
        row = rows[index] if index < len(rows) else {}
        slug = str(row.get("slug", "")).strip() if isinstance(row, Mapping) else ""
        existing = slug_ids.get(slug)
        if existing:
            allocated.append(existing)
            continue
        while f"D-{next_number:03d}" in used:
            next_number += 1
        diagram_id = f"D-{next_number:03d}"
        used.add(diagram_id)
        allocated.append(diagram_id)
        next_number += 1
    return allocated


def render_prewrite_atlas_sources(proposal: Mapping[str, Any]) -> dict[str, str]:
    """Render Atlas Mermaid source files in memory for the completion gate."""

    sources: dict[str, str] = {}
    for row in proposal.get("diagrams", []):
        if not isinstance(row, Mapping):
            continue
        slug = str(row.get("slug", "")).strip() or slugify(str(row.get("title", "")).strip())
        if not slug:
            continue
        sources[f"odylith/atlas/source/{slug}.mmd"] = validated_mermaid_source(row).rstrip() + "\n"
    return sources


def _next_diagram_id(repo_root: Path) -> str:
    catalog = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    max_id = 0
    if catalog.is_file():
        try:
            payload = json.loads(catalog.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        for row in payload.get("diagrams", []) if isinstance(payload, Mapping) else []:
            match = re.fullmatch(r"D-(\d{3,})", str(row.get("diagram_id", "")).strip())
            if match:
                max_id = max(max_id, int(match.group(1)))
    return f"D-{max_id + 1:03d}"


def _catalog_diagram_ids_by_slug(repo_root: Path) -> dict[str, str]:
    catalog = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    if not catalog.is_file():
        return {}
    try:
        payload = json.loads(catalog.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    diagrams = payload.get("diagrams") if isinstance(payload, Mapping) else None
    if not isinstance(diagrams, list):
        return {}
    result: dict[str, str] = {}
    for row in diagrams:
        if not isinstance(row, Mapping):
            continue
        slug = str(row.get("slug", "")).strip()
        diagram_id = str(row.get("diagram_id", "")).strip()
        if slug and re.fullmatch(r"D-\d{3,}", diagram_id):
            result.setdefault(slug, diagram_id)
    return result


__all__ = [
    "allocated_diagram_ids",
    "render_prewrite_atlas_sources",
]
