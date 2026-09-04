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

    assert any("no visible topology edge" in finding.message for finding in findings)
