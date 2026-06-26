from __future__ import annotations

from odylith.runtime.reasoning.tribunal_lens import tribunal_lens_check
from odylith.runtime.reasoning.tribunal_lens import tribunal_lens_report


def test_tribunal_lens_check_carries_typed_repair_custody() -> None:
    check = tribunal_lens_check(
        lens="architect",
        role="Architect",
        name="component_topology",
        passed=False,
        evidence="1 active component, no boundary proof",
        issue="quality lens architect missing component topology from internal systems",
        surface="registry",
        target_path="proposal.components",
        projection_id="review_report",
        semantic_node_id="SemanticModelIR.component_contracts",
        repairability="semantic_patch",
        owner="semantic_model_compiler",
    )

    payload = check.to_dict()

    assert payload["status"] == "failed"
    assert payload["lens"] == "architect"
    assert payload["surface"] == "registry"
    assert payload["target_path"] == "proposal.components"
    assert payload["semantic_node_id"] == "SemanticModelIR.component_contracts"
    assert payload["repairability"] == "semantic_patch"
    assert payload["owner"] == "semantic_model_compiler"


def test_tribunal_lens_report_preserves_existing_report_shape() -> None:
    report = tribunal_lens_report(
        {
            "product_manager": (
                tribunal_lens_check(
                    lens="product_manager",
                    role="Product manager",
                    name="decision_boundary",
                    passed=False,
                    evidence="0 assumptions, 0 ambiguity rows",
                    issue="quality lens product_manager missing assumptions or ambiguity boundary",
                    surface="product_manager",
                    target_path="proposal.assumptions",
                    projection_id="review_report",
                    semantic_node_id="SemanticModelIR.decision_boundary",
                    owner="semantic_model_compiler",
                ),
            )
        },
        version="example-v1",
    )

    assert report["version"] == "example-v1"
    assert report["status"] == "failed"
    assert report["issues"] == ["quality lens product_manager missing assumptions or ambiguity boundary"]
    assert report["lenses"]["product_manager"]["status"] == "failed"
    assert report["lenses"]["product_manager"]["role"] == "Product manager"
    assert report["lenses"]["product_manager"]["checks"][0]["target_path"] == "proposal.assumptions"
