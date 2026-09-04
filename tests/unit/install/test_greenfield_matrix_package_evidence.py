from __future__ import annotations

import sys

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_package_evidence import _atlas_findings
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import RenderedArtifact


def test_atlas_edge_evidence_uses_the_canonical_mermaid_graph_parser() -> None:
    artifact = RenderedArtifact(
        surface="Atlas Mermaid",
        name="responsibility-map.mmd",
        text="graph LR\n  Intake[Request intake] --- Proof[Accepted proof]\n",
    )

    findings = _atlas_findings(
        artifacts=(artifact,),
        proposal={"diagrams": [{"diagram_id": "D-001"}]},
    )

    assert not any("no visible topology edge" in finding.message for finding in findings)


def test_atlas_edge_evidence_still_rejects_a_nodes_only_diagram() -> None:
    artifact = RenderedArtifact(
        surface="Atlas Mermaid",
        name="responsibility-map.mmd",
        text="graph LR\n  Intake[Request intake]\n  Proof[Accepted proof]\n",
    )

    findings = _atlas_findings(
        artifacts=(artifact,),
        proposal={"diagrams": [{"diagram_id": "D-001"}]},
    )

    assert any("neither a typed edge nor a distinct containment" in finding.message for finding in findings)


def test_atlas_evidence_accepts_distinct_authored_containment_without_an_edge() -> None:
    artifact = RenderedArtifact(
        surface="Atlas Mermaid",
        name="state-evidence.mmd",
        text=(
            'flowchart LR\n'
            '  subgraph accepted["Accepted project facts"]\n'
            '    state["Consent evidence"]\n'
            '  end\n'
        ),
    )
    findings = _atlas_findings(
        artifacts=(artifact,),
        proposal={
            "diagrams": [
                {
                    "slug": "state-evidence",
                    "projection_origin": "model_authored_typed_intent",
                    "diagram_boxes": [
                        {
                            "node_id": "accepted",
                            "label": "Accepted project facts",
                            "role": "Container",
                            "description": "Accepted fact container.",
                        },
                        {
                            "node_id": "state",
                            "label": "Consent evidence",
                            "role": "State object",
                            "description": "Accepted state.",
                        },
                    ],
                }
            ]
        },
    )

    assert not findings


def test_atlas_evidence_rejects_self_nested_authored_boundary() -> None:
    artifact = RenderedArtifact(
        surface="Atlas Mermaid",
        name="component-boundaries.mmd",
        text=(
            'flowchart LR\n'
            '  subgraph product["Shelter intake"]\n'
            '    component["Shelter intake"]\n'
            '  end\n'
        ),
    )
    findings = _atlas_findings(
        artifacts=(artifact,),
        proposal={
            "diagrams": [
                {
                    "slug": "component-boundaries",
                    "projection_origin": "model_authored_typed_intent",
                    "diagram_boxes": [
                        {
                            "node_id": "product",
                            "label": "Shelter intake",
                            "role": "Product boundary",
                            "description": "Product container.",
                        },
                        {
                            "node_id": "component",
                            "label": "Shelter intake",
                            "role": "Product-owned component",
                            "description": "Candidate component.",
                        },
                    ],
                }
            ]
        },
    )

    messages = [finding.message for finding in findings]
    assert any("two distinct typed concepts" in message for message in messages)
    assert any("neither a typed edge nor a distinct containment" in message for message in messages)
