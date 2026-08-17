"""Parser-free Atlas materialization for verified Semantic Intent graphs."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.common import diagram_freshness
from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.surfaces import generated_flowchart_assets


def semantic_catalog_entry(
    *,
    diagram_id: str,
    slug: str,
    title: str,
    kind: str,
    owner: str,
    summary: str,
    read_guide: str,
    components: Sequence[Mapping[str, Any]],
    related_backlog: Sequence[str],
    watch_paths: Sequence[str],
    review_date: str,
    diagram_boxes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build one exact v7 Atlas row from typed graph projections."""

    if not read_guide:
        raise ValueError(f"verified semantic diagram `{slug}` lacks its typed read guide")
    source_mmd = f"odylith/atlas/source/{slug}.mmd"
    return {
        "diagram_id": diagram_id,
        "slug": slug,
        "title": title,
        "kind": kind,
        "status": "draft",
        "owner": owner,
        "last_reviewed_utc": review_date,
        "source_mmd": source_mmd,
        "source_svg": f"odylith/atlas/source/{slug}.svg",
        "source_png": f"odylith/atlas/source/{slug}.png",
        "change_watch_paths": dedupe_strings(watch_paths) or [source_mmd],
        "summary": summary,
        "read_guide": read_guide,
        "projection_origin": "verified_semantic_intent_graph",
        "diagram_boxes": semantic_diagram_boxes(diagram_boxes, slug=slug),
        "components": [dict(row) for row in components],
        "related_backlog": dedupe_strings(related_backlog),
        "related_plans": [],
        "related_docs": [],
        "related_code": [],
        "link_state": "atlas_first_draft",
    }


def semantic_diagram_boxes(
    rows: Sequence[Mapping[str, Any]], *, slug: str
) -> list[dict[str, str]]:
    """Validate and copy the graph-authored box explanations without interpretation."""

    boxes: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) != {"label", "role", "description"}:
            raise ValueError(f"verified semantic diagram `{slug}` box {index} has an invalid shape")
        box = {
            key: " ".join(str(row.get(key) or "").split())
            for key in ("label", "role", "description")
        }
        if not all(box.values()):
            raise ValueError(f"verified semantic diagram `{slug}` box {index} is incomplete")
        boxes.append(box)
    if not boxes:
        raise ValueError(f"verified semantic diagram `{slug}` lacks typed diagram boxes")
    if len({box["label"].casefold() for box in boxes}) != len(boxes):
        raise ValueError(f"verified semantic diagram `{slug}` has duplicate typed box labels")
    return boxes


def render_verified_semantic_diagram_assets(
    *, root: Path, rows: Sequence[Mapping[str, Any]]
) -> None:
    """Render typed flowcharts and bind their exact source/watch fingerprints."""

    for row in rows:
        rendered = generated_flowchart_assets.render_generated_flowchart_assets(
            repo_root=root,
            source_mmd=str(row.get("source_mmd") or ""),
            source_svg=str(row.get("source_svg") or ""),
            source_png=str(row.get("source_png") or ""),
        )
        if not rendered:
            raise RuntimeError(
                "verified semantic Atlas source is outside the graph-native flowchart renderer"
            )
    _record_render_fingerprints(root=root, rows=rows)


def _record_render_fingerprints(*, root: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    catalog_path = root / "odylith/atlas/source/catalog/diagrams.v1.json"
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("verified semantic Atlas catalog is unreadable") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("diagrams"), list):
        raise RuntimeError("verified semantic Atlas catalog is missing after materialization")
    by_id = {
        str(row.get("diagram_id") or "").strip(): row
        for row in payload["diagrams"]
        if isinstance(row, dict)
    }
    fingerprints = diagram_freshness.ContentFingerprintCache()
    for source_row in rows:
        diagram_id = str(source_row.get("diagram_id") or "").strip()
        catalog_row = by_id.get(diagram_id)
        if not isinstance(catalog_row, dict):
            raise RuntimeError(f"verified semantic Atlas catalog lost `{diagram_id}`")
        source_mmd = str(catalog_row.get("source_mmd") or "").strip()
        watch_paths = [
            str(value).strip()
            for value in catalog_row.get("change_watch_paths", ())
            if str(value).strip()
        ]
        catalog_row["render_source_fingerprint"] = fingerprints.mermaid_render_fingerprint(
            root / source_mmd
        )
        catalog_row["reviewed_watch_fingerprints"] = diagram_freshness.watched_path_fingerprints(
            repo_root=root,
            watched_paths=watch_paths,
            cache=fingerprints,
        )
    catalog_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
