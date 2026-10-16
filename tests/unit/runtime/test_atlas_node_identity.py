"""Mermaid label inventory stays exact without generating human explanations."""

import pytest

from odylith.runtime.surfaces import atlas_box_explanations as boxes
from odylith.runtime.surfaces import atlas_diagram_intelligence as graph


@pytest.mark.parametrize(
    ("node_label", "expected_label"),
    [
        ("Gateway<br/>RequestContract", "Gateway RequestContract"),
        ("Storage<br/>RecordSchema", "Storage RecordSchema"),
        ("Scheduler<br/>JobDefinition", "Scheduler JobDefinition"),
    ],
)
def test_multiline_declared_node_is_inventory_once(node_label: str, expected_label: str) -> None:
    source = f'flowchart LR\n  Alpha["{node_label}"] --> Beta["Worker"]\n'
    assert [box.label for box in boxes.extract_diagram_boxes_from_mermaid(source)] == [expected_label, "Worker"]


def test_declared_node_identity_remains_case_sensitive() -> None:
    source = 'flowchart LR\n  Node["Upper endpoint"] --> node["Lower endpoint"]\n'
    assert [box.label for box in boxes.extract_diagram_boxes_from_mermaid(source)] == [
        "Upper endpoint", "Lower endpoint",
    ]


@pytest.mark.parametrize(("declared_id", "graph_id"), [("Node", "node"), ("node", "Node")])
def test_graph_only_node_is_not_hidden_by_differently_cased_declared_id(
    declared_id: str, graph_id: str,
) -> None:
    source = f'flowchart LR\n  {declared_id}["Named endpoint"] --> {graph_id}\n'
    assert [box.label for box in boxes.extract_diagram_boxes_from_mermaid(source)] == [
        "Named endpoint", "Node",
    ]


def test_graph_only_endpoints_and_state_aliases_remain_discoverable() -> None:
    flow = "flowchart LR\n  RequestGateway --> WorkQueue\n"
    state = 'stateDiagram-v2\n  state "Ready for work" as Ready\n  Ready --> Completed\n'
    assert [box.label for box in boxes.extract_diagram_boxes_from_mermaid(flow)] == [
        "Request Gateway", "Work Queue",
    ]
    assert [box.label for box in boxes.extract_diagram_boxes_from_mermaid(state)] == [
        "Ready for work", "Completed",
    ]


def test_nested_containers_are_in_inventory_once_without_inferred_roles() -> None:
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
    found = boxes.extract_diagram_boxes_from_mermaid(source)
    assert [box.label for box in found] == [
        "Product boundary", "Runtime boundary", "Gateway RequestContract", "Worker", "Outside endpoint",
    ]
    assert all(box.role == box.description == "" for box in found)


def test_sequence_participants_keep_exact_labels_without_inferred_duties() -> None:
    source = "\n".join(
        [
            "sequenceDiagram",
            "  participant Client as Requesting client",
            "  participant Worker as Processing worker",
            "  Client->>Worker: Submit request",
        ]
    )
    found = boxes.extract_diagram_boxes_from_mermaid(source)
    assert [box.label for box in found] == ["Requesting client", "Processing worker"]
    assert all(box.role == box.description == "" for box in found)


@pytest.mark.parametrize("label", ["Opaque checkpoint", "Opaque checkpoints"])
def test_unknown_isolated_nodes_do_not_invent_responsibilities(label: str) -> None:
    found = boxes.extract_diagram_boxes_from_mermaid(f'flowchart LR\n  a["{label}"]\n')
    assert [(box.label, box.role, box.description) for box in found] == [(label, "", "")]


def test_graph_relationships_remain_machine_facts_without_explanation_copy() -> None:
    source = "\n".join(
        [
            "flowchart LR",
            '  copy["Archive Copier: write exact bytes"] --> compare["Compare SHA-256 and permission mode"]',
            '  compare -->|"verified"| result["Byte preservation passes"]',
        ]
    )
    found = boxes.extract_diagram_boxes_from_mermaid(source)
    parsed = graph.parse_mermaid_graph(source)
    assert [box.label for box in found] == [
        "Archive Copier: write exact bytes", "Compare SHA-256 and permission mode", "Byte preservation passes",
    ]
    assert [(edge.source_id, edge.target_id, edge.label) for edge in parsed.edges] == [
        ("copy", "compare", ""), ("compare", "result", "verified"),
    ]
    assert all(box.role == box.description == "" for box in found)


def test_authored_catalog_box_keeps_exact_role_description_and_details() -> None:
    source = 'flowchart LR\n  copy["Archive Copier"] --> proof["Proof receipt"]\n'
    authored = boxes.DiagramBoxExplanation(
        label="Archive Copier",
        role="Custodian",
        description="Writes the exact source bytes and preserves their file mode.",
        details=({"label": "Evidence", "text": "Source hash and target mode are recorded."},),
    )
    assert [box.label for box in boxes.extract_diagram_boxes_from_mermaid(source)] == [
        "Archive Copier", "Proof receipt",
    ]
    assert boxes.merge_diagram_box_explanations(source_text=source, catalog_boxes=[authored]) == (
        authored.as_dict(),
        {"label": "Proof receipt", "role": "", "description": ""},
    )


def test_greenfield_labels_and_deferrals_remain_exact_without_semantic_copy() -> None:
    source = "\n".join(
        [
            "flowchart LR",
            '  actor1["Solo performer (primary)"] --> component1',
            '  component1["Rhythm, Tempo, And Meter Estimator Service"]',
            '  component1 --> proof1["Proof boundary<br/>Recorded take review"]',
            '  external1["Weather alert feeds are<br/>deferred"] --> component1',
        ]
    )
    found = boxes.extract_diagram_boxes_from_mermaid(source)
    assert [box.label for box in found] == [
        "Solo performer (primary)", "Rhythm, Tempo, And Meter Estimator Service",
        "Proof boundary", "Weather alert feeds",
    ]
    assert all(box.role == box.description == "" for box in found)


def test_truncated_component_and_source_symbol_labels_resolve_without_copy() -> None:
    sequence = "\n".join(
        [
            "sequenceDiagram",
            "  participant A as Solo performer (primary)",
            "  participant C1 as Audio Capture And Pre-processing…",
            "  A->>C1: start accepted first path",
        ]
    )
    component_rows = [
        {
            "name": "Audio Capture And Pre-processing Service",
            "description": "Owns microphone or line-in to mono PCM, noise gate, optional normalization.",
        }
    ]
    found = boxes.extract_diagram_boxes_from_mermaid(sequence, component_rows=component_rows)
    assert [box.label for box in found] == [
        "Solo performer (primary)", "Audio Capture And Pre-processing Service",
    ]
    source_symbol = 'flowchart LR\n  record["mRNA Stability Batch"] --> reviewer["Formulation Scientist"]\n'
    assert [box.label for box in boxes.extract_diagram_boxes_from_mermaid(source_symbol)] == [
        "mRNA Stability Batch", "Formulation Scientist",
    ]


def test_component_description_cleanup_retains_supplied_action_and_source_symbol() -> None:
    assert boxes.clean_component_description(
        name="mRNA Stability Batch",
        description="mRNA Stability Batch is the trusted record core for the product. It ties review evidence to source input.",
    ) == "Is the trusted record core for the product."
    assert boxes.clean_component_description(
        name="Dispatch / Automation Service",
        description="Issues control actions to downstream devices.",
    ) == "Issues control actions to downstream devices."
