from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
import tempfile
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_backlog_commit
from odylith.runtime.domain_intelligence import greenfield_compiled_memory_readback
from odylith.runtime.domain_intelligence import greenfield_compiled_readback
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_create_baseline
from odylith.runtime.domain_intelligence import greenfield_compiled_write
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_create_transaction
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_release_commit
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence import greenfield_repository_lock
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.greenfield_create_transaction import PRODUCT_CREATE_TRANSACTION_COMPILER
from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import load_compiled_product_create_transaction_file
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_from_dict
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_to_dict
from odylith.runtime.domain_intelligence.greenfield_create_transaction import require_product_create_transaction_verified
from odylith.runtime.domain_intelligence.greenfield_create_transaction import write_compiled_product_create_transaction_file
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    DEEP_PROFILE_ID,
    RESCUE_PROFILE_ID,
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
)
from odylith.runtime.domain_intelligence.greenfield_create_manifest import PRECONFIRM_ENGINE_VERSION
from odylith.runtime.domain_intelligence.greenfield_create_manifest import PRECONFIRM_QUALITY_MANIFEST_VERSION
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.governance import backlog_authoring
from odylith.runtime.governance import validate_backlog_contract as backlog_contract
from odylith.runtime.surfaces import brand_assets
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import materialize_typed_intent_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import seal_compiled_greenfield_package_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import seal_compiled_greenfield_transaction
from tests.unit.runtime.greenfield_proposal_fixtures import surface_refresh_preview_fixture

COMPILED_ACCEPTED_AT = "2026-07-07T00:00:00-07:00"


def test_create_transaction_reuses_shared_mapping_coercion() -> None:
    source = Path(greenfield_create_transaction.__file__).read_text(encoding="utf-8")

    assert "value_coercion import mapping_copy" in source
    assert "def _mapping(" not in source


def _proposal() -> dict[str, Any]:
    return {
        "intent": {
            "title": "Supplier Risk Board",
            "product_story": "Supplier risk analysts need one reviewable board for recording supplier risk decisions and their evidence.",
            "state_object": "A supplier risk case tracks supplier evidence, review status, decision, owner, and proof record.",
            "first_path": "A supplier risk analyst records one supplier case, reviews the evidence, records a decision, and sees a reviewable risk receipt.",
            "human_actors": ["Supplier Risk Analyst: records supplier evidence, reviews the risk decision, and checks the receipt."],
            "proof_boundary": "The first release works when a reviewer can inspect the supplier case, decision, and evidence together.",
        },
        "backlog": [{"title": "Prove supplier risk review path"}],
        "components": [],
        "diagrams": [],
    }


def _authored_supplier_proposal(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    first_path = (
        "Supplier Risk Analyst records one supplier risk case. "
        "Supplier Review Service presents the supplier evidence. "
        "Supplier Risk Analyst reviews the evidence. "
        "Supplier Risk Analyst records a decision. "
        "Supplier Review Service shows a reviewable risk receipt."
    )
    intent: dict[str, Any] = {
        "title": "Supplier Risk Board",
        "product_story": (
            "Supplier Risk Board gives supplier risk analysts one reviewable place for "
            "supplier decisions and their evidence."
        ),
        "state_object": "supplier risk case",
        "first_path": first_path,
        "proof_boundary": (
            "Verify one supplier case, its evidence, recorded decision, and reviewable risk "
            "receipt together."
        ),
        "problem": "Supplier risk decisions lose trust when evidence and decisions are separated.",
        "customer": "Supplier risk analysts",
        "opportunity": "Prove one traceable supplier review before broadening the workflow.",
        "product_view": "The board keeps supplier evidence, review state, and decisions connected.",
        "success_metrics": ["A reviewer can trace one decision to its supplier evidence."],
        "evidence_requirements": ["Retain the supplier evidence and recorded decision together."],
        "operational_constraints": ["Keep every decision traceable to reviewed evidence."],
        "component_responsibilities": [
            "Own supplier case state, evidence review, decisions, and risk receipts."
        ],
        "human_actors": ["Supplier Risk Analyst"],
        "external_systems": [],
        "internal_systems": ["Supplier Review Service"],
        "assumptions": ["The first release supports one reviewer role."],
        "ambiguities": [],
        "non_goals": ["Do not automate supplier approval decisions."],
    }
    candidate = materialize_typed_intent_fixture(
        repo_root,
        intent=intent,
        first_path_relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Supplier Risk Analyst",
                "event_quote": "Supplier Risk Analyst records one supplier risk case",
                "action_verb_quote": "records",
                "target_quote": "one supplier risk case",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Supplier Review Service",
                "owner_system_quote": "Supplier Review Service",
                "event_quote": "Supplier Review Service presents the supplier evidence",
                "action_verb_quote": "presents",
                "target_quote": "the supplier evidence",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "human",
                "actor_quote": "Supplier Risk Analyst",
                "event_quote": "Supplier Risk Analyst reviews the evidence",
                "action_verb_quote": "reviews",
                "target_quote": "the evidence",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "human",
                "actor_quote": "Supplier Risk Analyst",
                "event_quote": "Supplier Risk Analyst records a decision",
                "action_verb_quote": "records",
                "target_quote": "a decision",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Supplier Review Service",
                "owner_system_quote": "Supplier Review Service",
                "event_quote": "Supplier Review Service shows a reviewable risk receipt",
                "action_verb_quote": "shows",
                "target_quote": "a reviewable risk receipt",
                "visible_result_quote": "a reviewable risk receipt",
                "recovery_path": False,
            },
        ],
        component_responsibility_owners=["Supplier Review Service"],
    )
    authority = dict(candidate.pop(PRODUCT_INTENT_AUTHORITY_KEY))
    proposal = {
        "intent": candidate,
        PRODUCT_INTENT_AUTHORITY_KEY: authority,
        "projection_origin": AUTHORED_PROJECTION_ORIGIN,
        "backlog": [{"title": "Prove supplier risk review path"}],
        "components": [],
        "diagrams": [],
    }
    return proposal, authority


def _complete_authored_supplier_proposal(
    repo_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Project the typed supplier intent through the real authored proposal path."""

    minimal, authority = _authored_supplier_proposal(repo_root)
    confirmed_intent = {
        **dict(minimal["intent"]),
        PRODUCT_INTENT_AUTHORITY_KEY: authority,
    }
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=repo_root,
        prompt=str(confirmed_intent.get("prompt") or ""),
        release_selector="0.0.1",
        confirmed_intent=confirmed_intent,
        require_completion_ready=False,
    )
    return proposal, authority


def _package(proposal: dict[str, Any]) -> GreenfieldCompletionPackage:
    idea_path = Path("/repo/odylith/radar/source/ideas/B-001.md")
    backlog_rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    workstream_title = str(
        (backlog_rows[0].get("title") if backlog_rows else "")
        or "Prove supplier risk review path"
    )
    created_backlog = [
        {"title": workstream_title, "idea_id": "B-001", "idea_path": str(idea_path)}
    ]
    backlog_result = {
        "created": created_backlog,
        "idea_files": {str(idea_path): workstream_title},
        "backlog_index": "/repo/odylith/radar/source/INDEX.md",
        "backlog_index_text": f"| B-001 | {workstream_title} |",
        "_candidate_idea_specs": {
            "B-001": backlog_contract.IdeaSpec(
                path=idea_path,
                metadata={"idea_id": "B-001", "status": "candidate"},
                sections={"Problem", "Product View"},
                section_bodies={"Problem": "Supplier risk is hard to review.", "Product View": "Review board."},
            )
        },
    }
    diagram_rows = [row for row in proposal.get("diagrams", []) if isinstance(row, dict)]
    diagram_ids = tuple(f"D-{index:03d}" for index, _row in enumerate(diagram_rows, start=1))
    rendered_atlas_sources = {
        f"odylith/atlas/source/{str(row.get('slug', f'diagram-{index}')).strip() or f'diagram-{index}'}.mmd": (
            "flowchart TD\n  A[\"Accepted input\"] --> B[\"Review result\"]\n"
        )
        for index, row in enumerate(diagram_rows, start=1)
    }
    traceability_plan = greenfield_traceability.build_traceability_plan(
        proposal=proposal,
        created_backlog=created_backlog,
        diagram_ids=diagram_ids,
    )
    atlas_catalog_rows = greenfield_apply_diagrams.render_prewrite_atlas_catalog_rows(
        root=Path("/repo"),
        rows=diagram_rows,
        diagram_ids=diagram_ids,
        traceability_plan=traceability_plan,
        review_date="2026-07-07",
    )
    component_rows = [row for row in proposal.get("components", []) if isinstance(row, Mapping)]
    component_row = component_rows[0] if component_rows else {}
    component_id = str(component_row.get("component_id") or "supplier-risk-service")
    component_label = str(component_row.get("label") or "Supplier Risk Service")
    component_path = str(component_row.get("intended_path") or "src/supplier_risk")
    component_kind = str(component_row.get("kind") or "service")
    component_responsibility = str(
        component_row.get("responsibility")
        or "Supplier Risk Service keeps supplier review state attached."
    )
    component_key = greenfield_traceability.component_key(
        {"component_id": component_id, "label": component_label}
    )
    component_diagrams = traceability_plan.component_diagrams.get(component_key, ())
    component_handoff = {
        "workstream_id": "B-001",
        "workstream_title": workstream_title,
        "implementation_prompt": "Implement the accepted supplier risk review path.",
    }
    component_authoring_input = {
        "component_id": component_id,
        "label": component_label,
        "path": component_path,
        "kind": component_kind,
        "category": "application",
        "qualification": "candidate",
        "owner": "repo",
        "status": "planned",
        "product_layer": "application",
        "sources": ("user_intent",),
        "workstreams": ("B-001",),
        "diagrams": component_diagrams,
        "responsibility": component_responsibility,
        "boundary": str(component_row.get("boundary") or "Supplier review state only."),
        "dependencies": (),
        "interfaces": (),
        "validation": (),
        "risks": (),
        "implementation_handoff": component_handoff,
        "component_contract": dict(component_row.get("component_contract") or {}),
    }
    package = GreenfieldCompletionPackage(
        proposal=proposal,
        release_selector="0.0.1",
        rendered_atlas_sources=rendered_atlas_sources,
        atlas_review_date="2026-07-07",
        atlas_diagram_ids=diagram_ids,
        atlas_catalog_rows=atlas_catalog_rows,
        backlog_result=backlog_result,
        prewrite_safety_preview={"status": "passed"},
        surface_refresh_preview=surface_refresh_preview_fixture(),
        component_registry_preview=(
            {
                "component_id": component_id,
                "label": component_label,
                "spec_path": f"odylith/registry/source/components/{component_id}/CURRENT_SPEC.md",
                "implementation_handoff": component_handoff,
                "authoring_input": component_authoring_input,
                "registry_entry": {
                    "component_id": component_id,
                    "name": component_label,
                    "kind": component_kind,
                    "category": "application",
                    "qualification": "candidate",
                    "aliases": [],
                    "path_prefixes": [component_path],
                    "workstreams": ["B-001"],
                    "diagrams": list(component_diagrams),
                    "owner": "repo",
                    "status": "planned",
                    "what_it_is": f"{component_label} defines the planned ownership boundary for supplier review state.",
                    "why_tracked": "Tracked from user-stated intent because this named ownership boundary must stay understandable before source-backed behavior promotes it.",
                    "spec_ref": f"odylith/registry/source/components/{component_id}/CURRENT_SPEC.md",
                    "sources": ["user_intent"],
                    "subcomponents": [],
                    "product_layer": "application",
                },
            },
        ),
        rendered_component_specs={
            component_label: f"# {component_label}\n\n{component_responsibility}\n",
        },
        project_brief_record_text=f"# Supplier Risk Board Project Brief\n\n- accepted_at: {COMPILED_ACCEPTED_AT}\n",
        accepted_project_preview={
            "schema_version": "odylith.accepted_project.v1",
            "origin": "greenfield",
            "evidence_tier": "user_intent",
            "accepted_at": COMPILED_ACCEPTED_AT,
            "title": "Supplier Risk Board",
            "source_launch": {"implementation_prompt": "Start B-001 from the accepted transaction package."},
            "created": {"workstreams": [{"idea_id": "B-001"}], "components": [], "diagrams": []},
            "validation_gate": {"status": "passed", "issues": []},
        },
        compass_memory_preview={
            "version": "v1",
            "kind": "decision",
            "summary": "Accepted greenfield proposal for Supplier Risk Board.",
            "ts_iso": COMPILED_ACCEPTED_AT,
            "author": "odylith",
            "source": "domain-intelligence",
            "workstreams": ["B-001"],
            "artifacts": ["odylith/runtime/source/project-brief.v1.md"],
            "components": ["supplier-risk-service"],
            "evidence_tier": "user_intent",
            "work_category": "governance",
        },
        next_steps_preview={
            "project_workstream_id": "B-001",
            "start_workstream_id": "B-001",
            "start_workstream_title": "Prove supplier risk review path",
            "release_selector": "0.0.1",
            "implementation_prompt": "Start B-001 from the accepted transaction package.",
            "operator_sequence": ["Open B-001.", "Implement the first path."],
            "coding_readiness_gates": ["Transaction package accepted."],
            "verification_commands": ["odylith context --repo-root . B-001"],
        },
        traceability_plan=traceability_plan,
        release_target_result={
            "dry_run": True,
            "selector": "0.0.1",
            "release": {
                "release_id": "release-0-0-1",
                "status": "planning",
                "version": "0.0.1",
                "tag": "v0.0.1",
                "name": "Release 0.0.1",
                "notes": "First compiled greenfield release.",
                "created_utc": "2026-07-07T00:00:00Z",
            },
        },
        release_assignment_result={
            "dry_run": True,
            "workstream_ids": ["B-001"],
            "events": [],
            "release": {"release_id": "release-0-0-1"},
        },
        release_workstream_ids=("B-001",),
    )
    return _seal_test_package(package, repo_root=Path("/repo"))


def _seal_test_package(package: GreenfieldCompletionPackage, *, repo_root: Path) -> GreenfieldCompletionPackage:
    return seal_compiled_greenfield_package_fixture(package, repo_root=repo_root)


def _compiled_memory_event(package: GreenfieldCompletionPackage) -> dict[str, Any]:
    return dict(package.compass_memory_preview or {})


def _write_compass_memory_event(root: Path, event: Mapping[str, Any]) -> Path:
    stream_path = root / "odylith/compass/runtime/agent-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text(json.dumps(dict(event), sort_keys=True) + "\n", encoding="utf-8")
    return stream_path


def _approved_quality_manifest(**overrides: Any) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "version": PRECONFIRM_QUALITY_MANIFEST_VERSION,
        "engine": PRECONFIRM_ENGINE_VERSION,
        "status": "passed",
        "validation_status": "passed",
        "issue_count": 0,
        "hard_blocker": None,
        "requested_repair_tier": "auto",
        "repair_tier": "standard",
        "budget_seconds": 60.0,
        "elapsed_seconds": 12.3,
        "write_transaction": {
            "status": "not_started",
            "rollback_guard": "enabled",
            "prewrite_clean_before_commit": True,
        },
        "semantic_compiler": {
            "version": "odylith.greenfield.authored-semantic-validation.v1",
            "status": "passed",
            "semantic_owner": "single_model_authoring_response",
            "post_authoring_interpretation_calls": 0,
        },
        "model_authoring": _approved_model_authoring(
            STANDARD_PROFILE_ID,
            elapsed_seconds=12.0,
        ),
    }
    manifest.update(overrides)
    return manifest


def _approved_model_authoring(profile_id: str, *, elapsed_seconds: float) -> dict[str, Any]:
    profile = get_greenfield_model_profile(profile_id)
    return {
        "authoring_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "semantic_model_call_count": 1,
        "tier": profile.repair_tier,
        "elapsed_seconds": elapsed_seconds,
        "model_profile": {
            "profile_id": profile.profile_id,
            "provider": profile.provider,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
            "effective_timeout_seconds": profile.model_timeout_seconds,
            "authoring_tier": profile.repair_tier,
        },
    }


def test_quality_approval_accepts_one_model_call_and_zero_reinterpretation() -> None:
    greenfield_create_transaction.require_product_create_transaction_quality_approved(
        _approved_quality_manifest(
            semantic_compiler={
                "version": "odylith.greenfield.authored-semantic-validation.v1",
                "status": "passed",
                "semantic_owner": "single_model_authoring_response",
                "post_authoring_interpretation_calls": 0,
            },
            model_authoring=_approved_model_authoring(
                STANDARD_PROFILE_ID,
                elapsed_seconds=12.0,
            ),
        )
    )


def test_quality_approval_accepts_explicit_deep_profile() -> None:
    greenfield_create_transaction.require_product_create_transaction_quality_approved(
        _approved_quality_manifest(
            requested_repair_tier="deep",
            repair_tier="deep",
            budget_seconds=120.0,
            semantic_compiler={
                "version": "odylith.greenfield.authored-semantic-validation.v1",
                "status": "passed",
                "semantic_owner": "single_model_authoring_response",
                "post_authoring_interpretation_calls": 0,
            },
            model_authoring=_approved_model_authoring(
                DEEP_PROFILE_ID,
                elapsed_seconds=100.0,
            ),
        )
    )


def test_quality_approval_accepts_explicit_rescue_profile() -> None:
    greenfield_create_transaction.require_product_create_transaction_quality_approved(
        _approved_quality_manifest(
            requested_repair_tier="rescue",
            repair_tier="rescue",
            budget_seconds=90.0,
            semantic_compiler={
                "version": "odylith.greenfield.authored-semantic-validation.v1",
                "status": "passed",
                "semantic_owner": "single_model_authoring_response",
                "post_authoring_interpretation_calls": 0,
            },
            model_authoring=_approved_model_authoring(
                RESCUE_PROFILE_ID,
                elapsed_seconds=80.0,
            ),
        )
    )


def test_quality_approval_rejects_default_route_relabelled_as_rescue() -> None:
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        greenfield_create_transaction.require_product_create_transaction_quality_approved(
            _approved_quality_manifest(
                requested_repair_tier="auto",
                repair_tier="rescue",
                budget_seconds=90.0,
                semantic_compiler={
                    "version": "odylith.greenfield.authored-semantic-validation.v1",
                    "status": "passed",
                    "semantic_owner": "single_model_authoring_response",
                    "post_authoring_interpretation_calls": 0,
                },
                model_authoring=_approved_model_authoring(
                    RESCUE_PROFILE_ID,
                    elapsed_seconds=50.0,
                ),
            )
        )


def test_quality_approval_rejects_profile_tier_relabeling() -> None:
    receipt = _approved_model_authoring(DEEP_PROFILE_ID, elapsed_seconds=12.0)
    receipt["tier"] = "standard"

    with pytest.raises(ValueError, match="quality manifest is not approved"):
        greenfield_create_transaction.require_product_create_transaction_quality_approved(
            _approved_quality_manifest(
                requested_repair_tier="deep",
                repair_tier="deep",
                budget_seconds=120.0,
                semantic_compiler={
                    "version": "odylith.greenfield.authored-semantic-validation.v1",
                    "status": "passed",
                    "semantic_owner": "single_model_authoring_response",
                    "post_authoring_interpretation_calls": 0,
                },
                model_authoring=receipt,
            )
        )


@pytest.mark.parametrize(
    "retired_version",
    (
        "odylith.greenfield.model-intent-authoring.v1",
        "odylith.greenfield.intent-authoring.v4",
        "odylith.greenfield.intent-authoring.v5",
    ),
)
def test_quality_approval_rejects_retired_model_authoring_versions(
    retired_version: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="pre-confirm ProductCreateTransaction quality manifest is not approved",
    ):
        greenfield_create_transaction.require_product_create_transaction_quality_approved(
            _approved_quality_manifest(
                semantic_compiler={
                    "version": "odylith.greenfield.authored-semantic-validation.v1",
                    "status": "passed",
                    "semantic_owner": "single_model_authoring_response",
                    "post_authoring_interpretation_calls": 0,
                },
                model_authoring={
                    "authoring_version": retired_version,
                    "semantic_model_call_count": 1,
                    "tier": "standard",
                    "elapsed_seconds": 12.0,
                },
            ),
            authored_projection_verified=True,
        )


def _valid_idea_file_text(*, idea_id: str, title: str) -> str:
    sections = {
        section: f"{title} keeps the first release path concrete and reviewable."
        for section in backlog_contract._REQUIRED_SECTIONS
    }
    return backlog_authoring._render_idea_text(  # noqa: SLF001
        metadata={
            "status": "queued",
            "idea_id": idea_id,
            "title": title,
            "date": "2026-07-07",
            "priority": "P1",
            "commercial_value": "3",
            "product_impact": "3",
            "market_value": "3",
            "impacted_parts": "odylith",
            "sizing": "M",
            "complexity": "Medium",
            "ordering_score": "100",
            "ordering_rationale": "Compiled greenfield transaction replay fixture.",
            "confidence": "medium",
            "founder_override": "no",
            "promoted_to_plan": "",
            "execution_model": "standard",
            "workstream_type": "standalone",
        },
        sections=sections,
    )


def _transaction(repo_root: Path | None = None) -> Any:
    root = repo_root or Path(tempfile.mkdtemp(prefix="odylith-authored-transaction-"))
    proposal, authority = _complete_authored_supplier_proposal(root)
    package = replace(
        _package(proposal),
        baseline_writes=greenfield_create_baseline.precompiled_greenfield_create_baseline_writes(root),
        brand_asset_writes=brand_assets.precompiled_brand_asset_writes(repo_root=root),
    )
    package = _seal_test_package(package, repo_root=root)
    return build_product_create_transaction(
        proposal=proposal,
        release_selector="0.0.1",
        validation_gate={"status": "passed", "issues": []},
        prewrite_package=package,
        backlog_result=package.backlog_result or {},
        intent_authority=authority,
        quality_manifest=_approved_quality_manifest(),
        repo_root=root,
    )


def _sealed_transaction(repo_root: Path, transaction: Any | None = None) -> Any:
    return seal_compiled_greenfield_transaction(
        repo_root=repo_root,
        transaction=transaction or _transaction(repo_root=repo_root),
    )


def test_compiled_memory_readback_rejects_accepted_project_drift(tmp_path: Path) -> None:
    package = _package(_complete_authored_supplier_proposal(tmp_path)[0])
    source_root = tmp_path / "odylith/runtime/source"
    source_root.mkdir(parents=True, exist_ok=True)
    accepted_project = dict(package.accepted_project_preview or {})
    accepted_project["title"] = "Drifted Project"
    (source_root / "accepted-project.v1.json").write_text(
        json.dumps(accepted_project, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (source_root / "project-brief.v1.md").write_text(
        package.project_brief_record_text,
        encoding="utf-8",
    )
    event = _compiled_memory_event(package)
    stream_path = _write_compass_memory_event(tmp_path, event)

    with pytest.raises(ValueError, match="accepted project record does not match compiled transaction preview"):
        greenfield_compiled_memory_readback.raise_for_compiled_memory_readback(
            root=tmp_path,
            prewrite_package=package,
            memory_record={"stream": str(stream_path), "event": event},
        )


def test_compiled_memory_readback_accepts_json_round_trip_equivalent_preview(tmp_path: Path) -> None:
    package = _package(_complete_authored_supplier_proposal(tmp_path)[0])
    preview = dict(package.accepted_project_preview or {})
    preview["created"] = {
        **dict(preview.get("created") or {}),
        "components": [{"component_id": "supplier-risk-service", "dependencies": ("B-001",)}],
    }
    package = replace(package, accepted_project_preview=preview)
    source_root = tmp_path / "odylith/runtime/source"
    source_root.mkdir(parents=True, exist_ok=True)
    accepted_project = json.loads(json.dumps(preview))
    (source_root / "accepted-project.v1.json").write_text(
        json.dumps(accepted_project, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (source_root / "project-brief.v1.md").write_text(
        package.project_brief_record_text,
        encoding="utf-8",
    )
    event = _compiled_memory_event(package)
    stream_path = _write_compass_memory_event(tmp_path, event)

    greenfield_compiled_memory_readback.raise_for_compiled_memory_readback(
        root=tmp_path,
        prewrite_package=package,
        memory_record={"stream": str(stream_path), "event": event},
    )


def test_compiled_memory_readback_rejects_canonicalized_compass_component_ids(tmp_path: Path) -> None:
    package = _package(_complete_authored_supplier_proposal(tmp_path)[0])
    preview = dict(package.compass_memory_preview or {})
    preview["components"] = ["Supplier-Risk-Service"]
    package = replace(package, compass_memory_preview=preview)
    source_root = tmp_path / "odylith/runtime/source"
    source_root.mkdir(parents=True, exist_ok=True)
    accepted_project = dict(package.accepted_project_preview or {})
    (source_root / "accepted-project.v1.json").write_text(
        json.dumps(accepted_project, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (source_root / "project-brief.v1.md").write_text(
        package.project_brief_record_text,
        encoding="utf-8",
    )
    event = _compiled_memory_event(package)
    event["components"] = ["supplier-risk-service"]
    stream_path = _write_compass_memory_event(tmp_path, event)

    with pytest.raises(ValueError, match="Compass memory event does not match compiled transaction preview"):
        greenfield_compiled_memory_readback.raise_for_compiled_memory_readback(
            root=tmp_path,
            prewrite_package=package,
            memory_record={"stream": str(stream_path), "event": event},
        )


def test_compiled_memory_readback_rejects_compass_event_drift(tmp_path: Path) -> None:
    package = _package(_complete_authored_supplier_proposal(tmp_path)[0])
    source_root = tmp_path / "odylith/runtime/source"
    source_root.mkdir(parents=True, exist_ok=True)
    accepted_project = dict(package.accepted_project_preview or {})
    (source_root / "accepted-project.v1.json").write_text(
        json.dumps(accepted_project, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (source_root / "project-brief.v1.md").write_text(
        package.project_brief_record_text,
        encoding="utf-8",
    )
    event = _compiled_memory_event(package)
    event["summary"] = "Accepted a different greenfield proposal."
    stream_path = _write_compass_memory_event(tmp_path, event)

    with pytest.raises(ValueError, match="Compass memory event does not match compiled transaction preview"):
        greenfield_compiled_memory_readback.raise_for_compiled_memory_readback(
            root=tmp_path,
            prewrite_package=package,
            memory_record={"stream": str(stream_path), "event": event},
        )


def test_compiled_memory_readback_rejects_missing_compass_stream_event(tmp_path: Path) -> None:
    package = _package(_complete_authored_supplier_proposal(tmp_path)[0])
    source_root = tmp_path / "odylith/runtime/source"
    source_root.mkdir(parents=True, exist_ok=True)
    accepted_project = dict(package.accepted_project_preview or {})
    (source_root / "accepted-project.v1.json").write_text(
        json.dumps(accepted_project, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (source_root / "project-brief.v1.md").write_text(
        package.project_brief_record_text,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Compass memory stream does not contain compiled transaction event"):
        greenfield_compiled_memory_readback.raise_for_compiled_memory_readback(
            root=tmp_path,
            prewrite_package=package,
            memory_record={"event": _compiled_memory_event(package)},
        )


def test_product_create_transaction_hash_rejects_mutation() -> None:
    transaction = _transaction()

    assert transaction.verified
    require_product_create_transaction_verified(transaction)

    tampered = replace(
        transaction,
        proposal={**transaction.proposal, "intent": {"title": "Different Project"}},
    )

    assert not tampered.verified
    with pytest.raises(ValueError, match="sealed Product Intent authority"):
        require_product_create_transaction_verified(tampered)


def test_product_create_transaction_json_round_trips_with_hash() -> None:
    transaction = _transaction()
    payload = product_create_transaction_to_dict(transaction)

    restored = product_create_transaction_from_dict(payload)

    assert restored.transaction_hash == transaction.transaction_hash
    assert not restored.verified
    with pytest.raises(ValueError, match="not accepted by the pre-confirm compiler"):
        require_product_create_transaction_verified(restored)
    assert restored.compiler_provenance["compiler"] == PRODUCT_CREATE_TRANSACTION_COMPILER
    assert restored.summary()["compiler_phase"] == "pre_confirm_compile"
    assert restored.prewrite_package.proposal == transaction.prewrite_package.proposal
    assert restored.quality_manifest["status"] == "passed"
    restored_preview = restored.prewrite_package.component_registry_preview
    assert restored_preview[0]["implementation_handoff"]["workstream_id"] == "B-001"
    assert restored_preview[0]["authoring_input"]["workstreams"] == ["B-001"]
    assert restored.prewrite_package.accepted_project_preview["accepted_at"] == COMPILED_ACCEPTED_AT
    assert isinstance(restored.prewrite_package.traceability_plan, greenfield_traceability.GreenfieldTraceabilityPlan)
    assert restored.prewrite_package.traceability_plan.workstreams[0].idea_id == "B-001"
    assert restored.prewrite_package.project_brief_record_text.startswith("# Supplier Risk Board Project Brief")
    assert payload["prewrite_package"]["surface_refresh_preview"]["status"] == "passed"
    assert (
        restored.prewrite_package.surface_refresh_preview
        == transaction.prewrite_package.surface_refresh_preview
    )
    restored_specs = restored.backlog_result["_candidate_idea_specs"]
    assert isinstance(restored_specs["B-001"], backlog_contract.IdeaSpec)
    assert restored_specs["B-001"].metadata["idea_id"] == "B-001"

    tampered_surface = json.loads(json.dumps(payload))
    tampered_surface["prewrite_package"]["surface_refresh_preview"]["status"] = "failed"
    with pytest.raises(ValueError, match="hash mismatch"):
        product_create_transaction_from_dict(tampered_surface)

    payload["quality_manifest"] = {**payload["quality_manifest"], "status": "failed"}
    with pytest.raises(ValueError, match="hash mismatch"):
        product_create_transaction_from_dict(payload)


def test_sealed_transaction_keeps_staging_paths_out_of_accepted_project_custody(tmp_path: Path) -> None:
    target_root = tmp_path / "consumer"
    staged_root = tmp_path / "odylith-greenfield-prewrite-stage" / "repo"
    original = _transaction(repo_root=target_root)
    accepted = greenfield_apply_prewrite.preview_accepted_project_memory(
        root=staged_root,
        target_root=target_root,
        proposal=original.proposal,
        backlog_result={
            "created": [
                {
                    "idea_id": "B-001",
                    "idea_path": target_root / "odylith/radar/source/ideas/2026-08/supplier-risk.md",
                }
            ]
        },
        component_items=(
            {
                "component_id": "supplier-risk-service",
                "spec_path": target_root
                / "odylith/registry/source/components/supplier-risk-service/CURRENT_SPEC.md",
            },
        ),
        release_selector="0.0.1",
        release_target_result=original.prewrite_package.release_target_result,
        release_assignment_result=original.prewrite_package.release_assignment_result,
        validation_gate=original.validation_gate,
    )
    package = _seal_test_package(
        replace(original.prewrite_package, accepted_project_preview=accepted),
        repo_root=target_root,
    )
    transaction = build_product_create_transaction(
        proposal=original.proposal,
        release_selector=original.release_selector,
        validation_gate=original.validation_gate,
        prewrite_package=package,
        backlog_result=package.backlog_result or {},
        intent_authority=original.intent_authority,
        quality_manifest=original.quality_manifest,
        repo_root=target_root,
    )

    payload = product_create_transaction_to_dict(transaction)
    accepted_payload = payload["prewrite_package"]["accepted_project_preview"]
    serialized = json.dumps(accepted_payload, sort_keys=True)

    assert payload["intent_authority"] == transaction.intent_authority
    assert PRODUCT_INTENT_AUTHORITY_KEY in payload["proposal"]
    assert PRODUCT_INTENT_AUTHORITY_KEY not in accepted_payload["proposal"]
    assert str(staged_root) not in serialized
    assert "odylith-greenfield-prewrite" not in serialized
    assert accepted_payload["created"]["workstreams"][0]["idea_path"] == (
        "odylith/radar/source/ideas/2026-08/supplier-risk.md"
    )
    assert accepted_payload["created"]["components"][0]["spec_path"] == (
        "odylith/registry/source/components/supplier-risk-service/CURRENT_SPEC.md"
    )


def test_compiled_transaction_file_requires_untampered_compiler_receipt(tmp_path: Path) -> None:
    transaction = _transaction(repo_root=tmp_path)
    path = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    write_compiled_product_create_transaction_file(path, transaction)

    restored = load_compiled_product_create_transaction_file(path)

    assert restored.verified
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="does not match its pre-confirm compiler receipt"):
        load_compiled_product_create_transaction_file(path)


def test_product_create_transaction_json_round_trips_traceability_diagram_links() -> None:
    root = Path(tempfile.mkdtemp(prefix="odylith-authored-traceability-"))
    proposal, authority = _complete_authored_supplier_proposal(root)
    package = _package(proposal)
    transaction = build_product_create_transaction(
        proposal=proposal,
        release_selector="0.0.1",
        validation_gate={"status": "passed", "issues": []},
        prewrite_package=package,
        backlog_result=package.backlog_result or {},
        intent_authority=authority,
        quality_manifest=_approved_quality_manifest(),
        repo_root=root,
    )

    restored = product_create_transaction_from_dict(product_create_transaction_to_dict(transaction))
    plan = restored.prewrite_package.traceability_plan

    assert isinstance(plan, greenfield_traceability.GreenfieldTraceabilityPlan)
    assert isinstance(plan.workstreams[0].path, Path)
    assert plan.diagram_links[0].diagram_id == "D-001"
    assert plan.diagram_links[0].related_workstream_ids == ("B-001",)
    assert plan.diagram_links[0].related_backlog_paths == ("/repo/odylith/radar/source/ideas/B-001.md",)
    assert restored.prewrite_package.atlas_diagram_ids == transaction.prewrite_package.atlas_diagram_ids
    assert restored.prewrite_package.rendered_atlas_sources == transaction.prewrite_package.rendered_atlas_sources
    assert restored.prewrite_package.atlas_catalog_rows == transaction.prewrite_package.atlas_catalog_rows


def test_product_create_commit_owner_stays_separate_from_proposal_generation() -> None:
    commit_source = Path(greenfield_create_commit.__file__).read_text(encoding="utf-8")
    proposal_source = Path(greenfield_proposals.__file__).read_text(encoding="utf-8")

    assert "def commit_greenfield_create_transaction" not in proposal_source
    assert "GreenfieldApplyTransaction" not in proposal_source
    assert "greenfield_compiled_write" in commit_source
    assert "write_compiled_greenfield_package" in commit_source
    assert "require_greenfield_repository_preconditions" in commit_source
    assert "greenfield_repository_write_set" in commit_source
    assert "materialize_precompiled_greenfield_create_baseline" not in commit_source
    assert "materialize_precompiled_brand_assets" not in commit_source
    assert "ensure_greenfield_create_baseline" not in commit_source
    assert "write_greenfield_proposal" not in commit_source
    assert "greenfield_apply_write" not in commit_source
    forbidden_commit_tokens = (
        "run_greenfield_preconfirm_engine",
        "complete_confirmed_proposal",
        "complete_greenfield_semantic_apply_payload",
        "apply_greenfield_patchset_repairs",
        "build_product_create_transaction",
        "compile_greenfield_create_transaction",
        "normalize_host_reasoned_proposal",
        "validate_host_reasoned_proposal",
    )
    for token in forbidden_commit_tokens:
        assert token not in commit_source


def test_commit_product_create_transaction_is_commit_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _sealed_transaction(tmp_path)

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("commit must not run product interpretation, generation, repair, or surface refresh")

    for retired_name in (
        "_build_repaired_prewrite_package",
        "complete_confirmed_proposal",
        "complete_greenfield_semantic_apply_payload",
    ):
        assert not hasattr(greenfield_proposals, retired_name)
    monkeypatch.setattr(greenfield_proposals, "run_greenfield_preconfirm_engine", forbidden)
    monkeypatch.setattr(greenfield_apply_prewrite, "build_prewrite_completion_package", forbidden)
    monkeypatch.setattr(greenfield_release_commit, "materialize_compiled_release_target", forbidden)
    monkeypatch.setattr(greenfield_release_commit, "materialize_compiled_release_assignment", forbidden)
    monkeypatch.setattr(greenfield_component_commit, "materialize_compiled_component_from_preview", forbidden)
    monkeypatch.setattr(greenfield_apply_diagrams, "materialize_apply_diagrams", forbidden)

    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=transaction.transaction_file,
        transaction_hash=transaction.transaction_hash,
        confirm=True,
        started_at=0.0,
    )

    assert result["product_create_transaction"]["transaction_hash"] == transaction.transaction_hash
    assert result["product_create_transaction"]["verified"] is True
    assert result["repository_write_set"]["status"] == "passed"
    assert result["commit_manifest"]["write_transaction"]["status"] == "committed"
    assert result["commit_manifest"]["write_transaction"]["commit_only"] is True
    assert (
        result["commit_manifest"]["write_transaction"]["product_create_transaction_hash"]
        == transaction.transaction_hash
    )


def test_commit_product_create_transaction_rejects_bad_hash_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _sealed_transaction(tmp_path)

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("bad transaction hash must fail before baseline setup, rollback guard, or write path")

    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", forbidden)
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", forbidden)

    with pytest.raises(ValueError, match="does not match the confirmed transaction hash"):
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction.transaction_file,
            transaction_hash="not-the-compiled-hash",
            confirm=True,
            started_at=0.0,
        )


def test_commit_product_create_transaction_requires_a_receipt_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction_file = tmp_path / ".odylith/runtime/greenfield/missing-product-create-transaction.v1.json"

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("a missing receipt must fail before the write boundary")

    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", forbidden)
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", forbidden)

    with pytest.raises(ValueError, match="missing its pre-confirm compiler receipt"):
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction_file,
            transaction_hash="untrusted-in-memory-object",
            confirm=True,
            started_at=0.0,
        )


def test_commit_product_create_transaction_rejects_repo_drift_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _sealed_transaction(tmp_path)
    index_path = tmp_path / "odylith/radar/source/INDEX.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("operator edit after compile\n", encoding="utf-8")

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("repo drift must fail before entering the write boundary")

    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", forbidden)
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", forbidden)

    with pytest.raises(ValueError, match="repo preconditions changed"):
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction.transaction_file,
            transaction_hash=transaction.transaction_hash,
            confirm=True,
            started_at=0.0,
        )

    assert index_path.read_text(encoding="utf-8") == "operator edit after compile\n"


def test_commit_product_create_transaction_rejects_busy_repository_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _sealed_transaction(tmp_path)

    def busy(*_args: Any, **_kwargs: Any) -> None:
        raise BlockingIOError("simulated competing create transaction")

    monkeypatch.setattr(greenfield_repository_lock.fcntl, "flock", busy)
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", lambda **_kwargs: None)

    with pytest.raises(greenfield_create_commit.GreenfieldCreateCommitError) as exc:
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction.transaction_file,
            transaction_hash=transaction.transaction_hash,
            confirm=True,
            started_at=0.0,
        )

    assert exc.value.failure_kind == "post_confirm_repository_busy"
    assert exc.value.rollback_status == "not_started"


def test_commit_product_create_transaction_rejects_missing_confirm_before_hash_or_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction_file = tmp_path / ".odylith/runtime/greenfield/ignored-product-create-transaction.v1.json"

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("missing confirm must fail before hash verification, rollback guard, or write path")

    monkeypatch.setattr(greenfield_create_commit, "load_sealed_product_create_commit", forbidden)
    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", forbidden)
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", forbidden)

    with pytest.raises(ValueError, match="--confirm is required"):
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction_file,
            transaction_hash="not-the-compiled-hash",
            confirm=False,
            started_at=0.0,
        )


@pytest.mark.parametrize(
    "quality_manifest",
    (
        {"status": "failed", "validation_status": "passed", "issue_count": 0},
        {"status": "passed", "validation_status": "failed", "issue_count": 0},
        {"status": "passed", "validation_status": "passed", "issue_count": 0, "hard_blocker": "component spec"},
        {"status": "passed", "validation_status": "passed", "issue_count": 1},
        _approved_quality_manifest(version=""),
        _approved_quality_manifest(engine=""),
        _approved_quality_manifest(write_transaction={"status": "committed", "rollback_guard": "enabled"}),
        _approved_quality_manifest(
            write_transaction={
                "status": "not_started",
                "rollback_guard": "disabled",
                "prewrite_clean_before_commit": True,
            }
        ),
        _approved_quality_manifest(
            write_transaction={
                "status": "not_started",
                "rollback_guard": "enabled",
                "prewrite_clean_before_commit": False,
            }
        ),
        _approved_quality_manifest(
            write_transaction={
                "status": "not_started",
                "rollback_guard": "enabled",
                "prewrite_clean_before_commit": True,
                "commit_only": True,
            }
        ),
        _approved_quality_manifest(elapsed_seconds=60.0),
        _approved_quality_manifest(budget_seconds=90.0),
        _approved_quality_manifest(
            requested_repair_tier="auto",
            repair_tier="rescue",
            budget_seconds=90.0,
        ),
        _approved_quality_manifest(
            requested_repair_tier="auto",
            repair_tier="deep",
            budget_seconds=120.0,
        ),
        _approved_quality_manifest(
            semantic_compiler={
                "semantic_owner": "single_model_authoring_response",
                "post_authoring_interpretation_calls": 0,
            }
        ),
        _approved_quality_manifest(
            semantic_compiler={
                "version": "odylith.greenfield.authored-semantic-validation.v1",
                "status": "passed",
                "semantic_owner": "single_model_authoring_response",
                "post_authoring_interpretation_calls": 0,
            },
            model_authoring={
                "authoring_version": GREENFIELD_INTENT_AUTHORING_VERSION,
                "semantic_model_call_count": 1,
                "tier": "standard",
            },
        ),
        _approved_quality_manifest(
            semantic_compiler={
                "version": "odylith.greenfield.authored-semantic-validation.v1",
                "status": "passed",
                "semantic_owner": "single_model_authoring_response",
                "post_authoring_interpretation_calls": 0,
            },
            model_authoring={
                "authoring_version": "odylith.greenfield.intent-authoring.v4",
                "semantic_model_call_count": 1,
                "tier": "standard",
            },
        ),
    ),
)
def test_build_product_create_transaction_rejects_unapproved_manifest_before_confirmation(
    tmp_path: Path,
    quality_manifest: Mapping[str, Any],
) -> None:
    base = _transaction(repo_root=tmp_path)
    with pytest.raises(ValueError, match="pre-confirm ProductCreateTransaction quality manifest is not approved"):
        build_product_create_transaction(
            proposal=base.proposal,
            release_selector=base.release_selector,
            validation_gate=base.validation_gate,
            prewrite_package=base.prewrite_package,
            backlog_result=base.backlog_result,
            intent_authority=base.intent_authority,
            quality_manifest=quality_manifest,
            repo_root=tmp_path,
        )


def test_compiled_backlog_atlas_readback_rejects_backlog_drift(tmp_path: Path) -> None:
    proposal = _complete_authored_supplier_proposal(tmp_path)[0]
    idea_path = tmp_path / "odylith/radar/source/ideas/2026-07/2026-07-07-supplier-risk-readback-path.md"
    index_path = tmp_path / "odylith/radar/source/INDEX.md"
    package = _package(proposal)
    package = replace(
        package,
        backlog_result={
            **dict(package.backlog_result or {}),
            "idea_files": {str(idea_path): "compiled backlog text\n"},
            "backlog_index": str(index_path),
            "backlog_index_text": "| compiled backlog index |\n",
        },
    )
    idea_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    idea_path.write_text("drifted backlog text\n", encoding="utf-8")
    index_path.write_text("| compiled backlog index |\n", encoding="utf-8")

    with pytest.raises(ValueError, match="compiled backlog idea file readback does not match"):
        greenfield_compiled_readback.raise_for_compiled_backlog_and_atlas_readback(root=tmp_path, package=package)


def test_compiled_backlog_atlas_readback_rejects_atlas_drift(tmp_path: Path) -> None:
    proposal = _complete_authored_supplier_proposal(tmp_path)[0]
    idea_path = tmp_path / "odylith/radar/source/ideas/2026-07/2026-07-07-supplier-risk-readback-path.md"
    index_path = tmp_path / "odylith/radar/source/INDEX.md"
    atlas_path = tmp_path / "odylith/atlas/source/supplier-risk-flow.mmd"
    package = _package(proposal)
    package = replace(
        package,
        backlog_result={
            **dict(package.backlog_result or {}),
            "idea_files": {str(idea_path): "compiled backlog text\n"},
            "backlog_index": str(index_path),
            "backlog_index_text": "| compiled backlog index |\n",
        },
        rendered_atlas_sources={
            "odylith/atlas/source/supplier-risk-flow.mmd": "flowchart TD\n  A[\"Compiled\"] --> B[\"Flow\"]\n",
        },
    )
    idea_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    atlas_path.parent.mkdir(parents=True, exist_ok=True)
    idea_path.write_text("compiled backlog text\n", encoding="utf-8")
    index_path.write_text("| compiled backlog index |\n", encoding="utf-8")
    atlas_path.write_text("flowchart TD\n  A[\"Drifted\"] --> B[\"Flow\"]\n", encoding="utf-8")

    with pytest.raises(ValueError, match="compiled Atlas source readback does not match"):
        greenfield_compiled_readback.raise_for_compiled_backlog_and_atlas_readback(root=tmp_path, package=package)


def test_compiled_backlog_atlas_readback_accepts_exact_atlas_catalog_rows(tmp_path: Path) -> None:
    proposal = _complete_authored_supplier_proposal(tmp_path)[0]
    idea_path = tmp_path / "odylith/radar/source/ideas/2026-07/2026-07-07-supplier-risk-readback-path.md"
    index_path = tmp_path / "odylith/radar/source/INDEX.md"
    catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    package = _package(proposal)
    package = replace(
        package,
        backlog_result={
            **dict(package.backlog_result or {}),
            "idea_files": {str(idea_path): "compiled backlog text\n"},
            "backlog_index": str(index_path),
            "backlog_index_text": "| compiled backlog index |\n",
        },
    )
    idea_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    idea_path.write_text("compiled backlog text\n", encoding="utf-8")
    index_path.write_text("| compiled backlog index |\n", encoding="utf-8")
    for relative_path, source in package.rendered_atlas_sources.items():
        atlas_path = tmp_path / relative_path
        atlas_path.parent.mkdir(parents=True, exist_ok=True)
        atlas_path.write_text(source, encoding="utf-8")
    catalog_path.write_text(
        json.dumps(
            {
                "schema_version": "odylith.diagrams.v1",
                "diagrams": [dict(row) for row in package.atlas_catalog_rows],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    greenfield_compiled_readback.raise_for_compiled_backlog_and_atlas_readback(root=tmp_path, package=package)


def test_compiled_backlog_atlas_readback_rejects_atlas_catalog_drift(tmp_path: Path) -> None:
    proposal = _complete_authored_supplier_proposal(tmp_path)[0]
    idea_path = tmp_path / "odylith/radar/source/ideas/2026-07/2026-07-07-supplier-risk-readback-path.md"
    index_path = tmp_path / "odylith/radar/source/INDEX.md"
    catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    package = _package(proposal)
    package = replace(
        package,
        backlog_result={
            **dict(package.backlog_result or {}),
            "idea_files": {str(idea_path): "compiled backlog text\n"},
            "backlog_index": str(index_path),
            "backlog_index_text": "| compiled backlog index |\n",
        },
    )
    catalog_row = dict(package.atlas_catalog_rows[0])
    catalog_row["title"] = "Drifted Supplier Risk Flow"
    idea_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    idea_path.write_text("compiled backlog text\n", encoding="utf-8")
    index_path.write_text("| compiled backlog index |\n", encoding="utf-8")
    for relative_path, source in package.rendered_atlas_sources.items():
        atlas_path = tmp_path / relative_path
        atlas_path.parent.mkdir(parents=True, exist_ok=True)
        atlas_path.write_text(source, encoding="utf-8")
    catalog_rows = [dict(row) for row in package.atlas_catalog_rows]
    catalog_rows[0] = catalog_row
    catalog_path.write_text(
        json.dumps({"schema_version": "odylith.diagrams.v1", "diagrams": catalog_rows}, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"compiled Atlas catalog row readback does not match.*D-001.title"):
        greenfield_compiled_readback.raise_for_compiled_backlog_and_atlas_readback(root=tmp_path, package=package)


def test_compiled_backlog_writer_rejects_path_escape(tmp_path: Path) -> None:
    escaped_path = tmp_path.parent / "escaped-greenfield-backlog.md"

    with pytest.raises(ValueError, match="compiled backlog path escapes repo root"):
        greenfield_backlog_commit.write_backlog_files(
            {
                "idea_files": {str(escaped_path): "escaped text\n"},
                "backlog_index": "odylith/radar/source/INDEX.md",
                "backlog_index_text": "| index |\n",
            },
            repo_root=tmp_path,
        )


def test_prewrite_compiled_backlog_omits_program_metadata(tmp_path: Path) -> None:
    _seed_empty_governance_repo(tmp_path)
    authored, authority = _authored_supplier_proposal(tmp_path)
    confirmed_intent = dict(authored["intent"])
    confirmed_intent[PRODUCT_INTENT_AUTHORITY_KEY] = authority
    prompt = str(confirmed_intent["prompt"])
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_intent,
    )
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")

    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_prewrite.release_assignment_note(selector="0.0.1"),
    )

    rendered_backlog = "\n".join(prewrite.backlog_result["idea_files"].values())

    def structural_program_residue(value: object) -> list[str]:
        issues: list[str] = []
        if isinstance(value, Mapping):
            for key, item in value.items():
                normalized_key = str(key).casefold()
                if normalized_key in {
                    "program",
                    "confirmed_program",
                    "program_result",
                    "delivery_waves",
                    "execution_waves",
                }:
                    issues.append(normalized_key)
                if normalized_key in {"workstream_type", "execution_model"} and str(item).casefold() in {
                    "program_parent",
                    "umbrella",
                    "child",
                    "umbrella_waves",
                }:
                    issues.append(f"{normalized_key}={item}")
                issues.extend(structural_program_residue(item))
        elif isinstance(value, (list, tuple)):
            for item in value:
                issues.extend(structural_program_residue(item))
        return issues

    assert structural_program_residue(
        {
            "proposal": prewrite.package.proposal,
            "accepted_project_preview": prewrite.package.accepted_project_preview,
            "project_dashboard_preview": prewrite.package.project_dashboard_preview,
            "compass_memory_preview": prewrite.package.compass_memory_preview,
            "release_target_result": prewrite.package.release_target_result,
            "release_assignment_result": prewrite.package.release_assignment_result,
            "backlog_result": prewrite.package.backlog_result,
        }
    ) == []
    assert prewrite.package.release_workstream_ids
    assert "execution_model: umbrella_waves" not in rendered_backlog
    assert not list((tmp_path / "odylith/radar/source/programs").glob("*.execution-waves.v1.json"))


def test_compiled_write_replays_exact_sealed_release_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staged_root = tmp_path / "staged"
    release_registry_path = staged_root / "odylith/radar/source/releases/releases.v1.json"
    event_log_path = staged_root / "odylith/radar/source/releases/release-assignment-events.v1.jsonl"
    release_registry_path.parent.mkdir(parents=True, exist_ok=True)
    release_registry_bytes = b'{"aliases":{"0.0.1":"release-0-0-1","current":"release-0-0-1"}}\n'
    event_log_bytes = b'{"action":"add","release_id":"release-0-0-1","workstream_id":"B-001"}\n'
    release_registry_path.write_bytes(release_registry_bytes)
    event_log_path.write_bytes(event_log_bytes)
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=tmp_path,
        staged_root=staged_root,
    )
    transaction = _transaction(repo_root=tmp_path)
    transaction = replace(
        transaction,
        prewrite_package=replace(transaction.prewrite_package, repository_write_set=write_set),
    )

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("compiled create must not recompute release writes after confirmation")

    monkeypatch.setattr(greenfield_release_commit, "materialize_compiled_release_target", forbidden)
    monkeypatch.setattr(greenfield_release_commit, "materialize_compiled_release_assignment", forbidden)

    result = greenfield_compiled_write.write_compiled_greenfield_package(
        root=tmp_path,
        transaction=transaction,
    )

    assert (tmp_path / "odylith/radar/source/releases/releases.v1.json").read_bytes() == release_registry_bytes
    assert (
        tmp_path / "odylith/radar/source/releases/release-assignment-events.v1.jsonl"
    ).read_bytes() == event_log_bytes
    assert result["repository_write_set"]["write_set_hash"] == write_set["write_set_hash"]


def test_compiled_release_assignment_replay_is_idempotent(tmp_path: Path) -> None:
    idea_path = tmp_path / "odylith/radar/source/ideas/2026-07/2026-07-07-supplier-risk-release-replay-path.md"
    idea_title = "Prove supplier risk release replay path"
    idea_path.parent.mkdir(parents=True, exist_ok=True)
    idea_path.write_text(_valid_idea_file_text(idea_id="B-001", title=idea_title), encoding="utf-8")
    compiled_release = {
        "release_id": "release-0-0-1",
        "status": "planning",
        "version": "0.0.1",
        "tag": "v0.0.1",
        "name": "0.0.1",
        "notes": "Compiled release plan for Supplier Risk Board.",
        "created_utc": "2026-07-07",
        "shipped_utc": "",
        "closed_utc": "",
        "aliases": ["0.0.1", "current"],
    }
    compiled_event = {
        "action": "add",
        "workstream_id": "B-001",
        "release_id": "release-0-0-1",
        "recorded_at": "2026-07-07T00:00:00Z",
        "note": "Compiled assignment note.",
    }
    target_result = {
        "command": "ensure",
        "created": True,
        "dry_run": True,
        "release": compiled_release,
    }
    assignment_result = {
        "command": "add",
        "dry_run": True,
        "events": [compiled_event],
        "workstream_ids": ["B-001"],
        "new_workstream_ids": ["B-001"],
        "existing_workstream_ids": [],
        "release": compiled_release,
    }

    first_target = greenfield_release_commit.materialize_compiled_release_target(
        repo_root=tmp_path,
        release_selector="0.0.1",
        release_target_result=target_result,
    )
    first_assignment = greenfield_release_commit.materialize_compiled_release_assignment(
        repo_root=tmp_path,
        release_assignment_result=assignment_result,
    )
    second_target = greenfield_release_commit.materialize_compiled_release_target(
        repo_root=tmp_path,
        release_selector="0.0.1",
        release_target_result=target_result,
    )
    second_assignment = greenfield_release_commit.materialize_compiled_release_assignment(
        repo_root=tmp_path,
        release_assignment_result=assignment_result,
    )

    event_log = (tmp_path / "odylith/radar/source/releases/release-assignment-events.v1.jsonl").read_text(
        encoding="utf-8"
    )
    committed_events = [json.loads(line) for line in event_log.splitlines() if line.strip()]
    assert first_target["created"] is True
    assert second_target["created"] is False
    assert first_assignment["replayed_event_count"] == 1
    assert second_assignment["replayed_event_count"] == 0
    assert committed_events == [compiled_event]


def test_product_create_transaction_rejects_incomplete_compiled_package_before_confirm(tmp_path: Path) -> None:
    proposal, authority = _complete_authored_supplier_proposal(tmp_path)
    package = replace(_package(proposal), next_steps_preview=None)

    with pytest.raises(ValueError, match="missing compiled next_steps_preview"):
        build_product_create_transaction(
            proposal=proposal,
            release_selector="",
            validation_gate={"status": "passed", "issues": []},
            backlog_result=package.backlog_result or {},
            prewrite_package=package,
            intent_authority=authority,
            quality_manifest=_approved_quality_manifest(),
            repo_root=tmp_path,
        )


def test_product_create_transaction_rejects_drift_between_reviewed_and_compiled_proposals(
    tmp_path: Path,
) -> None:
    proposal, authority = _complete_authored_supplier_proposal(tmp_path)
    drifted_intent = {**proposal["intent"], "first_path": "DRIFTED PACKAGE PATH"}
    package = replace(_package(proposal), proposal={**proposal, "intent": drifted_intent})

    with pytest.raises(ValueError, match="compiled package proposal does not match"):
        build_product_create_transaction(
            proposal=proposal,
            release_selector="0.0.1",
            validation_gate={"status": "passed", "issues": []},
            backlog_result=package.backlog_result or {},
            prewrite_package=package,
            intent_authority=authority,
            quality_manifest=_approved_quality_manifest(),
            repo_root=tmp_path,
        )


def test_hash_verification_rejects_rehashed_compiled_package_proposal_drift(tmp_path: Path) -> None:
    transaction = _transaction(repo_root=tmp_path)
    drifted_intent = {
        **transaction.prewrite_package.proposal["intent"],
        "first_path": "DRIFTED PACKAGE PATH",
    }
    drifted_package = replace(
        transaction.prewrite_package,
        proposal={**transaction.prewrite_package.proposal, "intent": drifted_intent},
    )
    drifted = replace(transaction, prewrite_package=drifted_package, transaction_hash="")
    drifted = replace(
        drifted,
        transaction_hash=greenfield_create_transaction.product_create_transaction_hash(drifted),
    )

    assert not drifted.verified
    with pytest.raises(ValueError, match="compiled package proposal does not match"):
        greenfield_create_transaction.require_product_create_transaction_hash_verified(drifted)


def test_product_create_transaction_rejects_missing_surface_refresh_proof_before_confirm(tmp_path: Path) -> None:
    proposal, authority = _complete_authored_supplier_proposal(tmp_path)
    package = replace(_package(proposal), surface_refresh_preview=None)

    with pytest.raises(ValueError, match="missing compiled pre-confirm surface refresh proof"):
        build_product_create_transaction(
            proposal=proposal,
            release_selector="",
            validation_gate={"status": "passed", "issues": []},
            backlog_result=package.backlog_result or {},
            prewrite_package=package,
            intent_authority=authority,
            quality_manifest=_approved_quality_manifest(),
            repo_root=tmp_path,
        )


def test_product_create_transaction_rejects_missing_compiled_atlas_catalog_rows_before_confirm(
    tmp_path: Path,
) -> None:
    proposal, authority = _complete_authored_supplier_proposal(tmp_path)
    package = replace(_package(proposal), atlas_catalog_rows=())

    with pytest.raises(ValueError, match="Atlas catalog rows missing or incomplete"):
        build_product_create_transaction(
            proposal=proposal,
            release_selector="",
            validation_gate={"status": "passed", "issues": []},
            backlog_result=package.backlog_result or {},
            prewrite_package=package,
            intent_authority=authority,
            quality_manifest=_approved_quality_manifest(),
            repo_root=tmp_path,
        )


def test_product_create_transaction_rejects_missing_compiled_traceability_before_confirm(tmp_path: Path) -> None:
    proposal, authority = _complete_authored_supplier_proposal(tmp_path)
    package = replace(_package(proposal), traceability_plan=None)

    with pytest.raises(ValueError, match="missing compiled traceability_plan"):
        build_product_create_transaction(
            proposal=proposal,
            release_selector="",
            validation_gate={"status": "passed", "issues": []},
            backlog_result=package.backlog_result or {},
            prewrite_package=package,
            intent_authority=authority,
            quality_manifest=_approved_quality_manifest(),
            repo_root=tmp_path,
        )


def test_product_create_transaction_rejects_compiled_traceability_without_diagram_links(
    tmp_path: Path,
) -> None:
    proposal, authority = _complete_authored_supplier_proposal(tmp_path)
    package = _package(proposal)
    traceability_plan = replace(package.traceability_plan, diagram_links=())
    package = replace(package, traceability_plan=traceability_plan)

    with pytest.raises(ValueError, match="missing compiled traceability diagram links"):
        build_product_create_transaction(
            proposal=proposal,
            release_selector="",
            validation_gate={"status": "passed", "issues": []},
            backlog_result=package.backlog_result or {},
            prewrite_package=package,
            intent_authority=authority,
            quality_manifest=_approved_quality_manifest(),
            repo_root=tmp_path,
        )


def test_compiled_write_uses_exact_precompiled_component_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staged_root = tmp_path / "staged"
    registry_path = staged_root / "odylith/registry/source/component_registry.v1.json"
    spec_path = staged_root / "odylith/registry/source/components/supplier-risk-service/CURRENT_SPEC.md"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    registry_bytes = b'{"components":[{"component_id":"supplier-risk-service","name":"Compiled Registry Service"}]}\n'
    spec_bytes = b"# Compiled Registry Service\n\nCompiled registry service spec.\n"
    registry_path.write_bytes(registry_bytes)
    spec_path.write_bytes(spec_bytes)
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=tmp_path,
        staged_root=staged_root,
    )
    transaction = _transaction(repo_root=tmp_path)
    transaction = replace(
        transaction,
        prewrite_package=replace(transaction.prewrite_package, repository_write_set=write_set),
    )

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("post-confirm write must not recompute component authoring inputs")

    assert not hasattr(greenfield_component_commit, "component_authoring_responsibility")
    assert not hasattr(greenfield_component_commit, "component_dependency_lines")
    assert not hasattr(greenfield_component_commit, "component_risk_lines")
    assert not hasattr(greenfield_component_commit, "component_authoring")
    monkeypatch.setattr(
        greenfield_component_commit.component_compiled_commit,
        "materialize_compiled_component",
        forbidden,
    )

    result = greenfield_compiled_write.write_compiled_greenfield_package(
        root=tmp_path,
        transaction=transaction,
    )

    assert (tmp_path / "odylith/registry/source/component_registry.v1.json").read_bytes() == registry_bytes
    assert (
        tmp_path / "odylith/registry/source/components/supplier-risk-service/CURRENT_SPEC.md"
    ).read_bytes() == spec_bytes
    assert result["repository_write_set"]["write_set_hash"] == write_set["write_set_hash"]
