"""Declared Mermaid nodes retain identity across explanation discovery passes."""

import pytest

from odylith.runtime.surfaces import atlas_box_explanations


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

    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(source)

    assert [box.label for box in boxes] == [expected_label, "Worker"]


def test_declared_node_identity_remains_case_sensitive() -> None:
    source = 'flowchart LR\n  Node["Upper endpoint"] --> node["Lower endpoint"]\n'

    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(source)

    assert [box.label for box in boxes] == ["Upper endpoint", "Lower endpoint"]


@pytest.mark.parametrize(("declared_id", "graph_id"), [("Node", "node"), ("node", "Node")])
def test_graph_only_node_is_not_hidden_by_differently_cased_declared_id(
    declared_id: str, graph_id: str,
) -> None:
    source = f'flowchart LR\n  {declared_id}["Named endpoint"] --> {graph_id}\n'

    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(source)

    assert [box.label for box in boxes] == ["Named endpoint", "Node"]


def test_graph_only_endpoints_remain_discoverable() -> None:
    source = "flowchart LR\n  RequestGateway --> WorkQueue\n"

    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(source)

    assert [box.label for box in boxes] == ["Request Gateway", "Work Queue"]


def test_graph_only_state_aliases_remain_discoverable() -> None:
    source = 'stateDiagram-v2\n  state "Ready for work" as Ready\n  Ready --> Completed\n'

    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(source)

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

    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(source)

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

    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(source)

    assert [(box.label, box.role) for box in boxes] == [
        ("Requesting client", "Participant"),
        ("Processing worker", "Participant"),
    ]


@pytest.mark.parametrize("label", ["Opaque checkpoint", "Opaque checkpoints"])
def test_unknown_isolated_nodes_do_not_invent_responsibilities(label: str) -> None:
    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(f'flowchart LR\n  a["{label}"]\n')

    assert [(box.label, box.description) for box in boxes] == [(label, "")]


def test_unknown_nodes_use_actual_graph_neighbours_without_advice() -> None:
    source = '\n'.join([
        'flowchart LR',
        '  copy["Archive Copier: write exact bytes"] --> compare["Compare SHA-256 and permission mode"]',
        '  compare --> result["Byte preservation passes"]',
    ])

    by_label = {box.label: box.description for box in atlas_box_explanations.extract_diagram_boxes_from_mermaid(source)}

    assert "Compare SHA-256 and permission mode" in by_label["Archive Copier: write exact bytes"]
    assert "Archive Copier: write exact bytes" in by_label["Compare SHA-256 and permission mode"]
    assert "Compare SHA-256 and permission mode" in by_label["Byte preservation passes"]
    assert all("named responsibility" not in text and "should name" not in text for text in by_label.values())


def test_catalog_authored_description_still_overrides_generated_graph_copy() -> None:
    source = 'flowchart LR\n  copy["Archive Copier"] --> proof["Proof receipt"]\n'
    authored = atlas_box_explanations.DiagramBoxExplanation(
        label="Archive Copier", role="Custodian",
        description="Writes the exact source bytes and preserves their file mode.",
    )

    merged = atlas_box_explanations.merge_diagram_box_explanations(source_text=source, catalog_boxes=[authored])

    assert merged[0]["description"] == authored.description
    assert merged[0]["role"] == "Custodian"


def test_atlas_box_explanations_generate_action_oriented_node_copy() -> None:
    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(
        "\n".join(
            [
                "flowchart LR",
                "  PlantOwner[Plant owner] --> Plant[One potted plant]",
                "  Plant --> Sensor[Plant sensing unit]",
                "  Sensor --> Decision[Care decision core]",
                "  Decision --> Doser[Liquid dosing controller]",
                "  Doser --> Log[Care event log]",
                "  Log --> Interface[Owner status interface]",
                "",
            ]
        )
    )
    by_label = {box.label: box.description for box in boxes}

    assert "owns or manages the potted plants" in by_label["Plant owner"]
    assert "hands off" not in by_label["Plant owner"]
    assert "object whose state changes" in by_label["One potted plant"]
    assert "hands off" not in by_label["One potted plant"]
    assert "measures the current state" in by_label["Plant sensing unit"]
    assert "hands off" not in by_label["Plant sensing unit"]
    assert "decides whether the next action is allowed" in by_label["Care decision core"]
    assert "hands off" not in by_label["Care decision core"]
    assert "performs the bounded action" in by_label["Liquid dosing controller"]
    assert "hands off" not in by_label["Liquid dosing controller"]
    assert "keeps the evidence needed" in by_label["Care event log"]
    assert "hands off" not in by_label["Care event log"]
    assert "primary user surface" in by_label["Owner status interface"]
    assert "current state" in by_label["Owner status interface"]
    assert all("This box represents" not in description for description in by_label.values())


def test_atlas_box_explanations_use_domain_meaning_before_graph_mechanics() -> None:
    source = "\n".join(
        [
            "flowchart LR",
            "    Steward[\"Land Steward<br/>(owns parcels)\"]:::actor",
            "    Observer[\"Field Observer /<br/>Community Monitor\"]:::actor",
            "    Verifier[\"Verifier /<br/>Auditor\"]:::actor",
            "    Coordinator[\"Program<br/>Coordinator\"]:::actor",
            "    subgraph FPT [\"Forest Preservation Tracker\"]",
            "        Web[\"Steward Web Surface\"]:::product",
            "        Field[\"Field Capture Surface\"]:::product",
            "        Core[\"Core Services:<br/>parcel records,<br/>observation ledger,<br/>evidence linker,<br/>condition deriver,<br/>audit trail\"]:::product",
            "        Auth[\"Auth Service\"]:::product",
            "        RSA[\"Remote Sensing Adapter\"]:::product",
            "        Privacy[\"Privacy and<br/>Sharing Controls\"]:::product",
            "    end",
            "    Imagery[\"Remote-Sensing Providers<br/>(Sentinel-2, Planet, GFW)\"]:::external",
            "    Cadastral[\"Cadastral and<br/>Boundary Sources\"]:::external",
            "    IDP[\"Identity Provider\"]:::external",
            "    Notif[\"Notification Channels<br/>(later wave)\"]:::external",
            "    Steward --> Web",
            "    Coordinator --> Web",
            "    Observer --> Field",
            "    Verifier --> Web",
            "    Web --> Core",
            "    Field --> Core",
            "    Web --> Auth",
            "    Field --> Auth",
            "    Core --> Auth",
            "    Core --> Privacy",
            "    RSA --> Core",
            "    Imagery --> RSA",
            "    Cadastral --> Core",
            "    IDP --> Auth",
            "    Privacy -. later .-> Notif",
        ]
    )
    boxes = atlas_box_explanations.merge_diagram_box_explanations(
        source_text=source,
        catalog_boxes=(),
        component_rows=[
            {
                "name": "Forest Parcel Records Service",
                "description": "Owns forest Parcel and BoundaryRevision; emits audit entries for every state-affecting operator.",
            },
            {
                "name": "Forest Observation Ledger",
                "description": "Owns the append-only forest observation ledger with content-hashed, source-attributed entries.",
            },
        ],
        diagram_title="System Context View",
        diagram_summary=(
            "Boundary view of the Forest Preservation Tracker showing stewards, observers, verifiers, "
            "program coordinators, remote-sensing providers, cadastral sources, and notification channels."
        ),
    )
    by_label = {box["label"]: box["description"] for box in boxes}

    assert "Field Observer / Community Monitor" in by_label
    assert "forest parcels" in by_label["Land Steward (owns parcels)"]
    assert "trustworthy identity, state, evidence, and history" in by_label["Land Steward (owns parcels)"]
    assert "source, time, location, evidence" in by_label["Field Observer / Community Monitor"]
    assert "forest parcel claim" in by_label["Verifier / Auditor"]
    assert "audit history" in by_label["Verifier / Auditor"]
    assert "trusted record layer" in by_label["Core Services: parcel records, observation ledger, evidence linker, condition deriver, audit trail"]
    assert "traceable claims" in by_label["Core Services: parcel records, observation ledger, evidence linker, condition deriver, audit trail"]
    assert "external source of remote signals" in by_label["Remote-Sensing Providers (Sentinel-2, Planet, GFW)"]
    assert "boundary or ownership reference" in by_label["Cadastral and Boundary Sources"]
    assert "later-wave communication path" in by_label["Notification Channels (later wave)"]
    forbidden = ("part of the path", "incoming arrows", "outgoing arrows", "hands off", "branch point")
    assert all(not any(term in description for term in forbidden) for description in by_label.values())


def test_atlas_box_explanations_sanitize_greenfield_component_and_scope_copy() -> None:
    source = "\n".join(
        [
            "flowchart LR",
            '  actor1["Solo performer (primary)"] --> component1',
            '  component1["Rhythm, Tempo, And Meter Estimator Service"]',
            '  component1 --> export1["Export Service"]',
            '  export1 --> model1["Score Model Service"]',
            '  export1 --> proof1["Proof boundary<br/>Recorded take review"]',
            '  external1["No external account system, no payment processor"] --> component1',
            "",
        ]
    )
    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(
        source,
        component_rows=[
            {
                "name": "Rhythm, Tempo, And Meter Estimator Service",
                "description": (
                    "Rhythm, tempo, and meter estimator owns beat tracking and quantization grid. "
                    "For release 0.0.1, it receives or produces the domain information needed by this first path."
                ),
            },
            {
                "name": "Export Service",
                "description": "Writes the rendered score to MusicXML, MIDI, and PDF artifacts on local disk.",
            },
            {
                "name": "Score Model Service",
                "description": "Owns the internal score state that renderers and exporters read.",
            },
        ],
        diagram_title="First Path Sequence",
        diagram_summary="First release live take path for a musician and reviewed score export.",
    )
    by_label = {box.label: box.description for box in boxes}
    rendered = "\n".join(by_label.values())

    assert "Component1" not in rendered
    assert "entry responsibility" not in rendered
    assert "trusted account evidence" not in rendered
    assert "trusted proof boundary evidence" not in rendered
    assert "trusted the take evidence" not in rendered
    assert "the the" not in rendered
    assert "owns tempo, and meter estimator owns" not in rendered
    assert "owns beat tracking and quantization grid" in by_label["Rhythm, Tempo, And Meter Estimator Service"]
    assert "external source of remote signals" not in by_label["Score Model Service"]
    assert "owns the internal score state" in by_label["Score Model Service"]
    assert "outside the first-release proof boundary" in by_label[
        "No external account system, no payment processor"
    ]
    assert [box.label for box in boxes].count("Proof boundary") == 1


def test_atlas_box_explanations_preserve_lower_first_source_symbol_descriptions() -> None:
    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(
        "\n".join(
            [
                "flowchart LR",
                '  record["mRNA Stability Batch"] --> reviewer["Formulation Scientist"]',
                "",
            ]
        ),
        component_rows=[
            {
                "name": "mRNA Stability Batch",
                "description": (
                    "mRNA Stability Batch is the trusted record core for the product. "
                    "It ties review evidence to source input."
                ),
            }
        ],
        diagram_title="mRNA Stability Batch Review",
        diagram_summary="Shows how the formulation scientist reviews one mRNA stability record.",
    )
    by_label = {box.label: box.description for box in boxes}

    assert by_label["mRNA Stability Batch"].startswith("mRNA Stability Batch is")
    assert "MRNA Stability" not in "\n".join(by_label.values())


def test_atlas_box_explanations_do_not_prefix_action_component_copy_with_owns() -> None:
    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(
        "\n".join(
            [
                "flowchart LR",
                '  forecast["Forecasting Service"] --> dispatch["Dispatch / Automation Service"]',
                '  dispatch --> surface["Insights Surface"]',
                '  surface --> status["Public Coordination Status View Service"]',
                "",
            ]
        ),
        component_rows=[
            {
                "name": "Forecasting Service",
                "description": "Predicts generation and household demand.",
            },
            {
                "name": "Dispatch / Automation Service",
                "description": "Issues control actions to downstream devices.",
            },
            {
                "name": "Insights Surface",
                "description": "Shows the plan, realized result, and history to the operator.",
            },
            {
                "name": "Public Coordination Status View Service",
                "description": "Presents public coordination status, role visibility, and source event history.",
            },
        ],
        diagram_title="Component Boundary View",
        diagram_summary="Shows which product systems own SunLedger release responsibilities.",
    )
    by_label = {box.label: box.description for box in boxes}
    rendered = "\n".join(by_label.values())

    assert "Forecasting Service predicts generation and household demand" in by_label["Forecasting Service"]
    assert "Dispatch / Automation Service issues control actions to downstream devices" in by_label[
        "Dispatch / Automation Service"
    ]
    assert "Insights Surface shows the plan" in by_label["Insights Surface"]
    assert "Public Coordination Status View Service presents public coordination status" in by_label[
        "Public Coordination Status View Service"
    ]
    assert "owns predicts" not in rendered
    assert "owns issues" not in rendered
    assert "owns shows" not in rendered
    assert "owns presents" not in rendered


def test_atlas_box_explanations_keep_plural_action_components_grammatical() -> None:
    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(
        '\n'.join(
            [
                'flowchart LR',
                '  adapters["Managed SDK adapters"] --> hooks["Host hooks"]',
            ]
        ),
        component_rows=[
            {
                "name": "Managed SDK adapters",
                "description": "Expose the same governed harness contract through host-neutral adapters.",
            }
        ],
    )
    by_label = {box.label: box.description for box in boxes}

    assert by_label["Managed SDK adapters"].startswith("Managed SDK adapters expose")
    assert "owns expose" not in by_label["Managed SDK adapters"]


def test_atlas_box_explanations_use_plain_generic_container_copy() -> None:
    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(
        '\n'.join(
            [
                'flowchart LR',
                '  subgraph wave["Execution waves"]',
                '    first["First wave"]',
                '  end',
            ]
        )
    )
    by_label = {box.label: box.description for box in boxes}

    assert by_label["Execution waves"].startswith("Execution waves is a product boundary.")
    assert "for the product" not in by_label["Execution waves"]


def test_atlas_box_explanations_strip_deferred_predicates_before_sentence_templates() -> None:
    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(
        "\n".join(
            [
                "flowchart LR",
                '  external1["Weather alert feeds are<br/>deferred"] --> product',
                '  external2["Emergency dispatch systems are<br/>deferred"] --> product',
                '  product["Coordination Workspace"] --> status["Public Coordination Status View Service"]',
                "",
            ]
        ),
        component_rows=[
            {
                "name": "Public Coordination Status View Service",
                "description": "Presents public coordination status, role visibility, and source event history.",
            },
        ],
        diagram_title="System Context View",
        diagram_summary="Coordination Workspace boundary view showing deferred outside inputs.",
    )
    by_label = {box.label: box.description for box in boxes}
    rendered = "\n".join(f"{box.label}: {box.description}" for box in boxes)

    assert "Weather alert feeds" in by_label
    assert "Emergency dispatch systems" in by_label
    assert "Weather alert feeds are deferred" not in rendered
    assert "Emergency dispatch systems are deferred" not in rendered
    assert by_label["Weather alert feeds"].startswith("Weather alert feeds are ")
    assert "Coordination Workspace" in by_label["Emergency dispatch systems"]
    assert "named responsibility" not in rendered and "should name the domain object" not in rendered
    assert "are is" not in rendered
    assert "are and Emergency dispatch systems are" not in rendered
    assert "owns presents" not in rendered


def test_atlas_box_explanations_parse_sequence_participants_without_broken_labels() -> None:
    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(
        "\n".join(
            [
                "sequenceDiagram",
                "  autonumber",
                "  participant A as Solo performer (primary)",
                "  participant C1 as Audio Capture And Pre-processing…",
                "  A->>C1: start accepted first path",
                "  Note over A,C1: recorded take proof",
                "",
            ]
        ),
        component_rows=[
            {
                "name": "Audio Capture And Pre-processing Service",
                "description": "Owns microphone or line-in to mono PCM, noise gate, optional normalization.",
            },
        ],
        diagram_title="First Path Sequence",
        diagram_summary="First release live take path for a musician.",
    )
    by_label = {box.label: box.description for box in boxes}

    assert "primary" not in by_label
    assert "Solo performer (primary)" in by_label
    assert "person this product must serve" in by_label["Solo performer (primary)"]
    assert "Audio Capture And Pre-processing…" not in by_label
    assert "Audio Capture And Pre-processing Service" in by_label
    assert "owns microphone or line-in" in by_label["Audio Capture And Pre-processing Service"]


def test_atlas_box_explanations_do_not_classify_product_or_action_labels_as_people() -> None:
    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(
        "\n".join(
            [
                "flowchart LR",
                '  actor["Support Leads"]',
                '  product["Customer Recovery Desk"]',
                '  repair["Repair customer trust"]',
                '  proof["Proof result<br/>Response path accepted"]',
                "  actor --> product",
                "  product --> repair",
                "  repair --> proof",
                "",
            ]
        ),
        component_rows=[
            {
                "name": "Customer Recovery Desk",
                "description": "Coordinates recovery work, owner assignment, response evidence, and review state.",
            },
        ],
        diagram_title="First Path Sequence",
        diagram_summary="Customer Recovery Desk keeps the first release path reviewable for support leads.",
    )
    by_label = {box.label: box.description for box in boxes}
    rendered = "\n".join(by_label.values())

    assert "Support Leads are people" in by_label["Support Leads"]
    assert "Customer Recovery Desk is a person" not in rendered
    assert "Repair customer trust is a person" not in rendered
    assert "coordinates recovery work" in by_label["Customer Recovery Desk"]
    assert "Repair customer trust carries the state forward" in by_label["Repair customer trust"]


def test_atlas_box_explanations_infer_common_governance_surface_actions() -> None:
    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(
        "\n".join(
            [
                "flowchart LR",
                "  Product[Odylith product] --> Radar[Radar]",
                "  Radar --> Plans[Technical Plans]",
                "  Plans --> Atlas[Atlas topology map]",
                "  Atlas --> Compass[Compass status]",
                "  Compass --> Router[Subagent Router]",
                "  Router --> Orchestrator[Subagent Orchestrator]",
                "  Orchestrator --> Handshake[Context-to-Execution handshake]",
                "",
            ]
        )
    )
    by_label = {box.label: box.description for box in boxes}

    assert "defines the product scope" in by_label["Odylith product"]
    assert "hands off" not in by_label["Odylith product"]
    assert "tracks the work choices" in by_label["Radar"]
    assert "hands off" not in by_label["Radar"]
    assert "turn selected work into an implementation path" in by_label["Technical Plans"]
    assert "hands off" not in by_label["Technical Plans"]
    assert "shows the system shape" in by_label["Atlas topology map"]
    assert "hands off" not in by_label["Atlas topology map"]
    assert "summarizes current runtime state" in by_label["Compass status"]
    assert "hands off" not in by_label["Compass status"]
    assert "chooses where work should go next" in by_label["Subagent Router"]
    assert "hands off" not in by_label["Subagent Router"]
    assert "coordinates bounded work" in by_label["Subagent Orchestrator"]
    assert "passes agreed state across a boundary" in by_label["Context-to-Execution handshake"]
    assert "reached after" not in by_label["Context-to-Execution handshake"]
    assert all("concrete step" not in description for description in by_label.values())
