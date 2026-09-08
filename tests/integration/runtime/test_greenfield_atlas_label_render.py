"""Native Mermaid proof for literal Greenfield node and relationship labels."""

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from odylith.runtime.domain_intelligence.greenfield_authored_atlas_design_views import (
    mermaid_label,
)
from odylith.runtime.surfaces.mermaid_worker_session import _MermaidWorkerSession
from tests.unit.runtime.test_greenfield_authored_atlas_view import _authored_diagrams


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
    for box in row["diagram_boxes"]:
        if box["role"] == "Supported source actions":
            assert " ".join(box["label"].split()) in labels
        elif box["role"] == "Proposed component":
            responsibility = box["description"].removeprefix("Proposed responsibility: ")
            assert f"Responsibility {responsibility}" in labels
        elif box["role"] == "Proposed boundary verification":
            assert f"Verification {box['label']}" in labels
    edges = [element for element in root.iter() if "flowchart-link" in element.attrib.get("class", "").split()]
    assert len(edges) == 8
    assert {element.attrib["data-id"].rsplit("_", 1)[0] for element in edges} == {
        f"L_component{index}_component{index}_{target}"
        for index in range(1, 5) for target in ("actions", "verification")
    }
    assert png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
