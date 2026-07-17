from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_compiled_write
from odylith.runtime.domain_intelligence import greenfield_create_baseline
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import PRECONFIRM_ENGINE_VERSION
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import PRECONFIRM_QUALITY_MANIFEST_VERSION
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.surfaces import brand_assets
from tests.unit.runtime.greenfield_proposal_fixtures import CONFIRMED_INTENT_TEXT
from tests.unit.runtime.greenfield_proposal_fixtures import compiled_greenfield_package_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_intent_with_authority


def _approved_quality_manifest() -> dict[str, Any]:
    return {
        "version": PRECONFIRM_QUALITY_MANIFEST_VERSION,
        "engine": PRECONFIRM_ENGINE_VERSION,
        "status": "passed",
        "validation_status": "passed",
        "hard_blocker": False,
        "issue_count": 0,
        "write_transaction": {
            "status": "not_started",
            "rollback_guard": "enabled",
            "prewrite_clean_before_commit": True,
        },
    }


def _compiled_transaction(repo_root: Path) -> Any:
    intent = confirmed_intent_with_authority(
        CONFIRMED_INTENT_TEXT,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
        repo_root=repo_root,
        write_files=True,
    )
    authority = dict(intent[PRODUCT_INTENT_AUTHORITY_KEY])
    proposal = {
        "intent": {"title": "Municipal Permit Review Workspace"},
        PRODUCT_INTENT_AUTHORITY_KEY: authority,
        "backlog": [{"title": "Prove permit review path"}],
        "components": [],
        "diagrams": [],
    }
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
        quality_manifest=_approved_quality_manifest(),
        repo_root=repo_root,
    )


@pytest.mark.parametrize(
    "damage",
    ("missing_sidecar", "invalid_sidecar", "source_drift"),
)
def test_greenfield_create_cli_uses_transaction_authority_not_mutable_intent_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    damage: str,
) -> None:
    transaction = _compiled_transaction(tmp_path)
    transaction_path = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    greenfield_proposals.write_product_create_transaction_file(transaction_path, transaction)
    markdown_path = tmp_path / ".odylith/runtime/greenfield/confirmed-intent.md"
    sidecar_path = markdown_path.with_suffix(".json")
    if damage == "missing_sidecar":
        sidecar_path.unlink()
    elif damage == "invalid_sidecar":
        sidecar_path.write_text("{not-json", encoding="utf-8")
    elif damage == "source_drift":
        markdown_path.write_text(CONFIRMED_INTENT_TEXT + "\n## Product story\nDrifted after compile.\n", encoding="utf-8")

    calls: list[str] = []

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        calls.append("forbidden")
        raise AssertionError("create must not build, compile, repair, or apply proposal artifacts")

    def fake_compiled_write(**_kwargs: Any) -> dict[str, Any]:
        calls.append("compiled_write")
        return greenfield_compiled_write.compiled_greenfield_commit_result(transaction=transaction)

    monkeypatch.setattr(greenfield_proposals, "build_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_proposals, "compile_greenfield_create_transaction", forbidden)
    monkeypatch.setattr(greenfield_proposals, "apply_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", fake_compiled_write)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            ".odylith/runtime/greenfield/product-create-transaction.v1.json",
            "--transaction-hash",
            transaction.transaction_hash,
            "--confirm",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["product_create_transaction"]["transaction_hash"] == transaction.transaction_hash
    assert payload["commit_manifest"]["write_transaction"]["commit_only"] is True
    assert "commit_failure" not in payload
    assert calls == ["compiled_write"]
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))
