from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_issues
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import RenderedPackageQualityFinding
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_cli_output
from odylith.runtime.domain_intelligence import greenfield_component_contract as component_contract
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_surface_refresh_proof
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.governance.component_spec_rendering import build_component_spec
from tests.unit.runtime.greenfield_proposal_fixtures import CONFIRMED_INTENT_TEXT
from tests.unit.runtime.greenfield_proposal_fixtures import _governed_greenfield_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_intent_with_authority
from tests.unit.runtime.greenfield_proposal_fixtures import surface_refresh_preview_fixture


def _proposal(tmp_path: Path) -> dict[str, object]:
    prompt = "Draft a greenfield proposal for a trip comparison workspace"
    proposal = _governed_greenfield_fixture(
        tmp_path,
        prompt,
    )
    confirmed_intent = confirmed_intent_with_authority(
        CONFIRMED_INTENT_TEXT,
        prompt=prompt,
        repo_root=tmp_path,
        write_files=True,
    )
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = confirmed_intent[PRODUCT_INTENT_AUTHORITY_KEY]
    brief = proposal.get("project_brief") if isinstance(proposal.get("project_brief"), dict) else {}
    brief["purpose"] = (
        "Travel planners face risk when cost, timing, accessibility, and policy constraints are compared in separate "
        "notes, so the workspace keeps the operational tension visible before broader booking automation is considered."
    )
    brief["project_outcome"] = (
        "A reviewer can inspect the selected itinerary comparison, unresolved constraints, source evidence, risk "
        "tradeoffs, and release decision before implementation expands scope."
    )
    gates = brief.get("coding_readiness_gates")
    if isinstance(gates, list) and gates:
        gates[0] = "The accepted story names the trip-planning actor, comparison state, first path, and unresolved assumptions."
    return proposal


def _stub_apply_refreshes(monkeypatch) -> None:
    def render_preconfirm_surfaces(*, repo_root: Path):
        for relative_path in greenfield_surface_refresh_proof.GREENFIELD_REQUIRED_SURFACE_ARTIFACTS:
            path = Path(repo_root) / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("stubbed pre-confirm surface\n", encoding="utf-8")
        return surface_refresh_preview_fixture()

    monkeypatch.setattr(
        greenfield_surface_refresh_proof,
        "build_prewrite_surface_refresh_preview",
        render_preconfirm_surfaces,
    )
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(
        greenfield_component_commit.component_authoring.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "skipped_in_unit_test"},
    )
    monkeypatch.setattr(
        greenfield_apply_write,
        "_refresh_greenfield_dashboard",
        lambda **_kwargs: {
            "status": "passed",
            "surfaces": ["radar", "registry", "atlas", "compass", "tooling_shell"],
            "view": "odylith/index.html?tab=project",
        },
    )


def _compile_transaction(tmp_path: Path, proposal: dict[str, object] | None = None):
    completed = greenfield_proposals.complete_confirmed_proposal(
        proposal or _proposal(tmp_path),
        release_selector="0.0.1",
    )
    completed = greenfield_proposals.complete_greenfield_semantic_apply_payload(
        completed,
        release_selector="0.0.1",
    )
    greenfield_proposals.validate_host_reasoned_proposal(completed)
    return greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path,
        proposal=completed,
        release_selector="0.0.1",
        proposal_ready=True,
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


def test_compiled_commit_skips_final_next_steps_quality_after_confirm(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    _stub_apply_refreshes(monkeypatch)
    transaction = _compile_transaction(tmp_path)

    def final_copy_issues(scope: str, _value: object) -> tuple[str, ...]:
        if scope == "operator next-steps final memory":
            raise AssertionError("compiled commit must not run final next-steps quality after confirmation")
        return ()

    monkeypatch.setattr(greenfield_apply_write, "generated_public_copy_issues", final_copy_issues)

    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction=transaction,
        confirm=True,
    )

    manifest = result["commit_manifest"]
    assert manifest["write_transaction"]["status"] == "committed"
    assert "completion_priority" not in manifest
    accepted_project = json.loads((tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text())
    assert "completion_priority_quality_debt" not in accepted_project

    greenfield_cli_output.print_apply_result(result, verb="create")
    closeout = capsys.readouterr().out
    assert "- quality debt:" not in closeout


def test_compiled_commit_skips_final_package_quality_after_confirm(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    _stub_apply_refreshes(monkeypatch)
    transaction = _compile_transaction(tmp_path)
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

    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction=transaction,
        confirm=True,
    )

    manifest = result["commit_manifest"]
    assert manifest["write_transaction"]["status"] == "committed"
    assert "completion_priority" not in manifest
    accepted_project = json.loads((tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text())
    assert "completion_priority_quality_debt" not in accepted_project


def test_compiled_commit_does_not_roll_back_on_late_source_truth_package_repetition(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    _stub_apply_refreshes(monkeypatch)
    proposal = _proposal(tmp_path)
    transaction = _compile_transaction(tmp_path, proposal=proposal)
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

    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction=transaction,
        confirm=True,
    )

    assert result["commit_manifest"]["write_transaction"]["status"] == "committed"
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert (tmp_path / "odylith/runtime/source/accepted-project.v1.json").exists()


def test_compiled_commit_does_not_roll_back_on_late_substantive_quality_finding(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    _stub_apply_refreshes(monkeypatch)
    transaction = _compile_transaction(tmp_path)
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

    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction=transaction,
        confirm=True,
    )

    assert result["commit_manifest"]["write_transaction"]["status"] == "committed"
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert (tmp_path / "odylith/runtime/source/accepted-project.v1.json").exists()


def test_compiled_commit_does_not_roll_back_on_late_generated_prose_finding(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    _stub_apply_refreshes(monkeypatch)
    transaction = _compile_transaction(tmp_path)
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

    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction=transaction,
        confirm=True,
    )

    assert result["commit_manifest"]["write_transaction"]["status"] == "committed"
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert (tmp_path / "odylith/runtime/source/accepted-project.v1.json").exists()


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
