from __future__ import annotations

from odylith.runtime.artifact_quality.greenfield_project_judgment import greenfield_project_judgment_issues
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_source_casing import package_with_source_casing


def test_source_casing_custody_repairs_visible_copy_without_rewriting_structural_ids() -> None:
    package = GreenfieldCompletionPackage(
        proposal={
            "intent": {
                "title": "CRISPR Perturbation Review",
                "state_object": "CRISPR perturbation record with reviewer notes and evidence status.",
            },
            "components": [
                {
                    "component_id": "crispr-review",
                    "label": "cRISPR Review Service",
                }
            ],
            "backlog": [
                {
                    "title": "Review CRISPR evidence",
                    "component_focus": ["crispr-review"],
                }
            ],
            "semantic_model": {
                "domain_ontology": {
                    "state_object": "cRISPR perturbation record",
                },
                "workstreams": [
                    {
                        "title": "Review CRISPR evidence",
                        "component_ids": ["crispr-review"],
                    }
                ],
                "diagram_event_graph": {
                    "component_sequence": ["crispr-review"],
                },
            },
        },
        rendered_atlas_sources={
            "odylith/atlas/source/crispr-review.mmd": 'flowchart LR\n    review["Review cRISPR perturbation evidence"]'
        },
        project_brief_preview={
            "project_outcome": "The cRISPR review explains perturbation evidence and keeps reviewers aligned.",
        },
        backlog_result={
            "idea_files": {
                "/tmp/crispr-review.md": "The cRISPR review keeps perturbation evidence available for decision review."
            }
        },
    )

    assert any("source token `CRISPR` into `cRISPR`" in issue for issue in greenfield_project_judgment_issues(package))

    restored = package_with_source_casing(package)

    assert not [
        issue for issue in greenfield_project_judgment_issues(restored) if "source token `CRISPR` into `cRISPR`" in issue
    ]
    assert restored.proposal["components"][0]["component_id"] == "crispr-review"
    assert restored.proposal["components"][0]["label"] == "CRISPR Review Service"
    assert restored.proposal["backlog"][0]["component_focus"] == ["crispr-review"]
    assert restored.proposal["semantic_model"]["diagram_event_graph"]["component_sequence"] == ["crispr-review"]
    assert "CRISPR review" in restored.project_brief_preview["project_outcome"]
    assert "cRISPR" not in "\n".join(restored.rendered_atlas_sources.values())
    assert "/tmp/crispr-review.md" in restored.backlog_result["idea_files"]
