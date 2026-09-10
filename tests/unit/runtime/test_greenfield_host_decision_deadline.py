"""Decision callbacks must return before the host can fail open on timeout."""

from __future__ import annotations

import io
import json
import signal
import threading
import time
from pathlib import Path

import pytest

from odylith.runtime.surfaces import greenfield_host_confirmation as confirmation
from odylith.runtime.surfaces import claude_host_prompt_bundle
from odylith.runtime.surfaces import codex_host_prompt_context
from odylith.runtime.domain_intelligence import greenfield_generation_state
from tests.unit.runtime.test_greenfield_host_confirmation import _stage_pending_transaction


@pytest.mark.parametrize("host", ["codex", "claude"])
@pytest.mark.parametrize("command", ["CONFIRM", "REJECT", "EDIT"])
def test_pending_resolution_deadline_returns_blocked_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, host: str, command: str,
) -> None:
    transaction_hash = "a" * 64
    monkeypatch.setattr(confirmation, "_DECISION_BUDGET_SECONDS", 0.02, raising=False)

    def delayed_resolution(**kwargs: object) -> Path:
        time.sleep(0.10)
        return tmp_path / "transaction.json"

    def forbidden_mutation(**kwargs: object) -> None:
        pytest.fail("timed-out resolution reached mutation")

    monkeypatch.setattr(
        confirmation.greenfield_pending_transaction_store,
        "resolve_pending_transaction", delayed_resolution,
    )
    monkeypatch.setattr(confirmation, "_confirm_pending_transaction", forbidden_mutation)
    monkeypatch.setattr(confirmation, "_reject_pending_transaction", forbidden_mutation)
    decision = confirmation.maybe_handle_greenfield_decision(
        repo_root=tmp_path, host_family=host, prompt=f"{command} {transaction_hash}",
    )
    assert decision is not None
    assert decision["status"] == "RECOVERY_REQUIRED"
    assert decision["transaction_hash"] == transaction_hash
    payload = confirmation.host_hook_payload(decision)
    assert payload["decision"] == "block"
    assert transaction_hash in payload["reason"]
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("host", ["", "generic", "future-host"])
@pytest.mark.parametrize("command", ["CONFIRM", "EDIT", "REJECT"])
def test_unregistered_host_exact_decision_is_read_only_before_any_repo_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, host: str, command: str,
) -> None:
    transaction_hash = "b" * 64

    def forbidden_access(*args: object, **kwargs: object) -> None:
        pytest.fail("unregistered host reached repository or transaction access")

    monkeypatch.setattr(confirmation, "Path", forbidden_access)
    monkeypatch.setattr(confirmation, "_has_pending_transactions", forbidden_access)
    monkeypatch.setattr(
        confirmation.greenfield_pending_transaction_store,
        "resolve_pending_transaction", forbidden_access,
    )
    decision = confirmation.maybe_handle_greenfield_decision(
        repo_root=tmp_path, host_family=host, prompt=f"{command} {transaction_hash}",
    )
    assert decision is not None
    assert decision["status"] == "HOST_CONFIRMATION_UNAVAILABLE"
    assert decision["transaction_hash"] == transaction_hash
    payload = confirmation.host_hook_payload(decision)
    assert payload["decision"] == "block"
    assert transaction_hash in payload["reason"]
    assert "read-only" in payload["reason"]


@pytest.mark.parametrize("host", ["codex", "claude"])
@pytest.mark.parametrize("phase", ["before_publication", "publication_boundary", "after_publication", "browser_open"])
def test_real_commit_deadline_preserves_publication_and_same_hash_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, host: str, phase: str,
) -> None:
    # This seals a mechanical write-set fixture; it is not authored-package quality proof.
    transaction_path, receipt_path, transaction_hash = _stage_pending_transaction(tmp_path)
    sealed_bytes = transaction_path.read_bytes(), receipt_path.read_bytes()
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in (tmp_path / "odylith").rglob("*") if path.is_file()
    }
    publication_before = greenfield_generation_state.read_active_publication(tmp_path)
    kernel = confirmation.greenfield_create_commit
    owner, attribute = {
        "before_publication": (kernel.greenfield_compiled_write, "write_compiled_greenfield_package"),
        "publication_boundary": (kernel.greenfield_generation_store, "publish_greenfield_generation"),
        "after_publication": (kernel.GreenfieldCommitJournal, "mark_published"),
        "browser_open": (confirmation.greenfield_post_confirm_handoff, "open_committed_dashboard"),
    }[phase]
    original = getattr(owner, attribute)
    reached: list[str] = []

    def delayed(*args: object, **kwargs: object) -> None:
        reached.append(phase)
        if phase in {"publication_boundary", "after_publication"}:
            original(*args, **kwargs)
        time.sleep(2.0)
        pytest.fail("the real deadline did not interrupt the selected commit phase")

    monkeypatch.setenv("ODYLITH_NO_BROWSER", "1")
    monkeypatch.setattr(confirmation, "_DECISION_BUDGET_SECONDS", 1.0)
    monkeypatch.setattr(owner, attribute, delayed)
    decision = confirmation.maybe_handle_greenfield_decision(
        repo_root=tmp_path, host_family=host, prompt=f"CONFIRM {transaction_hash}",
    )
    assert reached == [phase]
    assert decision is not None
    assert decision["status"] == ("CLOSED" if phase == "browser_open" else "RECOVERY_REQUIRED")
    assert decision["transaction_hash"] == transaction_hash
    payload = confirmation.host_hook_payload(decision)
    assert payload["decision"] == "block"
    assert transaction_hash in payload["reason"]
    assert (transaction_path.read_bytes(), receipt_path.read_bytes()) == sealed_bytes
    state_path = tmp_path / ".odylith/runtime/greenfield/create-journal" / transaction_hash / "state.v1.json"
    state = json.loads(state_path.read_text())
    publication_after = greenfield_generation_state.read_active_publication(tmp_path)
    if phase == "before_publication":
        assert state["lifecycle_state"] == "ABORTED"
        assert "rolled_back" in payload["reason"]
        assert publication_after == publication_before
        assert {
            path.relative_to(tmp_path): path.read_bytes()
            for path in (tmp_path / "odylith").rglob("*") if path.is_file()
        } == before
    else:
        assert publication_after is not None
        assert state["lifecycle_state"] == {
            "publication_boundary": "PREPARED",  # Durable projecting journal, pointer already active.
            "after_publication": "PUBLISHED",
            "browser_open": "CLOSED",
        }[phase]
        if phase == "browser_open":
            navigation = confirmation.greenfield_post_confirm_handoff.post_confirm_navigation(
                tmp_path, transaction_hash=transaction_hash,
            )
            assert navigation["view_status"] == "reviewed_generation"
            assert navigation["project_url"] in payload["reason"]
        else:
            assert "committed" in payload["reason"]

    monkeypatch.setattr(owner, attribute, original)
    monkeypatch.setattr(confirmation, "_DECISION_BUDGET_SECONDS", 10.0)
    retry = confirmation.maybe_handle_greenfield_decision(
        repo_root=tmp_path, host_family=host, prompt=f"CONFIRM {transaction_hash}",
    )
    assert retry is not None and retry["status"] == "CLOSED", retry
    assert retry["transaction_hash"] == transaction_hash
    assert json.loads(state_path.read_text())["lifecycle_state"] == "CLOSED"
    if phase != "before_publication":
        assert greenfield_generation_state.read_active_publication(tmp_path) == publication_after
    assert (transaction_path.read_bytes(), receipt_path.read_bytes()) == sealed_bytes


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_deadline_before_reject_deletion_preserves_pending_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, host: str,
) -> None:
    transaction, receipt, transaction_hash = _stage_pending_transaction(tmp_path)
    sealed_bytes = transaction.read_bytes(), receipt.read_bytes()

    def delayed_discard(**kwargs: object) -> None:
        time.sleep(0.5)
        pytest.fail("expired rejection reached staging deletion")

    monkeypatch.setattr(confirmation, "_DECISION_BUDGET_SECONDS", 0.05)
    monkeypatch.setattr(confirmation.greenfield_pending_transaction_store, "discard_pending_transaction", delayed_discard)
    decision = confirmation.maybe_handle_greenfield_decision(
        repo_root=tmp_path, host_family=host, prompt=f"REJECT {transaction_hash}",
    )
    assert decision is not None and decision["status"] == "RECOVERY_REQUIRED"
    assert (transaction.read_bytes(), receipt.read_bytes()) == sealed_bytes
    assert confirmation.host_hook_payload(decision)["decision"] == "block"


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_non_main_thread_fails_closed_before_pending_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, host: str,
) -> None:
    def forbidden_access(**kwargs: object) -> None:
        pytest.fail("unsupported deadline platform reached pending access")

    monkeypatch.setattr(confirmation.greenfield_pending_transaction_store, "resolve_pending_transaction", forbidden_access)
    decisions: list[dict[str, object] | None] = []
    thread = threading.Thread(target=lambda: decisions.append(
        confirmation.maybe_handle_greenfield_decision(
            repo_root=tmp_path, host_family=host, prompt=f"CONFIRM {'c' * 64}",
        )
    ))
    thread.start()
    thread.join(timeout=1)
    assert not thread.is_alive()
    assert len(decisions) == 1
    assert decisions[0] is not None and decisions[0]["status"] == "RECOVERY_REQUIRED"
    assert confirmation.host_hook_payload(decisions[0])["decision"] == "block"
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_public_hook_consumes_deadline_without_reaching_later_routing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], host: str,
) -> None:
    hook = codex_host_prompt_context if host == "codex" else claude_host_prompt_bundle

    def delayed_resolution(**kwargs: object) -> None:
        time.sleep(0.1)

    def forbidden_route(**kwargs: object) -> None:
        pytest.fail("expired decision reached ordinary host routing")

    monkeypatch.setattr(confirmation, "_DECISION_BUDGET_SECONDS", 0.02)
    monkeypatch.setattr(confirmation.greenfield_pending_transaction_store, "resolve_pending_transaction", delayed_resolution)
    monkeypatch.setattr(hook.host_prompt_route_locks, "route_lock_context", forbidden_route)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"prompt": f"CONFIRM {'d' * 64}"})))
    assert hook.main(["--repo-root", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    assert "d" * 64 in payload["reason"]


def test_successful_callback_restores_existing_alarm(
    tmp_path: Path,
) -> None:
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)

    def caller_alarm(signum: int, frame: object) -> None:
        pytest.fail("caller alarm unexpectedly expired")

    try:
        signal.signal(signal.SIGALRM, caller_alarm)
        signal.setitimer(signal.ITIMER_REAL, 5.0)
        decision = confirmation.maybe_handle_greenfield_decision(
            repo_root=tmp_path, host_family="codex", prompt=f"CONFIRM {'e' * 64}",
        )
        assert decision is not None and decision["status"] == "STALE_TRANSACTION"
        assert signal.getsignal(signal.SIGALRM) is caller_alarm
        assert 0 < signal.getitimer(signal.ITIMER_REAL)[0] <= 5.0
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer[0] > 0:
            signal.setitimer(signal.ITIMER_REAL, *previous_timer)


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_published_deadline_retry_cannot_accept_operator_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, host: str,
) -> None:
    transaction, receipt, transaction_hash = _stage_pending_transaction(tmp_path)
    sealed_bytes = transaction.read_bytes(), receipt.read_bytes()
    journal_type = confirmation.greenfield_create_commit.GreenfieldCommitJournal
    original = journal_type.mark_published

    def interrupted(journal: object, *args: object, **kwargs: object) -> None:
        original(journal, *args, **kwargs)
        raise confirmation.host_hook_execution.HookBudgetExpired

    monkeypatch.setattr(journal_type, "mark_published", interrupted)
    decision = confirmation.maybe_handle_greenfield_decision(
        repo_root=tmp_path, host_family=host, prompt=f"CONFIRM {transaction_hash}",
    )
    assert decision is not None and decision["status"] == "RECOVERY_REQUIRED"
    monkeypatch.setattr(journal_type, "mark_published", original)
    publication = tmp_path / "odylith/index.html"
    operator_bytes = b"<!doctype html><title>operator intervention</title>\n"
    publication.write_bytes(operator_bytes)
    retry = confirmation.maybe_handle_greenfield_decision(
        repo_root=tmp_path, host_family=host, prompt=f"CONFIRM {transaction_hash}",
    )
    assert retry is not None and retry["status"] == "RECOVERY_REQUIRED"
    assert confirmation.host_hook_payload(retry)["decision"] == "block"
    assert publication.read_bytes() == operator_bytes
    assert (transaction.read_bytes(), receipt.read_bytes()) == sealed_bytes
