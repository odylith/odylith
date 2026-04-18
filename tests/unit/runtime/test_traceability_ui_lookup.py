"""Coverage for Radar/Atlas tooltip lookup payload helpers."""

from __future__ import annotations

from odylith.runtime.governance import traceability_ui_lookup as lookup


def test_build_workstream_title_lookup_merges_entries_and_graph() -> None:
    entries = [
        {"idea_id": "B-002", "title": "Entry Title"},
        {"idea_id": "invalid", "title": "Ignored"},
    ]
    traceability_graph = {
        "workstreams": [
            {"idea_id": "B-001", "title": "Graph Title"},
            {"idea_id": "B-002", "title": "Graph Override"},
        ]
    }

    result = lookup.build_workstream_title_lookup(
        entries=entries,
        traceability_graph=traceability_graph,
    )

    assert result == {
        "B-001": "Graph Title",
        "B-002": "Graph Override",
    }


def test_build_diagram_title_lookup_normalizes_prefixed_ids() -> None:
    diagrams = [
        {"diagram_id": "D-001", "title": "Catalog Diagram"},
        {"diagram_id": "invalid", "title": "Ignored"},
    ]
    traceability_graph = {
        "diagrams": [
            {"diagram_id": "diagram:D-002", "title": "Graph Diagram"},
            {"diagram_id": "diagram:invalid", "title": "Ignored"},
        ],
        "nodes": [
            {"type": "diagram", "id": "diagram:D-003", "label": "Node Diagram"},
            {"type": "artifact", "id": "artifact:x", "label": "Ignore"},
        ],
    }

    result = lookup.build_diagram_title_lookup(
        diagrams=diagrams,
        traceability_graph=traceability_graph,
    )

    assert result == {
        "D-001": "Catalog Diagram",
        "D-002": "Graph Diagram",
        "D-003": "Node Diagram",
    }


def test_normalize_identifiers() -> None:
    assert lookup.normalize_workstream_id("B-123") == "B-123"
    assert lookup.normalize_workstream_id("B-12A") == ""
    assert lookup.normalize_diagram_id("diagram:D-004") == "D-004"
    assert lookup.normalize_diagram_id("D-004") == "D-004"
    assert lookup.normalize_diagram_id("diagram:abc") == ""
    assert lookup.normalize_component_id("Compass") == "compass"
    assert lookup.normalize_component_id("invalid token!") == ""


def test_build_tooltip_lookup_payload_combines_maps() -> None:
    payload = lookup.build_tooltip_lookup_payload(
        entries=[{"idea_id": "B-101", "title": "Workstream 101"}],
        diagrams=[{"diagram_id": "D-101", "title": "Diagram 101"}],
        components=[{"component_id": "compass", "name": "Compass"}],
        traceability_graph={},
    )

    assert payload == {
        "workstream_titles": {"B-101": "Workstream 101"},
        "diagram_titles": {"D-101": "Diagram 101"},
        "component_titles": {"compass": "Compass"},
        "diagram_related_workstreams": {},
    }
