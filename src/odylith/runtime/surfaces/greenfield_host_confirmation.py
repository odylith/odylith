"""Deterministic Greenfield decision callback shared by supported hosts."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import re
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store
from odylith.runtime.domain_intelligence import greenfield_post_confirm_handoff
from odylith.runtime.domain_intelligence import greenfield_repository_lock


HOST_CONFIRMATION_CALLBACK_VERSION = "odylith.greenfield.host-confirmation-callback.v1"
SUPPORTED_HOSTS = frozenset({"codex", "claude"})
PENDING_ROOT_RELATIVE_PATH = Path(".odylith/runtime/greenfield/pending")
_DECISION_PATTERN = re.compile(r"^(CONFIRM|EDIT|REJECT)\s+([0-9a-f]{64})(?:\s+(.+))?$", re.DOTALL)


def maybe_handle_greenfield_decision(
    *,
    repo_root: Path | str,
    host_family: str,
    prompt: str,
) -> dict[str, Any] | None:
    """Handle exact pending-transaction commands before host model reasoning."""

    host = str(host_family or "").strip().casefold()
    if host not in SUPPORTED_HOSTS:
        return None
    root = Path(repo_root).expanduser().resolve()
    command_text = str(prompt or "").strip()
    match = _DECISION_PATTERN.fullmatch(command_text)
    if match is None:
        if command_text in {"CONFIRM", "EDIT", "REJECT"} and _has_pending_transactions(root):
            return _decision(
                status="DECISION_HASH_REQUIRED",
                command=command_text,
                visible_markdown=(
                    "**Odylith Greenfield needs the approval code**\n\n"
                    "Copy the complete hash-bound command from the proposal. The code is what binds your decision "
                    "to the exact package you reviewed."
                ),
                developer_context="Do not infer a pending package from a mutable current pointer. Ask for the exact displayed command.",
            )
        return None
    command, transaction_hash, edit_evidence = match.groups()
    try:
        transaction_path = greenfield_pending_transaction_store.resolve_pending_transaction(
            repo_root=root,
            transaction_hash=transaction_hash,
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        return _decision(
            status="STALE_TRANSACTION",
            command=command,
            transaction_hash=transaction_hash,
            visible_markdown=(
                "**Odylith Greenfield transaction is unavailable**\n\n"
                "No governed records were written. Rebuild and review a new hash-bound package."
            ),
            developer_context=f"Report STALE_TRANSACTION without product-intent failure language. Detail: {error}",
        )
    if command == "EDIT":
        return _decision(
            status="edit_evidence_received" if edit_evidence else "edit_evidence_required",
            command=command,
            transaction_hash=transaction_hash,
            visible_markdown=(
                "**Odylith Greenfield edit**\n\n"
                + (
                    "The correction is new evidence. Odylith will rebuild the full package and show a new hash before anything is written."
                    if edit_evidence
                    else "Add the correction after the hash in the same reply. Odylith will treat it as new evidence, rebuild the full package, and show a new hash before anything is written."
                )
            ),
            developer_context=(
                "No transaction was committed. Rebuild from the supplied correction as new evidence; do not mutate the reviewed package."
                if edit_evidence
                else "No transaction was committed. Ask only for the user's correction; do not reinterpret or write artifacts."
            ),
        )
    if command == "REJECT":
        return _reject_pending_transaction(root=root, transaction_hash=transaction_hash)
    return _confirm_pending_transaction(
        root=root,
        transaction_path=transaction_path,
        transaction_hash=transaction_hash,
    )


def host_hook_payload(decision: Mapping[str, Any]) -> dict[str, Any]:
    """Return the same UserPromptSubmit transport shape for Codex and Claude."""

    visible = str(decision.get("visible_markdown") or "").strip()
    context = str(decision.get("developer_context") or "").strip()
    payload: dict[str, Any] = {}
    if visible:
        payload["systemMessage"] = visible
    if context:
        payload["hookSpecificOutput"] = {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    return payload


def confirmation_supported(host_family: str) -> bool:
    return str(host_family or "").strip().casefold() in SUPPORTED_HOSTS


def _confirm_pending_transaction(
    *,
    root: Path,
    transaction_path: Path,
    transaction_hash: str,
) -> dict[str, Any]:
    try:
        result = greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=root,
            transaction_file=transaction_path,
            transaction_hash=transaction_hash,
            confirm=True,
        )
    except greenfield_create_commit.GreenfieldCreateCommitError as error:
        if error.failure_kind == "post_confirm_repository_busy":
            return _decision(
                status="BUSY_NO_WRITE",
                command="CONFIRM",
                visible_markdown=(
                    "**Odylith Greenfield is busy**\n\n"
                    "Another create transaction owns the repository lock. No bytes from this transaction were written. "
                    "Retry `CONFIRM` after it finishes."
                ),
                developer_context="Report BUSY_NO_WRITE. Do not regenerate, repair, or reinterpret the pending transaction.",
            )
        return _decision(
            status="RECOVERY_REQUIRED",
            command="CONFIRM",
            visible_markdown=(
                "**Odylith Greenfield needs recovery**\n\n"
                "The sealed package could not finish its environment-level publication. Product intent was not rejected. "
                f"Recovery status: `{error.rollback_status}`."
            ),
            developer_context=(
                "Report the environment/transaction outcome only. Do not generate or repair product artifacts. "
                f"Failure kind: {error.failure_kind}. Recovery path: {error.recovery_path or 'not retained'}."
            ),
        )
    except ValueError as error:
        return _decision(
            status="STALE_TRANSACTION",
            command="CONFIRM",
            visible_markdown=(
                "**Odylith Greenfield transaction is stale**\n\n"
                "No governed records were written. Run `EDIT` with the current evidence to rebuild and review a new hash."
            ),
            developer_context=f"Report STALE_TRANSACTION without Product Intent failure language. Detail: {error}",
        )
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        return _decision(
            status="RECOVERY_REQUIRED",
            command="CONFIRM",
            visible_markdown=(
                "**Odylith Greenfield could not publish**\n\n"
                "An environment or transaction-integrity failure stopped publication. Product intent was not rejected."
            ),
            developer_context=f"Report the environment outcome only; do not regenerate artifacts. Detail: {error}",
        )
    navigation = greenfield_post_confirm_handoff.post_confirm_navigation(
        root,
        transaction_hash=transaction_hash,
    )
    browser = greenfield_post_confirm_handoff.open_committed_dashboard(navigation)
    return _decision(
        status="CLOSED",
        command="CONFIRM",
        transaction_hash=transaction_hash,
        visible_markdown=greenfield_post_confirm_handoff.completion_markdown(
            transaction_hash=transaction_hash,
            result=result,
            navigation=navigation,
            browser_result=browser,
        ),
        developer_context=(
            "The exact pending Greenfield transaction was committed and read back by the pre-model Odylith callback. "
            "Do not run greenfield create, parse evidence, call a model, regenerate, or repair. Return the supplied completion handoff."
        ),
    )


def _reject_pending_transaction(*, root: Path, transaction_hash: str) -> dict[str, Any]:
    try:
        with greenfield_repository_lock.greenfield_repository_lock(root):
            greenfield_pending_transaction_store.resolve_pending_transaction(
                repo_root=root,
                transaction_hash=transaction_hash,
            )
            journal = root / ".odylith/runtime/greenfield/create-journal" / transaction_hash
            if journal.exists() or journal.is_symlink():
                if _journal_is_closed(journal):
                    return _decision(
                        status="CLOSED",
                        command="REJECT",
                        transaction_hash=transaction_hash,
                        visible_markdown=(
                            "**Odylith Greenfield is already published**\n\n"
                            "This transaction is closed, so `REJECT` cannot undo it. Use `EDIT` to propose a new "
                            "reviewed transaction or create a separately reviewed compensating change."
                        ),
                        developer_context=(
                            "Report the existing CLOSED transaction. Do not delete staging, roll back, regenerate, or "
                            "reinterpret product intent."
                        ),
                    )
                return _decision(
                    status="RECOVERY_REQUIRED",
                    command="REJECT",
                    visible_markdown=(
                        "**Odylith Greenfield cannot discard this transaction yet**\n\n"
                        "Publication recovery evidence exists, so the sealed transaction was preserved for deterministic recovery."
                    ),
                    developer_context="Do not delete a nonterminal journal or generation. Report RECOVERY_REQUIRED.",
                )
            greenfield_pending_transaction_store.discard_pending_transaction(
                repo_root=root,
                transaction_hash=transaction_hash,
            )
    except greenfield_repository_lock.GreenfieldRepositoryBusyError:
        return _decision(
            status="BUSY_NO_WRITE",
            command="REJECT",
            transaction_hash=transaction_hash,
            visible_markdown=(
                "**Odylith Greenfield is busy**\n\n"
                "Another decision owns the repository lock. This exact pending package was preserved. Retry the hash-bound `REJECT`."
            ),
            developer_context="Report BUSY_NO_WRITE. Do not delete or reinterpret another transaction.",
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        return _decision(
            status="RECOVERY_REQUIRED",
            command="REJECT",
            visible_markdown=(
                "**Odylith Greenfield could not discard staging**\n\n"
                "No governed records were written, but the pending transaction remains for safe cleanup."
            ),
            developer_context=f"Report staging cleanup failure without changing governed truth. Detail: {error}",
        )
    return _decision(
        status="ABORTED",
        command="REJECT",
        transaction_hash=transaction_hash,
        visible_markdown=(
            "**Odylith Greenfield rejected**\n\n"
            "The pending sealed transaction was discarded. No governed records were written."
        ),
        developer_context="The exact pending transaction was rejected and its terminal staging was removed. Do not write artifacts.",
    )


def _journal_is_closed(path: Path) -> bool:
    if path.is_symlink() or not path.is_dir():
        return False
    state_path = path / "state.v1.json"
    if state_path.is_symlink() or not state_path.is_file():
        return False
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, Mapping):
        return False
    return str(payload.get("state") or "") == "closed" and str(payload.get("lifecycle_state") or "") in {
        "",
        "CLOSED",
    }


def _has_pending_transactions(root: Path) -> bool:
    pending = root / PENDING_ROOT_RELATIVE_PATH
    if pending.is_symlink() or not pending.is_dir():
        return False
    return any(entry.is_dir() and not entry.is_symlink() for entry in pending.iterdir())


def _decision(
    *,
    status: str,
    command: str,
    visible_markdown: str,
    developer_context: str,
    transaction_hash: str = "",
) -> dict[str, Any]:
    return {
        "version": HOST_CONFIRMATION_CALLBACK_VERSION,
        "status": status,
        "command": command,
        "transaction_hash": transaction_hash,
        "visible_markdown": visible_markdown,
        "developer_context": developer_context,
    }


__all__ = [
    "HOST_CONFIRMATION_CALLBACK_VERSION",
    "SUPPORTED_HOSTS",
    "confirmation_supported",
    "host_hook_payload",
    "maybe_handle_greenfield_decision",
]
