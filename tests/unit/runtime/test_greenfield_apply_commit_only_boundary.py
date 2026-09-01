from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_backlog_commit
from odylith.runtime.domain_intelligence import greenfield_compiled_package_contract
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_prewrite_surface_stage
from odylith.runtime.domain_intelligence import greenfield_model_intent_materialization
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_proposals_cli
from odylith.runtime.domain_intelligence import greenfield_release_commit
from odylith.runtime.domain_intelligence import greenfield_surface_refresh_proof
from odylith.runtime.domain_intelligence import greenfield_traceability_commit
from odylith.runtime.domain_intelligence import proposal_memory
from tests.unit.runtime.greenfield_proposal_fixtures import _canonical_model_authored_greenfield_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import surface_refresh_preview_fixture


def test_apply_confirm_is_disabled_before_compile_commit_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    compile_calls: list[dict[str, Any]] = []

    def forbidden_compile(**kwargs: Any) -> None:
        compile_calls.append(dict(kwargs))
        raise AssertionError("legacy apply must not compile after confirmation")

    monkeypatch.setattr(greenfield_proposals, "compile_greenfield_create_transaction", forbidden_compile)

    rc = greenfield_proposals_cli.main(
        ["apply", "--repo-root", str(tmp_path), "--confirm"]
    )

    assert rc == 2
    assert "greenfield apply is disabled" in capsys.readouterr().out
    assert compile_calls == []


def test_create_confirm_cli_commits_transaction_without_post_confirm_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_empty_governance_repo(tmp_path)

    def render_stubbed_surfaces(*, repo_root: Path) -> dict[str, Any]:
        for relative_path in greenfield_surface_refresh_proof.GREENFIELD_REQUIRED_SURFACE_ARTIFACTS:
            path = Path(repo_root) / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.is_file():
                path.write_text("stubbed pre-confirm surface\n", encoding="utf-8")
        return surface_refresh_preview_fixture()

    monkeypatch.setattr(
        greenfield_surface_refresh_proof,
        "build_prewrite_surface_refresh_preview",
        render_stubbed_surfaces,
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "passed", "atlas_surface_count": 3, "atlas_diagram_count": 2},
    )
    proposal = _canonical_model_authored_greenfield_fixture(tmp_path)
    authoring_receipt = proposal.pop("_test_model_authoring_receipt")
    assert isinstance(authoring_receipt, dict)
    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        proposal_ready=True,
        preconfirm_elapsed_seconds=float(authoring_receipt.get("elapsed_seconds") or 0.0),
        model_authoring_tier=str(authoring_receipt.get("tier") or ""),
        model_authoring_receipt=authoring_receipt,
    )
    write_set = transaction.prewrite_package.repository_write_set or {}
    write_paths = {
        str(row.get("path", ""))
        for row in write_set.get("writes", ())
        if isinstance(row, dict)
    }
    assert {
        "odylith/radar/source/releases/release-assignment-events.v1.jsonl",
        "odylith/runtime/source/accepted-project.v1.json",
        "odylith/runtime/source/project-brief.v1.md",
        "odylith/registry/source/component_registry.v1.json",
        "odylith/atlas/source/catalog/diagrams.v1.json",
        "odylith/index.html",
    }.issubset(write_paths)
    transaction_file = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    greenfield_proposals.write_product_create_transaction_file(transaction_file, transaction)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("commit-only create must not compile, repair, clean, or rebuild package projections")

    monkeypatch.setattr(greenfield_proposals, "compile_greenfield_create_transaction", forbidden)
    monkeypatch.setattr(greenfield_proposals, "_build_authored_prewrite_package", forbidden)
    monkeypatch.setattr(
        greenfield_model_intent_materialization,
        "materialize_model_authored_intent",
        forbidden,
    )
    monkeypatch.setattr(greenfield_apply_prewrite, "build_prewrite_completion_package", forbidden)
    monkeypatch.setattr(greenfield_prewrite_surface_stage, "build_staged_surface_refresh_preview", forbidden)
    monkeypatch.setattr(greenfield_prewrite_surface_stage, "materialize_staged_greenfield_surfaces", forbidden)
    monkeypatch.setattr(greenfield_apply_prewrite, "remove_prewrite_stale_idea_files", forbidden)
    monkeypatch.setattr(greenfield_apply_prewrite, "remove_stale_workstream_artifacts", forbidden)
    monkeypatch.setattr(greenfield_compiled_package_contract, "require_complete_compiled_greenfield_package", forbidden)
    monkeypatch.setattr(greenfield_backlog_commit, "write_backlog_files", forbidden)
    monkeypatch.setattr(greenfield_release_commit, "materialize_compiled_release_target", forbidden)
    monkeypatch.setattr(greenfield_release_commit, "materialize_compiled_release_assignment", forbidden)
    monkeypatch.setattr(greenfield_traceability_commit, "rebase_compiled_traceability_plan", forbidden)
    monkeypatch.setattr(proposal_memory, "record_compiled_greenfield_acceptance", forbidden)
    monkeypatch.setattr(
        greenfield_component_commit.component_authoring.owned_surface_refresh,
        "raise_for_failed_refresh",
        forbidden,
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        forbidden,
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        forbidden,
    )
    monkeypatch.setattr(greenfield_component_commit, "materialize_compiled_component_from_preview", forbidden)
    monkeypatch.setattr(greenfield_apply_diagrams, "materialize_apply_diagrams", forbidden)

    rc = greenfield_proposals_cli.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            str(transaction_file),
            "--transaction-hash",
            transaction.transaction_hash,
            "--confirm",
            "--json",
        ]
    )
    output = capsys.readouterr().out

    assert rc == 0, output
    payload = json.loads(output)
    assert payload["commit_manifest"]["write_transaction"]["commit_only"] is True
    assert payload["repository_write_set"]["status"] == "passed"
    assert payload["product_create_transaction"]["transaction_hash"] == transaction.transaction_hash


def test_commit_executor_has_no_preconfirm_compiler_or_rescue_imports() -> None:
    tree = ast.parse(inspect.getsource(greenfield_create_commit))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )

    assert not {
        "odylith.runtime.domain_intelligence.greenfield_apply_write",
        "odylith.runtime.domain_intelligence.greenfield_preconfirm_engine",
        "odylith.runtime.domain_intelligence.greenfield_preconfirm_rescue_planner",
        "odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority",
    }.intersection(imported_modules)
