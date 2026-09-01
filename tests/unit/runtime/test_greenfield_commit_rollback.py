from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_compiled_write
from odylith.runtime.domain_intelligence import greenfield_create_baseline
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import PRECONFIRM_ENGINE_VERSION
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import PRECONFIRM_QUALITY_MANIFEST_VERSION
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.surfaces import brand_assets
from tests.unit.runtime.greenfield_proposal_fixtures import compiled_greenfield_package_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import canonical_model_authored_intent_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import _canonical_model_authored_greenfield_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import approved_authored_quality_manifest_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import seal_compiled_greenfield_transaction


def _quality_manifest() -> dict[str, Any]:
    return approved_authored_quality_manifest_fixture()


def _transaction(repo_root: Path) -> Any:
    proposal = _canonical_model_authored_greenfield_fixture(repo_root)
    authority = dict(proposal[PRODUCT_INTENT_AUTHORITY_KEY])
    package = compiled_greenfield_package_fixture(
        proposal=proposal,
        repo_root=repo_root,
        baseline_writes=greenfield_create_baseline.precompiled_greenfield_create_baseline_writes(repo_root),
        brand_asset_writes=brand_assets.precompiled_brand_asset_writes(repo_root=repo_root),
    )
    return build_product_create_transaction(
        proposal=proposal,
        release_selector="0.0.1",
        validation_gate={"status": "passed", "issues": []},
        prewrite_package=package,
        backlog_result=package.backlog_result or {},
        intent_authority=authority,
        quality_manifest=_quality_manifest(),
        repo_root=repo_root,
    )


def test_commit_product_create_transaction_rolls_back_when_compiled_write_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _transaction(tmp_path)
    transaction = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)

    def fail_after_precompiled_writes(**_kwargs: Any) -> dict[str, Any]:
        raise OSError("simulated compiled write failure")

    monkeypatch.setattr(
        greenfield_compiled_write,
        "write_compiled_greenfield_package",
        fail_after_precompiled_writes,
    )

    with pytest.raises(greenfield_create_commit.GreenfieldCreateCommitError) as exc:
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction.transaction_file,
            transaction_hash=transaction.transaction_hash,
            confirm=True,
            started_at=0.0,
        )

    assert exc.value.rollback_status == "rolled_back"
    assert not (tmp_path / "odylith/radar/source/INDEX.md").exists()
    assert not (tmp_path / "odylith/technical-plans/INDEX.md").exists()
    assert not (tmp_path / "odylith/surfaces/brand/manifest.json").exists()
