"""Capture the sealed pre-confirm transaction that an installed matrix case commits."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import copy
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import shlex
import time
from types import SimpleNamespace
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_create_lifecycle
from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_generation_store
from odylith.runtime.domain_intelligence import greenfield_prewrite_commit_result
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal
from odylith.runtime.domain_intelligence.greenfield_commit_transaction import _payload_hash
from odylith.runtime.domain_intelligence.greenfield_authored_assumptions import require_provisional_proof_decision
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_facts_payload,
)


DRY_RUN_RECEIPT_VERSION = "odylith.greenfield.matrix.dry-run-receipt.v2"
_HOST_REPAIR_OUTPUT_TOKENS = (
    '"reasoning_contract"', '"host_instruction"', "active-proposal.v1.json",
    "must be non-empty", "greenfield proposal validation failed",
    "greenfield proposal Tribunal failed", "host-side schema repair",
)
_TERMINAL_DECISION_REASON = (
    "Nothing has been published. Run one command in a terminal; ordinary chat approval "
    "does not authorize publication. For EDIT, replace <corrections> with your changes."
)
_TERMINAL_CONFIRMATION_VERSION = "odylith.greenfield.host-confirmation-callback.v1"
_TERMINAL_CONFIRMATION_FIELDS = frozenset(("version", "status", "command", "transaction_hash", "visible_markdown", "developer_context"))
@dataclass(frozen=True)
class CompiledCreateExecution:
    """Terminal confirmation evidence and its same-hash retry."""

    decision: Any | None
    retry_decision: Any | None
    commit_payload: Mapping[str, Any]
    failure: Any | None
    proposal_seconds: float
    confirmation_seconds: float
    retry_seconds: float
    dry_run_receipt: Mapping[str, Any]
    proposal_payload: Mapping[str, Any]
    terminal_journal: Mapping[str, Any] = field(default_factory=dict)
    terminal_journal_sha256: str = ""
    terminal_journal_text: str = ""
    terminal_pre_retry_snapshot: Mapping[str, Any] = field(default_factory=dict)
    terminal_proof_issues: tuple[str, ...] = ()
    output_contract_issues: tuple[str, ...] = ()


def commit_precompiled_transaction(
    *,
    repo_root: Path,
    proposed: Any,
    proposal_seconds: float,
    invoke_cli: Callable[[Sequence[str]], Any],
) -> CompiledCreateExecution:
    """Confirm through the terminal path, then prove same-hash terminal retry."""

    try:
        proposal_returncode = int(getattr(proposed, "returncode", 1))
    except (TypeError, ValueError):
        proposal_returncode = 1
    proposed_payload = _json_mapping(getattr(proposed, "stdout", ""))
    output_issues = _positive_journey_output_issues(proposed, stage="propose", repo_root=repo_root)
    if output_issues:
        return CompiledCreateExecution(
            decision=None,
            retry_decision=None,
            commit_payload={},
            failure=_error_result("; ".join(output_issues)),
            proposal_seconds=proposal_seconds,
            confirmation_seconds=0.0,
            retry_seconds=0.0,
            dry_run_receipt=_receipt(status="proposal_contract_failed"),
            proposal_payload=proposed_payload,
            output_contract_issues=output_issues,
        )
    if proposal_returncode != 0:
        return CompiledCreateExecution(
            decision=None,
            retry_decision=None,
            commit_payload={},
            failure=proposed,
            proposal_seconds=proposal_seconds,
            confirmation_seconds=0.0,
            retry_seconds=0.0,
            dry_run_receipt=_receipt(status="proposal_failed"),
            proposal_payload=proposed_payload,
        )
    proposal_mode = str(proposed_payload.get("mode") or "").strip()
    if proposal_mode == "clarification_required":
        return CompiledCreateExecution(
            decision=None,
            retry_decision=None,
            commit_payload={},
            failure=SimpleNamespace(
                returncode=2,
                stdout=getattr(proposed, "stdout", ""),
                stderr="greenfield proposal requires a material clarification before compiling a transaction",
            ),
            proposal_seconds=proposal_seconds,
            confirmation_seconds=0.0,
            retry_seconds=0.0,
            dry_run_receipt=_receipt(status="clarification_required", proposal_mode=proposal_mode),
            proposal_payload=proposed_payload,
        )
    summary = _mapping(proposed_payload.get("product_create_transaction"))
    transaction_hash = str(summary.get("transaction_hash") or "").strip()
    transaction_file = str(proposed_payload.get("transaction_file") or "").strip()
    if proposal_mode != "product_create_transaction" or not transaction_hash or not transaction_file:
        return CompiledCreateExecution(
            decision=None,
            retry_decision=None,
            commit_payload={},
            failure=_error_result("greenfield propose did not return a ProductCreateTransaction hash and transaction file"),
            proposal_seconds=proposal_seconds,
            confirmation_seconds=0.0,
            retry_seconds=0.0,
            dry_run_receipt=_receipt(status="proposal_contract_failed", proposal_mode=proposal_mode),
            proposal_payload=proposed_payload,
        )
    receipt, issues = _sealed_dry_run_receipt(
        repo_root=repo_root,
        transaction_file=transaction_file,
        transaction_hash=transaction_hash,
        proposal_mode=proposal_mode,
    )
    if issues:
        return CompiledCreateExecution(
            decision=None,
            retry_decision=None,
            commit_payload={},
            failure=_error_result("greenfield propose returned an invalid pre-confirm transaction: " + "; ".join(issues)),
            proposal_seconds=proposal_seconds,
            confirmation_seconds=0.0,
            retry_seconds=0.0,
            dry_run_receipt=receipt,
            proposal_payload=proposed_payload,
        )
    started = time.perf_counter()
    decision = invoke_cli(
        (
            "./.odylith/bin/odylith",
            "greenfield",
            "decide",
            "--repo-root",
            ".",
            "CONFIRM",
            transaction_hash,
            "--json",
        )
    )
    confirmation_seconds = round(time.perf_counter() - started, 3)
    journal, journal_sha256, journal_text, terminal_issues = _terminal_confirmation_issues(
        decision=decision, receipt=receipt, repo_root=repo_root,
    )
    terminal_issues = tuple(dict.fromkeys(
        (*_positive_journey_output_issues(decision, stage="decide", repo_root=repo_root), *terminal_issues)
    ))
    commit_payload = _mapping(journal.get("commit_result"))
    if terminal_issues:
        return CompiledCreateExecution(
            decision=decision,
            retry_decision=None,
            commit_payload=commit_payload,
            failure=_error_result("; ".join(terminal_issues)),
            proposal_seconds=proposal_seconds,
            confirmation_seconds=confirmation_seconds,
            retry_seconds=0.0,
            dry_run_receipt=receipt,
            proposal_payload=proposed_payload,
            terminal_journal=journal,
            terminal_journal_sha256=journal_sha256,
            terminal_journal_text=journal_text,
            terminal_proof_issues=terminal_issues,
        )
    before_retry = _terminal_state_snapshot(repo_root=repo_root, receipt=receipt, journal_sha256=journal_sha256)
    started = time.perf_counter()
    retry_decision = invoke_cli(
        (
            "./.odylith/bin/odylith", "greenfield", "decide", "--repo-root", ".",
            "CONFIRM", transaction_hash, "--json",
        )
    )
    retry_seconds = round(time.perf_counter() - started, 3)
    retry_journal, retry_sha256, _retry_text, retry_issues = _terminal_confirmation_issues(
        decision=retry_decision, receipt=receipt, repo_root=repo_root,
    )
    output_issues = tuple(dict.fromkeys((
        *_positive_journey_output_issues(retry_decision, stage="decide", repo_root=repo_root),
        *retry_issues,
    )))
    if _mapping(retry_journal.get("commit_result")) != commit_payload:
        output_issues += ("same-hash terminal retry did not return the terminal confirmation identity",)
    if before_retry != _terminal_state_snapshot(repo_root=repo_root, receipt=receipt, journal_sha256=journal_sha256):
        output_issues += ("same-hash terminal retry changed terminal confirmation state",)
    if retry_sha256 != journal_sha256:
        output_issues += ("same-hash terminal retry changed terminal journal bytes",)
    return CompiledCreateExecution(
        decision=decision,
        retry_decision=retry_decision,
        commit_payload=commit_payload,
        failure=None,
        proposal_seconds=proposal_seconds,
        confirmation_seconds=confirmation_seconds,
        retry_seconds=retry_seconds,
        dry_run_receipt=receipt,
        proposal_payload=proposed_payload,
        terminal_journal=journal,
        terminal_journal_sha256=journal_sha256,
        terminal_journal_text=journal_text,
        terminal_pre_retry_snapshot=before_retry,
        terminal_proof_issues=terminal_issues,
        output_contract_issues=output_issues,
    )


def _terminal_confirmation_issues(
    *, decision: Any, receipt: Mapping[str, Any], repo_root: Path,
) -> tuple[dict[str, Any], str, str, tuple[str, ...]]:
    """Read the durable terminal result; never synthesize a create response."""

    transaction_hash = str(receipt.get("transaction_hash") or "").strip()
    write_set_hash = str(receipt.get("repository_write_set_hash") or "").strip()
    issues: list[str] = []
    if getattr(decision, "returncode", 1) != 0:
        issues.append("terminal CONFIRM did not succeed")
    response = _json_mapping(getattr(decision, "stdout", ""))
    if (
        set(response) != _TERMINAL_CONFIRMATION_FIELDS
        or response.get("version") != _TERMINAL_CONFIRMATION_VERSION
        or response.get("status") != "CLOSED"
        or response.get("command") != "CONFIRM"
        or response.get("transaction_hash") != transaction_hash
        or not str(response.get("visible_markdown") or "").strip()
        or not str(response.get("developer_context") or "").strip()
    ):
        issues.append("terminal CONFIRM did not return the exact CLOSED response")
    root = Path(repo_root).expanduser().resolve()
    journal_path = root / ".odylith/runtime/greenfield/create-journal" / transaction_hash / "state.v1.json"
    try:
        GreenfieldCommitJournal.pin_reviewed_generation(repo_root=root, transaction_hash=transaction_hash)
        journal_bytes = journal_path.read_bytes()
        journal = _json_mapping(journal_bytes)
    except (OSError, RuntimeError, ValueError):
        return {}, "", "", tuple(dict.fromkeys([*issues, "terminal CONFIRM journal is missing or invalid"]))
    journal_sha256 = hashlib.sha256(journal_bytes).hexdigest()
    try:
        journal_text = journal_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return {}, "", "", tuple(dict.fromkeys([*issues, "terminal CONFIRM journal is missing or invalid"]))
    if journal.get("state") != "closed" or journal.get("lifecycle_state") != greenfield_create_lifecycle.CLOSED:
        issues.append("terminal CONFIRM journal is not CLOSED")
    if (
        journal.get("transaction_hash") != transaction_hash
        or journal.get("repository_write_set_hash") != write_set_hash
    ):
        issues.append("terminal CONFIRM journal identity does not match the sealed transaction")
    commit_result = _mapping(journal.get("commit_result"))
    if not commit_result:
        issues.append("terminal CONFIRM journal is missing its commit result")
    else:
        try:
            greenfield_prewrite_commit_result.require_greenfield_commit_result_preview(commit_result)
        except ValueError:
            issues.append("terminal CONFIRM journal has an invalid sealed commit result")
        if _mapping(commit_result.get("validation_gate")).get("status") != "passed":
            issues.append("terminal CONFIRM journal commit result did not pass validation")
        issues.extend(dry_run_commit_issues(receipt=receipt, create_payload=commit_result, repo_root=root))
    return journal, journal_sha256, journal_text, tuple(dict.fromkeys(issues))


def _terminal_state_snapshot(
    *, repo_root: Path, receipt: Mapping[str, Any], journal_sha256: str,
) -> dict[str, Any]:
    """Capture only sealed state already checked before an optional idempotency retry."""

    root = Path(repo_root).expanduser().resolve()
    transaction_hash = str(receipt["transaction_hash"])
    pinned = GreenfieldCommitJournal.pin_reviewed_generation(
        repo_root=root, transaction_hash=transaction_hash,
    )
    return {
        "journal_sha256": journal_sha256,
        "active_generation": greenfield_generation_state.active_generation_identity(root),
        "generation_after": greenfield_repository_write_set.greenfield_managed_fingerprints(pinned.repository_root),
        "repository_after": greenfield_repository_write_set.greenfield_managed_fingerprints(root),
    }


def _positive_journey_output_issues(result: Any, *, stage: str, repo_root: Path) -> tuple[str, ...]:
    if getattr(result, "returncode", 1) != 0:
        return ()
    output = "\n".join(str(getattr(result, stream, "") or "") for stream in ("stdout", "stderr"))
    issues = [
        f"greenfield {stage} exposed a host-side repair contract: {token}"
        for token in _HOST_REPAIR_OUTPUT_TOKENS if token in output
    ]
    return tuple(issues)


def confirmation_preview_issues(
    *,
    proposal_payload: Mapping[str, Any],
    repo_root: Path,
    execution: CompiledCreateExecution | None = None,
) -> tuple[str, ...]:
    """Validate the terminal offer and its optional terminal execution proof."""

    transaction = _mapping(proposal_payload.get("product_create_transaction"))
    transaction_hash = str(transaction.get("transaction_hash") or "").strip()
    confirmation = _mapping(proposal_payload.get("confirmation"))
    choices = confirmation.get("choices")
    issues: list[str] = []
    if str(proposal_payload.get("mode") or "").strip() != "product_create_transaction":
        issues.append("pre-confirm payload did not expose a ProductCreateTransaction")
    if not _is_sha256(transaction_hash):
        issues.append("pre-confirm payload is missing a valid transaction hash")
    if not str(proposal_payload.get("transaction_file") or "").strip():
        issues.append("pre-confirm payload is missing its transaction file")
    if str(confirmation.get("status") or "").strip() != "terminal_only":
        issues.append("pre-confirm payload does not expose the terminal-only decision offer")
    if str(confirmation.get("interface") or "").strip() != "terminal":
        issues.append("pre-confirm terminal decision offer does not declare the terminal interface")
    if not str(confirmation.get("reason") or "").strip():
        issues.append("pre-confirm terminal decision offer is missing its reason")
    elif str(confirmation["reason"]).strip() != _TERMINAL_DECISION_REASON:
        issues.append("pre-confirm terminal decision offer has an invalid terminal warning")
    allowed_fields = {"status", "interface", "reason", "choices"}
    unexpected_fields = sorted(set(confirmation) - allowed_fields)
    if unexpected_fields:
        issues.append("pre-confirm terminal decision offer exposes unsupported authority fields")
    expected_root = str(repo_root.expanduser().resolve())
    expected_labels = ("CONFIRM", "EDIT", "REJECT")
    if not isinstance(choices, list):
        issues.append("pre-confirm terminal decision offer is missing its choices list")
    elif len(choices) != len(expected_labels):
        issues.append("pre-confirm terminal decision offer must contain exactly three choices")
    else:
        labels: list[str] = []
        for choice in choices:
            if not isinstance(choice, Mapping) or set(choice) != {"label", "command"}:
                issues.append("pre-confirm terminal decision choice has an invalid shape")
                continue
            label = str(choice["label"] or "").strip()
            labels.append(label)
            try:
                command = shlex.split(str(choice["command"] or ""))
            except ValueError:
                issues.append("pre-confirm terminal decision choice is not shell-parseable")
                continue
            expected_command = [
                "odylith", "greenfield", "decide", "--repo-root", expected_root,
                label, transaction_hash,
            ]
            if label == "EDIT":
                expected_command.extend(("--edit", "<corrections>"))
            if command != expected_command:
                issues.append("pre-confirm terminal decision choice is not the exact repo/hash-bound command")
        if tuple(labels) != expected_labels:
            issues.append("pre-confirm terminal decision offer must contain CONFIRM, EDIT, and REJECT once each")
    if execution is None:
        issues.append("terminal decision offer remains unqualified: terminal execution proof is absent")
    else:
        if execution.decision is None or execution.retry_decision is None:
            issues.append("terminal decision execution proof is incomplete")
        if execution.terminal_proof_issues:
            issues.append("terminal decision execution proof has sealed-state failures")
        if execution.output_contract_issues:
            issues.append("terminal decision retry proof has sealed-state failures")
        if not _mapping(execution.commit_payload):
            issues.append("terminal decision execution proof is missing the saved commit payload")
        if not str(execution.terminal_journal_sha256 or "").strip():
            issues.append("terminal decision execution proof is missing the journal record hash")
    return tuple(issues)


def terminal_handoff_issues(
    *,
    terminal_decision: Any,
    repo_root: Path,
    transaction_hash: str,
    browser_open_suppressed: bool,
) -> tuple[str, ...]:
    """Bind the terminal handoff form to its reviewed generation and browser policy."""

    root = Path(repo_root).expanduser().resolve()
    try:
        reviewed = GreenfieldCommitJournal.pin_reviewed_generation(
            repo_root=root, transaction_hash=transaction_hash,
        )
    except (OSError, RuntimeError, ValueError):
        return ("terminal handoff has no valid reviewed generation receipt",)
    dashboard = (reviewed.repository_root / "odylith/index.html").resolve()
    response = _json_mapping(getattr(terminal_decision, "stdout", ""))
    visible = str(response.get("visible_markdown") or "")
    project_url = f"{dashboard.as_uri()}?tab=project"
    opened_handoff = f"Opened the committed [Project dashboard]({project_url})."
    fallback_handoff = (
        "The package is committed. Open the "
        f"[Project dashboard]({project_url}) or use `{dashboard}`."
    )
    missing = []
    if response.get("transaction_hash") != transaction_hash:
        missing.append("transaction receipt")
    if project_url not in visible:
        missing.append("reviewed generation project URL")
    if opened_handoff not in visible and f"`{dashboard}`" not in visible:
        missing.append("reviewed generation dashboard path")
    if browser_open_suppressed and fallback_handoff not in visible and not missing:
        missing.append("suppressed-browser fallback handoff")
    elif not browser_open_suppressed and opened_handoff not in visible and fallback_handoff not in visible and not missing:
        missing.append("reviewed generation handoff")
    if not dashboard.is_file():
        missing.append("reviewed generation dashboard")
    return (
        ("terminal handoff does not expose the reviewed generation: " + ", ".join(missing),)
        if missing else ()
    )


def dry_run_commit_issues(
    *,
    receipt: Mapping[str, Any],
    create_payload: Mapping[str, Any],
    repo_root: Path,
) -> tuple[str, ...]:
    """Require the successful create readback to match the receipt captured before confirmation."""

    if str(receipt.get("version") or "") != DRY_RUN_RECEIPT_VERSION:
        return ("pre-confirm dry-run receipt version is unsupported",)
    if str(receipt.get("status") or "") != "compiled":
        return ("pre-confirm dry-run receipt was not compiled before commit",)
    expected_transaction = str(receipt.get("transaction_hash") or "").strip()
    expected_product_facts = str(receipt.get("product_facts_sha256") or "").strip()
    expected_write_set = str(receipt.get("repository_write_set_hash") or "").strip()
    required_digests = {
        "transaction hash": expected_transaction,
        "transaction bytes hash": str(receipt.get("transaction_file_sha256") or "").strip(),
        "transaction body hash": str(receipt.get("transaction_body_sha256") or "").strip(),
        "compiler receipt hash": str(receipt.get("compiler_receipt_sha256") or "").strip(),
        "product facts hash": expected_product_facts,
        "atomic custody hash": str(receipt.get("atomic_custody_sha256") or "").strip(),
        "repository write-set hash": expected_write_set,
        "publication bytes hash": str(receipt.get("publication_sha256") or "").strip(),
    }
    invalid = [label for label, value in required_digests.items() if not _is_sha256(value)]
    if invalid:
        return ("pre-confirm dry-run receipt is missing valid " + ", ".join(invalid),)
    if required_digests["transaction body hash"] != expected_transaction:
        return ("pre-confirm dry-run receipt transaction body hash is not transaction-bound",)
    expected_after = _fingerprint_mapping(receipt.get("managed_after_fingerprints"))
    if expected_after is None:
        return ("pre-confirm dry-run receipt is missing exact managed after-state fingerprints",)

    manifest = _mapping(create_payload.get("commit_manifest"))
    write_transaction = _mapping(manifest.get("write_transaction"))
    manifest_transaction = _mapping(manifest.get("product_create_transaction"))
    create_transaction = _mapping(create_payload.get("product_create_transaction"))
    repository_write_set = _mapping(create_payload.get("repository_write_set"))
    observed_transactions = (
        str(create_transaction.get("transaction_hash") or "").strip(),
        str(manifest_transaction.get("transaction_hash") or "").strip(),
        str(write_transaction.get("product_create_transaction_hash") or "").strip(),
    )
    observed_product_facts = (
        str(create_transaction.get("product_facts_sha256") or "").strip(),
        str(manifest_transaction.get("product_facts_sha256") or "").strip(),
        str(write_transaction.get("product_facts_sha256") or "").strip(),
    )
    observed_write_sets = (
        str(create_transaction.get("repository_write_set_hash") or "").strip(),
        str(manifest_transaction.get("repository_write_set_hash") or "").strip(),
        str(write_transaction.get("repository_write_set_hash") or "").strip(),
        str(repository_write_set.get("write_set_hash") or "").strip(),
    )
    issues: list[str] = []
    if any(value != expected_transaction for value in observed_transactions):
        issues.append("commit readback does not match the pre-confirm transaction hash")
    if any(value != expected_product_facts for value in observed_product_facts):
        issues.append("commit readback does not match the pre-confirm product facts hash")
    if any(value != expected_write_set for value in observed_write_sets):
        issues.append("commit readback does not match the pre-confirm repository write-set hash")
    if str(write_transaction.get("lifecycle_version") or "").strip() != (
        greenfield_create_lifecycle.CREATE_LIFECYCLE_VERSION
    ):
        issues.append("commit readback does not expose the supported create lifecycle")
    if str(write_transaction.get("lifecycle_state") or "").strip() != greenfield_create_lifecycle.CLOSED:
        issues.append("commit readback lifecycle is not CLOSED")
    issues.extend(_sealed_file_readback_issues(repo_root=repo_root, receipt=receipt))
    issues.extend(
        _active_generation_issues(
            repo_root=repo_root,
            transaction_hash=expected_transaction,
            write_set_hash=expected_write_set,
            after_fingerprints=expected_after,
            publication_sha256=str(receipt["publication_sha256"]),
        )
    )
    return tuple(dict.fromkeys(issues))


def _sealed_dry_run_receipt(
    *,
    repo_root: Path,
    transaction_file: str,
    transaction_hash: str,
    proposal_mode: str,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    receipt = _receipt(
        status="invalid",
        proposal_mode=proposal_mode,
        transaction_file=transaction_file,
        transaction_hash=transaction_hash,
    )
    transaction_path, path_issue = _repo_path(repo_root, transaction_file)
    if path_issue:
        return receipt, (path_issue,)
    compiler_receipt_path = transaction_path.with_name(transaction_path.name + ".compiler-receipt.v1.json")
    try:
        transaction_bytes = transaction_path.read_bytes()
        compiler_receipt_bytes = compiler_receipt_path.read_bytes()
    except OSError as error:
        return receipt, (f"pre-confirm transaction receipt is unavailable: {error}",)
    transaction = _json_mapping(transaction_bytes)
    compiler_receipt = _json_mapping(compiler_receipt_bytes)
    transaction_file_sha256 = hashlib.sha256(transaction_bytes).hexdigest()
    compiler_receipt_sha256 = hashlib.sha256(compiler_receipt_bytes).hexdigest()
    quality_manifest = _mapping(transaction.get("quality_manifest"))
    semantic_snapshot = _semantic_snapshot(transaction)
    authority = _mapping(transaction.get("intent_authority"))
    prewrite_package = _mapping(transaction.get("prewrite_package"))
    repository_write_set = _mapping(prewrite_package.get("repository_write_set"))
    commit_summary = _mapping(transaction.get("commit_summary"))
    product_facts_sha256 = str(authority.get("product_facts_sha256") or "").strip()
    atomic_custody_sha256 = str(authority.get("atomic_custody_sha256") or "").strip()
    repository_write_set_hash = str(repository_write_set.get("write_set_hash") or "").strip()
    after_fingerprints = _fingerprint_mapping(repository_write_set.get("after_fingerprints"))
    body_transaction_hash = _payload_hash(transaction)
    receipt.update(
        {
            "transaction_file": str(transaction_path.relative_to(Path(repo_root).resolve())),
            "transaction_file_sha256": transaction_file_sha256,
            "transaction_body_sha256": body_transaction_hash,
            "compiler_receipt_file": str(compiler_receipt_path.relative_to(Path(repo_root).resolve())),
            "compiler_receipt_sha256": compiler_receipt_sha256,
            "compiler_receipt_transaction_hash": str(compiler_receipt.get("transaction_hash") or "").strip(),
            "product_facts_sha256": product_facts_sha256,
            "atomic_custody_sha256": atomic_custody_sha256,
            "repository_write_set_hash": repository_write_set_hash,
            "managed_after_fingerprints": after_fingerprints or {},
            "preconfirm_quality_status": str(quality_manifest.get("status") or "").strip(),
            "preconfirm_validation_status": str(quality_manifest.get("validation_status") or "").strip(),
            "semantic_snapshot": semantic_snapshot,
            "semantic_snapshot_sha256": _sha256_json(semantic_snapshot) if semantic_snapshot else "",
        }
    )
    issues: list[str] = []
    try:
        manifest_text = prewrite_package.get("generation_manifest_text")
        greenfield_generation_store.require_sealed_greenfield_generation_manifest(
            manifest_text, write_set=repository_write_set,
        )
        publication = greenfield_generation_state.require_sealed_greenfield_publication_entry(
            prewrite_package.get("publication_entry_text"),
            write_set_hash=repository_write_set_hash,
            generation_manifest_sha256=hashlib.sha256(manifest_text.encode("utf-8")).hexdigest(),
        )
        receipt["publication_sha256"] = publication["publication_sha256"]
    except (TypeError, ValueError):
        issues.append("pre-confirm transaction is missing valid sealed generation/publication bytes")
    declared_transaction_hash = str(transaction.get("transaction_hash") or "").strip()
    if declared_transaction_hash != transaction_hash:
        issues.append("transaction file hash does not match the propose response")
    if declared_transaction_hash != body_transaction_hash:
        issues.append("transaction body does not match its declared transaction hash")
    if str(compiler_receipt.get("transaction_hash") or "").strip() != transaction_hash:
        issues.append("compiler receipt hash does not match the propose response")
    if str(compiler_receipt.get("transaction_file_sha256") or "").strip() != transaction_file_sha256:
        issues.append("compiler receipt file digest does not match the transaction bytes")
    if not _is_sha256(product_facts_sha256):
        issues.append("pre-confirm transaction is missing a valid product facts hash")
    if str(commit_summary.get("product_facts_sha256") or "").strip() != product_facts_sha256:
        issues.append("pre-confirm transaction summary does not match its product facts hash")
    if not _is_sha256(atomic_custody_sha256):
        issues.append("pre-confirm transaction is missing a valid atomic custody hash")
    if not _is_sha256(repository_write_set_hash):
        issues.append("pre-confirm transaction is missing a valid repository write-set hash")
    if str(commit_summary.get("repository_write_set_hash") or "").strip() != repository_write_set_hash:
        issues.append("pre-confirm transaction summary does not match its repository write-set hash")
    if after_fingerprints is None:
        issues.append("pre-confirm transaction is missing exact managed after-state fingerprints")
    if receipt["preconfirm_quality_status"] != "passed":
        issues.append("pre-confirm transaction quality is not passed")
    if receipt["preconfirm_validation_status"] != "passed":
        issues.append("pre-confirm transaction validation is not passed")
    if not semantic_snapshot:
        issues.append("pre-confirm transaction does not expose canonical semantic facts")
    if issues:
        return receipt, tuple(issues)
    receipt["status"] = "compiled"
    return receipt, ()


def _receipt(*, status: str, **values: Any) -> dict[str, Any]:
    return {"version": DRY_RUN_RECEIPT_VERSION, "status": status, **values}


def _semantic_snapshot(transaction: Mapping[str, Any]) -> dict[str, Any]:
    proposal = _mapping(transaction.get("proposal"))
    intent = _mapping(proposal.get("intent"))
    authored_semantics = intent.get("authored_semantics")
    try:
        require_provisional_proof_decision(intent)
        facts = product_facts_payload(intent)
    except ValueError:
        return {}
    if not all(key in facts for key in ("product_story", "state_object", "first_path")):
        return {}
    authority = _mapping(transaction.get("intent_authority"))
    operating_envelope = _mapping(authority.get("operating_envelope"))
    material_fields = _mapping(authority.get("material_fields"))
    atomic_facts = [dict(row) for row in authority.get("atomic_facts", ()) if isinstance(row, Mapping)]
    custody = {
        key: {
            "custody_state": str(_mapping(value).get("custody_state") or "").strip(),
            "entailment_relationship": str(_mapping(value).get("entailment_relationship") or "").strip(),
        }
        for key, value in sorted(material_fields.items())
        if isinstance(value, Mapping)
    }
    return {
        "facts": facts,
        "material_custody": custody,
        "atomic_facts": atomic_facts,
        "atomic_custody_sha256": str(authority.get("atomic_custody_sha256") or "").strip(),
        "product_facts_sha256": str(authority.get("product_facts_sha256") or "").strip(),
        "authored_semantics": (
            copy.deepcopy(authored_semantics)
            if isinstance(authored_semantics, Mapping)
            else None
        ),
        "authored_relation_set_sha256": copy.deepcopy(
            authority.get("authored_relation_set_sha256")
        ),
        # Release scoring must use the exact support receipt reviewed before
        # confirmation.  Copying it here preserves that authority boundary;
        # the matrix never recomputes an operating-envelope classification.
        "operating_envelope": copy.deepcopy(operating_envelope),
    }


def _active_generation_issues(
    *,
    repo_root: Path,
    transaction_hash: str,
    write_set_hash: str,
    after_fingerprints: Mapping[str, str],
    publication_sha256: str,
) -> tuple[str, ...]:
    root = Path(repo_root).expanduser().resolve()
    issues: list[str] = []
    try:
        state = greenfield_generation_state.active_generation_identity(root)
    except (OSError, RuntimeError, ValueError):
        return ("active generation readback is missing or invalid",)
    if state["status"] != greenfield_generation_state.ACTIVE:
        return ("active generation readback is missing or invalid",)
    try:
        pinned = GreenfieldCommitJournal.pin_reviewed_generation(
            repo_root=root,
            transaction_hash=transaction_hash,
        )
    except (OSError, RuntimeError, ValueError):
        return ("immutable generation readback is missing or invalid",)
    expected_identity = {
        "status": greenfield_generation_state.ACTIVE,
        "write_set_hash": write_set_hash,
        "generation_manifest_sha256": pinned.manifest_sha256,
        "publication_sha256": publication_sha256,
    }
    observed_identity = {
        key: str(state.get(key) or "").strip()
        for key in expected_identity
    }
    if observed_identity != expected_identity:
        issues.append("active generation identity does not match the sealed transaction")
    if pinned.write_set_hash != write_set_hash:
        issues.append("immutable generation identity does not match the sealed transaction")
    manifest_after = _fingerprint_mapping(pinned.manifest.get("after_fingerprints"))
    if manifest_after != dict(after_fingerprints):
        issues.append("immutable generation manifest does not match the sealed managed after-state")
    try:
        generation_after = greenfield_repository_write_set.greenfield_managed_fingerprints(
            pinned.repository_root
        )
        repository_after = greenfield_repository_write_set.greenfield_managed_fingerprints(root)
    except (OSError, RuntimeError, ValueError):
        issues.append("managed after-state readback is unavailable")
        return tuple(issues)
    if generation_after != dict(after_fingerprints):
        issues.append("immutable generation repository does not match the sealed managed after-state")
    if repository_after != dict(after_fingerprints):
        issues.append("managed repository readback does not match the sealed after-state")
    return tuple(issues)


def _sealed_file_readback_issues(
    *,
    repo_root: Path,
    receipt: Mapping[str, Any],
) -> tuple[str, ...]:
    issues: list[str] = []
    for label, path_key, digest_key in (
        ("transaction", "transaction_file", "transaction_file_sha256"),
        ("compiler receipt", "compiler_receipt_file", "compiler_receipt_sha256"),
    ):
        path, path_issue = _repo_path(repo_root, str(receipt.get(path_key) or ""))
        if path_issue:
            issues.append(f"post-confirm {label} readback path escapes the case repository")
            continue
        try:
            observed = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            issues.append(f"post-confirm {label} readback is unavailable")
            continue
        if observed != str(receipt.get(digest_key) or "").strip():
            issues.append(f"post-confirm {label} bytes do not match the pre-confirm receipt")
    return tuple(issues)


def _fingerprint_mapping(value: Any) -> dict[str, str] | None:
    if not isinstance(value, Mapping):
        return None
    fingerprints = {str(key): str(item or "").strip() for key, item in value.items()}
    if set(fingerprints) != set(greenfield_repository_write_set.GREENFIELD_REPOSITORY_WRITE_PATHS):
        return None
    if any(not _is_sha256(item) for item in fingerprints.values()):
        return None
    return fingerprints


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _repo_path(repo_root: Path, token: str) -> tuple[Path, str]:
    root = Path(repo_root).resolve()
    candidate = (root / token).resolve() if not Path(token).is_absolute() else Path(token).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return candidate, "pre-confirm transaction path escapes the case repository"
    return candidate, ""


def _error_result(message: str) -> SimpleNamespace:
    return SimpleNamespace(
        returncode=2,
        stdout=json.dumps({"mode": "error", "error": message}, sort_keys=True),
        stderr="",
    )


def _json_mapping(value: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(value.decode("utf-8") if isinstance(value, bytes) else str(value or ""))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return _mapping(parsed)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


__all__ = [
    "DRY_RUN_RECEIPT_VERSION",
    "CompiledCreateExecution",
    "commit_precompiled_transaction",
    "dry_run_commit_issues",
]
