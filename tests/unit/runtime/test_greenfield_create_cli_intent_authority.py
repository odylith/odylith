from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_compiled_write
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_to_dict
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import POST_CONFIRM_ENGINE_VERSION
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import POST_CONFIRM_QUALITY_MANIFEST_VERSION
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from tests.unit.runtime.greenfield_proposal_fixtures import CONFIRMED_INTENT_TEXT
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_intent_with_authority


def _approved_quality_manifest() -> dict[str, Any]:
    return {
        "version": POST_CONFIRM_QUALITY_MANIFEST_VERSION,
        "engine": POST_CONFIRM_ENGINE_VERSION,
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
    package = GreenfieldCompletionPackage(
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result={
            "created": [{"title": "Prove permit review path", "idea_id": "B-001"}],
            "idea_files": {},
            "backlog_index": str(repo_root / "odylith/radar/source/INDEX.md"),
            "backlog_index_text": "",
            "_candidate_idea_specs": {},
        },
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
    ("damage", "expected_error"),
    (
        ("missing_sidecar", "structured sidecar is not readable"),
        ("invalid_sidecar", "structured sidecar is invalid"),
        ("source_drift", "source hash changed"),
    ),
)
def test_greenfield_create_cli_rejects_intent_authority_drift_before_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    damage: str,
    expected_error: str,
) -> None:
    transaction = _compiled_transaction(tmp_path)
    transaction_path = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    transaction_path.parent.mkdir(parents=True, exist_ok=True)
    transaction_path.write_text(
        json.dumps(product_create_transaction_to_dict(transaction), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
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
        raise AssertionError("authority drift must fail before build, compile, repair, transaction, or write")

    class ForbiddenTransaction:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            forbidden()

    monkeypatch.setattr(greenfield_proposals, "build_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_proposals, "compile_greenfield_create_transaction", forbidden)
    monkeypatch.setattr(greenfield_proposals, "apply_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_create_commit, "ensure_greenfield_create_baseline", forbidden)
    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", ForbiddenTransaction)
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", forbidden)

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
    assert rc == 2
    assert expected_error in payload["error"]
    assert "commit_failure" not in payload
    assert calls == []
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))
