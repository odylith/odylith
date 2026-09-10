"""Declared Mermaid nodes retain identity across explanation discovery passes."""

import pytest

from odylith.runtime.surfaces.atlas_box_explanations import extract_diagram_boxes_from_mermaid


@pytest.mark.parametrize(
    ("node_label", "expected_label"),
    [
        ("Gateway<br/>RequestContract", "Gateway RequestContract"),
        ("Storage<br/>RecordSchema", "Storage RecordSchema"),
        ("Scheduler<br/>JobDefinition", "Scheduler JobDefinition"),
    ],
)
def test_multiline_declared_node_is_explained_once(
    node_label: str, expected_label: str,
) -> None:
    source = f'flowchart LR\n  Alpha["{node_label}"] --> Beta["Worker"]\n'

    boxes = extract_diagram_boxes_from_mermaid(source)

    assert [box.label for box in boxes] == [expected_label, "Worker"]


def test_declared_node_identity_remains_case_sensitive() -> None:
    source = 'flowchart LR\n  Node["Upper endpoint"] --> node["Lower endpoint"]\n'

    boxes = extract_diagram_boxes_from_mermaid(source)

    assert [box.label for box in boxes] == ["Upper endpoint", "Lower endpoint"]


@pytest.mark.parametrize(("declared_id", "graph_id"), [("Node", "node"), ("node", "Node")])
def test_graph_only_node_is_not_hidden_by_differently_cased_declared_id(
    declared_id: str, graph_id: str,
) -> None:
    source = f'flowchart LR\n  {declared_id}["Named endpoint"] --> {graph_id}\n'

    boxes = extract_diagram_boxes_from_mermaid(source)

    assert [box.label for box in boxes] == ["Named endpoint", "Node"]


def test_graph_only_endpoints_remain_discoverable() -> None:
    source = "flowchart LR\n  RequestGateway --> WorkQueue\n"

    boxes = extract_diagram_boxes_from_mermaid(source)

    assert [box.label for box in boxes] == ["Request Gateway", "Work Queue"]


def test_graph_only_state_aliases_remain_discoverable() -> None:
    source = 'stateDiagram-v2\n  state "Ready for work" as Ready\n  Ready --> Completed\n'

    boxes = extract_diagram_boxes_from_mermaid(source)

    assert [box.label for box in boxes] == ["Ready for work", "Completed"]


def test_declared_node_keeps_innermost_container_context_without_rediscovery() -> None:
    source = "\n".join(
        [
            "flowchart LR",
            '  subgraph Product["Product boundary"]',
            '    subgraph Runtime["Runtime boundary"]',
            '      Alpha["Gateway<br/>RequestContract"]',
            "    end",
            '    Beta["Worker"]',
            "  end",
            '  Gamma["Outside endpoint"]',
        ]
    )

    boxes = extract_diagram_boxes_from_mermaid(source)

    assert [(box.label, box.role) for box in boxes] == [
        ("Product boundary", "Container"),
        ("Runtime boundary", "Container"),
        ("Gateway RequestContract", "Runtime boundary"),
        ("Worker", "Product boundary"),
        ("Outside endpoint", "Step"),
    ]
    assert boxes[2].description.startswith("Within Runtime boundary, ")
    assert boxes[3].description.startswith("Within Product boundary, ")
    assert not boxes[4].description.startswith("Within ")


def test_sequence_participants_keep_their_existing_discovery_path() -> None:
    source = "\n".join(
        [
            "sequenceDiagram",
            "  participant Client as Requesting client",
            "  participant Worker as Processing worker",
            "  Client->>Worker: Submit request",
        ]
    )

    boxes = extract_diagram_boxes_from_mermaid(source)

    assert [(box.label, box.role) for box in boxes] == [
        ("Requesting client", "Participant"),
        ("Processing worker", "Participant"),
    ]
