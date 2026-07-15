from __future__ import annotations

from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_preconfirm_patch_apply
from odylith.runtime.domain_intelligence.greenfield_apply_semantic import ensure_apply_semantic_model
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import GreenfieldCompletionReport
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import GreenfieldPreconfirmRepairContext
from odylith.runtime.domain_intelligence.greenfield_preconfirm_patchset import (
    patchset_request_from_findings,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_review import review_finding


def test_patchset_maps_registered_semantic_ontology_slot_without_local_string_branch() -> None:
    patchset = patchset_request_from_findings(
        (
            review_finding(
                code="semantic_alignment",
                surface="project_brief",
                target_path="semantic_model.domain_ontology.non_goals",
                projection_id="project_brief",
                semantic_node_id="SemanticModelIR.domain_ontology.non_goals",
                severity="medium",
                repairability="semantic_patch",
                owner="semantic_model_compiler",
                source="quality_lens",
                message="Non-goal boundary drifted from accepted intent.",
            ),
        )
    ).to_dict()

    assert patchset["status"] == "repairable"
    assert patchset["operations"][0]["operation_kind"] == "semantic_non_goals"
    assert patchset["operations"][0]["target_layer"] == "semantic_model"
    assert patchset["operations"][0]["target_path"] == "semantic_model.domain_ontology.non_goals"


def test_registered_semantic_target_declares_full_prewrite_scope_and_source_mirror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(greenfield_preconfirm_patch_apply, "validate_host_reasoned_proposal", lambda _proposal: None)
    monkeypatch.setattr(
        greenfield_preconfirm_patch_apply,
        "normalize_host_reasoned_proposal",
        lambda proposal: dict(proposal),
    )
    monkeypatch.setattr(
        greenfield_preconfirm_patch_apply,
        "ensure_apply_semantic_model",
        lambda proposal, **_kwargs: dict(proposal),
    )
    monkeypatch.setattr(
        greenfield_preconfirm_patch_apply,
        "repair_greenfield_semantic_projections",
        lambda _proposal: False,
    )
    context = GreenfieldPreconfirmRepairContext(
        pass_index=0,
        elapsed_seconds=1.0,
        budget_seconds=90.0,
        report=GreenfieldCompletionReport(
            status="failed",
            version="greenfield-preconfirm-completion-v1",
            semantic_model=True,
            artifact_counts={},
            tribunal_status="passed",
            issues=("non-goal boundary drifted from accepted intent",),
        ),
        issues=(),
        review_report={"version": "odylith.greenfield.preconfirm.review_report.v1"},
        patchset_request={
            "version": "odylith.greenfield.preconfirm.patchset_request.v1",
            "operations": [
                {
                    "operation_id": "GF-PATCH-NON-GOALS",
                    "target_layer": "semantic_model",
                    "operation_kind": "semantic_non_goals",
                    "target_path": "semantic_model.domain_ontology.non_goals",
                    "semantic_node_id": "SemanticModelIR.domain_ontology.non_goals",
                    "affected_projections": ["project_brief"],
                    "replacement_fact": {"non_goals": ["Forecasting automation remains deferred."]},
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
            "state_object": "A review decision record.",
            "first_path": "A reviewer records evidence and sees the saved decision.",
            "proof_boundary": "Proof links the saved decision to replayable evidence.",
            "non_goals": ["Unscoped analytics"],
        },
        "non_goals": ["Unscoped analytics"],
        "components": [],
        "backlog": [],
        "semantic_model": {
            "domain_ontology": {
                "non_goals": ["Unscoped analytics"],
            }
        },
    }

    repaired = greenfield_preconfirm_patch_apply.apply_greenfield_patchset_repairs(
        proposal,
        release_selector="0.0.1",
        repair_context=context,
    )

    assert repaired["intent"]["non_goals"] == ["Forecasting automation remains deferred."]
    assert repaired["non_goals"] == ["Forecasting automation remains deferred."]
    application = repaired["preconfirm_patch_application_ledger"][-1]
    assert application["affected_projections"] == ("project_brief", "radar", "atlas")
    assert application["full_prewrite_required"] is True
    assert application["rerender_scope"] == "full_prewrite"

    refreshed = ensure_apply_semantic_model(dict(repaired), refresh=True)

    assert refreshed["semantic_model"]["domain_ontology"]["non_goals"] == [
        "Forecasting automation remains deferred."
    ]
