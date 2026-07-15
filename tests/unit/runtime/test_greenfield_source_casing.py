from __future__ import annotations

from odylith.runtime.artifact_quality.greenfield_project_judgment import greenfield_project_judgment_issues
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_label
from odylith.runtime.domain_intelligence.greenfield_apply_write import _source_cased_validation_gate
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_source_casing import package_with_source_casing
from odylith.runtime.domain_intelligence.greenfield_source_casing import proposal_source_casing_text
from odylith.runtime.domain_intelligence.proposal_memory import build_accepted_project_source_payload


def test_title_label_preserves_source_owned_mixed_case_tokens() -> None:
    assert title_label("mRNA stability batch comparison") == "mRNA Stability Batch Comparison"


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
        component_registry_preview=(
            {
                "registry_entry": {
                    "component_id": "crispr-review",
                    "name": "cRISPR Review Service",
                    "path_prefixes": ["src/crispr/review"],
                    "spec_ref": "odylith/registry/source/components/crispr-review/CURRENT_SPEC.md",
                    "what_it_is": "cRISPR Review Service defines the planned service ownership boundary.",
                }
            },
        ),
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
    restored_registry_entry = restored.component_registry_preview[0]["registry_entry"]
    assert restored_registry_entry["name"] == "CRISPR Review Service"
    assert restored_registry_entry["path_prefixes"] == ["src/crispr/review"]
    assert restored_registry_entry["spec_ref"] == "odylith/registry/source/components/crispr-review/CURRENT_SPEC.md"
    assert "CRISPR Review Service" in restored_registry_entry["what_it_is"]
    assert "CRISPR review" in restored.project_brief_preview["project_outcome"]
    assert "cRISPR" not in "\n".join(restored.rendered_atlas_sources.values())
    assert "/tmp/crispr-review.md" in restored.backlog_result["idea_files"]


def test_mixed_case_gate_uses_accepted_intent_before_generated_title_casing() -> None:
    package = GreenfieldCompletionPackage(
        proposal={
            "intent": {
                "title": "Cryogenic Protein Microscopy",
                "first_path": "Structural biologist reviews an ambiguous cryo-EM reconstruction case.",
            },
            "semantic_model": {
                "domain_ontology": {
                    "state_object": "Cryo-EM reconstruction record",
                }
            },
        },
        project_brief_preview={
            "project_outcome": "The product keeps the cryo-EM reconstruction case reviewable.",
        },
    )

    issues = greenfield_project_judgment_issues(package)

    assert "greenfield artifacts drift mixed-case source token `Cryo-EM` into `cryo-EM`" not in issues


def test_mixed_case_gate_does_not_treat_generated_all_caps_variant_as_source_authority() -> None:
    package = GreenfieldCompletionPackage(
        proposal={
            "intent": {
                "title": "MRNA Stability Batch Comparison Workspace",
                "first_path": "Formulation scientist can review an ambiguous mRNA stability batch comparison case.",
                "product_view": "The mRNA stability batch comparison remains reviewable.",
            },
        },
        project_brief_preview={
            "project_outcome": "The mRNA stability batch comparison record stays reviewable.",
        },
    )

    issues = greenfield_project_judgment_issues(package)

    assert "greenfield artifacts drift mixed-case source token `MRNA` into `mRNA`" not in issues


def test_source_casing_custody_prefers_lower_first_mixed_case_source_token() -> None:
    package = GreenfieldCompletionPackage(
        proposal={
            "intent": {
                "title": "MRNA Stability Batch Comparison Workspace",
                "first_path": "Formulation scientist can review an ambiguous mRNA stability batch comparison case.",
            },
            "components": [
                {
                    "component_id": "mrna-review",
                    "label": "MRNA Stability Batch Comparison Workspace Review Workspace",
                }
            ],
        },
        project_brief_preview={
            "project_outcome": "MRNA Stability Batch Comparison Workspace keeps the mRNA case reviewable.",
        },
    )

    restored = package_with_source_casing(package)

    assert restored.proposal["components"][0]["component_id"] == "mrna-review"
    assert restored.proposal["intent"]["title"] == "mRNA Stability Batch Comparison Workspace"
    assert restored.proposal["components"][0]["label"] == "mRNA Stability Batch Comparison Workspace Review Workspace"
    assert "mRNA Stability Batch Comparison Workspace" in restored.project_brief_preview["project_outcome"]
    assert "MRNA Stability" not in restored.project_brief_preview["project_outcome"]


def test_accepted_project_memory_restores_mixed_case_visible_actors() -> None:
    proposal = {
        "intent": {
            "title": "mRNA Stability Batch Comparison Workspace",
            "product_story": "mRNA Stability Batch Comparison Workspace keeps review evidence tied to mRNA source input.",
        },
        "confirmed_intent": {
            "title": "mRNA Stability Batch Comparison Workspace",
            "first_path": "A formulation scientist reviews one mRNA stability comparison with traceable evidence.",
        },
    }
    payload = build_accepted_project_source_payload(
        proposal=proposal,
        backlog_items=[],
        component_items=[],
        diagram_ids=[],
        release_selector="0.0.1",
        release_id="R1",
        validation_gate={
            "status": "passed",
            "visible_actors": [
                {
                    "stable_role": "evidence_owner",
                    "visible_actor": "MRNA Stability Batch proof reviewer",
                    "actor_source": "generated_role_projection",
                }
            ],
        },
    )

    actor = payload["validation_gate"]["visible_actors"][0]["visible_actor"]
    assert actor == "mRNA Stability Batch proof reviewer"
    assert "MRNA Stability" not in "\n".join(str(value) for value in payload["validation_gate"].values())


def test_returned_validation_gate_uses_same_source_casing_as_accepted_memory() -> None:
    proposal = {
        "intent": {
            "title": "mRNA Stability Batch Comparison Workspace",
            "product_story": "mRNA Stability Batch Comparison Workspace keeps review evidence tied to mRNA source input.",
        },
        "confirmed_intent": {
            "title": "mRNA Stability Batch Comparison Workspace",
            "first_path": "A formulation scientist reviews one mRNA stability comparison with traceable evidence.",
        },
    }

    class Tribunal:
        def to_dict(self) -> dict[str, object]:
            return {
                "status": "passed",
                "visible_actors": [
                    {
                        "stable_role": "evidence_owner",
                        "visible_actor": "MRNA Stability Batch proof reviewer",
                        "actor_source": "generated_role_projection",
                    }
                ],
            }

    source_text = proposal_source_casing_text(proposal)
    gate = _source_cased_validation_gate(Tribunal(), source_text=source_text)
    payload = build_accepted_project_source_payload(
        proposal=proposal,
        backlog_items=[],
        component_items=[],
        diagram_ids=[],
        release_selector="0.0.1",
        release_id="R1",
        validation_gate=gate,
    )

    returned_actor = gate["visible_actors"][0]["visible_actor"]
    accepted_actor = payload["validation_gate"]["visible_actors"][0]["visible_actor"]
    assert returned_actor == accepted_actor == "mRNA Stability Batch proof reviewer"
