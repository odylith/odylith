from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import require_product_create_transaction_verified
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage


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
        backlog_result={
            "created": [{"title": "Prove supplier risk review path", "idea_id": "B-001"}],
            "idea_files": {"/repo/odylith/radar/source/ideas/B-001.md": "Supplier risk review path"},
            "backlog_index": "/repo/odylith/radar/source/INDEX.md",
            "backlog_index_text": "| B-001 | Prove supplier risk review path |",
            "_candidate_idea_specs": {},
        },
        prewrite_safety_preview={"status": "passed"},
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
    assert result["post_confirm_quality_manifest"]["write_transaction"]["commit_only"] is True
    assert (
        result["post_confirm_quality_manifest"]["write_transaction"]["product_create_transaction_hash"]
        == transaction.transaction_hash
    )
