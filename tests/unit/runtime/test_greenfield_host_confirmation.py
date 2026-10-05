"""Post-confirm host routing stays commit-only after canonical candidate sealing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store
from odylith.runtime.surfaces import greenfield_host_confirmation
from tests.unit.runtime.test_greenfield_create_transaction import _transaction


def _stage_pending_transaction(repo_root: Path) -> tuple[Path, Path, str]:
    compiled = _transaction(repo_root=repo_root)
    transaction = greenfield_pending_transaction_store.stage_pending_transaction(
        repo_root=repo_root,
        transaction=compiled,
    )
    receipt = transaction.with_name(transaction.name + ".compiler-receipt.v1.json")
    return transaction, receipt, compiled.transaction_hash


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_supported_hosts_confirm_exact_sealed_transaction_without_semantic_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    host: str,
) -> None:
    transaction, _receipt, transaction_hash = _stage_pending_transaction(tmp_path)
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        greenfield_host_confirmation.greenfield_create_commit,
        "commit_greenfield_create_transaction",
        lambda **kwargs: calls.append(dict(kwargs))
        or {
            "product_create_transaction": {
                "repository_write_count": 1,
                "quality_status": "passed",
                "validation_status": "passed",
            }
        },
    )
    monkeypatch.setattr(
        greenfield_host_confirmation.greenfield_post_confirm_handoff,
        "post_confirm_navigation",
        lambda *_args, **_kwargs: {
            "dashboard_path": "/tmp/odylith/index.html",
            "project_url": "file:///tmp/odylith/index.html?tab=project",
        },
    )
    monkeypatch.setattr(
        greenfield_host_confirmation.greenfield_post_confirm_handoff,
        "open_committed_dashboard",
        lambda _navigation: {"status": "unavailable", "reason": "test", "url": ""},
    )

    decision = greenfield_host_confirmation.maybe_handle_greenfield_decision(
        repo_root=tmp_path,
        host_family=host,
        prompt=f"CONFIRM {transaction_hash}",
    )

    assert decision is not None
    assert decision["status"] == "CLOSED"
    assert decision["transaction_hash"] == transaction_hash
    assert calls == [
        {
            "repo_root": tmp_path.resolve(),
            "transaction_file": transaction,
            "transaction_hash": transaction_hash,
            "confirm": True, "completion_receipt": None,
        }
    ]


def test_confirm_reports_closed_after_navigation_failure_and_same_hash_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _transaction_path, _receipt, transaction_hash = _stage_pending_transaction(tmp_path)
    handoff = greenfield_host_confirmation.greenfield_post_confirm_handoff
    original_navigation = handoff.post_confirm_navigation
    monkeypatch.setenv("ODYLITH_NO_BROWSER", "1")

    def failed_navigation(*_args: object, **_kwargs: object) -> dict[str, str]:
        raise RuntimeError("injected dashboard pin failure")

    monkeypatch.setattr(handoff, "post_confirm_navigation", failed_navigation)
    first = greenfield_host_confirmation.handle_greenfield_decision(
        repo_root=tmp_path,
        command="CONFIRM",
        transaction_hash=transaction_hash,
    )

    dashboard = tmp_path / "odylith" / "index.html"
    assert first["status"] == "CLOSED"
    assert "was committed from the exact reviewed bytes and passed readback" in first["visible_markdown"]
    assert "automatic reviewed-generation navigation is unavailable" in first["visible_markdown"]
    assert str(dashboard) in first["visible_markdown"]
    assert dashboard.is_file()
    journal = tmp_path / ".odylith/runtime/greenfield/create-journal" / transaction_hash / "state.v1.json"
    assert json.loads(journal.read_text(encoding="utf-8"))["state"] == "closed"

    monkeypatch.setattr(handoff, "post_confirm_navigation", original_navigation)
    second = greenfield_host_confirmation.handle_greenfield_decision(
        repo_root=tmp_path,
        command="CONFIRM",
        transaction_hash=transaction_hash,
    )
    assert second["status"] == "CLOSED"
    assert "Opened the committed" not in second["visible_markdown"]
    assert "reviewed-generation navigation is unavailable" not in second["visible_markdown"]
    assert dashboard.is_file()


def test_confirm_keeps_committed_receipt_when_browser_open_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _transaction_path, _receipt, transaction_hash = _stage_pending_transaction(tmp_path)
    handoff = greenfield_host_confirmation.greenfield_post_confirm_handoff

    def browser_failed(_navigation: object) -> dict[str, str]:
        raise RuntimeError("injected browser open failure")

    monkeypatch.setattr(handoff, "open_committed_dashboard", browser_failed)
    decision = greenfield_host_confirmation.handle_greenfield_decision(
        repo_root=tmp_path,
        command="CONFIRM",
        transaction_hash=transaction_hash,
    )

    assert decision["status"] == "CLOSED"
    assert "was committed from the exact reviewed bytes and passed readback" in decision["visible_markdown"]
    assert "The package is committed. Open the" in decision["visible_markdown"]
    assert "odylith/index.html" in decision["visible_markdown"]
