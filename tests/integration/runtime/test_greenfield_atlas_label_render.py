"""Native Mermaid proof for literal Greenfield node and relationship labels."""

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_atlas_design_views import (
    mermaid_label,
)
from odylith.runtime.domain_intelligence.greenfield_authored_atlas_view import validate_authored_atlas_view
from odylith.runtime.surfaces.mermaid_worker_session import _MermaidWorkerSession
from tests.unit.runtime.test_greenfield_authored_atlas_view import (
    _authored_diagrams,
    _source_lifecycle,
    _provisional_design,
)


_LABELS = (
    "A sample's release-readiness proof is available for review.",
    'Review "accepted" and O’Connor’s sample.',
    'AT&T <required> > threshold',
    'Literal &amp; &#39; &#x27; #quot; #35; &lt;b&gt;',
    '<b>not bold</b> <br/> stays text',
    '<img src=x onerror=alert(1)>',
    '"]; injected["node"] --> target; %%',
    '`**not Markdown**` and \\ escape',
    '日本語 — café ♥ 50% / path | value',
)


def test_greenfield_labels_render_as_literal_text_without_injected_structure(tmp_path: Path) -> None:
    source = ["flowchart TD"]
    for index, value in enumerate(_LABELS):
        label = mermaid_label(value, width=512)
        source.extend([
            f'  n{index}["{label}"]',
            f'  n{index} -->|"{label}"| z{index}["end"]',
        ])
    mmd, svg, png = (tmp_path / f"literal-labels.{suffix}" for suffix in ("mmd", "svg", "png"))
    mmd.write_text("\n".join(source) + "\n", encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[3]
    with _MermaidWorkerSession(repo_root=repo_root, cli_version="11.12.0") as worker:
        worker.render_one(job={
            "diagram_id": "literal-labels",
            "source_mmd": str(mmd),
            "source_svg": str(svg),
            "source_png": str(png),
        }, timeout_seconds=30)
    root = ET.parse(svg).getroot()
    node_labels = [
        "".join(element.itertext()) for element in root.iter()
        if element.attrib.get("class") == "nodeLabel"
    ]
    edge_labels = [
        "".join(element.itertext()) for element in root.iter()
        if element.attrib.get("class") == "edgeLabel"
    ]
    assert node_labels == [label for value in _LABELS for label in (value, "end")]
    assert set(edge_labels) == set(_LABELS)
    assert sum("node" in element.attrib.get("class", "").split() for element in root.iter()) == 2 * len(_LABELS)
    assert sum("flowchart-link" in element.attrib.get("class", "").split() for element in root.iter()) == len(_LABELS)
    for element in root.iter():
        assert element.tag.rsplit("}", 1)[-1] not in {"script", "img", "b", "a"}
        assert not any(key.casefold().startswith("on") for key in element.attrib)
    assert png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_capability_support_groups_render_complete_local_relationships(tmp_path: Path) -> None:
    row = _authored_diagrams()[-1]
    assert row["authority_kind"] == "provisional_design"
    mmd, svg, png = (tmp_path / f"support.{suffix}" for suffix in ("mmd", "svg", "png"))
    mmd.write_text(row["mermaid_source"], encoding="utf-8")
    with _MermaidWorkerSession(repo_root=Path(__file__).resolve().parents[3], cli_version="11.12.0") as worker:
        worker.render_one(job={
            "diagram_id": "support", "source_mmd": str(mmd),
            "source_svg": str(svg), "source_png": str(png),
        }, timeout_seconds=30)
    root = ET.parse(svg).getroot()
    labels = [
        " ".join(" ".join(element.itertext()).split()) for element in root.iter()
        if element.attrib.get("class") == "nodeLabel"
    ]
    design = _provisional_design()
    boxes = {box["node_id"]: box for box in row["diagram_boxes"]}
    for index, component in enumerate(design["components"], 1):
        actions = ", ".join(map(str, component["supported_event_orders"]))
        assert labels.count(
            f"Proposed: {component['name']} Source actions: {actions} "
            "Select for responsibility and check"
        ) == 1
        detail = boxes[f"component{index}"]["description"]
        assert f"Proposed responsibility: {component['responsibility']}" in detail
        assert f"Proposed boundary verification: {component['verification']}" in detail
    for index, workstream in enumerate(design["workstreams"], 1):
        assert labels.count(f"Proposed delivery {workstream['title']} Select for acceptance") == 1
        detail = boxes[f"workstream{index}_acceptance"]["description"]
        assert f"Proposed deliverable: {workstream['deliverable']}" in detail
        assert f"Proposed verification: {workstream['verification']}" in detail
    assert labels.count("Source action reference Select for full actions and performers") == 1
    for order, event in enumerate((
        "Dock attendant Ivo enters a vessel tag",
        "the product records berth occupancy",
        "the berth map shows the placement",
    ), 1):
        assert boxes["source_actions"]["description"].count(f"Source event: {event}") == 1
        assert f"Source action {order} · " in boxes["source_actions"]["description"]
    assert len(labels) == 10
    edges = [element for element in root.iter() if "flowchart-link" in element.attrib.get("class", "").split()]
    assert len(edges) == 4
    assert {element.attrib["data-id"].rsplit("_", 1)[0] for element in edges} == {
        f"L_component{index}_workstream{index}_acceptance" for index in range(1, 5)
    }
    assert validate_authored_atlas_view(row, source_text=mmd.read_text())["diagram_boxes"] == row["diagram_boxes"]
    png_bytes = png.read_bytes()
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    # The compact support view must retain at least 80% of the native 15px font.
    assert int.from_bytes(png_bytes[16:20], "big") / float(root.attrib["viewBox"].split()[2]) >= 0.8


@pytest.mark.parametrize("shared_field", [False, True])
def test_cited_passive_lifecycle_renders_trigger_and_both_field_effects(
    tmp_path: Path, shared_field: bool,
) -> None:
    lifecycle = _source_lifecycle()
    if shared_field:
        lifecycle["off_path_transitions"][0]["source_refs"] = [{
            "quote": "Withdrawal removes the record from future cached aggregates and invalidates affected unpublished cached analysis.",
            "occurrence": 1,
        }]
        lifecycle["off_path_transitions"][0]["effects"] = [
            {
                "state_field_id": "F2", "field": "cache",
                "change": "Remove the withdrawn record from future cached aggregates.",
                "observable_check": "New aggregates exclude the withdrawn record.",
            },
            {
                "state_field_id": "F2", "field": "cache",
                "change": "Invalidate affected unpublished cached analysis.",
                "observable_check": "Affected unpublished analysis cannot be released.",
            },
        ]
    row = _authored_diagrams(source_lifecycle=lifecycle)[-1]
    assert row["authority_kind"] == "provisional_design"
    mmd, svg, png = (tmp_path / f"lifecycle.{suffix}" for suffix in ("mmd", "svg", "png"))
    mmd.write_text(row["mermaid_source"], encoding="utf-8")
    with _MermaidWorkerSession(repo_root=Path(__file__).resolve().parents[3], cli_version="11.12.0") as worker:
        worker.render_one(job={
            "diagram_id": "lifecycle", "source_mmd": str(mmd),
            "source_svg": str(svg), "source_png": str(png),
        }, timeout_seconds=30)
    root = ET.parse(svg).getroot()
    labels = {
        " ".join(" ".join(element.itertext()).split()) for element in root.iter()
        if element.attrib.get("class") in {"nodeLabel", "edgeLabel"}
    }
    boxes = {box["node_id"]: box for box in row["diagram_boxes"]}
    assert "Off-path state transition berth occupancy · withdrawal Select for source detail" in labels
    for citation in lifecycle["off_path_transitions"][0]["source_refs"]:
        assert citation["quote"] in boxes["off_path_transition1"]["description"]
    expected_edges = {
        f"L_component{index}_workstream{index}_acceptance" for index in range(1, 5)
    } | {"L_component2_off_path_transition1"}
    field_nodes = {field["duty_id"]: f"state_field{index}" for index, field in enumerate(lifecycle["state_fields"], 1)}
    for index, effect in enumerate(lifecycle["off_path_transitions"][0]["effects"], 1):
        node = f"off_path_transition1_effect{index}"
        assert f"Effect 1.{index} {effect['change']}" in labels
        assert f"changes {effect['field']}" in labels
        assert f"Change: {effect['change']}\nObservable check: {effect['observable_check']}" in boxes[node]["description"]
        expected_edges.add(f"L_off_path_transition1_{node}")
        expected_edges.add(f"L_{node}_{field_nodes[effect['state_field_id']]}")
    edges = [element for element in root.iter() if "flowchart-link" in element.attrib.get("class", "").split()]
    assert len(edges) == 9
    assert {element.attrib["data-id"].rsplit("_", 1)[0] for element in edges} == expected_edges
    assert validate_authored_atlas_view(row, source_text=mmd.read_text())["diagram_boxes"] == row["diagram_boxes"]
    png_bytes = png.read_bytes()
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert int.from_bytes(png_bytes[16:20], "big") / float(root.attrib["viewBox"].split()[2]) >= 0.8
