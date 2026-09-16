from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_package_evidence import _atlas_findings
from greenfield_matrix_package_evidence import _registry_findings
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import RenderedArtifact


_PROPOSED_SPEC = """# Request Intake

## Component Snapshot
Proposed logical component; no implementation or deployment is asserted.

## Proposed responsibility
Retain requests for review.

## Proposed inputs and outputs
No component exchanges are proposed for this capability.

## Proposed verification
The submitted request can be retrieved.

## Source-event support
The coordinator submits a request; the actor retains ownership.

## Trace links
Canonical design row: /authored_semantics/provisional_design/components/0

## Feature History
Initial provisional design.
"""


def _registry_messages(text: str) -> list[str]:
    return [finding.message for finding in _registry_findings(
        package=SimpleNamespace(),
        artifacts=(RenderedArtifact("Registry component spec", "request-intake/CURRENT_SPEC.md", text),),
        proposal={"components": [{"component_id": "request-intake"}]},
    )]


def test_registry_evidence_accepts_explicitly_proposed_design_without_source_ownership() -> None:
    assert _registry_messages(_PROPOSED_SPEC) == []


@pytest.mark.parametrize("section", (
    "Component Snapshot", "Proposed responsibility", "Proposed inputs and outputs",
    "Proposed verification", "Source-event support", "Trace links", "Feature History",
))
@pytest.mark.parametrize("change", ("missing", "empty", "body_only"))
def test_registry_evidence_requires_real_nonempty_proposed_sections(section: str, change: str) -> None:
    heading = f"## {section}\n"
    before, tail = _PROPOSED_SPEC.split(heading, 1)
    body, separator, remainder = tail.partition("\n## ")
    suffix = separator + remainder
    replacement = {"missing": "", "empty": heading, "body_only": section + "\n" + body}[change]
    assert any(section in message for message in _registry_messages(before + replacement + suffix))


def test_registry_evidence_does_not_accept_superseded_source_owned_sections() -> None:
    obsolete = _PROPOSED_SPEC.replace("Proposed responsibility", "Source-custodied responsibility")
    assert any("Proposed responsibility" in message for message in _registry_messages(obsolete))


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
            '  actor["Intake coordinator"] --> product\n'
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
                        {
                            "node_id": "actor",
                            "label": "Intake coordinator",
                            "role": "Human actor",
                            "description": "Accepted actor.",
                        },
                    ],
                }
            ]
        },
    )

    messages = [finding.message for finding in findings]
    assert messages == [
        "Atlas Mermaid `component-boundaries.mmd` repeats the product boundary as an identically named child component"
    ]
