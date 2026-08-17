from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_create_transaction
from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store
from odylith.runtime.domain_intelligence import greenfield_repository_lock
from odylith.runtime.surfaces import claude_host_prompt_bundle
from odylith.runtime.surfaces import codex_host_prompt_context
from odylith.runtime.surfaces import greenfield_host_confirmation
from tests.unit.runtime.greenfield_proposal_fixtures import compiled_graph_transaction


def _transaction(*, repo_root: Path):
    return compiled_graph_transaction(repo_root)


def _stage_pending_transaction(repo_root: Path) -> tuple[Path, Path, str]:
    compiled = _transaction(repo_root=repo_root)
    transaction = greenfield_pending_transaction_store.stage_pending_transaction(
        repo_root=repo_root,
        transaction=compiled,
    )
    receipt = transaction.with_name(transaction.name + ".compiler-receipt.v1.json")
    return transaction, receipt, compiled.transaction_hash


def _committed_result() -> dict[str, object]:
    return {
        "product_create_transaction": {
            "repository_write_count": 17,
            "quality_status": "passed",
            "validation_status": "passed",
        }
    }


def _stub_navigation(monkeypatch: pytest.MonkeyPatch) -> None:
    def _navigation(root: Path, *, transaction_hash: str) -> dict[str, str]:
        dashboard = root / ".odylith/runtime/greenfield/generations" / transaction_hash / "repository/odylith/index.html"
        return {
            "project": "odylith/index.html?tab=project",
            "radar": "odylith/index.html?tab=radar",
            "registry": "odylith/index.html?tab=registry",
            "atlas": "odylith/index.html?tab=atlas",
            "compass": "odylith/index.html?tab=compass&date=live",
            "dashboard_path": str(dashboard),
            "project_url": f"{dashboard.as_uri()}?tab=project",
        }

    monkeypatch.setattr(
        greenfield_host_confirmation.greenfield_post_confirm_handoff,
        "post_confirm_navigation",
        _navigation,
    )


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_supported_hosts_commit_the_pending_hash_without_semantic_work(
    tmp_path: Path,
    monkeypatch,
    host: str,
) -> None:
    transaction, _receipt, transaction_hash = _stage_pending_transaction(tmp_path)
    calls: list[dict[str, object]] = []

    def _commit(**kwargs: object) -> dict[str, object]:
        calls.append(dict(kwargs))
        return _committed_result()

    monkeypatch.setattr(
        greenfield_host_confirmation.greenfield_create_commit,
        "commit_greenfield_create_transaction",
        _commit,
    )
    _stub_navigation(monkeypatch)
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
    assert "exact reviewed bytes" in str(decision["visible_markdown"])
    assert "Product Intent failure" not in str(decision)
    assert calls == [
        {
            "repo_root": tmp_path.resolve(),
            "transaction_file": transaction,
            "transaction_hash": transaction_hash,
            "confirm": True,
        }
    ]


def test_codex_and_claude_hooks_short_circuit_to_identical_confirmation_payload(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _transaction_path, _receipt, transaction_hash = _stage_pending_transaction(tmp_path)
    commits: list[dict[str, object]] = []
    monkeypatch.setattr(
        greenfield_host_confirmation.greenfield_create_commit,
        "commit_greenfield_create_transaction",
        lambda **kwargs: commits.append(dict(kwargs)) or _committed_result(),
    )
    _stub_navigation(monkeypatch)
    monkeypatch.setattr(
        greenfield_host_confirmation.greenfield_post_confirm_handoff,
        "open_committed_dashboard",
        lambda navigation: {"status": "unavailable", "reason": "test", "url": navigation["project_url"]},
    )
    monkeypatch.setattr(
        codex_host_prompt_context.host_prompt_route_locks,
        "route_lock_context",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("confirmation must precede Codex routing")),
    )
    monkeypatch.setattr(
        claude_host_prompt_bundle.host_prompt_route_locks,
        "route_lock_context",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("confirmation must precede Claude routing")),
    )

    command = f"CONFIRM {transaction_hash}"
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"prompt": command})))
    assert codex_host_prompt_context.main(["--repo-root", str(tmp_path)]) == 0
    codex_payload = json.loads(capsys.readouterr().out)

    assert claude_host_prompt_bundle.main(
        [
            "--repo-root",
            str(tmp_path),
            "--payload",
            json.dumps({"prompt": command}),
        ]
    ) == 0
    claude_payload = json.loads(capsys.readouterr().out)

    assert codex_payload == claude_payload
    assert codex_payload["systemMessage"].startswith("**Odylith Greenfield published**")
    assert len(commits) == 2
    assert commits[0] == commits[1]


def test_decision_callback_is_exact_and_proposal_only_for_unknown_hosts(tmp_path: Path) -> None:
    _transaction_path, _receipt, transaction_hash = _stage_pending_transaction(tmp_path)

    for prompt in (
        "confirm",
        "CONFIRM please",
        "EDIT correction",
        "REJECT now",
        f"CONFIRM {transaction_hash} unexpected",
        f"REJECT {transaction_hash} unexpected",
        f"CONFIRM {transaction_hash.upper()}",
    ):
        assert greenfield_host_confirmation.maybe_handle_greenfield_decision(
            repo_root=tmp_path,
            host_family="codex",
            prompt=prompt,
        ) is None
    for prompt in ("CONFIRM", "EDIT", "REJECT"):
        decision = greenfield_host_confirmation.maybe_handle_greenfield_decision(
            repo_root=tmp_path,
            host_family="codex",
            prompt=prompt,
        )
        assert decision is not None
        assert decision["status"] == "DECISION_HASH_REQUIRED"
    assert greenfield_host_confirmation.maybe_handle_greenfield_decision(
        repo_root=tmp_path,
        host_family="generic",
        prompt=f"CONFIRM {transaction_hash}",
    ) is None
    assert greenfield_host_confirmation.confirmation_supported("codex") is True
    assert greenfield_host_confirmation.confirmation_supported("claude") is True
    assert greenfield_host_confirmation.confirmation_supported("generic") is False


def test_edit_requests_new_evidence_without_mutating_staging(tmp_path: Path) -> None:
    transaction, receipt, transaction_hash = _stage_pending_transaction(tmp_path)

    decision = greenfield_host_confirmation.maybe_handle_greenfield_decision(
        repo_root=tmp_path,
        host_family="codex",
        prompt=f"EDIT {transaction_hash}",
    )

    assert decision is not None
    assert decision["status"] == "edit_evidence_required"
    assert "new evidence" in str(decision["visible_markdown"])
    assert transaction.is_file()
    assert receipt.is_file()


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_edit_returns_exact_resumable_semantic_authoring_request(
    tmp_path: Path,
    host: str,
) -> None:
    transaction, receipt, transaction_hash = _stage_pending_transaction(tmp_path)
    sealed = greenfield_create_transaction.load_compiled_product_create_transaction_file(transaction)
    original_evidence = dict(sealed.intent_authority["evidence_sources"])

    decision = greenfield_host_confirmation.maybe_handle_greenfield_decision(
        repo_root=tmp_path,
        host_family=host,
        prompt=f"EDIT {transaction_hash} The receipt must show the source card id.",
    )

    assert decision is not None
    assert decision["status"] == "edit_evidence_received"
    request = decision["authoring_request"]
    assert request["supersedes_transaction_hash"] == transaction_hash
    assert request["evidence_sources"]["operator_prompt"] == original_evidence[
        "operator_prompt"
    ]
    assert request["revision_evidence"] == {
        "prior_operator_edit": original_evidence["operator_edit"],
        "new_operator_correction": "The receipt must show the source card id.",
        "canonical_separator": "\n\n--- next operator correction ---\n\n",
    }
    hook = greenfield_host_confirmation.host_hook_payload(decision)
    assert "SemanticIntentAuthoringRequest:" in hook["hookSpecificOutput"][
        "additionalContext"
    ]
    assert transaction.is_file()
    assert receipt.is_file()


def test_reject_removes_only_terminal_staging(tmp_path: Path) -> None:
    transaction, receipt, transaction_hash = _stage_pending_transaction(tmp_path)

    decision = greenfield_host_confirmation.maybe_handle_greenfield_decision(
        repo_root=tmp_path,
        host_family="claude",
        prompt=f"REJECT {transaction_hash}",
    )

    assert decision is not None
    assert decision["status"] == "ABORTED"
    assert not transaction.exists()
    assert not receipt.exists()
    assert not (tmp_path / "odylith").exists()


def test_reject_preserves_staging_when_recovery_evidence_exists(tmp_path: Path) -> None:
    transaction, receipt, transaction_hash = _stage_pending_transaction(tmp_path)
    journal = tmp_path / ".odylith/runtime/greenfield/create-journal" / transaction_hash
    journal.mkdir(parents=True)

    decision = greenfield_host_confirmation.maybe_handle_greenfield_decision(
        repo_root=tmp_path,
        host_family="codex",
        prompt=f"REJECT {transaction_hash}",
    )

    assert decision is not None
    assert decision["status"] == "RECOVERY_REQUIRED"
    assert transaction.is_file()
    assert receipt.is_file()
    assert journal.is_dir()


def test_reject_does_not_claim_to_undo_a_closed_transaction(tmp_path: Path) -> None:
    transaction, receipt, transaction_hash = _stage_pending_transaction(tmp_path)
    journal = tmp_path / ".odylith/runtime/greenfield/create-journal" / transaction_hash
    journal.mkdir(parents=True)
    (journal / "state.v1.json").write_text(
        json.dumps({"state": "closed", "lifecycle_state": "CLOSED"}),
        encoding="utf-8",
    )

    decision = greenfield_host_confirmation.maybe_handle_greenfield_decision(
        repo_root=tmp_path,
        host_family="codex",
        prompt=f"REJECT {transaction_hash}",
    )

    assert decision is not None
    assert decision["status"] == "CLOSED"
    assert "cannot undo" in str(decision["visible_markdown"])
    assert transaction.is_file()
    assert receipt.is_file()


def test_busy_confirmation_reports_no_write_without_regeneration(tmp_path: Path, monkeypatch) -> None:
    _transaction_path, _receipt, transaction_hash = _stage_pending_transaction(tmp_path)

    def _busy(**_kwargs: object) -> dict[str, object]:
        raise greenfield_create_commit.GreenfieldCreateCommitError(
            "busy",
            rollback_status="not_started",
            failure_kind="post_confirm_repository_busy",
        )

    monkeypatch.setattr(
        greenfield_host_confirmation.greenfield_create_commit,
        "commit_greenfield_create_transaction",
        _busy,
    )

    decision = greenfield_host_confirmation.maybe_handle_greenfield_decision(
        repo_root=tmp_path,
        host_family="claude",
        prompt=f"CONFIRM {transaction_hash}",
    )

    assert decision is not None
    assert decision["status"] == "BUSY_NO_WRITE"
    assert "No bytes" in str(decision["visible_markdown"])
    assert "regenerate" in str(decision["developer_context"])


def test_busy_reject_preserves_the_exact_pending_package(tmp_path: Path) -> None:
    transaction, receipt, transaction_hash = _stage_pending_transaction(tmp_path)

    with greenfield_repository_lock.greenfield_repository_lock(tmp_path):
        decision = greenfield_host_confirmation.maybe_handle_greenfield_decision(
            repo_root=tmp_path,
            host_family="claude",
            prompt=f"REJECT {transaction_hash}",
        )

    assert decision is not None
    assert decision["status"] == "BUSY_NO_WRITE"
    assert transaction.is_file()
    assert receipt.is_file()


def test_hash_bound_confirm_cannot_be_retargeted_by_a_newer_pending_proposal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    first_path, _first_receipt, first_hash = _stage_pending_transaction(tmp_path)
    existing = tmp_path / "odylith/radar/source/operator-change.md"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("different preconfirm evidence\n", encoding="utf-8")
    second_path, _second_receipt, second_hash = _stage_pending_transaction(tmp_path)
    assert first_hash != second_hash
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        greenfield_host_confirmation.greenfield_create_commit,
        "commit_greenfield_create_transaction",
        lambda **kwargs: calls.append(dict(kwargs)) or _committed_result(),
    )
    _stub_navigation(monkeypatch)
    monkeypatch.setattr(
        greenfield_host_confirmation.greenfield_post_confirm_handoff,
        "open_committed_dashboard",
        lambda _navigation: {"status": "unavailable", "reason": "test", "url": ""},
    )

    decision = greenfield_host_confirmation.maybe_handle_greenfield_decision(
        repo_root=tmp_path,
        host_family="codex",
        prompt=f"CONFIRM {first_hash}",
    )

    assert decision is not None
    assert decision["transaction_hash"] == first_hash
    assert calls[0]["transaction_file"] == first_path
    assert calls[0]["transaction_file"] != second_path
    assert calls[0]["transaction_hash"] == first_hash
