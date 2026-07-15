from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_surface_refresh_proof
from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_from_dict
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_to_dict
from tests.unit.runtime.greenfield_proposal_fixtures import CONFIRMED_INTENT_TEXT
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_intent_with_authority
from tests.unit.runtime.greenfield_proposal_fixtures import surface_refresh_preview_fixture
from odylith.runtime.surfaces import brand_assets


_PROMPT = "Draft a greenfield proposal for a municipal permit review workspace"


def _disable_refreshes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "passed", "test_refresh_stub": True},
    )
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
        greenfield_surface_refresh_proof,
        "build_prewrite_surface_refresh_preview",
        lambda **_kwargs: surface_refresh_preview_fixture(),
    )


def _proposal(repo_root: Path) -> dict[str, object]:
    return greenfield_proposals.build_greenfield_proposal(
        repo_root=repo_root,
        prompt=_PROMPT,
        release_selector="0.0.1",
        confirmed_intent=confirmed_intent_with_authority(
            CONFIRMED_INTENT_TEXT,
            prompt=_PROMPT,
            repo_root=repo_root,
            write_files=True,
        ),
    )


def _compiled_transaction(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    _disable_refreshes(monkeypatch)
    return greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=repo_root,
        proposal=_proposal(repo_root),
        release_selector="0.0.1",
    )


def test_compile_greenfield_create_transaction_precompiles_missing_brand_asset_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _compiled_transaction(tmp_path, monkeypatch)

    writes = transaction.prewrite_package.brand_asset_writes or {}
    assert "odylith/surfaces/brand/manifest.json" in writes
    assert "odylith/surfaces/brand/icon/odylith-icon.svg" in writes
    assert not (tmp_path / "odylith/surfaces/brand/manifest.json").exists()


def test_brand_asset_writes_round_trip_and_bind_transaction_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _compiled_transaction(tmp_path, monkeypatch)
    payload = product_create_transaction_to_dict(transaction)

    restored = product_create_transaction_from_dict(payload)

    assert restored.prewrite_package.brand_asset_writes == transaction.prewrite_package.brand_asset_writes

    tampered = dict(payload)
    tampered_package = dict(tampered["prewrite_package"])
    tampered_writes = dict(tampered_package["brand_asset_writes"])
    tampered_manifest = dict(tampered_writes["odylith/surfaces/brand/manifest.json"])
    tampered_manifest["sha256"] = "0" * 64
    tampered_writes["odylith/surfaces/brand/manifest.json"] = tampered_manifest
    tampered_package["brand_asset_writes"] = tampered_writes
    tampered["prewrite_package"] = tampered_package

    with pytest.raises(ValueError, match="hash mismatch"):
        product_create_transaction_from_dict(tampered)


def test_commit_product_create_transaction_uses_write_set_when_legacy_brand_field_is_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _compiled_transaction(tmp_path, monkeypatch)
    package = replace(base.prewrite_package, brand_asset_writes={})
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

    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction=transaction,
        confirm=True,
        started_at=0.0,
    )

    assert result["repository_write_set"]["status"] == "passed"
    assert (tmp_path / "odylith/surfaces/brand/manifest.json").is_file()


def test_commit_product_create_transaction_does_not_seed_brand_assets_after_confirm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _compiled_transaction(tmp_path, monkeypatch)

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("commit must not call dynamic brand asset seeding")

    monkeypatch.setattr(brand_assets, "ensure_brand_assets", forbidden)
    monkeypatch.setattr(brand_assets, "materialize_precompiled_brand_assets", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "_refresh_greenfield_dashboard", lambda **_kwargs: {"status": "passed"})
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "skipped"},
    )

    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction=transaction,
        confirm=True,
        started_at=0.0,
    )

    assert result["commit_manifest"]["write_transaction"]["commit_only"] is True
    assert (tmp_path / "odylith/surfaces/brand/manifest.json").is_file()
    assert (tmp_path / "odylith/surfaces/brand/icon/odylith-icon.svg").is_file()
