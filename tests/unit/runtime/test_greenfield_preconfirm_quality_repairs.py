from __future__ import annotations

import json

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_workstream_titles
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_component_contract import public_prose_quality_issues
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import action_chain_fragment
from odylith.runtime.domain_intelligence.greenfield_preconfirm_semantic_drift import contrastive_domain_drift_issues
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import build_greenfield_package_report
from odylith.runtime.domain_intelligence.greenfield_preconfirm_package_findings import package_artifact_findings
from odylith.runtime.domain_intelligence.greenfield_preconfirm_patchset import patchset_request_from_findings
from odylith.runtime.domain_intelligence.greenfield_preconfirm_repair import repair_greenfield_package_once
from odylith.runtime.domain_intelligence.greenfield_preconfirm_repair import repair_greenfield_package_until_clean
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.domain_intelligence.greenfield_product_risks import build_product_risks
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.domain_intelligence.proposal_memory import build_accepted_project_source_payload
from odylith.runtime.governance.component_spec_narrative import build_narrative_component_spec


def _mechanical_copy_operation(*affected_projections: str, **overrides: object) -> dict[str, object]:
    operation: dict[str, object] = {
        "target_layer": "artifact_draft_set",
        "target_path": "prewrite_package.rendered_component_specs::spec.md",
        "issue_code": "generated_copy_quality",
        "operation_kind": "artifact_draft_mechanical_copy",
        "repair_owner": "artifact_draft_cleaner",
        "requested_action": "Apply only explicitly safe mechanical cleanup, then rerun the same typed review gates.",
        "replacement_fact": "",
        "decision_ledger_entry": "",
        "proof_obligation_delta": "",
        "affected_projections": list(affected_projections),
    }
    operation.update(overrides)
    return operation


def test_plain_title_actor_subjects_separate_coherently_from_actions() -> None:
    assert base_action_clause("Home Cook picks a recipe") == "home cook picks a recipe"
    assert action_chain_fragment("Home Cook picks a recipe") == "pick a recipe"
    assert first_path_capability_phrase("Home Cook picks a recipe") == "pick a recipe"
    assert generated_semantic_slop_issues({"capability": first_path_capability_phrase("Home Cook picks a recipe")}) == []

    assert base_action_clause("Station Lead Review") == "station lead review"
    assert action_chain_fragment("Station Lead Review") == "station lead review"
    assert generated_semantic_slop_issues({"fragment": action_chain_fragment("Station Lead Review")}) == []


def test_generated_semantic_slop_gate_rejects_malformed_actor_labels() -> None:
    issues = generated_semantic_slop_issues(
        {
            "intent": {
                "human_actors": [
                    "Port Operations Compare Vessel: needs the product to schedule berth windows.",
                    "Operator Signoff Before: needs the product to publish a daily berth plan.",
                ]
            }
        }
    )

    assert any("action clause leaked into actor label" in issue for issue in issues)
    assert any("dangling relation leaked into actor label" in issue for issue in issues)


def test_generated_semantic_slop_gate_keeps_role_ending_actor_labels() -> None:
    assert generated_semantic_slop_issues(
        {"intent": {"human_actors": ["Lab Support Owner: needs the product to coordinate evidence."]}}
    ) == []


def test_public_copy_gates_ignore_private_authority_prose_but_keep_public_siblings_strict() -> None:
    private_fragment = 'The win is a clear answer to "did I burn enough?'
    authority_only = {
        PRODUCT_INTENT_AUTHORITY_KEY: {
            "atomic_facts": [{"normalized_value": private_fragment}],
        }
    }

    assert generated_semantic_slop_issues(authority_only, root="proposal") == []
    assert public_prose_quality_issues(authority_only) == []

    with_public_fragment = {**authority_only, "product_view": private_fragment}
    assert any("unbalanced quoted text" in issue for issue in generated_semantic_slop_issues(with_public_fragment))


def test_action_chain_fragment_preserves_conditional_visible_result() -> None:
    assert action_chain_fragment(
        "After enough data the app shows whether the tracked metrics changed with usage for that protocol"
    ) == "review whether the tracked metrics changed with usage for that protocol"


def test_accepted_project_memory_treats_repo_name_as_structural_metadata() -> None:
    payload = {"proposal": {"observed_source": {"repo_name": "odylith-debug-sports-concussion-return"}}}

    assert generated_public_copy_issues("accepted-project final memory", payload) == ()


def test_package_repair_does_not_rewrite_semantic_grammar_even_with_draft_permission() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        rendered_component_specs={"spec.md": "The component owns maintains state."},
        next_steps_preview={"gate": "The operator can submits a request."},
    )

    repaired = repair_greenfield_package_once(
        package,
        patchset_request={
            "status": "repairable",
            "operations": [
                {
                    "target_layer": "artifact_draft_set",
                    "issue_code": "generated_copy_quality",
                    "affected_projections": ["registry", "next_steps"],
                }
            ],
        },
    )

    assert repaired == package


def test_package_repair_rejects_non_mechanical_artifact_draft_operations() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        rendered_component_specs={"spec.md": "The record stays attached attached to the accepted state."},
    )

    for operation in (
        _mechanical_copy_operation("registry", operation_kind="semantic_fact"),
        _mechanical_copy_operation("registry", repair_owner="semantic_model_compiler"),
        _mechanical_copy_operation("registry", replacement_fact="rewrite the rendered copy"),
    ):
        repaired = repair_greenfield_package_once(
            package,
            patchset_request={"status": "repairable", "operations": [operation]},
        )

        assert repaired == package


def test_package_repair_does_not_rewrite_duplicate_or_dangling_rendered_copy() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        rendered_component_specs={
            "spec.md": "The component owns maintains state and keeps evidence evidence visible until."
        },
    )

    repaired = repair_greenfield_package_once(
        package,
        patchset_request={
            "status": "repairable",
            "operations": [_mechanical_copy_operation("registry")],
        },
    )

    assert repaired == package


def test_generated_copy_quality_ignores_structural_semantic_axis_values() -> None:
    issues = generated_public_copy_issues(
        "accepted-project memory preview",
        {
            "proposal": {
                "semantic_model": {
                    "components": [
                        {"semantic_axis": "derived_flood-shelter-intake-ledger-keep"},
                    ],
                },
            },
        },
    )

    assert issues == ()


def test_package_repair_does_not_mutate_addressed_artifact_leaf() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        rendered_component_specs={
            "spec.md": "The record stays attached attached to the accepted state.",
            "other.md": "The other record stays attached attached to the accepted state.",
        },
    )

    repaired = repair_greenfield_package_once(
        package,
        patchset_request={
            "status": "repairable",
            "operations": [
                _mechanical_copy_operation(
                    "registry",
                    target_path="prewrite_package.rendered_component_specs::spec.md",
                )
            ],
        },
    )

    assert repaired == package


def test_package_quality_findings_emit_exact_artifact_plan_target_path() -> None:
    package = GreenfieldCompletionPackage(
        proposal={
            "components": [
                {
                    "component_id": "spec.md",
                    "label": "spec.md",
                    "component_contract": {"produced_outputs": "accepted state"},
                }
            ]
        },
        rendered_component_specs={
            "spec.md": "The record stays attached attached to the accepted state.",
        },
    )

    findings = package_artifact_findings(package)
    finding = next(item for item in findings if item.code == "generated_copy_quality")
    patchset = patchset_request_from_findings((finding,)).to_dict()
    operation = patchset["operations"][0]

    assert finding.projection_id == "registry"
    assert finding.repairability == "plan_patch"
    assert finding.owner == "artifact_plan_projector"
    assert finding.target_path == "components[0].component_contract.produced_outputs"
    assert finding.semantic_node_id == "ArtifactPlanIR.components[0].component_contract.produced_outputs"
    assert operation["target_layer"] == "artifact_plan"
    assert operation["target_path"] == "components[0].component_contract.produced_outputs"
    assert operation["affected_projections"] == ("registry",)


def test_package_repair_ignores_exact_rendered_artifact_targets() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        rendered_component_specs={"spec.md": "The record stays attached attached to the accepted state."},
        rendered_atlas_sources={"flow.mmd": "flow stays attached attached to the accepted state."},
        next_steps_preview={"implementation_prompt": "The next step stays attached attached to the accepted state."},
    )

    repaired = repair_greenfield_package_once(
        package,
        patchset_request={
            "status": "repairable",
            "operations": [
                _mechanical_copy_operation(
                    "rendered_component_specs",
                    target_path="prewrite_package.rendered_component_specs::spec.md",
                ),
                _mechanical_copy_operation(
                    "rendered_atlas_sources",
                    target_path="prewrite_package.rendered_atlas_sources::flow.mmd",
                ),
            ],
        },
    )

    assert repaired == package


def test_package_repair_ignores_unsupported_preview_tree_targets() -> None:
    registry_path = "/tmp/stays attached attached/odylith/registry/source/component_registry.v1.json"
    spec_path = "/tmp/stays attached attached/odylith/registry/source/components/c-001/CURRENT_SPEC.md"
    package = GreenfieldCompletionPackage(
        proposal={},
        component_registry_preview=(
            {
                "component_id": "case-redaction",
                "registry_path": registry_path,
                "spec_path": spec_path,
                "feature_history": [
                    {"summary": "The record stays attached attached to the accepted state."},
                ],
            },
        ),
        accepted_project_preview={
            "schema_version": "odylith.accepted_project.v1",
            "created": {
                "components": [
                    {
                        "component_id": "case-redaction",
                        "registry_path": registry_path,
                        "spec_path": spec_path,
                        "feature_history": [
                            {"summary": "The record stays attached attached to the accepted state."},
                        ],
                    }
                ]
            },
        },
    )

    repaired = repair_greenfield_package_once(
        package,
        patchset_request={
            "status": "repairable",
            "operations": [
                _mechanical_copy_operation(
                    "accepted_project",
                    "registry",
                    target_path="prewrite_package.accepted_project_preview",
                )
            ],
        },
    )

    assert repaired == package


def test_package_repair_preserves_adjacent_duplicate_words_for_gate_failure() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        rendered_component_specs={"spec.md": "The record stays attached attached to the accepted state."},
    )

    repaired = repair_greenfield_package_once(package)

    assert repaired == package


def test_package_repair_requires_artifact_draft_patchset_permission() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        rendered_component_specs={"spec.md": "The record stays attached attached to the accepted state."},
    )

    repaired = repair_greenfield_package_once(
        package,
        patchset_request={"status": "no_repairable_operations", "operations": []},
    )

    assert repaired == package


def test_package_repair_does_not_mutate_rendered_copy_for_plan_patch() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        rendered_component_specs={"spec.md": "The record stays attached attached to the accepted state."},
    )

    repaired = repair_greenfield_package_once(
        package,
        patchset_request={
            "status": "repairable",
            "operations": [
                {
                    "target_layer": "artifact_plan",
                    "issue_code": "generated_copy_quality",
                    "affected_projections": ["registry"],
                }
            ],
        },
    )

    assert repaired == package


def test_package_repair_rejects_whole_preview_tree_targets() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        rendered_component_specs={"spec.md": "The record stays attached attached to the accepted state."},
        next_steps_preview={"implementation_prompt": "The next step stays attached attached to the accepted state."},
    )

    repaired = repair_greenfield_package_once(
        package,
        patchset_request={
            "status": "repairable",
            "operations": [
                _mechanical_copy_operation(
                    "next_steps",
                    target_path="prewrite_package.next_steps_preview",
                )
            ],
        },
    )

    assert repaired.rendered_component_specs == package.rendered_component_specs
    assert repaired.next_steps_preview == package.next_steps_preview


def test_package_repair_does_not_mutate_exact_preview_leaf() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        next_steps_preview={
            "implementation_prompt": "The next step stays attached attached to the accepted state.",
            "operator_sequence": [
                "Review the accepted accepted brief.",
                "Open the first workstream.",
            ],
        },
    )

    repaired = repair_greenfield_package_once(
        package,
        patchset_request={
            "status": "repairable",
            "operations": [
                _mechanical_copy_operation(
                    "next_steps",
                    target_path="prewrite_package.next_steps_preview.operator_sequence[0]",
                )
            ],
        },
    )

    assert repaired == package


def test_package_repair_does_not_mutate_indexed_preview_leaf_paths() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        accepted_project_preview={
            "created": {
                "components": [
                    {
                        "feature_history": [
                            {"summary": "The accepted state state remains visible."},
                        ],
                    },
                ],
            },
        },
        project_dashboard_preview={
            "host_handoff_prompts": [
                {"prompt": "The implementation prompt prompt stays visible."},
            ],
        },
    )

    repaired = repair_greenfield_package_once(package)

    assert repaired == package


def test_package_repair_reports_project_dashboard_non_prompt_leaf_without_mutating() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        project_dashboard_preview={
            "overview": {"summary": "The dashboard dashboard keeps governed state visible."},
        },
    )

    findings = package_artifact_findings(package)
    generated = [item for item in findings if item.code == "generated_copy_quality"]
    repaired = repair_greenfield_package_once(package)

    assert [item.target_path for item in generated] == [
        "prewrite_package.project_dashboard_preview.overview.summary"
    ]
    assert repaired == package


def test_package_repair_loop_preserves_indexed_and_dashboard_preview_copy_findings() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        accepted_project_preview={
            "created": {
                "components": [
                    {
                        "feature_history": [
                            {"summary": "The accepted state state remains visible."},
                        ],
                    },
                ],
            },
        },
        project_dashboard_preview={
            "overview": {"summary": "The dashboard dashboard keeps governed state visible."},
        },
    )

    result = repair_greenfield_package_until_clean(package)

    assert result.changed is False
    assert result.report == result.initial_report
    assert "accepted-project memory preview leaked adjacent duplicate word prose" in result.initial_report.issues
    assert "project dashboard preview leaked adjacent duplicate word prose" in result.initial_report.issues
    assert "accepted-project memory preview leaked adjacent duplicate word prose" in result.report.issues
    assert "project dashboard preview leaked adjacent duplicate word prose" in result.report.issues


def test_package_quality_findings_emit_source_fact_repair_path_for_preview_leaf() -> None:
    package = GreenfieldCompletionPackage(
        proposal={
            "intent": {
                "first_path": "The operator records intake evidence and sees an accepted decision.",
            },
            "semantic_model": {
                "first_path_contract": {
                    "raw_path": "The operator records intake evidence and sees an accepted decision.",
                },
            },
        },
        next_steps_preview={
            "implementation_prompt": "The next step stays attached attached to the accepted state.",
            "verification_commands": ["./.odylith/bin/odylith validate plan-workstream-binding --repo-root ."],
        },
    )

    findings = package_artifact_findings(package)
    generated = [item for item in findings if item.code == "generated_copy_quality"]

    assert [item.target_path for item in generated] == [
        "prewrite_package.next_steps_preview.implementation_prompt"
    ]
    patchset = patchset_request_from_findings(tuple(generated)).to_dict()
    assert patchset["operations"][0]["target_layer"] == "semantic_model"
    assert patchset["operations"][0]["target_path"] == "semantic_model.first_path_contract"
    assert patchset["operations"][0]["semantic_node_id"] == "SemanticModelIR.first_path_contract"
    assert patchset["operations"][0]["affected_projections"] == ("next_steps", "project_dashboard")


def test_accepted_project_preview_proposal_copy_targets_artifact_plan_source() -> None:
    package = GreenfieldCompletionPackage(
        proposal={
            "diagrams": [
                {
                    "slug": "first-path",
                    "mermaid_source": "flowchart TD\n    A[\"State state remains visible\"]",
                }
            ]
        },
        accepted_project_preview={
            "proposal": {
                "diagrams": [
                    {
                        "slug": "first-path",
                        "mermaid_source": "flowchart TD\n    A[\"State state remains visible\"]",
                    }
                ]
            }
        },
    )

    generated = [item for item in package_artifact_findings(package) if item.code == "generated_copy_quality"]

    assert [item.target_path for item in generated] == [
        "prewrite_package.accepted_project_preview.proposal.diagrams[0].mermaid_source"
    ]
    patchset = patchset_request_from_findings(tuple(generated)).to_dict()
    assert patchset["operations"][0]["target_layer"] == "artifact_plan"
    assert patchset["operations"][0]["target_path"] == "diagrams[0].mermaid_source"
    assert patchset["operations"][0]["affected_projections"] == (
        "atlas",
        "accepted_project",
        "project_dashboard",
    )


def test_mermaid_source_preview_units_inspect_visible_labels_not_graph_syntax() -> None:
    clean_mermaid = (
        "flowchart LR\n"
        "  actor1[\"City Staff\"] --> component1\n"
        "  component1[\"Flood Shelter Intake System<br/>Intake Register Service\"]\n"
        "  component1 --> component2\n"
        "  component2[\"Flood Shelter Intake System<br/>Review Workspace\"]\n"
        "  class component1,component2 service;"
    )
    package = GreenfieldCompletionPackage(
        proposal={"diagrams": [{"mermaid_source": clean_mermaid}]},
        accepted_project_preview={"proposal": {"diagrams": [{"mermaid_source": clean_mermaid}]}},
    )

    generated = [item for item in package_artifact_findings(package) if item.code == "generated_copy_quality"]

    assert generated == []


def test_project_dashboard_preview_contract_copy_targets_semantic_first_path() -> None:
    package = GreenfieldCompletionPackage(
        proposal={
            "intent": {
                "first_path": "The operator records intake evidence and receives a review proof.",
            },
            "semantic_model": {
                "first_path_contract": {
                    "raw_path": "The operator records intake evidence and receives a review proof.",
                },
            },
        },
        project_dashboard_preview={
            "product_story": {
                "release_contract": [
                    {
                        "label": "User Problem",
                        "body": (
                            "Operators need one clear place to collect evidence, understand progress, "
                            "and avoid manual reconstruction before review begins."
                        ),
                    },
                    {
                        "label": "First Path",
                        "body": "The operator records intake evidence and receives receives a review proof.",
                    },
                ],
            }
        },
    )

    generated = [item for item in package_artifact_findings(package) if item.code == "generated_copy_quality"]

    assert [item.target_path for item in generated] == [
        "prewrite_package.project_dashboard_preview.product_story.release_contract[1].body"
    ]
    patchset = patchset_request_from_findings(tuple(generated)).to_dict()
    assert patchset["operations"][0]["target_layer"] == "semantic_model"
    assert patchset["operations"][0]["target_path"] == "semantic_model.first_path_contract"
    assert patchset["operations"][0]["operation_kind"] == "semantic_first_path"
    assert patchset["operations"][0]["affected_projections"] == ("project_dashboard",)


def test_project_dashboard_preview_boundary_card_targets_artifact_plan_not_first_path() -> None:
    clean_body = (
        "Operators need one clear place to collect evidence, understand progress, "
        "and avoid manual reconstruction before review begins."
    )
    package = GreenfieldCompletionPackage(
        proposal={
            "project_brief": {
                "operating_principle": (
                    "The release stays limited to the first accepted path and leaves broader variants for later proof."
                ),
            },
        },
        project_dashboard_preview={
            "product_story": {
                "release_contract": [
                    {"label": "User Problem", "body": clean_body},
                    {"label": "First Path", "body": clean_body},
                    {
                        "label": "Product Boundary",
                        "body": (
                            "The release stays inside boundary boundary decisions until the next operating path "
                            "has evidence that reviewers can inspect."
                        ),
                    },
                    {"label": "Owned Capabilities", "body": clean_body},
                    {"label": "Proof", "body": clean_body},
                ],
            }
        },
    )

    generated = [item for item in package_artifact_findings(package) if item.code == "generated_copy_quality"]

    assert [item.target_path for item in generated] == [
        "prewrite_package.project_dashboard_preview.product_story.release_contract[2].body"
    ]
    patchset = patchset_request_from_findings(tuple(generated)).to_dict()
    assert patchset["operations"][0]["target_layer"] == "artifact_plan"
    assert patchset["operations"][0]["target_path"] == "project_brief.operating_principle"
    assert patchset["operations"][0]["operation_kind"] == "artifact_plan_projection"
    assert patchset["operations"][0]["affected_projections"] == (
        "project_brief",
        "accepted_project",
        "project_dashboard",
        "compass",
        "next_steps",
    )


def test_project_dashboard_preview_proof_card_targets_proof_boundary() -> None:
    clean_body = (
        "Operators need one clear place to collect evidence, understand progress, "
        "and avoid manual reconstruction before review begins."
    )
    package = GreenfieldCompletionPackage(
        proposal={
            "semantic_model": {
                "domain_ontology": {
                    "proof_boundary": "The release proof links the saved result, reviewer context, and validation evidence.",
                },
            },
        },
        project_dashboard_preview={
            "product_story": {
                "release_contract": [
                    {"label": "User Problem", "body": clean_body},
                    {"label": "First Path", "body": clean_body},
                    {"label": "Product Boundary", "body": clean_body},
                    {"label": "Owned Capabilities", "body": clean_body},
                    {
                        "label": "Proof",
                        "body": (
                            "The proof proof keeps the accepted result, review context, and validation evidence "
                            "visible before release."
                        ),
                    },
                ],
            }
        },
    )

    generated = [item for item in package_artifact_findings(package) if item.code == "generated_copy_quality"]

    assert [item.target_path for item in generated] == [
        "prewrite_package.project_dashboard_preview.product_story.release_contract[4].body"
    ]
    patchset = patchset_request_from_findings(tuple(generated)).to_dict()
    assert patchset["operations"][0]["target_layer"] == "semantic_model"
    assert patchset["operations"][0]["target_path"] == "semantic_model.domain_ontology.proof_boundary"
    assert patchset["operations"][0]["operation_kind"] == "semantic_proof_boundary"


def test_package_report_suppresses_legacy_broad_repair_target_when_exact_leaf_exists() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        next_steps_preview={
            "implementation_prompt": "The next step stays attached attached to the accepted state.",
        },
    )

    report = build_greenfield_package_report(package)
    generated = [item for item in report.findings if item.code == "generated_copy_quality"]

    assert [item.target_path for item in generated] == [
        "prewrite_package.next_steps_preview.implementation_prompt"
    ]
    assert all("prewrite_package.next_steps." not in item.target_path for item in generated)
    assert all(item.repairability == "plan_patch" for item in generated)


def test_package_repair_reports_exact_compass_preview_leaf_without_mutating() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        compass_memory_preview={
            "summary": "The accepted state state remains visible.",
            "proof": "Release proof stays attached attached to the decision.",
        },
    )

    report = build_greenfield_package_report(package)
    generated = [item for item in report.findings if item.code == "generated_copy_quality"]
    assert [item.target_path for item in generated] == [
        "prewrite_package.compass_memory_preview.summary",
        "prewrite_package.compass_memory_preview.proof",
    ]

    patchset = patchset_request_from_findings(tuple(generated)).to_dict()
    repaired = repair_greenfield_package_once(package, patchset_request=patchset)

    assert repaired == package


def test_package_repair_preserves_markdown_plan_link_targets() -> None:
    summary = (
        "2026-06-25: Registered Flood Shelter Intake System Intake Register Service as a planned service from user intent "
        "(Plan: [B-002](odylith/radar/radar.html?view=plan&workstream=B-002))."
    )
    package = GreenfieldCompletionPackage(
        proposal={},
        component_registry_preview=(
            {
                "component_id": "intake-register",
                "feature_history": [{"date": "2026-06-25", "summary": summary}],
            },
        ),
        rendered_component_specs={"spec.md": f"## Feature History\n- {summary}\n"},
    )

    repaired = repair_greenfield_package_once(package)

    repaired_summary = repaired.component_registry_preview[0]["feature_history"][0]["summary"]
    assert repaired == package
    assert "odylith/radar/radar.html?view=plan&workstream=B-002" in repaired_summary
    assert "radar. html? view=plan" not in repaired_summary
    assert "odylith/radar/radar.html?view=plan&workstream=B-002" in repaired.rendered_component_specs["spec.md"]


def test_final_next_steps_quality_fails_closed_on_duplicate_copy() -> None:
    with pytest.raises(ValueError, match="final next-steps quality failed"):
        greenfield_apply_write._raise_for_final_next_steps_quality(
            {
                "start_workstream_id": "B-002",
                "validation_gates": [
                    "Flood Shelter Intake System Intake Register Service owns flood shelter intake intake register evidence, review rules, and result visibility",
                    "Flood Shelter Intake System Intake Register Service blocks incomplete evidence before presenting a result, then explains what has to change for flood shelter intake intake register",
                ],
            }
        )


def test_final_next_steps_quality_preserves_release_selector_tokens() -> None:
    next_steps = (
        {
            "release_selector": "0.0.1",
            "customization_options": [
                "External systems: Confirm whether release 0.0.1 needs these external systems: Browser runtime.",
                "Release ambition: Keep 0.0.1 to the accepted first path.",
            ],
            "coding_readiness_gates": [
                "Release 0.0.1 has proof checks for success, failure, replay, access, and review evidence."
            ],
            "operator_sequence": [
                "Open the progress view and verify the active wave `first proof` plus release `0.0.1` match the accepted project shape."
            ],
        }
    )

    greenfield_apply_write._raise_for_final_next_steps_quality(next_steps)
    rendered = json.dumps(next_steps, sort_keys=True)
    assert "0.0.1" in rendered
    assert "0. 0. 1" not in rendered


def test_greenfield_dashboard_refresh_fails_closed_on_visibility_failure(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        greenfield_apply_write.owned_surface_refresh,
        "raise_for_failed_refreshes",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("Atlas render failed")),
    )

    with pytest.raises(RuntimeError, match="Atlas render failed"):
        greenfield_apply_write._refresh_greenfield_dashboard(repo_root=tmp_path)  # noqa: SLF001


def test_greenfield_rendered_surface_custody_requires_atlas_assets_and_fingerprints(tmp_path) -> None:
    atlas_root = tmp_path / "odylith/atlas"
    source_root = atlas_root / "source"
    catalog_path = source_root / "catalog/diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    for relative in ("atlas.html", "mermaid-payload.v1.js", "mermaid-app.v1.js"):
        (atlas_root / relative).write_text("rendered\n", encoding="utf-8")
    (source_root / "demo.svg").write_text("<svg />\n", encoding="utf-8")
    catalog_path.write_text(
        json.dumps(
            {
                "diagrams": [
                    {
                        "diagram_id": "D-001",
                        "source_svg": "odylith/atlas/source/demo.svg",
                        "source_png": "odylith/atlas/source/demo.png",
                        "render_source_fingerprint": "",
                        "reviewed_watch_fingerprints": {},
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError) as exc_info:
        greenfield_apply_diagrams.raise_for_greenfield_rendered_surface_custody(  # noqa: SLF001
            repo_root=tmp_path,
            diagram_ids=("D-001",),
        )

    message = str(exc_info.value)
    assert "D-001: missing rendered Atlas source_png" in message
    assert "D-001: missing Atlas render_source_fingerprint" in message
    assert "D-001: missing Atlas reviewed_watch_fingerprints" in message


def test_robotic_safety_parent_workstream_uses_proof_subject_and_visible_status() -> None:
    intent = parse_confirmed_intent_text(
        """
# Robotic Warehouse Safety Stop Console

## Product story
Warehouse operators need a safety console that makes blocked aisles, impacted robots, inventory moves, stop decisions, overrides, maintenance actions, and recovery evidence visible before automation resumes.

## State object
A robotics exception record tracks aisle blocker, impacted robots, inventory moves, stop or resume decision, safety reviewer approval, override reason, maintenance action, incident evidence, and recovery status.

## First complete path
A floor operator reports a blocked aisle, the console maps impacted robots and moves, a safety reviewer confirms whether to stop or resume automation, maintenance records corrective action, and operations receives recovery status with unsafe states still visible.

## Human actors
- Floor operator who reports blocked aisles and exceptions
- Safety reviewer who approves stop or resume decisions
- Maintenance technician who records corrective action
- Operations lead who accepts recovery status
- Automation supervisor who reviews overrides

## External systems
- Warehouse robot control system
- Inventory movement system
- Safety interlock telemetry
- Maintenance ticketing system

## Internal systems
- Exception intake console
- Robot impact mapper
- Safety stop decision ledger
- Override and interlock tracker
- Maintenance recovery record
- Operations readiness view

## Critical assumptions
- Unsafe states must stop the first path rather than be hidden.
- The product records safety decisions and handoffs but does not bypass physical interlocks.
- Recovery needs evidence before automation resumes.

## Ambiguities
- Whether robot commands are sent directly or exported for the control system.
- Which incident evidence is mandatory for each stop class.

## Proof boundary
Release 0.0.1 succeeds when one blocked aisle incident can stop automation, record impacted robots and inventory moves, capture corrective action, and show reviewed recovery status before resume.
""",
        prompt="Robotic warehouse safety stop console",
    )
    proposal = build_confirmed_greenfield_proposal(
        prompt="Robotic warehouse safety stop console",
        title="Robotic Warehouse Safety Stop Console",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert generated_semantic_slop_issues(proposal) == []
    assert "proves map impacted robots" not in rendered
    assert "maping impacted robots" not in rendered
    assert "letting the safety reviewer state still visible" not in rendered
    assert "proves mapping impacted robots and moves" in rendered
    assert "letting the safety reviewer see the recovery status with unsafe states still visible" in rendered


def test_confirmed_intent_accepts_trustworthy_when_proof_boundary() -> None:
    intent = parse_confirmed_intent_text(
        """
# Sewing Pattern Relief Planner

## Product story
A garment maker needs to understand where a sewing pattern may feel tight before cutting fabric. A fitting coach needs a repeatable adjustment record that explains measurements, garment ease, suggested adjustment, and risk notes.

## State object
A pattern adjustment record tracks garment type, wearer measurements, pattern size, target ease, pressure areas, suggested adjustment, rationale, fitting notes, and approval status.

## First complete path
Garment Maker enters measurements, chooses a garment pattern, reviews pressure areas, accepts a suggested adjustment, and receives an adjustment plan with rationale and fitting notes.

## Human actors
- Garment maker who enters measurements and reviews the adjustment
- Fitting coach who approves adjustment guidance
- Pattern librarian who maintains garment pattern data

## Internal systems
- Measurement intake workflow
- Pattern comparison model
- Adjustment recommendation service
- Fitting-note review workspace

## Proof boundary
Release 0.0.1 is trustworthy when one garment maker can produce an adjustment plan and a fitting coach can inspect the rationale.
""",
        prompt="Draft a greenfield proposal for a sewing pattern relief planner",
    )

    assert intent["proof_boundary"].startswith("Release 0.0.1 is trustworthy when")


def test_accepted_project_memory_avoids_compact_action_splice_after_capability() -> None:
    intent = complete_confirmed_intent(
        parse_confirmed_intent_text(
            """
# Choice Practice Learning App

## Product story
A parent needs a child-safe practice app where a learner can make one guided choice and give the parent a simple recap.

## State object
A practice session record tracks learner profile, scenario, selected choice, consequence, reflection answer, parent recap status, and safety review notes.

## First complete path
Operator creates a learner profile, starts one scenario, lets the learner choose an option, shows the consequence and reflection prompt, and saves a parent recap with safety notes.

## Human actors
- Parent who sets up the learner and reviews the recap
- Learner who makes the guided choice and reflection
- Content reviewer who approves scenarios and safety notes

## Internal systems
- Learner profile and consent setup
- Scenario and choice engine
- Reflection capture workflow
- Parent recap and safety review

## Proof boundary
Release 0.0.1 is trustworthy when one learner can complete a scenario and the parent can review the recap.
""",
            prompt="Draft a greenfield proposal for a child choice-practice learning app",
        )
    )
    proposal = build_confirmed_greenfield_proposal(
        prompt="Draft a greenfield proposal for a child choice-practice learning app",
        title="Choice Practice Learning App",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    payload = build_accepted_project_source_payload(
        proposal=proposal,
        backlog_items=[],
        component_items=[],
        diagram_ids=[],
        release_selector="0.0.1",
        release_id="release-choice-practice-0-0-1",
        validation_gate={"status": "passed"},
    )

    assert generated_public_copy_issues("accepted-project memory preview", payload) == ()


def test_greenfield_quality_gate_ignores_apply_result_operational_metadata() -> None:
    payload = {
        "intent": {"prompt": "Draft a greenfield proposal for a request workspace"},
        "validation_gate": {
            "dimensions": {
                "artifact_substance": "Radar, Registry, Atlas, and Compass surfaces refreshed."
            }
        },
        "commit_manifest": {
            "quality_lenses": {
                "lenses": [
                    {"role": "architect", "checks": [{"evidence": "Atlas diagram count is complete."}]}
                ]
            }
        },
        "next_steps": {
            "verification_commands": [
                "./.odylith/bin/odylith context --repo-root . B-001",
            ]
        },
    }

    assert greenfield_quality_issues(payload) == []


def test_terminal_result_chain_allows_captured_reflection_before_completion_action() -> None:
    assert generated_public_copy_issues(
        "first path",
        "The learner writes or records a short reflection, completes the session, and the parent opens a recap.",
    ) == ()
    assert generated_public_copy_issues(
        "bad result",
        "The visible result and completes the session.",
    ) == ("bad result leaked terminal action inside result prose",)


def test_contrastive_drift_allows_recommendation_when_intent_says_suggested() -> None:
    proposal = {
        "intent": {
            "title": "Adjustment Planner",
            "product_story": "A maker reviews a suggested adjustment before accepting a change plan.",
            "state_object": "An adjustment plan with suggested adjustment, rationale, and review status.",
            "first_path": "A maker reviews a suggested adjustment and saves the accepted plan.",
            "proof_boundary": "Release succeeds when the suggested adjustment can be reviewed.",
        },
        "components": [
            {
                "label": "Adjustment Review Service",
                "source_system_description": "keeps the suggested adjustment reviewable",
                "component_contract": {
                    "owned_state": (
                        "recommendation result, recommendation rationale, recommendation evidence, "
                        "recommendation status, recommendation blocker, recommendation review, "
                        "recommendation handoff, and recommendation history"
                    )
                },
            }
        ],
    }

    assert contrastive_domain_drift_issues(proposal, {}) == []


def test_product_risks_strip_bare_actor_label_from_weak_input_clause() -> None:
    risks = build_product_risks(
        title="Municipal Permit Review Portal",
        product_story=(
            "A resident needs one clear online path to request a small building permit, provide required project details, "
            "receive corrections when information is missing, and see the review decision."
        ),
        first_path=(
            "Resident Applicant selects the permit type, enters project details, attaches required documents, "
            "pays the fee, and receives an approved or rejected permit decision with reviewer notes."
        ),
        state_object="A permit application record with applicant identity, submitted documents, status, and decision notes.",
        proof_boundary=(
            "Release 0.0.1 is trustworthy when one resident can submit a permit application and inspect the decision evidence."
        ),
        human_actors=[
            "Resident Applicant: submits project details and corrections",
            "Permit Reviewer: checks zoning and document completeness",
        ],
        release="0.0.1",
    )
    rendered = json.dumps(risks, sort_keys=True)

    assert "resident Applicant" not in rendered
    assert "weak inputs are the permit type" in rendered
    assert generated_semantic_slop_issues({"risks": risks}) == []


def test_product_risks_use_object_from_compound_input_action() -> None:
    risks = build_product_risks(
        title="Gene Expression Simulation Model",
        product_story=(
            "A research workspace helps scientists run and review gene expression prediction experiments."
        ),
        first_path=(
            "A researcher uploads or selects a small expression dataset, defines the biological context "
            "and prediction target, runs a simulation, and saves the result as a reviewable experiment."
        ),
        state_object="A gene expression simulation run tracks input dataset, model version, outputs, and review notes.",
        proof_boundary=(
            "Release 0.0.1 succeeds when one researcher can reopen the saved run with the same inputs."
        ),
        human_actors=["Researcher", "Scientific reviewer"],
        release="0.0.1",
    )
    rendered = json.dumps(risks, sort_keys=True)

    assert "weak inputs are or selects" not in rendered
    assert "weak inputs are a small expression dataset" in rendered
    assert generated_semantic_slop_issues({"risks": risks}) == []


def test_product_risks_describe_noun_focus_as_information_for_activity() -> None:
    risks = build_product_risks(
        title="Practice Session Workspace",
        product_story="A learner needs one place to complete a practice session and leave usable evidence.",
        first_path="A learner opens the lab session and sees a visible summary.",
        state_object="A lab session with selected scenario, attempt history, visible result, and completion status.",
        proof_boundary="Release 0.0.1 succeeds when one learner can complete a session and see a summary.",
        human_actors=["Learner", "Coach"],
        release="0.0.1",
    )
    raw_rendered = json.dumps(risks, sort_keys=True)
    rendered = raw_rendered.casefold()

    assert "provides lab session" not in rendered
    assert "provides information for lab session" in rendered
    assert "wrong person. the learner" not in raw_rendered
    assert generated_semantic_slop_issues({"risks": risks}) == []


def test_product_risks_turn_abstract_boundary_actor_into_review_role() -> None:
    risks = build_product_risks(
        title="Autonomous Incident Review Workspace",
        product_story="A review team needs one workspace to explain incident evidence and release readiness.",
        first_path=(
            "Operators capture mission logs, statements, sensor anomalies, safety hold decisions, "
            "corrective actions, and release-readiness proof."
        ),
        state_object="An incident review record with mission logs, safety hold decisions, corrective actions, and proof status.",
        proof_boundary="Release 0.0.1 succeeds when the review path explains evidence and readiness without controlling hardware.",
        human_actors=["Safety: needs the product to hold decisions and keep the result visible and reviewable"],
        release="0.0.1",
    )
    rendered = json.dumps(risks, sort_keys=True)

    assert "the safety may" not in rendered
    assert "for the safety." not in rendered
    assert "for the safety reviewer" in rendered
    assert generated_semantic_slop_issues({"risks": risks}) == []


def test_product_risks_nominalize_actor_led_decision_pair_outcomes() -> None:
    reject_risks = build_product_risks(
        title="Evidence Review Desk",
        product_story="Review teams need a clear evidence path before readiness decisions are trusted.",
        first_path=(
            "Intake coordinator records one case packet, reviewer checks required evidence, "
            "approval reviewer approves or rejects release readiness."
        ),
        state_object="A review record with packet evidence, reviewer decision, and readiness status.",
        proof_boundary="Release 0.0.1 proves one packet can be reviewed with decision evidence.",
        human_actors=["Intake coordinator", "Reviewer", "Approval reviewer"],
        release="0.0.1",
    )
    reject_rendered = json.dumps(reject_risks, sort_keys=True)

    assert "the approval or rejection of release readiness" in reject_rendered
    assert "product produced approval reviewer approves" not in reject_rendered
    assert "approves or reject" not in reject_rendered
    assert generated_semantic_slop_issues({"risks": reject_risks}) == []

    block_risks = build_product_risks(
        title="Battery Materials Release Evidence Desk",
        product_story="A lab team needs one place to record batch evidence and approve or block a first manufacturing handoff.",
        first_path=(
            "A materials intake coordinator records one lab batch, attaches required test evidence, "
            "a reviewer checks readiness criteria, and the release owner approves or blocks manufacturing readiness."
        ),
        state_object="A lab batch readiness record with material identity, review evidence, and release status.",
        proof_boundary="Release 0.0.1 succeeds when a release owner can approve or block the handoff.",
        human_actors=["Materials intake coordinator", "Technical reviewer", "Release owner"],
        release="0.0.1",
    )
    block_rendered = json.dumps(block_risks, sort_keys=True)

    assert "the approval or blocking of manufacturing readiness" in block_rendered
    assert "product produced the release owner approves" not in block_rendered
    assert generated_semantic_slop_issues({"risks": block_risks}) == []


def test_workstream_titles_compact_while_keeping_clauses() -> None:
    workflow_title, _boundary_title, _proof_title = confirmed_workstream_titles(
        label="Case Preparation Workspace",
        components=[
            {"label": "Case Preparation Workspace Intake Register Service"},
            {"label": "Case Preparation Workspace Review Workspace"},
            {"label": "Case Preparation Workspace Proof Ledger"},
        ],
        internal_systems=[],
        first_path=(
            "Legal aid teams organize client statements, country-condition evidence, deadline risk, "
            "interpreter needs, affidavit review, and filing readiness while keeping legal signoff "
            "separate from evidence collection."
        ),
        state_object="A case preparation record with statements, evidence, deadline risk, review notes, and filing readiness.",
        proof_boundary="Release 0.0.1 succeeds when the case preparation record is reviewable and legal signoff stays separate.",
        human_actors=["Case Preparation Workspace User: needs the product to hold decisions and keep the result visible"],
    )

    assert "While Keeping" not in workflow_title
    assert "with Legal Signoff Separate" in workflow_title


def test_workstream_titles_drop_actor_context_clause_before_title_clipping() -> None:
    workflow_title, _boundary_title, _proof_title = confirmed_workstream_titles(
        label="Museum Loan Provenance Exchange",
        components=[
            {"label": "Artifact Loan Request Service"},
            {"label": "Condition Report Review Service"},
            {"label": "Provenance Proof Ledger"},
        ],
        internal_systems=[],
        first_path=(
            "Curators coordinate artifact loan requests, condition reports, insurer evidence, courier handoff plans, "
            "conservation constraints, and curator signoff before an inter-museum transfer is accepted."
        ),
        state_object=(
            "An artifact loan record with provenance evidence, condition report, insurer evidence, "
            "courier handoff plan, conservation constraints, and curator signoff."
        ),
        proof_boundary=(
            "Release 0.0.1 succeeds when an inter-museum transfer is accepted with provenance, "
            "condition, insurer, courier, conservation, and curator signoff evidence."
        ),
        human_actors=["curator signoff before an inter-museum transfer is accepted"],
    )

    assert workflow_title == "Let Curator Coordinate Artifact Loan Requests"
    assert "Before an" not in workflow_title
    assert not workflow_title.endswith(" an")


def test_component_specs_strip_coordinated_actions_from_owned_artifact_slots() -> None:
    intent = complete_confirmed_intent(
        parse_confirmed_intent_text(
            """
# Solar Energy Optimization Workspace

## Product story
A building owner needs a daily plan that compares solar production, consumption, and battery state before choosing load timing.

## State object
An energy plan day tracks solar forecast, expected consumption profile, battery state, selected load window, recommendation status, and plan history.

## First complete path
An energy manager imports or enters a solar forecast, adds an expected consumption profile, enters current battery state, chooses one flexible load, reviews the recommended run window, and sees the updated daily plan.

## Human actors
- Energy manager who prepares the daily plan and reviews recommendations

## Internal systems
- Solar forecast intake.
- Consumption profile builder.
- Battery and tariff constraint model.
- Daily energy plan view.

## Proof boundary
Release 0.0.1 succeeds when one energy manager can create a daily plan, receive a recommended load window, and see the reason while missing forecasts or battery constraints block misleading recommendations.
""",
            prompt="An app that optimizes the production and consumption of solar energy",
        )
    )
    proposal = build_confirmed_greenfield_proposal(
        prompt="An app that optimizes the production and consumption of solar energy",
        title="Solar Energy Optimization Workspace",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    component = next(row for row in proposal["components"] if "Consumption Profile" in row["label"])
    spec = build_narrative_component_spec(
        component_id=component["component_id"],
        label=component["label"],
        path="src/example/consumption_profile_builder",
        kind=component.get("kind", "service"),
        status=component.get("status", "planned"),
        sources=("user_intent",),
        workstreams=("B-002",),
        responsibility=component.get("responsibility", ""),
        implementation_handoff={"workstream_id": "B-002", "workstream_title": "Build the consumption profile"},
        component_contract=component["component_contract"],
    )

    assert "and adds expected consumption profile" not in spec
    assert "and expected consumption profile" in spec
