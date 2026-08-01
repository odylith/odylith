from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_write
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
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_release_commit
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import write_structured_confirmed_intent_file
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_create_transaction import PRODUCT_CREATE_TRANSACTION_COMPILER
from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import load_compiled_product_create_transaction_file
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_hash
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_from_dict
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_to_dict
from odylith.runtime.domain_intelligence.greenfield_create_transaction import require_product_create_transaction_verified
from odylith.runtime.domain_intelligence.greenfield_create_transaction import write_compiled_product_create_transaction_file
from odylith.runtime.domain_intelligence.greenfield_create_manifest import PRECONFIRM_ENGINE_VERSION
from odylith.runtime.domain_intelligence.greenfield_create_manifest import PRECONFIRM_QUALITY_MANIFEST_VERSION
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import build_product_intent_envelope
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import product_intent_authority_from_envelope
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.governance import backlog_authoring
from odylith.runtime.governance import validate_backlog_contract as backlog_contract
from odylith.runtime.surfaces import brand_assets
from tests.unit.runtime.greenfield_proposal_fixtures import CONFIRMED_INTENT_TEXT
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
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


def _intent_authority(
    repo_root: Path,
    *,
    write_files: bool = False,
    intent: Mapping[str, Any] | None = None,
    source_text: str = "",
) -> dict[str, Any]:
    markdown_path = repo_root / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    structured_path = markdown_path.with_suffix(".json")
    facts = dict(intent) if isinstance(intent, Mapping) else dict(_proposal()["intent"])
    evidence = source_text or json.dumps(facts, ensure_ascii=True, sort_keys=True)
    envelope = build_product_intent_envelope(
        facts,
        source_text=evidence,
        source_path=markdown_path,
        source_format="markdown" if source_text else "in_memory_confirmed_intent",
    )
    if write_files:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(evidence, encoding="utf-8")
        write_structured_confirmed_intent_file(markdown_path, facts, envelope=envelope)
    return product_intent_authority_from_envelope(
        envelope,
        structured_intent_path=structured_path,
        markdown_source_path=markdown_path,
    )


def _confirmed_intent_with_authority(repo_root: Path) -> dict[str, Any]:
    intent = parse_confirmed_intent_text(
        CONFIRMED_INTENT_TEXT,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
    )
    intent[PRODUCT_INTENT_AUTHORITY_KEY] = _intent_authority(
        repo_root,
        write_files=True,
        intent=intent,
        source_text=CONFIRMED_INTENT_TEXT,
    )
    return intent


def _package(proposal: dict[str, Any]) -> GreenfieldCompletionPackage:
    idea_path = Path("/repo/odylith/radar/source/ideas/B-001.md")
    created_backlog = [{"title": "Prove supplier risk review path", "idea_id": "B-001", "idea_path": str(idea_path)}]
    backlog_result = {
        "created": created_backlog,
        "idea_files": {str(idea_path): "Supplier risk review path"},
        "backlog_index": "/repo/odylith/radar/source/INDEX.md",
        "backlog_index_text": "| B-001 | Prove supplier risk review path |",
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
                "component_id": "supplier-risk-service",
                "label": "Supplier Risk Service",
                "spec_path": "odylith/registry/source/components/supplier-risk-service/CURRENT_SPEC.md",
                "implementation_handoff": {
                    "workstream_id": "B-001",
                    "workstream_title": "Prove supplier risk review path",
                    "implementation_prompt": "Implement the accepted supplier risk review path.",
                },
                "authoring_input": {
                    "component_id": "supplier-risk-service",
                    "label": "Supplier Risk Service",
                    "path": "src/supplier_risk",
                    "kind": "service",
                    "category": "application",
                    "qualification": "candidate",
                    "owner": "repo",
                    "status": "planned",
                    "product_layer": "application",
                    "sources": ("user_intent",),
                    "workstreams": ("B-001",),
                    "diagrams": (),
                    "responsibility": "Supplier Risk Service keeps supplier review state attached.",
                    "boundary": "Supplier review state only.",
                    "dependencies": (),
                    "interfaces": (),
                    "validation": (),
                    "risks": (),
                    "implementation_handoff": {
                        "workstream_id": "B-001",
                        "workstream_title": "Prove supplier risk review path",
                        "implementation_prompt": "Implement the accepted supplier risk review path.",
                    },
                    "component_contract": {},
                },
                "registry_entry": {
                    "component_id": "supplier-risk-service",
                    "name": "Supplier Risk Service",
                    "kind": "service",
                    "category": "application",
                    "qualification": "candidate",
                    "aliases": [],
                    "path_prefixes": ["src/supplier_risk"],
                    "workstreams": ["B-001"],
                    "diagrams": [],
                    "owner": "repo",
                    "status": "planned",
                    "what_it_is": "Supplier Risk Service defines the planned service ownership boundary for supplier review state.",
                    "why_tracked": "Tracked from user-stated intent because this named ownership boundary must stay understandable before source-backed behavior promotes it.",
                    "spec_ref": "odylith/registry/source/components/supplier-risk-service/CURRENT_SPEC.md",
                    "sources": ["user_intent"],
                    "subcomponents": [],
                    "product_layer": "application",
                },
            },
        ),
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
        program_result={
            "created": True,
            "dry_run": True,
            "umbrella_id": "B-001",
            "program_path": "/repo/odylith/radar/source/programs/B-001.execution-waves.v1.json",
            "waves": [
                {
                    "wave_id": "W1",
                    "label": "First release slice",
                    "status": "active",
                    "summary": "Review the first supplier risk path.",
                    "exit_gate": "The first supplier review path is proven.",
                    "validation": [],
                    "depends_on": [],
                    "primary_workstreams": ["B-001"],
                    "carried_workstreams": [],
                    "in_band_workstreams": [],
                    "gate_refs": [],
                }
            ],
            "program_count": 0,
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


def _record_compiled_memory_for_readback(**kwargs: Any) -> dict[str, Any]:
    repo_root = Path(kwargs["repo_root"])
    source_root = repo_root / "odylith/runtime/source"
    source_root.mkdir(parents=True, exist_ok=True)
    accepted_project = dict(kwargs.get("accepted_project_preview") or {})
    (source_root / "accepted-project.v1.json").write_text(
        json.dumps(accepted_project, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (source_root / "project-brief.v1.md").write_text(
        str(kwargs.get("project_brief_record_text") or ""),
        encoding="utf-8",
    )
    event = dict(kwargs.get("compass_memory_preview") or {})
    stream_path = repo_root / "odylith/compass/runtime/agent-stream.v1.jsonl"
    _write_compass_memory_event(repo_root, event)
    return {"stream": str(stream_path), "event": event}


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
        "elapsed_seconds": 12.3,
        "write_transaction": {
            "status": "not_started",
            "rollback_guard": "enabled",
            "prewrite_clean_before_commit": True,
        },
    }
    manifest.update(overrides)
    return manifest


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
    root = repo_root or Path("/repo")
    proposal = _proposal()
    authority = _intent_authority(root, write_files=repo_root is not None)
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = authority
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
    package = _package(_proposal())
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
    package = _package(_proposal())
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
    package = _package(_proposal())
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
    package = _package(_proposal())
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
    package = _package(_proposal())
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
    authority = _intent_authority(Path("/repo"))
    proposal = {
        **_proposal(),
        PRODUCT_INTENT_AUTHORITY_KEY: authority,
        "diagrams": [
            {
                "slug": "supplier-risk-flow",
                "title": "Supplier Risk Flow",
                "summary": "Supplier risk review path traceability.",
                "kind": "flowchart",
            }
        ],
    }
    package = _package(proposal)
    transaction = build_product_create_transaction(
        proposal=proposal,
        release_selector="0.0.1",
        validation_gate={"status": "passed", "issues": []},
        prewrite_package=package,
        backlog_result=package.backlog_result or {},
        intent_authority=authority,
        quality_manifest=_approved_quality_manifest(),
        repo_root=Path("/repo"),
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

    monkeypatch.setattr(greenfield_proposals, "_build_repaired_prewrite_package", forbidden)
    monkeypatch.setattr(greenfield_proposals, "run_greenfield_preconfirm_engine", forbidden)
    monkeypatch.setattr(greenfield_proposals, "complete_confirmed_proposal", forbidden)
    monkeypatch.setattr(greenfield_proposals, "complete_greenfield_semantic_apply_payload", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "write_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_apply_prewrite, "build_prewrite_completion_package", forbidden)
    monkeypatch.setattr(greenfield_programs, "materialize_compiled_greenfield_program", forbidden)
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
    monkeypatch.setattr(greenfield_apply_write, "write_greenfield_proposal", forbidden)
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

    monkeypatch.setattr(greenfield_create_commit.fcntl, "flock", busy)
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


def test_write_greenfield_proposal_does_not_materialize_a_program(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = _proposal()
    package = _package(proposal)
    backlog_result = dict(package.backlog_result or {})
    idea_path = tmp_path / "odylith/radar/source/ideas/B-001.md"
    backlog_result["created"] = [
        {**dict(row), "idea_path": str(idea_path)}
        for row in backlog_result.get("created", [])
        if isinstance(row, dict)
    ]
    backlog_result["idea_files"] = {str(idea_path): "Supplier risk review path\n"}
    backlog_result["backlog_index"] = str(tmp_path / "odylith/radar/source/INDEX.md")
    backlog_result["backlog_index_text"] = "| B-001 | Prove supplier risk review path |\n"
    package = replace(
        package,
        backlog_result=backlog_result,
        traceability_plan=greenfield_traceability.build_traceability_plan(
            proposal=proposal,
            created_backlog=backlog_result["created"],
            diagram_ids=(),
        ),
    )
    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("greenfield onboarding must not create an execution program")

    monkeypatch.setattr(greenfield_programs, "create_greenfield_program", forbidden)
    monkeypatch.setattr(greenfield_programs, "first_release_workstream_ids", forbidden)
    monkeypatch.setattr(greenfield_programs, "materialize_compiled_greenfield_program", forbidden)
    monkeypatch.setattr(greenfield_apply_write.greenfield_traceability, "build_traceability_plan", forbidden)
    monkeypatch.setattr(greenfield_apply_write.greenfield_traceability, "apply_backlog_traceability", forbidden)
    monkeypatch.setattr(greenfield_apply_write.greenfield_experience, "build_component_handoffs", forbidden)
    monkeypatch.setattr(greenfield_apply_write.greenfield_experience, "build_next_steps", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "record_greenfield_acceptance", forbidden)
    monkeypatch.setattr(
        greenfield_apply_write,
        "record_compiled_greenfield_acceptance",
        _record_compiled_memory_for_readback,
    )
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_component_spec_quality", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_final_next_steps_quality", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_final_package_quality", forbidden)
    calls: dict[str, Any] = {}

    def fake_compiled_readback(**kwargs: Any) -> None:
        calls["compiled_readback"] = kwargs

    monkeypatch.setattr(
        greenfield_apply_write.greenfield_compiled_readback,
        "raise_for_compiled_backlog_and_atlas_readback",
        fake_compiled_readback,
    )
    monkeypatch.setattr(greenfield_apply_write, "_refresh_greenfield_dashboard", lambda **_kwargs: {"status": "passed"})
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "skipped"},
    )

    result = greenfield_apply_write.write_greenfield_proposal(
        root=tmp_path,
        proposal=proposal,
        release_selector="",
        tribunal={"status": "passed", "issues": []},
        backlog_result=backlog_result,
        prewrite_package=package,
    )

    assert calls["compiled_readback"]["package"] is package
    assert result["next_steps"] == package.next_steps_preview
    assert "program" not in result
    assert not list((tmp_path / "odylith/radar/source/programs").glob("*.execution-waves.v1.json"))
    assert result["backlog_topology"] == ["odylith/radar/source/ideas/B-001.md"]


def test_compiled_backlog_atlas_readback_rejects_backlog_drift(tmp_path: Path) -> None:
    proposal = _proposal()
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
    proposal = _proposal()
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
    proposal = {
        **_proposal(),
        "diagrams": [
            {
                "slug": "supplier-risk-flow",
                "title": "Supplier Risk Flow",
                "summary": "Supplier risk review path traceability.",
                "kind": "flowchart",
            }
        ],
    }
    idea_path = tmp_path / "odylith/radar/source/ideas/2026-07/2026-07-07-supplier-risk-readback-path.md"
    index_path = tmp_path / "odylith/radar/source/INDEX.md"
    atlas_path = tmp_path / "odylith/atlas/source/supplier-risk-flow.mmd"
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
    atlas_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    idea_path.write_text("compiled backlog text\n", encoding="utf-8")
    index_path.write_text("| compiled backlog index |\n", encoding="utf-8")
    atlas_path.write_text(package.rendered_atlas_sources["odylith/atlas/source/supplier-risk-flow.mmd"], encoding="utf-8")
    catalog_path.write_text(
        json.dumps({"schema_version": "odylith.diagrams.v1", "diagrams": [dict(package.atlas_catalog_rows[0])]}, indent=2)
        + "\n",
        encoding="utf-8",
    )

    greenfield_compiled_readback.raise_for_compiled_backlog_and_atlas_readback(root=tmp_path, package=package)


def test_compiled_backlog_atlas_readback_rejects_atlas_catalog_drift(tmp_path: Path) -> None:
    proposal = {
        **_proposal(),
        "diagrams": [
            {
                "slug": "supplier-risk-flow",
                "title": "Supplier Risk Flow",
                "summary": "Supplier risk review path traceability.",
                "kind": "flowchart",
            }
        ],
    }
    idea_path = tmp_path / "odylith/radar/source/ideas/2026-07/2026-07-07-supplier-risk-readback-path.md"
    index_path = tmp_path / "odylith/radar/source/INDEX.md"
    atlas_path = tmp_path / "odylith/atlas/source/supplier-risk-flow.mmd"
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
    atlas_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    idea_path.write_text("compiled backlog text\n", encoding="utf-8")
    index_path.write_text("| compiled backlog index |\n", encoding="utf-8")
    atlas_path.write_text(package.rendered_atlas_sources["odylith/atlas/source/supplier-risk-flow.mmd"], encoding="utf-8")
    catalog_path.write_text(
        json.dumps({"schema_version": "odylith.diagrams.v1", "diagrams": [catalog_row]}, indent=2) + "\n",
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
    prompt = "Draft a greenfield proposal for a municipal permit review workspace"
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=_confirmed_intent_with_authority(tmp_path),
    )
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")

    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_write.release_assignment_note(selector="0.0.1"),
    )

    rendered_backlog = "\n".join(prewrite.backlog_result["idea_files"].values())

    assert prewrite.package.program_result == {}
    assert prewrite.package.release_workstream_ids
    assert "execution_model: umbrella_waves" not in rendered_backlog
    assert not list((tmp_path / "odylith/radar/source/programs").glob("*.execution-waves.v1.json"))


def test_write_greenfield_proposal_compiled_path_does_not_run_source_casing_repair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = {
        **_proposal(),
        "intent": {
            "title": "GLP-1 Companion",
            "prompt": "Build a GLP-1 companion that keeps GLP-1 medication tracking reviewable.",
        },
        "confirmed_intent": {
            "product_story": "GLP-1 patients need a reviewable medication tracking path.",
        },
    }
    package = _package(proposal)
    backlog_result = dict(package.backlog_result or {})
    idea_path = tmp_path / "odylith/radar/source/ideas/B-001.md"
    backlog_result["created"] = [
        {**dict(row), "idea_path": str(idea_path)}
        for row in backlog_result.get("created", [])
        if isinstance(row, dict)
    ]
    backlog_result["idea_files"] = {str(idea_path): "GLP-1 companion review path\n"}
    backlog_result["backlog_index"] = str(tmp_path / "odylith/radar/source/INDEX.md")
    backlog_result["backlog_index_text"] = "| B-001 | Prove GLP-1 companion review path |\n"
    package = replace(
        package,
        backlog_result=backlog_result,
        traceability_plan=greenfield_traceability.build_traceability_plan(
            proposal=proposal,
            created_backlog=backlog_result["created"],
            diagram_ids=(),
        ),
    )

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("compiled create must not repair source casing after confirmation")

    def fake_materialize(**_kwargs: Any) -> dict[str, Any]:
        return {
            "created": True,
            "umbrella_id": "B-001",
            "program_path": str(tmp_path / "odylith/radar/source/programs/B-001.execution-waves.v1.json"),
            "waves": list(package.program_result["waves"]),
            "program_count": 1,
        }

    monkeypatch.setattr(greenfield_apply_write.greenfield_source_casing, "proposal_source_casing_text", forbidden)
    monkeypatch.setattr(greenfield_apply_write.greenfield_source_casing, "restore_source_casing_in_public_copy", forbidden)
    monkeypatch.setattr(greenfield_apply_write.greenfield_source_casing, "package_with_source_casing", forbidden)
    monkeypatch.setattr(greenfield_programs, "create_greenfield_program", forbidden)
    monkeypatch.setattr(greenfield_programs, "first_release_workstream_ids", forbidden)
    monkeypatch.setattr(greenfield_programs, "materialize_compiled_greenfield_program", fake_materialize)
    monkeypatch.setattr(greenfield_apply_write.greenfield_traceability, "build_traceability_plan", forbidden)
    monkeypatch.setattr(greenfield_apply_write.greenfield_traceability, "apply_backlog_traceability", forbidden)
    monkeypatch.setattr(greenfield_apply_write.greenfield_experience, "build_component_handoffs", forbidden)
    monkeypatch.setattr(greenfield_apply_write.greenfield_experience, "build_next_steps", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "record_greenfield_acceptance", forbidden)
    monkeypatch.setattr(
        greenfield_apply_write,
        "record_compiled_greenfield_acceptance",
        _record_compiled_memory_for_readback,
    )
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_component_spec_quality", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_final_next_steps_quality", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_final_package_quality", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "_refresh_greenfield_dashboard", lambda **_kwargs: {"status": "passed"})
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "skipped"},
    )

    result = greenfield_apply_write.write_greenfield_proposal(
        root=tmp_path,
        proposal=proposal,
        release_selector="",
        tribunal={"status": "passed", "issues": []},
        backlog_result=backlog_result,
        prewrite_package=package,
    )

    assert result["next_steps"] == package.next_steps_preview
    assert result["backlog_topology"] == ["odylith/radar/source/ideas/B-001.md"]


def test_write_greenfield_proposal_compiled_path_replays_release_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = _proposal()
    package = _package(proposal)
    backlog_result = dict(package.backlog_result or {})
    idea_path = tmp_path / "odylith/radar/source/ideas/2026-07/2026-07-07-supplier-risk-release-replay-path.md"
    idea_title = "Prove supplier risk release replay path"
    backlog_result["created"] = [
        {**dict(row), "title": idea_title, "idea_path": str(idea_path)}
        for row in backlog_result.get("created", [])
        if isinstance(row, dict)
    ]
    backlog_result["idea_files"] = {str(idea_path): _valid_idea_file_text(idea_id="B-001", title=idea_title)}
    backlog_result["backlog_index"] = str(tmp_path / "odylith/radar/source/INDEX.md")
    backlog_result["backlog_index_text"] = "| B-001 | Prove supplier risk release replay path |\n"
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
    package = replace(
        package,
        backlog_result=backlog_result,
        traceability_plan=greenfield_traceability.build_traceability_plan(
            proposal=proposal,
            created_backlog=backlog_result["created"],
            diagram_ids=(),
        ),
        release_target_result={
            "command": "ensure",
            "created": True,
            "dry_run": True,
            "release": compiled_release,
            "registry_path": str(tmp_path / "odylith/radar/source/releases/releases.v1.json"),
        },
        release_assignment_result={
            "command": "add",
            "dry_run": True,
            "events": [compiled_event],
            "workstream_ids": ["B-001"],
            "new_workstream_ids": ["B-001"],
            "existing_workstream_ids": [],
            "release": compiled_release,
            "event_log_path": str(tmp_path / "odylith/radar/source/releases/release-assignment-events.v1.jsonl"),
        },
    )

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("compiled create must not recompute release writes after confirmation")

    def fake_materialize(**_kwargs: Any) -> dict[str, Any]:
        return {
            "created": True,
            "umbrella_id": "B-001",
            "program_path": str(tmp_path / "odylith/radar/source/programs/B-001.execution-waves.v1.json"),
            "waves": list(package.program_result["waves"]),
            "program_count": 1,
        }

    monkeypatch.setattr(greenfield_apply_write.greenfield_apply_prewrite, "ensure_release_target", forbidden)
    monkeypatch.setattr(greenfield_apply_write.release_planning_authoring, "add_workstreams_to_release", forbidden)
    monkeypatch.setattr(greenfield_programs, "create_greenfield_program", forbidden)
    monkeypatch.setattr(greenfield_programs, "first_release_workstream_ids", forbidden)
    monkeypatch.setattr(greenfield_programs, "materialize_compiled_greenfield_program", fake_materialize)
    monkeypatch.setattr(greenfield_apply_write.greenfield_traceability, "build_traceability_plan", forbidden)
    monkeypatch.setattr(greenfield_apply_write.greenfield_traceability, "apply_backlog_traceability", forbidden)
    monkeypatch.setattr(greenfield_apply_write.greenfield_experience, "build_component_handoffs", forbidden)
    monkeypatch.setattr(greenfield_apply_write.greenfield_experience, "build_next_steps", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "record_greenfield_acceptance", forbidden)
    monkeypatch.setattr(
        greenfield_apply_write,
        "record_compiled_greenfield_acceptance",
        _record_compiled_memory_for_readback,
    )
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_component_spec_quality", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_final_next_steps_quality", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_final_package_quality", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "_refresh_greenfield_dashboard", lambda **_kwargs: {"status": "passed"})
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "skipped"},
    )

    result = greenfield_apply_write.write_greenfield_proposal(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        tribunal={"status": "passed", "issues": []},
        backlog_result=backlog_result,
        prewrite_package=package,
    )

    release_registry = json.loads(
        (tmp_path / "odylith/radar/source/releases/releases.v1.json").read_text(encoding="utf-8")
    )
    event_log = (tmp_path / "odylith/radar/source/releases/release-assignment-events.v1.jsonl").read_text(
        encoding="utf-8"
    )
    committed_events = [json.loads(line) for line in event_log.splitlines() if line.strip()]
    assert release_registry["aliases"]["0.0.1"] == "release-0-0-1"
    assert release_registry["aliases"]["current"] == "release-0-0-1"
    assert release_registry["releases"][0] == {key: compiled_release[key] for key in release_registry["releases"][0]}
    assert committed_events == [compiled_event]
    assert result["release_bootstrap"]["dry_run"] is False
    assert result["release_target"]["dry_run"] is False
    assert result["release_target"]["events"] == [compiled_event]


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


def test_write_greenfield_proposal_legacy_path_still_applies_backlog_traceability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = _proposal()
    idea_path = tmp_path / "odylith/radar/source/ideas/B-001.md"
    backlog_result: dict[str, Any] = {
        "created": [{"title": "Prove supplier risk review path", "idea_id": "B-001", "idea_path": str(idea_path)}],
        "idea_files": {str(idea_path): "Supplier risk review path\n"},
        "backlog_index": str(tmp_path / "odylith/radar/source/INDEX.md"),
        "backlog_index_text": "| B-001 | Prove supplier risk review path |\n",
        "_candidate_idea_specs": {},
    }
    sentinel_plan = greenfield_traceability.build_traceability_plan(
        proposal=proposal,
        created_backlog=backlog_result["created"],
        diagram_ids=(),
    )
    build_calls: list[dict[str, Any]] = []
    traceability_calls: list[dict[str, Any]] = []

    def fake_build_traceability(**kwargs: Any) -> greenfield_traceability.GreenfieldTraceabilityPlan:
        build_calls.append(kwargs)
        return sentinel_plan

    def fake_apply_traceability(**kwargs: Any) -> list[str]:
        traceability_calls.append(kwargs)
        return ["legacy-traceability-applied"]

    monkeypatch.setattr(
        greenfield_programs,
        "create_greenfield_program",
        lambda **_kwargs: {"created": True, "program_count": 1, "waves": []},
    )
    monkeypatch.setattr(greenfield_programs, "first_release_workstream_ids", lambda **_kwargs: ["B-001"])
    monkeypatch.setattr(greenfield_apply_write.greenfield_traceability, "build_traceability_plan", fake_build_traceability)
    monkeypatch.setattr(greenfield_apply_write.greenfield_traceability, "apply_backlog_traceability", fake_apply_traceability)
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_component_spec_quality", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_final_next_steps_quality", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_final_package_quality", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write, "_refresh_greenfield_dashboard", lambda **_kwargs: {"status": "passed"})
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "skipped"},
    )
    monkeypatch.setattr(greenfield_apply_write, "record_greenfield_acceptance", lambda **_kwargs: {"event": {}})

    result = greenfield_apply_write.write_greenfield_proposal(
        root=tmp_path,
        proposal=proposal,
        release_selector="",
        tribunal={"status": "passed", "issues": []},
        backlog_result=backlog_result,
    )

    assert len(build_calls) == 1
    assert len(traceability_calls) == 1
    assert traceability_calls[0]["plan"] is sentinel_plan
    assert result["backlog_topology"] == ["legacy-traceability-applied"]


def test_product_create_transaction_rejects_incomplete_compiled_package_before_confirm(tmp_path: Path) -> None:
    proposal = _proposal()
    authority = _intent_authority(tmp_path, write_files=True)
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = authority
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


def test_product_create_transaction_rejects_missing_surface_refresh_proof_before_confirm(tmp_path: Path) -> None:
    proposal = _proposal()
    authority = _intent_authority(tmp_path, write_files=True)
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = authority
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
    proposal = {
        **_proposal(),
        "diagrams": [
            {
                "slug": "supplier-risk-flow",
                "title": "Supplier Risk Flow",
                "summary": "Supplier risk review path traceability.",
                "kind": "flowchart",
            }
        ],
    }
    authority = _intent_authority(tmp_path, write_files=True)
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = authority
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
    proposal = _proposal()
    authority = _intent_authority(tmp_path, write_files=True)
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = authority
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


def test_write_greenfield_proposal_rejects_compiled_traceability_without_diagram_links(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = {
        **_proposal(),
        "diagrams": [
            {
                "slug": "supplier-risk-flow",
                "title": "Supplier Risk Flow",
                "summary": "Supplier risk review path traceability.",
                "kind": "flowchart",
            }
        ],
    }
    authority = _intent_authority(tmp_path, write_files=True)
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = authority
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


def test_write_greenfield_proposal_uses_precompiled_component_authoring_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = {
        **_proposal(),
        "components": [
            {
                "component_id": "supplier-risk-service",
                "label": "Proposal Recomputed Label",
                "intended_path": "src/proposal",
                "kind": "service",
                "release_scope": "first_release",
                "responsibility": "This proposal value must not be used after confirmation.",
            }
        ],
    }
    package = _package(proposal)
    backlog_result = dict(package.backlog_result or {})
    idea_path = tmp_path / "odylith/radar/source/ideas/B-001.md"
    backlog_result["created"] = [
        {**dict(row), "idea_path": str(idea_path)}
        for row in backlog_result.get("created", [])
        if isinstance(row, dict)
    ]
    backlog_result["idea_files"] = {str(idea_path): "Supplier risk review path\n"}
    backlog_result["backlog_index"] = str(tmp_path / "odylith/radar/source/INDEX.md")
    backlog_result["backlog_index_text"] = "| B-001 | Prove supplier risk review path |\n"
    authoring_input = {
        **package.component_registry_preview[0]["authoring_input"],
        "label": "Compiled Registry Service",
        "path": "src/compiled",
        "responsibility": "Compiled Registry Service keeps accepted supplier review state attached.",
        "workstreams": ("B-001", "B-099"),
    }
    registry_entry = {
        **package.component_registry_preview[0]["registry_entry"],
        "name": "Compiled Registry Service",
        "path_prefixes": ["src/compiled"],
        "workstreams": ["B-001", "B-099"],
        "what_it_is": "Compiled Registry Service defines the planned service ownership boundary for accepted supplier review state.",
    }
    component_preview = (
        {
            **package.component_registry_preview[0],
            "label": "Compiled Registry Service",
            "authoring_input": authoring_input,
            "registry_entry": registry_entry,
        },
    )
    package = replace(
        package,
        proposal=proposal,
        backlog_result=backlog_result,
        component_registry_preview=component_preview,
        traceability_plan=greenfield_traceability.build_traceability_plan(
            proposal=proposal,
            created_backlog=backlog_result["created"],
            diagram_ids=(),
        ),
        rendered_component_specs={
            "Compiled Registry Service": "# Compiled Registry Service\n\nCompiled registry service spec.\n"
        },
    )
    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("post-confirm write must not recompute component authoring inputs")

    def fake_materialize(**_kwargs: Any) -> dict[str, Any]:
        return {
            "created": True,
            "umbrella_id": "B-001",
            "program_path": str(tmp_path / "odylith/radar/source/programs/B-001.execution-waves.v1.json"),
            "waves": list(package.program_result["waves"]),
            "program_count": 1,
        }

    monkeypatch.setattr(greenfield_programs, "materialize_compiled_greenfield_program", fake_materialize)
    monkeypatch.setattr(greenfield_apply_write.greenfield_traceability, "build_traceability_plan", forbidden)
    monkeypatch.setattr(greenfield_apply_write.greenfield_traceability, "apply_backlog_traceability", forbidden)
    monkeypatch.setattr(greenfield_apply_write.greenfield_experience, "build_component_handoffs", forbidden)
    monkeypatch.setattr(greenfield_component_commit, "component_authoring_responsibility", forbidden)
    monkeypatch.setattr(greenfield_component_commit, "component_dependency_lines", forbidden)
    monkeypatch.setattr(greenfield_component_commit, "component_risk_lines", forbidden)
    monkeypatch.setattr(greenfield_component_commit.component_authoring, "register_component", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "record_greenfield_acceptance", forbidden)
    monkeypatch.setattr(
        greenfield_apply_write,
        "record_compiled_greenfield_acceptance",
        _record_compiled_memory_for_readback,
    )
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_component_spec_quality", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_final_next_steps_quality", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_final_package_quality", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "_refresh_greenfield_dashboard", lambda **_kwargs: {"status": "passed"})
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "skipped"},
    )

    result = greenfield_apply_write.write_greenfield_proposal(
        root=tmp_path,
        proposal=proposal,
        release_selector="",
        tribunal={"status": "passed", "issues": []},
        backlog_result=backlog_result,
        prewrite_package=package,
    )

    registry = json.loads(
        (tmp_path / "odylith/registry/source/component_registry.v1.json").read_text(encoding="utf-8")
    )
    committed_entry = registry["components"][0]
    assert committed_entry == registry_entry
    committed_spec = (
        tmp_path / "odylith/registry/source/components/supplier-risk-service/CURRENT_SPEC.md"
    ).read_text(encoding="utf-8")
    assert committed_spec == "# Compiled Registry Service\n\nCompiled registry service spec.\n"
    assert result["components"][0]["label"] == "Compiled Registry Service"
    assert result["backlog_topology"] == ["odylith/radar/source/ideas/B-001.md"]


def test_materialize_compiled_greenfield_program_does_not_recompute_governance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = backlog_contract.IdeaSpec(
        path=tmp_path / "odylith/radar/source/ideas/B-001.md",
        metadata={"idea_id": "B-001"},
        sections=set(),
        section_bodies={},
    )
    program_path = tmp_path / "odylith/radar/source/programs/B-001.execution-waves.v1.json"
    calls: dict[str, Any] = {}

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("compiled program materialization must not recompute governance")

    def fake_update(path: Path, updates: dict[str, str]) -> None:
        calls["metadata_path"] = path
        calls["metadata_updates"] = updates

    def fake_write(repo_root: Path, umbrella_id: str, payload: dict[str, Any]) -> Path:
        calls["program_payload"] = payload
        program_path.parent.mkdir(parents=True, exist_ok=True)
        program_path.write_text("compiled program\n", encoding="utf-8")
        return program_path

    monkeypatch.setattr(greenfield_programs.program_wave_execution_engine, "program_governance_decision", forbidden)
    monkeypatch.setattr(greenfield_programs.program_wave_authoring, "_update_idea_metadata", fake_update)
    monkeypatch.setattr(greenfield_programs.program_wave_authoring, "_write_program_document", fake_write)
    monkeypatch.setattr(greenfield_programs.execution_wave_contract, "collect_execution_programs", lambda **_kwargs: ([{}], []))

    result = greenfield_programs.materialize_compiled_greenfield_program(
        repo_root=tmp_path,
        backlog_result={"_candidate_idea_specs": {"B-001": spec}},
        program_result={
            "created": True,
            "dry_run": True,
            "umbrella_id": "B-001",
            "waves": [{"wave_id": "W1", "primary_workstreams": ["B-001"]}],
            "program_count": 0,
        },
    )

    assert calls["metadata_path"] == spec.path
    assert calls["metadata_updates"]["execution_model"] == "umbrella_waves"
    assert calls["program_payload"]["waves"] == [{"wave_id": "W1", "primary_workstreams": ["B-001"]}]
    assert "dry_run" not in result
    assert result["program_path"] == str(program_path)
    assert result["program_count"] == 1
