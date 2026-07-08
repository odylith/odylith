from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_from_dict
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_to_dict
from odylith.runtime.domain_intelligence.greenfield_create_transaction import require_product_create_transaction_verified
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.governance import validate_backlog_contract as backlog_contract


def _proposal() -> dict[str, Any]:
    return {
        "intent": {"title": "Supplier Risk Board"},
        "backlog": [{"title": "Prove supplier risk review path"}],
        "components": [],
        "diagrams": [],
    }


def _package(proposal: dict[str, Any]) -> GreenfieldCompletionPackage:
    return GreenfieldCompletionPackage(
        proposal=proposal,
        release_selector="0.0.1",
        atlas_review_date="2026-07-07",
        backlog_result={
            "created": [{"title": "Prove supplier risk review path", "idea_id": "B-001"}],
            "idea_files": {"/repo/odylith/radar/source/ideas/B-001.md": "Supplier risk review path"},
            "backlog_index": "/repo/odylith/radar/source/INDEX.md",
            "backlog_index_text": "| B-001 | Prove supplier risk review path |",
            "_candidate_idea_specs": {
                "B-001": backlog_contract.IdeaSpec(
                    path=Path("/repo/odylith/radar/source/ideas/B-001.md"),
                    metadata={"idea_id": "B-001", "status": "candidate"},
                    sections={"Problem", "Product View"},
                    section_bodies={"Problem": "Supplier risk is hard to review.", "Product View": "Review board."},
                )
            },
        },
        prewrite_safety_preview={"status": "passed"},
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
            },
        ),
        project_brief_record_text="# Supplier Risk Board Project Brief\n\n- accepted_at: prewrite\n",
        accepted_project_preview={
            "schema_version": "odylith.accepted_project.v1",
            "origin": "greenfield",
            "evidence_tier": "user_intent",
            "accepted_at": "prewrite",
            "title": "Supplier Risk Board",
            "source_launch": {"implementation_prompt": "Start B-001 from the accepted transaction package."},
            "created": {"workstreams": [{"idea_id": "B-001"}], "components": [], "diagrams": []},
            "validation_gate": {"status": "passed", "issues": []},
        },
        compass_memory_preview={
            "version": "v1",
            "kind": "decision",
            "summary": "Accepted greenfield proposal for Supplier Risk Board.",
            "ts_iso": "prewrite",
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
        release_workstream_ids=("B-001",),
    )


def _transaction() -> Any:
    proposal = _proposal()
    package = _package(proposal)
    return build_product_create_transaction(
        proposal=proposal,
        release_selector="0.0.1",
        validation_gate={"status": "passed", "issues": []},
        prewrite_package=package,
        backlog_result=package.backlog_result or {},
        quality_manifest={
            "status": "passed",
            "validation_status": "passed",
            "elapsed_seconds": 12.3,
            "write_transaction": {"status": "not_started", "rollback_guard": "enabled"},
        },
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
    with pytest.raises(ValueError, match="hash mismatch"):
        require_product_create_transaction_verified(tampered)


def test_product_create_transaction_json_round_trips_with_hash() -> None:
    transaction = _transaction()
    payload = product_create_transaction_to_dict(transaction)

    restored = product_create_transaction_from_dict(payload)

    assert restored.transaction_hash == transaction.transaction_hash
    assert restored.verified
    assert restored.prewrite_package.proposal == transaction.prewrite_package.proposal
    assert restored.quality_manifest["status"] == "passed"
    restored_preview = restored.prewrite_package.component_registry_preview
    assert restored_preview[0]["implementation_handoff"]["workstream_id"] == "B-001"
    assert restored.prewrite_package.accepted_project_preview["accepted_at"] == "prewrite"
    assert restored.prewrite_package.project_brief_record_text.startswith("# Supplier Risk Board Project Brief")
    restored_specs = restored.backlog_result["_candidate_idea_specs"]
    assert isinstance(restored_specs["B-001"], backlog_contract.IdeaSpec)
    assert restored_specs["B-001"].metadata["idea_id"] == "B-001"

    payload["quality_manifest"] = {**payload["quality_manifest"], "status": "failed"}
    with pytest.raises(ValueError, match="hash mismatch"):
        product_create_transaction_from_dict(payload)


def test_commit_product_create_transaction_is_commit_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _transaction()
    calls: list[dict[str, Any]] = []

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("commit must not run product interpretation, repair, or package compilation")

    class _RollbackGuard:
        def __init__(self, repo_root: Path) -> None:
            self.repo_root = repo_root
            self.committed = False

        def __enter__(self) -> "_RollbackGuard":
            return self

        def commit(self) -> None:
            self.committed = True

        def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
            assert self.committed
            return False

    def fake_write(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return {
            "mode": "applied",
            "validation_gate": kwargs["tribunal"],
            "backlog": [],
            "components": [],
            "diagrams": [],
        }

    monkeypatch.setattr(greenfield_proposals, "_build_repaired_prewrite_package", forbidden)
    monkeypatch.setattr(greenfield_proposals, "run_greenfield_post_confirm_engine", forbidden)
    monkeypatch.setattr(greenfield_proposals, "complete_confirmed_proposal", forbidden)
    monkeypatch.setattr(greenfield_proposals, "complete_greenfield_semantic_apply_payload", forbidden)
    monkeypatch.setattr(greenfield_proposals, "GreenfieldApplyTransaction", _RollbackGuard)
    monkeypatch.setattr(greenfield_proposals, "ensure_greenfield_create_baseline", lambda _root: None)
    monkeypatch.setattr(greenfield_apply_write, "write_greenfield_proposal", fake_write)

    result = greenfield_proposals.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction=transaction,
        confirm=True,
        started_at=0.0,
    )

    assert len(calls) == 1
    assert calls[0]["proposal"] == transaction.proposal
    assert calls[0]["prewrite_package"] == transaction.prewrite_package
    assert calls[0]["backlog_result"] == transaction.backlog_result
    assert calls[0]["tribunal"] == transaction.validation_gate
    assert result["product_create_transaction"]["transaction_hash"] == transaction.transaction_hash
    assert result["product_create_transaction"]["verified"] is True
    assert result["post_confirm_quality_manifest"]["write_transaction"]["status"] == "committed"
    assert result["post_confirm_quality_manifest"]["write_transaction"]["commit_only"] is True
    assert (
        result["post_confirm_quality_manifest"]["write_transaction"]["product_create_transaction_hash"]
        == transaction.transaction_hash
    )


def test_write_greenfield_proposal_uses_precompiled_program_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = _proposal()
    package = _package(proposal)
    backlog_result = dict(package.backlog_result or {})
    idea_path = tmp_path / "odylith/radar/source/ideas/B-001.md"
    backlog_result["idea_files"] = {str(idea_path): "Supplier risk review path\n"}
    backlog_result["backlog_index"] = str(tmp_path / "odylith/radar/source/INDEX.md")
    backlog_result["backlog_index_text"] = "| B-001 | Prove supplier risk review path |\n"
    package = replace(package, backlog_result=backlog_result)
    calls: dict[str, Any] = {}

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("post-confirm write must consume the compiled program plan")

    def fake_materialize(**kwargs: Any) -> dict[str, Any]:
        calls["materialize"] = kwargs
        return {
            "created": True,
            "umbrella_id": "B-001",
            "program_path": str(tmp_path / "odylith/radar/source/programs/B-001.execution-waves.v1.json"),
            "waves": list(package.program_result["waves"]),
            "program_count": 1,
        }

    monkeypatch.setattr(greenfield_programs, "create_greenfield_program", forbidden)
    monkeypatch.setattr(greenfield_programs, "first_release_workstream_ids", forbidden)
    monkeypatch.setattr(greenfield_programs, "materialize_compiled_greenfield_program", fake_materialize)
    monkeypatch.setattr(greenfield_apply_write.greenfield_traceability, "apply_backlog_traceability", lambda **_kwargs: [])
    monkeypatch.setattr(greenfield_apply_write.greenfield_experience, "build_component_handoffs", forbidden)
    monkeypatch.setattr(greenfield_apply_write.greenfield_experience, "build_next_steps", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "record_greenfield_acceptance", forbidden)
    monkeypatch.setattr(
        greenfield_apply_write,
        "record_compiled_greenfield_acceptance",
        lambda **_kwargs: {"event": {"ts_iso": "2026-07-07T00:00:00-07:00"}},
    )
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_component_spec_quality", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_final_next_steps_quality", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write, "_raise_for_final_package_quality", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.brand_assets, "ensure_brand_assets", lambda **_kwargs: [])
    monkeypatch.setattr(greenfield_apply_write, "_refresh_greenfield_dashboard", lambda **_kwargs: {"status": "passed"})
    monkeypatch.setattr(
        greenfield_apply_write,
        "_raise_for_greenfield_rendered_surface_custody",
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

    assert calls["materialize"]["program_result"] == package.program_result
    assert result["next_steps"] == package.next_steps_preview
    assert result["program"]["program_count"] == 1


def test_write_greenfield_proposal_rejects_incomplete_compiled_package_before_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = _proposal()
    package = replace(_package(proposal), next_steps_preview=None)

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("post-confirm write must not regenerate missing transaction artifacts")

    monkeypatch.setattr(greenfield_apply_write.greenfield_experience, "build_next_steps", forbidden)

    with pytest.raises(ValueError, match="missing compiled next_steps_preview"):
        greenfield_apply_write.write_greenfield_proposal(
            root=tmp_path,
            proposal=proposal,
            release_selector="",
            tribunal={"status": "passed", "issues": []},
            backlog_result=package.backlog_result or {},
            prewrite_package=package,
        )


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
