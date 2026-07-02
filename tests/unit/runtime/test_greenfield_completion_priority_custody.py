from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_issues
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import RenderedPackageQualityFinding
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_cli_output
from odylith.runtime.domain_intelligence import greenfield_component_contract as component_contract
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.governance.component_spec_rendering import build_component_spec
from tests.unit.runtime.greenfield_proposal_fixtures import _governed_greenfield_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo


def _proposal(tmp_path: Path) -> dict[str, object]:
    return _governed_greenfield_fixture(
        tmp_path,
        "Draft a greenfield proposal for a trip comparison workspace",
    )


def _stub_apply_refreshes(monkeypatch) -> None:
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(
        greenfield_apply_write.component_authoring.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_apply_write.scaffold_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_apply_write,
        "_raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "skipped_in_unit_test"},
    )
    monkeypatch.setattr(
        greenfield_apply_write,
        "_refresh_greenfield_dashboard",
        lambda **_kwargs: {
            "status": "passed",
            "surfaces": ["radar", "registry", "atlas", "compass", "casebook", "tooling_shell"],
            "view": "odylith/index.html?tab=project",
        },
    )


def test_component_contract_completion_promotes_required_proof_floor_before_rendering() -> None:
    row = {
        "label": "Model Evaluation View",
        "component_contract": {
            "owned_state": "evaluation result, uncertainty summary, baseline comparison, and review state",
            "accepted_inputs": "model output, validation dataset, baseline result, and reviewer context",
            "produced_outputs": "reviewable evaluation result, uncertainty summary, and next-step context",
            "states_or_transitions": "draft, reviewed, blocked, accepted, and ready-for-release",
            "outside_boundary": "model training, source data collection, and release promotion",
            "local_proof": [
                "Successful path evidence for Model Evaluation View: evaluation result, visible result, and reviewer explanation.",
                "Input evidence for lifecycle state.",
                "Replay evidence for Model Evaluation View: actor, input facts, status, explanation, and proof trail.",
                "Access evidence for Model Evaluation View: role-specific actor visibility is enforced.",
                "Freshness evidence for model state.",
            ],
            "upstream_truth": "Prediction Run Service",
            "downstream_consumers": "Release review",
            "unique_failure": "Model Evaluation View can mislead reviewers if evaluation evidence is missing or stale.",
        },
    }

    contract = component_contract.ensure_component_contract(row, proposal={})
    proof_text = " ".join(contract["local_proof"])
    spec = build_component_spec(
        component_id="model-evaluation-view",
        label="Model Evaluation View",
        path="src/model/evaluation_view",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-001",),
        component_contract=contract,
    )

    assert "Blocked input evidence for Model Evaluation View" in proof_text
    assert "Blocked input evidence for Model Evaluation View" in spec
    assert not [
        issue
        for issue in greenfield_rendered_package_quality_issues(
            SimpleNamespace(rendered_component_specs={"Model Evaluation View": spec})
        )
        if "missing proof contract text" in issue
    ]


def test_completion_priority_final_write_debt_is_persisted_and_printed(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    _stub_apply_refreshes(monkeypatch)

    def final_copy_issues(scope: str, _value: object) -> tuple[str, ...]:
        if scope == "operator next-steps final memory":
            return ("operator next-steps final memory leaked adjacent duplicate word prose",)
        return ()

    monkeypatch.setattr(greenfield_apply_write, "generated_public_copy_issues", final_copy_issues)

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=_proposal(tmp_path),
        confirm=True,
        release_selector="0.0.1",
    )

    manifest = result["post_confirm_quality_manifest"]
    assert manifest["write_transaction"]["status"] == "committed"
    assert manifest["completion_priority"]["final_write_quality_debt"] == [
        "final next steps quality: operator next-steps final memory leaked adjacent duplicate word prose"
    ]
    accepted_project = json.loads((tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text())
    debt_ledger = accepted_project["completion_priority_quality_debt"]
    assert debt_ledger["guard"] == "typed_noncritical_projection_debt_only"
    assert debt_ledger["items"] == manifest["completion_priority"]["final_write_quality_debt"]
    assert accepted_project["source_launch"]["completion_priority_quality_debt"]["count"] == 1

    greenfield_cli_output.print_apply_result(result, verb="create")
    closeout = capsys.readouterr().out
    assert "- quality debt: 1 non-critical projection issue(s) recorded after governed write" in closeout


def test_completion_priority_final_write_records_package_repetition_debt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    _stub_apply_refreshes(monkeypatch)
    message = (
        "greenfield rendered package repeats noncanonical prose across 3 artifact(s) and 3 occurrence(s): "
        "`It should carry state from one step to the next with visible progress`"
    )
    monkeypatch.setattr(
        greenfield_apply_write,
        "greenfield_rendered_package_quality_findings",
        lambda _package: [
            RenderedPackageQualityFinding(
                message=message,
                projection_id="registry",
                target_path="components",
                code="package_repetition",
                surface="registry",
                semantic_node_id="ArtifactPlanIR.registry",
                severity="medium",
                repairability="unrepairable",
                owner="registry_renderer",
                source="package_repetition_quality",
                sample="It should carry state from one step to the next with visible progress",
                occurrence_count=3,
                artifact_count=3,
                occurrence_paths=("components",),
                occurrence_projections=("registry",),
                occurrence_surfaces=("registry",),
            )
        ],
    )

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=_proposal(tmp_path),
        confirm=True,
        release_selector="0.0.1",
    )

    manifest = result["post_confirm_quality_manifest"]
    assert manifest["write_transaction"]["status"] == "committed"
    assert manifest["completion_priority"]["final_write_quality_debt"] == [f"final write quality: {message}"]
    accepted_project = json.loads((tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text())
    assert accepted_project["completion_priority_quality_debt"]["items"] == [
        f"final write quality: {message}"
    ]


def test_completion_priority_write_rolls_back_source_truth_package_repetition(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    _stub_apply_refreshes(monkeypatch)
    proposal = _proposal(tmp_path)
    repeated = str(proposal["project_brief"]["project_outcome"])
    message = (
        "greenfield rendered package repeats noncanonical prose across 3 artifact(s) and 3 occurrence(s): "
        f"`{repeated}`"
    )
    monkeypatch.setattr(
        greenfield_apply_write,
        "greenfield_rendered_package_quality_findings",
        lambda _package: [
            RenderedPackageQualityFinding(
                message=message,
                projection_id="registry",
                target_path="components",
                code="package_repetition",
                surface="registry",
                semantic_node_id="ArtifactPlanIR.registry",
                severity="medium",
                repairability="unrepairable",
                owner="registry_renderer",
                source="package_repetition_quality",
                sample=repeated,
                occurrence_count=3,
                artifact_count=3,
                occurrence_paths=("components",),
                occurrence_projections=("registry",),
                occurrence_surfaces=("registry",),
            )
        ],
    )
    with pytest.raises(ValueError, match="greenfield post-confirm final write quality failed"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )

    assert not list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert not (tmp_path / "odylith/runtime/source/accepted-project.v1.json").exists()


def test_completion_priority_write_rolls_back_substantive_final_quality_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    _stub_apply_refreshes(monkeypatch)
    monkeypatch.setattr(
        greenfield_apply_write,
        "greenfield_rendered_package_quality_findings",
        lambda _package: [
            RenderedPackageQualityFinding(
                message="Project implementation prompt `Build the review path` is too shallow for engineering handoff",
                projection_id="project_brief",
                target_path="project_brief.implementation_prompt",
                code="project_prompt_quality",
                surface="project_brief",
                semantic_node_id="ArtifactPlanIR.project_brief",
                severity="high",
                repairability="unrepairable",
                owner="project_brief_projector",
                source="project_prompt_quality",
            )
        ],
    )

    with pytest.raises(ValueError, match="greenfield post-confirm final write quality failed"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=_proposal(tmp_path),
            confirm=True,
            release_selector="0.0.1",
        )

    assert not list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert not (tmp_path / "odylith/runtime/source/accepted-project.v1.json").exists()


def test_completion_priority_write_rolls_back_nonmechanical_generated_prose_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    _stub_apply_refreshes(monkeypatch)
    monkeypatch.setattr(
        greenfield_apply_write,
        "greenfield_rendered_package_quality_findings",
        lambda _package: [
            RenderedPackageQualityFinding(
                message="generated prose uses generic governance posture filler at components[0].responsibility",
                projection_id="registry",
                target_path="components[0].responsibility",
                code="generated_copy_quality",
                surface="registry",
                semantic_node_id="ArtifactPlanIR.registry",
                severity="medium",
                repairability="unrepairable",
                owner="registry_renderer",
                source="package_quality",
            )
        ],
    )

    with pytest.raises(ValueError, match="greenfield post-confirm final write quality failed"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=_proposal(tmp_path),
            confirm=True,
            release_selector="0.0.1",
        )

    assert not list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert not (tmp_path / "odylith/runtime/source/accepted-project.v1.json").exists()


def test_completion_priority_debt_guard_rejects_nonmechanical_generated_prose_labels() -> None:
    assert greenfield_apply_write._late_projection_copy_debt_issue(
        debt_prefix="component spec quality",
        issue="generated prose uses malformed ownership verb pair at components[0].responsibility",
    )
    for label in (
        "summary elision leaked into governed record",
        "provisional title qualifier",
        "generic governance posture filler",
        "accepted-items summary leaked",
    ):
        assert not greenfield_apply_write._late_projection_copy_debt_issue(
            debt_prefix="component spec quality",
            issue=f"generated prose uses {label} at components[0].responsibility",
        )
