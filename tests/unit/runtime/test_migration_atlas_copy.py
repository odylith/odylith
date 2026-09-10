"""Migration architecture explanations must be authored for every visible box."""

import json
from pathlib import Path

from odylith.runtime.surfaces import atlas_box_explanations as boxes


def test_migration_diagram_has_complete_exact_authored_box_coverage() -> None:
    repo = Path(__file__).resolve().parents[3]
    payload = json.loads((repo / "odylith/atlas/source/catalog/diagrams.v1.json").read_text())
    diagram = next(row for row in payload["diagrams"] if row["diagram_id"] == "D-042")
    source = (repo / diagram["source_mmd"]).read_text()
    errors = []
    authored = boxes.normalize_catalog_diagram_boxes(
        raw_boxes=diagram["diagram_boxes"], context="D-042", errors=errors,
    )
    assert errors == []
    visible = boxes.extract_diagram_boxes_from_mermaid(source)
    authored_labels = boxes.diagram_box_labels(row.as_dict() for row in authored)
    visible_labels = boxes.diagram_box_labels(row.as_dict() for row in visible)
    assert set(authored_labels) == set(visible_labels), {
        "missing": sorted(set(visible_labels) - set(authored_labels)),
        "orphaned": sorted(set(authored_labels) - set(visible_labels)),
    }
    merged = boxes.merge_diagram_box_explanations(source_text=source, catalog_boxes=authored)
    assert len(merged) == len(visible) == len(authored)
    assert {row["label"]: row["description"] for row in merged} == {
        row.label: row.description for row in authored
    }
