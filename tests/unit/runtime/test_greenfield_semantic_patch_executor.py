from __future__ import annotations

from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_post_confirm_patch_apply
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import GreenfieldPostConfirmRepairContext
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionReport
from odylith.runtime.domain_intelligence.greenfield_semantic_patch_executor import apply_semantic_patch_operations
from odylith.runtime.domain_intelligence.greenfield_semantic_patch_executor import (
    apply_semantic_patch_operations_detailed,
)


def test_semantic_patch_executor_applies_replacement_fact_and_records_ledger() -> None:
    proposal: dict[str, Any] = {
        "intent": {
            "title": "Decision Evidence Workspace",
            "first_path": "A decision evidence workspace for review teams.",
        },
        "semantic_model": {"stale": True},
    }
    operations = [
        {
            "operation_id": "semantic-patch-1",
            "target_layer": "semantic_model",
            "target_path": "semantic_model.first_path_contract",
            "semantic_node_id": "SemanticModelIR.first_path_contract",
            "issue_code": "semantic_alignment",
            "replacement_fact": {
                "first_path": "A reviewer records evidence, compares open risks, and sees the release decision."
            },
            "decision_ledger_entry": {
                "ambiguity": "record was interpreted as a user action instead of a governance object."
            },
            "rejected_interpretation": "record as a governance artifact",
            "confidence": 0.91,
        }
    ]

    changed = apply_semantic_patch_operations(proposal, operations)

    assert changed is True
    assert proposal["intent"]["first_path"] == (
        "A reviewer records evidence, compares open risks, and sees the release decision."
    )
    assert proposal["semantic_model"]["stale"] is True
    assert proposal["semantic_model"]["first_path_contract"]["raw_path"] == (
        "A reviewer records evidence, compares open risks, and sees the release decision."
    )
    assert proposal["semantic_model"]["first_path_contract"]["capability"]
    assert proposal["semantic_patch_ledger"] == [
        {
            "ambiguity": "record was interpreted as a user action instead of a governance object.",
            "applied_field": "semantic_model.first_path_contract.raw_path",
            "operation_id": "semantic-patch-1",
            "target_path": "semantic_model.first_path_contract",
            "semantic_node_id": "SemanticModelIR.first_path_contract",
            "issue_code": "semantic_alignment",
            "rejected_interpretation": "record as a governance artifact",
            "confidence": 0.91,
        }
    ]


def test_semantic_patch_executor_rejects_non_action_first_path_replacement() -> None:
    proposal: dict[str, Any] = {
        "intent": {
            "title": "Decision Evidence Workspace",
            "first_path": "A reviewer records evidence, compares open risks, and sees the release decision.",
        },
        "semantic_model": {"stable": True},
    }

    changed = apply_semantic_patch_operations(
        proposal,
        [
            {
                "target_layer": "semantic_model",
                "target_path": "semantic_model.first_path_contract",
                "semantic_node_id": "SemanticModelIR.first_path_contract",
                "replacement_fact": {"first_path": "A decision evidence workspace for teams."},
            }
        ],
    )

    assert changed is False
    assert proposal["intent"]["first_path"] == (
        "A reviewer records evidence, compares open risks, and sees the release decision."
    )
    assert proposal["semantic_model"] == {"stable": True}
    assert "semantic_patch_ledger" not in proposal


def test_semantic_patch_executor_routes_external_systems_without_rewriting_internal_systems() -> None:
    proposal: dict[str, Any] = {
        "intent": {
            "title": "Evidence Decision Workspace",
            "internal_systems": ["Decision Ledger"],
            "external_systems": ["Legacy Import Feed"],
        },
        "semantic_model": {"stale": True},
    }

    changed = apply_semantic_patch_operations(
        proposal,
        [
            {
                "operation_id": "external-system-repair",
                "target_layer": "semantic_model",
                "target_path": "semantic_model.external_systems",
                "semantic_node_id": "SemanticModelIR.external_systems",
                "replacement_fact": {"external_systems": ["Partner Evidence Feed"]},
                "proof_obligation_delta": {
                    "add": ["Replay proof must name the external feed version."]
                },
            }
        ],
    )

    assert changed is True
    assert proposal["intent"]["internal_systems"] == ["Decision Ledger"]
    assert proposal["intent"]["external_systems"] == ["Partner Evidence Feed"]
    assert proposal["semantic_model"]["stale"] is True
    assert proposal["semantic_model"]["domain_ontology"]["external_systems"] == ["Partner Evidence Feed"]
    assert proposal["semantic_patch_ledger"][0]["applied_field"] == (
        "semantic_model.domain_ontology.external_systems"
    )
    assert proposal["semantic_patch_ledger"][0]["proof_obligation_delta"] == {
        "add": ["Replay proof must name the external feed version."]
    }


def test_semantic_patch_executor_records_host_adjudication_for_idempotent_fact() -> None:
    proposal: dict[str, Any] = {
        "intent": {
            "title": "Evidence Decision Workspace",
            "external_systems": ["Partner Evidence Feed"],
        },
        "semantic_model": {
            "domain_ontology": {
                "external_systems": ["Partner Evidence Feed"],
            },
        },
    }

    result = apply_semantic_patch_operations_detailed(
        proposal,
        [
            {
                "operation_id": "external-system-adjudication",
                "target_layer": "semantic_model",
                "target_path": "semantic_model.domain_ontology.external_systems",
                "semantic_node_id": "SemanticModelIR.domain_ontology.external_systems",
                "issue_code": "semantic_alignment",
                "operation_kind": "semantic_external_systems",
                "replacement_fact": {"external_systems": ["Partner Evidence Feed"]},
                "decision_ledger_entry": {
                    "chosen_interpretation": "Partner Evidence Feed is the accepted external system boundary.",
                    "rationale": "The host repair confirmed the existing semantic fact instead of inventing a new one.",
                    "rejected_interpretations": ["Add another external system not present in the accepted intent."],
                },
                "confidence": 0.92,
            }
        ],
    )

    assert result.changed is True
    assert result.applied_fields == ("semantic_model.domain_ontology.external_systems",)
    assert proposal["intent"]["external_systems"] == ["Partner Evidence Feed"]
    assert proposal["semantic_model"]["domain_ontology"]["external_systems"] == ["Partner Evidence Feed"]
    assert proposal["semantic_patch_ledger"] == [
        {
            "chosen_interpretation": "Partner Evidence Feed is the accepted external system boundary.",
            "rationale": "The host repair confirmed the existing semantic fact instead of inventing a new one.",
            "rejected_interpretations": ["Add another external system not present in the accepted intent."],
            "applied_field": "semantic_model.domain_ontology.external_systems",
            "operation_id": "external-system-adjudication",
            "target_path": "semantic_model.domain_ontology.external_systems",
            "semantic_node_id": "SemanticModelIR.domain_ontology.external_systems",
            "issue_code": "semantic_alignment",
            "confidence": 0.92,
        }
    ]


def test_semantic_patch_executor_uses_operation_kind_as_primary_target() -> None:
    proposal: dict[str, Any] = {
        "intent": {
            "title": "Evidence Decision Workspace",
            "state_object": "Old state.",
        },
        "semantic_model": {"stable": True},
    }

    changed = apply_semantic_patch_operations(
        proposal,
        [
            {
                "operation_id": "state-object-repair",
                "target_layer": "semantic_model",
                "operation_kind": "semantic_state_object",
                "target_path": "semantic_model.generic_fact",
                "semantic_node_id": "SemanticModelIR.generic_fact",
                "replacement_fact": {"state_object": "A decision record with evidence, owner, status, and result."},
            }
        ],
    )

    assert changed is True
    assert proposal["intent"]["state_object"] == "A decision record with evidence, owner, status, and result."
    assert proposal["semantic_model"]["domain_ontology"]["state_object"] == (
        "A decision record with evidence, owner, status, and result."
    )
    assert proposal["semantic_patch_ledger"][0]["applied_field"] == (
        "semantic_model.domain_ontology.state_object"
    )


def test_semantic_patch_executor_does_not_route_by_incidental_substrings() -> None:
    proposal: dict[str, Any] = {
        "intent": {
            "title": "Evidence Decision Workspace",
            "human_actors": ["Review Clerk"],
            "internal_systems": ["Decision Ledger"],
        },
        "semantic_model": {"stable": True},
    }

    changed = apply_semantic_patch_operations(
        proposal,
        [
            {
                "operation_id": "unrelated-substring",
                "target_layer": "semantic_model",
                "target_path": "semantic_model.reactor_policy",
                "semantic_node_id": "SemanticModelIR.ecosystem_boundary",
                "replacement_fact": {
                    "actors": ["Incorrect Actor"],
                    "systems": ["Incorrect System"],
                },
            }
        ],
    )

    assert changed is False
    assert proposal["intent"]["human_actors"] == ["Review Clerk"]
    assert proposal["intent"]["internal_systems"] == ["Decision Ledger"]
    assert proposal["semantic_model"] == {"stable": True}
    assert "semantic_patch_ledger" not in proposal


def test_semantic_patch_executor_rejects_partial_exact_path_matches() -> None:
    proposal: dict[str, Any] = {
        "intent": {
            "title": "Evidence Decision Workspace",
            "state_object": "Original state object.",
        },
        "semantic_model": {"stable": True},
    }

    changed = apply_semantic_patch_operations(
        proposal,
        [
            {
                "operation_id": "partial-path",
                "target_layer": "semantic_model",
                "operation_kind": "semantic_fact",
                "target_path": "semantic_model.domain_ontology.state_object_notes",
                "semantic_node_id": "SemanticModelIR.domain_ontology.state_object_notes",
                "replacement_fact": {"state_object": "Incorrectly routed state object."},
            }
        ],
    )

    assert changed is False
    assert proposal["intent"]["state_object"] == "Original state object."
    assert proposal["semantic_model"] == {"stable": True}
    assert "semantic_patch_ledger" not in proposal


def test_semantic_patch_executor_uses_exact_compatibility_paths_without_token_splitting() -> None:
    proposal: dict[str, Any] = {
        "intent": {
            "title": "Evidence Decision Workspace",
            "proof_boundary": "Old proof.",
        },
        "semantic_model": {"stable": True},
    }

    changed = apply_semantic_patch_operations(
        proposal,
        [
            {
                "operation_id": "proof-boundary-repair",
                "target_layer": "semantic_model",
                "target_path": "semantic_model.domain_ontology.proof_boundary",
                "semantic_node_id": "SemanticModelIR.unknown",
                "replacement_fact": {"proof_boundary": "Proof links one decision to evidence and review history."},
            }
        ],
    )

    assert changed is True
    assert proposal["intent"]["proof_boundary"] == "Proof links one decision to evidence and review history."
    assert proposal["semantic_model"]["domain_ontology"]["proof_boundary"] == (
        "Proof links one decision to evidence and review history."
    )


def test_semantic_patch_executor_reports_scoped_non_first_path_application() -> None:
    proposal: dict[str, Any] = {
        "intent": {
            "title": "Evidence Decision Workspace",
            "state_object": "Old state.",
        },
        "semantic_model": {"stable": True},
    }

    application = apply_semantic_patch_operations_detailed(
        proposal,
        [
            {
                "operation_id": "state-object-repair",
                "target_layer": "semantic_model",
                "operation_kind": "semantic_state_object",
                "affected_projections": ["project_brief"],
                "replacement_fact": {"state_object": "A decision record with evidence, owner, status, and result."},
            }
        ],
    )

    assert application.changed is True
    assert application.operation_ids == ("state-object-repair",)
    assert application.applied_fields == ("semantic_model.domain_ontology.state_object",)
    assert application.affected_projections == ("project_brief",)
    assert application.completion_required is False


def test_semantic_patch_executor_requires_completion_without_explicit_scope() -> None:
    proposal: dict[str, Any] = {
        "intent": {
            "title": "Evidence Decision Workspace",
            "state_object": "Old state.",
        },
        "semantic_model": {"stable": True},
    }

    application = apply_semantic_patch_operations_detailed(
        proposal,
        [
            {
                "operation_id": "state-object-repair",
                "target_layer": "semantic_model",
                "operation_kind": "semantic_state_object",
                "replacement_fact": {"state_object": "A decision record with evidence, owner, status, and result."},
            }
        ],
    )

    assert application.changed is True
    assert application.affected_projections == ()
    assert application.completion_required is True


def test_patchset_repair_applies_host_replacement_before_semantic_model_regeneration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "validate_host_reasoned_proposal", lambda _proposal: None)
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "complete_confirmed_proposal",
        lambda proposal, *, release_selector: dict(proposal),
    )
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "repair_greenfield_semantic_projections",
        lambda _proposal: False,
    )
    context = GreenfieldPostConfirmRepairContext(
        pass_index=0,
        elapsed_seconds=1.0,
        budget_seconds=90.0,
        report=GreenfieldCompletionReport(
            status="failed",
            version="greenfield-post-confirm-completion-v1",
            semantic_model=True,
            artifact_counts={},
            tribunal_status="passed",
            issues=("prewrite Radar package missing semantic coverage for first path",),
        ),
        issues=(),
        review_report={"version": "odylith.greenfield.post_confirm.review_report.v1"},
        patchset_request={
            "version": "odylith.greenfield.post_confirm.patchset_request.v1",
            "operations": [
                {
                    "operation_id": "host-semantic-repair",
                    "target_layer": "semantic_model",
                    "target_path": "semantic_model.first_path_contract",
                    "semantic_node_id": "SemanticModelIR.first_path_contract",
                    "issue_code": "semantic_alignment",
                    "replacement_fact": {
                        "first_path": (
                            "An operator reviews incoming evidence, records the acceptance decision, "
                            "and sees the governed release proof."
                        )
                    },
                    "decision_ledger_entry": {
                        "ambiguity": "incoming evidence was chosen as the state-changing object."
                    },
                    "rejected_interpretation": "workspace noun phrase with no user action",
                    "confidence": 0.88,
                }
            ],
        },
        quality_lenses={"lenses": {}},
        semantic_compiler={},
        repair_tier="rescue",
        rescue_activated=True,
    )
    proposal: dict[str, Any] = {
        "intent": {
            "title": "Evidence Decision Workspace",
            "state_object": "A governed evidence decision record.",
            "first_path": "An evidence decision workspace for operators.",
            "human_actors": ["Operator"],
        },
        "components": [],
        "backlog": [],
        "semantic_model": {"stale": True},
    }

    repaired = greenfield_post_confirm_patch_apply.apply_greenfield_patchset_repairs(
        proposal,
        release_selector="0.0.1",
        repair_context=context,
    )

    expected = (
        "An operator reviews incoming evidence, records the acceptance decision, "
        "and sees the governed release proof."
    )
    assert repaired["intent"]["first_path"] == expected
    assert repaired["semantic_model"]["first_path_contract"]["raw_path"] == expected
    assert repaired["semantic_patch_ledger"][0]["applied_field"] == "semantic_model.first_path_contract.raw_path"
    assert repaired["semantic_patch_ledger"][0]["ambiguity"] == (
        "incoming evidence was chosen as the state-changing object."
    )


def test_patchset_repair_skips_completion_for_scoped_non_first_path_semantic_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "validate_host_reasoned_proposal", lambda _proposal: None)
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "normalize_host_reasoned_proposal",
        lambda proposal: dict(proposal),
    )

    def unexpected_completion(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        calls.append("completion")
        return {}

    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "complete_confirmed_proposal", unexpected_completion)
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "ensure_apply_semantic_model", unexpected_completion)
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "repair_greenfield_semantic_projections",
        lambda _proposal: False,
    )
    context = GreenfieldPostConfirmRepairContext(
        pass_index=0,
        elapsed_seconds=1.0,
        budget_seconds=90.0,
        report=GreenfieldCompletionReport(
            status="failed",
            version="greenfield-post-confirm-completion-v1",
            semantic_model=True,
            artifact_counts={},
            tribunal_status="passed",
            issues=("project brief preview state object needs repair",),
        ),
        issues=(),
        review_report={"version": "odylith.greenfield.post_confirm.review_report.v1"},
        patchset_request={
            "version": "odylith.greenfield.post_confirm.patchset_request.v1",
            "operations": [
                {
                    "operation_id": "GF-PATCH-STATE",
                    "target_layer": "semantic_model",
                    "operation_kind": "semantic_state_object",
                    "target_path": "semantic_model.domain_ontology.state_object",
                    "semantic_node_id": "SemanticModelIR.domain_ontology.state_object",
                    "affected_projections": ["project_brief"],
                    "replacement_fact": {"state_object": "A decision record with owner, status, and result."},
                }
            ],
        },
        quality_lenses={"lenses": {}},
        semantic_compiler={},
        repair_tier="rescue",
        rescue_activated=True,
    )

    repaired = greenfield_post_confirm_patch_apply.apply_greenfield_patchset_repairs(
        {"intent": {"title": "Evidence Decision Workspace", "state_object": "Old state."}, "semantic_model": {}},
        release_selector="0.0.1",
        repair_context=context,
    )

    assert calls == []
    assert repaired["intent"]["state_object"] == "A decision record with owner, status, and result."
    application = repaired["post_confirm_patch_application_ledger"][-1]
    assert application["affected_projections"] == ("project_brief",)
    assert application["rerender_projections"] == (
        "project_brief",
        "accepted_project",
        "compass",
        "next_steps",
    )
    assert application["semantic_changed"] is True
    assert application["completion_required"] is False
    assert application["full_prewrite_required"] is False
    assert application["rerender_scope"] == "affected_projections"


def test_patchset_repair_keeps_first_path_semantic_patch_completion_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "validate_host_reasoned_proposal", lambda _proposal: None)
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "normalize_host_reasoned_proposal",
        lambda proposal: dict(proposal),
    )

    def complete(proposal: dict[str, Any], *, release_selector: str) -> dict[str, Any]:
        calls.append(f"complete:{release_selector}")
        return dict(proposal)

    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "complete_confirmed_proposal", complete)
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "ensure_apply_semantic_model",
        lambda proposal, **_kwargs: dict(proposal),
    )
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "repair_greenfield_semantic_projections",
        lambda _proposal: False,
    )
    context = GreenfieldPostConfirmRepairContext(
        pass_index=0,
        elapsed_seconds=1.0,
        budget_seconds=90.0,
        report=GreenfieldCompletionReport(
            status="failed",
            version="greenfield-post-confirm-completion-v1",
            semantic_model=True,
            artifact_counts={},
            tribunal_status="passed",
            issues=("first path needs semantic repair",),
        ),
        issues=(),
        review_report={"version": "odylith.greenfield.post_confirm.review_report.v1"},
        patchset_request={
            "version": "odylith.greenfield.post_confirm.patchset_request.v1",
            "operations": [
                {
                    "operation_id": "GF-PATCH-FIRST-PATH",
                    "target_layer": "semantic_model",
                    "operation_kind": "semantic_first_path",
                    "target_path": "semantic_model.first_path_contract",
                    "semantic_node_id": "SemanticModelIR.first_path_contract",
                    "affected_projections": ["project_brief"],
                    "replacement_fact": {
                        "first_path": "A reviewer records evidence and sees the governed decision."
                    },
                }
            ],
        },
        quality_lenses={"lenses": {}},
        semantic_compiler={},
        repair_tier="rescue",
        rescue_activated=True,
    )

    repaired = greenfield_post_confirm_patch_apply.apply_greenfield_patchset_repairs(
        {
            "intent": {
                "title": "Evidence Decision Workspace",
                "first_path": "A decision workspace for review.",
            },
            "semantic_model": {},
        },
        release_selector="0.0.1",
        repair_context=context,
    )

    assert calls == ["complete:0.0.1"]
    application = repaired["post_confirm_patch_application_ledger"][-1]
    assert application["affected_projections"] == ("project_brief",)
    assert application["completion_required"] is True
    assert application["full_prewrite_required"] is True
    assert application["rerender_scope"] == "full_prewrite"


def test_patchset_repair_does_not_synthesize_first_path_when_structured_fact_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "validate_host_reasoned_proposal", lambda _proposal: None)
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "normalize_host_reasoned_proposal",
        lambda proposal: dict(proposal),
    )

    def unexpected_completion(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        calls.append("completion")
        return {}

    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "complete_confirmed_proposal", unexpected_completion)
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "ensure_apply_semantic_model", unexpected_completion)
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "repair_greenfield_semantic_projections",
        lambda _proposal: False,
    )
    context = GreenfieldPostConfirmRepairContext(
        pass_index=0,
        elapsed_seconds=1.0,
        budget_seconds=90.0,
        report=GreenfieldCompletionReport(
            status="failed",
            version="greenfield-post-confirm-completion-v1",
            semantic_model=True,
            artifact_counts={},
            tribunal_status="passed",
            issues=("first path needs semantic repair",),
        ),
        issues=(),
        review_report={"version": "odylith.greenfield.post_confirm.review_report.v1"},
        patchset_request={
            "version": "odylith.greenfield.post_confirm.patchset_request.v1",
            "operations": [
                {
                    "operation_id": "GF-PATCH-FIRST-PATH",
                    "target_layer": "semantic_model",
                    "operation_kind": "semantic_first_path",
                    "target_path": "semantic_model.first_path_contract",
                    "semantic_node_id": "SemanticModelIR.first_path_contract",
                    "affected_projections": ["project_brief"],
                    "replacement_fact": {"first_path": "A decision workspace for review."},
                }
            ],
        },
        quality_lenses={"lenses": {}},
        semantic_compiler={},
        repair_tier="rescue",
        rescue_activated=True,
    )
    proposal = {
        "intent": {
            "title": "Evidence Decision Workspace",
            "first_path": "A decision workspace for review.",
        },
        "semantic_model": {},
    }

    repaired = greenfield_post_confirm_patch_apply.apply_greenfield_patchset_repairs(
        proposal,
        release_selector="0.0.1",
        repair_context=context,
    )

    assert calls == []
    assert repaired["intent"]["first_path"] == "A decision workspace for review."
    assert repaired["semantic_model"] == {}
    assert "post_confirm_patch_application_ledger" not in repaired
