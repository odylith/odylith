from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_create_baseline
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_surface_refresh_proof
from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from tests.unit.runtime.greenfield_proposal_fixtures import canonical_model_authored_intent_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import _canonical_model_authored_greenfield_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import seal_compiled_greenfield_transaction
from tests.unit.runtime.greenfield_proposal_fixtures import surface_refresh_preview_fixture


_PROMPT = "Draft a greenfield proposal for a municipal permit review workspace"


def _disable_refreshes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "passed", "test_refresh_stub": True},
    )
    monkeypatch.setattr(
        greenfield_component_commit.component_compiled_commit.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_surface_refresh_proof,
        "build_prewrite_surface_refresh_preview",
        lambda **_kwargs: surface_refresh_preview_fixture(),
    )


def _proposal(repo_root: Path) -> dict[str, object]:
    return _canonical_model_authored_greenfield_fixture(repo_root)


def _compiled_transaction(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    _disable_refreshes(monkeypatch)
    proposal = _proposal(repo_root)
    authoring_receipt = dict(proposal.pop("_test_model_authoring_receipt"))
    return greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=repo_root,
        proposal=proposal,
        release_selector="0.0.1",
        proposal_ready=True,
        preconfirm_elapsed_seconds=float(authoring_receipt["elapsed_seconds"]),
        model_authoring_tier=str(authoring_receipt["tier"]),
        model_authoring_receipt=authoring_receipt,
    )


def test_compile_greenfield_create_transaction_precompiles_missing_baseline_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _compiled_transaction(tmp_path, monkeypatch)

    baseline = transaction.prewrite_package.baseline_writes or {}
    assert "odylith/radar/source/INDEX.md" in baseline
    assert "odylith/technical-plans/INDEX.md" in baseline
    assert "odylith/atlas/source/catalog/diagrams.v1.json" in baseline
    assert not (tmp_path / "odylith/radar/source/INDEX.md").exists()


def test_commit_product_create_transaction_uses_write_set_when_legacy_baseline_field_is_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _compiled_transaction(tmp_path, monkeypatch)
    package = replace(base.prewrite_package, baseline_writes={})
    transaction = build_product_create_transaction(
        proposal=base.proposal,
        release_selector=base.release_selector,
        validation_gate=base.validation_gate,
        prewrite_package=package,
        backlog_result=base.backlog_result,
        intent_authority=base.intent_authority,
        quality_manifest=base.quality_manifest,
        repo_root=tmp_path,
    )
    transaction = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)

    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=transaction.transaction_file,
        transaction_hash=transaction.transaction_hash,
        confirm=True,
        started_at=0.0,
    )

    assert result["repository_write_set"]["status"] == "passed"
    assert (tmp_path / "odylith/radar/source/INDEX.md").is_file()


def test_materialize_precompiled_baseline_rejects_non_text_payload(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="not text"):
        greenfield_create_baseline.materialize_precompiled_greenfield_create_baseline(
            root=tmp_path,
            baseline_writes={
                "odylith/radar/source/INDEX.md": object(),
                "odylith/technical-plans/INDEX.md": "# Plans\n",
                "odylith/atlas/source/catalog/diagrams.v1.json": "{}\n",
            },
        )
